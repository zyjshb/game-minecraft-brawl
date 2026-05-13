import math
import random
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pygame

SEASON_CHAR_KEYS = {"spring": "season_spring", "summer": "season_summer", "autumn": "season_autumn", "winter": "season_winter"}


def get_season_char(season_key):
    from i18n import t
    k = SEASON_CHAR_KEYS.get(season_key, season_key)
    return t(k)


SEASON_COLORS = {
    "spring": (100, 255, 120),
    "summer": (255, 100, 80),
    "autumn": (255, 200, 60),
    "winter": (150, 210, 255),
}
SEASON_GLOW = {
    "spring": (60, 200, 80),
    "summer": (220, 70, 50),
    "autumn": (220, 160, 40),
    "winter": (100, 180, 240),
}
SEASON_VIGNETTE = {
    "spring": (20, 60, 25),
    "summer": (60, 20, 15),
    "autumn": (50, 35, 15),
    "winter": (20, 30, 45),
}


class SeasonEffect:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.life = 0

    def update(self):
        pass

    def draw(self, surface):
        pass
