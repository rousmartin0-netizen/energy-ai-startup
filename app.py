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
st.markdown("Reálný dispečink bateriového kontejneru s chronologickou fyzikální simulací rychlosti nabíjení.")

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
            
            # Vyhledání aktuálního řádku
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

            # --- SPOJENÝ GRAF: CENA + VÝKON BATERIE ---
            st.subheader("📊 Integrovaný dispečerský graf: Cena elektřiny vs. Výkon BESS")
            st.markdown("*Modrá čára ukazuje vývoj ceny (€/MWh) na burze. Sloupce znázorňují aktivitu kontejneru: zelená = nabíjení (příkon), červená = vybíjení (dodávka do sítě).*")

            # Vytvoření pokročilého překrývajícího se grafu (Dual-Axis) přes Altair
            base = alt.Chart(df).encode(x=alt.X('time:N', title='Hodina dne'))

            price_line = base.mark_line(strokeWidth=3, color='#1f77b4').encode(
                y=alt.Y('price:Q', title='Cena elektřiny (€/MWh)')
            )

            # Opraveno alt.Condition -> alt.condition (s malým 'c')
            power_bars = base.mark_bar(opacity=0.75, width=15).encode(
                y=alt.Y('bess_power_kw:Q', title='BESS Výkon střídače (kW)'),
                color=alt.condition(
                    alt.datum.bess_power_kw > 0,
                    alt.value('#2ca02c'), # Zelená pro nabíjení
                    alt.value('#d62728')  # Červená pro vybíjení
                ),
                tooltip=['time', 'price', 'bess_action', 'bess_power_kw', 'battery_soc_kwh']
            )

            combined_chart = alt.layer(price_line, power_bars).resolve_scale(
                y='independent'
            ).properties(
                height=420
            )

            st.altair_chart(combined_chart, use_container_width=True)

            st.markdown("---")

            # --- DVOUSLOUPCOVÝ PŘEHLED (STATUS + VÝVOJ SoC) ---
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.subheader("🔋 Vývoj stavu nabití (SoC v čase)")
                soc_chart_data = df.set_index('time')[['battery_soc_kwh']]
                st.line_chart(soc_chart_data, use_container_width=True)

            with right_col:
                st.subheader("🚨 Aktuální stav kontejneru")
                
                if "NABÍJENÍ" in str(current_action):
                    st.success(f"🟢 **AKTIVNĚ NABÍJÍ**\nPříkon do baterie: **+{current_power:.1f} kW**")
                elif "VYBÍJENÍ" in str(current_action):
                    st.warning(f"🔴 **AKTIVNĚ VYBÍJÍ**\nDodávka do sítě: **{current_power:.1f} kW**")
                else:
                    st.info("🔵 **IDLE (Pohotovost)**\nČeká na optimální cenové okno v síti.")

                st.markdown("#### Fyzické parametry kontejneru:")
                st.progress(int(soc_percent))
                st.write(f"• **Kapacita v baterii:** {current_soc:.1f} kWh / 1000 kWh")
                st.write(f"• **Rychlost střídače:** 500 kW limit")
                st.write(f"• **Ztráty účinnosti:** 88% celkově (Round-trip)")
                st.success("🤖 Chronologický fyzikální model aktivní.")

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
