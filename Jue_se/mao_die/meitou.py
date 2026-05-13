import pygame
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import get_font
from i18n import get_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_MATERIALS_DIR = os.path.join(BASE_DIR, "Sound effects materials")

_meitou_img = None
_meitou_sfx = None


def get_meitou_image():
    global _meitou_img
    if _meitou_img is None:
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "名刀.png")).convert_alpha()
            _meitou_img = pygame.transform.scale(raw, (80, 80))
        except Exception:
            _meitou_img = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.rect(_meitou_img, (200, 180, 255, 200), (10, 10, 60, 60))
    return _meitou_img


def get_meitou_sfx():
    global _meitou_sfx
    if _meitou_sfx is None:
        try:
            _meitou_sfx = pygame.mixer.Sound(os.path.join(SFX_MATERIALS_DIR, "名刀破碎.mp3"))
        except Exception:
            _meitou_sfx = None
    return _meitou_sfx


class MeitouEffect:
    _MEITOU_COLORS = [
        (180, 80, 220),
        (140, 100, 240),
        (200, 140, 250),
        (120, 80, 210),
        (220, 180, 255),
        (255, 200, 50),
        (160, 60, 200),
        (100, 150, 240),
        (190, 120, 230),
        (240, 200, 255),
        (130, 70, 180),
        (170, 110, 250),
    ]

    def __init__(self, target):
        self._target = target
        self.life = 70
        self.max_life = 70
        self.scale = 0.0
        self.image = get_meitou_image()
        self._base_w = self.image.get_width()
        self._base_h = self.image.get_height()
        self._particles = []
        self._burst = False

    @property
    def x(self):
        return self._target.rect.centerx

    @property
    def y(self):
        return self._target.rect.centery

    def update(self):
        self.life -= 1

        if not self._burst and self.life <= 52:
            self._burst = True
            self._spawn_burst()

        if not self._burst:
            t = 1.0 - (self.max_life - self.life) / 18.0
            self.scale = max(0.0, min(1.0, t))

        for p in self._particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.96
            p['vy'] *= 0.96
            p['vy'] += 0.15
            p['life'] -= 1
            if p['life'] <= 0:
                self._particles.remove(p)

    def _spawn_burst(self):
        import random
        for _ in range(28):
            angle = random.uniform(0, 6.2832)
            speed = random.uniform(2.5, 8.0)
            self._particles.append({
                'x': float(self.x),
                'y': float(self.y),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(18, 45),
                'max_life': 45,
                'color': random.choice(self._MEITOU_COLORS),
                'size': random.randint(4, 12),
            })

    @property
    def is_done(self):
        return self.life <= 0 and len(self._particles) == 0

    def draw(self, surface):
        if self.life <= 0 and len(self._particles) == 0:
            return

        if not self._burst:
            alpha = int(255 * min(1.0, (self.max_life - self.life) / 12.0))
            if alpha > 0:
                w = max(4, int(self._base_w * self.scale))
                h = max(4, int(self._base_h * self.scale))
                scaled = pygame.transform.smoothscale(self.image, (w, h))
                scaled.set_alpha(alpha)
                r = scaled.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(scaled, r)

        for p in self._particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            if alpha <= 0:
                continue
            s = p['size']
            ps = pygame.Surface((s, s), pygame.SRCALPHA)
            ps.fill((*p['color'], alpha))
            surface.blit(ps, (int(p['x'] - s // 2), int(p['y'] - s // 2)))


class MeitouDialog:
    def __init__(self, target):
        self._target = target
        self.life = 150
        self.max_life = 150
        self.text = get_text("meitou")
        self._font = get_font(22)
        self._alpha = 0

    @property
    def x(self):
        return self._target.rect.centerx

    @property
    def y(self):
        return self._target.rect.centery

    def update(self):
        self.life -= 1
        progress = self.life / self.max_life
        if progress > 0.85:
            self._alpha = int(255 * (1.0 - progress) / 0.15)
        elif progress < 0.25:
            self._alpha = int(255 * progress / 0.25)
        else:
            self._alpha = 255

    @property
    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0 or self._alpha <= 0:
            return

        text_surf = self._font.render(self.text, True, (255, 220, 80))
        text_surf.set_alpha(self._alpha)

        shadow = self._font.render(self.text, True, (0, 0, 0))
        shadow.set_alpha(self._alpha // 2)

        tw = text_surf.get_width()
        th = text_surf.get_height()

        padding = 12
        bubble_w = tw + padding * 2
        bubble_h = th + padding * 2

        bubble = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
        bubble_rect = bubble.get_rect()
        pygame.draw.rect(bubble, (30, 20, 10, int(self._alpha * 0.85)),
                         bubble_rect, border_radius=14)
        pygame.draw.rect(bubble, (200, 160, 40, int(self._alpha * 0.6)),
                         bubble_rect, width=2, border_radius=14)

        tail_h = 12
        tail_w = 10
        tail_x = bubble_w // 2 - tail_w // 2 + 20
        tail_points = [
            (tail_x, bubble_h),
            (tail_x + tail_w // 2, bubble_h + tail_h),
            (tail_x + tail_w, bubble_h),
        ]
        pygame.draw.polygon(bubble, (30, 20, 10, int(self._alpha * 0.85)), tail_points)
        pygame.draw.polygon(bubble, (200, 160, 40, int(self._alpha * 0.6)), tail_points, width=1)

        bx = int(self.x) - bubble_w // 2
        by = int(self.y) - bubble_h - tail_h - 50

        surface.blit(bubble, (bx, by))
        surface.blit(shadow, (bx + padding + 2, by + padding + 2))
        surface.blit(text_surf, (bx + padding, by + padding))
