"""
天气系统兼容入口。

说明：
- 原先所有天气代码集中在本文件。
- 现已按项目架构拆分到 `Ditu/weather/` 子模块。
- 为了不影响现有 import（如 `from .weather_system import WeatherSystem`），
  该文件保留并转发同名公开接口。
"""

from .weather import (
    DESERT_FORBIDDEN,
    SEASON_NAMES,
    SEASON_WEATHER_POOLS,
    TIME_SKY_COLORS,
    WEATHER_CONFIGS,
    WEATHER_NAMES,
    WeatherSystem,
    WeatherType,
)

__all__ = [
    "WeatherType",
    "WEATHER_NAMES",
    "SEASON_WEATHER_POOLS",
    "SEASON_NAMES",
    "DESERT_FORBIDDEN",
    "WEATHER_CONFIGS",
    "TIME_SKY_COLORS",
    "WeatherSystem",
]
