# Jue_se/skeleton.py
import pygame
import math
import os
import random
from entity import Entity
from ._sfx import play_sfx

# 获取项目根目录，定位资源
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SFX_DIR = os.path.join(BASE_DIR, "SFX", "xiao-bai")
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")

class Arrow:
    def __init__(self, x, y, target_rect, speed=15, is_ultimate=False, shooter=None):
        self.x, self.y = x, y
        self.is_ultimate = is_ultimate
        self.speed = 25 if is_ultimate else speed
        self.active = True
        self.shooter = shooter
        
        # 🌟 [数值调整]：普通箭的基础伤害。之前是 15，现在削弱成 10。
        # 如果以后想让他彻底刮痧，可以改成 5；想加强就改回 15。
        self.damage = 10 
        
        self.knockback = 15 if is_ultimate else 8
        self.particles = [] 
        
        dx = target_rect.centerx - x
        dy = target_rect.centery - y
        dist = math.hypot(dx, dy)
        
        if dist == 0:
            self.vx, self.vy = self.speed, 0
        else:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed
            angle = math.degrees(math.atan2(-dy, dx))
            
        try:
            img_name = "灵光箭.png" if is_ultimate else "箭.png"
            orig_img = pygame.image.load(os.path.join(SPRITES_DIR, img_name)).convert_alpha()
            scaled_img = pygame.transform.scale(orig_img, (60,60))
            self.image = pygame.transform.rotate(scaled_img, angle - 45)
        except:
            self.image = pygame.Surface((60, 6))
            self.image.fill((255, 215, 0) if is_ultimate else (200, 200, 200))
            self.image = pygame.transform.rotate(self.image, angle)
            
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (self.x, self.y)
        
        if self.is_ultimate:
            self.particles.append([[self.x, self.y], [random.uniform(-2, 2), random.uniform(-2, 2)], random.randint(3, 6)])
            
        for p in self.particles[:]:
            p[0][0] += p[1][0]
            p[0][1] += p[1][1]
            p[2] -= 0.3 
            if p[2] <= 0:
                self.particles.remove(p)

    def draw(self, surface):
        for p in self.particles:
            pygame.draw.circle(surface, (255, 215, 0), (int(p[0][0]), int(p[0][1])), int(p[2]))
        surface.blit(self.image, self.rect)


class Skeleton(Entity):
    def __init__(self, x, y, size=50):
        super().__init__(x, y, size, 100)
        
        # 🌟 [数值调整]：射击间隔。150 代表 150帧射一箭，数值越小射得越快（机枪）。
        self.shoot_timer = 150 
        
        self.revenge_pool = 0 
        self.is_charging_revenge = False 
        
        # 🌟 [数值调整]：大招蓄力时间。45 帧大约是 0.75 秒。
        self.charge_timer = 0 
        self.last_bounce_time = 0 
        self.shoot_anim_timer = 0
        
        self.load_assets()

    def load_assets(self):
        try:
            p = os.path.join(SPRITES_DIR, "小白.webp")
            self.image = pygame.transform.scale(pygame.image.load(p).convert_alpha(), (self.size, self.size))
            self.bow_frames = []
            for i in [1, 2, 3]:
                frame_path = os.path.join(SPRITES_DIR, f"拉弓的状态{i}.png")
                frame = pygame.image.load(frame_path).convert_alpha()
                bow_size = int(self.size * 0.95)
                self.bow_frames.append(pygame.transform.scale(frame, (bow_size, bow_size)))
            self.sfx_shoot = pygame.mixer.Sound(os.path.join(SFX_DIR, "小白的射击音效.mp3"))
            self.sfx_ultimate = pygame.mixer.Sound(os.path.join(SFX_DIR, "箭的音效.mp3"))
            self.sfx_hurt = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小白的受伤音效{i}.mp3")) for i in [1, 2, 3]]
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "小白的死亡音效.mp3"))
        except:
            self.image = None
            self.bow_frames = []
            self.sfx_shoot = self.sfx_ultimate = self.sfx_die = None
            self.sfx_hurt = []

        try:
            self.sfx_bounce = [pygame.mixer.Sound(os.path.join(SFX_DIR, f"小白撞击音效{i}.mp3")) for i in [1, 2, 3, 4]]
        except:
            self.sfx_bounce = []

    def _on_boss_mode(self):
        self.max_hp = self.hp = 220
        self._boss_shoot_cd = 90
        self._boss_pct_damage = 0.028
        self._boss_ult_pct = 0.08
        self._boss_kite_range = 400
        self._boss_flee_speed = 0.55
        self._boss_dodge_chance = 0.35
        self.dmg_res = 0.28
        self._dance_timer = 0
        self._dance_dir = 1

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0: return
        if self._boss_mode and random.random() < self._boss_dodge_chance:
            self._boss_shadow_step()
            heal = min(18, self.max_hp - self.hp)
            if heal > 0:
                self.hp += heal
            if self.float_texts:
                from entity import FloatText
                self.float_texts.append(FloatText(self.rect.centerx + random.randint(-15, 15), self.rect.top - 20, "闪避!", (180, 180, 255)))
                if heal > 0:
                    self.float_texts.append(FloatText(self.rect.centerx + random.randint(-10, 10), self.rect.top - 40, f"+{heal}", (100, 255, 100)))
            return
        self.hp -= amount
        self.trigger_damage_flash()
        if self._boss_mode:
            self._boss_shadow_step()
        self.revenge_pool += amount

        if self.hp <= 0:
            if self.sfx_die: play_sfx(self.sfx_die)
        else:
            if self.sfx_hurt:
                play_sfx(random.choice(self.sfx_hurt))

    def _boss_shadow_step(self):
        if self._boss_target and self._boss_target.hp > 0:
            dx = self.rect.centerx - self._boss_target.rect.centerx
            dy = self.rect.centery - self._boss_target.rect.centery
            dist = math.hypot(dx, dy) or 1
            self.rect.x += int((dx / dist) * 75 + random.uniform(-25, 25))
            self.rect.y += int((dy / dist) * 75 + random.uniform(-25, 25))
        else:
            self.rect.x += int(random.uniform(-90, 90))
            self.rect.y += int(random.uniform(-90, 90))

    def _boss_arrow_damage(self):
        if self._boss_target and self._boss_target.hp > 0:
            return max(1, int(self._boss_target.max_hp * self._boss_pct_damage))
        return 10

    def _boss_ult_damage(self):
        if self._boss_target and self._boss_target.hp > 0:
            return max(2, int(self._boss_target.max_hp * self._boss_ult_pct))
        return max(10, self.revenge_pool)

    def update(self, bw, bh, target_rect, arrows_list):
        if self.hp <= 0: return
        self.update_buffs()
        if self._boss_mode:
            if not hasattr(self, 'fx'): self.fx, self.fy = float(self.rect.x), float(self.rect.y)
            self.fx += self.vx
            self.fy += self.vy
            self.vx *= 0.90
            self.vy *= 0.90
            if self.fx < 10.0:
                self.fx = 10.0
                if self.vx < 0: self.vx *= -0.20
            elif self.fx > float(bw - self.size - 10):
                self.fx = float(bw - self.size - 10)
                if self.vx > 0: self.vx *= -0.20
            if self.fy < 10.0:
                self.fy = 10.0
                if self.vy < 0: self.vy *= -0.20
            elif self.fy > float(bh - self.size - 10):
                self.fy = float(bh - self.size - 10)
                if self.vy > 0: self.vy *= -0.20
            self.rect.x, self.rect.y = int(self.fx), int(self.fy)
        else:
            self.apply_physics(bw, bh)
        if target_rect is None: return

        if self._boss_mode and target_rect:
            dx = self.rect.centerx - target_rect.centerx
            dy = self.rect.centery - target_rect.centery
            dist = math.hypot(dx, dy)

            self._dance_timer -= 1
            if self._dance_timer <= 0:
                self._dance_timer = random.randint(50, 120)
                self._dance_dir = random.choice([-1, 1])

            lateral = 0.35 * self._dance_dir
            perp_x = -dy / (dist or 1)
            perp_y = dx / (dist or 1)

            if dist < self._boss_kite_range and dist > 0:
                flee = 0.75
                if dist < self._boss_kite_range * 0.45:
                    flee = 1.05
                self.vx += (dx / dist) * flee + perp_x * lateral
                self.vy += (dy / dist) * flee + perp_y * lateral
            elif dist < self._boss_kite_range * 1.3:
                self.vx += perp_x * lateral * 2.0
                self.vy += perp_y * lateral * 2.0
            elif dist > 0:
                self.vx += perp_x * lateral * 1.0
                self.vy += perp_y * lateral * 1.0

        if self.shoot_anim_timer > 0:
            self.shoot_anim_timer -= 1

        if self.is_charging_revenge:
            self.charge_timer -= 1
            self.shoot_anim_timer = max(self.shoot_anim_timer, 10)
            if self.charge_timer <= 0:
                if self._boss_mode:
                    final_dmg = self._boss_ult_damage()
                else:
                    final_dmg = max(10, self.revenge_pool)
                
                new_arrow = Arrow(self.rect.centerx, self.rect.centery, target_rect, is_ultimate=True, shooter=self)
                new_arrow.damage = final_dmg
                arrows_list.append(new_arrow)
                
                if hasattr(self, 'sfx_ultimate'): play_sfx(self.sfx_ultimate)
                
                self.is_charging_revenge = False
                self.shoot_anim_timer = 12
                self.shoot_timer = self._boss_shoot_cd if self._boss_mode else 150
                try:
                    from i18n import t as _tt
                    self._pending_speech = _tt("p2_skeleton")
                except Exception:
                    self._pending_speech = "这一箭贯穿星辰"
            return 

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            # 🌟 [数值调整]：大招触发概率。
            # 这里写的是：如果血量 <= 50%，概率是 1/3；否则概率是 1/10。
            # 如果以后想让他更难发大招，可以改成 (1/4) 和 (1/20)。
            prob = (1/3) if self.hp <= 50 else (1/10)
            is_revenge = random.random() < prob
            
            if is_revenge:
                self.is_charging_revenge = True
                self.shoot_anim_timer = 10
                self.charge_timer = 45 
            else:
                new_arrow = Arrow(self.rect.centerx, self.rect.centery, target_rect, is_ultimate=False, shooter=self)
                arrow_dmg = self._boss_arrow_damage() if self._boss_mode else getattr(self, 'damage', 10)
                new_arrow.damage = arrow_dmg
                
                arrows_list.append(new_arrow)
                if hasattr(self, 'sfx_shoot'): play_sfx(self.sfx_shoot)
                self.shoot_anim_timer = 12
                self.shoot_timer = self._boss_shoot_cd if self._boss_mode else 150

    def draw(self, surface):
        if self.hp <= 0: return
        bow_overlay = None
        if self.bow_frames:
            if self.is_charging_revenge:
                bow_overlay = self.bow_frames[2]
            elif self.shoot_anim_timer > 8:
                bow_overlay = self.bow_frames[0]
            elif self.shoot_anim_timer > 4:
                bow_overlay = self.bow_frames[1]
            elif self.shoot_anim_timer > 0:
                bow_overlay = self.bow_frames[2]
        
        draw_img = self.image
        if self.is_charging_revenge:
            alpha = int(abs(math.sin(self.charge_timer * 0.4)) * 150) + 50 
            if self.image:
                draw_img = self.image.copy()
                draw_img.fill((255, 215, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(draw_img, self.rect)
            else:
                pygame.draw.rect(surface, (255, 255, 255), self.rect)
            if bow_overlay:
                bow_rect = bow_overlay.get_rect(center=self.rect.center)
                surface.blit(bow_overlay, bow_rect)
            pygame.draw.rect(surface, (255, 215, 0), self.rect.inflate(10, 10), 3)
        else:
            if self.image:
                surface.blit(self.image, self.rect)
            else: pygame.draw.rect(surface, (255, 255, 255), self.rect)
            if bow_overlay:
                bow_rect = bow_overlay.get_rect(center=self.rect.center)
                surface.blit(bow_overlay, bow_rect)

        if self.damage_flash_timer > 0 and self.image:
            flash = self.image.copy()
            flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)

        if self.hp > 0:
            hp_pct = max(0, self.hp / max(1, self.max_hp))
            pygame.draw.rect(surface, (255, 0, 0), (self.rect.x, self.rect.y - 10, self.size, 5))
            pygame.draw.rect(surface, (0, 255, 0), (self.rect.x, self.rect.y - 10, int(self.size * hp_pct), 5))

        self.draw_float_texts(surface)

    def play_bounce_sfx(self):
        now = pygame.time.get_ticks()
        if now - getattr(self, 'last_bounce_time', 0) > 200:
            if hasattr(self, 'sfx_bounce') and self.sfx_bounce:
                play_sfx(random.choice(self.sfx_bounce))
                self.last_bounce_time = now

    def on_wall_hit(self):
        self.play_bounce_sfx()

