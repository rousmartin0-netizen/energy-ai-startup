import requests
import pandas as pd
from datetime import datetime
import os

def get_market_data():
    # 1. Cena elektřiny (DE-LU zóna) z Energy-Charts
    try:
        price_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        prices = requests.get(price_url).json()["price"]
        current_price = prices[-1]
    except Exception as e:
        print(f"Chyba při stahování cen: {e}")
        current_price = 0

    # 2. Předpověď větru (Hamburk) z Open-Meteo
    try:
        weather_url = "https://api.open-meteo.com/v1/forecast?latitude=53.55&longitude=9.99&hourly=wind_speed_100m"
        weather_data = requests.get(weather_url).json()
        current_wind = weather_data["hourly"]["wind_speed_100m"][0]
    except Exception as e:
        print(f"Chyba při stahování počasí: {e}")
        current_wind = 0
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Vytvoření nového řádku dat
    new_data = pd.DataFrame([[timestamp, current_price, current_wind]], 
                            columns=["time", "price", "wind"])
    
    # Uložení do CSV souboru
    file_path = "market_history.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    
    df.to_csv(file_path, index=False)
    print(f"Úspěch! {timestamp} | Cena: {current_price} EUR | Vítr: {current_wind} km/h")

if __name__ == "__main__":
    get_market_data()
