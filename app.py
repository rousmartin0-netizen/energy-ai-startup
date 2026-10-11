import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

# --- KONFIGURACE STRÁNEK ---
st.set_page_config(
    page_title="CZ Energy Trading Terminal | Second Foundation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Automatický refresh dat každých 30 sekund
st_autorefresh(interval=30000, key="datarefresh")

# --- HLAVIČKA TERMINÁLU ---
st.title("🇨🇿 Second Foundation: ENERGY TRADING TERMINAL")
st.markdown("Profesionální přehled reálného trhu s elektřinou pro českou zónu (DE-LU / CZE) s hodinovou křivkou a predikcí.")

file_path = "market_history.csv"

if os.path.exists(file_path):
    try:
        df = pd.read_csv(file_path)
        if not df.empty:
            prague_tz = ZoneInfo("Europe/Prague")
            now_prague = datetime.now(prague_tz)
            
            current_time_str = now_prague.strftime("%H:%M")
            current_date_str = now_prague.strftime("%d.%m.%Y")
            
            # Klasifikace dat na minulost a budoucnost podle českého času
            now_dt = now_prague.time()
            
            def classify_time(t_str):
                try:
                    t_obj = datetime.strptime(str(t_str).strip(), "%H:%M").time()
                    return "Minulost" if t_obj <= now_dt else "Budoucnost (Predikce)"
                except:
                    return "Neznámé"

            df['status'] = df['time'].apply(classify_time)
            
            # Výpočet klíčových tržních metrik dne
            latest_price = df.iloc[-1]['price'] if 'price' in df.columns else 0
            max_price = df['price'].max() if 'price' in df.columns else 0
            min_price = df['price'].min() if 'price' in df.columns else 0
            avg_price = df['price'].mean() if 'price' in df.columns else 0

            # --- HORNÍ PANEL METRIK ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Aktuální čas (CZ)", current_time_str, current_date_str)
            col2.metric("Aktuální cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Denní maximum", f"{max_price:.2f} €/MWh")
            col4.metric("Denní minimum", f"{min_price:.2f} €/MWh")
            col5.metric("Průměrná cena", f"{avg_price:.2f} €/MWh")
            
            st.markdown("---")

            # --- HLAVNÍ SEKCE: GRAF A TELEMETRIE ---
            left_col, right_col = st.columns([3, 1])

            with left_col:
                st.subheader("📈 Hodinová cenová křivka dne")
                st.markdown("Kompletní trajektorie reálných a predikovaných cen elektřiny na burze (v českém čase).")
                
                # Vykreslení hlavního grafu
                chart_data = df.set_index('time')[['price']]
                st.line_chart(chart_data, use_container_width=True)

            with right_col:
                st.subheader("📰 Tržní přehled")
                latest_headline = df.iloc[-1].get('headline', 'Stabilní situace na trhu.') if 'headline' in df.columns else 'Sleduji trh...'
                wind_speed = df.iloc[-1].get('wind', 0) if 'wind' in df.columns else 0
                
                st.info(f"**Hlavní zpráva:**\n\n{latest_headline}")
                st.metric("Vítr (Praha)", f"{wind_speed} km/h")
                st.success("🤖 Systém běží automatizovaně.")

            st.markdown("---")

            # --- DETAILNÍ TABULKOVÝ HARMONOGRAM ---
            st.subheader("📋 Detailní hodinový harmonogram")
            
            tab1, tab2 = st.tabs(["Všechny hodinové bloky", "Filtrovaný pohled"])
            
            with tab1:
                st.dataframe(df[['time', 'price', 'wind', 'status', 'headline']], use_container_width=True, height=300)
            
            with tab2:
                filter_status = st.selectbox("Zobrazit sekci:", ["Vše", "Minulost", "Budoucnost (Predikce)"])
                if filter_status == "Vše":
                    st.dataframe(df[['time', 'price', 'wind', 'status', 'headline']], use_container_width=True)
                else:
                    filtered_df = df[df['status'] == filter_status]
                    st.dataframe(filtered_df[['time', 'price', 'wind', 'status', 'headline']], use_container_width=True)

        else:
            st.warning("⚠️ Databáze je zatím prázdná. Čekám na první data z engine.py.")
    except Exception as e:
        st.error(f"Chyba při vykreslování terminálu: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen. Spusťte workflow v GitHub Actions.")
