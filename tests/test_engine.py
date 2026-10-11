"""Tests for energy_ai_startup.engine.

All external API calls are mocked — no network required.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
import requests

from energy_ai_startup.engine import (
    Config,
    collect_and_store,
    fetch_headline,
    fetch_price,
    fetch_wind,
    save_market_data,
    send_telegram_msg,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_data_file(tmp_path: Path) -> str:
    """Return a path to a non-existent CSV inside a temp dir."""
    return str(tmp_path / "market_history.csv")


@pytest.fixture
def sample_csv(tmp_path: Path) -> str:
    """Create a CSV with a few rows and return its path."""
    df = pd.DataFrame(
        [
            ["10:00", 120.0, 10.0, 0, 0, "headline a"],
            ["11:00", 130.0, 12.0, 0, 0, "headline b"],
        ],
        columns=["time", "price", "wind", "solar", "news_score", "headline"],
    )
    path = tmp_path / "market_history.csv"
    df.to_csv(path, index=False)
    return str(path)


# ── Config ────────────────────────────────────────────────────────────────


class TestConfig:
    def test_default_values(self) -> None:
        """Config falls back to sensible defaults when env is empty."""
        cfg = Config()
        assert cfg.bidding_zone == "CZ"
        assert cfg.weather_lat == "50.07"
        assert cfg.weather_lon == "14.43"
        assert cfg.news_lang == "cs"
        assert cfg.news_country == "CZ"
        assert cfg.data_file == "market_history.csv"
        assert cfg.max_history_points == 50

    def test_telegram_optional(self) -> None:
        """has_telegram is False when credentials are absent."""
        cfg = Config()
        assert cfg.has_telegram is False

    @patch.dict(os.environ, {"TELEGRAM_TOKEN": "abc", "TELEGRAM_CHAT_ID": "123"})
    def test_telegram_present(self) -> None:
        """has_telegram is True when both env vars are set."""
        # Clear cached Config by creating fresh instance
        cfg = Config()
        assert cfg.has_telegram is True


# ── send_telegram_msg ─────────────────────────────────────────────────────


class TestSendTelegramMsg:
    def test_returns_false_when_no_creds(self) -> None:
        assert send_telegram_msg("hi", None, None) is False
        assert send_telegram_msg("hi", "tok", None) is False

    @patch("energy_ai_startup.engine.requests.get")
    def test_success(self, mock_get: Mock) -> None:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.raise_for_status = MagicMock()
        assert send_telegram_msg("ahoj", "tok", "123") is True

    @patch("energy_ai_startup.engine.requests.get")
    def test_network_error(self, mock_get: Mock) -> None:
        mock_get.side_effect = requests.ConnectionError("timeout")
        assert send_telegram_msg("ahoj", "tok", "123") is False

    @patch("energy_ai_startup.engine.requests.get")
    def test_http_error(self, mock_get: Mock) -> None:
        mock_get.return_value.raise_for_status.side_effect = (
            requests.HTTPError("401")
        )
        assert send_telegram_msg("ahoj", "tok", "123") is False


# ── fetch_price ───────────────────────────────────────────────────────────


class TestFetchPrice:
    @patch("energy_ai_startup.engine.requests.get")
    def test_returns_last_price(self, mock_get: Mock) -> None:
        mock_get.return_value.json.return_value = {"price": [50, 60, 70]}
        assert fetch_price("CZ") == 70

    @patch("energy_ai_startup.engine.requests.get")
    def test_network_error_fallback(self, mock_get: Mock) -> None:
        mock_get.side_effect = requests.ConnectionError
        assert fetch_price("CZ") == 100.0

    @patch("energy_ai_startup.engine.requests.get")
    def test_malformed_json_fallback(self, mock_get: Mock) -> None:
        mock_get.return_value.json.return_value = {}
        assert fetch_price("CZ") == 100.0


# ── fetch_wind ────────────────────────────────────────────────────────────


class TestFetchWind:
    @patch("energy_ai_startup.engine.requests.get")
    def test_returns_windspeed(self, mock_get: Mock) -> None:
        mock_get.return_value.json.return_value = {
            "current_weather": {"windspeed": 15.3}
        }
        assert fetch_wind("50.07", "14.43") == 15.3

    @patch("energy_ai_startup.engine.requests.get")
    def test_error_fallback(self, mock_get: Mock) -> None:
        mock_get.side_effect = requests.ConnectionError
        assert fetch_wind("50.07", "14.43") == 0.0


# ── fetch_headline ────────────────────────────────────────────────────────


class TestFetchHeadline:
    @patch("energy_ai_startup.engine.GNews")
    def test_returns_title(self, mock_gnews_cls: Mock) -> None:
        mock_instance = mock_gnews_cls.return_value
        mock_instance.get_news.return_value = [{"title": "Trh roste"}]
        assert fetch_headline("cs", "CZ") == "Trh roste"

    @patch("energy_ai_startup.engine.GNews")
    def test_empty_news_fallback(self, mock_gnews_cls: Mock) -> None:
        mock_instance = mock_gnews_cls.return_value
        mock_instance.get_news.return_value = []
        assert fetch_headline("cs", "CZ") == "Klid na trhu"

    @patch("energy_ai_startup.engine.GNews")
    def test_exception_fallback(self, mock_gnews_cls: Mock) -> None:
        mock_instance = mock_gnews_cls.return_value
        mock_instance.get_news.side_effect = Exception("API down")
        assert fetch_headline("cs", "CZ") == "Sleduji trh..."


# ── save_market_data ──────────────────────────────────────────────────────


class TestSaveMarketData:
    def test_creates_new_file(self, tmp_data_file: str) -> None:
        save_market_data(tmp_data_file, "12:00", 150.0, 8.0, "novinka", 50)
        df = pd.read_csv(tmp_data_file)
        assert len(df) == 1
        assert df.iloc[0]["price"] == 150.0

    def test_appends_to_existing(self, sample_csv: str) -> None:
        save_market_data(sample_csv, "12:00", 200.0, 5.0, "extra", 50)
        df = pd.read_csv(sample_csv)
        assert len(df) == 3
        assert df.iloc[-1]["price"] == 200.0

    def test_trims_to_max_points(self, tmp_data_file: str) -> None:
        for i in range(10):
            save_market_data(
                tmp_data_file, f"{i:02d}:00", float(i), 1.0, "x", 3
            )
        df = pd.read_csv(tmp_data_file)
        assert len(df) == 3
        assert df.iloc[0]["price"] == 7.0  # trimmed to last 3


# ── collect_and_store (integration-style) ─────────────────────────────────


class TestCollectAndStore:
    @patch("energy_ai_startup.engine.send_telegram_msg", return_value=True)
    @patch("energy_ai_startup.engine.fetch_headline", return_value="Zpráva")
    @patch("energy_ai_startup.engine.fetch_wind", return_value=12.5)
    @patch("energy_ai_startup.engine.fetch_price", return_value=155.0)
    @patch("energy_ai_startup.engine.Path.exists", return_value=True)
    @patch("energy_ai_startup.engine.pd.read_csv")
    def test_full_cycle(
        self,
        mock_read: Mock,
        mock_exists: Mock,
        mock_price: Mock,
        mock_wind: Mock,
        mock_headline: Mock,
        mock_telegram: Mock,
        tmp_data_file: str,
    ) -> None:
        """collect_and_store feeds the mocked values correctly."""
        mock_read.return_value = pd.DataFrame(
            [["10:00", 100.0, 5.0, 0, 0, "old"]],
            columns=["time", "price", "wind", "solar", "news_score", "headline"],
        )

        cfg = Config()
        cfg.data_file = tmp_data_file
        result = collect_and_store(config=cfg)

        assert result["price"] == 155.0
        assert result["wind"] == 12.5
        assert result["headline"] == "Zpráva"
        assert result["telegram_sent"] is True
        assert result["bidding_zone"] == "CZ"
