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

def simulate_bess_mpc_advanced(df, capacity_kwh=1000.0, max_power_kw=500.0, efficiency=0.88, degradation_cost_mwh=15.0):
    """
    Pokročilá MPC simulace s fyzikálními parametry a degradačními náklady.
    - degradation_cost_mwh: Náklady na opotřebení článků (€ / MWh propustnosti)
    """
    SQRT_EFF = np.sqrt(efficiency)
    
    SOC_MIN = capacity_kwh * 0.05   # 5%
    SOC_MAX = capacity_kwh * 0.95   # 95%
    current_soc = capacity_kwh * 0.5 # Startujeme na 50%
    
    df = df.sort_values('time').reset_index(drop=True)
    prices = df['price'].values
    n_hours = len(prices)
    
    actions = ["IDLE (POHOTOVOST)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    for i in range(n_hours):
        p = prices[i]
        future_horizon_prices = prices[i:]
        
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        if len(future_horizon_prices) > 0:
            mean_future = np.mean(future_horizon_prices)
            min_future = np.min(future_horizon_prices)
            max_future = np.max(future_horizon_prices)
            
            # 1. NABÍJENÍ: Lokální minimum, pod průměrem a zohlednění degradačního limitu
            if p <= min_future * 1.05 and p < (mean_future - degradation_cost_mwh) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_power_kw, headroom / SQRT_EFF)
                
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    # Peněžní tok: nákup energie + započtení degradačního nákladu na MWh
                    energy_mwh = power / 1000.0
                    cash_flow[i] = - (energy_mwh * p) - (energy_mwh * degradation_cost_mwh * 0.5)
                    
            # 2. VYBÍJENÍ: Čekáme na absolutní špičku s ohledem na degradaci
            elif p >= max_future * 0.97 and p > (mean_future + degradation_cost_mwh) and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(max_power_kw, available * SQRT_EFF)
                
                if abs(power) > 10.0:
                    action = "VYBÍJENÍ (DISCHARGE)"
                    energy_taken = abs(power) / SQRT_EFF
                    current_soc -= energy_taken
                    energy_mwh = abs(power) / 1000.0
                    # Peněžní tok: prodej energie minus degradační náklady
                    cash_flow[i] = (energy_mwh * p) - (energy_mwh * degradation_cost_mwh)

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
    print("Stahuji reálná data a spouštím pokročilou MPC simulaci...")
    prague_tz = ZoneInfo("Europe/Prague")
    now_prague = datetime.now(prague_tz)
    current_date = now_prague.date()
    
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        data = requests.get(p_url, timeout=10).json()
        
        prices = data["price"]
        timestamps = data.get("unix_seconds", data.get("time", []))
        
        df_all = pd.DataFrame({
            'timestamp': timestamps,
            'price': prices
        })
        df_all['dt'] = pd.to_datetime(df_all['timestamp'], unit='s', utc=True).dt.tz_convert(prague_tz)
        df_all['date'] = df_all['dt'].dt.date
        
        available_dates = sorted(df_all['date'].unique())
        target_date = current_date if current_date in available_dates else available_dates[-1]
        
        df_day = df_all[df_all['date'] == target_date].copy()
        df_day['time'] = df_day['dt'].dt.strftime("%H:%M")
        
        df_list = df_day[['time', 'price']].values.tolist()
        
        df = pd.DataFrame(df_list, columns=["time", "price"])
        df = df.drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
        
        # Spuštění s výchozími parametry
        df = simulate_bess_mpc_advanced(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = f"BESS EMS optimalizuje den {target_date} s degradačním modelováním."
        
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
        send_telegram_msg(f"⚡ BESS Velín ({target_date}): Zisk = {total_profit:.2f} EUR | Cena: {latest_price} EUR/MWh")
        
    print(f"Hotovo. Simulace uložena pro {len(df)} hodin dne {target_date}.")

if __name__ == "__main__":
    get_market_data()
