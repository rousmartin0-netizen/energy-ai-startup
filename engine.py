import requests
import pandas as pd
from datetime import datetime
import os
from gnews import GNews

def get_market_data():
    print("Sběr dat pro český trh zahájen...")
    
    # 1. Cena elektřiny pro ČR (Czechia)
    try:
        # Používáme kód zóny CZE
        p_url = "https://api.energy-charts.info/price?bzn=CZE"
        price = requests.get(p_url, timeout=10).json()["price"][-1]
    except:
        price = 0

    # 2. Počasí pro ČR (Praha - střed republiky)
    try:
        # Souřadnice Prahy: 50.07, 14.43
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=50.07&longitude=14.43&hourly=wind_speed_10m,shortwave_radiation"
        w_data = requests.get(w_url, timeout=10).json()
        wind = w_data["hourly"]["wind_speed_10m"][0]
        solar = w_data["hourly"]["shortwave_radiation"][0]
    except:
        wind, solar = 0, 0

    # 3. ČESKÉ ZPRÁVY (Sentiment)
    try:
        # Nastavení GNews na češtinu a ČR
        google_news = GNews(language='cs', country='CZ', period='24h', max_results=5)
        news = google_news.get_news('cena elektřiny plyn energetika')
        
        # Česká klíčová slova
        spatne = ['krize', 'zdražení', 'nedostatek', 'problém', 'nárůst', 'válka', 'stop']
        dobre = ['pokles', 'zlevnění', 'přebytek', 'stabilizace', 'obnovitelné', 'levná']
        
        sentiment_score = 0
        news_titles = []
        for item in news:
            title = item['title'].lower()
            news_titles.append(item['title'])
            for word in spatne:
                if word in title: sentiment_score += 1
            for word in dobre:
                if word in title: sentiment_score -= 1
    except:
        sentiment_score = 0
        news_titles = ["Žádné nové zprávy z trhu."]
    
    # 4. ZÁPIS DO DATABÁZE
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Uložíme i poslední titulek zprávy, abychom ho viděli v appce
    last_headline = news_titles[0] if news_titles else "Klid na trhu"
    
    new_data = pd.DataFrame([[timestamp, price, wind, solar, sentiment_score, last_headline]], 
                            columns=["time", "price", "wind", "solar", "news_score", "headline"])
    
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        # Přidáme nové sloupce do starých dat, pokud chybí
        for col in ["solar", "news_score", "headline"]:
            if col not in df.columns: df[col] = "0"
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print(f"Update hotov. Cena v ČR: {price} EUR, Sentiment: {sentiment_score}")

if __name__ == "__main__":
    get_market_data()
