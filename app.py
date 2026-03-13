import streamlit as st
import pandas as pd
import os

# Základní nastavení stránky
st.set_page_config(page_title="Český Energetický Bot", layout="wide", page_icon="🇨🇿")

# Profesionální tmavý vzhled
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🇨🇿 Second Foundation: Český energetický trh")

file_path = "market_history.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    
    # Kontrola, zda máme aspoň nějaká data
    if not df.empty:
        latest = df.iloc[-1]
        
        # Načtení hodnot s ošetřením chybějících sloupců
        cena = latest['price']
        vitr = latest['wind']
        slunce = latest.get('solar', 0)
        sentiment = latest.get('news_score', 0)
        titulek = latest.get('headline', "Hledám nové zprávy...")

        # 1. Horní řada metrik
        col1, col2, col3, col4 = st.columns(4)
        
        # Pokud je cena 0, zobrazíme varování
        if cena <= 0:
            col1.metric("Cena v ČR", "Čekám...", delta="Offline")
        else:
            col1.metric("Cena v ČR", f"{cena} EUR/MWh")
            
        col2.metric("Rychlost větru", f"{vitr} km/h")
        col3.metric("Solární index", f"{slunce} W/m²")
        col4.metric("AI Sentiment", sentiment)

        st.markdown("---")

        # 2. Analýza a Doporučení
        st.subheader("🤖 AI Analýza a Doporučení")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            # Logika doporučení
            if sentiment > 1 or (cena > 150 and vitr < 10):
                st.error("🚀 DOPORUČENÍ: NAKOUPIT (BUY)")
                st.write("**Důvod:** Negativní zprávy nebo nízká výroba tlačí ceny nahoru.")
            elif vitr > 25 or slunce > 500 or sentiment < -1:
                st.success("🚨 DOPORUČENÍ: PRODAT (SELL)")
                st.write("**Důvod:** Vysoká produkce z obnovitelných zdrojů srazí cenu dolů.")
            else:
                st.info("⚖️ DOPORUČENÍ: DRŽET (HOLD)")
                st.write("**Důvod:** Trh je momentálně stabilní a v rovnováze.")

        with c2:
            st.write("### Poslední zpráva z monitoringu:")
            st.info(f"📰 {titulek}")

        # 3. Graf historie
        st.markdown("---")
        st.subheader("📈 Vývoj ceny na vnitrodenním trhu")
        
        if len(df) > 1:
            # Vykreslíme oblastní graf pro lepší vizuální efekt
            chart_data = df.set_index('time')['price']
            st.area_chart(chart_data, color="#00ff00")
        else:
            st.info("Sběr dat zahájen. Graf se vykreslí po druhém měření (každou hodinu).")
            # Ukážeme aspoň tabulku, pokud není graf
            st.write(df)

    else:
        st.warning("Soubor s daty je prázdný. Spusťte bota v GitHub Actions.")
else:
    st.error("❌ Datový tunel nenalezen. Musíte nejdříve spustit 'Run workflow' v záložce Actions na GitHubu.")

# Sidebar s informacemi
st.sidebar.title("Nastavení bota")
st.sidebar.write("Region: **Česká republika**")
st.sidebar.write("Model: **Alpha-v2-Czech**")
st.sidebar.markdown("---")
st.sidebar.caption("Bot automaticky skenuje burzu PXE, Open-Meteo a české zpravodajské servery.")
