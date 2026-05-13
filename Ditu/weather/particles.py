import math
import random

import pygame

from .resources import get_sprite_path


class RainParticle:
    def __init__(self, x, y, speed, angle):
        self.x = x
        self.y = y
        self.speed = speed
        self.angle = angle
        rad = math.radians(angle)
        self.vx = math.sin(rad) * speed * 0.3
        self.vy = speed
        self.length = random.uniform(6, 14)
        self.alpha = random.randint(130, 240)

    def update(self, bw, bh, wind):
        self.x += self.vx + wind * 0.5
        self.y += self.vy
        if self.x < -40 or self.x > bw + 40 or self.y > bh + 40:
            self.y = random.uniform(-40, -5)
            self.x = random.uniform(-40, bw + 40)

    def draw(self, surface):
        ex = self.x - self.vx * 0.2
        ey = self.y - self.length
        c = (190, 210, 245, self.alpha)
        pygame.draw.line(surface, c, (self.x, self.y), (ex, ey), 2)


class SnowParticle:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed
        self.size = random.randint(2, 5)
        self.alpha = random.randint(160, 255)
        self.sway = random.uniform(-0.5, 0.5)
        self.phase_speed = random.uniform(0.02, 0.05)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, bw, bh, wind):
        self.phase += self.phase_speed
        self.x += math.sin(self.phase) * 0.5 + wind * 0.25 + self.sway
        self.y += self.speed
        if self.x < -20 or self.x > bw + 20 or self.y > bh + 20:
            self.y = random.uniform(-15, -3)
            self.x = random.uniform(0, bw)
            self.phase = random.uniform(0, math.pi * 2)

    def draw(self, surface):
        c = (255, 255, 255, self.alpha)
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), self.size)


class CloudOverlay:
    def __init__(self, w, h):
        self.surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self.w = w
        self.h = h
        self._cloud_data = []
        for _ in range(random.randint(8, 14)):
            cx = random.randint(0, w)
            cy = random.randint(0, h // 3)
            r = random.randint(60, 160)
            a = random.randint(18, 50)
            n = random.randint(3, 6)
            blobs = []
            for _ in range(n):
                ox = random.randint(-r // 2, r // 2)
                oy = random.randint(-12, 12)
                or2 = random.randint(r // 5, r // 3)
                blobs.append((ox, oy, or2))
            self._cloud_data.append((cx, cy, a, blobs))

    def draw(self, surface, alpha):
        if alpha <= 0:
            return
        self.surface.fill((0, 0, 0, 0))
        for cx, cy, a, blobs in self._cloud_data:
            for ox, oy, or2 in blobs:
                rect = (cx + ox - or2, cy + oy - or2 // 2, or2 * 2, or2)
                pygame.draw.ellipse(self.surface, (255, 255, 255, a), rect)
        self.surface.set_alpha(min(255, alpha))
        surface.blit(self.surface, (0, 0))


class SandParticle:
    def __init__(self, x, y, wind):
        self.x = x
        self.y = y
        self.size = random.randint(1, 3)
        self.vx = wind * random.uniform(0.5, 1.3)
        self.vy = random.uniform(-1.2, 0.8)
        self.life = random.randint(20, 55)

    def update(self, bw, bh, wind):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.x < -30 or self.x > bw + 30 or self.y < -30 or self.y > bh + 30 or self.life <= 0:
            self.x = random.uniform(-30, bw + 30)
            self.y = random.uniform(-10, bh + 10)
            self.life = random.randint(20, 55)
            self.vx = wind * random.uniform(0.5, 1.3)

    def draw(self, surface):
        if self.life > 0:
            a = min(180, self.life * 4)
            c = (210, 175, 105, a)
            pygame.draw.circle(surface, c, (int(self.x), int(self.y)), self.size)


class Torch:
    MAX_TORCHES = 4

    def __init__(self, x, y, sprite_name="火把.png"):
        self.rect = pygame.Rect(x, y, 30, 40)
        self.size = 30
        self.active = True
        self.light_radius = 200
        self.flicker = random.uniform(0, math.pi * 2)
        self.blocked_timer = 0
        self.sprite_name = sprite_name
        self.has_collision = "海晶灯" in sprite_name
        try:
            raw = pygame.image.load(get_sprite_path(sprite_name)).convert_alpha()
            w = 20 if "火把" in sprite_name else 28
            h = 40 if "火把" in sprite_name else 36
            self.image = pygame.transform.scale(raw, (w, h))
        except Exception:
            self.image = pygame.Surface((16, 32))
            self.image.fill((200, 150, 50))
            pygame.draw.rect(self.image, (100, 60, 20), (4, 24, 8, 8))

    def update(self):
        self.flicker += 0.15
        if self.blocked_timer > 0:
            self.blocked_timer -= 1

    def draw(self, surface):
        if not self.active or self.blocked_timer > 0:
            return
        if self.image:
            img_rect = self.image.get_rect(centerx=self.rect.centerx, bottom=self.rect.bottom)
            surface.blit(self.image, img_rect)
        size = 5 + int(abs(math.sin(self.flicker)) * 3)
        is_sea_lantern = "海晶灯" in self.sprite_name
        if is_sea_lantern:
            glow1 = (80, 200, 220)
            glow2 = (180, 240, 255)
        else:
            glow1 = (255, 200, 50)
            glow2 = (255, 255, 180)
        pygame.draw.circle(surface, glow1, (self.rect.centerx, self.rect.top + 8), size)
        pygame.draw.circle(surface, glow2, (self.rect.centerx, self.rect.top + 6), size // 2)
