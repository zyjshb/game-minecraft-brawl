import pygame
import random
import math
import os

from .desert_traps import SandstoneBlock, TrapDispenser, TrapTNT
from .desert_particles import BASE_DIR, DustParticle

SFX_DIR = os.path.join(BASE_DIR, "SFX", "shang-mo")


class DesertEnvironment:
    def __init__(self, bw, bh, safe_zones, target_size):
        self.bw = bw
        self.bh = bh
        self.base_safe_zones = safe_zones

        try:
            self.sfx_piston = pygame.mixer.Sound(os.path.join(SFX_DIR, "活塞的伸出音效.mp3"))
        except:
            self.sfx_piston = None

        self.blocks = []
        self.dispensers = []
        self.tnts = []
        self.arrows = []
        self.particles = []

        self.refresh_timer = 0
        self.refresh_interval = 600
        self.layout_density = {"大": 15, "中": 10, "小": 6}.get(target_size, 10)

        self._refresh_layout(initial=True)

    def _get_random_valid_pos(self, size, extra_rects):
        for _ in range(50):
            x = random.randint(100, self.bw - size - 100)
            y = random.randint(100, self.bh - size - 100)
            rect = pygame.Rect(x, y, size, size)
            if not any(rect.colliderect(sz) for sz in self.base_safe_zones):
                if not any(rect.colliderect(er) for er in extra_rects):
                    return x, y, rect
        return -1000, -1000, pygame.Rect(-1000, -1000, size, size)

    def _refresh_layout(self, initial=False):
        current_rects = []
        if initial:
            for _ in range(self.layout_density):
                x, y, r = self._get_random_valid_pos(60, current_rects)
                self.blocks.append(SandstoneBlock(x, y))
                current_rects.append(r)
        else:
            if self.sfx_piston:
                self.sfx_piston.play()

            new_blocks = []
            new_dispensers = []
            new_tnts = []

            for b in self.blocks:
                rand_val = random.random()
                if rand_val < 0.2:
                    new_tnts.append(TrapTNT(b.rect.x, b.rect.y))
                    for _ in range(5):
                        self.particles.append(DustParticle(b.rect.centerx, b.rect.centery))
                elif rand_val < 0.4:
                    d = random.choice(["up", "down", "left", "right"])
                    new_dispensers.append(TrapDispenser(b.rect.x, b.rect.y, d))
                    for _ in range(5):
                        self.particles.append(DustParticle(b.rect.centerx, b.rect.centery))
                else:
                    new_blocks.append(b)

            self.blocks = new_blocks
            self.dispensers = new_dispensers
            self.tnts.extend(new_tnts)

            current_rects = [b.rect for b in self.blocks] + [d.rect for d in self.dispensers] + [t.rect for t in self.tnts]

            for _ in range(3):
                x, y, r = self._get_random_valid_pos(60, current_rects)
                self.blocks.append(SandstoneBlock(x, y))
                current_rects.append(r)

    def update(self, fighters, external_blocks=None, external_particles=None):
        self.refresh_timer += 1
        if self.refresh_timer >= self.refresh_interval:
            self.refresh_timer = 0
            self._refresh_layout()

        for b in self.blocks:
            b.update()
            for f in fighters:
                b.process_collision(f, self)

        for d in self.dispensers:
            d.update(self)
            for f in fighters:
                d.process_collision(f)

        for tnt in self.tnts[:]:
            tnt.update(fighters, self, external_blocks, external_particles)
            if tnt.exploded:
                self.tnts.remove(tnt)

        for arrow in self.arrows[:]:
            arrow.update(fighters, self.blocks + self.dispensers, self)
            if not arrow.active or arrow.rect.x < -200 or arrow.rect.x > self.bw + 200 or arrow.rect.y < -200 or arrow.rect.y > self.bh + 200:
                self.arrows.remove(arrow)

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw_bottom(self, surface):
        for t in self.tnts:
            t.draw(surface)

    def draw_top(self, surface):
        for b in self.blocks:
            b.draw(surface)
        for d in self.dispensers:
            d.draw(surface)
        for a in self.arrows:
            a.draw(surface)
        for p in self.particles:
            p.draw(surface)
