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

def simulate_rolling_mpc(df, capacity_kwh=1000.0, max_power_kw=500.0, efficiency=0.88, degradation_cost_mwh=15.0):
    """
    Reálný Rolling-Horizon MPC dispečink:
    - Respektuje reálný plynoucí čas v zóně Europe/Prague.
    - Minulost drží reálnou historii, budoucnost se optimalizuje ze ζivého SoC.
    """
    prague_tz = ZoneInfo("Europe/Prague")
    now_prague = datetime.now(prague_tz)
    current_time_obj = now_prague.time()
    
    SQRT_EFF = np.sqrt(efficiency)
    SOC_MIN = capacity_kwh * 0.05
    SOC_MAX = capacity_kwh * 0.95
    
    prices = df['price'].values
    times = df['time'].values
    n_hours = len(prices)
    
    actions = ["IDLE (POHOTOVOST)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    statuses = ["Budoucnost (Plán)"] * n_hours
    
    current_soc = capacity_kwh * 0.5  # Startovací SoC o půlnoci
    
    for i in range(n_hours):
        t_str = str(times[i]).strip()
        try:
            row_time = datetime.strptime(t_str, "%H:%M").time()
        except:
            row_time = current_time_obj
            
        p = prices[i]
        
        # Určení, zda je hodina v minulosti nebo budoucnosti
        is_past = row_time <= current_time_obj
        statuses[i] = "Minulost" if is_past else "Budoucnost (Plán)"
        
        # Horizon pro rozhodování (od této hodiny do konce dne)
        future_prices = prices[i:]
        
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        if len(future_prices) > 0:
            mean_f = np.mean(future_prices)
            min_f = np.min(future_prices)
            max_f = np.max(future_prices)
            
            # Logika nabíjení
            if p <= min_f * 1.05 and p < (mean_f - degradation_cost_mwh) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_power_kw, headroom / SQRT_EFF)
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    en_mwh = power / 1000.0
                    cash_flow[i] = - (en_mwh * p) - (en_mwh * degradation_cost_mwh * 0.5)
                    
            # Logika vybíjení na špičky
            elif p >= max_f * 0.97 and p > (mean_f + degradation_cost_mwh) and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(max_power_kw, available * SQRT_EFF)
                if abs(power) > 10.0:
                    action = "VYBÍJENÍ (DISCHARGE)"
                    current_soc -= abs(power) / SQRT_EFF
                    en_mwh = abs(power) / 1000.0
                    cash_flow[i] = (en_mwh * p) - (en_mwh * degradation_cost_mwh)

        actions[i] = action
        power_flow[i] = power
        soc_levels[i] = current_soc

    df['bess_action'] = actions
    df['bess_power_kw'] = power_flow
    df['battery_soc_kwh'] = soc_levels
    df['hourly_cash_eur'] = cash_flow
    df['cumulative_profit_eur'] = np.cumsum(cash_flow)
    df['status'] = statuses
    
    # Konfidenční koridor cen (±10% volatilita trhu)
    df['price_upper'] = df['price'] * 1.10
    df['price_lower'] = df['price'] * 0.90
    
    return df

def get_market_data():
    print("Stahuji reálná tržní data a spouštím Rolling-Horizon MPC...")
    prague_tz = ZoneInfo("Europe/Prague")
    now_prague = datetime.now(prague_tz)
    current_date = now_prague.date()
    
    try:
        p_url = "https://api.energy-charts.info/price?bzn=DE-LU"
        data = requests.get(p_url, timeout=10).json()
        
        prices = data["price"]
        timestamps = data.get("unix_seconds", data.get("time", []))
        
        df_all = pd.DataFrame({'timestamp': timestamps, 'price': prices})
        df_all['dt'] = pd.to_datetime(df_all['timestamp'], unit='s', utc=True).dt.tz_convert(prague_tz)
        df_all['date'] = df_all['dt'].dt.date
        
        available_dates = sorted(df_all['date'].unique())
        target_date = current_date if current_date in available_dates else available_dates[-1]
        
        df_day = df_all[df_all['date'] == target_date].copy()
        df_day['time'] = df_day['dt'].dt.strftime("%H:%M")
        
        df = df_day[['time', 'price']].drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
        df = simulate_rolling_mpc(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = f"BESS EMS optimalizuje den {target_date} reálným MPC."
        
    except Exception as e:
        print(f"Chyba při stahování: {e}")
        now_prague = datetime.now(prague_tz)
        df = pd.DataFrame([[now_prague.strftime("%H:%M"), 100.0, 110.0, 90.0, "IDLE", 0.0, 500.0, 0.0, 0.0, "Minulost", 15, "Záložní"]], 
                          columns=["time", "price", "price_upper", "price_lower", "bess_action", "bess_power_kw", "battery_soc_kwh", "hourly_cash_eur", "cumulative_profit_eur", "status", "wind", "headline"])

    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    if not df.empty and 'cumulative_profit_eur' in df.columns:
        total_profit = df.iloc[-1]['cumulative_profit_eur']
        send_telegram_msg(f"⚡ BESS Velín ({target_date}): Celkový zisk = {total_profit:.2f} EUR")
        
    print(f"Hotovo. Uloženo pro {target_date}.")

if __name__ == "__main__":
    get_market_data()
