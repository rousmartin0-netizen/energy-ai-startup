import requests
import pandas as pd
from datetime import datetime
import os
from gnews import GNews

# --- NASTAVENÍ TELEGRAMU ---
TELEGRAM_TOKEN = "8071040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={message}"
        requests.get(url, timeout=10)
        print("Telegram zpráva odeslána!")
    except Exception as e:
        print(f"Chyba Telegramu: {e}")

def get_market_data():
    print("Startuju český motor s alerty...")
    
    # 1. Cena pro ČR
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        price = requests.get(p_url, timeout=10).json()["price"][-1]
    except:
        price = 100.0

    # 2. TESTOVACÍ ALERT (pošle zprávu vždy, když je cena > 1 EUR - jen pro ověření)
    # Později si tu 1 změň na třeba 150
    if price > 1:
        send_telegram_msg(f"🤖 Bot Online! Aktuální cena v ČR: {price} EUR/MWh. Dashboard běží.")

    # 3. Počasí Praha
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=50.07&longitude=14.43&current_weather=true"
        w_data = requests.get(w_url, timeout=10).json()
        wind = w_data["current_weather"]["windspeed"]
    except:
        wind = 0

    # 4. České zprávy
    try:
        google_news = GNews(language='cs', country='CZ', period='24h', max_results=1)
        news = google_news.get_news('energetika cena elektřiny')
        titulek = news[0]['title'] if news else "Na trhu je klid"
    except:
        titulek = "Monitoring běží"

    # 5. Uložení
    timestamp = datetime.now().strftime("%H:%M")
    new_data = pd.DataFrame([[timestamp, price, wind, 0, 0, titulek]], 
                            columns=["time", "price", "wind", "solar", "news_score", "headline"])
    
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = pd.concat([df, new_data], ignore_index=True).tail(50)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print(f"Hotovo. Cena: {price}")

if __name__ == "__main__":
    get_market_data()
