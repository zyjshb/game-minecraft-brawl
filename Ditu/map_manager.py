import pygame
import math
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from world import MineralBlock


class MapManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.blocks = []
        self.particles = []
        self.allow_regenerate = True
        self._fixed_ocean_block_rects = []
        self._is_ocean = False

    def generate_blocks(self, fighters):
        mineral_names = ["铁矿石", "砖石矿", "金矿", "石头", "青金石"]
        num_blocks = random.randint(5, 10)

        for _ in range(num_blocks):
            name = random.choice(mineral_names)
            attempts = 0
            while attempts < 100:
                bx = random.randint(50, self.width - 100)
                by = random.randint(50, self.height - 100)

                conflict = False
                for f in fighters:
                    if math.hypot(bx - f.rect.centerx, by - f.rect.centery) < 120:
                        conflict = True
                        break
                if conflict:
                    attempts += 1
                    continue

                new_rect = pygame.Rect(bx, by, 50, 50)
                is_overlapping = False
                for existing_block in self.blocks:
                    if new_rect.colliderect(existing_block.rect.inflate(20, 20)):
                        is_overlapping = True
                        break

                if not is_overlapping:
                    self.blocks.append(MineralBlock(bx, by, name))
                    break
                attempts += 1

    def generate_ocean_blocks(self, fighters):
        from world import PrismarineBlock
        self._is_ocean = True
        self._fixed_ocean_block_rects = []
        mw, mh = self.width, self.height
        margin = 100

        fixed_positions = [
            (margin, margin),
            (mw - margin, margin),
            (margin, mh - margin),
            (mw - margin, mh - margin),
            ((margin + (mw - margin)) // 2, margin),
            ((margin + (mw - margin)) // 2, mh - margin),
            (margin, (margin + (mh - margin)) // 2),
            (mw - margin, (margin + (mh - margin)) // 2),
        ]
        for x, y in fixed_positions:
            conflict = False
            for f in fighters:
                if math.hypot(x - f.rect.centerx, y - f.rect.centery) < 140:
                    conflict = True
                    break
            if not conflict:
                b = PrismarineBlock(x, y)
                self.blocks.append(b)
                self._fixed_ocean_block_rects.append(b.rect)

        self._spawn_center_ocean_blocks(fighters)

    def _spawn_center_ocean_blocks(self, fighters):
        from world import PrismarineBlock
        mw, mh = self.width, self.height
        count = random.randint(2, 3)
        for _ in range(count * 3):
            if _ >= 20:
                break
            bx = random.randint(mw // 3, 2 * mw // 3)
            by = random.randint(mh // 3, 2 * mh // 3)
            tr = pygame.Rect(bx, by, 48, 48)
            conflict = False
            for f in fighters:
                if math.hypot(bx - f.rect.centerx, by - f.rect.centery) < 100:
                    conflict = True
                    break
            for eb in self.blocks:
                if eb.active and tr.colliderect(eb.rect.inflate(20, 20)):
                    conflict = True
                    break
            for fr in self._fixed_ocean_block_rects:
                if tr.colliderect(fr.inflate(20, 20)):
                    conflict = True
                    break
            if not conflict:
                self.blocks.append(PrismarineBlock(bx, by))
                count -= 1
                if count <= 0:
                    break

    def _count_active_center_ocean(self):
        n = 0
        for b in self.blocks:
            if b.active and b.rect not in self._fixed_ocean_block_rects:
                n += 1
        return n

    def update(self, fighters=None, extra_avoid=None):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        if self._is_ocean:
            center_alive = self._count_active_center_ocean()
            if center_alive < 2:
                self._spawn_center_ocean_blocks(fighters or [])
        elif self.allow_regenerate:
            active_count = sum(1 for b in self.blocks if b.active)
            if active_count < 4:
                mineral_names = ["铁矿石", "砖石矿", "金矿", "石头", "青金石"]
                for _ in range(50):
                    bx = random.randint(50, self.width - 100)
                    by = random.randint(50, self.height - 100)
                    nr = pygame.Rect(bx, by, 50, 50)
                    conflict = False
                    if fighters:
                        for f in fighters:
                            if math.hypot(bx - f.rect.centerx, by - f.rect.centery) < 100:
                                conflict = True
                                break
                    for eb in self.blocks:
                        if eb.active and nr.colliderect(eb.rect.inflate(20, 20)):
                            conflict = True
                            break
                    if extra_avoid:
                        for av in extra_avoid:
                            if nr.colliderect(av.inflate(40, 40)):
                                conflict = True
                                break
                    if not conflict:
                        self.blocks.append(MineralBlock(bx, by, random.choice(mineral_names)))
                        break

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        for b in self.blocks:
            if b.active:
                b.draw(surface)
