# energy-ai-startup

AI-powered energy trading bot that forecasts electricity prices based on
weather (wind) and market data from [Energy-Charts](https://energy-charts.info)
and [Open-Meteo](https://open-meteo.com/). Built for automated data collection
and signal generation.

## Features

- 📡 **Market data collection** — fetches day-ahead electricity prices via
  the Energy-Charts API for configurable bidding zones (default: CZ)
- 🌤️ **Weather integration** — real-time wind speed from Open-Meteo
- 📰 **News monitoring** — energy-sector headlines via Google News
- 🤖 **Telegram alerts** — instant notifications on each collection cycle
- 📊 **Live dashboard** — Streamlit-based visualisation with buy/sell/hold
  signals
- ⏱️ **CI/CD** — automated data collection every 5 minutes via GitHub Actions

## Quick Start

```bash
# Clone & install
git clone https://github.com/rousmartin0-netizen/energy-ai-startup.git
cd energy-ai-startup
pip install -e ".[dev]"

# Configure (optional — defaults work without env vars)
cp .env.example .env
# Edit .env with your Telegram credentials (see below)

# Run one collection cycle
energy-bot
```

## Configuration

All settings are read from environment variables or a `.env` file
(copy `.env.example` to `.env` to get started).

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | — | Bot token from [@BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | — | Your Telegram chat ID |
| `BIDDING_ZONE` | `CZ` | Market bidding zone (CZ, DE-LU, AT, PL, …) |
| `WEATHER_LAT` | `50.07` | Weather station latitude |
| `WEATHER_LON` | `14.43` | Weather station longitude |
| `DATA_FILE` | `market_history.csv` | Path to the CSV data store |
| `MAX_HISTORY_POINTS` | `50` | Max rows kept in the CSV |

## Usage

### CLI

```bash
# Run one data-collection cycle (default entry point)
energy-bot

# Or via Python module
python -m energy_ai_startup.engine
```

### Dashboard

```bash
streamlit run energy_ai_startup/dashboard.py
```

Opens a live terminal at `http://localhost:8501` that auto-refreshes every
30 seconds.

### GitHub Actions

The repo includes a scheduled workflow (`.github/workflows/main.yml`) that
runs `engine.py` every 5 minutes via `cron: '*/5 * * * *'`.  The collected
data is committed back to the repository automatically.

## Project Structure

```
energy-ai-startup/
├── energy_ai_startup/
│   ├── __init__.py       # Package init
│   ├── engine.py         # Data-collection engine + Telegram alerts
│   └── dashboard.py      # Streamlit live dashboard
├── tests/
│   └── test_engine.py    # 14 test cases (mocked, no network required)
├── .env.example          # Environment variable template
├── .github/workflows/    # CI/CD workflows
├── pyproject.toml        # Build config, dependencies, tool settings
└── README.md
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v           # All tests pass offline
ruff check .               # Lint
```

## License

MIT — see [LICENSE](LICENSE).
