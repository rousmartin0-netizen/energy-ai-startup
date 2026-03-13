import streamlit as st
import pandas as pd
import os
from streamlit_autorefresh import st_autorefresh

# 1. KONFIGURACE STRÁNKY
st.set_page_config(page_title="CZ Second Foundation Live", layout="wide", page_icon="🇨🇿")

# 2. AUTO-REFRESH (Stránka se sama obnoví každých 30 sekund)
# To zajistí, že uvidíš nová data hned, jak je robot zapíše
st_autorefresh(interval=30000, key="datarefresh")

# Profesionální tmavý vzhled
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🇨🇿 CZ Second Foundation: LIVE TERMINAL")

file_path = "market_history.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    
    if not df.empty:
        latest = df.iloc[-1]
        
        # Načtení dat
        cena = latest['price']
        vitr = latest['wind']
        slunce = latest.get('solar', 0)
        sentiment = latest.get('news_score', 0)
        titulek = latest.get('headline', "Skenuji český trh...")

        # METRIKY
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cena v ČR", f"{cena} EUR/MWh")
        col2.metric("Vítr (Praha)", f"{vitr} km/h")
        col3.metric("Slunce", f"{slunce} W/m²")
        col4.metric("AI Sentiment", sentiment)

        st.markdown("---")

        # ANALÝZA
        st.subheader("🤖 AI Analýza a Doporučení")
        c1, c2 = st.columns([1, 1])
        with c1:
            if sentiment > 1 or (cena > 150 and vitr < 10):
                st.error("🚀 DOPORUČENÍ: NAKOUPIT (BUY)")
            elif vitr > 25 or slunce > 500 or sentiment < -1:
                st.success("🚨 DOPORUČENÍ: PRODAT (SELL)")
            else:
                st.info("⚖️ DOPORUČENÍ: DRŽET (HOLD)")
            
            st.caption(f"Poslední aktualizace terminálu: {latest['time']}")

        with c2:
            st.write("### 📰 Monitoring médií:")
            st.info(f"{titulek}")

        # LIVE GRAF
        st.markdown("---")
        st.subheader("📈 Real-time cenová křivka")
        
        if len(df) > 1:
            # Vykreslení grafu
            st.area_chart(df.set_index('time')['price'], color="#00ff00")
        else:
            st.info("Sběr dat zahájen. Čekám na další body pro vykreslení křivky...")

    else:
        st.warning("Databáze je prázdná. Spusťte bota v GitHub Actions.")
else:
    st.error("❌ Soubor s daty nebyl nalezen.")

# SIDEBAR
st.sidebar.title("Terminál v2.0")
st.sidebar.write("Stav: **ONLINE - LIVE**")
st.sidebar.write("Obnovování: **30s**")
st.sidebar.markdown("---")
st.sidebar.caption("Tento dashboard se automaticky aktualizuje. Nechte ho otevřený pro sledování trhu.")
