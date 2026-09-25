"""Streamlit dashboard for the Energy AI bot — live monitoring terminal."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ── Page config (must be first Streamlit call) ────────────────────────────

st.set_page_config(
    page_title="CZ Second Foundation Live",
    layout="wide",
    page_icon="🇨🇿",
)

# ── Constants ─────────────────────────────────────────────────────────────

DEFAULT_DATA_FILE = "market_history.csv"
AUTO_REFRESH_MS = 30_000

# ── Helpers ───────────────────────────────────────────────────────────────


def _dark_style() -> str:
    return """\
    <style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #161b22;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #30363d;
    }
    </style>"""


def load_latest_row(data_file: str) -> tuple[pd.DataFrame, pd.Series] | None:
    """Read CSV and return (full_df, latest_row) or ``None`` on failure."""
    path = Path(data_file)
    if not path.exists():
        return None

    df = pd.read_csv(path)
    if df.empty:
        return None

    return df, df.iloc[-1]


# ── UI ────────────────────────────────────────────────────────────────────

st.markdown(_dark_style(), unsafe_allow_html=True)
st.title("🇨🇿 CZ Second Foundation: LIVE TERMINAL")

st_autorefresh(interval=AUTO_REFRESH_MS, key="datarefresh")

data_file = os.getenv("DATA_FILE", DEFAULT_DATA_FILE)
result = load_latest_row(data_file)
file_path_label = Path(data_file).name

if result is None:
    file_exists = Path(data_file).exists()
    if file_exists:
        st.warning("Databáze je prázdná. Spusťte bota v GitHub Actions.")
    else:
        st.error(f"❌ Soubor s daty nebyl nalezen ({file_path_label}).")
else:
    df, latest = result

    cena: float = latest["price"]
    vitr: float = latest["wind"]
    slunce: float = latest.get("solar", 0)
    sentiment: float = latest.get("news_score", 0)
    titulek: str = str(latest.get("headline", "Skenuji český trh..."))

    # ── Metrics ────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cena v ČR", f"{cena} EUR/MWh")
    col2.metric("Vítr (Praha)", f"{vitr} km/h")
    col3.metric("Slunce", f"{slunce} W/m²")
    col4.metric("AI Sentiment", sentiment)

    st.markdown("---")

    # ── Analysis ───────────────────────────────────────────────────────
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

    # ── Chart ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Real-time cenová křivka")

    if len(df) > 1:
        st.area_chart(df.set_index("time")["price"], color="#00ff00")
    else:
        st.info("Sběr dat zahájen. Čekám na další body pro vykreslení křivky...")

# ── Sidebar ───────────────────────────────────────────────────────────────

st.sidebar.title("Terminál v2.0")
st.sidebar.write("Stav: **ONLINE - LIVE**")
st.sidebar.write("Obnovování: **30s**")
st.sidebar.markdown("---")
st.sidebar.caption(
    "Tento dashboard se automaticky aktualizuje. "
    "Nechte ho otevřený pro sledování trhu."
)
