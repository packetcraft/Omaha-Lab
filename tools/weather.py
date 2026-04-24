import os
import requests
from langchain_core.tools import tool

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns temperature (°F), conditions, humidity, and wind speed."""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Error: WEATHER_API_KEY is not set. Add it to your .env file."

    try:
        resp = requests.get(
            _BASE_URL,
            params={"q": city, "appid": api_key, "units": "imperial"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == 404:
            return f"City not found: '{city}'. Check the spelling or try a nearby city."
        if code == 401:
            return "Invalid WEATHER_API_KEY. Check your .env file."
        return f"Weather API error {code}: {exc}"
    except requests.RequestException as exc:
        return f"Network error fetching weather: {exc}"

    data = resp.json()
    name = data.get("name", city)
    country = data.get("sys", {}).get("country", "")
    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    description = data["weather"][0]["description"].capitalize()
    wind = data["wind"]["speed"]

    return (
        f"Location:    {name}, {country}\n"
        f"Temperature: {temp}°F (feels like {feels}°F)\n"
        f"Condition:   {description}\n"
        f"Humidity:    {humidity}%\n"
        f"Wind:        {wind} mph"
    )
