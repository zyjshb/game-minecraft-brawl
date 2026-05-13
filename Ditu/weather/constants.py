class WeatherType:
    SUNNY = 0
    CLOUDY = 1
    OVERCAST = 2
    LIGHT_RAIN = 3
    MODERATE_RAIN = 4
    HEAVY_RAIN = 5
    THUNDERSTORM = 6
    LIGHT_SNOW = 7
    MODERATE_SNOW = 8
    HEAVY_SNOW = 9
    FOG = 10
    SANDSTORM = 11


WEATHER_NAMES = {
    WeatherType.SUNNY: "晴天",
    WeatherType.CLOUDY: "多云",
    WeatherType.OVERCAST: "阴天",
    WeatherType.LIGHT_RAIN: "小雨",
    WeatherType.MODERATE_RAIN: "中雨",
    WeatherType.HEAVY_RAIN: "大雨",
    WeatherType.THUNDERSTORM: "雷暴雨",
    WeatherType.LIGHT_SNOW: "小雪",
    WeatherType.MODERATE_SNOW: "中雪",
    WeatherType.HEAVY_SNOW: "大雪",
    WeatherType.FOG: "大雾",
    WeatherType.SANDSTORM: "沙尘暴",
}

SEASON_WEATHER_POOLS = {
    "spring": [
        WeatherType.SUNNY, WeatherType.SUNNY,
        WeatherType.CLOUDY, WeatherType.CLOUDY,
        WeatherType.OVERCAST,
        WeatherType.LIGHT_RAIN, WeatherType.MODERATE_RAIN,
        WeatherType.FOG,
    ],
    "summer": [
        WeatherType.SUNNY,
        WeatherType.CLOUDY,
        WeatherType.OVERCAST,
        WeatherType.LIGHT_RAIN,
        WeatherType.MODERATE_RAIN,
        WeatherType.HEAVY_RAIN, WeatherType.HEAVY_RAIN,
        WeatherType.THUNDERSTORM, WeatherType.THUNDERSTORM, WeatherType.THUNDERSTORM,
    ],
    "autumn": [
        WeatherType.SUNNY,
        WeatherType.CLOUDY, WeatherType.CLOUDY,
        WeatherType.OVERCAST, WeatherType.OVERCAST,
        WeatherType.LIGHT_RAIN, WeatherType.MODERATE_RAIN,
        WeatherType.FOG, WeatherType.FOG, WeatherType.FOG,
    ],
    "winter": [
        WeatherType.SUNNY, WeatherType.CLOUDY,
        WeatherType.OVERCAST, WeatherType.OVERCAST,
        WeatherType.LIGHT_SNOW, WeatherType.LIGHT_SNOW,
        WeatherType.MODERATE_SNOW, WeatherType.MODERATE_SNOW,
        WeatherType.HEAVY_SNOW, WeatherType.HEAVY_SNOW,
        WeatherType.FOG,
    ],
}

SEASON_NAMES = {"spring": "春季", "summer": "夏季", "autumn": "秋季", "winter": "冬季"}

DESERT_FORBIDDEN = {
    WeatherType.LIGHT_RAIN, WeatherType.MODERATE_RAIN, WeatherType.HEAVY_RAIN,
    WeatherType.THUNDERSTORM, WeatherType.LIGHT_SNOW, WeatherType.MODERATE_SNOW,
    WeatherType.HEAVY_SNOW,
}

WEATHER_CONFIGS = {
    WeatherType.SUNNY: {
        "cloud_alpha": 0, "fog_alpha": 0, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 0, "snow_speed": 0,
        "wind": 0, "lightning_chance": 0,
    },
    WeatherType.CLOUDY: {
        "cloud_alpha": 50, "fog_alpha": 0, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 0, "snow_speed": 0,
        "wind": 0.4, "lightning_chance": 0,
    },
    WeatherType.OVERCAST: {
        "cloud_alpha": 150, "fog_alpha": 10, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 0, "snow_speed": 0,
        "wind": 0.8, "lightning_chance": 0,
    },
    WeatherType.LIGHT_RAIN: {
        "cloud_alpha": 120, "fog_alpha": 20, "sand_alpha": 0,
        "rain_density": 50, "rain_speed": 16, "rain_angle": 8,
        "snow_density": 0, "snow_speed": 0,
        "wind": 1.2, "lightning_chance": 0,
    },
    WeatherType.MODERATE_RAIN: {
        "cloud_alpha": 165, "fog_alpha": 40, "sand_alpha": 0,
        "rain_density": 130, "rain_speed": 20, "rain_angle": 14,
        "snow_density": 0, "snow_speed": 0,
        "wind": 2.0, "lightning_chance": 0,
    },
    WeatherType.HEAVY_RAIN: {
        "cloud_alpha": 200, "fog_alpha": 60, "sand_alpha": 0,
        "rain_density": 260, "rain_speed": 24, "rain_angle": 17,
        "snow_density": 0, "snow_speed": 0,
        "wind": 3.0, "lightning_chance": 0,
    },
    WeatherType.THUNDERSTORM: {
        "cloud_alpha": 230, "fog_alpha": 70, "sand_alpha": 0,
        "rain_density": 340, "rain_speed": 27, "rain_angle": 19,
        "snow_density": 0, "snow_speed": 0,
        "wind": 4.0, "lightning_chance": 0.003,
    },
    WeatherType.LIGHT_SNOW: {
        "cloud_alpha": 90, "fog_alpha": 10, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 30, "snow_speed": 1.5,
        "wind": 0.6, "lightning_chance": 0,
    },
    WeatherType.MODERATE_SNOW: {
        "cloud_alpha": 135, "fog_alpha": 25, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 85, "snow_speed": 2.2,
        "wind": 1.2, "lightning_chance": 0,
    },
    WeatherType.HEAVY_SNOW: {
        "cloud_alpha": 180, "fog_alpha": 45, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 190, "snow_speed": 2.8,
        "wind": 2.0, "lightning_chance": 0,
    },
    WeatherType.FOG: {
        "cloud_alpha": 45, "fog_alpha": 140, "sand_alpha": 0,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 0, "snow_speed": 0,
        "wind": 0.2, "lightning_chance": 0,
    },
    WeatherType.SANDSTORM: {
        "cloud_alpha": 30, "fog_alpha": 0, "sand_alpha": 150,
        "rain_density": 0, "rain_speed": 0, "rain_angle": 0,
        "snow_density": 0, "snow_speed": 0,
        "wind": 5.0, "lightning_chance": 0,
    },
}

# 一天中各时段的天空渐变 (top, bottom)
TIME_SKY_COLORS = [
    ((10, 15, 45), (25, 35, 70)),
    ((20, 28, 65), (50, 45, 95)),
    ((55, 45, 95), (90, 70, 130)),
    ((110, 75, 110), (170, 110, 150)),
    ((190, 140, 120), (210, 190, 170)),
    ((175, 195, 225), (195, 215, 235)),
    ((130, 200, 230), (155, 210, 238)),
    ((118, 190, 225), (145, 200, 233)),
    ((125, 185, 220), (155, 200, 230)),
    ((175, 165, 195), (195, 185, 215)),
    ((215, 135, 95), (235, 175, 135)),
    ((155, 75, 95), (175, 95, 125)),
    ((55, 25, 75), (75, 35, 105)),
]
