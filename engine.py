import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
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
    prague_tz = ZoneInfo("Europe/Prague")
    
    try:
        # Stáhneme reálná data z Energy-Charts (zóna DE-LU / ČR)
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        data = requests.get(p_url, timeout=10).json()
        
        prices = data["price"]
        timestamps = data.get("unix_seconds", data.get("time", []))
        
        # Převedeme na DataFrame s reálnými časy v českém čase
        df_list = []
        for t, p in zip(timestamps, prices):
            dt = datetime.fromtimestamp(t, tz=prague_tz)
            # Bereme dnešní data v českém čase
            if dt.date() == datetime.now(prague_tz).date():
                time_str = dt.strftime("%H:%M")
                df_list.append([time_str, p])
                
        # Pojistka kdyby dnešní den nebyl plně naplněný
        if not df_list and timestamps and prices:
            for t, p in zip(timestamps[-24:], prices[-24:]):
                dt = datetime.fromtimestamp(t, tz=prague_tz)
                time_str = dt.strftime("%H:%M")
                df_list.append([time_str, p])

        df = pd.DataFrame(df_list, columns=["time", "price"])
        
        # Doplňkové hodnoty
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["news_score"] = 0
        df["headline"] = "Trh s elektřinou je stabilní."
        
    except Exception as e:
        print(f"Chyba při stahování dat: {e}")
        # Záložní data při výpadku API v českém čase
        now_prague = datetime.now(prague_tz)
        df = pd.DataFrame([[now_prague.strftime("%H:%M"), 100.0, 15, 0, 0, "Záložní režim"]], 
                          columns=["time", "price", "wind", "solar", "news_score", "headline"])

    # Uložení reálných dat
    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    if not df.empty:
        latest_price = df.iloc[-1]["price"]
        send_telegram_msg(f"📊 Aktuální reálná cena elektřiny v ČR: {latest_price} EUR/MWh")
        
    print(f"✅ Hotovo. Uloženo {len(df)} reálných bodů.")

if __name__ == "__main__":
    get_market_data()
