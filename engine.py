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

def simulate_bess_mpc(df):
    """
    Model Predictive Control (MPC) simulace pro BESS kontejner.
    - Kapacita: 1000 kWh (1 MWh)
    - Max výkon střídače: 500 kW
    - Účinnost cyklu: 88%
    - Logika: Bot nezná budoucnost absolutně, ale vyhodnocuje predikovaný cenový horizont 
      pro zbývající hodiny dne a podle toho inteligentně časuje nákup a prodej.
    """
    CAPACITY_KWH = 1000.0
    MAX_POWER_KW = 500.0
    EFFICIENCY = 0.88
    SQRT_EFF = np.sqrt(EFFICIENCY)
    
    SOC_MIN = 50.0   # 5%
    SOC_MAX = 950.0  # 95%
    current_soc = 500.0 # Startujeme na 50% kapacity
    
    df = df.sort_values('time').reset_index(drop=True)
    prices = df['price'].values
    n_hours = len(prices)
    
    actions = ["IDLE (POHOTOVOST)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    # Simulace řízení hodinu po hodině (MPC přístup)
    for i in range(n_hours):
        p = prices[i]
        
        # Predikční horizont: pohled na zbývající hodiny dne
        future_horizon_prices = prices[i:]
        
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        if len(future_horizon_prices) > 0:
            mean_future = np.mean(future_horizon_prices)
            min_future = np.min(future_horizon_prices)
            max_future = np.max(future_horizon_prices)
            
            # 1. NABÍJENÍ: Pokud je aktuální cena na lokálním minimu predikce a pod průměrem
            if p <= min_future * 1.08 and p < mean_future and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(MAX_POWER_KW, headroom / SQRT_EFF)
                
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    cash_flow[i] = - (power * p) / 1000.0
                    
            # 2. VYBÍJENÍ: Pokud cena dosahuje vrcholu predikovaného horizontu (např. večerní špička)
            elif p >= max_future * 0.92 and p > mean_future and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(MAX_POWER_KW, available * SQRT_EFF)
                
                if abs(power) > 10.0:
                    action = "VYBÍJENÍ (DISCHARGE)"
                    current_soc -= abs(power) / SQRT_EFF
                    cash_flow[i] = (abs(power) * p) / 1000.0

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
    print("🚀 Stahuji reálná data a spouštím predikční MPC BESS simulaci...")
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
        df = simulate_bess_mpc(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = "BESS EMS běží v predikčním MPC režimu."
        
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
        send_telegram_msg(f"⚡ BESS MPC Velín: Predikovaný zisk = {total_profit:.2f} EUR | Cena: {latest_price} EUR/MWh")
        
    print(f"✅ Hotovo. Predikční simulace uložena pro {len(df)} hodin.")

if __name__ == "__main__":
    get_market_data()
