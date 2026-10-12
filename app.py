import streamlit as st
import pandas as pd
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

# --- SIDEBAR: WHAT-IF SCÉNÁŘE ---
st.sidebar.header("🎛️ What-If Scénáře & Kontejner")
st.sidebar.markdown("Upravte fyzické parametry baterie a sledujte okamžitou reakci EMS algoritmů.")

cap_slider = st.sidebar.slider("Kapacita baterie (kWh)", min_value=500.0, max_value=3000.0, value=1000.0, step=100.0)
power_slider = st.sidebar.slider("Max výkon střídače (kW)", min_value=100.0, max_value=1500.0, value=500.0, step=50.0)
eff_slider = st.sidebar.slider("Účinnost cyklu (Round-trip)", min_value=0.75, max_value=0.98, value=0.88, step=0.01)
deg_slider = st.sidebar.slider("Degradační náklady (€/MWh)", min_value=0.0, max_value=50.0, value=15.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.info("💡 Změna parametrů v panelu okamžitě přepočítá chování baterie i celkový finanční výsledek.")

st.title("⚡ SECOND FOUNDATION: BESS CONTROL CENTER (1 MWh / 500 kW)")
st.markdown("Reálný dispečink bateriového kontejneru s plynulou výkonovou křivkou a interaktivním MPC řízením.")

file_path = "market_history.csv"

# Lokální simulace pro What-If slidery v reálném čase
def simulate_local(df_prices, capacity, max_p, eff, deg_cost):
    SQRT_EFF = np.sqrt(eff)
    SOC_MIN = capacity * 0.05
    SOC_MAX = capacity * 0.95
    current_soc = capacity * 0.5
    
    prices = df_prices['price'].values
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
            
            if p <= min_future * 1.05 and p < (mean_future - deg_cost) and current_soc < SOC_MAX:
                headroom = SOC_MAX - current_soc
                power = min(max_p, headroom / SQRT_EFF)
                if power > 10.0:
                    action = "NABÍJENÍ (CHARGE)"
                    current_soc += power * SQRT_EFF
                    energy_mwh = power / 1000.0
                    cash_flow[i] = - (energy_mwh * p) - (energy_mwh * deg_cost * 0.5)
                    
            elif p >= max_future * 0.97 and p > (mean_future + deg_cost) and current_soc > SOC_MIN:
                available = current_soc - SOC_MIN
                power = -min(max_p, available * SQRT_EFF)
                if abs(power) > 10.0:
                    action = "VYBÍJENÍ (DISCHARGE)"
                    energy_taken = abs(power) / SQRT_EFF
                    current_soc -= energy_taken
                    energy_mwh = abs(power) / 1000.0
                    cash_flow[i] = (energy_mwh * p) - (energy_mwh * deg_cost)

        actions[i] = action
        power_flow[i] = power
        soc_levels[i] = current_soc

    df_prices['bess_action'] = actions
    df_prices['bess_power_kw'] = power_flow
    df_prices['battery_soc_kwh'] = soc_levels
    df_prices['hourly_cash_eur'] = cash_flow
    df_prices['cumulative_profit_eur'] = np.cumsum(cash_flow)
    return df_prices

if os.path.exists(file_path):
    try:
        df_raw = pd.read_csv(file_path)
        if not df_raw.empty:
            # Spustíme simulaci s parametry ze sidebar sliderů
            df = simulate_local(df_raw, cap_slider, power_slider, eff_slider, deg_slider)
            
            prague_tz = ZoneInfo("Europe/Prague")
            now_prague = datetime.now(prague_tz)
            
            current_time_str = now_prague.strftime("%H:%M")
            current_date_str = now_prague.strftime("%d.%m.%Y")
            
            now_dt = now_prague.time()
            def classify_time(t_str):
                try:
                    t_obj = datetime.strptime(str(t_str).strip(), "%H:%M").time()
                    return "Minulost" if t_obj <= now_dt else "Budoucnost (Plán)"
                except:
                    return "Neznámé"

            df['status'] = df['time'].apply(classify_time)
            
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

            # --- HORNÍ PANEL METRIK ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Dispečerský čas", current_time_str, current_date_str)
            col2.metric("Tržní cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Množství energie v BESS", f"{current_soc:.1f} kWh", f"{soc_percent:.1f}% kapacity")
            col4.metric("Výkon střídače", f"{current_power:+.1f} kW", f"Max {power_slider} kW")
            col5.metric("Celkový denní P&L", f"{total_profit:+.2f} EUR", "Čistá arbitráž")
            
            st.markdown("---")

            # --- INTEGROVANÝ DISPEČERSKÝ GRAF ---
            st.subheader("📊 Integrovaný dispečerský graf: Cena elektřiny vs. BESS Výkonová Křivka")
            st.markdown("*Modrá čára znázorňuje vývoj tržní ceny (€/MWh). Plynulá barevná křivka (zelená = nabíjení, červená = vybíjení) ukazuje výkon střídače v čase.*")

            base = alt.Chart(df).encode(x=alt.X('time:N', title='Hodina dne'))

            price_line = base.mark_line(strokeWidth=3, color='#1f77b4').encode(
                y=alt.Y('price:Q', title='Cena elektřiny (€/MWh)')
            )

            charge_area = base.mark_area(interpolate='monotone', fill='#2ca02c', opacity=0.5).encode(
                y=alt.Y('charge_power:Q', title='BESS Výkon (kW) [Nabíjení > 0, Vybíjení < 0]'),
                y2=alt.value(0),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            discharge_area = base.mark_area(interpolate='monotone', fill='#d62728', opacity=0.5).encode(
                y=alt.Y('discharge_power:Q', title=''),
                y2=alt.value(0),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            combined_chart = alt.layer(price_line, charge_area, discharge_area).resolve_scale(
                y='independent'
            ).properties(
                height=420
            )

            st.altair_chart(combined_chart, use_container_width=True)

            st.markdown("---")

            # --- DVOUSLOUPCOVÝ PŘEHLED ---
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.subheader("🔋 Vývoj stavu nabití (SoC v čase)")
                soc_chart_data = df.set_index('time')[['battery_soc_kwh']]
                st.line_chart(soc_chart_data, use_container_width=True)

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
                st.write(f"• **Ztráty účinnosti:** {int(eff_slider*100)}% celkově (Round-trip)")
                st.write(f"• **Degradační náklady:** {deg_slider:.1f} €/MWh")
                st.success("🤖 MPC predikční model s degradačním řízením aktivní.")

            st.markdown("---")

            # --- DISPEČERSKÝ HARMONOGRAM & EXPORT ---
            st.subheader("🔮 Harmonogram, auditní stopa a log")
            
            tab1, tab2, tab3 = st.tabs(["Budoucí plán (Predikce)", "Minulost (Uplynulé hodiny)", "Kompletní log & Export"])
            
            with tab1:
                future_df = df[df['status'] == "Budoucnost (Plán)"]
                if not future_df.empty:
                    st.dataframe(future_df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur']], use_container_width=True)
                else:
                    st.info("Pro dnešní den již nejsou k dispozici budoucí hodinové bloky.")
            
            with tab2:
                past_df = df[df['status'] == "Minulost"]
                st.dataframe(past_df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur']], use_container_width=True)

            with tab3:
                st.dataframe(df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur', 'cumulative_profit_eur', 'status']], use_container_width=True)
                
                # Tlačítko pro export auditního CSV pro investory/financial audit
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
        st.error(f"Chyba při vykreslování terminálu: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen.")
