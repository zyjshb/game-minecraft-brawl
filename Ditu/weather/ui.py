import math
import random as _rnd

import pygame

from .constants import WeatherType


def draw_weather_icon(surface, weather, cx, cy, big=False):
    wt = weather.current_weather
    half = 18 if big else 14
    scale = 1.1 if big else 1.0

    if wt == WeatherType.SUNNY:
        r = int((half - 2) * scale)
        pygame.draw.circle(surface, (255, 220, 80), (cx, cy), r)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            sx = cx + math.cos(rad) * (r - 3)
            sy = cy + math.sin(rad) * (r - 3)
            ex = cx + math.cos(rad) * (r + 3)
            ey = cy + math.sin(rad) * (r + 3)
            pygame.draw.line(surface, (255, 220, 80), (sx, sy), (ex, ey), int(2 * scale))

    elif wt in (WeatherType.CLOUDY, WeatherType.OVERCAST):
        cc = (190, 190, 200) if wt == WeatherType.CLOUDY else (140, 140, 155)
        clouds = [(0, 0, int(10*scale)), (-6, 3, int(9*scale)), (7, -1, int(12*scale)), (-8, -1, int(8*scale)), (8, 3, int(9*scale))]
        for ox, oy, r in clouds:
            pygame.draw.circle(surface, cc, (cx + ox, cy + oy), r)
            hl = tuple(min(c + 40, 255) for c in cc)
            pygame.draw.circle(surface, hl, (cx + ox, cy + oy - 2), max(1, r - 3))

    elif wt in (WeatherType.LIGHT_RAIN, WeatherType.MODERATE_RAIN, WeatherType.HEAVY_RAIN, WeatherType.THUNDERSTORM):
        for ox, oy, r in [(-5, -2, 9), (5, 0, 10), (0, -6, 8)]:
            r2 = int(r * scale)
            pygame.draw.circle(surface, (140, 145, 165), (cx + int(ox*scale), cy + int(oy*scale) - 4), r2)
        drops = 6 if (wt == WeatherType.HEAVY_RAIN or wt == WeatherType.THUNDERSTORM) else 4
        for i in range(drops):
            dx = cx - 12 + i * 8
            dy = cy + 5
            pygame.draw.line(surface, (130, 180, 220), (dx, dy), (dx - 1, dy + 7), int(2*scale))
        if wt == WeatherType.THUNDERSTORM:
            lx, ly = cx, cy - 16
            pts = [(lx, ly - 7), (lx + 5, ly + 3), (lx + 2, ly + 1), (lx + 7, ly + 12), (lx - 4, ly + 2), (lx + 2, ly)]
            pygame.draw.polygon(surface, (255, 240, 100), pts)

    elif wt in (WeatherType.LIGHT_SNOW, WeatherType.MODERATE_SNOW, WeatherType.HEAVY_SNOW):
        for ox, oy, r in [(-5, -2, 9), (5, 0, 10), (0, -6, 8)]:
            r2 = int(r * scale)
            pygame.draw.circle(surface, (185, 190, 210), (cx + int(ox*scale), cy + int(oy*scale) - 4), r2)
        count = 6 if wt == WeatherType.HEAVY_SNOW else 4
        for i in range(count):
            sx = cx - 12 + i * 8
            sy = cy + 5 + (i % 2) * 3
            pygame.draw.circle(surface, (245, 250, 255), (sx, sy), int(2*scale))

    elif wt == WeatherType.FOG:
        for i in range(4):
            ly = cy - 5 + i * 7
            alpha = 110 - i * 20
            s = pygame.Surface((50, int(3*scale)), pygame.SRCALPHA)
            s.fill((190, 190, 195, alpha))
            surface.blit(s, (cx - 25, ly))

    elif wt == WeatherType.SANDSTORM:
        for i in range(8):
            sx = cx - 12 + i * 5
            sy = cy - 6 + _rnd.randint(0, 14)
            pygame.draw.circle(surface, (215, 180, 105), (sx, sy), int(2*scale))


class WeatherAlertBanner:
    def __init__(self, w):
        self.w = w
        self.h = 72
        self.y = -self.h
        self.text = ""
        self.alpha = 0
        self.timer = 0
        self.active = False
        self._font = None
        self._season_font = None

    def _ensure_font(self):
        if self._font is None:
            try:
                from config import get_font

                self._font = get_font(32)
                self._season_font = get_font(36)
            except Exception:
                self._font = pygame.font.Font(None, 32)
                self._season_font = pygame.font.Font(None, 36)

    def show(self, text, is_season=False):
        self._ensure_font()
        self.text = text
        self.y = -self.h
        self.alpha = 0
        self.timer = 160
        self.active = True
        self.is_season = is_season

    def update(self):
        if not self.active:
            return
        if self.timer > 115:
            self.y += (0 - self.y) * 0.12
            self.alpha = min(230, self.alpha + 10)
        elif self.timer > 45:
            self.alpha = 220
        else:
            self.alpha = max(0, self.alpha - 8)
            if self.timer <= 0:
                self.y = -self.h
                self.active = False
        self.timer -= 1

    def draw(self, surface):
        if not self.active or self.alpha <= 0 or self._font is None:
            return
        banner = pygame.Surface((self.w, self.h + 16), pygame.SRCALPHA)
        banner.fill((8, 10, 20, min(190, self.alpha + 35)))
        py = max(0, int(self.y))
        surface.blit(banner, (0, py - 8))

        font = self._season_font if getattr(self, "is_season", False) else self._font
        txt = font.render(self.text, True, (240, 230, 200))
        txt.set_alpha(min(255, self.alpha + 50))
        r = txt.get_rect(center=(self.w // 2, py + self.h // 2))
        surface.blit(txt, r)

        line_y = py + self.h
        pygame.draw.line(
            surface,
            (180, 160, 100, min(255, self.alpha)),
            (80, line_y),
            (self.w - 80, line_y),
            2,
        )
