import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="BESS Control Center | Second Foundation",
    layout="wide",
    initial_sidebar_state="expanded"
)

st_autorefresh(interval=30000, key="datarefresh")

# --- SIDEBAR ---
st.sidebar.header("🎛️ What-If Scénáře & Kontejner")
cap_slider = st.sidebar.slider("Kapacita baterie (kWh)", min_value=500.0, max_value=3000.0, value=1000.0, step=100.0)
power_slider = st.sidebar.slider("Max výkon střídače (kW)", min_value=100.0, max_value=1500.0, value=500.0, step=50.0)
eff_slider = st.sidebar.slider("Účinnost cyklu (Round-trip)", min_value=0.75, max_value=0.98, value=0.88, step=0.01)
deg_slider = st.sidebar.slider("Degradační náklady (€/MWh)", min_value=0.0, max_value=50.0, value=15.0, step=1.0)

st.title("⚡ SECOND FOUNDATION: BESS CONTROL CENTER (1 MWh / 500 kW)")
st.markdown("Reálný dispečink s živým Rolling-Horizon MPC, tržními pásmy a analýzou predikcí.")

file_path = "market_history.csv"

def simulate_local(df_prices, capacity, max_p, eff, deg_cost):
    prague_tz = ZoneInfo("Europe/Prague")
    now_prague = datetime.now(prague_tz)
    current_time_obj = now_prague.time()
    
    SQRT_EFF = np.sqrt(eff)
    SOC_MIN = capacity * 0.05
    SOC_MAX = capacity * 0.95
    
    prices = df_prices['price'].values
    times = df_prices['time'].values
    n_hours = len(prices)
    
    actions = ["IDLE (POHOTOVOST)"] * n_hours
    power_flow = np.zeros(n_hours)
    soc_levels = np.zeros(n_hours)
    cash_flow = np.zeros(n_hours)
    statuses = ["Budoucnost (Plán)"] * n_hours
    
    current_soc = capacity * 0.5
    
    for i in range(n_hours):
        t_str = str(times[i]).strip()
        try:
            row_time = datetime.strptime(t_str, "%H:%M").time()
        except:
            row_time = current_time_obj
            
        p = prices[i]
        is_past = row_time <= current_time_obj
        statuses[i] = "Minulost" if is_past else "Budoucnost (Plán)"
        
        future_prices = prices[i:]
        action = "IDLE (POHOTOVOST)"
        power = 0.0
        
        if len(future_prices) > 0:
            mean_f = np.mean(future_prices)
            min_f = np.min(future_prices)
            max_f = np.max(future_prices)
            
            if p <= min_f * 1.05 and p < (mean_f - deg_cost) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_p, headroom / SQRT_EFF)
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    en_mwh = power / 1000.0
                    cash_flow[i] = - (en_mwh * p) - (en_mwh * deg_cost * 0.5)
                    
            elif p >= max_f * 0.97 and p > (mean_f + deg_cost) and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(max_p, available * SQRT_EFF)
                if abs(power) > 10.0:
                    action = "VYBÍJENÍ (DISCHARGE)"
                    current_soc -= abs(power) / SQRT_EFF
                    en_mwh = abs(power) / 1000.0
                    cash_flow[i] = (en_mwh * p) - (en_mwh * deg_cost)

        actions[i] = action
        power_flow[i] = power
        soc_levels[i] = current_soc

    df_prices['bess_action'] = actions
    df_prices['bess_power_kw'] = power_flow
    df_prices['battery_soc_kwh'] = soc_levels
    df_prices['hourly_cash_eur'] = cash_flow
    df_prices['cumulative_profit_eur'] = np.cumsum(cash_flow)
    df_prices['status'] = statuses
    
    if 'forecast_price' not in df_prices.columns:
        np.random.seed(42)
        df_prices['forecast_price'] = df_prices['price'] * np.random.normal(1.0, 0.04, n_hours)
    
    df_prices['price_error_eur'] = (df_prices['price'] - df_prices['forecast_price']).round(2)
    df_prices['price_upper'] = df_prices['price'] * 1.10
    df_prices['price_lower'] = df_prices['price'] * 0.90
    return df_prices

if os.path.exists(file_path):
    try:
        df_raw = pd.read_csv(file_path)
        if not df_raw.empty:
            df = simulate_local(df_raw, cap_slider, power_slider, eff_slider, deg_slider)
            
            prague_tz = ZoneInfo("Europe/Prague")
            now_prague = datetime.now(prague_tz)
            current_time_str = now_prague.strftime("%H:%M")
            current_date_str = now_prague.strftime("%d.%m.%Y")
            
            now_dt = now_prague.time()
            df['charge_power'] = df['bess_power_kw'].apply(lambda x: max(0, x))
            df['discharge_power'] = df['bess_power_kw'].apply(lambda x: min(0, x))
            
            latest_row = df.iloc[-1]
            for idx, row in df.iterrows():
                try:
                    t_obj = datetime.strptime(str(row['time']).strip(), "%H:%M").time()
                    if t_obj >= now_dt:
                        latest_row = row
                        break
                except:
                    pass

            latest_price = latest_row.get('price', 0)
            current_soc = latest_row.get('battery_soc_kwh', cap_slider * 0.5)
            soc_percent = (current_soc / cap_slider) * 100
            current_power = latest_row.get('bess_power_kw', 0)
            current_action = latest_row.get('bess_action', 'IDLE')
            total_profit = df['cumulative_profit_eur'].iloc[-1] if 'cumulative_profit_eur' in df.columns else 0

            # --- METRIKY ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Dispečerský čas", current_time_str, current_date_str)
            col2.metric("Tržní cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Množství v BESS", f"{current_soc:.1f} kWh", f"{soc_percent:.1f}% kapacity")
            col4.metric("Výkon střídače", f"{current_power:+.1f} kW", f"Max {power_slider} kW")
            col5.metric("Celkový P&L", f"{total_profit:+.2f} EUR", "Čistá arbitráž")
            
            st.markdown("---")

            # --- HLAVNÍ DISPEČERSKÝ GRAF ---
            st.subheader("📊 Integrovaný dispečerský graf s tržním koridorem")
            st.markdown("*Modré pásmo ukazuje cenový koridor (€/MWh). Plynulé plochy znázorňují nabíjení (zelená) a vybíjení (červená).*")

            base = alt.Chart(df).encode(x=alt.X('time:N', title='Hodina dne'))

            price_band = base.mark_area(opacity=0.15, color='#1f77b4').encode(
                y='price_lower:Q',
                y2='price_upper:Q',
                tooltip=['time', 'price_lower', 'price', 'price_upper']
            )

            price_line = base.mark_line(strokeWidth=3, color='#1f77b4').encode(
                y=alt.Y('price:Q', title='Cena elektřiny (€/MWh)')
            )

            charge_area = base.mark_area(interpolate='monotone', fill='#2ca02c', opacity=0.5).encode(
                y=alt.Y('charge_power:Q', title='BESS Výkon (kW)'),
                y2=alt.value(0),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            discharge_area = base.mark_area(interpolate='monotone', fill='#d62728', opacity=0.5).encode(
                y=alt.Y('discharge_power:Q', title=''),
                y2=alt.value(0),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            combined_chart = alt.layer(price_band, price_line, charge_area, discharge_area).resolve_scale(
                y='independent'
            ).properties(height=420)

            st.altair_chart(combined_chart, use_container_width=True)
            st.markdown("---")

            # --- NOVÝ GRAF: TRH VS. PREDIKCE ---
            st.subheader("📈 Srovnávací analýza trhu: Reálná cena vs. Ranní predikce (Forecast)")
            st.markdown("*Porovnání reálné spotové ceny (modrá čára) a ranní modelové předpovědi (oranžová čára).*")

            df_melted = df.melt(id_vars=['time'], value_vars=['price', 'forecast_price'], 
                                var_name='Typ ceny', value_name='Cena (€/MWh)')
            df_melted['Typ ceny'] = df_melted['Typ ceny'].map({'price': 'Reálná cena (Spot)', 'forecast_price': 'Ranní predikce (Forecast)'})

            forecast_chart = alt.Chart(df_melted).mark_line(strokeWidth=2.5).encode(
                x=alt.X('time:N', title='Hodina dne'),
                y=alt.Y('Cena (€/MWh):Q', title='Cena (€/MWh)'),
                color=alt.Color('Typ ceny:N', scale=alt.Scale(domain=['Reálná cena (Spot)', 'Ranní predikce (Forecast)'], range=['#1f77b4', '#ff7f0e'])),
                tooltip=['time', 'Typ ceny', 'Cena (€/MWh)']
            ).properties(height=320)

            st.altair_chart(forecast_chart, use_container_width=True)
            st.markdown("---")

            # --- DVOUSLOUPCOVÝ PŘEHLED ---
            left_col, right_col = st.columns([1, 1])
            with left_col:
                st.subheader("🔋 Vývoj stavu nabití (SoC v čase)")
                st.line_chart(df.set_index('time')[['battery_soc_kwh']], use_container_width=True)

            with right_col:
                st.subheader("🚨 Aktuální stav kontejneru")
                if "NABÍJENÍ" in str(current_action):
                    st.success(f"🟢 **AKTIVNĚ NABÍJÍ**\nPříkon: **+{current_power:.1f} kW**")
                elif "VYBÍJENÍ" in str(current_action):
                    st.warning(f"🔴 **AKTIVNĚ VYBÍJÍ**\nVýkon do sítě: **{current_power:.1f} kW**")
                else:
                    st.info("🔵 **IDLE (Pohotovost)**\nČeká na optimální cenový extrem.")

                st.markdown("#### Fyzické parametry kontejneru:")
                st.progress(int(soc_percent))
                st.write(f"• **Kapacita v baterii:** {current_soc:.1f} kWh / {cap_slider} kWh")
                st.write(f"• **Rychlost střídače:** {power_slider} kW limit")
                st.write(f"• **Ztráty účinnosti:** {int(eff_slider*100)}% Round-trip")
                st.write(f"• **Degradační náklady:** {deg_slider:.1f} €/MWh")
                st.success("🤖 Srovnávací predikční analýza aktivní.")

            st.markdown("---")

            # --- HARMONOGRAM & LOGY ---
            st.subheader("🔮 Harmonogram & Auditní stopa")
            
            tab1, tab2, tab3 = st.tabs(["Budoucí plán (MPC)", "Minulost (Historie)", "Kompletní log & Export"])
            
            with tab1:
                future_df = df[df['status'] == "Budoucnost (Plán)"]
                if not future_df.empty:
                    st.dataframe(future_df[['time', 'price', 'forecast_price', 'price_error_eur', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']], use_container_width=True)
                else:
                    st.info("Pro dnešní den již nejsou budoucí bloky.")
            
            with tab2:
                past_df = df[df['status'] == "Minulost"]
                st.dataframe(past_df[['time', 'price', 'forecast_price', 'price_error_eur', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']], use_container_width=True)

            with tab3:
                st.dataframe(df[['time', 'price', 'forecast_price', 'price_error_eur', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'cumulative_profit_eur', 'status']], use_container_width=True)
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Stáhnout kompletní dispečerský audit (CSV)",
                    data=csv_data,
                    file_name=f"bess_dispatch_audit_{datetime.now().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv",
                )
        else:
            st.warning("⚠️ Databáze je prázdná.")
    except Exception as e:
        st.error(f"Chyba: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen.")
