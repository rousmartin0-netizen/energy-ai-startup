"""Energy AI bot engine — market data collection and Telegram notifications."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from gnews import GNews

logger = logging.getLogger(__name__)


# ── Defaults ──────────────────────────────────────────────────────────────

_DEFAULT_BIDDING_ZONE = "CZ"
_DEFAULT_WEATHER_LAT = "50.07"
_DEFAULT_WEATHER_LON = "14.43"
_DEFAULT_NEWS_LANG = "cs"
_DEFAULT_NEWS_COUNTRY = "CZ"
_DEFAULT_DATA_FILE = "market_history.csv"
_DEFAULT_MAX_POINTS = 50


# ── Configuration ─────────────────────────────────────────────────────────


class Config:
    """Runtime configuration loaded from environment variables / .env file."""

    __slots__ = (
        "telegram_token",
        "telegram_chat_id",
        "bidding_zone",
        "weather_lat",
        "weather_lon",
        "news_lang",
        "news_country",
        "data_file",
        "max_history_points",
    )

    def __init__(self) -> None:
        load_dotenv()
        self.telegram_token: str | None = os.getenv("TELEGRAM_TOKEN") or None
        self.telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID") or None
        self.bidding_zone: str = os.getenv("BIDDING_ZONE", _DEFAULT_BIDDING_ZONE)
        self.weather_lat: str = os.getenv("WEATHER_LAT", _DEFAULT_WEATHER_LAT)
        self.weather_lon: str = os.getenv("WEATHER_LON", _DEFAULT_WEATHER_LON)
        self.news_lang: str = os.getenv("NEWS_LANG", _DEFAULT_NEWS_LANG)
        self.news_country: str = os.getenv("NEWS_COUNTRY", _DEFAULT_NEWS_COUNTRY)
        self.data_file: str = os.getenv("DATA_FILE", _DEFAULT_DATA_FILE)
        self.max_history_points: int = int(
            os.getenv("MAX_HISTORY_POINTS", str(_DEFAULT_MAX_POINTS))
        )

    @property
    def has_telegram(self) -> bool:
        """Whether Telegram credentials are configured."""
        return bool(self.telegram_token and self.telegram_chat_id)


# ── Helpers ───────────────────────────────────────────────────────────────


def send_telegram_msg(
    message: str,
    token: str | None,
    chat_id: str | None,
) -> bool:
    """Send a plain-text message via the Telegram Bot API.

    Returns ``True`` on success, ``False`` on failure or when credentials are
    missing.
    """
    if not token or not chat_id:
        logger.warning("Telegram credentials not configured — skipping message.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params: dict[str, str] = {"chat_id": chat_id, "text": message}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except requests.RequestException as exc:
        logger.warning("Failed to send Telegram message: %s", exc)
        return False


def fetch_price(bidding_zone: str) -> float:
    """Fetch latest day-ahead electricity price (EUR/MWh) for *bidding_zone*.

    Falls back to ``100.0`` on any error.
    """
    url = f"https://api.energy-charts.info/price?bzn={bidding_zone}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        prices: list[float] = resp.json()["price"]
        return prices[-1]
    except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
        logger.warning("Failed to fetch price for zone %s: %s", bidding_zone, exc)
        return 100.0


def fetch_wind(lat: str, lon: str) -> float:
    """Fetch current wind speed (km/h) at the given coordinates.

    Falls back to ``0.0`` on error.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["current_weather"]["windspeed"])
    except (requests.RequestException, KeyError, TypeError) as exc:
        logger.warning("Failed to fetch wind data: %s", exc)
        return 0.0


def fetch_headline(lang: str, country: str) -> str:
    """Fetch a recent news headline about electricity / energy.

    Falls back to a default string on error.
    """
    try:
        gnews = GNews(language=lang, country=country, period="24h", max_results=1)
        news = gnews.get_news("energetika cena elektřiny")
        return news[0]["title"] if news else "Klid na trhu"
    except Exception as exc:
        logger.debug("Failed to fetch news headline: %s", exc)
        return "Sleduji trh..."


def save_market_data(
    data_file: str,
    timestamp: str,
    price: float,
    wind: float,
    headline: str,
    max_points: int,
) -> None:
    """Append one row to the CSV history and keep at most *max_points* rows."""
    new_row = pd.DataFrame(
        [[timestamp, price, wind, 0, 0, headline]],
        columns=["time", "price", "wind", "solar", "news_score", "headline"],
    )

    path = Path(data_file)
    if path.exists():
        existing = pd.read_csv(path)
        df = pd.concat([existing, new_row], ignore_index=True).tail(max_points)
    else:
        df = new_row

    df.to_csv(path, index=False)
    logger.info("Saved %d rows to %s", len(df), data_file)


# ── Public API ────────────────────────────────────────────────────────────


def collect_and_store(config: Config | None = None) -> dict:
    """Run one full collection cycle and return a summary dict.

    Parameters
    ----------
    config : Config or None
        Runtime configuration.  A default ``Config()`` is created when
        ``None`` is passed.

    Returns
    -------
    dict
        Keys: ``price``, ``wind``, ``headline``, ``telegram_sent``,
        ``bidding_zone``.
    """
    if config is None:
        config = Config()

    logger.info("Starting collection cycle (zone=%s) …", config.bidding_zone)

    price = fetch_price(config.bidding_zone)
    wind = fetch_wind(config.weather_lat, config.weather_lon)
    headline = fetch_headline(config.news_lang, config.news_country)
    timestamp = datetime.now().strftime("%H:%M")

    save_market_data(
        data_file=config.data_file,
        timestamp=timestamp,
        price=price,
        wind=wind,
        headline=headline,
        max_points=config.max_history_points,
    )

    telegram_sent = send_telegram_msg(
        f"🤖 Bot je online!\nAktuální cena v {config.bidding_zone}: {price} EUR/MWh",
        token=config.telegram_token,
        chat_id=config.telegram_chat_id,
    )

    logger.info("Cycle done. Price=%.1f, Wind=%.1f", price, wind)

    return {
        "price": price,
        "wind": wind,
        "headline": headline,
        "telegram_sent": telegram_sent,
        "bidding_zone": config.bidding_zone,
    }


def main() -> None:
    """CLI entry point (one collection cycle)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    summary = collect_and_store()
    print(f"✅ Price={summary['price']} EUR/MWh, Wind={summary['wind']} km/h")


if __name__ == "__main__":
    main()
