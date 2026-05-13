import pygame
import math
import os
import sys
import random

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from entity import Entity, Particle

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX")


class Trident:
    def __init__(self, x, y, target_x, target_y, damage=30):
        self.x, self.y = x, y
        dx, dy = target_x - x, target_y - y
        dist = max(1, math.hypot(dx, dy))
        self.vx, self.vy = (dx / dist) * 7, (dy / dist) * 7
        self.damage = damage
        self.life = 80
        self.size = 14
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "三叉戟.png")).convert_alpha()
            self.image = pygame.transform.scale(raw, (28, 28))
        except Exception:
            self.image = None

    def update(self, bw, bh):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def is_dead(self):
        return self.life <= 0 or not (0 < self.x < 2000 and 0 < self.y < 2000)

    def draw(self, surface):
        if self.image:
            r = self.image.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(self.image, r)
        else:
            pygame.draw.circle(surface, (80, 180, 220), (int(self.x), int(self.y)), self.size)


class Drowned(Entity):
    def __init__(self, x, y, size=80):
        super().__init__(x, y, size, 800)
        self.speed = 1.6
        self.damage = 25
        self.attack_range = 100
        self.attack_cd = 0
        self.trident_cd = 0
        self.dmg_res = 0.10
        self.kb_res = 0.60
        self.phase = 1
        self._phase2_triggered = False
        self.particles = []
        self.trident_list = []
        self.vx = 0
        self.vy = 0
        self.load_assets()

    def load_assets(self):
        boss_img = os.path.join(BASE_DIR, "Boss", "溺尸王", "溺尸王.png")
        try:
            if os.path.exists(boss_img):
                raw = pygame.image.load(boss_img).convert_alpha()
            else:
                raw = pygame.image.load(os.path.join(SPRITES_DIR, "溺尸.webp")).convert_alpha()
            self.image = pygame.transform.scale(raw, (self.size, self.size))
        except Exception:
            try:
                raw = pygame.image.load(os.path.join(SPRITES_DIR, "僵尸.webp")).convert_alpha()
                self.image = pygame.transform.scale(raw, (self.size, self.size))
            except Exception:
                self.image = None
        try:
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"溺尸受伤{i}.mp3")) for i in [1, 2]]
        except Exception:
            self.sfx_hurt = []

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0:
            return
        actual = amount * (1.0 - self.dmg_res)
        self.hp -= actual
        self.trigger_damage_flash()
        if self.hp <= 400 and not self._phase2_triggered:
            self._phase2_triggered = True
            self.phase = 2
            self.damage = 35
            self.speed = 2.0
            self.size = 100
            self.attack_range = 120
            self.dmg_res = 0.18
            self.rect = pygame.Rect(self.rect.x, self.rect.y, self.size, self.size)
            self.rect.center = (self.rect.centerx, self.rect.centery)
            try:
                from i18n import t as _tt
                self._pending_speech = _tt("p2_drowned")
            except Exception:
                self._pending_speech = "深海之下，无人能逃..."
            for _ in range(60):
                self.particles.append(Particle(self.rect.centerx, self.rect.centery,
                    (60, 140, 200), speed_mult=2.5))

    def update(self, enemies, bw, bh, tridents_out):
        if self.hp <= 0:
            return None
        self.update_buffs()
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        target = None
        min_dist = 9999
        for e in enemies:
            if e != self and e.hp > 0:
                d = math.hypot(e.rect.centerx - self.rect.centerx, e.rect.centery - self.rect.y)
                if d < min_dist:
                    min_dist = d
                    target = e

        if target:
            dx = target.rect.centerx - self.rect.centerx
            dy = target.rect.centery - self.rect.centery
            dist = max(1, math.hypot(dx, dy))
            self.vx += (dx / dist) * self.speed * 0.15
            self.vy += (dy / dist) * self.speed * 0.15

        self.apply_physics(bw, bh)

        if self.attack_cd > 0:
            self.attack_cd -= 1
        if self.trident_cd > 0:
            self.trident_cd -= 1

        result = None
        if target and min_dist < self.attack_range and self.attack_cd <= 0:
            self.attack_cd = 50
            result = {"target": target, "damage": self.damage}

        if target and self.trident_cd <= 0 and random.random() < 0.012:
            self.trident_cd = 150
            t = Trident(self.rect.centerx, self.rect.centery,
                        target.rect.centerx, target.rect.centery,
                        damage=35)
            tridents_out.append(t)

        return result

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        if self.hp <= 0:
            return
        if self.image:
            r = self.image.get_rect(center=self.rect.center)
            surface.blit(self.image, r)
        else:
            pygame.draw.rect(surface, (60, 140, 200), self.rect)
        self.draw_float_texts(surface)
