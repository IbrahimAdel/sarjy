from __future__ import annotations

from pydantic import BaseModel


class CurrentWeatherResponse(BaseModel):
    class CurrentWeatherUnits(BaseModel):
        time: str
        interval: str
        temperature: str
        windspeed: str
        winddirection: str
        is_day: str
        weathercode: str

    class CurrentWeather(BaseModel):
        time: str
        interval: int
        temperature: float
        windspeed: float
        winddirection: int
        is_day: int
        weathercode: int

    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str
    elevation: float
    current_weather_units: CurrentWeatherUnits
    current_weather: CurrentWeather
