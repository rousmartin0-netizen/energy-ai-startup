import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Second Foundation Alpha", layout="wide", page_icon="⚡")

# OPRAVENÉ CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Second Foundation Alpha")

file_path = "market_history.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    latest = df.iloc[-1]
    
    # Ošetření sloupce solar pro starší data
    solar_val = latest['solar'] if 'solar' in latest else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Market Price", f"{latest['price']} EUR")
    col2.metric("Wind Speed", f"{latest['wind']} km/h")
    col3.metric("Solar Index", f"{solar_val} W/m²")

    st.markdown("---")

    # LOGIKA ROZHODOVÁNÍ
    st.subheader("🤖 AI Analysis Logic")
    
    # Výpočet sentimentu
    if latest['price'] > 120 and latest['wind'] < 10:
        sentiment = "VERY BULLISH"
        advice = "🚀 STRONG BUY"
    elif latest['wind'] > 35 or solar_val > 400:
        sentiment = "VERY BEARISH"
        advice = "🚨 STRONG SELL"
    else:
        sentiment = "NEUTRAL"
        advice = "⚖️ HOLD"

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Market Sentiment:** {sentiment}")
        st.write(f"### Recommendation: {advice}")
    
    with c2:
        # Odhad pohybu ceny pro příští hodinu
        change = (latest['wind'] * -0.4) + (solar_val * -0.05)
        st.write(f"### Expected Price Shift: {round(change, 2)} EUR")

    st.subheader("📊 Price History")
    st.line_chart(df.set_index('time')['price'])

else:
    st.warning("Čekám na synchronizaci datového tunelu... Zkuste obnovit stránku za minutu.")
