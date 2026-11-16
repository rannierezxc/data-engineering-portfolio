from datetime import UTC, datetime

from weather_pipeline.models import WeatherResponse
from weather_pipeline.transform import to_readings


def test_one_reading_per_hours(manila, sample_payload):
    readings = to_readings(manila, WeatherResponse.model_validate(sample_payload))

    assert len(readings) == 3
    first = readings[0]
    assert first.city == "Manila"
    assert first.reading_time == datetime(2026, 11, 10, 0, 0, tzinfo=UTC)
    assert first.temperature_c == 27.1
    assert first.precipitation_mm == 0.0


def test_missing_values_stay_missing(manila, sample_payload):
    readings = to_readings(manila, WeatherResponse.model_validate(sample_payload))
    assert readings[2].temperature_c is None
