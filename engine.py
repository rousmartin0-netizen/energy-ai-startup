import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
import os

TELEGRAM_TOKEN = "8671040720:AAF9Lmr2wx0gfs_2DA-xQuTxznIJ7qKBt18"
TELEGRAM_CHAT_ID = "6143507725"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def simulate_rolling_mpc(df, capacity_kwh=1000.0, max_power_kw=500.0, efficiency=0.88, degradation_cost_mwh=15.0):
    prague_tz = ZoneInfo("Europe/Prague")
    now_prague = datetime.now(prague_tz)
    current_time_obj = now_prague.time()
    
    SQRT_EFF = np.sqrt(efficiency)
    SOC_MIN = capacity_kwh * 0.05
    SOC_MAX = capacity_kwh * 0.95
    
    prices = df['price'].values
    times = df['time'].values
    n_hours = len(prices)
    
    actions = ["IDLE (Pohotovost)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    statuses = ["Budoucnost"] * n_hours
    
    current_soc = capacity_kwh * 0.5
    
    for i in range(n_hours):
        t_str = str(times[i]).strip()
        try:
            row_time = datetime.strptime(t_str, "%H:%M").time()
        except:
            row_time = current_time_obj
            
        p = prices[i]
        is_past = row_time <= current_time_obj
        statuses[i] = "Minulost" if is_past else "Budoucnost"
        
        future_prices = prices[i:]
        action = "IDLE (Pohotovost)"
        power = 0.0
        
        if len(future_prices) > 0:
            mean_f = np.mean(future_prices)
            min_f = np.min(future_prices)
            max_f = np.max(future_prices)
            
            if p <= min_f * 1.05 and p < (mean_f - degradation_cost_mwh) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_power_kw, headroom / SQRT_EFF)
                if power > 10.0:
                    action = "Nabíjení"
                    current_soc += power * SQRT_EFF
                    en_mwh = power / 1000.0
                    cash_flow[i] = - (en_mwh * p) - (en_mwh * degradation_cost_mwh * 0.5)
                    
            elif p >= max_f * 0.97 and p > (mean_f + degradation_cost_mwh) and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(max_power_kw, available * SQRT_EFF)
                if abs(power) > 10.0:
                    action = "Vybíjení"
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
    
    np.random.seed(42)
    forecast_prices = prices * np.random.normal(1.0, 0.04, n_hours)
    df['forecast_price'] = forecast_prices
    df['price_error_eur'] = (df['price'] - df['forecast_price']).round(2)
    
    df['price_upper'] = df['price'] * 1.10
    df['price_lower'] = df['price'] * 0.90
    
    return df

def update_historical_ledger(target_date_str, daily_profit):
    ledger_path = "historical_ledger.csv"
    if os.path.exists(ledger_path):
        ledger_df = pd.read_csv(ledger_path)
    else:
        ledger_df = pd.DataFrame(columns=["date", "daily_profit_eur", "cumulative_all_time_eur"])
    
    # Pokud už záznam pro daný den existuje, aktualizujeme ho, jinak přidáme nový
    if target_date_str in ledger_df['date'].values:
        ledger_df.loc[ledger_df['date'] == target_date_str, 'daily_profit_eur'] = round(daily_profit, 2)
    else:
        new_row = pd.DataFrame({"date": [target_date_str], "daily_profit_eur": [round(daily_profit, 2)], "cumulative_all_time_eur": [0.0]})
        ledger_df = pd.concat([ledger_df, new_row], ignore_index=True)
    
    # Seřadit podle data a přepočítat celkový kumulativní zisk napříč historií
    ledger_df = ledger_df.sort_values("date").reset_index(drop=True)
    ledger_df['cumulative_all_time_eur'] = ledger_df['daily_profit_eur'].cumsum().round(2)
    ledger_df.to_csv(ledger_path, index=False)

def get_market_data():
    print("Stahuji data pro EnergyAi...")
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
        df["headline"] = f"EnergyAi optimalizuje den {target_date}."
        
        # Uložení do denního souboru
        file_path = "market_history.csv"
        df.to_csv(file_path, index=False)
        
        # Zápis do historické knihy (ledgeru)
        if not df.empty and 'cumulative_profit_eur' in df.columns:
            total_profit = df.iloc[-1]['cumulative_profit_eur']
            update_historical_ledger(str(target_date), total_profit)
            send_telegram_msg(f"⚡ EnergyAi Velín ({target_date}): Denní zisk = {total_profit:.2f} EUR")
            
    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    get_market_data()
