"""pydantic models = data contracts. If the api sends grabage, we fail loudly here"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

MEASUREMENT_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
)


class HourlyBlock(BaseModel):
    """the hourly  part of the open-meteo response: parallel lists, one item per hour."""

    time: list[datetime]
    temperature_2m: list[float | None]
    relative_humidity_2m: list[float | None]
    precipitation: list[float | None]
    wind_speed_10m: list[float | None]

    @model_validator(mode="after")
    def check_lists_line_up(self) -> "HourlyBlock":
        expected = len(self.time)
        if expected == 0:
            raise ValueError("API returned no hourly readings")
        for field_name in MEASUREMENT_FIELDS:
            actual = len(getattr(self, field_name))
            if actual != expected:
                raise ValueError(f"'{field_name}' has {actual} values but 'time' has {expected}")
        return self


class WeatherResponse(BaseModel):
    """the whole api response. Extra fields we dont list are ignored"""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str
    hourly: HourlyBlock


class WeatherReading(BaseModel):
    """one clean, flat row: one city, one hour"""

    city: str
    latitude: float
    longitude: float
    reading_time: datetime
    temperature_c: float | None = Field(default=None, ge=-90, le=60)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    precipitation_mm: float | None = Field(default=None, ge=0)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
