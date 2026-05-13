# Jue_se/enderman.py
import pygame
import os
import random
import math
from entity import Entity
from ._sfx import play_sfx

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX", "xiao-hei")

class PurpleParticle:
    def __init__(self, x, y, is_attack=False):
        self.x, self.y = x, y
        if is_attack:
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(4, 9)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.life = random.randint(6, 12) 
            self.size = random.randint(5, 8)  
        else:
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(-1.0, -0.2)
            self.life = random.randint(20, 40)
            self.size = random.randint(2, 4)

        self.max_life = self.life
        self.color = random.choice([(255, 0, 255), (160, 32, 240), (230, 130, 255)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9 
        self.vy *= 0.9
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = int((self.life / self.max_life) * 255)
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surface.blit(s, (self.x, self.y))

class AttackVFX:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = 10 
        self.max_life = 10

    def update(self):
        self.life -= 1

    def draw(self, surface):
        progress = (self.max_life - self.life) / self.max_life
        rect_size = int(10 + progress * 70)
        alpha = int((self.life / self.max_life) * 200)
        
        vfx_rect = pygame.Rect(0, 0, rect_size, rect_size)
        vfx_rect.center = (self.x, self.y)
        
        pygame.draw.rect(surface, (255, 100, 255, alpha), vfx_rect, 3) 
        inner_rect = vfx_rect.inflate(-10, -10)
        if inner_rect.width > 0:
            pygame.draw.rect(surface, (200, 0, 200, alpha // 2), inner_rect, 2) 

class Enderman(Entity):
    def __init__(self, x, y, size=60):
        super().__init__(x, y, size, 100) 
        self.speed = 1.5 
        self.tp_cd = 60  
        self.attack_cd = 0
        self.damage = 20 
        self.angry = False
        self.revenge_target = None
        self.prev_hp = self.hp
        self.last_bw, self.last_bh = 1024, 1024
        self.particles = []
        self.vfx_list = [] 
        self.last_bounce_time = 0
        self.wander_timer = 0
        self.wander_dir_x = self.wander_dir_y = 0
        self.dirt_place_cd = 180
        self.dirt_place_cd_max = 600
        self.combo_lock_timer = 0
        self.load_assets()

    def _on_boss_mode(self):
        if self._boss_target:
            self.angry = True
            self.revenge_target = self._boss_target
            self.speed = 2.2
            self.damage = 38
            self.max_hp = self.hp = 280
            self.dmg_res = 0.32
            self._boss_attack_range = 115

    def load_assets(self):
        try:
            p = os.path.join(SPRITES_DIR, "小黑.webp")
            self.image = pygame.transform.scale(pygame.image.load(p).convert_alpha(), (self.size, self.size))
        except: 
            self.image = pygame.Surface((self.size, self.size)); self.image.fill((100, 0, 100))
        try:
            self.sfx_tp = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小黑的传送音效{i}.mp3")) for i in [1, 2]]
            self.sfx_atk = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小黑的攻击音效{i}.mp3")) for i in [1, 2, 3, 4]]
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小黑的受伤音效{i}.mp3")) for i in [1, 2, 3, 4]]
            self.sfx_bounce = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小黑的碰撞音效{i}.mp3")) for i in [1, 2, 3]]
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "小黑的死亡音效.mp3"))
            self.sfx_place_dirt = pygame.mixer.Sound(os.path.join(SFX_DIR, "小黑的放泥土音效.mp3"))
        except: 
            self.sfx_tp = self.sfx_atk = self.sfx_hurt = self.sfx_bounce = []
            self.sfx_die = None
            self.sfx_place_dirt = None

    def tick_support_logic(self):
        if self.dirt_place_cd > 0:
            self.dirt_place_cd -= 1
        if self.combo_lock_timer > 0:
            self.combo_lock_timer -= 1

    def can_place_dirt_now(self):
        return self.dirt_place_cd <= 0 and self.hp > 0 and not self.angry

    def notify_combo_started(self):
        self.combo_lock_timer = 85

    def on_dirt_placed(self):
        self.dirt_place_cd = self.dirt_place_cd_max
        if self.sfx_place_dirt:
            play_sfx(self.sfx_place_dirt)

    def teleport(self, bw, bh, target_pos=None):
        safe_bw, safe_bh = (bw if bw > 200 else self.last_bw), (bh if bh > 200 else self.last_bh)
        self.spawn_effects(25) 
        if self.sfx_tp: play_sfx(random.choice(self.sfx_tp))
        if target_pos:
            tx, ty = target_pos
            self.rect.x = max(50, min(safe_bw - 100, tx + random.randint(-10, 10)))
            self.rect.y = max(50, min(safe_bh - 100, ty + random.randint(-10, 10)))
        else:
            self.rect.x = random.randint(50, max(51, safe_bw - 100))
            self.rect.y = random.randint(50, max(51, safe_bh - 100))
        if hasattr(self, 'x'): self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.spawn_effects(25) 
        self.tp_cd = 30 if self.angry else 180

    def spawn_effects(self, count=20, is_attack=False, x=None, y=None):
        target_x = x if x else self.rect.centerx
        target_y = y if y else self.rect.centery
        for _ in range(count):
            self.particles.append(PurpleParticle(target_x, target_y, is_attack))

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0: return
        actual = int(amount * (1.0 - getattr(self, 'dmg_res', 0.0)))
        self.hp -= actual
        self.trigger_damage_flash()
        
        # 🌟 修复核心：只有确切的实体玩家打他，他才会生气！
        if attacker and attacker != self and hasattr(attacker, 'hp') and attacker.hp > 0:
            self.angry = True
            self.revenge_target = attacker
            if not self._pending_speech:
                try:
                    from i18n import t as _tt
                    self._pending_speech = _tt("p2_enderman")
                except Exception:
                    self._pending_speech = "啊！！！"

        if self.hp <= 0:
            if self.sfx_die: play_sfx(self.sfx_die)
        else:
            if self.sfx_hurt: play_sfx(random.choice(self.sfx_hurt))
            
            if self._boss_mode:
                now_ms = pygame.time.get_ticks()
                if now_ms - getattr(self, '_last_hurt_teleport', 0) > 2000:
                    self._last_hurt_teleport = now_ms
                    dx = self.revenge_target.rect.centerx - self.rect.centerx
                    dy = self.revenge_target.rect.centery - self.rect.centery
                    dist = math.hypot(dx, dy)
                    if dist > 0:
                        self.teleport(self.last_bw, self.last_bh, (self.revenge_target.rect.centerx + (dx/dist)*80, self.revenge_target.rect.centery + (dy/dist)*80))
                    else:
                        self.teleport(self.last_bw, self.last_bh)
            elif self.angry and self.revenge_target and self.revenge_target.hp > 0:
                dx = self.revenge_target.rect.centerx - self.rect.centerx
                dy = self.revenge_target.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self.teleport(self.last_bw, self.last_bh, (self.revenge_target.rect.centerx + (dx/dist)*50, self.revenge_target.rect.centery + (dy/dist)*50))
                else: 
                    self.teleport(self.last_bw, self.last_bh)
            else: 
                self.teleport(self.last_bw, self.last_bh)

    def play_bounce_sfx(self):
        now = pygame.time.get_ticks()
        if now - getattr(self, 'last_bounce_time', 0) > 1500:
            if random.random() < 0.3 and self.sfx_bounce: play_sfx(random.choice(self.sfx_bounce))
            self.last_bounce_time = now

    def on_wall_hit(self):
        self.play_bounce_sfx()
        if not self.angry: self.wander_dir_x *= -1; self.wander_dir_y *= -1

    def update(self, enemies, bw, bh):
        if self.hp <= 0: return None
        self.update_buffs()
        self.last_bw, self.last_bh = bw, bh
        if self._boss_mode:
            self._boss_move_only(bw, bh)
        else:
            self.apply_physics(bw, bh)
        
        if random.random() < 0.15: self.spawn_effects(1)
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        
        for vfx in self.vfx_list: vfx.update()
        self.vfx_list = [vfx for vfx in self.vfx_list if vfx.life > 0]

        # 🌟 此处已删除那个“根据血量差随意锁定仇恨”的 bug 兜底逻辑
        self.prev_hp = self.hp

        if self.angry and self.revenge_target:
            if self.revenge_target.hp <= 0:
                self.angry = False
                self.revenge_target = None
                self.tp_cd = 180                 
            else:
                dx = self.revenge_target.rect.centerx - self.rect.centerx
                dy = self.revenge_target.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy)
                if self._boss_mode:
                    if dist > self._boss_attack_range * 0.75:
                        self.vx += (dx / dist) * self.speed * 0.55
                        self.vy += (dy / dist) * self.speed * 0.55
                    else:
                        self.vx *= 0.70
                        self.vy *= 0.70
                        self.vx += (dx / dist) * self.speed * 0.10
                        self.vy += (dy / dist) * self.speed * 0.10
                elif dist > 40:
                    self.vx += (dx / dist) * self.speed * 0.4
                    self.vy += (dy / dist) * self.speed * 0.4
                
                if self.attack_cd > 0: self.attack_cd -= 1
                atk_range = self._boss_attack_range if self._boss_mode else 65
                if dist < atk_range and self.attack_cd <= 0:
                    self.attack_cd = 40
                    self.notify_combo_started()
                    if self.sfx_atk: play_sfx(random.choice(self.sfx_atk))
                    self.spawn_effects(25, is_attack=True, x=self.revenge_target.rect.centerx, y=self.revenge_target.rect.centery)
                    self.vfx_list.append(AttackVFX(self.revenge_target.rect.centerx, self.revenge_target.rect.centery))
                    return {"target": self.revenge_target, "damage": self.damage}

        if not self.angry:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                if random.random() < 0.4: self.wander_dir_x = self.wander_dir_y = 0
                else: self.wander_dir_x, self.wander_dir_y = random.choice([-1, 1]), random.choice([-1, 1])
                self.wander_timer = random.randint(60, 150)
            self.vx += self.wander_dir_x * self.speed * 0.05
            self.vy += self.wander_dir_y * self.speed * 0.05

        if self.tp_cd > 0: self.tp_cd -= 1
        else:
            if random.random() < (0.05 if self.angry else 0.005): self.teleport(bw, bh)

        self.tick_support_logic()
        if not self._boss_mode:
            self.apply_physics(bw, bh)
        return None

    def draw(self, surface):
        if self.hp <= 0: return
        for vfx in self.vfx_list: vfx.draw(surface)
        surface.blit(self.image, self.rect)
        if self.damage_flash_timer > 0 and self.image:
            flash = self.image.copy()
            flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)
        hp_color = (255, 50, 50) if self.angry else (150, 0, 200)
        hy = max(10, self.rect.y - 10)
        pygame.draw.rect(surface, (100,0,0), (self.rect.x, hy, self.size, 5))
        pygame.draw.rect(surface, hp_color, (self.rect.x, hy, int(max(0, self.hp / max(1, self.max_hp)) * self.size), 5))
        for p in self.particles: p.draw(surface)
        self.draw_float_texts(surface)

    def _boss_move_only(self, bw, bh):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.vx *= 0.80
        self.vy *= 0.80
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(bw, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(bh, self.rect.bottom)