import requests
import pandas as pd
from datetime import datetime
import os
import random
from gnews import GNews

def get_market_data():
    print("Startuju český motor...")
    
    # 1. Cena pro ČR (v EUR)
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU" # Stabilnější zdroj pro střední Evropu
        price = requests.get(p_url, timeout=10).json()["price"][-1]
    except:
        price = 105.0 # Záložní cena, kdyby API vypadlo

    # 2. Počasí Praha
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=50.07&longitude=14.43&current_weather=true"
        w_data = requests.get(w_url, timeout=10).json()
        wind = w_data["current_weather"]["windspeed"]
    except:
        wind = 5.0

    # 3. České zprávy
    try:
        google_news = GNews(language='cs', country='CZ', period='24h', max_results=1)
        news = google_news.get_news('energetika cena elektřiny')
        titulek = news[0]['title'] if news else "Na trhu je klid"
    except:
        titulek = "Sledování zpráv je dočasně nedostupné"

    # 4. Uložení
    timestamp = datetime.now().strftime("%H:%M")
    new_data = pd.DataFrame([[timestamp, price, wind, 0, 0, titulek]], 
                            columns=["time", "price", "wind", "solar", "news_score", "headline"])
    
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = pd.concat([df, new_data], ignore_index=True).tail(20)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print(f"Hotovo: {price} EUR")

if __name__ == "__main__":
    get_market_data()
    
