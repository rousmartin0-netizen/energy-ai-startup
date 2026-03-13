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
    
    # Ošetření nových sloupců (solar a news_score)
    solar_val = latest['solar'] if 'solar' in latest else 0
    news_val = latest['news_score'] if 'news_score' in latest else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Price", f"{latest['price']} EUR")
    col2.metric("Wind Speed", f"{latest['wind']} km/h")
    col3.metric("Solar Index", f"{solar_val} W/m²")
    
    # Barva pro news score (červená pokud je vysoké riziko)
    news_color = "normal" if news_val <= 2 else "inverse"
    col4.metric("News Risk Score", news_val, delta_color=news_color)

    st.markdown("---")

    # LOGIKA ROZHODOVÁNÍ (Teď i se zprávami!)
    st.subheader("🤖 AI Analysis Logic")
    
    # Výpočet sentimentu (přidali jsme vliv zpráv)
    if (latest['price'] > 120 and latest['wind'] < 10) or news_val > 3:
        sentiment = "VERY BULLISH"
        advice = "🚀 STRONG BUY"
    elif latest['wind'] > 35 or solar_val > 400 or news_val < -2:
        sentiment = "VERY BEARISH"
        advice = "🚨 STRONG SELL"
    else:
        sentiment = "NEUTRAL"
        advice = "⚖️ HOLD"

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Market Sentiment:** {sentiment}")
        st.write(f"### Recommendation: {advice}")
        if news_val > 2:
            st.warning(f"⚠️ POZOR: Zprávy naznačují vysokou volatilitu (Risk: {news_val})")
    
    with c2:
        # Odhad pohybu ceny pro příští hodinu (zprávy zvyšují cenu)
        change = (latest['wind'] * -0.4) + (solar_val * -0.05) + (news_val * 2)
        st.write(f"### Expected Price Shift: {round(change, 2)} EUR")

    st.subheader("📊 Price History")
    st.line_chart(df.set_index('time')['price'])

else:
    st.warning("Čekám na synchronizaci datového tunelu... Zkuste obnovit stránku za minutu.")
