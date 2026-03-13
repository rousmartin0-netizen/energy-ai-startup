import streamlit as st
import pandas as pd
import os
import random

st.set_page_config(page_title="Energy AI Startup", layout="wide", page_icon="⚡")

# Custom CSS pro profi vzhled
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_index=True)

st.title("🛡️ Second Foundation Alpha - Energy Intelligence")

file_path = "market_history.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    
    # 1. HLAVNÍ METRIKY
    latest = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Live Market Price", f"{latest['price']} EUR")
    col2.metric("Wind Speed (DE)", f"{latest['wind']} km/h")
    
    # Simulovaný solární index a sentiment (zatím pro vzhled, brzy napojíme na API)
    solar_power = random.randint(5, 85) # % produkce
    col3.metric("Solar Load Index", f"{solar_power} %")
    
    # Sentiment ze zpráv (zatím náhodný, simuluje NLP modul)
    sentiment = random.choice(["BULLISH", "BEARISH", "NEUTRAL"])
    col4.metric("Market Sentiment", sentiment)

    st.markdown("---")

    # 2. AI ANALÝZA RIZIKA A SIGNÁL
    st.subheader("🤖 AI Decision Engine v1.1")
    
    # Pokročilejší rozhodovací logika
    risk_score = 0
    if latest['wind'] > 30: risk_score -= 40
    if solar_power > 60: risk_score -= 30
    if sentiment == "BEARISH": risk_score -= 20
    if sentiment == "BULLISH": risk_score += 30

    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.write("### Obchodní doporučení")
        if risk_score < -20:
            st.error("🚨 STRONG SELL (Očekáván přebytek)")
        elif risk_score > 20:
            st.success("🚀 STRONG BUY (Očekáván nedostatek)")
        else:
            st.info("⚖️ HOLD (Stabilní trh)")
            
        st.progress(min(max((risk_score + 100) / 200, 0.0), 1.0))
        st.caption("Risk Exposure Index (-100 to +100)")

    with c2:
        # 3. PREDIKCE (Jednoduchý trendový model)
        st.write("### Market Projection (Next 4h)")
        # Simulace predikce - vezmeme poslední cenu a přidáme šum podle větru
        projection = [latest['price'] + (random.uniform(-5, 5) - (latest['wind']/10)) for _ in range(5)]
        st.area_chart(projection)

    st.markdown("---")

    # 4. GRAF HISTORIE
    st.subheader("📊 Real-time Feed Analysis")
    st.line_chart(df.set_index('time')['price'])

else:
    st.warning("Čekám na inicializaci datového tunelu...")

st.sidebar.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
st.sidebar.title("Bot Settings")
st.sidebar.write("Model: **Llama-3-Energy-v1**")
st.sidebar.write("Region: **DE-LU (Central Europe)**")
st.sidebar.button("Retrain Model")
