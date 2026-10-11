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

def simulate_bess_chronological(df):
    """
    Přísná časová (chronologická) fyzikální simulace BESS kontejneru.
    - Kapacita: 1000 kWh (1 MWh)
    - Max výkon střídače: 500 kW (max 500 kWh za 1 hodinový blok)
    - Účinnost cyklu (Round-trip): 88%
    - Bezpečné okno SoC: 5% (50 kWh) až 95% (950 kWh)
    """
    CAPACITY_KWH = 1000.0
    MAX_POWER_KW = 500.0
    EFFICIENCY = 0.88
    SQRT_EFF = np.sqrt(EFFICIENCY)
    
    SOC_MIN = 50.0   # 5%
    SOC_MAX = 950.0  # 95%
    current_soc = 500.0 # startujeme den s 50% kapacity
    
    # Seřadíme data striktně chronologicky podle času (00:00 -> 23:00)
    df = df.sort_values('time').reset_index(drop=True)
    prices = df['price'].values
    n_hours = len(prices)
    
    # Předvýpočet: Určíme si nejlevnější a nejdražší hodiny dne pro arbitráž
    price_sorted_indices = np.argsort(prices)
    n_target = min(6, n_hours // 3) if n_hours >= 6 else 2
    cheapest_indices = set(price_sorted_indices[:n_target])
    expensive_indices = set(price_sorted_indices[-n_target:])
    
    actions = ["IDLE"] * n_hours
    power_flow = np.zeros(n_hours) # + nabíjení (kW), - vybíjení (kW)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    # Průchod časem hodinu po hodině (reálná fyzikální evoluce stavu)
    for i in range(n_hours):
        p = prices[i]
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        # 1. Kritérium pro NABÍJENÍ (Nízká cena nebo záporná cena, a máme místo v baterii)
        if (i in cheapest_indices or p < 45.0) and current_soc < SOC_MAX:
            headroom_energy = SOC_MAX - current_soc
            max_grid_power = headroom_energy / SQRT_EFF
            power = min(MAX_POWER_KW, max_grid_power) # Respektuje rychlost střídače (max 500 kW)
            
            if power > 10.0:
                action = "NABÍJENÍ (CHARGE)"
                energy_into_battery = power * SQRT_EFF
                current_soc += energy_into_battery
                cash_flow[i] = - (power * p) / 1000.0 # Náklady v EUR
        
        # 2. Kritérium pro VYBÍJENÍ (Vysoká cena ve špičce, a máme energii v baterii)
        elif (i in expensive_indices or p > 95.0) and current_soc > SOC_MIN:
            available_energy = current_soc - SOC_MIN
            max_discharge_power = available_energy * SQRT_EFF
            power = -min(MAX_POWER_KW, max_discharge_power) # Respektuje rychlost vybíjení
            
            if abs(power) > 10.0:
                action = "VYBÍJENÍ (DISCHARGE)"
                energy_taken = abs(power) / SQRT_EFF
                current_soc -= energy_taken
                cash_flow[i] = (abs(power) * p) / 1000.0 # Výnos v EUR

        actions[i] = action
        power_flow[i] = power
        soc_levels[i] = current_soc

    df['bess_action'] = actions
    df['bess_power_kw'] = power_flow
    df['battery_soc_kwh'] = soc_levels
    df['hourly_cash_eur'] = cash_flow
    df['cumulative_profit_eur'] = np.cumsum(cash_flow)
    
    return df

def get_market_data():
    print("🚀 Stahuji reálná data a spouštím chronologickou BESS simulaci...")
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
        df = simulate_bess_chronological(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = "BESS kontejner v chronologickém arbitrážním režimu."
        
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
        send_telegram_msg(f"⚡ BESS Velín: Denní zisk = {total_profit:.2f} EUR | Cena: {latest_price} EUR/MWh")
        
    print(f"✅ Hotovo. Simulace uložena pro {len(df)} hodin.")

if __name__ == "__main__":
    get_market_data()
