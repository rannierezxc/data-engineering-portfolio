"""statis configuration: which cities to fetch, which api to call, where files go"""

from dataclasses import dataclass
from pathlib import Path

API_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]

REQUEST_TIMEOUT_SECONDS = 10
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOG_DIR = Path("logs")


@dataclass(frozen=True)
class City:
    name: str
    country: str
    region: str
    latitude: float
    longitude: float
    timezone: str


CITIES: list[City] = [
    City("Manila", "Philippines", "Metro Manila", 14.5995, 120.9842, "Asia/Manila"),
    City("Cebu", "Philippines", "Centra Visayas", 10.3157, 123.8854, "Asia/Manila"),
    City("Davao", "Philippines", "Davao Region", 7.1907, 125.4553, "Asia/Manila"),
    City("Singapore", "Singapore", "Cnetral", 1.3521, 103.8198, "Asia/Singapore"),
    City("Tokyo", "Japan", "Kanto", 35.6762, 139.6503, "Asia/Tokyo"),
]
