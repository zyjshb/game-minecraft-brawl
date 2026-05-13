import pygame
import math
import os
import random
from entity import Entity, Particle
from ._sfx import play_sfx

BASE_DIR = os.path.dirname(os.path.dirname(__file__)) # 🌟 向上跳一级，回到根目录
SFX_DIR = os.path.join(BASE_DIR, "SFX", "ku-li-pa")
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")

# BASE_DIR = os.path.dirname(__file__)
# SFX_DIR = os.path.join(BASE_DIR, "SFX", "ku-li-pa")
# SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")

class ShockwaveRing:
    def __init__(self, x, y, max_radius, color=(255, 255, 255)):
        self.x, self.y, self.radius, self.max_radius = x, y, 10, max_radius
        self.thickness, self.alpha = 20, 255
        self.color = color 

    def update(self):
        self.radius += 12 * (self.max_radius / 160); self.thickness -= 1; self.alpha -= 10
        
    def draw(self, surface):
        if self.alpha > 0 and self.radius < self.max_radius:
            s = pygame.Surface((int(self.max_radius * 2), int(self.max_radius * 2)), pygame.SRCALPHA)
            draw_color = (*self.color, max(0, int(self.alpha)))
            pygame.draw.circle(s, draw_color, (int(self.max_radius), int(self.max_radius)), int(self.radius), int(self.thickness))
            surface.blit(s, (self.x - self.max_radius, self.y - self.max_radius))

class Creeper(Entity):
    def __init__(self, x, y, size=50):
        super().__init__(x, y, size, 100)
        self.state, self.is_charged, self.fuse_timer = "IDLE", False, 0
        self.particles, self.shockwave = [], None
        self._roll_timer = 0
        self._roll_cd = 0
        self._explode_cd = 0
        self._exploded_once = False
        self._pending_death_explosion = False
        self.load_assets()

    def load_assets(self):
        try:
            self.image = pygame.transform.scale(pygame.image.load(os.path.join(SPRITES_DIR, "苦力怕.webp")).convert_alpha(), (self.size, self.size))
        except:
            self.image = None
        try:
            self.sfx_fuse = pygame.mixer.Sound(os.path.join(SFX_DIR, "苦力怕即将爆炸音效.mp3"))
            self.sfx_boom = pygame.mixer.Sound(os.path.join(SFX_DIR, "苦力怕爆炸影响.mp3"))
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"苦力怕受伤音效{i}.mp3")) for i in [1, 2]]
            self.sfx_hurt.append(pygame.mixer.Sound(os.path.join(SFX_DIR, "苦力怕受伤3.mp3")))
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "苦力怕死亡音效.mp3"))
        except:
            self.sfx_fuse = self.sfx_boom = self.sfx_die = None
            self.sfx_hurt = []

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0:
            return

        if self._boss_mode:
            would_die = (self.hp - amount) <= 0
            if would_die and not self._exploded_once:
                self.hp = 1
                self.trigger_damage_flash()
                self.is_charged = True
                self._pending_death_explosion = True
                return

        self.hp -= amount
        self.trigger_damage_flash()
        if self.hp <= 0:
            if hasattr(self, 'sfx_die'): play_sfx(self.sfx_die)
            if hasattr(self, 'sfx_fuse'): self.sfx_fuse.stop()
            self.state = "IDLE"
        elif self.sfx_hurt: play_sfx(random.choice(self.sfx_hurt))

    def _on_boss_mode(self):
        self.max_hp = self.hp = 180
        self.is_charged = True
        self._boss_fuse_range = 140
        self._boss_explode_dmg = 70
        self._boss_explode_radius = 280
        self._boss_roll_speed = 1.80
        self._boss_chase_speed = 0.65
        self.dmg_res = 0.28

    def update(self, target_rect, bw, bh):
        self.update_buffs()
        if self._boss_mode:
            if not hasattr(self, 'fx'): self.fx, self.fy = float(self.rect.x), float(self.rect.y)
            self.fx += self.vx
            self.fy += self.vy
            self.vx *= 0.90
            self.vy *= 0.90
            self.fx = max(10.0, min(float(bw - self.size - 10), self.fx))
            self.fy = max(10.0, min(float(bh - self.size - 10), self.fy))
            self.rect.x, self.rect.y = int(self.fx), int(self.fy)
        else:
            self.apply_physics(bw, bh)
        if self.shockwave: self.shockwave.update()
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

        if self._boss_mode and (self._pending_death_explosion or (self.hp <= 1 and not self._exploded_once)):
            self._pending_death_explosion = False
            self._exploded_once = True
            if hasattr(self, 'sfx_boom'):
                try:
                    play_sfx(self.sfx_boom)
                except:
                    pass
            exp_color = (0, 255, 255)
            r = self._boss_explode_radius
            self.shockwave = ShockwaveRing(self.rect.centerx, self.rect.centery, r, exp_color)
            for _ in range(60):
                self.particles.append(Particle(self.rect.centerx, self.rect.centery, exp_color, 3))
            self.hp = 0
            if hasattr(self, 'sfx_die'): play_sfx(self.sfx_die)
            return {"damage": self._boss_explode_dmg * 8, "radius": r, "mult": 4, "x": self.rect.centerx, "y": self.rect.centery}

        if self.hp <= 0 or target_rect is None:
            if self.state == "FUSE":
                self.state = "IDLE"
                if hasattr(self, 'sfx_fuse'): self.sfx_fuse.stop()
            return None

        if self._boss_mode and target_rect:
            dist = math.hypot(target_rect.centerx - self.rect.centerx, target_rect.centery - self.rect.centery)
            dx = target_rect.centerx - self.rect.centerx
            dy = target_rect.centery - self.rect.centery

            if self._explode_cd > 0:
                self._explode_cd -= 1

            if dist < self._boss_fuse_range and self._explode_cd <= 0:
                self._explode_cd = 140
                self._exploded_once = True
                result = self._explode(dist)
                if result:
                    result["damage"] = self._boss_explode_dmg * result["mult"]
                return result

            if dist > 0:
                speed = self._boss_roll_speed if dist > 180 else self._boss_chase_speed
                self.vx += (dx / dist) * speed
                self.vy += (dy / dist) * speed
            return None

        if target_rect:
            dist = math.hypot(target_rect.centerx - self.rect.centerx, target_rect.centery - self.rect.centery)

            if self.hp <= 50 and not self.is_charged:
                self.is_charged = True

            if self.state == "IDLE" and dist < 120:
                self.state = "FUSE"
                self.fuse_timer = 45
                if hasattr(self, 'sfx_fuse'): play_sfx(self.sfx_fuse)
            elif self.state == "FUSE":
                if dist > 140:
                    self.state = "IDLE"
                    if hasattr(self, 'sfx_fuse'): self.sfx_fuse.stop()
                else:
                    self.fuse_timer -= 1
                    if self.fuse_timer <= 0:
                        return self._explode(dist)
            if self.state in ("IDLE", "FUSE") and dist > 0:
                self.vx += (target_rect.centerx - self.rect.centerx) / dist * 0.25
                self.vy += (target_rect.centery - self.rect.centery) / dist * 0.25

        return None

    def _explode(self, dist):
        mult = 2 if self.is_charged else 1
        if self._boss_mode:
            r = self._boss_explode_radius
            self_dmg = 5
        else:
            r = 160 * mult
            self_dmg = 0 if self.is_charged else 10
        self.hp -= self_dmg
        if self.hp <= 0 and hasattr(self, 'sfx_fuse'):
            self.sfx_fuse.stop()
        if hasattr(self, 'sfx_boom'): play_sfx(self.sfx_boom)
        
        self.vx += random.uniform(-8, -2) * mult
        self.vy += random.uniform(-8, -2) * mult
        
        exp_color = (0, 191, 255) if self.is_charged else (255, 255, 255)
        self.shockwave = ShockwaveRing(self.rect.centerx, self.rect.centery, r, exp_color)
        for _ in range(40 * mult): 
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, exp_color, mult))
            
        self.state = "IDLE"
        # 这是原来的最后两行
        self.state = "IDLE"
        
        # 🌟 替换这里的 return，把伤害和推力数据传出去
        return {
            "dist": dist, 
            "radius": r, 
            "mult": mult, 
            "x": self.rect.centerx, 
            "y": self.rect.centery,
            "damage": 20 * mult,      # 👈 苦力怕自己决定炸多少血！
            "knockback": 20 * mult    # 👈 苦力怕自己决定把人推多远！
        }
    

    def draw(self, surface):
        if self.shockwave: self.shockwave.draw(surface)
        if self.hp > 0:
            draw_img = self.image
            if self.is_charged:
                for _ in range(3):
                    start_pt = (self.rect.centerx + random.randint(-25, 25), self.rect.centery + random.randint(-25, 25))
                    end_pt = (start_pt[0] + random.randint(-10, 10), start_pt[1] + random.randint(-10, 10))
                    pygame.draw.line(surface, (0, 255, 255), start_pt, end_pt, 2)
                pygame.draw.rect(surface, (0,255,255), self.rect.inflate(10,10), 2)
                
            if self.state == "FUSE" and (self.fuse_timer // 5) % 2 == 0:
                pygame.draw.rect(surface, (255, 255, 255), self.rect)
            elif self.image: 
                if self.is_charged:
                    draw_img = self.image.copy()
                    draw_img.fill((0, 100, 255, 100), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(draw_img, self.rect)
                else:
                    surface.blit(self.image, self.rect)
            if self.damage_flash_timer > 0 and self.image:
                flash = self.image.copy()
                flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(flash, self.rect)
            self._draw_hp(surface)
            self.draw_float_texts(surface)
        for p in self.particles: p.draw(surface)

    def _draw_hp(self, surface):
        hy = max(10, self.rect.y - 10)
        hp_pct = max(0, self.hp / max(1, self.max_hp))
        pygame.draw.rect(surface, (255,0,0), (self.rect.x, hy, self.size, 5))
        pygame.draw.rect(surface, (0,255,0), (self.rect.x, hy, int(hp_pct * self.size), 5))