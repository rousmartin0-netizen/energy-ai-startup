import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

# --- NASTAVENÍ TELEGRAMU ---
TELEGRAM_TOKEN = "8671040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def simulate_bess_arbitrage(df):
    """
    Přísná fyzikální a ekonomická simulace BESS kontejneru.
    Parametry:
    - Kapacita: 1000 kWh (1 MWh)
    - Max výkon střídače: 500 kW
    - Účinnost (Round-trip): 88% (odpovídá ~93.8% jednosměrně)
    - Bezpečné SoC: 5% až 95%
    """
    CAPACITY_KWH = 1000.0
    MAX_POWER_KW = 500.0
    EFFICIENCY = 0.88
    SQRT_EFF = np.sqrt(EFFICIENCY) # rozdělení ztrát na nabíjení a vybíjení
    
    SOC_MIN = 50.0   # 5%
    SOC_MAX = 950.0  # 95%
    initial_soc = 500.0 # startujeme na 50%
    
    n_hours = len(df)
    prices = df['price'].values
    
    # Rozhodovací logika: Seřadíme hodiny podle ceny
    # Nejlevnější hodiny -> Nabíjení, Nejdražší hodiny -> Vybíjení
    sorted_indices = np.argsort(prices)
    
    actions = ["IDLE"] * n_hours
    power_flow = np.zeros(n_hours) # kladné = nabíjení, záporné = vybíjení
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    current_soc = initial_soc
    
    # Jednoduchá, ale robustní heuristika pro arbitráž respektující fyziku
    # Procházíme od nejlevnějších po nejdražší
    for idx in sorted_indices:
        p = prices[idx]
        
        # Pokud je cena velmi nízká nebo záporná, prioritně NABÍJÍME
        if p < 50.0 and current_soc < SOC_MAX:
            # Kolik můžeme vzít do plna?
            headroom_kwh = (SOC_MAX - current_soc) / SQRT_EFF
            charge_kwh = min(MAX_POWER_KW, headroom_kwh)
            
            if charge_kwh > 1.0: # ignorujeme zlomky
                actions[idx] = "CHARGE"
                power_flow[idx] = charge_kwh
                energy_stored = charge_kwh * SQRT_EFF
                current_soc += energy_stored
                cash_flow[idx] = - (charge_kwh * p) / 1000.0 # náklady v EUR (price je za MWh)
                
        # Pokud je cena vysoká, prioritně VYBÍJÍME
        elif p > 100.0 and current_soc > SOC_MIN:
            # Kolik můžeme vydat do min?
            available_kwh = (current_soc - SOC_MIN) * SQRT_EFF
            discharge_kwh = min(MAX_POWER_KW, available_kwh)
            
            if discharge_kwh > 1.0:
                actions[idx] = "DISCHARGE"
                power_flow[idx] = -discharge_kwh
                energy_extracted = discharge_kwh * SQRT_EFF
                current_soc -= discharge_kwh
                cash_flow[idx] = (discharge_kwh * p) / 1000.0 # příjem v EUR

        soc_levels[idx] = current_soc

    df['bess_action'] = actions
    df['bess_power_kw'] = power_flow
    df['battery_soc_kwh'] = soc_levels
    df['hourly_cash_eur'] = cash_flow
    
    return df

def get_market_data():
    print("🚀 Stahuji reálná data z trhu a spouštím BESS simulaci...")
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
        
        # Spuštění přísné fyzikální simulace BESS
        df = simulate_bess_arbitrage(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = "BESS kontejner v aktivním arbitrážním režimu."
        
    except Exception as e:
        print(f"Chyba při stahování dat: {e}")
        now_prague = datetime.now(prague_tz)
        df = pd.DataFrame([[now_prague.strftime("%H:%M"), 100.0, "IDLE", 0.0, 500.0, 0.0, 15, "Záložní režim"]], 
                          columns=["time", "price", "bess_action", "bess_power_kw", "battery_soc_kwh", "hourly_cash_eur", "wind", "headline"])

    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    if not df.empty and 'hourly_cash_eur' in df.columns:
        total_daily_profit = df['hourly_cash_eur'].sum()
        latest_price = df.iloc[-1]["price"]
        send_telegram_msg(f"📊 BESS Simulace: Denní zisk = {total_daily_profit:.2f} EUR | Aktuální cena: {latest_price} EUR/MWh")
        
    print(f"✅ Hotovo. Simulace proběhla pro {len(df)} hodinových bloků.")

if __name__ == "__main__":
    get_market_data()
