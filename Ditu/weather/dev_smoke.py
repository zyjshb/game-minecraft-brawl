"""
Minimal smoke test for the weather module.

Run:
    python -m Ditu.weather.dev_smoke
"""

import os

import pygame

from .system import WeatherSystem


def run_smoke(frames=30):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))

    width, height = 960, 540
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    ws = WeatherSystem(width, height, map_path="", is_desert=False)

    for _ in range(frames):
        ws.update()
        ws.draw_bottom(surface)
        ws.draw_top(surface)

    ws.destroy()
    pygame.quit()
    print(f"weather smoke ok ({frames} frames)")


if __name__ == "__main__":
    run_smoke()
