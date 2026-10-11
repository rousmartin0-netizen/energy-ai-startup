import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = "8671040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def simulate_bess_arbitrage_advanced(df):
    """
    Pokročilá fyzikální simulace 1MWh BESS kontejneru.
    - Kapacita: 1000 kWh (1 MWh)
    - Výkon střídače: 500 kW
    - Účinnost cyklu (Round-trip): 88% (~93.8% jednosměrně)
    - Bezpečné okno SoC: 50 kWh (5%) až 950 kWh (95%)
    """
    CAPACITY_KWH = 1000.0
    MAX_POWER_KW = 500.0
    EFFICIENCY = 0.88
    SQRT_EFF = np.sqrt(EFFICIENCY)
    
    SOC_MIN = 50.0
    SOC_MAX = 950.0
    
    n_hours = len(df)
    # Seřadíme data chronologicky podle času (00:00 -> 23:00)
    df = df.sort_values('time').reset_index(drop=True)
    prices = df['price'].values
    
    # Inteligentní optimalizace: Najdeme nejlevnější časy pro nákup a nejdražší pro prodej
    sorted_indices = np.argsort(prices)
    
    actions = ["IDLE"] * n_hours
    power_flow = np.zeros(n_hours) # +nabíjení, -vybíjení
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    # Startujeme den s 50% nabitou baterií (500 kWh)
    current_soc = 500.0
    
    # Simulace průběhu dne
    for idx in sorted_indices:
        p = prices[idx]
        
        # Nákup (Nabíjení) v levných / záporných hodinách
        if p < 55.0 and current_soc < SOC_MAX:
            headroom_kwh = (SOC_MAX - current_soc) / SQRT_EFF
            charge_kwh = min(MAX_POWER_KW, headroom_kwh)
            
            if charge_kwh > 1.0:
                actions[idx] = "NABÍJENÍ (CHARGE)"
                power_flow[idx] = charge_kwh
                current_soc += charge_kwh * SQRT_EFF
                cash_flow[idx] = - (charge_kwh * p) / 1000.0
                
        # Prodej (Vybíjení) v drahých špičkách
        elif p > 95.0 and current_soc > SOC_MIN:
            available_kwh = (current_soc - SOC_MIN) * SQRT_EFF
            discharge_kwh = min(MAX_POWER_KW, available_kwh)
            
            if discharge_kwh > 1.0:
                actions[idx] = "VYBÍJENÍ (DISCHARGE)"
                power_flow[idx] = -discharge_kwh
                current_soc -= discharge_kwh
                cash_flow[idx] = (discharge_kwh * p) / 1000.0

        soc_levels[idx] = current_soc

    df['bess_action'] = actions
    df['bess_power_kw'] = power_flow
    df['battery_soc_kwh'] = soc_levels
    df['hourly_cash_eur'] = cash_flow
    df['cumulative_profit_eur'] = np.cumsum(cash_flow)
    
    return df

def get_market_data():
    print("🚀 Stahuji reálná data a spouštím pokročilou BESS simulaci...")
    prague_tz = ZoneInfo("Europe/Prague")
    
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        data = requests.get(p_url, timeout=10).json()
        
        prices = data["price"]
        timestamps = data.get("unix_seconds", data.get("time", []))
        
        df_list = []
        for t, p in zip(timestamps, prices):
            dt = datetime.fromtimestamp(t, tz=prague_tz)
            if dt.date() == datetime.now(prague_tz).date():
                time_str = dt.strftime("%H:%M")
                df_list.append([time_str, p])
                
        if not df_list and timestamps and prices:
            for t, p in zip(timestamps[-24:], prices[-24:]):
                dt = datetime.fromtimestamp(t, tz=prague_tz)
                time_str = dt.strftime("%H:%M")
                df_list.append([time_str, p])

        df = pd.DataFrame(df_list, columns=["time", "price"])
        df = simulate_bess_arbitrage_advanced(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = "BESS kontejner optimalizuje denní arbitráž."
        
    except Exception as e:
        print(f"Chyba při stahování dat: {e}")
        now_prague = datetime.now(prague_tz)
        df = pd.DataFrame([[now_prague.strftime("%H:%M"), 100.0, "IDLE", 0.0, 500.0, 0.0, 0.0, 15, "Záložní režim"]], 
                          columns=["time", "price", "bess_action", "bess_power_kw", "battery_soc_kwh", "hourly_cash_eur", "cumulative_profit_eur", "wind", "headline"])

    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    if not df.empty and 'cumulative_profit_eur' in df.columns:
        total_profit = df.iloc[-1]['cumulative_profit_eur']
        latest_price = df.iloc[-1]["price"]
        send_telegram_msg(f"⚡ BESS Velín: Aktuální zisk = {total_profit:.2f} EUR | Cena: {latest_price} EUR/MWh")
        
    print(f"✅ Hotovo. Simulace uložena pro {len(df)} hodin.")

if __name__ == "__main__":
    get_market_data()
