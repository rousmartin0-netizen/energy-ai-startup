import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Český Energetický Bot", layout="wide", page_icon="🇨🇿")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🇨🇿 Second Foundation: Český energetický trh")

if os.path.exists("market_history.csv"):
    df = pd.read_csv("market_history.csv")
    latest = df.iloc[-1]
    
    # Načtení dat
    cena = latest['price']
    vitr = latest['wind']
    slunce = latest['solar'] if 'solar' in latest else 0
    sentiment = latest['news_score'] if 'news_score' in latest else 0
    titulek = latest['headline'] if 'headline' in latest else "Aktualizuji zprávy..."
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cena v ČR", f"{cena} EUR")
    col2.metric("Rychlost větru", f"{vitr} km/h")
    col3.metric("Solární index", f"{slunce} W/m²")
    col4.metric("Zpravodajské riziko", sentiment)

    st.markdown("---")

    st.subheader("🤖 AI Analýza a Doporučení")
    
    c1, c2 = st.columns(2)
    with c1:
        if sentiment > 1 or (cena > 150 and vitr < 5):
            st.error("🚀 DOPORUČENÍ: NAKOUPIT (BUY)")
            st.write("Důvod: Nízká výroba a negativní zprávy tlačí cenu nahoru.")
        elif vitr > 25 or slunce > 500:
            st.success("🚨 DOPORUČENÍ: PRODAT (SELL)")
            st.write("Důvod: Vysoká výroba z OZE srazí cenu dolů.")
        else:
            st.info("⚖️ DOPORUČENÍ: DRŽET (HOLD)")
            st.write("Důvod: Trh je v rovnováze.")

    with c2:
        st.write("### Poslední zpráva z monitoringu:")
        st.info(f"📰 {titulek}")

    st.subheader("📈 Historie ceny v ČR")
    st.line_chart(df.set_index('time')['price'])

else:
    st.warning("Čekám na první česká data...")
