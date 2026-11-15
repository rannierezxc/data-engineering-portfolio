"""shared test fixtures: fake data we can reuse in every test file"""

from typing import Any

import pytest

from weather_pipeline.config import City


@pytest.fixture
def manila() -> City:
    return City("Manila", "Philippines", "Metro Manila", 14.5995, 120.9842, "Asial/Manila")


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    """A tiny, realistic copy of what Open-Meteo returns (3 hours instead of 24)."""
    return {
        "latitude": 14.6,
        "longitude": 121.0,
        "timezone": "GMT",
        "hourly": {
            "time": ["2026-11-10T00:00", "2026-11-10T01:00", "2026-11-10T02:00"],
            "temperature_2m": [27.1, 26.8, None],
            "relative_humidity_2m": [80, 82, 85],
            "precipitation": [0.0, 0.2, 1.4],
            "wind_speed_10m": [8.5, 7.9, 6.0],
        },
    }
