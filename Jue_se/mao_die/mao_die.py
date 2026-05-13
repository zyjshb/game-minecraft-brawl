import pygame
import math
import os
import random

from entity import Entity

from .constants import (
    BASE_ATTACK_CD,
    BASE_DAMAGE,
    BASE_HP_PER_LIFE,
    DAMAGE_RESIST,
    ENCHANT_ATTACK_SPEED_BUFF,
    ENCHANT_BUFF_DURATION,
    ENCHANT_DAMAGE_BUFF,
    HA_QI_SPEED_BUFF,
    HA_QI_MOVE_BOOST,
    KNOCKBACK_RESIST,
    LAST_LIFE_HP,
    LIFE_COLORS,
    LIVES_TOTAL,
    PHASE2_DEATH_THRESHOLD,
    SFX_ATTACK_COOLDOWN_MS,
    SFX_HA_QI_COOLDOWN_MS,
    SFX_HURT_COOLDOWN_MS,
    SIZE,
)
from .ha_qi import HaQiSystem
from .phase2 import Phase2System
from .vfx import ClawSlash, CrossSlash, get_ha_qi_image_for_face
from .meitou import MeitouEffect, MeitouDialog, get_meitou_sfx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX", "mao-die")


class MaoDie(Entity):
    def __init__(self, x, y, size=SIZE):
        super().__init__(x, y, size, BASE_HP_PER_LIFE)
        self.base_size = size
        self.max_hp_per_life = BASE_HP_PER_LIFE
        self.lives = LIVES_TOTAL
        self.death_count = 0
        self.kb_res = KNOCKBACK_RESIST
        self.dmg_res = DAMAGE_RESIST
        self.attack_cd = 0
        self.attack_range = 72
        self.current_damage = BASE_DAMAGE
        self.last_bounce_time = 0

        self.ha_qi = HaQiSystem()
        self.phase2 = Phase2System()

        self._phase2_pending = False
        self._phase2_pending_frames = 0

        self.slashes = []

        self._last_sfx_attack = 0
        self._last_sfx_ha_qi = 0
        self._last_sfx_hurt = 0

        self._enchanted = False
        self._enchanted_delay = 0

        self._altar_target = None
        self._seek_altar_roll = None

        self._ghost_images = []

        self._meitou_effects = []
        self._meitou_dialogs = []
        self._meitou_first_triggered = False
        self._meitou_invincible_until = 0
        self._meitou_sfx = None

        self.ha_qi_face_img = None

        self.load_assets()

    def _on_boss_mode(self):
        self.max_hp_per_life = int(BASE_HP_PER_LIFE * 1.8)
        self.max_hp = self.hp = self.max_hp_per_life
        self._boss_damage_mult = 1.50
        self.attack_range = 140
        self._boss_chase_speed = 0.70
        self._pullback_timer = 0
        self._pullback_cd = 0

    def load_assets(self):
        try:
            p = os.path.join(SPRITES_DIR, "耄耋.png")
            self.image = pygame.transform.scale(
                pygame.image.load(p).convert_alpha(),
                (self.size, self.size),
            )
        except Exception:
            self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            self.image.fill((180, 130, 80))

        try:
            self.ha_qi_face_img = get_ha_qi_image_for_face(self.size)
        except Exception:
            self.ha_qi_face_img = None

        try:
            self.sfx_ha_qi = pygame.mixer.Sound(os.path.join(SFX_DIR, "耄耋哈气.mp3"))
        except Exception:
            self.sfx_ha_qi = None

        try:
            self.sfx_ha_qi_triple = pygame.mixer.Sound(os.path.join(SFX_DIR, "耄耋三连哈.mp3"))
        except Exception:
            self.sfx_ha_qi_triple = None

        try:
            self.sfx_attack = pygame.mixer.Sound(os.path.join(SFX_DIR, "耄耋攻击.mp3"))
        except Exception:
            self.sfx_attack = None

        try:
            self.sfx_hurt = pygame.mixer.Sound(os.path.join(SFX_DIR, "耄耋受伤.mp3"))
        except Exception:
            self.sfx_hurt = None

        try:
            self.sfx_die = pygame.mixer.Sound(os.path.join(SFX_DIR, "耄耋死亡.mp3"))
        except Exception:
            self.sfx_die = None

        self.sfx_bounce = []

        self._meitou_sfx = get_meitou_sfx()

    def _play_sfx(self, sound, last_attr, cooldown, volume=1.0):
        if sound is None:
            return
        now = pygame.time.get_ticks()
        if now - getattr(self, last_attr, 0) < cooldown:
            return
        setattr(self, last_attr, now)
        try:
            from audio_manager import play_sfx_managed
            play_sfx_managed(sound, volume)
        except Exception:
            try:
                sound.play()
            except Exception:
                pass

    def _play_death_sfx(self):
        if self.sfx_die is None:
            return
        try:
            from audio_manager import play_sfx_managed
            play_sfx_managed(self.sfx_die, 1.0)
        except Exception:
            try:
                self.sfx_die.play()
            except Exception:
                pass

    def apply_enchant_buff(self):
        self._enchanted = True
        self.add_buff("atk_up", ENCHANT_DAMAGE_BUFF, ENCHANT_BUFF_DURATION, "buff")
        self._enchanted_delay = 30
        self.current_damage = self._get_effective_damage()

    def _spawn_ghosts(self, count=5, outward=True, life_color=None):
        if life_color is None:
            lost_lives = LIVES_TOTAL - self.lives
            life_idx = min(len(LIFE_COLORS) - 1, max(0, lost_lives))
            life_color = LIFE_COLORS[life_idx]
        for _ in range(count):
            ox = self.rect.centerx + random.uniform(-self.size // 2, self.size // 2)
            oy = self.rect.centery + random.uniform(-self.size // 2, self.size // 2)
            dx = (ox - self.rect.centerx) * (2.0 if outward else -2.0)
            dy = (oy - self.rect.centery) * (2.0 if outward else -2.0)
            self._ghost_images.append({
                'x': ox,
                'y': oy,
                'vx': dx,
                'vy': dy,
                'life': random.randint(18, 30),
                'max_life': 30,
                'color': life_color,
            })

    def take_damage(self, amount, attacker=None):
        if self.hp <= 0:
            return

        if self._meitou_invincible_until > 0:
            now = pygame.time.get_ticks()
            if now < self._meitou_invincible_until:
                return
            self._meitou_invincible_until = 0

        actual = amount * (1.0 - self.dmg_res)
        self.hp -= actual

        self.trigger_damage_flash()

        self.ha_qi.cooldown = max(self.ha_qi.cooldown, 45)

        if self.hp <= 0:
            self.hp = 0
            self._on_death()
            return

        self._play_sfx(self.sfx_hurt, '_last_sfx_hurt', SFX_HURT_COOLDOWN_MS)

    def _on_death(self):
        if self.lives <= 0:
            return

        self._play_death_sfx()
        self._spawn_ghosts(12, outward=True)

        self.death_count += 1
        self.phase2.on_life_lost()
        self.lives -= 1

        self._trigger_meitou()

        if self.lives == 5 and not self._enchanted:
            self.apply_enchant_buff()
            self._spawn_ghosts(20, outward=False, life_color=(255, 200, 50))
            self._spawn_ghosts(15, outward=True, life_color=(255, 240, 150))
            from entity import FloatText
            self.float_texts.append(FloatText(self.rect.centerx, self.rect.top - 25, "附魔融合!", (255, 200, 50)))

        if self.lives <= 0:
            self._meitou_invincible_until = pygame.time.get_ticks() + 450
            self.hp = 1
            return

        if not self.phase2.active and self.death_count >= PHASE2_DEATH_THRESHOLD and not self._phase2_pending:
            self.ha_qi.trigger_triple_start()
            self._phase2_pending = True
            self._phase2_pending_frames = 0
            try:
                from i18n import t as _tt
                self._pending_speech = _tt("p2_maodie")
            except Exception:
                self._pending_speech = "哈！！！"
            if self.lives == 1:
                self.max_hp_per_life = LAST_LIFE_HP
            else:
                self.max_hp_per_life = BASE_HP_PER_LIFE
            self.max_hp = self.max_hp_per_life
            self.hp = self.max_hp_per_life
            self._reset_knockback()
            self._spawn_ghosts(10, outward=False)
            return

        if self.lives == 1:
            self.max_hp_per_life = LAST_LIFE_HP
        elif self.phase2.active:
            decayed = self.phase2.get_decayed_max_hp(BASE_HP_PER_LIFE)
            self.max_hp_per_life = decayed
        else:
            self.max_hp_per_life = BASE_HP_PER_LIFE

        self.max_hp = self.max_hp_per_life
        self.hp = self.max_hp_per_life
        self.current_damage = self._get_effective_damage()
        self._reset_knockback()
        self._spawn_ghosts(10, outward=False)

    def _trigger_meitou(self):
        if self.death_count > LIVES_TOTAL:
            return

        self._meitou_effects.append(MeitouEffect(self))

        if not self._meitou_first_triggered:
            self._meitou_first_triggered = True
            self._meitou_dialogs.append(MeitouDialog(self))

        if self._meitou_sfx:
            try:
                from audio_manager import play_sfx_managed, start_sfx_duck
                duration_ms = int(self._meitou_sfx.get_length() * 1000) + 100
                start_sfx_duck(duration_ms, 0.2)
                play_sfx_managed(self._meitou_sfx, 1.0)
            except Exception:
                try:
                    self._meitou_sfx.play()
                except Exception:
                    pass

        self._meitou_invincible_until = pygame.time.get_ticks() + 1000

    def _reset_knockback(self):
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)

    def _move_toward(self, target_rect):
        dx = target_rect.centerx - self.rect.centerx
        dy = target_rect.centery - self.rect.centery
        dist = math.hypot(dx, dy) or 1.0
        move_speed = 0.2
        self.vx += (dx / dist) * move_speed
        self.vy += (dy / dist) * move_speed

    def set_altar_target(self, rect):
        self._altar_target = rect if rect else None
        if rect and self._seek_altar_roll is None:
            self._seek_altar_roll = random.random() < 0.7

    def _get_effective_damage(self):
        base = self.phase2.attack_damage if self.phase2.active else BASE_DAMAGE
        if self._boss_mode:
            base = int(base * self._boss_damage_mult)
        if self._enchanted:
            base += self.get_buff_value("atk_up")
        return base

    def _get_effective_attack_cd(self):
        cd = self.phase2.attack_cd if self.phase2.active else BASE_ATTACK_CD
        cd = int(cd * self.ha_qi.get_attack_cd_multiplier())
        if self._enchanted:
            speed_buff = self.get_buff_value("spd_up")
            if speed_buff > 0:
                cd = int(cd * (1.0 - speed_buff))
        if self._boss_mode:
            cd = max(28, int(cd * 0.65))
        return max(2, cd)

    def update(self, enemies, bw, bh):
        self.update_buffs()

        if self._boss_mode:
            self._altar_target = None
            self._seek_altar_roll = False

        if self._enchanted_delay > 0:
            self._enchanted_delay -= 1
            if self._enchanted_delay <= 0:
                self.add_buff("spd_up", ENCHANT_ATTACK_SPEED_BUFF, ENCHANT_BUFF_DURATION, "buff")
            self.current_damage = self._get_effective_damage()

        for g in self._ghost_images[:]:
            g['x'] += g['vx']
            g['y'] += g['vy']
            g['vx'] *= 0.96
            g['vy'] *= 0.96
            g['life'] -= 1
            if g['life'] <= 0:
                self._ghost_images.remove(g)

        for e in self._meitou_effects[:]:
            e.update()
            if e.is_done:
                self._meitou_effects.remove(e)

        for d in self._meitou_dialogs[:]:
            d.update()
            if d.is_done:
                self._meitou_dialogs.remove(d)

        if self._meitou_invincible_until > 0:
            if pygame.time.get_ticks() >= self._meitou_invincible_until:
                self._meitou_invincible_until = 0

        if self.hp <= 0:
            return None

        if self._boss_mode:
            self._boss_move_only(bw, bh)
        else:
            self.apply_physics(bw, bh)

        self.ha_qi.update()
        self.phase2.update()

        for s in self.slashes[:]:
            s.update()
            if s.life <= 0:
                self.slashes.remove(s)

        if self._phase2_pending:
            self._phase2_pending_frames += 1
            self.vx *= 0.85
            self.vy *= 0.85
            if self.ha_qi.is_triple:
                return None
            if self._phase2_pending_frames >= 90:
                self._phase2_pending = False
                self.phase2.complete_activation()
                self.current_damage = self._get_effective_damage()
            return None

        if self.attack_cd > 0:
            self.attack_cd -= 1

        closest_enemy = None
        min_dist = 9999
        for enemy in enemies:
            if enemy == self or enemy.hp <= 0:
                continue
            d = math.hypot(
                enemy.rect.centerx - self.rect.centerx,
                enemy.rect.centery - self.rect.centery,
            )
            if d < min_dist:
                min_dist = d
                closest_enemy = enemy

        if closest_enemy is None:
            if self._altar_target and self._seek_altar_roll and not self._enchanted:
                self._move_toward(self._altar_target)
            return None

        if self._altar_target and self._seek_altar_roll and not self._enchanted:
            if self._altar_target.colliderect(self.rect.inflate(20, 20)):
                self._move_toward(self._altar_target)
                return None

        enemy_rect = closest_enemy.rect
        me_rect = self.rect

        if min_dist < self.attack_range and self.attack_cd <= 0:
            effective_cd = self._get_effective_attack_cd()
            self.attack_cd = effective_cd
            self._play_sfx(self.sfx_attack, '_last_sfx_attack', SFX_ATTACK_COOLDOWN_MS)
            is_p2 = self.phase2.active
            if is_p2:
                self.slashes.append(
                    ClawSlash(closest_enemy.rect.centerx, closest_enemy.rect.centery, is_phase2=True)
                )
                self.slashes.append(
                    CrossSlash(closest_enemy.rect.centerx, closest_enemy.rect.centery)
                )
            else:
                self.slashes.append(
                    ClawSlash(closest_enemy.rect.centerx, closest_enemy.rect.centery, is_phase2=False)
                )
            attack_result = {
                "target": closest_enemy,
                "damage": self._get_effective_damage(),
            }
            if is_p2:
                attack_result["second_damage"] = self.phase2.second_claw_damage
            if self._boss_mode and self._pullback_cd <= 0:
                self._pullback_timer = 25
                self._pullback_cd = 100
            return attack_result

        ha_qi_result = None
        ha_qi_fired = False
        if self.ha_qi.should_trigger(me_rect, enemy_rect) and not self.ha_qi.active:
            if self.ha_qi.is_triple and self.ha_qi.triple_cooldown <= 0:
                ha_qi_result = self.ha_qi._fire_triple_burst(me_rect, enemy_rect)
                ha_qi_fired = True
                if self.ha_qi.triple_index >= 3:
                    self.ha_qi.is_triple = False
            elif not self.ha_qi.is_triple:
                ha_qi_result = self.ha_qi.trigger_single(me_rect, enemy_rect)
                ha_qi_fired = True
        if ha_qi_fired:
            self._play_sfx(self.sfx_ha_qi, '_last_sfx_ha_qi', SFX_HA_QI_COOLDOWN_MS, volume=0.25)
            if self.phase2.active and ha_qi_result and "push" in ha_qi_result:
                px, py = ha_qi_result["push"]
                ha_qi_result["push"] = (px * 0.5, py * 0.5)
            return ha_qi_result

        dx = enemy_rect.centerx - me_rect.centerx
        dy = enemy_rect.centery - me_rect.centery
        dist = math.hypot(dx, dy) or 1.0
        if self._boss_mode:
            comfort = self.attack_range * 0.75
            if self._pullback_timer > 0:
                self._pullback_timer -= 1
                self.vx -= (dx / dist) * 0.55
                self.vy -= (dy / dist) * 0.55
            elif dist > comfort:
                if self._pullback_cd > 0:
                    self._pullback_cd -= 1
                self.vx += (dx / dist) * self._boss_chase_speed
                self.vy += (dy / dist) * self._boss_chase_speed
            else:
                if self._pullback_cd > 0:
                    self._pullback_cd -= 1
                self.vx *= 0.70
                self.vy *= 0.70
                self.vx += (dx / dist) * self._boss_chase_speed * 0.15
                self.vy += (dy / dist) * self._boss_chase_speed * 0.15
        else:
            move_speed = 0.12 * (1.0 + HA_QI_MOVE_BOOST if self.ha_qi.buff_active else 1.0)
            if self.phase2.active:
                move_speed *= 1.4
            self.vx += (dx / dist) * move_speed
            self.vy += (dy / dist) * move_speed

        if self.phase2.active:
            self.hp = self.phase2.update_regen(self.hp, self.max_hp_per_life)

        return None

    def _get_draw_image(self):
        if self.ha_qi_face_img and self.ha_qi.active:
            return self.ha_qi_face_img
        return self.image

    def draw(self, surface):
        if self.hp <= 0:
            return

        for g in self._ghost_images:
            alpha = int(180 * (g['life'] / g['max_life']))
            if alpha > 0:
                s = pygame.Surface((6, 6), pygame.SRCALPHA)
                s.fill((*g['color'], alpha))
                surface.blit(s, (int(g['x']) - 3, int(g['y']) - 3))

        draw_img = self._get_draw_image()

        if self.phase2.active:
            tint = draw_img.copy()
            tint.fill((255, 60, 15, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tint, self.rect)
        else:
            surface.blit(draw_img, self.rect)

        if self.damage_flash_timer > 0:
            flash = draw_img.copy()
            flash.fill((255, 255, 255, self.damage_flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, self.rect)

        for s in self.slashes:
            s.draw(surface)

        for e in self._meitou_effects:
            e.draw(surface)

        for d in self._meitou_dialogs:
            d.draw(surface)

        self._draw_lives_ui(surface)
        self.ha_qi.draw(surface)
        self.phase2.draw(surface)
        self.draw_float_texts(surface)

    def _draw_lives_ui(self, surface):
        bar_w = self.size + 20
        bar_h = 6
        bx = self.rect.centerx - bar_w // 2
        by = max(25, self.rect.top - 16)
        step = bar_w / LIVES_TOTAL
        lost = LIVES_TOTAL - self.lives
        for i in range(LIVES_TOTAL):
            alive = i >= lost
            color = LIFE_COLORS[i]
            if not alive:
                color = tuple(max(0, c - 200) for c in color)
            rx = int(bx + i * step)
            pygame.draw.rect(surface, (0, 0, 0, 180),
                             (rx, by, int(step), bar_h))
            if alive:
                inner = pygame.Rect(rx + 1, by + 1, int(step) - 2, bar_h - 2)
                pygame.draw.rect(surface, color, inner)

        if self.hp > 0:
            hp_ratio = min(1.0, self.hp / max(1, self.max_hp_per_life))
            hp_w = int(self.size * hp_ratio)
            hp_by = max(38, by + 6)
            hp_bg = pygame.Rect(self.rect.x, hp_by, self.size, 4)
            pygame.draw.rect(surface, (40, 10, 10), hp_bg)
            life_idx = min(len(LIFE_COLORS) - 1, lost)
            hp_color = LIFE_COLORS[life_idx]
            hp_fill = pygame.Rect(self.rect.x, hp_by, max(2, hp_w), 4)
            pygame.draw.rect(surface, hp_color, hp_fill)

    def play_bounce_sfx(self):
        pass

    def on_wall_hit(self):
        pass

    def _boss_move_only(self, bw, bh):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.vx *= 0.80
        self.vy *= 0.80
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(bw, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(bh, self.rect.bottom)
