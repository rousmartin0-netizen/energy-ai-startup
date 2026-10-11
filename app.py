import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="BESS Control Center | Second Foundation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st_autorefresh(interval=30000, key="datarefresh")

st.title("⚡ SECOND FOUNDATION: BESS CONTROL CENTER (1 MWh / 500 kW)")
st.markdown("Živý dispečink velkokapacitního bateriového kontejneru na českém spotovém trhu.")

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
                    return "Minulost" if t_obj <= now_dt else "Budoucnost (Plán)"
                except:
                    return "Neznámé"

            df['status'] = df['time'].apply(classify_time)
            
            # Vyhledání nejbližšího aktuálního řádku podle času
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
            current_soc = latest_row.get('battery_soc_kwh', 500)
            soc_percent = (current_soc / 1000.0) * 100
            current_power = latest_row.get('bess_power_kw', 0)
            current_action = latest_row.get('bess_action', 'IDLE')
            total_profit = df['cumulative_profit_eur'].iloc[-1] if 'cumulative_profit_eur' in df.columns else 0

            # --- HORNÍ PANEL ŘÍDÍCÍCH METRIK ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Dispečerský čas", current_time_str, current_date_str)
            col2.metric("Aktuální tržní cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Množství energie v BESS", f"{current_soc:.1f} kWh", f"{soc_percent:.1f}% kapacity")
            col4.metric("Aktuální výkon střídače", f"{current_power:+.1f} kW", "Kladné=Nabíjí / Záporné=Vybíjí")
            col5.metric("Celkový denní čistý P&L", f"{total_profit:+.2f} EUR", "Arbitrážní výnos")
            
            st.markdown("---")

            # --- HLAVNÍ VIZUALIZACE ---
            left_col, right_col = st.columns([2, 1])

            with left_col:
                st.subheader("📊 Vizualizace stavu nabití (SoC) během dne")
                st.markdown("*Graf ukazuje, jak se kontejner plní (nabíjí při levné/záporné ceně) a vyprazdňuje (prodává ve špičce).*")
                
                # Vizualizace 1: Vývoj kapacity baterie v čase
                soc_chart_data = df.set_index('time')[['battery_soc_kwh']]
                st.line_chart(soc_chart_data, use_container_width=True)

                st.subheader("📈 Tržní ceny & Výkonové toky")
                price_chart_data = df.set_index('time')[['price']]
                st.line_chart(price_chart_data, use_container_width=True)

            with right_col:
                st.subheader("🚨 Živý stav kontejneru")
                
                if "NABÍJENÍ" in str(current_action):
                    st.success("🟢 Stav: **AKTIVNĚ NABÍJÍ**\nNakupuje levnou elektřinu do zásoby.")
                elif "VYBÍJENÍ" in str(current_action):
                    st.warning("🔴 Stav: **AKTIVNĚ VYBÍJÍ**\nProdává drahou elektřinu do sítě.")
                else:
                    st.info("🔵 Stav: **IDLE (Pohotovost)**\nČeká na optimální cenové okno.")

                st.markdown("#### Fyzické parametry:")
                st.progress(int(soc_percent))
                st.write(f"• **Kapacita:** {current_soc:.1f} / 1000 kWh")
                st.write(f"• **Invertor:** Max 500 kW")
                st.write(f"• **Efektivita kontejneru:** 88%")
                
                st.markdown("---")
                st.info("💡 **Strategie:** Automatická arbitráž s plnou znalostí denní křivky (Perfect Foresight).")

            st.markdown("---")

            # --- BUDOUCÍ PLÁN A DISPEČERSKÝ HARMONOGRAM ---
            st.subheader("🔮 Plán dispečinku pro budoucí hodiny a kompletní log")
            
            tab1, tab2, tab3 = st.tabs(["Budoucí plán (Predikce)", "Minulost (Uplynulé hodiny)", "Kompletní log dne"])
            
            with tab1:
                future_df = df[df['status'] == "Budoucnost (Plán)"]
                if not future_df.empty:
                    st.dataframe(future_df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur']], use_container_width=True)
                else:
                    st.info("Pro dnešní den již vypršely budoucí hodinové bloky. Čeká se na zítřejší aukci.")
            
            with tab2:
                past_df = df[df['status'] == "Minulost"]
                st.dataframe(past_df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur']], use_container_width=True)

            with tab3:
                st.dataframe(df[['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh', 'hourly_cash_eur', 'cumulative_profit_eur', 'status']], use_container_width=True)

        else:
            st.warning("⚠️ Databáze je prázdná.")
    except Exception as e:
        st.error(f"Chyba při vykreslování terminálu: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen.")
