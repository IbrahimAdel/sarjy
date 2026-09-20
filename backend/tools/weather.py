from httpx2 import AsyncClient

from tools.schemas import CurrentWeatherResponse

WEATHER_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Fetch current weather for a city using Open-Meteo API.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
                "city_name": {"type": "string", "description": "City name for display"},
            },
            "required": ["latitude", "longitude", "city_name"],
        },
    },
}

MEMORY_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "save_preference",
        "description": "Save or update a user preference, habit, or fact (e.g., favorite color, home city).",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Preference key e.g. city",
                },
                "value": {
                    "type": "string",
                    "description": "Preference value e.g. London",
                },
            },
            "required": ["key", "value"],
        },
    },
}


class WeatherService:
    client: AsyncClient = AsyncClient(
        base_url="https://api.open-meteo.com",
        headers={
            "Content-Type": "application/json",
            "Connection": "keep-alive",
        },
    )

    def __init__(self):
        raise Exception("WeatherService cannot be instantiated")  # noqa: TRY002

    @classmethod
    async def get_current_weather(
        cls,
        latitude: float,
        longitude: float,
        city_name: str,
    ) -> str:
        response = CurrentWeatherResponse.model_validate_json(
            (
                await cls.client.get(
                    url="v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current_weather": True,
                    },
                )
            )
            .raise_for_status()
            .content
        )
        temp = response.current_weather.temperature
        wind = response.current_weather.windspeed
        temp_unit = response.current_weather_units.temperature
        wind_unit = response.current_weather_units.windspeed
        return f"Current weather in {city_name}: {temp}{temp_unit}, Wind speed: {wind} {wind_unit}."
