import pygame
import math
import random
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")

_ha_qi_img = None


def _get_ha_qi_image():
    global _ha_qi_img
    if _ha_qi_img is None:
        try:
            raw = pygame.image.load(os.path.join(SPRITES_DIR, "耄耋哈气.png")).convert_alpha()
            _ha_qi_img = pygame.transform.scale(raw, (90, 70))
        except Exception:
            _ha_qi_img = pygame.Surface((90, 70), pygame.SRCALPHA)
            _ha_qi_img.fill((180, 180, 200, 120))
    return _ha_qi_img


def get_ha_qi_image_for_face(size):
    img = _get_ha_qi_image()
    return pygame.transform.scale(img, (size, size))


class ClawSlash:
    def __init__(self, x, y, is_phase2=False):
        self.x, self.y = x, y
        self.life = 15
        self.max_life = 15
        self.size = 56
        self.color = (255, 200, 50)
        self.is_phase2 = is_phase2
        self.particles = []

    def update(self):
        self.life -= 1
        if self.is_phase2:
            if self.life > 0 and random.random() < 0.25:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1.5, 4)
                px = self.x + random.uniform(-12, 12)
                py = self.y + random.uniform(-12, 12)
                self.particles.append([px, py, math.cos(angle) * speed, math.sin(angle) * speed, random.randint(6, 14), 255])
            for p in self.particles[:]:
                p[0] += p[2]
                p[1] += p[3]
                p[2] *= 0.94
                p[3] *= 0.94
                p[3] += 0.08
                p[5] -= 12
                if p[5] <= 0:
                    self.particles.remove(p)

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int((self.life / self.max_life) * 255)

        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        if self.is_phase2:
            glow_alpha = int(alpha * 0.4)
            glow_s = pygame.Surface((self.size + 20, self.size + 20), pygame.SRCALPHA)
            pygame.draw.line(glow_s, (255, 120, 20, glow_alpha), (8, 8), (8, self.size + 12), 12)
            pygame.draw.line(glow_s, (255, 120, 20, glow_alpha), (23, 8), (23, self.size + 12), 12)
            pygame.draw.line(glow_s, (255, 120, 20, glow_alpha), (38, 8), (38, self.size + 12), 12)
            surface.blit(glow_s, (self.x - self.size // 2 - 10, self.y - self.size // 2 - 6))
        for i in range(3):
            color = (255, 120, 30) if self.is_phase2 else self.color
            pygame.draw.line(s, (*color, alpha),
                             (10 + i * 15, 10),
                             (5 + i * 15, self.size - 10), 5)
        surface.blit(s, (self.x - self.size // 2, self.y - self.size // 2))

        for p in self.particles:
            color_val = (255, 140, 20) if self.is_phase2 else self.color
            cs = int(p[4])
            s2 = pygame.Surface((cs, cs), pygame.SRCALPHA)
            s2.fill((*color_val, max(0, p[5])))
            surface.blit(s2, (int(p[0]) - cs // 2, int(p[1]) - cs // 2))


class DodgeGhost:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.image = image.copy() if image else None
        self.life = 12
        self.max_life = 12
        self.dir_x = random.uniform(-1, 1)
        self.dir_y = random.uniform(-0.6, -0.2)

    def update(self):
        self.life -= 1
        self.x += self.dir_x * 2
        self.y += self.dir_y * 2

    def draw(self, surface):
        if self.life <= 0 or not self.image:
            return
        alpha = int(160 * (self.life / self.max_life))
        ghost = self.image.copy()
        ghost.fill((200, 220, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
        ghost.set_alpha(alpha)
        r = ghost.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(ghost, r)


class HaQiAirWave:
    def __init__(self, x, y, facing_right):
        self.x = x
        self.y = y
        self.life = 32
        self.max_life = 32
        self.facing_right = facing_right
        self.sparks = []
        self.arcs = []
        self._shimmer_t = 0

    def update(self):
        self.life -= 1
        self._shimmer_t += 0.3

        if self.life in (30, 22, 14, 6):
            self.arcs.append({'offset': 0, 'alpha': 240, 'stretch': 1.0})

        for a in self.arcs:
            a['offset'] += 4.5
            a['alpha'] = max(0, a['alpha'] - 10)
            a['stretch'] = a['stretch'] * 1.06 + 0.08
        self.arcs = [a for a in self.arcs if a['alpha'] > 0]

        if self.life > 3 and random.random() < 0.6:
            spread = random.uniform(-0.5, 0.5)
            base_angle = 0 if self.facing_right else math.pi
            angle = base_angle + spread
            speed = random.uniform(3, 9)
            self.sparks.append({
                'x': self.x,
                'y': self.y + random.uniform(-14, 14),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(10, 25),
                'max_life': 25,
                'size': random.randint(2, 5),
            })

        for sp in self.sparks[:]:
            sp['x'] += sp['vx']
            sp['y'] += sp['vy']
            sp['vx'] *= 0.97
            sp['vy'] *= 0.97
            sp['life'] -= 1
            if sp['life'] <= 0:
                self.sparks.remove(sp)

    def draw(self, surface):
        if self.life <= 0:
            return
        progress = self.life / self.max_life
        master_alpha = int(255 * progress)
        cx = int(self.x)
        cy = int(self.y)
        direction = 1 if self.facing_right else -1

        for a in self.arcs:
            arc_alpha = int(a['alpha'] * progress)
            if arc_alpha < 6:
                continue
            ox = int(a['offset'] * direction)
            rx = int(a['stretch'] * 36)
            ry = int(a['stretch'] * 28)

            arc_surf = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
            acx = rx + 2
            acy = ry + 2

            for layer in range(3):
                la = int(arc_alpha * (0.25 + layer * 0.25))
                if la <= 0:
                    continue
                lr = int(rx - layer * 4)
                lry = int(ry - layer * 3)
                if lr < 2 or lry < 2:
                    continue
                color_shift = layer * 30
                r = min(255, 180 + color_shift)
                g = min(255, 210 + color_shift)
                b = min(255, 250)
                pygame.draw.ellipse(arc_surf, (r, g, b, la),
                                    (acx - lr, acy - lry, lr * 2, lry * 2), max(1, 3 - layer))

            surface.blit(arc_surf, (cx + ox - rx - 2, cy - ry - 2))

        streak_w = int(30 * progress + 10)
        for i in range(6):
            sy = cy - 18 + i * 7 + int(math.sin(self._shimmer_t + i) * 6)
            sa = int(master_alpha * 0.5 * (1.0 - abs(i - 2.5) / 3.0))
            if sa < 8:
                continue
            streak = pygame.Surface((streak_w + 10, 4), pygame.SRCALPHA)
            for col in range(streak_w):
                fade = 1.0 - (col / streak_w) ** 1.5
                ca = int(sa * fade)
                streak.set_at((col, 1), (180, 210, 255, ca))
                streak.set_at((col, 2), (200, 230, 255, ca // 2))
            px = cx if self.facing_right else cx - streak_w
            surface.blit(streak, (px, sy - 2))

        flash_a = int(master_alpha * 0.5)
        if flash_a > 0:
            flash_size = int(16 * progress + 8)
            flash = pygame.Surface((flash_size * 2, flash_size * 2), pygame.SRCALPHA)
            for r in range(flash_size, 0, -2):
                ratio = r / flash_size
                fa = int(flash_a * (ratio ** 3))
                pygame.draw.circle(flash, (255, 255, 255, fa), (flash_size, flash_size), r)
            surface.blit(flash, (cx - flash_size, cy - flash_size))

        for sp in self.sparks:
            sa = int((sp['life'] / sp['max_life']) * master_alpha)
            ss = int(sp['size'])
            s = pygame.Surface((ss, ss), pygame.SRCALPHA)
            s.fill((200, 240, 255, max(0, sa)))
            surface.blit(s, (int(sp['x']) - ss // 2, int(sp['y']) - ss // 2))


class CrossSlash:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.life = 12
        self.max_life = 12
        self.rotation = random.uniform(0, math.pi * 2)
        self._surface = pygame.Surface((120, 120), pygame.SRCALPHA)

    def update(self):
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        progress = self.life / self.max_life
        alpha = int(240 * progress)

        self._surface.fill((0, 0, 0, 0))

        size = int(20 + (1.0 - progress) * 45)
        sweep = (1.0 - progress) * 0.9
        angle1 = self.rotation + sweep
        angle2 = angle1 + math.pi / 2

        cx = 60
        cy = 60
        for angle, color in [(angle1, (255, 220, 50)), (angle2, (255, 100, 30))]:
            ex = cx + int(math.cos(angle) * size)
            ey = cy + int(math.sin(angle) * size)
            bx = cx - int(math.cos(angle) * size * 0.15)
            by = cy - int(math.sin(angle) * size * 0.15)
            pygame.draw.line(self._surface, (20, 10, 5, alpha), (bx - 1, by - 1), (ex + 1, ey + 1), 8)
            pygame.draw.line(self._surface, (*color, alpha), (bx, by), (ex, ey), 4)

        surface.blit(self._surface, (self.x - 60, self.y - 60))
