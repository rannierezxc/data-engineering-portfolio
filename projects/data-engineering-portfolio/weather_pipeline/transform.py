"""turn the api's 'parallel lists' shape into one flat row per city per hour"""

from datetime import UTC

from weather_pipeline.config import City
from weather_pipeline.models import WeatherReading, WeatherResponse


def to_readings(city: City, response: WeatherResponse) -> list[WeatherReading]:
    hourly = response.hourly
    readings: list[WeatherReading] = []
    for ts, temp, humidity, rain, wind in zip(
        hourly.time,
        hourly.temperature_2m,
        hourly.relative_humidity_2m,
        hourly.precipitation,
        hourly.wind_speed_10m,
        strict=True,
    ):
        readings.append(
            WeatherReading(
                city=city.name,
                latitude=city.latitude,
                longitude=city.longitude,
                reading_time=ts.replace(tzinfo=UTC),
                temperature_c=temp,
                humidity_pct=humidity,
                precipitation_mm=rain,
                wind_speed_kmh=wind,
            )
        )  # we use WeatherReading as list so that every
        # single item/row is validated since it is pydantic model
    return readings
