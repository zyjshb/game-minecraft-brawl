# Jue_se/zombie.py
import pygame
import math
import os
import random
from entity import Entity, Particle
from ._sfx import play_sfx

# 路径定位
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) 
SFX_DIR = os.path.join(BASE_DIR, "SFX", "jiang-shi")
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")

class ClawSlash:
    def __init__(self, x, y, is_giant, boss_mode=False):
        self.x, self.y = x, y
        self.life = 18 if boss_mode else 15
        self.is_boss_mode = boss_mode
        if boss_mode:
            self.size = 60
            self.color = (180, 30, 30)
        elif is_giant:
            self.size = 80
            self.color = (255, 50, 50)
        else:
            self.size = 50
            self.color = (200, 200, 200)

    def update(self): self.life -= 1
    def draw(self, surface):
        if self.life > 0:
            ratio = self.life / (18 if self.is_boss_mode else 15)
            alpha = int(ratio * 255)
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            n = 3
            gap = (self.size - 30) // max(1, n - 1)
            for i in range(n):
                x0 = 10 + i * gap
                x1 = 8 + i * gap
                w = 3
                pygame.draw.line(s, (*self.color, alpha), (x0, 10), (x1, self.size - 10), w)
            surface.blit(s, (self.x - self.size // 2, self.y - self.size // 2))

class Zombie(Entity):
    def __init__(self, x, y, size=50):
        super().__init__(x, y, size, 100)
        self.base_size = size
        self.is_giant = False
        self.last_bounce_time = 0 
        
        # 属性设定
        self.speed = 0.6 
        self.kb_res = 0.4    
        self.dmg_res = 0.0   
        
        # 🌟 修改：普通状态伤害从 5 提升到 10
        self.damage = 10
        
        self.attack_cd = 0
        self.attack_range = 65
        self.slashes = []
        self.particles = []
        self.has_endured = False 
        self.ai_lock_timer = 0
        self.load_assets()

    def load_assets(self):
        try:
            p = os.path.join(SPRITES_DIR, "僵尸.webp")
            self.orig_image = pygame.image.load(p).convert_alpha()
            self.image = pygame.transform.scale(self.orig_image, (self.size, self.size))
        except: self.orig_image = self.image = None
        
        try:
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"僵尸的受伤的音效{i}.mp3")) for i in [1, 2]]
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "僵尸的死亡音效.mp3"))
        except: self.sfx_hurt = []; self.sfx_die = None

        try:
            self.sfx_bounce = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"僵尸的撞击声{i}.mp3")) for i in [1, 2, 3]]
        except: 
            self.sfx_bounce = []

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0: return

        actual_damage = amount * (1.0 - self.dmg_res)
        
        if self._boss_mode:
            actual_damage = int(actual_damage)
            if actual_damage < 1:
                actual_damage = 1
            would_die = (self.hp - actual_damage) <= 0
            if would_die and not self.is_giant:
                self.hp = 1
                self.trigger_damage_flash()
            else:
                self.hp -= actual_damage
                self.trigger_damage_flash()
        elif (self.hp - actual_damage) <= 0 and not self.has_endured:
            self.hp = 1
            self.has_endured = True 
            self.trigger_damage_flash()
        else:
            self.hp -= actual_damage
            self.trigger_damage_flash()

        if self.hp <= 0:
            if self.sfx_die: play_sfx(self.sfx_die)
            return

        if self.sfx_hurt: play_sfx(random.choice(self.sfx_hurt))
        
        if self.hp < 20 and not self.is_giant: 
            self._trigger_gigantification()
            try:
                from i18n import t as _tt
                self._pending_speech = _tt("p2_zombie")
            except Exception:
                self._pending_speech = "彻底疯狂！！"

    def _trigger_gigantification(self):
        self.is_giant = True
        self.has_endured = True 

        if self._boss_mode:
            self.hp = 160
            self.dmg_res = 0.95
            self.kb_res = 0.99
            self.speed = 1.5
            self.damage = 6
            self.attack_range = 185
            self._boss_chase_speed = 0.60
        else:
            self.hp = 60
            self.dmg_res = 0.15
            self.kb_res = 0.85
            self.speed = 0.9
            self.damage = 15
            self.attack_range = 90

        self.size = int(self.base_size * 1.6)
        self.rect.size = (self.size, self.size)
        if self.orig_image:
            self.image = pygame.transform.scale(self.orig_image, (self.size, self.size))

    def _on_boss_mode(self):
        self.is_giant = False
        self.max_hp = self.hp = int(self.max_hp * 3.0)
        self.dmg_res = 0.40
        self.kb_res = 0.98
        self.speed = 1.2
        self.damage = 7
        self.attack_range = 175
        self._boss_chase_speed = 0.50
        self._charge_used = False
        self._charge_timer = 0

    def update(self, enemies, bw, bh):
        if self.hp <= 0: return None
        self.update_buffs()
        if self._boss_mode:
            self._boss_move_only(bw, bh)
        else:
            self.apply_physics(bw, bh)
        for s in self.slashes[:]:
            s.update()
            if s.life <= 0: self.slashes.remove(s)
        if self.attack_cd > 0: self.attack_cd -= 1
        
        closest_enemy = None
        min_dist = 9999
        for enemy in enemies:
            if enemy == self or enemy.hp <= 0: continue
            d = math.hypot(enemy.rect.centerx - self.rect.centerx, enemy.rect.centery - self.rect.centery)
            if d < min_dist: min_dist = d; closest_enemy = enemy
            
        if closest_enemy:
            if min_dist < self.attack_range and self.attack_cd <= 0:
                cd = 80 if self._boss_mode else 60
                self.attack_cd = cd
                self.slashes.append(ClawSlash(closest_enemy.rect.centerx, closest_enemy.rect.centery, self.is_giant, boss_mode=self._boss_mode))
                return {"target": closest_enemy, "damage": self.damage}
            else:
                dx = closest_enemy.rect.centerx - self.rect.centerx
                dy = closest_enemy.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy) or 1
                if self._boss_mode:
                    if self._charge_timer > 0:
                        self._charge_timer -= 1
                        self.vx += (dx / dist) * 2.00
                        self.vy += (dy / dist) * 2.00
                    elif dist > self.attack_range * 1.6 and not self._charge_used:
                        self._charge_used = True
                        self._charge_timer = 18
                        self.vx += (dx / dist) * 3.00
                        self.vy += (dy / dist) * 3.00
                        from entity import FloatText
                        self.float_texts.append(FloatText(self.rect.centerx, self.rect.top - 25, "无畏冲锋!", (255, 80, 0)))
                    else:
                        self.vx += (dx / dist) * self._boss_chase_speed
                        self.vy += (dy / dist) * self._boss_chase_speed
                else:
                    self.vx += (dx / dist) * 0.1
                    self.vy += (dy / dist) * 0.1
        return None

    def _boss_move_only(self, bw, bh):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.vx *= 0.88
        self.vy *= 0.88
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(bw, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(bh, self.rect.bottom)

    def draw(self, surface):
        if self.hp <= 0: return
        draw_img = self.image
        if self.is_giant:
            draw_img = self.image.copy()
            draw_img.fill((255, 50, 50, 150), special_flags=pygame.BLEND_RGBA_MULT)
            pygame.draw.rect(surface, (255, 0, 0), self.rect.inflate(8, 8), 2)
            surface.blit(draw_img, self.rect)
        elif self.image:
            surface.blit(self.image, self.rect)
        if self.damage_flash_timer > 0 and self.image:
            flash = self.image.copy()
            flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)
        self._draw_hp(surface)
        for s in self.slashes: s.draw(surface)
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)
            else:
                p.draw(surface)
        self.draw_float_texts(surface)

    def _draw_hp(self, surface):
        hy = max(10, self.rect.y - 10)
        hp_pct = max(0, self.hp / max(1, self.max_hp))
        pygame.draw.rect(surface, (255,0,0), (self.rect.x, hy, self.size, 5))
        pygame.draw.rect(surface, (0,255,0), (self.rect.x, hy, int(hp_pct * self.size), 5))
    
    def play_bounce_sfx(self):
        now = pygame.time.get_ticks()
        if now - getattr(self, 'last_bounce_time', 0) > 600: # 1. 冷却
            if hasattr(self, 'sfx_bounce') and self.sfx_bounce:
                if random.random() < 0.4: # 2. 概率
                    sound = random.choice(self.sfx_bounce)
                    sound.set_volume(0.4)
                    play_sfx(sound, volume=0.4)
                self.last_bounce_time = now
    

    def on_wall_hit(self):
        self.play_bounce_sfx()