# Jue_se/illusioner.py
import pygame
import os
import random
import math
from entity import Entity
from ._sfx import play_sfx

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX", "huan-shu-shi")

class SwirlParticle:
    """🌟 蓝色像素回旋粒子特效"""
    def __init__(self, x, y):
        self.x = x + random.randint(-20, 20)
        self.y = y + random.randint(-20, 20)
        self.life = 40
        self.max_life = 40
        self.angle = random.randint(0, 360)

    def update(self): 
        self.life -= 1
        self.angle += 10 
        self.y -= 1 

    def draw(self, surface):
        if self.life > 0:
            alpha = int((self.life / self.max_life) * 255)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            color = (50, 50, 220, alpha)
            pygame.draw.rect(s, color, (5, 5, 10, 3))
            pygame.draw.rect(s, color, (5, 5, 3, 10))
            pygame.draw.rect(s, color, (5, 15, 10, 3))
            pygame.draw.rect(s, color, (15, 7, 3, 10))
            pygame.draw.rect(s, (100, 100, 255, alpha), (9, 9, 4, 4)) 
            
            rotated_s = pygame.transform.rotate(s, self.angle)
            rect = rotated_s.get_rect(center=(self.x, self.y))
            surface.blit(rotated_s, rect)

class MagicOrb:
    """🌟 纯代码手搓的魔法球"""
    def __init__(self, x, y, angle, damage, shooter=None):
        self.x, self.y = x, y
        self.angle = angle
        self.damage = damage
        self.shooter = shooter
        self.speed = 10
        self.life = 100
        self.size = 10
        self.active = True  
        self.rect = pygame.Rect(x-10, y-10, 20, 20)
        self.particles = []

    def is_dead(self):
        return self.life <= 0 or not (-100 < self.x < 3000 and -100 < self.y < 3000)

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.rect.center = (self.x, self.y)
        self.life -= 1
        if self.life % 2 == 0:
            self.particles.append([self.x, self.y, 10])
        for p in self.particles: p[2] -= 1
        self.particles = [p for p in self.particles if p[2] > 0]

    def draw(self, surface):
        for p in self.particles:
            pygame.draw.circle(surface, (100, 100, 255, 100), (int(p[0]), int(p[1])), p[2])
        pygame.draw.circle(surface, (50, 50, 200), self.rect.center, 10)
        pygame.draw.circle(surface, (150, 150, 255), self.rect.center, 5)

class IllusionerClone(Entity):
    """🌟 幻术师分身"""
    def __init__(self, x, y, parent):
        super().__init__(x, y, 60, 20) 
        self.parent = parent # 绑定本体，用来借用本体的音效！
        
        # 🌟 修复：初始CD缩短，落地 0.2~0.5 秒直接开火，不再发呆！
        self.attack_cd = random.randint(15, 30)
        
        self.image = parent.image.copy()
        self.image.fill((100, 150, 255, 180), special_flags=pygame.BLEND_RGBA_MULT)

    def update(self, enemies, bw, bh):
        if self.hp <= 0: return None
        self.update_buffs()
        self.apply_physics(bw, bh)
        if self.attack_cd > 0: self.attack_cd -= 1
        
        target = None
        min_dist = 999
        for e in enemies:
            if e != self and not isinstance(e, Illusioner) and not isinstance(e, IllusionerClone) and e.hp > 0:
                d = math.hypot(e.rect.centerx - self.rect.centerx, e.rect.centery - self.rect.centery)
                if d < min_dist: min_dist = d; target = e

        if target and min_dist < 500 and self.attack_cd <= 0:
            self.attack_cd = 85
            clone_dmg = 18 if getattr(self.parent, '_boss_mode', False) else 2
            
            if self.parent.sfx_atk: play_sfx(random.choice(self.parent.sfx_atk))
                
            angle = math.atan2(target.rect.centery - self.rect.centery, target.rect.centerx - self.rect.centerx)
            orb = MagicOrb(self.rect.centerx, self.rect.centery, angle, clone_dmg, shooter=self.parent)
            orb.from_clone = True
            return {"projectile": orb}
        return None

    def draw(self, surface):
        if self.hp > 0:
            surface.blit(self.image, self.rect)
            if self.damage_flash_timer > 0 and self.image:
                flash = self.image.copy()
                flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(flash, self.rect)
            hp_pct = max(0, self.hp / max(1, self.max_hp))
            pygame.draw.rect(surface, (0,0,255), (self.rect.x, self.rect.y-10, int(hp_pct * self.size), 5))
            self.draw_float_texts(surface)

class Illusioner(Entity):
    def __init__(self, x, y, size=60):
        super().__init__(x, y, size, 100) 
        self.phase = 1
        self.speed = 0.8
        self.attack_cd = 0
        self.swap_cd = 180 
        self.particles = []
        self.current_enemies = [] 
        self.last_bounce_time = 0
        self.meitou_charges = 4
        self.load_assets()

    def _on_boss_mode(self):
        self.max_hp = self.hp = 100
        self._boss_cast_dmg = 65
        self._boss_kite_range = 380
        self._boss_attack_range = 560
        self._boss_flee_speed = 0.45
        self._boss_regen_timer = 0
        self.meitou_charges = 3
        self._burst_timer = 0

    def load_assets(self):
        try:
            p = os.path.join(SPRITES_DIR, "幻术师.webp")
            self.image = pygame.transform.scale(pygame.image.load(p).convert_alpha(), (self.size, self.size))
        except: 
            self.image = pygame.Surface((self.size, self.size)); self.image.fill((0, 0, 200))
        
        # 🌟 修复：补全所有音效加载！
        try:
            self.sfx_cast = pygame.mixer.Sound(os.path.join(SFX_DIR, "幻术师发动分影法术音效.mp3"))
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "幻术师死亡音效.mp3"))
            self.sfx_tp = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"幻术师传送音效{i}.mp3")) for i in [1, 2]]
            self.sfx_atk = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"幻术师的攻击音效{i}.mp3")) for i in [1, 2]]
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"幻术师受伤音效{i}.mp3")) for i in [1, 2]]
            self.sfx_bounce = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"幻术师的撞击音效{i}.mp3")) for i in [1, 2, 3, 4]]
        except Exception as e: 
            print(f"[WARN] 音效加载失败: {e}")
            self.sfx_cast = self.sfx_die = None
            self.sfx_tp = self.sfx_atk = self.sfx_hurt = self.sfx_bounce = []

    def spawn_effects(self, x, y, count=5):
        for _ in range(count): self.particles.append(SwirlParticle(x, y))

    def trigger_phase_2(self):
        self.phase = 2
        print("[INFO] 幻术师进入二阶段！发动分影法术！")
        if self.sfx_cast: play_sfx(self.sfx_cast)
        self.spawn_effects(self.rect.centerx, self.rect.centery, 15)
        
        # 🌟 修复：火力全开！制造 4 个分身，占据四个角
        clones = [
            IllusionerClone(self.rect.x - 80, self.rect.y - 80, self), # 左上
            IllusionerClone(self.rect.x + 80, self.rect.y + 80, self), # 右下
            IllusionerClone(self.rect.x + 80, self.rect.y - 80, self), # 右上
            IllusionerClone(self.rect.x - 80, self.rect.y + 80, self)  # 左下
        ]
        return clones

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0: return

        self.trigger_damage_flash()

        if self.hp - amount <= 0 and self.meitou_charges > 0:
            if self.phase == 2:
                alive_clones = [e for e in self.current_enemies if isinstance(e, IllusionerClone) and e.hp > 0]
                if alive_clones:
                    target_clone = random.choice(alive_clones)
                    self.spawn_effects(self.rect.centerx, self.rect.centery, 10)
                    self.spawn_effects(target_clone.rect.centerx, target_clone.rect.centery, 10)
                    if self.sfx_tp: play_sfx(random.choice(self.sfx_tp))
                    self.rect.center = target_clone.rect.center
                    if hasattr(self, 'x'): self.x, self.y = self.rect.centerx, self.rect.centery
                    target_clone.hp = 0
                    self.meitou_charges -= 1
                    return
            if self.phase == 1:
                self.meitou_charges -= 1
                self.hp = 1
                self.phase = 2
                self._meitou_pending_clones = True
                return

        self.hp -= amount
        if self.hp <= 0:
            if self.sfx_die: play_sfx(self.sfx_die)
        else:
            if self.sfx_hurt: play_sfx(random.choice(self.sfx_hurt))
        
    def update(self, enemies, bw, bh):
        if self.hp <= 0: return None
        self.update_buffs()
        self.apply_physics(bw, bh)
        if self._boss_mode:
            self._boss_regen_timer += 1
            if self._boss_regen_timer >= 90:
                self._boss_regen_timer = 0
                self.hp = min(self.max_hp, self.hp + 1)
        self.current_enemies = enemies 
        
        spawns = []
        if getattr(self, '_meitou_pending_clones', False):
            self._meitou_pending_clones = False
            clones = self.trigger_phase_2()
            try:
                from i18n import t as _tt
                self._pending_speech = _tt("p2_illusioner")
            except Exception:
                self._pending_speech = "空间和时间你都无法捕捉~"
            spawns.extend(clones)
        elif self.hp <= 50 and self.phase == 1:
            clones = self.trigger_phase_2()
            try:
                from i18n import t as _tt
                self._pending_speech = _tt("p2_illusioner")
            except Exception:
                self._pending_speech = "空间和时间你都无法捕捉~"
            spawns.extend(clones)

        if self.attack_cd > 0: self.attack_cd -= 1
        if self.swap_cd > 0: self.swap_cd -= 1
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        if self.phase == 2 and self.swap_cd <= 0 and random.random() < 0.06:
            alive_clones = [e for e in enemies if isinstance(e, IllusionerClone) and e.hp > 0]
            if alive_clones:
                target = random.choice(alive_clones)
                self.spawn_effects(self.rect.centerx, self.rect.centery)
                self.spawn_effects(target.rect.centerx, target.rect.centery)
                if self.sfx_tp: play_sfx(random.choice(self.sfx_tp))
                
                self.rect.center, target.rect.center = target.rect.center, self.rect.center
                if hasattr(self, 'x'): self.x, self.y = self.rect.centerx, self.rect.centery
                if hasattr(target, 'x'): target.x, target.y = target.rect.centerx, target.rect.centery
                self.swap_cd = 100 

        target = None
        min_dist = 999
        for e in enemies:
            if e != self and not isinstance(e, IllusionerClone) and e.hp > 0:
                d = math.hypot(e.rect.centerx - self.rect.centerx, e.rect.centery - self.rect.centery)
                if d < min_dist: min_dist = d; target = e

        result = {}
        attack_range = self._boss_attack_range if self._boss_mode else 400
        if target and min_dist < attack_range and self.attack_cd <= 0:
            orb_dmg = self._boss_cast_dmg if self._boss_mode else 10
            burst_count = 1
            if self._boss_mode:
                self._burst_timer -= 1
                if self._burst_timer <= 0:
                    self._burst_timer = random.randint(150, 260)
                    burst_count = 3
                    self.attack_cd = 110
                else:
                    self.attack_cd = 48
            else:
                self.attack_cd = 90
            
            if self.sfx_atk: play_sfx(random.choice(self.sfx_atk))

            base_angle = math.atan2(target.rect.centery - self.rect.centery, target.rect.centerx - self.rect.centerx)
            orbs = []
            for i in range(burst_count):
                spread = random.uniform(-0.18, 0.18) if burst_count > 1 else 0
                orbs.append(MagicOrb(self.rect.centerx, self.rect.centery, base_angle + spread, orb_dmg, shooter=self))
            if orbs:
                result["projectiles"] = orbs

        if self._boss_mode and target:
            dx = self.rect.centerx - target.rect.centerx
            dy = self.rect.centery - target.rect.centery
            d_safe = math.hypot(dx, dy)
            if d_safe > 0:
                if min_dist < self._boss_kite_range:
                    self.vx += (dx / d_safe) * self._boss_flee_speed
                    self.vy += (dy / d_safe) * self._boss_flee_speed
                elif min_dist > self._boss_kite_range * 1.5:
                    self.vx -= (dx / d_safe) * 0.30
                    self.vy -= (dy / d_safe) * 0.30
            
        if spawns:
            result["spawns"] = spawns 
            
        return result if result else None

    def draw(self, surface):
        if self.hp <= 0: return
        surface.blit(self.image, self.rect)
        if self.damage_flash_timer > 0 and self.image:
            flash = self.image.copy()
            flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)
        self._draw_hp(surface)
        for p in self.particles: p.draw(surface)
        self.draw_float_texts(surface)

    def _draw_hp(self, surface):
        hy = max(10, self.rect.y - 10)
        hp_pct = max(0, self.hp / max(1, self.max_hp))
        pygame.draw.rect(surface, (255,0,0), (self.rect.x, hy, self.size, 5))
        pygame.draw.rect(surface, (0,255,0) if self.phase == 1 else (200,50,255), (self.rect.x, hy, int(hp_pct * self.size), 5))

    # 🌟 修复：加入撞击音效逻辑，让裁判引擎能调得动！
    def play_bounce_sfx(self):
        now = pygame.time.get_ticks()
        if now - self.last_bounce_time > 600:
            if self.sfx_bounce and random.random() < 0.4:
                sound = random.choice(self.sfx_bounce)
                sound.set_volume(0.4)
                play_sfx(sound, volume=0.4)
                self.last_bounce_time = now

    def on_wall_hit(self):
        """撞击四周墙壁时，底层系统会自动调用这个"""
        self.play_bounce_sfx()