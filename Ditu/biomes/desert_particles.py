import pygame
import random
import math
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Particle:
    def __init__(self, x, y, color, life, speed=3, size=4):
        self.x, self.y = x, y
        self.color = color
        self.life = life
        angle = random.uniform(0, math.pi * 2)
        v = random.uniform(speed * 0.5, speed)
        self.vx = math.cos(angle) * v
        self.vy = math.sin(angle) * v
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))


class ExplosionParticle(Particle):
    def __init__(self, x, y):
        color = random.choice([(255, 69, 0), (255, 140, 0), (255, 215, 0), (50, 50, 50)])
        super().__init__(x, y, color, life=random.randint(20, 40), speed=8, size=random.randint(4, 10))


class DustParticle(Particle):
    def __init__(self, x, y):
        color = random.choice([(210, 180, 140), (194, 178, 128), (238, 214, 175)])
        super().__init__(x, y, color, life=random.randint(15, 30), speed=2, size=random.randint(3, 6))
