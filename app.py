import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Energy AI Startup", layout="wide", page_icon="⚡")

st.title("⚡ Energy AI Trading Bot")
st.markdown("---")

file_path = "market_history.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    
    # Poslední data
    latest_price = df['price'].iloc[-1]
    latest_wind = df['wind'].iloc[-1]
    latest_time = df['time'].iloc[-1]
    
    # Horní karty s metrikami
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktuální cena", f"{latest_price} EUR/MWh")
    col2.metric("Rychlost větru", f"{latest_wind} km/h")
    col3.metric("Poslední update", latest_time)

    st.markdown("---")

    # AI Trading Signál
    st.subheader("🤖 AI Trading Strategie")
    if latest_wind > 20:
        st.success("🎯 SIGNÁL: PRODAT (SELL). Vysoká větrná produkce v Německu srazí ceny dolů.")
    else:
        st.warning("🎯 SIGNÁL: NAKOUPIT (BUY). Nízká větrná produkce zvýší poptávku po drahých zdrojích.")

    # Graf vývoje ceny
    st.subheader("📈 Historický vývoj ceny (DE-LU)")
    st.line_chart(df.set_index('time')['price'])
    
    # Tabulka dat pro kontrolu
    with st.expander("Zobrazit surová data"):
        st.write(df.tail(10))
else:
    st.warning("🚀 Čekám na první data. Spusť 'Run workflow' v GitHub Actions, pokud je soubor prázdný.")
