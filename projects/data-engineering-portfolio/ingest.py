# weather api example

import json
import logging
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"

PARAMS: dict[str, str | float] = {
    "latitude": 14.5995,
    "longitude": 120.9842,
    "current": "temperature_2m,wind_speed_10m",
}

OUTPUT_PATH = Path("data/raw/weather.json")


def fetch_weather() -> dict:
    """call api and return json response as dict"""
    response = requests.get(API_URL, params=PARAMS, timeout=10)
    response.raise_for_status()
    return response.json()


def save_json(payload: dict, path: Path = OUTPUT_PATH) -> None:
    """write payload to disk formatted as json"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    logger.info("Saved payload to %s", path)


if __name__ == "__main__":
    try:
        save_json(fetch_weather())
    except requests.RequestException:
        logger.exception("Failed to fetch weather data")
        raise SystemExit(1) from None
