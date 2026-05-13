import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

TIME_LABELS = [
    (0.00, "time_midnight"),
    (0.08, "time_early_morning"),
    (0.17, "time_dawn"),
    (0.25, "time_morning"),
    (0.35, "time_late_morning"),
    (0.50, "time_noon"),
    (0.60, "time_afternoon"),
    (0.73, "time_dusk"),
    (0.82, "time_night"),
    (0.92, "time_late_night"),
]

_sky_time_font = None


def _get_time_font():
    global _sky_time_font
    if _sky_time_font is None:
        try:
            from config import get_font
            _sky_time_font = get_font(20)
        except Exception:
            _sky_time_font = pygame.font.Font(None, 20)
    return _sky_time_font


def _get_time_key(t):
    key = TIME_LABELS[0][1]
    for threshold, label in TIME_LABELS:
        if t >= threshold:
            key = label
    return key


def draw_celestial(surface, t, is_night, x, y, season=""):
    if not is_night:
        pygame.draw.circle(surface, (255, 240, 100), (x, y), 28)
        pygame.draw.circle(surface, (255, 250, 200), (x, y), 20)
        pygame.draw.circle(surface, (255, 255, 230), (x, y), 14)
    else:
        pygame.draw.circle(surface, (220, 225, 240), (x, y), 24)
        pygame.draw.circle(surface, (235, 238, 248), (x, y), 16)
        shadow = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (15, 20, 45, 180), (5, 15), 13)
        surface.blit(shadow, (x - 5, y - 15))
    _draw_time_label(surface, t, x, y + 42, season)


def draw_celestial_compact(surface, t, is_night, x, y):
    if not is_night:
        pygame.draw.circle(surface, (255, 240, 100), (x, y), 24)
        pygame.draw.circle(surface, (255, 250, 200), (x, y), 18)
        pygame.draw.circle(surface, (255, 255, 230), (x, y), 12)
    else:
        pygame.draw.circle(surface, (220, 225, 240), (x, y), 20)
        pygame.draw.circle(surface, (235, 238, 248), (x, y), 14)
        shadow = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (15, 20, 45, 180), (4, 13), 11)
        surface.blit(shadow, (x - 4, y - 13))


def _draw_time_label(surface, t, x, y, season=""):
    from i18n import t as _t
    font = _get_time_font()
    name = _t(_get_time_key(t))
    txt = font.render(name, True, (255, 255, 255))
    txt.set_alpha(200)
    r = txt.get_rect(center=(x, y))
    surface.blit(txt, r)
