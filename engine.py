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
    SQRT_EFF = np.sqrt(efficiency)
    SOC_MIN = capacity_kwh * 0.05
    SOC_MAX = capacity_kwh * 0.95
    
    # 1. Skutečná simulace (Actual execution)
    current_soc = capacity_kwh * 0.5
    prices = df['price'].values
    n_hours = len(prices)
    
    actions = ["IDLE (POHOTOVOST)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    
    for i in range(n_hours):
        p = prices[i]
        future_prices = prices[i:]
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        if len(future_prices) > 0:
            mean_f = np.mean(future_prices)
            min_f = np.min(future_prices)
            max_f = np.max(future_prices)
            
            if p <= min_f * 1.05 and p < (mean_f - degradation_cost_mwh) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_power_kw, headroom / SQRT_EFF)
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    en_mwh = power / 1000.0
                    cash_flow[i] = - (en_mwh * p) - (en_mwh * degradation_cost_mwh * 0.5)
                    
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

    # 2. Ranní plán / Predikce (Forecast sim s lehkou odchylkou pro backtesting)
    np.random.seed(42)
    forecast_prices = prices * np.random.normal(1.0, 0.05, n_hours)
    fc_soc = capacity_kwh * 0.5
    fc_actions = []
    fc_power = []
    
    for i in range(n_hours):
        p = forecast_prices[i]
        act = "IDLE (POHOTOVOST)"
        pw = 0.0
        if p < np.mean(forecast_prices) * 0.95 and fc_soc < SOC_MAX:
            act = "NABÍJENÍ (CHARGE)"
            pw = min(max_power_kw, (SOC_MAX - fc_soc) / SQRT_EFF)
            fc_soc += pw * SQRT_EFF
        elif p > np.mean(forecast_prices) * 1.05 and fc_soc > SOC_MIN:
            act = "VYBÍJENÍ (DISCHARGE)"
            pw = -min(max_power_kw, (fc_soc - SOC_MIN) * SQRT_EFF)
            fc_soc -= abs(pw) / SQRT_EFF
        fc_actions.append(act)
        fc_power.append(pw)

    df['forecast_price'] = forecast_prices
    df['forecast_action'] = fc_actions
    df['forecast_power_kw'] = fc_power
    
    # Konfidenční koridor cen (pásmová predikce ±12%)
    df['price_upper'] = df['price'] * 1.12
    df['price_lower'] = df['price'] * 0.88
    
    return df

def get_market_data():
    print("Stahuji data a spouštím pokročilý MPC s pásmovou predikcí...")
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
        df = simulate_bess_mpc_advanced(df)
        
        df["wind"] = 15.0  
        df["solar"] = 0.0
        df["headline"] = f"BESS EMS optimalizuje den {target_date} s pásmovou predikcí."
        
    except Exception as e:
        print(f"Chyba: {e}")
        now_prague = datetime.now(prague_tz)
        df = pd.DataFrame([[now_prague.strftime("%H:%M"), 100.0, 112.0, 88.0, "IDLE", 0.0, 500.0, 0.0, 0.0, 100.0, "IDLE", 0.0, 15, "Záložní"]], 
                          columns=["time", "price", "price_upper", "price_lower", "bess_action", "bess_power_kw", "battery_soc_kwh", "hourly_cash_eur", "cumulative_profit_eur", "forecast_price", "forecast_action", "forecast_power_kw", "wind", "headline"])

    file_path = "market_history.csv"
    df.to_csv(file_path, index=False)
    
    if not df.empty and 'cumulative_profit_eur' in df.columns:
        total_profit = df.iloc[-1]['cumulative_profit_eur']
        send_telegram_msg(f"⚡ BESS Velín ({target_date}): Zisk = {total_profit:.2f} EUR")
        
    print(f"Hotovo pro {target_date}.")

if __name__ == "__main__":
    get_market_data()
