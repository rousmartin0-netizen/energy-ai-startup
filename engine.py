import requests
import pandas as pd
from datetime import datetime
import os
from pygooglenews import GoogleNews

def get_market_data():
    print("Zahajuji sběr dat a analýzu zpráv...")
    
    # 1. Cena a Počasí (Zůstává stejné)
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        price = requests.get(p_url, timeout=10).json()["price"][-1]
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=53.55&longitude=9.99&hourly=wind_speed_100m,shortwave_radiation"
        w_data = requests.get(w_url, timeout=10).json()
        wind = w_data["hourly"]["wind_speed_100m"][0]
        solar = w_data["hourly"]["shortwave_radiation"][0]
    except:
        price, wind, solar = 0, 0, 0

    # 2. ANALÝZA ZPRÁV (Sentiment Analysis)
    gn = GoogleNews(lang='en', country='US')
    search = gn.search('European energy market prices', when='24h')
    
    # Jednoduchý slovník pro AI sentiment
    bad_words = ['crisis', 'shortage', 'spike', 'increase', 'danger', 'stop', 'war']
    good_words = ['surplus', 'drop', 'lower', 'cheap', 'renewable', 'stable']
    
    sentiment_score = 0
    for entry in search['entries'][:10]: # Projdeme posledních 10 titulků
        title = entry.title.lower()
        for word in bad_words:
            if word in title: sentiment_score += 1
        for word in good_words:
            if word in title: sentiment_score -= 1
    
    print(f"News Sentiment Score: {sentiment_score}")

    # 3. ZÁPIS DO DATABÁZE
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_data = pd.DataFrame([[timestamp, price, wind, solar, sentiment_score]], 
                            columns=["time", "price", "wind", "solar", "news_score"])
    
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        # Ošetření chybějících sloupců v historii
        for col in ["solar", "news_score"]:
            if col not in df.columns: df[col] = 0
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print("Update úspěšně dokončen.")

if __name__ == "__main__":
    get_market_data()
