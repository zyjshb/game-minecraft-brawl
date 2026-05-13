import os
import math

import pygame

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")


class EnchantAltar:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.active = True
        self.glow_timer = 0
        self._img = None
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "耄耋附魔架.png")).convert_alpha()
            self._img = pygame.transform.scale(raw, (48, 48))
        except Exception:
            self._img = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.rect(self._img, (255, 215, 0, 200), (0, 0, 48, 48), border_radius=8)
            pygame.draw.circle(self._img, (255, 255, 200, 150), (24, 24), 14)

    def update(self):
        self.glow_timer += 1

    def draw(self, surface):
        if not self.active:
            return
        pulse = int(abs(math.sin(self.glow_timer * 0.06)) * 40 + 20)
        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 215, 0, pulse), (30, 30), 26)
        pygame.draw.circle(glow, (255, 255, 180, pulse // 2), (30, 30), 20)
        surface.blit(glow, (self.rect.centerx - 30, self.rect.centery - 30))
        if self._img:
            r = self._img.get_rect(center=self.rect.center)
            surface.blit(self._img, r)
