import math
import os
import random
import re

import pygame

from entity import Entity, FloatText, Particle
from i18n import t
from ._sfx import play_sfx


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PREFERRED_ASSET_DIR = os.path.join(BASE_DIR, "Boss", "DrownedKing")
FALLBACK_ASSET_DIR = os.path.join(BASE_DIR, "Boss", "drowned_king")
ASSET_DIR = PREFERRED_ASSET_DIR if os.path.exists(os.path.join(PREFERRED_ASSET_DIR, "drowned_king.png")) else FALLBACK_ASSET_DIR
SFX_DIR = os.path.join(ASSET_DIR, "sfx")

_IMAGE_CACHE = {}
_FRAME_CACHE = {}
_SOUND_CACHE = {}


def _sort_key(path):
    name = os.path.basename(path)
    nums = [int(n) for n in re.findall(r"\d+", name)]
    return nums if nums else [0, name]


def _safe_load_image(path, fallback_color=None, scale=None):
    key = (path, scale, fallback_color)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing: {path}")
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.smoothscale(img, scale)
        _IMAGE_CACHE[key] = img
        return img
    except Exception as exc:
        print(f"[DrownedKing] load failed: {path} -> {exc}")
        if fallback_color:
            surf = pygame.Surface(scale or (64, 64), pygame.SRCALPHA)
            surf.fill(fallback_color)
            _IMAGE_CACHE[key] = surf
            return surf
        _IMAGE_CACHE[key] = None
        return None


def _load_frames(folder, scale=None):
    key = (folder, scale)
    if key in _FRAME_CACHE:
        return _FRAME_CACHE[key]
    frames = []
    try:
        if not os.path.exists(folder):
            raise FileNotFoundError(f"missing: {folder}")
        paths = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.lower().endswith(".png")
        ]
        for path in sorted(paths, key=_sort_key):
            frame = _safe_load_image(path, scale=scale)
            if frame:
                frames.append(frame)
    except Exception as exc:
        print(f"[DrownedKing] frame load failed: {folder} -> {exc}")
    _FRAME_CACHE[key] = frames
    return frames


def _load_sound(*names):
    key = names
    if key in _SOUND_CACHE:
        return _SOUND_CACHE[key]
    sound = None
    for name in names:
        path = os.path.join(SFX_DIR, name)
        if not os.path.exists(path):
            continue
        try:
            sound = pygame.mixer.Sound(path)
            break
        except Exception as exc:
            print(f"[DrownedKing] sound load failed: {path} -> {exc}")
            sound = None
    _SOUND_CACHE[key] = sound
    return sound


def _load_sound_group(names):
    return [sound for sound in (_load_sound(name) for name in names) if sound]


def _safe_play(sound, volume=1.0):
    if not sound:
        return
    try:
        play_sfx(sound, volume=volume)
    except Exception:
        try:
            sound.set_volume(volume)
            sound.play()
        except Exception:
            pass


def _asset_path(*parts):
    return os.path.join(ASSET_DIR, *parts)


def _draw_slash_arc(surface, cx, cy, radius, start_angle, end_angle, color, alpha):
    layer = pygame.Surface((radius * 2 + 48, radius * 2 + 48), pygame.SRCALPHA)
    center = radius + 24
    for idx in range(3):
        glow_alpha = max(0, int(alpha * (0.45 - idx * 0.12)))
        rect = pygame.Rect(
            center - radius - idx * 4,
            center - radius - idx * 4,
            (radius + idx * 4) * 2,
            (radius + idx * 4) * 2,
        )
        pygame.draw.arc(layer, (*color, glow_alpha), rect, start_angle, end_angle, width=max(3, 14 - idx * 4))
    rect = pygame.Rect(center - radius, center - radius, radius * 2, radius * 2)
    pygame.draw.arc(layer, (*color, alpha), rect, start_angle, end_angle, width=6)
    surface.blit(layer, (int(cx - center), int(cy - center)))


def _draw_full_circle_slash(surface, cx, cy, radius, color, alpha):
    layer = pygame.Surface((radius * 2 + 56, radius * 2 + 56), pygame.SRCALPHA)
    c = radius + 28
    pygame.draw.circle(layer, (*color, max(0, alpha // 3)), (c, c), radius + 8, width=18)
    pygame.draw.circle(layer, (*color, max(0, alpha // 2)), (c, c), radius + 2, width=12)
    pygame.draw.circle(layer, (*color, alpha), (c, c), radius, width=8)
    surface.blit(layer, (int(cx - c), int(cy - c)))


class DustParticle:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 24
        self.max_life = 24
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(170 * self.life / self.max_life)
        pygame.draw.circle(surface, (110, 210, 230, alpha), (int(self.x), int(self.y)), self.size)


class ChargeParticle:
    def __init__(self, owner, radius, phase):
        self.owner = owner
        self.radius = radius
        self.phase = phase
        self.life = 24
        self.max_life = 24

    def update(self):
        self.phase += 0.38
        self.radius *= 0.95
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        cx, cy = self.owner.rect.center
        x = cx + math.cos(self.phase) * self.radius
        y = cy + math.sin(self.phase) * self.radius * 0.55
        alpha = int(210 * self.life / self.max_life)
        pygame.draw.circle(surface, (90, 220, 255, alpha), (int(x), int(y)), 4)


class SlashArcVFX:
    def __init__(self, x, y, facing, radius=100, degrees=120, life=5):
        self.x = x
        self.y = y
        self.facing = facing
        self.radius = radius
        self.degrees = degrees
        self.life = life
        self.max_life = life

    def update(self):
        self.life -= 1

    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0:
            return
        fx, fy = self.facing
        center_angle = math.atan2(-fy, fx)
        half = math.radians(self.degrees * 0.5)
        alpha = int(255 * self.life / self.max_life)
        _draw_slash_arc(surface, self.x, self.y, self.radius, center_angle - half, center_angle + half, (135, 235, 255), alpha)


class CircleSlashVFX:
    def __init__(self, x, y, radius=150, life=8):
        self.x = x
        self.y = y
        self.radius = radius
        self.life = life
        self.max_life = life

    def update(self):
        self.life -= 1

    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(230 * self.life / self.max_life)
        _draw_full_circle_slash(surface, self.x, self.y, self.radius, (150, 240, 255), alpha)


class LightningBurst:
    def __init__(self, x, y, radius, frames):
        self.x = x
        self.y = y
        self.radius = radius
        self.frames = frames
        self.life = 28
        self.max_life = 28

    def update(self):
        self.life -= 1

    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0:
            return
        progress = 1.0 - self.life / self.max_life
        alpha = int(210 * (self.life / self.max_life))
        if self.frames:
            frame = self.frames[min(len(self.frames) - 1, int(progress * len(self.frames)))]
            size = max(36, int(self.radius * 2.25))
            img = pygame.transform.smoothscale(frame, (size, size))
            img.set_alpha(alpha)
            surface.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            return
        layer = pygame.Surface((int(self.radius * 2.4), int(self.radius * 2.4)), pygame.SRCALPHA)
        c = layer.get_width() // 2
        pygame.draw.circle(layer, (120, 230, 255, alpha), (c, c), int(self.radius), 4)
        pygame.draw.circle(layer, (255, 255, 255, alpha // 2), (c, c), int(self.radius * 0.35), 2)
        surface.blit(layer, layer.get_rect(center=(int(self.x), int(self.y))))


class BubbleParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.7, 0.7)
        self.vy = random.uniform(-1.9, -0.7)
        self.life = random.randint(20, 34)
        self.max_life = self.life
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.98
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(150 * self.life / self.max_life)
        pygame.draw.circle(surface, (170, 235, 255, alpha), (int(self.x), int(self.y)), self.radius, 1)


class WaterPrisonVFX:
    _generated_frames = None

    def __init__(self, target_entity):
        self.target = target_entity
        self.life = 90
        self.frames = _load_frames(_asset_path("vfx_water_prison"), scale=(120, 120))
        if not self.frames:
            self.frames = self._generate_frames()
        self.frame_index = 0.0
        self.bubble_particles = []
        self.burst_particles = []
        self.break_life = 0

    @classmethod
    def _generate_frames(cls):
        if cls._generated_frames:
            return cls._generated_frames
        frames = []
        for idx in range(16):
            surf = pygame.Surface((120, 120), pygame.SRCALPHA)
            pulse = math.sin(idx / 16 * math.tau)
            radius = 43 + int(pulse * 3)
            alpha = 72 + int(28 * abs(pulse))
            pygame.draw.circle(surf, (70, 190, 235, alpha), (60, 60), radius)
            pygame.draw.circle(surf, (170, 240, 255, 155), (60, 60), radius, 3)
            pygame.draw.arc(surf, (235, 255, 255, 180), (21, 18, 78, 78), math.radians(210), math.radians(300), 4)
            pygame.draw.arc(surf, (95, 210, 255, 120), (18, 20, 84, 82), math.radians(25 + idx * 7), math.radians(120 + idx * 7), 2)
            for dot in range(5):
                a = idx * 0.55 + dot * 1.6
                x = 60 + math.cos(a) * (radius - 10)
                y = 60 + math.sin(a) * (radius - 14)
                pygame.draw.circle(surf, (210, 250, 255, 130), (int(x), int(y)), 2)
            frames.append(surf)
        cls._generated_frames = frames
        return frames

    def refresh(self):
        self.life = 90
        self.break_life = 0

    def update(self):
        if not self.target or getattr(self.target, "hp", 0) <= 0:
            self._break()
        timer = getattr(self.target, "_drowned_king_slow_timer", 0) if self.target else 0
        if timer > 0:
            self.life = timer
        else:
            self.life -= 1
            if self.life <= 0:
                self._break()
        if self.break_life > 0:
            self.break_life -= 1
            for p in self.burst_particles[:]:
                p.update()
                if p.life <= 0:
                    self.burst_particles.remove(p)
            return self.break_life > 0 or bool(self.burst_particles)
        self.frame_index = (self.frame_index + 0.15) % max(1, len(self.frames))
        if self.life % 5 == 0 and self.target:
            cx, cy = self.target.rect.center
            spread = max(18, int(self.target.size * 0.48))
            self.bubble_particles.append(BubbleParticle(cx + random.randint(-spread, spread), cy + random.randint(-spread, spread)))
        for p in self.bubble_particles[:]:
            p.update()
            if p.life <= 0:
                self.bubble_particles.remove(p)
        return self.life > 0

    def _break(self):
        if self.break_life > 0:
            return
        self.break_life = 5
        if not self.target:
            return
        cx, cy = self.target.rect.center
        for _ in range(16):
            ang = random.random() * math.tau
            spd = random.uniform(1.0, 3.2)
            self.burst_particles.append(DustParticle(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd))

    def draw(self, surface):
        if not self.target:
            return
        if self.break_life > 0:
            for p in self.burst_particles:
                p.draw(surface)
            return
        if not self.frames:
            return
        frame = self.frames[int(self.frame_index) % len(self.frames)]
        size = max(48, int(self.target.size * 1.3))
        img = pygame.transform.smoothscale(frame, (size, size))
        rect = img.get_rect(center=self.target.rect.center)
        surface.blit(img, rect)
        for p in self.bubble_particles:
            p.draw(surface)


class Trident:
    def __init__(self, x, y, vx, vy, damage, shooter=None):
        self.state = "flying"
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.shooter = shooter
        self.life = 120
        self.size = 14
        self.rect = pygame.Rect(int(x) - 7, int(y) - 7, 14, 14)
        self.active = True
        self.is_drowned_king_trident = True
        self.hit_enemies = set()
        self.slow_duration = 50
        self.slow_amount = 0.25
        self.electrified_timer = 0
        self.electrified_pulse_timer = 0
        self.pulse_radius = 80
        self.pulse_damage = 8
        self.frame_tick = 0
        self.fly_frame_index = 0.0
        self.idle_frame_index = 0.0
        self.ult_frame_index = 0.0
        self.angle = math.atan2(self.vy, self.vx)
        self.trail_positions = []
        self.trail_max = 8
        self.water_prisons = []
        self.image = _safe_load_image(_asset_path("trident.png"), scale=(44, 44))
        self.fly_frames = _load_frames(_asset_path("vfx_fly"), scale=(48, 48))
        self.idle_frames = _load_frames(_asset_path("vfx_idle"), scale=(50, 50))
        self.ult_frames = _load_frames(_asset_path("vfx_ult"), scale=(88, 88))
        self.sfx_pinned = _load_sound("trident_explode.mp3")
        self.sfx_drop = _load_sound_group(["trident_drop_1.mp3", "trident_drop_2.mp3", "trident_drop_3.mp3"])
        self.sfx_pierce = _load_sound_group(["trident_pierce_1.mp3", "trident_pierce_2.mp3", "trident_pierce_3.mp3"])
        self.sfx_lightning = _load_sound("lightning_strike.mp3.mp3", "lightning_strike.mp3")

    @staticmethod
    def tick_slow_effects(fighters):
        for fighter in fighters:
            timer = getattr(fighter, "_drowned_king_slow_timer", 0)
            if timer <= 0:
                continue
            timer -= 1
            fighter._drowned_king_slow_timer = timer
            base_speed = getattr(fighter, "_drowned_king_base_speed", getattr(fighter, "speed", None))
            if base_speed is None:
                continue
            if timer <= 0:
                fighter.speed = base_speed
                for attr in ("_drowned_king_slow_timer", "_drowned_king_base_speed", "_drowned_king_slow_scale"):
                    if hasattr(fighter, attr):
                        try:
                            delattr(fighter, attr)
                        except Exception:
                            pass
            else:
                fighter.speed = base_speed * getattr(fighter, "_drowned_king_slow_scale", 0.6)

    def update(self, bw=None, bh=None, blocks=None, enemies=None):
        if not self.active:
            return []
        self.frame_tick += 1
        bw = bw if bw is not None else 2000
        bh = bh if bh is not None else 2000
        blocks = blocks or []
        enemies = enemies or []
        if self.state == "flying":
            self.trail_positions.append((self.x, self.y))
            if len(self.trail_positions) > self.trail_max:
                self.trail_positions.pop(0)
            self.x += self.vx
            self.y += self.vy
            self.life -= 1
            self.angle = math.atan2(self.vy, self.vx)
            self._sync_rect()
            if self.x <= 0 or self.x >= bw or self.y <= 0 or self.y >= bh:
                self.x = max(0.0, min(float(bw), self.x))
                self.y = max(0.0, min(float(bh), self.y))
                self._sync_rect()
                self._pin()
                return []
            for block in blocks:
                if getattr(block, "active", False) and getattr(block, "rect", None) and self.rect.colliderect(block.rect):
                    self._pin()
                    return []
            hits = self._check_enemy_pierce(enemies)
            if self.life <= 0:
                self._drop()
            return hits
        if self.state == "electrified":
            self.electrified_timer -= 1
            self.ult_frame_index = (self.ult_frame_index + 0.25) % max(1, len(self.ult_frames))
            if self.electrified_timer <= 0:
                self.state = "pinned"
                self.electrified_pulse_timer = 0
                return []
            self.electrified_pulse_timer += 1
            if self.electrified_pulse_timer >= 30:
                self.electrified_pulse_timer = 0
                _safe_play(self.sfx_lightning, 0.8)
                return self._check_electric_hits(enemies)
        elif self.state == "pinned":
            self.idle_frame_index = (self.idle_frame_index + 0.18) % max(1, len(self.idle_frames))
        return []

    def electrify(self, duration=300, pulse_radius=80, pulse_damage=8):
        if self.state != "pinned" or not self.active:
            return False
        self.state = "electrified"
        self.electrified_timer = duration
        self.electrified_pulse_timer = 0
        self.pulse_radius = pulse_radius
        self.pulse_damage = pulse_damage
        _safe_play(self.sfx_lightning, 0.55)
        return True

    def destroy(self):
        self.active = False

    def is_dead(self):
        return not self.active

    def draw(self, surface):
        if not self.active:
            return
        if self.state == "flying":
            self.fly_frame_index = (self.fly_frame_index + 0.2) % max(1, len(self.fly_frames))
            img = self.fly_frames[int(self.fly_frame_index) % len(self.fly_frames)] if self.fly_frames else self.image
            angle = self._draw_angle()
            positions = self.trail_positions[-self.trail_max:]
            for idx, (tx, ty) in enumerate(positions):
                if not img:
                    continue
                alpha = int(255 * (idx + 1) / (len(positions) + 1) * 0.55)
                trail_img = img.copy()
                trail_img.set_alpha(alpha)
                rotated = pygame.transform.rotate(trail_img, angle)
                surface.blit(rotated, rotated.get_rect(center=(int(tx), int(ty))))
            if img:
                rotated = pygame.transform.rotate(img, angle)
                surface.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))
            else:
                self._draw_vector_fallback(surface)
            return
        if self.state == "pinned":
            img = self.idle_frames[int(self.idle_frame_index) % len(self.idle_frames)] if self.idle_frames else self.image
            if img:
                surface.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            else:
                self._draw_vector_fallback(surface)
            return
        if self.state == "dropped":
            if self.image:
                img = pygame.transform.rotate(self.image, 90)
                img.set_alpha(210)
                surface.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            else:
                self._draw_vector_fallback(surface)
            return
        if self.state == "electrified":
            img = self.ult_frames[int(self.ult_frame_index) % len(self.ult_frames)] if self.ult_frames else self.image
            alpha = 255 if (self.frame_tick // 15) % 2 == 0 else 128
            if img:
                img = img.copy()
                img.set_alpha(alpha)
                surface.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            radius = self.pulse_radius
            layer = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
            glow = 48 + int(36 * abs(math.sin(self.frame_tick * 0.2)))
            pygame.draw.circle(layer, (80, 220, 255, glow), (radius + 5, radius + 5), radius, 2)
            pygame.draw.circle(layer, (230, 255, 255, glow), (radius + 5, radius + 5), 13, 2)
            surface.blit(layer, (int(self.x - radius - 5), int(self.y - radius - 5)))

    def _draw_angle(self):
        return -math.degrees(math.atan2(self.vy, self.vx)) - 45

    def _sync_rect(self):
        self.rect.center = (int(self.x), int(self.y))

    def _pin(self):
        self.state = "pinned"
        self.vx = 0.0
        self.vy = 0.0
        self.rect.size = (20, 20)
        self._sync_rect()
        _safe_play(self.sfx_pinned, 0.75)

    def _drop(self):
        self.state = "dropped"
        self.vx = 0.0
        self.vy = 0.0
        self.rect.size = (20, 20)
        self._sync_rect()
        if self.sfx_drop:
            _safe_play(random.choice(self.sfx_drop), 0.7)

    def _check_enemy_pierce(self, enemies):
        hits = []
        for enemy in enemies:
            if enemy is self.shooter or getattr(enemy, "hp", 0) <= 0:
                continue
            ident = id(enemy)
            if ident in self.hit_enemies:
                continue
            if self.rect.colliderect(enemy.rect.inflate(10, 10)):
                self.hit_enemies.add(ident)
                self._apply_slow(enemy)
                vfx = WaterPrisonVFX(enemy)
                self.water_prisons.append(vfx)
                if self.sfx_pierce:
                    _safe_play(random.choice(self.sfx_pierce), 0.65)
                hits.append({
                    "target": enemy,
                    "damage": self.damage,
                    "source": self,
                    "kind": "trident_pierce",
                    "water_prison": True,
                    "water_prison_vfx": vfx,
                })
        return hits

    def _check_electric_hits(self, enemies):
        hits = []
        for enemy in enemies:
            if enemy is self.shooter or getattr(enemy, "hp", 0) <= 0:
                continue
            dx = enemy.rect.centerx - self.x
            dy = enemy.rect.centery - self.y
            if math.hypot(dx, dy) <= self.pulse_radius + enemy.size * 0.5:
                hits.append({"target": enemy, "damage": self.pulse_damage, "source": self, "kind": "trident_lightning"})
        return hits

    def _apply_slow(self, enemy):
        if not hasattr(enemy, "speed"):
            return
        if getattr(enemy, "_drowned_king_slow_timer", 0) <= 0:
            enemy._drowned_king_base_speed = enemy.speed
        enemy._drowned_king_slow_scale = 1.0 - self.slow_amount
        enemy._drowned_king_slow_timer = self.slow_duration
        enemy.speed = enemy._drowned_king_base_speed * enemy._drowned_king_slow_scale
        try:
            enemy.add_buff("trident_slow", -40, self.slow_duration, "debuff")
        except Exception:
            pass

    def _draw_vector_fallback(self, surface):
        dx = math.cos(self.angle) * 18
        dy = math.sin(self.angle) * 18
        pygame.draw.line(surface, (190, 250, 255), (int(self.x - dx), int(self.y - dy)), (int(self.x + dx), int(self.y + dy)), 4)
        pygame.draw.circle(surface, (80, 190, 220), (int(self.x), int(self.y)), 5)


class DrownedKing(Entity):
    STATES = (
        "IDLE", "CHASE", "COMBAT_TAUNT", "MELEE_COMBO", "THROW",
        "THUNDER_CHARGE", "ULTIMATE", "WEAPON_RECALL", "COOLDOWN",
    )

    def __init__(self, x, y, size=100):
        super().__init__(x, y, size, 1200)
        self.speed = 2.6
        self.damage = 35
        self.attack_range = 135
        self.attack_cd = 0
        self.dmg_res = 0.14
        self.kb_res = 0.74
        self.phase = 1
        self._phase2_triggered = False
        self._phase1_base_speed = 2.6
        self._phase2_base_speed = 3.3
        self.vx = 0.0
        self.vy = 0.0
        self.state = "IDLE"
        self.state_timer = random.randint(20, 55)
        self.state_age = 0
        self.trident_list = []
        self.melee_cd = 0
        self.throw_cd = 90
        self.thunder_cd = 300
        self.ultimate_cd = 600
        self._recall_scan_timer = 30
        self._melee_data = None
        self._melee_released = False
        self._melee_combo_index = 0
        self._melee_hit_age = 0
        self._throw_released = False
        self._thunder_released = False
        self._ultimate_released = False
        self._recall_released = False
        self._recall_flag = False
        self._recall_heal_per = 15
        self._thunder_charge_flag = False
        self._thunder_charge_data = None
        self._ultimate_flag = False
        self._ultimate_data = None
        self._last_attacker = None
        self._facing = (1.0, 0.0)
        self._chase_offset = 0.0
        self._chase_offset_timer = 0
        self._backstep = (0.0, 0.0)
        self._taunt_target = None
        self._taunt_cd = 0
        self._taunt_duration = 180
        self._intro_locked = False
        self._intro_scale = 1.0
        self._speech_cooldown = 330
        self._spoken_keys = set()
        self.weather_is_storm = False
        self.speed_bonus = 0.0
        self.thunder_range_bonus = 0
        self.thunder_dmg_bonus = 0
        self.ultimate_radius_bonus = 0
        self.ultimate_multiplier_bonus = 0.0
        self._recent_dmg_log = []
        self._swarm_dmg_threshold = 0.06
        self._swarm_dmg_window = 90
        self._block_chance = 0.20
        self._block_glow = 0
        self._block_last_time = 0
        self.sprite_size = 140
        self.image = _safe_load_image(_asset_path("drowned_king.png"), scale=(self.sprite_size, self.sprite_size))
        self.trident_image = _safe_load_image(_asset_path("trident.png"), scale=(100, 100))
        self.ult_frames = _load_frames(_asset_path("vfx_ult"))
        self.particles = []
        self.charge_particles = []
        self.slash_vfx = []
        self.lightning_bursts = []
        self.thrust_scale_timer = 0
        self.spin_timer = 0
        self.spin_angle = 0.0
        self.hand_vfx_alpha = 0.0
        self.hand_vfx_idle_frames = _load_frames(_asset_path("vfx_idle"))
        self.sfx_throw = _load_sound("trident_throw.mp3")
        self.sfx_recall = _load_sound("Riptide_III.mp3", "Riptide_III.ogg.mp3")
        self.sfx_stab = _load_sound("drowned_stab.mp3")
        self.sfx_slash = _load_sound("drowned_slash.mp3")
        self.sfx_lightning = _load_sound("lightning_strike.mp3.mp3", "lightning_strike.mp3")

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0:
            return
        if self.phase == 2:
            self._block_chance = 0.28
        block_chance = self._block_chance
        if self._swarmed(self._last_enemies if hasattr(self, '_last_enemies') else []):
            block_chance *= 1.30
        blocked = random.random() < block_chance
        if blocked:
            actual = max(1, int(amount * 0.40))
            self.hp -= actual
            self.trigger_damage_flash()
            self._block_glow = 12
            self._block_last_time = pygame.time.get_ticks()
            try:
                _safe_play(self.sfx_slash, 0.45)
            except Exception:
                pass
        else:
            actual = max(1, int(round(amount * (1.0 - self.dmg_res))))
            self.hp -= actual
            self.trigger_damage_flash()
        self.float_texts.append(FloatText(
            self.rect.centerx + random.randint(-24, 24),
            self.rect.top - 18 - random.randint(0, 28),
            f"-{actual}", (255, 215, 0) if blocked else (220, 245, 255)))
        if attacker and attacker is not self and getattr(attacker, "hp", 0) > 0:
            self._last_attacker = attacker
        if self.hp > 0:
            self._trigger_phase2_if_needed()
        self._recent_dmg_log.append((pygame.time.get_ticks(), actual))

    def _swarmed(self, enemies):
        nearby = [e for e in enemies if e is not self and getattr(e, "hp", 0) > 0
                  and self._dist_to(e) < self.attack_range * 1.3]
        recent = self._recent_damage()
        threshold = self.max_hp * self._swarm_dmg_threshold
        return len(nearby) >= 2 and recent > threshold

    def _recent_damage(self):
        now = pygame.time.get_ticks()
        self._recent_dmg_log = [(t, d) for t, d in self._recent_dmg_log if now - t < self._swarm_dmg_window * 16.7]
        if not self._recent_dmg_log:
            return 0
        return sum(d for _, d in self._recent_dmg_log)

    def update(self, enemies, bw, bh, tridents_out=None, weather=None):
        if self.hp <= 0:
            return None
        if self._intro_locked:
            return None
        tridents_out = tridents_out if tridents_out is not None else []
        self.update_buffs()
        Trident.tick_slow_effects(enemies)
        self._sync_weather(weather)
        self._trigger_phase2_if_needed()
        self._tick_local_effects()
        self._tick_cooldowns()
        target = self._select_target(enemies)
        if target:
            self._update_facing(target)
        self._last_enemies = enemies
        self._recall_scan_timer -= 1
        if self.state != "WEAPON_RECALL" and self._recall_scan_timer <= 0:
            self._recall_scan_timer = 30
            if self._should_recall():
                self._enter_state("WEAPON_RECALL")
        result = None
        if self.state == "IDLE":
            self._update_idle(target)
        elif self.state == "CHASE":
            self._update_chase(target)
        elif self.state == "COMBAT_TAUNT":
            self._update_combat_taunt(target)
        elif self.state == "MELEE_COMBO":
            result = self._update_melee(enemies)
        elif self.state == "THROW":
            self._update_throw(target, tridents_out)
        elif self.state == "THUNDER_CHARGE":
            self._update_thunder_charge()
        elif self.state == "ULTIMATE":
            self._update_ultimate()
        elif self.state == "WEAPON_RECALL":
            self._update_weapon_recall()
        elif self.state == "COOLDOWN":
            self._update_cooldown(target)
        self._move_and_clamp(bw, bh)
        self.state_age += 1
        return result

    def draw(self, surface):
        for burst in self.lightning_bursts:
            burst.draw(surface)
        for effect in self.slash_vfx:
            effect.draw(surface)
        for particle in self.particles:
            particle.draw(surface)
        for particle in self.charge_particles:
            particle.draw(surface)
        if self.hp <= 0:
            return
        if self.state in ("ULTIMATE", "THUNDER_CHARGE") and self.ult_frames:
            frame = self.ult_frames[(self.state_age // 3) % len(self.ult_frames)]
            size = int(185 + 28 * abs(math.sin(self.state_age * 0.16)))
            img = pygame.transform.smoothscale(frame, (size, size))
            img.set_alpha(155 if self.state == "ULTIMATE" else 105)
            surface.blit(img, img.get_rect(center=self.rect.center))
        draw_img = self._current_sprite()
        if draw_img:
            if self.spin_timer > 0:
                draw_img = pygame.transform.rotate(draw_img, self.spin_angle)
            surface.blit(draw_img, draw_img.get_rect(center=self.rect.center))
        else:
            self._draw_body_fallback(surface)
        self._draw_weapon_overlay(surface)
        self._draw_hand_vfx(surface)
        if self.state in ("THUNDER_CHARGE", "WEAPON_RECALL"):
            pulse = int(9 + 7 * abs(math.sin(self.state_age * 0.25)))
            pygame.draw.ellipse(surface, (90, 220, 255), self.rect.inflate(pulse * 2, pulse), 2)
        self.draw_float_texts(surface)
        if self._block_glow > 0:
            glow_alpha = int((self._block_glow / 12) * 120)
            glow_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (255, 180, 60, glow_alpha), glow_surf.get_rect(), 5)
            pygame.draw.ellipse(glow_surf, (255, 220, 100, glow_alpha // 2), glow_surf.get_rect().inflate(-6, -6), 3)
            surface.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10))
            self._block_glow -= 1

    def add_lightning_burst(self, x, y, radius):
        self.lightning_bursts.append(LightningBurst(x, y, radius, _load_frames(_asset_path("vfx_ult"))))

    def _current_sprite(self):
        if not self.image:
            return None
        scale = self._intro_scale
        if self.state in ("IDLE", "CHASE"):
            scale += 0.02 * abs(math.sin(self.state_age * 0.08))
        if self.phase == 2:
            img = self.image.copy()
            img.fill((70, 170, 230, 74), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            img = self.image
        if abs(scale - 1.0) > 0.001:
            w = max(1, int(img.get_width() * scale))
            h = max(1, int(img.get_height() * scale))
            img = pygame.transform.smoothscale(img, (w, h))
        return img

    def _draw_weapon_overlay(self, surface):
        if not self.trident_image:
            return
        if self._intro_locked:
            return
        fx, fy = self._facing
        scale = 1.0
        if self.thrust_scale_timer > 0:
            scale = 1.0 + 0.2 * (self.thrust_scale_timer / 5.0)
        if self.state in ("THUNDER_CHARGE", "WEAPON_RECALL"):
            scale = 1.28 + 0.08 * abs(math.sin(self.state_age * 0.3))
        if self.state == "THROW":
            scale = 1.18
        img = self.trident_image
        w = max(1, int(img.get_width() * scale))
        h = max(1, int(img.get_height() * scale))
        img = pygame.transform.smoothscale(img, (w, h))
        angle = -math.degrees(math.atan2(fy, fx)) - 45
        img = pygame.transform.rotate(img, angle)
        cx = self.rect.centerx + fx * 38
        cy = self.rect.centery + fy * 38
        surface.blit(img, img.get_rect(center=(int(cx), int(cy))))

    def _draw_hand_vfx(self, surface):
        if self.hand_vfx_alpha <= 0:
            return
        if self._intro_locked:
            return
        fx, fy = self._facing
        hx = self.rect.centerx + fx * 34
        hy = self.rect.centery + fy * 34
        alpha = int(100 + 60 * math.sin(self.state_age * 0.13))
        alpha = int(alpha * self.hand_vfx_alpha)
        if alpha < 15:
            return
        tip_x = hx + fx * 56
        tip_y = hy + fy * 56
        size = int(abs(tip_x - hx) + abs(tip_y - hy)) + 20
        layer_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        ox, oy = size // 2 - int(hx), size // 2 - int(hy)
        for layer in range(3):
            la = alpha // (layer + 1)
            if la < 6:
                continue
            jitter = layer * 4
            pts = [(int(hx) + ox, int(hy) + oy)]
            for s in range(1, 6):
                t = s / 5.0
                sx = hx + (tip_x - hx) * t + random.uniform(-jitter, jitter)
                sy = hy + (tip_y - hy) * t + random.uniform(-jitter, jitter)
                pts.append((int(sx) + ox, int(sy) + oy))
            pts.append((int(tip_x) + ox, int(tip_y) + oy))
            if layer == 0:
                color = (255, 255, 255, la)
            elif layer == 1:
                color = (160, 220, 255, la)
            else:
                color = (100, 180, 240, la)
            if len(pts) >= 2:
                pygame.draw.lines(layer_surf, color, False, pts, max(1, 4 - layer))
        surface.blit(layer_surf, (int(hx) - size//2 + ox, int(hy) - size//2 + oy))
        for _ in range(3):
            bx = tip_x + random.uniform(-14, 14)
            by = tip_y + random.uniform(-14, 14)
            sa = min(alpha, random.randint(40, 90))
            surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 240, 255, sa), (3, 3), random.randint(1, 2))
            surface.blit(surf, (int(bx), int(by)))

    def _draw_body_fallback(self, surface):
        cx, cy = self.rect.center
        pygame.draw.ellipse(surface, (26, 76, 92), self.rect.inflate(18, 28))
        pygame.draw.ellipse(surface, (115, 220, 230), self.rect.inflate(10, 20), 3)
        pygame.draw.circle(surface, (230, 255, 255), (cx - 16, cy - 10), 4)
        pygame.draw.circle(surface, (230, 255, 255), (cx + 16, cy - 10), 4)

    def _tick_local_effects(self):
        if self._speech_cooldown > 0:
            self._speech_cooldown -= 1
        if self.thrust_scale_timer > 0:
            self.thrust_scale_timer -= 1
        if self.spin_timer > 0:
            self.spin_timer -= 1
            self.spin_angle = (self.spin_angle + 36.0) % 360
        for collection in (self.particles, self.charge_particles, self.slash_vfx, self.lightning_bursts):
            for item in collection[:]:
                item.update()
                done = item.is_done() if hasattr(item, "is_done") else getattr(item, "life", 0) <= 0
                if done:
                    collection.remove(item)

    def _tick_cooldowns(self):
        self.melee_cd = max(0, self.melee_cd - 1)
        self.throw_cd = max(0, self.throw_cd - 1)
        self.thunder_cd = max(0, self.thunder_cd - 1)
        self.ultimate_cd = max(0, self.ultimate_cd - 1)
        self._taunt_cd = max(0, self._taunt_cd - 1)

    def _sync_weather(self, weather):
        self.weather_is_storm = False
        if weather and getattr(weather, "enabled", False):
            try:
                from Ditu.weather.constants import WeatherType
                rainy = (
                    WeatherType.THUNDERSTORM,
                    WeatherType.LIGHT_RAIN,
                    WeatherType.MODERATE_RAIN,
                    WeatherType.HEAVY_RAIN,
                )
                self.weather_is_storm = getattr(weather, "current_weather", None) in rainy
            except Exception:
                self.weather_is_storm = False
        if self.weather_is_storm:
            self.speed_bonus = 0.3
            self.thunder_range_bonus = 30
            self.thunder_dmg_bonus = 3
            self.ultimate_radius_bonus = 40
            self.ultimate_multiplier_bonus = 0.3
        else:
            self.speed_bonus = 0.0
            self.thunder_range_bonus = 0
            self.thunder_dmg_bonus = 0
            self.ultimate_radius_bonus = 0
            self.ultimate_multiplier_bonus = 0.0

    def _trigger_phase2_if_needed(self):
        if self._phase2_triggered or self.hp > self.max_hp * 0.5:
            return
        self._phase2_triggered = True
        self.phase = 2
        speed_mult = self.speed / self._phase1_base_speed
        self.speed = self._phase2_base_speed * speed_mult
        self.dmg_res = 0.22
        self.attack_range = 138
        self._say(("dk_p2_trigger",))
        for _ in range(70):
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, (60, 180, 230), speed_mult=2.4))

    def _say(self, keys):
        if self._speech_cooldown > 0:
            return
        for key in keys:
            if key in self._spoken_keys:
                continue
            self._pending_speech = t(key)
            self._spoken_keys.add(key)
            self._speech_cooldown = 330
            return

    def _select_target(self, enemies):
        alive = [enemy for enemy in enemies if enemy is not self and getattr(enemy, "hp", 0) > 0]
        if not alive:
            return None
        if self._last_attacker in alive:
            return self._last_attacker
        imprisoned = [enemy for enemy in alive if getattr(enemy, "_drowned_king_slow_timer", 0) > 0]
        if imprisoned:
            return min(imprisoned, key=lambda enemy: self._dist_to(enemy))
        low = [enemy for enemy in alive if enemy.hp <= enemy.max_hp * 0.25]
        if low:
            return min(low, key=lambda enemy: self._dist_to(enemy))
        ranged = [enemy for enemy in alive if enemy.__class__.__name__ in ("Skeleton", "Illusioner", "IllusionerClone")]
        if ranged:
            order = {"Skeleton": 0, "Illusioner": 1, "IllusionerClone": 2}
            return min(ranged, key=lambda enemy: (order.get(enemy.__class__.__name__, 9), self._dist_to(enemy)))
        return min(alive, key=lambda enemy: self._dist_to(enemy))

    def _dist_to(self, target):
        return math.hypot(target.rect.centerx - self.rect.centerx, target.rect.centery - self.rect.centery)

    def _update_facing(self, target):
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            self._facing = (dx / dist, dy / dist)

    def _update_idle(self, target):
        self.vx *= 0.82
        self.vy *= 0.82
        self.state_timer -= 1
        if self.state_timer <= 0 or self._swarmed(self._last_enemies if hasattr(self, '_last_enemies') else []):
            self._choose_next_state(target)

    def _update_chase(self, target):
        if not target:
            self._enter_state("IDLE")
            return
        if self._try_enter_priority_skill(target):
            return
        self._chase_offset_timer -= 1
        if self._chase_offset_timer <= 0:
            self._chase_offset = math.radians(random.uniform(-15, 15))
            self._chase_offset_timer = 60
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx) + self._chase_offset
        chase_scale = 1.1 if getattr(target, "_drowned_king_slow_timer", 0) > 0 else 1.0
        force = self._effective_speed() * chase_scale * 0.16
        self.vx += math.cos(angle) * force
        self.vy += math.sin(angle) * force

    def _update_melee(self, enemies):
        if not self._melee_data or self._melee_combo_index >= len(self._melee_data):
            self._enter_state("COOLDOWN")
            return None
        current = self._melee_data[self._melee_combo_index]
        self.state_timer -= 1
        self._melee_hit_age += 1
        if current["type"] == "slash_big" and self._melee_hit_age >= current["windup"] and self.spin_timer <= 0 and not self._melee_released:
            self.spin_timer = 10
            self.spin_angle = 0.0
        result = None
        if not self._melee_released and self._melee_hit_age >= current["windup"]:
            self._melee_released = True
            result = self._execute_melee_hit(current, enemies)
        if self.state_timer <= 0:
            self._melee_combo_index += 1
            if self._melee_combo_index < len(self._melee_data):
                next_hit = self._melee_data[self._melee_combo_index]
                self._melee_released = False
                self._melee_hit_age = 0
                self.state_timer = next_hit["windup"] + next_hit["recovery"] + 1
            else:
                self.melee_cd = 80 if self.phase == 2 else 115
                self._backstep = (-self._facing[0], -self._facing[1])
                self._enter_state("COOLDOWN")
                if hasattr(self, '_last_enemies') and self._swarmed(self._last_enemies):
                    self.state_timer = max(12, self.state_timer // 3)
        return result

    def _execute_melee_hit(self, data, enemies):
        if data["type"] == "thrust":
            self.thrust_scale_timer = 5
            self.rect.x += int(self._facing[0] * 60)
            self.rect.y += int(self._facing[1] * 60)
            for _ in range(6):
                angle = math.atan2(-self._facing[1], -self._facing[0]) + random.uniform(-0.55, 0.55)
                speed = random.uniform(1.4, 3.2)
                self.particles.append(DustParticle(self.rect.centerx, self.rect.centery, math.cos(angle) * speed, math.sin(angle) * speed))
            _safe_play(self.sfx_stab, 0.85)
            self._say(("dk_melee_stab",))
        elif data["type"] == "slash_small":
            self.slash_vfx.append(SlashArcVFX(self.rect.centerx, self.rect.centery, self._facing, radius=100, degrees=120, life=5))
            _safe_play(self.sfx_slash, 0.8)
            self._say(("dk_melee_slash_small",))
        else:
            self.slash_vfx.append(CircleSlashVFX(self.rect.centerx, self.rect.centery, radius=150, life=8))
            _safe_play(self.sfx_slash, 1.0)
            self._say(("dk_melee_slash_big",))

        if data["type"] == "thrust":
            hits = []
            fx, fy = self._facing
            for enemy in enemies:
                if enemy is self or getattr(enemy, "hp", 0) <= 0:
                    continue
                dx = enemy.rect.centerx - self.rect.centerx
                dy = enemy.rect.centery - self.rect.centery
                forward = dx * fx + dy * fy
                lateral = abs(dx * fy - dy * fx)
                if 0 <= forward <= data["range"] and lateral <= 45:
                    hits.append(enemy)
            if hits:
                result = {
                    "aoe_hits": [{"target": e, "damage": self._scaled_damage(data["damage"])} for e in hits],
                    "melee_type": data["type"],
                }
                return result
        else:
            hits = []
            arc_deg = data.get("arc", 360)
            for enemy in enemies:
                if enemy is self or getattr(enemy, "hp", 0) <= 0:
                    continue
                dx = enemy.rect.centerx - self.rect.centerx
                dy = enemy.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy)
                if dist <= data["range"] and dist > 0:
                    if arc_deg >= 360:
                        hits.append(enemy)
                    else:
                        dot = (dx / dist) * self._facing[0] + (dy / dist) * self._facing[1]
                        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
                        if angle <= arc_deg * 0.5:
                            hits.append(enemy)
            if hits:
                result = {
                    "aoe_hits": [{"target": e, "damage": self._scaled_damage(data["damage"])} for e in hits],
                    "melee_type": data["type"],
                }
                if data["type"] == "slash_big":
                    result["knockback"] = (self._facing[0] * 8, self._facing[1] * 8)
                return result
        return None

    def _update_throw(self, target, tridents_out):
        self.state_timer -= 1
        if self.state_age < 15:
            for idx in range(3):
                self.charge_particles.append(ChargeParticle(self, 48 + idx * 8, self.state_age * 0.28 + idx * 2.1))
        if target and not self._throw_released and self.state_age >= 15:
            self._throw_released = True
            dx = target.rect.centerx - self.rect.centerx
            dy = target.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy) or 1.0
            speed = 10 if self.phase == 2 else 7
            trident = Trident(self.rect.centerx, self.rect.centery, dx / dist * speed, dy / dist * speed, 35, self)
            tridents_out.append(trident)
            _safe_play(self.sfx_throw, 0.85)
            self._say(("dk_skill_throw_1", "dk_skill_throw_2"))
            side = random.choice([-1, 1])
            self.vx += -dy / dist * 2.0 * side
            self.vy += dx / dist * 2.0 * side
        if self.state_timer <= 0:
            self.throw_cd = 125 if self.phase == 2 else 225
            self._enter_state("COOLDOWN")

    def _update_thunder_charge(self):
        self.state_timer -= 1
        if self.state_age < 20:
            self.charge_particles.append(ChargeParticle(self, 58, self.state_age * 0.32))
        if not self._thunder_released and self.state_age >= 20:
            self._thunder_released = True
            self._thunder_charge_flag = True
            self._thunder_charge_data = {
                "duration": 300,
                "pulse_radius": 80 + self.thunder_range_bonus,
                "pulse_damage": 8 + self.thunder_dmg_bonus,
            }
            _safe_play(self.sfx_lightning, 0.9)
            self._say(("dk_thunder",))
        if self.state_timer <= 0:
            self.thunder_cd = 450 if self.phase == 2 else 750
            if self.phase == 2 and self._count_tridents(total=True) >= 8 and self.ultimate_cd <= 0:
                self._enter_state("ULTIMATE")
            else:
                self._enter_state("COOLDOWN")

    def _update_ultimate(self):
        self.state_timer -= 1
        if not self._ultimate_released and self.state_age >= 30:
            total = max(1, self._count_tridents(total=True))
            self._ultimate_released = True
            self._ultimate_flag = True
            self._ultimate_data = {
                "radius": 120 + self.ultimate_radius_bonus,
                "base_damage": 18,
                "damage_multiplier": 0.8 + self.ultimate_multiplier_bonus,
                "trident_count": total,
            }
            _safe_play(self.sfx_recall, 0.95)
            self._say(("dk_ult",))
        if self.state_timer <= 0:
            self.ultimate_cd = 900 if self.phase == 2 else 1500
            self._enter_state("COOLDOWN")

    def _update_weapon_recall(self):
        self.state_timer -= 1
        if self.state_age < 15:
            for idx in range(2):
                self.charge_particles.append(ChargeParticle(self, 54 + idx * 12, self.state_age * 0.24 + idx * math.pi))
        if not self._recall_released and self.state_age >= 15:
            self._recall_released = True
            self._recall_flag = True
            self._recall_heal_per = 15
            _safe_play(self.sfx_recall, 0.9)
            self._say(("dk_recall",))
        if self.state_timer <= 0:
            self._enter_state("IDLE")

    def _update_cooldown(self, target):
        self.state_timer -= 1
        if self._backstep != (0.0, 0.0):
            self.vx += self._backstep[0] * 0.18
            self.vy += self._backstep[1] * 0.18
        self.vx *= 0.92
        self.vy *= 0.92
        if self.state_timer <= 20 and target and self._swarmed(self._last_enemies if hasattr(self, '_last_enemies') else []):
            self._backstep = (-self._facing[0] * 1.8, -self._facing[1] * 1.8)
            self.vx += self._backstep[0] * 0.40
            self.vy += self._backstep[1] * 0.40
        if self.state_timer <= 0:
            self._backstep = (0.0, 0.0)
            if target and self._dist_to(target) <= self.attack_range:
                if not self._try_enter_priority_skill(target):
                    self._enter_state("IDLE")
            elif target:
                self._enter_state("CHASE")
            else:
                self._enter_state("IDLE")

    def _choose_next_state(self, target):
        if not target:
            self._enter_state("IDLE")
            return
        if self._try_enter_priority_skill(target):
            return
        self._enter_state("CHASE")

    def _try_enter_priority_skill(self, target):
        pinned = self._count_tridents(states=("pinned",))
        total = self._count_tridents(total=True)
        dist = self._dist_to(target) if target else 999999
        if total >= 3 and self.ultimate_cd <= 0:
            self._enter_state("ULTIMATE")
            return True
        if pinned >= 1 and self.thunder_cd <= 0:
            self._enter_state("THUNDER_CHARGE")
            return True
        if target and self._taunt_cd <= 0 and dist > self.attack_range * 1.2:
            self._enter_state("COMBAT_TAUNT")
            return True
        if target and dist <= self.attack_range and self.melee_cd <= 0:
            self._enter_state("MELEE_COMBO")
            return True
        if target and dist > 400 and self.throw_cd <= 0:
            self._enter_state("THROW")
            return True
        return False

    def _update_combat_taunt(self, target):
        if not target:
            self._taunt_target = None
            self._enter_state("IDLE")
            return
        self._taunt_target = target
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            rush_speed = self._effective_speed() * 2.8
            self.vx = dx / dist * rush_speed
            self.vy = dy / dist * rush_speed
        self._update_facing(target)
        if dist <= self.attack_range and self.melee_cd <= 0:
            self._taunt_target = None
            self._enter_state("MELEE_COMBO")
            return

    def _enter_state(self, state):
        if state not in self.STATES:
            state = "IDLE"
        self.state = state
        self.state_age = 0
        if state == "IDLE":
            self.state_timer = random.randint(20, 55)
        elif state == "CHASE":
            self.state_timer = 0
        elif state == "COMBAT_TAUNT":
            self._taunt_cd = 500 if self.phase == 1 else 350
            self.state_timer = self._taunt_duration
            self._backstep = (0.0, 0.0)
        elif state == "MELEE_COMBO":
            self._melee_data = self._roll_melee()
            self._melee_combo_index = 0
            self._melee_released = False
            self._melee_hit_age = 0
            current = self._melee_data[0]
            self.state_timer = current["windup"] + current["recovery"] + 1
        elif state == "THROW":
            self._throw_released = False
            self.state_timer = 65
        elif state == "THUNDER_CHARGE":
            self._thunder_released = False
            self.state_timer = 80
        elif state == "ULTIMATE":
            self._ultimate_released = False
            self.state_timer = 170
        elif state == "WEAPON_RECALL":
            self._recall_released = False
            self.state_timer = 45
        elif state == "COOLDOWN":
            self.state_timer = random.randint(18, 40)

    def _roll_melee(self):
        return [
            {"type": "thrust", "damage": 36, "range": 115, "arc": 40, "windup": 6, "recovery": 16},
            {"type": "slash_small", "damage": 30, "range": 125, "arc": 135, "windup": 5, "recovery": 13},
            {"type": "slash_big", "damage": 45, "range": 182, "arc": 360, "windup": 12, "recovery": 24},
        ]

    def _find_melee_target(self, enemies, data):
        best = None
        best_dist = 999999
        fx, fy = self._facing
        for enemy in enemies:
            if enemy is self or getattr(enemy, "hp", 0) <= 0:
                continue
            dx = enemy.rect.centerx - self.rect.centerx
            dy = enemy.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if data["type"] == "thrust":
                forward = dx * fx + dy * fy
                lateral = abs(dx * fy - dy * fx)
                ok = 0 <= forward <= data["range"] and lateral <= 38
            elif data["type"] == "slash_big":
                ok = dist <= data["range"]
            else:
                if dist <= 0:
                    ok = True
                else:
                    dot = (dx / dist) * fx + (dy / dist) * fy
                    angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
                    ok = dist <= data["range"] and angle <= data["arc"] * 0.5
            if ok and dist < best_dist:
                best = enemy
                best_dist = dist
        return best

    def _scaled_damage(self, base):
        return max(1, int(round(base * max(0.1, self.damage / 25))))

    def _effective_speed(self):
        return self.speed + self.speed_bonus

    def _should_recall(self):
        threshold = 15 if self.phase == 2 else 20
        return self._count_tridents(states=("pinned", "dropped")) >= threshold

    def _count_tridents(self, states=None, total=False):
        count = 0
        for trident in self.trident_list:
            if not getattr(trident, "active", False):
                continue
            if total:
                count += 1
            elif states and getattr(trident, "state", None) in states:
                count += 1
        return count

    def _move_and_clamp(self, bw, bh):
        wall_margin = 85
        push_strength = 0.13
        if self.rect.left < wall_margin:
            self.vx += push_strength * (1.0 - self.rect.left / wall_margin)
        elif self.rect.right > bw - wall_margin:
            self.vx -= push_strength * (1.0 - (bw - self.rect.right) / wall_margin)
        if self.rect.top < wall_margin:
            self.vy += push_strength * (1.0 - self.rect.top / wall_margin)
        elif self.rect.bottom > bh - wall_margin:
            self.vy -= push_strength * (1.0 - (bh - self.rect.bottom) / wall_margin)
        max_speed = 9.0 if self.phase == 1 else 11.0
        speed = math.hypot(self.vx, self.vy)
        if speed > max_speed:
            self.vx = self.vx / speed * max_speed
            self.vy = self.vy / speed * max_speed
        self.rect.x += int(round(self.vx))
        self.rect.y += int(round(self.vy))
        self.vx *= 0.90
        self.vy *= 0.90
        if self.rect.left < 0:
            self.rect.left = 0
            self.vx = abs(self.vx) * 0.45
        elif self.rect.right > bw:
            self.rect.right = bw
            self.vx = -abs(self.vx) * 0.45
        if self.rect.top < 0:
            self.rect.top = 0
            self.vy = abs(self.vy) * 0.45
        elif self.rect.bottom > bh:
            self.rect.bottom = bh
            self.vy = -abs(self.vy) * 0.45
