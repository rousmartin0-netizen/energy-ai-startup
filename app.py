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
    initial_sidebar_state="collapsed"
)

st_autorefresh(interval=30000, key="datarefresh")

st.title("⚡ SECOND FOUNDATION: BESS CONTROL CENTER (1 MWh / 500 kW)")
st.markdown("Reálný dispečink bateriového kontejneru s plynulou výkonovou křivkou a MPC řízením.")

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
            
            # Příprava oddělených sérií pro plynulé křivky (nabíjení > 0, vybíjení < 0)
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
            current_soc = latest_row.get('battery_soc_kwh', 500)
            soc_percent = (current_soc / 1000.0) * 100
            current_power = latest_row.get('bess_power_kw', 0)
            current_action = latest_row.get('bess_action', 'IDLE')
            total_profit = df['cumulative_profit_eur'].iloc[-1] if 'cumulative_profit_eur' in df.columns else 0

            # --- HORNÍ PANEL METRIK ---
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Dispečerský čas", current_time_str, current_date_str)
            col2.metric("Tržní cena", f"{latest_price:.2f} €/MWh")
            col3.metric("Množství energie v BESS", f"{current_soc:.1f} kWh", f"{soc_percent:.1f}% kapacity")
            col4.metric("Výkon střídače", f"{current_power:+.1f} kW", "Max 500 kW")
            col5.metric("Celkový denní P&L", f"{total_profit:+.2f} EUR", "Čistá arbitráž")
            
            st.markdown("---")

            # --- INTEGROVANÝ DISPEČERSKÝ GRAF S PLYNULÝMI KŘIVKAMI ---
            st.subheader("📊 Integrovaný dispečerský graf: Cena elektřiny vs. BESS Výkonová Křivka")
            st.markdown("*Modrá čára znázorňuje vývoj tržní ceny (€/MWh). Plynulá barevná křivka (zelená = nabíjení, červená = vybíjení) ukazuje výkon střídače v čase.*")

            base = alt.Chart(df).encode(x=alt.X('time:N', title='Hodina dne'))

            price_line = base.mark_line(strokeWidth=3, color='#1f77b4').encode(
                y=alt.Y('price:Q', title='Cena elektřiny (€/MWh)')
            )

            # Plynulá zelená křivka pro nabíjení (nad nulou) - opraveno y2 na 0
            charge_area = base.mark_area(interpolate='monotone', fill='#2ca02c', opacity=0.5).encode(
                y=alt.Y('charge_power:Q', title='BESS Výkon (kW) [Nabíjení > 0, Vybíjení < 0]'),
                y2=alt.value(0),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            # Plynulá červená křivka pro vybíjení (pod nulou) - opraveno y2 na 0
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
                st.write(f"• **Kapacita v baterii:** {current_soc:.1f} kWh / 1000 kWh")
                st.write(f"• **Rychlost střídače:** 500 kW limit")
                st.write(f"• **Ztráty účinnosti:** 88% celkově (Round-trip)")
                st.success("🤖 MPC predikční model s čekáním na peaky aktivní.")

            st.markdown("---")

            # --- DISPEČERSKÝ HARMONOGRAM ---
            st.subheader("🔮 Harmonogram a dispečerský log")
            
            tab1, tab2, tab3 = st.tabs(["Budoucí plán (Predikce)", "Minulost (Uplynulé hodiny)", "Kompletní log dne"])
            
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

        else:
            st.warning("⚠️ Databáze je prázdná.")
    except Exception as e:
        st.error(f"Chyba při vykreslování terminálu: {e}")
else:
    st.warning("⚠️ Soubor 'market_history.csv' nebyl nalezen.")
