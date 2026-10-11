import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="BESS Trading Terminal | Second Foundation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st_autorefresh(interval=30000, key="datarefresh")

st.title("⚡ SECOND FOUNDATION: BESS TRADING TERMINAL (1 MWh / 500 kW)")
st.markdown("Fyzikálně verifikovaná simulace velkokapacitního bateriového kontejneru na spotovém trhu (DE-LU / CZE).")

file_path = "market_history.csv"

if os.path.exists(file_path):
    try:
        df = pd.read_csv(file_path)
        if not df.empty:
            prague_tz = ZoneInfo("Europe/Prague")
            now_prague = datetime.now(prague_tz)
            
            current_time_str = now_prague.strftime("%H:%M")
            current_date_str = now_prague.strftime("%d.%m.%Y")
            
            now_dt = now_prague.time()
            def classify_time(t_str):
                try:
                    t_obj = datetime.strptime(str(t_str).strip(), "%H:%M").time()
                    return "Minulost" if t_obj <= now_dt else "Budoucnost (Predikce)"
                except:
                    return "Neznámé"

            df['status'] = df['time'].apply(classify_time)
            
            # Finanční a fyzikální metriky BESS
            latest_price = df.iloc[-1]['price'] if 'price' in df.columns else 0
            total_profit = df['hourly_cash_eur'].sum() if 'hourly_cash_eur' in df.columns else 0
            current_soc = df.iloc[-1]['battery_soc_kwh'] if 'battery_soc_kwh' in df.columns else 500
            soc_percent = (current_soc / 1000.0) * 100

            # --- HORNÍ PANEL METRIK ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Aktuální čas (CZ)", current_time_str, current_date_str)
            col2.metric("Tržní cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Baterie SoC", f"{soc_percent:.1f}%", f"{current_soc:.0f} kWh")
            col4.metric("Celkový denní P&L", f"{total_profit:+.2f} EUR", "Čistý zisk")
            col5.metric("Kapacita kontejneru", "1.0 MWh", "500 kW Invertor")
            
            st.markdown("---")

            # --- HLAVNÍ SEKCE: GRAF A BESS STATUS ---
            left_col, right_col = st.columns([3, 1])

            with left_col:
                st.subheader("📈 Hodinová cenová křivka & Arbitrážní profil")
                st.markdown("Vývoj cen elektřiny na burze pro dnešní den.")
                
                chart_data = df.set_index('time')[['price']]
                st.line_chart(chart_data, use_container_width=True)

            with right_col:
                st.subheader("🔋 Stav BESS Kontejneru")
                latest_action = df.iloc[-1].get('bess_action', 'IDLE')
                
                if latest_action == "CHARGE":
                    st.success("🟢 Aktuální stav: **NABÍJÍ SE**")
                elif latest_action == "DISCHARGE":
                    st.warning("🔴 Aktuální stav: **VYBÍJÍ SE**")
                else:
                    st.info("🔵 Aktuální stav: **IDLE (Pohotovost)**")
                
                st.progress(int(soc_percent))
                st.markdown(f"**Účinnost cyklu:** 88% (Loss-aware)")
                st.markdown(f"**Ochrana článků:** 5% - 95% SoC")
                st.success("🤖 Fyzikální model bez odchylek aktivní.")

            st.markdown("---")

            # --- DETAILNÍ TABULKA ---
            st.subheader("📋 Detailní provozní harmonogram baterie")
            
            tab1, tab2 = st.tabs(["Fyzikální log (Všechny hodiny)", "Filtrovaný pohled"])
            
            with tab1:
                st.dataframe(df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur', 'status']], use_container_width=True, height=300)
            
            with tab2:
                filter_status = st.selectbox("Zobrazit sekci:", ["Vše", "Minulost", "Budoucnost (Predikce)"])
                if filter_status == "Vše":
                    st.dataframe(df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur', 'status']], use_container_width=True)
                else:
                    filtered_df = df[df['status'] == filter_status]
                    st.dataframe(filtered_df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur', 'status']], use_container_width=True)

        else:
            st.warning("⚠️ Databáze je zatím prázdná.")
    except Exception as e:
        st.error(f"Chyba při vykreslování terminálu: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen.")
