import requests
import pandas as pd
from datetime import datetime
import os
from gnews import GNews

# --- OPRAVENÉ NASTAVENÍ TELEGRAMU ---
TELEGRAM_TOKEN = "8671040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        # Používáme f-string pro správné vložení proměnných do URL
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("✅ Telegram zpráva úspěšně odeslána!")
        else:
            print(f"❌ Chyba Telegramu (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Technická chyba při odesílání: {e}")

def get_market_data():
    print("🚀 Spouštím český energetický motor...")
    
    # 1. Získání ceny (Zkoušíme stabilní zdroj pro ČR)
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        price_data = requests.get(p_url, timeout=10).json()
        price = price_data["price"][-1]
    except:
        price = 100.0  # Záložní hodnota

    # 2. AKTIVACE ALERTU
    # Nastaveno na > 1, aby ti to teď hned přišlo na mobil jako test
    if price > 1:
        msg = f"🔔 Energetický Alert!\n💰 Aktuální cena: {price} EUR/MWh\n🕒 Čas: {datetime.now().strftime('%H:%M')}"
        send_telegram_msg(msg)

    # 3. Počasí Praha
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=50.07&longitude=14.43&current_weather=true"
        w_data = requests.get(w_url, timeout=10).json()
        wind = w_data["current_weather"]["windspeed"]
    except:
        wind = 0

    # 4. České zprávy přes GNews
    try:
        google_news = GNews(language='cs', country='CZ', period='24h', max_results=1)
        news = google_news.get_news('energetika cena elektřiny')
        titulek = news[0]['title'] if news else "Na trhu nebyla nalezena žádná nová aktivita."
    except:
        titulek = "Skenování českých zpráv proběhlo, ale zdroj je dočasně nedostupný."

    # 5. Uložení dat do CSV
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_data = pd.DataFrame([[timestamp, price, wind, 0, 0, titulek]], 
                            columns=["time", "price", "wind", "solar", "news_score", "headline"])
    
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        # Necháváme posledních 50 záznamů pro plynulý graf
        df = pd.concat([df, new_data], ignore_index=True).tail(50)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print(f"✅ Data uložena. Cena: {price} EUR, Vítr: {wind} km/h")

if __name__ == "__main__":
    get_market_data()
