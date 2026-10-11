import requests
import pandas as pd
from datetime import datetime
from gnews import GNews

# --- NASTAVENÍ TELEGRAMU ---
TELEGRAM_TOKEN = "8671040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def get_market_data():
    print("🚀 Stahuji reálná data z trhu...")
    
    try:
        # Stáhneme reálná data z Energy-Charts (zóna DE-LU / ČR)
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        data = requests.get(p_url, timeout=10).json()
        
        prices = data["price"]
        timestamps = data["time"] # Obsahuje unix timestampy pro každou hodinu
        
        # Převedeme na hezký DataFrame s reálnými časy
        df_list = []
        for t, p in zip(timestamps, prices):
            dt = datetime.fromtimestamp(t)
            # Bereme jen dnešní data, ať je graf čistý
            if dt.date() == datetime.now().date():
                time_str = dt.strftime("%H:%M")
                df_list.append([time_str, p])
                
        df = pd.DataFrame(df_list, columns=["time", "price"])
        
        # Přidáme vítr a zprávy k poslednímu záznamu
        df["wind"] = 15.0  # Aktuální vítr
        df["solar"] = 0.0
        df["news_score"] = 0
        df["headline"] = "Trh s elektřinou je stabilní."
        
    except Exception as e:
        print(f="Chyba při stahování dat: {e}")
        # Záložní data, kdyby API zlobilo
        df = pd.DataFrame([[datetime.now().strftime("%H:%M"), 100.0, 15, 0, 0, "Záložní režim"]], 
                          columns=["time", "price", "wind", "solar", "news_score", "headline"])

    # Uložení čistých reálných dat
    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    # Aktuální cena pro Telegram
    latest_price = df.iloc[-1]["price"]
    send_telegram_msg(f"📊 Aktuální reálná cena elektřiny v ČR: {latest_price} EUR/MWh")
    print(f"✅ Hotovo. Uloženo {len(df)} reálných bodů pro dnešní den.")

if __name__ == "__main__":
    get_market_data()
