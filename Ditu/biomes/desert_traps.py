import pygame
import random
import math
import os

from .desert_particles import BASE_DIR, DustParticle, ExplosionParticle, Particle

SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX", "shang-mo")


class TempleArrow:
    def __init__(self, x, y, vx, vy):
        self.vx = vx
        self.vy = vy
        self.damage = 10
        self.active = True
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "箭.png")).convert_alpha()
            raw = pygame.transform.scale(raw, (70, 70))
            angle = math.degrees(math.atan2(-vy, vx)) - 45
            self.image = pygame.transform.rotate(raw, angle)
        except:
            self.image = pygame.Surface((70, 70)); self.image.fill((255, 255, 255))

        self.rect = self.image.get_rect(center=(x, y))

    def update(self, fighters, blocks, env):
        if not self.active:
            return
        self.rect.x += self.vx
        self.rect.y += self.vy

        for f in fighters:
            if f.hp > 0 and self.rect.colliderect(f.rect):
                try:
                    f.take_damage(self.damage, attacker=None)
                except TypeError:
                    f.take_damage(self.damage)

                f.vx += self.vx * 0.3
                f.vy += self.vy * 0.3
                for _ in range(5):
                    env.particles.append(Particle(self.rect.centerx, self.rect.centery, (220, 20, 20), 15))
                self.active = False
                return

        for b in blocks:
            if self.rect.colliderect(b.rect):
                for _ in range(3):
                    env.particles.append(DustParticle(self.rect.centerx, self.rect.centery))
                self.active = False
                return

    def draw(self, surface):
        if self.active:
            surface.blit(self.image, self.rect)


class SandstoneBlock:
    def __init__(self, x, y, size=60):
        self.rect = pygame.Rect(x, y, size, size)
        self.spawn_progress = 0.0
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "雕纹砂岩.png")).convert_alpha()
            self.image = pygame.transform.scale(raw, (size, size))
            self.sfx_hit = pygame.mixer.Sound(os.path.join(SFX_DIR, "雕纹砂岩撞击声.mp3"))
        except:
            self.image = pygame.Surface((size, size)); self.image.fill((218, 165, 32))
            self.sfx_hit = None
        self.last_hit = 0

    def update(self):
        if self.spawn_progress < 1.0:
            self.spawn_progress = min(1.0, self.spawn_progress + 0.1)

    def process_collision(self, entity, env):
        if self.rect.colliderect(entity.rect):
            dx = entity.rect.centerx - self.rect.centerx
            dy = entity.rect.centery - self.rect.centery
            if abs(dx) > abs(dy):
                if dx > 0:
                    entity.rect.left = self.rect.right
                else:
                    entity.rect.right = self.rect.left
                entity.vx *= -0.5
            else:
                if dy > 0:
                    entity.rect.top = self.rect.bottom
                else:
                    entity.rect.bottom = self.rect.top
                entity.vy *= -0.5

            now = pygame.time.get_ticks()
            if now - self.last_hit > 400:
                self.last_hit = now
                if self.sfx_hit:
                    self.sfx_hit.play()
                for _ in range(4):
                    env.particles.append(DustParticle(entity.rect.centerx, entity.rect.centery))

    def draw(self, surface):
        if self.spawn_progress < 1.0:
            w, h = self.image.get_size()
            nw, nh = int(w * self.spawn_progress), int(h * self.spawn_progress)
            if nw > 0 and nh > 0:
                scaled = pygame.transform.scale(self.image, (nw, nh))
                offset_x, offset_y = (w - nw) // 2, (h - nh) // 2
                surface.blit(scaled, (self.rect.x + offset_x, self.rect.y + offset_y))
        else:
            surface.blit(self.image, self.rect)


class TrapDispenser:
    def __init__(self, x, y, direction):
        self.rect = pygame.Rect(x, y, 60, 60)
        self.direction = direction
        self.timer = random.randint(60, 180)
        self.spawn_progress = 0.0
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "发射器.png")).convert_alpha()
            raw = pygame.transform.scale(raw, (60, 60))
            angles = {"up": 0, "left": 90, "down": 180, "right": -90}
            self.image = pygame.transform.rotate(raw, angles[direction])
            self.sfx_shoot = pygame.mixer.Sound(os.path.join(SFX_DIR, "射击的音效.mp3"))
        except:
            self.image = pygame.Surface((60, 60)); self.image.fill((105, 105, 105))
            self.sfx_shoot = None

    def update(self, env):
        if self.spawn_progress < 1.0:
            self.spawn_progress = min(1.0, self.spawn_progress + 0.1)

        self.timer -= 1
        if self.timer <= 0:
            self.timer = random.randint(120, 240)
            if self.sfx_shoot:
                self.sfx_shoot.play()

            v_map = {"up": (0, -18), "down": (0, 18), "left": (-18, 0), "right": (18, 0)}
            vx, vy = v_map[self.direction]

            offset = 75
            ax = self.rect.centerx + (offset if vx > 0 else (-offset if vx < 0 else 0))
            ay = self.rect.centery + (offset if vy > 0 else (-offset if vy < 0 else 0))

            env.arrows.append(TempleArrow(ax, ay, vx, vy))

    def process_collision(self, entity):
        if self.rect.colliderect(entity.rect):
            dx = entity.rect.centerx - self.rect.centerx
            dy = entity.rect.centery - self.rect.centery
            if abs(dx) > abs(dy):
                if dx > 0:
                    entity.rect.left = self.rect.right
                else:
                    entity.rect.right = self.rect.left
                entity.vx *= -0.5
            else:
                if dy > 0:
                    entity.rect.top = self.rect.bottom
                else:
                    entity.rect.bottom = self.rect.top
                entity.vy *= -0.5

    def draw(self, surface):
        if self.spawn_progress < 1.0:
            w, h = self.image.get_size()
            nw, nh = int(w * self.spawn_progress), int(h * self.spawn_progress)
            if nw > 0 and nh > 0:
                scaled = pygame.transform.scale(self.image, (nw, nh))
                offset_x, offset_y = (w - nw) // 2, (h - nh) // 2
                surface.blit(scaled, (self.rect.x + offset_x, self.rect.y + offset_y))
        else:
            surface.blit(self.image, self.rect)


class TrapTNT:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 60, 60)
        self.timer = 180
        self.exploded = False
        self.spawn_progress = 0.0
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "TNT.png")).convert_alpha()
            self.image = pygame.transform.scale(raw, (60, 60))
            self.sfx_ignite = pygame.mixer.Sound(os.path.join(SFX_DIR, "TNT激活音效.mp3"))
            self.sfx_explode = pygame.mixer.Sound(os.path.join(SFX_DIR, "TNT爆炸音效.mp3"))
            if self.sfx_ignite:
                self.sfx_ignite.play()
        except:
            self.image = pygame.Surface((60, 60)); self.image.fill((200, 50, 50))
            self.sfx_ignite = None; self.sfx_explode = None

    def update(self, fighters, env, external_blocks=None, external_particles=None):
        if self.spawn_progress < 1.0:
            self.spawn_progress = min(1.0, self.spawn_progress + 0.1)

        self.timer -= 1
        if self.timer <= 0:
            self.exploded = True
            if self.sfx_explode:
                self.sfx_explode.play()
            self._apply_explosion(fighters, env, external_blocks, external_particles)

    def _apply_explosion(self, fighters, env, external_blocks=None, external_particles=None):
        cx, cy = self.rect.center
        for f in fighters:
            dist = math.hypot(f.rect.centerx - cx, f.rect.centery - cy)
            if dist <= 120:
                try:
                    f.take_damage(40, attacker=None)
                except TypeError:
                    f.take_damage(40)
                self._apply_knockback(f, cx, cy, 15)
            elif dist <= 250:
                try:
                    f.take_damage(20, attacker=None)
                except TypeError:
                    f.take_damage(20)
                self._apply_knockback(f, cx, cy, 8)

        if external_blocks is not None:
            for b in external_blocks:
                if getattr(b, 'active', False):
                    dist = math.hypot(b.rect.centerx - cx, b.rect.centery - cy)
                    if dist <= 250:
                        b.take_damage(999, external_particles)

        for _ in range(40):
            env.particles.append(ExplosionParticle(cx, cy))

    def _apply_knockback(self, target, ex, ey, force):
        dx = target.rect.centerx - ex
        dy = target.rect.centery - ey
        dist = math.hypot(dx, dy) or 1
        target.vx += (dx / dist) * force
        target.vy += (dy / dist) * force

    def draw(self, surface):
        if self.exploded:
            return
        img = self.image.copy()

        flash_rate = 10 if self.timer > 60 else 4
        if (self.timer // flash_rate) % 2 == 0:
            img.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)

        if self.spawn_progress < 1.0:
            w, h = img.get_size()
            nw, nh = int(w * self.spawn_progress), int(h * self.spawn_progress)
            if nw > 0 and nh > 0:
                scaled = pygame.transform.scale(img, (nw, nh))
                offset_x, offset_y = (w - nw) // 2, (h - nh) // 2
                surface.blit(scaled, (self.rect.x + offset_x, self.rect.y + offset_y))
        else:
            surface.blit(img, self.rect)
