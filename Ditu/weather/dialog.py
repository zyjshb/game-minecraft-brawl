import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from i18n import get_text

WEATHER_KEYS = {
    0: "sunny", 1: "cloudy", 2: "overcast",
    3: "light_rain", 4: "moderate_rain", 5: "heavy_rain",
    6: "thunderstorm", 7: "light_snow", 8: "moderate_snow",
    9: "heavy_snow", 10: "fog", 11: "sandstorm",
}


class _WeatherBubbleDict(dict):
    def __getitem__(self, key):
        k = WEATHER_KEYS.get(key.value if hasattr(key, 'value') else key, str(key))
        return get_text("weather_bubble", k)


class _WeatherSameDict(dict):
    def __getitem__(self, key):
        k = WEATHER_KEYS.get(key.value if hasattr(key, 'value') else key, str(key))
        return get_text("weather_same", k)

    def get(self, key, default=None):
        k = WEATHER_KEYS.get(key.value if hasattr(key, 'value') else key, str(key))
        return get_text("weather_same", k)


WEATHER_BUBBLE_TEXT = _WeatherBubbleDict()
WEATHER_SAME_LINES = _WeatherSameDict()
