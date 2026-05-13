#entity.py
import pygame
import math
import random

class Particle:
    """通用的爆炸碎片粒子"""
    def __init__(self, x, y, color, speed_mult=1.0):
        self.x, self.y = x, y
        self.vx = random.uniform(-8, 8) * speed_mult
        self.vy = random.uniform(-8, 8) * speed_mult
        self.life, self.color = 255, color
        self.size = random.randint(4, 10)

    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy += 0.2; self.life -= 8

    def draw(self, surface):
        if self.life > 0:
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            s.fill((*self.color, max(0, self.life)))
            surface.blit(s, (self.x, self.y))


class FloatText:
    """浮动的+1/-1文字动画（大字显眼）"""
    def __init__(self, x, y, text, color=(255, 200, 50)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 55
        self.max_life = 55

    def update(self):
        self.life -= 1
        self.y -= 1.5

    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0:
            return
        progress = self.life / self.max_life
        alpha = int(255 * min(1.0, progress * 1.3))
        try:
            from config import get_font
            font = get_font(28)
        except:
            font = pygame.font.Font(None, 28)
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        shadow = font.render(self.text, True, (0, 0, 0))
        shadow.set_alpha(alpha // 2)
        r = surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(shadow, (r.x + 2, r.y + 2))
        surface.blit(surf, r)


class Buff:
    """角色的增益/减益效果（仅在内部生效，不贴文字在头上）"""
    def __init__(self, name, value, duration=0, buff_type="buff"):
        self.name = name
        self.value = value
        self.duration = duration
        self.max_duration = duration
        self.buff_type = buff_type
        self.timer = 0

    def update(self):
        if self.duration > 0:
            self.duration -= 1
        self.timer += 1

    def is_expired(self):
        return self.max_duration > 0 and self.duration <= 0


class Entity:
    """一切生物的物理基类"""
    def __init__(self, x, y, size, hp):
        self.size, self.rect, self.hp, self.max_hp = size, pygame.Rect(x, y, size, size), hp, hp
        angle = random.choice([0.7, 1.2, 2.3, 3.8, 5.1])
        self.vx, self.vy = math.cos(angle) * 5, math.sin(angle) * 5
        self.buffs = []
        self.damage_flash_timer = 0
        self.damage_flash_alpha = 0
        self.float_texts = []
        self._pending_speech = None
        self._boss_mode = False
        self._boss_target = None

    def set_boss_mode(self, boss=None):
        self._boss_mode = True
        self._boss_target = boss
        self._on_boss_mode()

    def _on_boss_mode(self):
        pass

    def add_buff(self, name, value, duration=0, buff_type="buff"):
        for b in self.buffs:
            if b.name == name and not b.is_expired():
                b.duration = max(b.duration, duration)
                b.max_duration = max(b.max_duration, duration)
                b.value = max(b.value, value)
                return b
        new_buff = Buff(name, value, duration, buff_type)
        self.buffs.append(new_buff)
        sign = "+" if value >= 0 else ""
        try:
            from i18n import t as _tt
            display_name = _tt("buff_" + name) if _tt("buff_" + name) != "buff_" + name else name
        except Exception:
            display_name = name
        text = f"{display_name} {sign}{value}"
        self.float_texts.append(FloatText(self.rect.centerx, self.rect.top - 10, text))
        return new_buff

    def remove_buff(self, name):
        self.buffs = [b for b in self.buffs if b.name != name]

    def has_buff(self, name):
        for b in self.buffs:
            if b.name == name and not b.is_expired():
                return True
        return False

    def get_buff_value(self, name):
        for b in self.buffs:
            if b.name == name and not b.is_expired():
                return b.value
        return 0

    def update_buffs(self):
        for b in self.buffs[:]:
            b.update()
            if b.is_expired():
                self.buffs.remove(b)
        for ft in self.float_texts[:]:
            ft.update()
            if ft.is_done():
                self.float_texts.remove(ft)
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= 1
            if self.damage_flash_timer <= 0:
                self.damage_flash_alpha = 0

    def trigger_damage_flash(self):
        pass  # 受击闪白已禁用

    def draw_float_texts(self, surface):
        for ft in self.float_texts:
            ft.draw(surface)

    def apply_physics(self, bw, bh):
        self.rect.x += self.vx; self.rect.y += self.vy
        if self.rect.left <= 0: self.rect.left = 1; self.vx = abs(self.vx); self.on_wall_hit()
        elif self.rect.right >= bw: self.rect.right = bw - 1; self.vx = -abs(self.vx); self.on_wall_hit()
        if self.rect.top <= 0: self.rect.top = 1; self.vy = abs(self.vy); self.on_wall_hit()
        elif self.rect.bottom >= bh: self.rect.bottom = bh - 1; self.vy = -abs(self.vy); self.on_wall_hit()

        for v in ['vx', 'vy']:
            val = getattr(self, v)
            if abs(val) < 1.5: setattr(self, v, 1.5 if val > 0 else -1.5)
            if abs(val) > 10: setattr(self, v, 10 if val > 0 else -10)

    def on_wall_hit(self): pass

    def take_damage(self, amount, attacker=None):
        self.hp -= amount
        self.trigger_damage_flash()
