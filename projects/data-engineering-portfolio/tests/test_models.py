"""
does the quality gate work?

"""

import pytest
from pydantic import ValidationError

from weather_pipeline.models import WeatherReading, WeatherResponse


def test_valid_payload_is_parsed(sample_payload):
    parsed = WeatherResponse.model_validate(sample_payload)
    assert len(parsed.hourly.time) == 3
    assert parsed.hourly.temperature_2m[2] is None


def test_mismatched_list_lengths_are_rejected(sample_payload):
    sample_payload["hourly"]["temperature_2m"].pop()  # now only 2 temps for 3hrs
    with pytest.raises(ValidationError, match="temperature_2m"):
        WeatherResponse.model_validate(sample_payload)


def test_missing_hourly_block_is_rejected(sample_payload):
    del sample_payload["hourly"]
    with pytest.raises(ValidationError):
        WeatherResponse.model_validate(sample_payload)


@pytest.mark.parametrize("bad_humidity", [-1, 101, 250])
def test_impossible_humidity_is_rejected(bad_humidity):
    with pytest.raises(ValidationError):
        WeatherReading(
            city="Manila",
            latitude=14.6,
            longitude=121.0,
            reading_time="2026-11-10T00:00:00Z",
            humidity_pct=bad_humidity,
        )


# pytest.raises(,..) - this code should fail with this error. If it doesnt fail, the test fails.
# @pytest.mark.parametrize - runs the same test three times, with -1, 101, and 250.
