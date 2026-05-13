import pygame
import os
import sys
import math
import random

import config

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Ditu.mine_level import BattleLevel
from Ditu.weather.speech import PRIORITY_HIGH
from referee import Referee
from Jue_se.drowned_king import (
    WaterPrisonVFX,
    _asset_path,
    _load_frames,
    _load_sound,
    _safe_load_image,
    _safe_play,
)

BOSS_WIDTH, BOSS_HEIGHT = 1400, 900

BOSS_NAME_BY_MAP = {
    "boss对战_平原要塞.png": "DrownedKing",
}


class LightPillarVFX:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.life = 20
        self.max_life = 20
        self.sparks = []

    def update(self):
        self.life -= 1
        if self.life > 0:
            for _ in range(3):
                angle = random.random() * math.tau
                speed = random.uniform(1.2, 4.2)
                self.sparks.append([
                    self.x,
                    self.y - random.uniform(20, 150),
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    random.randint(12, 22),
                ])
        for spark in self.sparks[:]:
            spark[0] += spark[2]
            spark[1] += spark[3]
            spark[2] *= 0.92
            spark[3] *= 0.92
            spark[4] -= 1
            if spark[4] <= 0:
                self.sparks.remove(spark)

    def is_done(self):
        return self.life <= 0 and not self.sparks

    def draw(self, surface):
        progress = 1.0 - max(0, self.life) / self.max_life
        if self.life > 0:
            height = max(1, int(200 * min(1.0, progress * 1.3)))
            alpha = int(220 * (1.0 - progress * 0.55))
            pillar = pygame.Surface((44, height + 8), pygame.SRCALPHA)
            pygame.draw.line(pillar, (255, 255, 215, alpha), (22, 8), (22, height), 4)
            pygame.draw.line(pillar, (255, 220, 100, alpha // 2), (25, 8), (25, height), 10)
            pygame.draw.line(pillar, (255, 255, 255, alpha // 3), (18, 8), (18, height), 16)
            rect = pillar.get_rect(midbottom=(int(self.x), int(self.y)))
            surface.blit(pillar, rect)
            pygame.draw.circle(surface, (255, 255, 255, alpha), (int(self.x), int(rect.top)), int(7 + 4 * (1 - progress)))
        for sx, sy, _, _, life in self.sparks:
            alpha = max(0, min(180, life * 10))
            pygame.draw.circle(surface, (255, 245, 170, alpha), (int(sx), int(sy)), 3)


class RecallParticle:
    def __init__(self, x, y, target):
        self.x = float(x)
        self.y = float(y)
        self.target = target
        self.life = 24
        self.max_life = 24

    def update(self):
        tx, ty = self.target.rect.center
        self.x += (tx - self.x) * 0.23
        self.y += (ty - self.y) * 0.23
        self.life -= 1

    def is_done(self):
        return self.life <= 0

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(210 * self.life / self.max_life)
        pygame.draw.circle(surface, (90, 220, 255, alpha), (int(self.x), int(self.y)), 5)
        if self.target:
            pygame.draw.line(surface, (90, 220, 255, alpha // 2), (int(self.x), int(self.y)), self.target.rect.center, 2)


class BossLevel(BattleLevel):
    def __init__(self, screen, bg_path, selected_chars, target_size=(BOSS_WIDTH, BOSS_HEIGHT), difficulty=None, buffs=None):
        sw, sh = screen.get_size()

        self.difficulty = difficulty or {"hp_mult": 1.0, "dmg_mult": 1.0, "spd_mult": 1.0, "aggro_mult": 1.0}
        self._boss_char = self._find_boss(selected_chars)
        self._buffs = buffs or []

        super().__init__(screen, bg_path, selected_chars, target_size=target_size)

        self.trident_list = []
        self.manager.drowned_king_tridents = self.trident_list
        self.water_prisons = []
        self.light_pillars = []
        self._recall_particles = []
        self._ripple_active = False
        self._ripple_queue = []
        self._ripple_timer = 0
        self._ripple_interval = 8
        self._ripple_post_timer = 0
        self._ripple_data = {}
        self._ripple_boss = None
        self._shake_amplitude = 0.0
        self._shake_duration = 0
        self._screen_offset_x = 0
        self._screen_offset_y = 0
        self._intro_state = "boss_appear"
        self._intro_timer = 0
        self._intro_corners = [
            (int(self.width * 0.10), int(self.height * 0.10)),
            (int(self.width * 0.90), int(self.height * 0.10)),
            (int(self.width * 0.10), int(self.height * 0.90)),
            (int(self.width * 0.90), int(self.height * 0.90)),
        ]
        self._intro_pins = []
        for cx, cy in self._intro_corners:
            self._intro_pins.append({"x": float(cx), "y": float(-100), "target": (cx, cy), "landed": False, "merged": False, "merge_rot": 0.0})
        self._intro_pin_idx = 0
        self._intro_merge_idx = 0
        self._intro_hand_glow_alpha = 0.0
        self._intro_boss_merge_scale = 1.0
        self._intro_camera_zoom = 1.0
        self._intro_arcs = []
        self._intro_boss_aura_alpha = 0.0
        self._intro_hp_bar_fill = 0.0
        self._intro_total_frames = 0
        self._intro_shockwaves = []
        self._intro_emp_alpha = 0.0
        self._intro_emp_ring_radius = 0.0
        self._intro_emp_particles = []
        self._intro_marked_pins = set()
        self._intro_zap_handle = None
        self._intro_merge_arc_sfx = None
        self._intro_ult_frames = _load_frames(_asset_path("vfx_ult"), scale=(110, 110))
        self._intro_fly_frames = _load_frames(_asset_path("vfx_fly"), scale=(72, 72))
        self._intro_trident_img = _safe_load_image(_asset_path("trident.png"), scale=(72, 72))
        self._intro_sfx_explode = _load_sound("trident_explode.mp3")
        self._intro_sfx_throw = _load_sound("trident_throw.mp3")
        self._intro_sfx_lightning = _load_sound("lightning_strike.mp3", "lightning_strike.mp3")
        self._intro_sfx_drop = [
            _load_sound("lightning_strike.mp3"),
            _load_sound("lightning_strike.mp3"),
            _load_sound("lightning_strike.mp3"),
        ]

        self._poetic_timer = 0
        self._poetic_last = ""

        self.boss = None
        for f in self.manager.fighters:
            if f.__class__.__name__ == self._boss_char:
                self.boss = f
                f.rect.center = (self.width * 4 // 5, self.height // 2)
                f.max_hp = int(f.max_hp * self.difficulty["hp_mult"])
                f.hp = f.max_hp
                f.damage = int(f.damage * self.difficulty["dmg_mult"])
                f.speed *= self.difficulty["spd_mult"]
                if f.__class__.__name__ == "DrownedKing":
                    f.trident_list = self.trident_list
                    f.max_hp = int(f.max_hp * 2.8)
                    f.hp = f.max_hp
                    f.damage = int(f.damage * 2.0)
                    f.speed *= 1.55
                    f.dmg_res = 0.30
                    f.kb_res = 0.89
                break

        if self._buffs and self.boss:
            for bdef in self._buffs:
                _, name, val, dur, btype, *_ = bdef
                for f in self.manager.fighters:
                    if f is not self.boss and f.hp > 0:
                        f.add_buff(name, val, dur, btype)

        for f in self.manager.fighters:
            if f is not self.boss:
                f.set_boss_mode(self.boss)

        self.intro_phase = bool(self.boss and self.boss.__class__.__name__ == "DrownedKing" and not config.SKIP_BOSS_INTRO)
        self.state = "INTRO" if self.intro_phase else "BATTLE"
        self._intro_saved_hp = self.boss.hp if self.boss else 0
        self._intro_saved_max_hp = self.boss.max_hp if self.boss else 0
        self._intro_grace_frames = 0
        if self.intro_phase and self.boss:
            self.boss._intro_locked = True
            self.boss.rect.center = (self.width // 2, self.height // 2)
            for f in self.manager.fighters:
                if f is not self.boss and f.hp > 0:
                    f.rect.x = 30 if f.rect.x < self.width // 2 else self.width - f.size - 30
                    f.rect.y = 30 if f.rect.y < self.height // 2 else self.height - f.size - 30
            if getattr(self.manager, "weather", None):
                self.manager.weather.paused = True
        self.intro_timer = 0
        self.intro_text_timer = 0
        self._boss_hp_display = self.boss.hp if self.boss else 0
        self._boss_phantom_dmg = 0
        self._boss_hp_bar_glow = 0

    def _find_boss(self, chars):
        for c in chars:
            if c in ("DrownedKing", "Drowned"):
                return c
        return "DrownedKing"

    def _do_lifesteal(self, attacker, dmg, from_clone=False):
        if not attacker or attacker.hp <= 0:
            return
        before_hp = attacker.hp
        if before_hp >= attacker.max_hp:
            return
        lifesteal = attacker.get_buff_value("lifesteal")
        clone_mul = 0.4 if from_clone else 1.0
        from entity import FloatText
        if lifesteal > 0:
            heal = min(int(dmg * lifesteal * 0.15 * clone_mul), int(attacker.max_hp * 0.06))
        elif attacker.__class__.__name__ == "Enderman":
            heal = max(1, int(dmg * 0.15 * clone_mul))
        else:
            return
        attacker.hp = min(attacker.max_hp, before_hp + heal)
        if attacker.hp > before_hp:
            color = (80, 255, 120) if lifesteal > 0 else (180, 100, 255)
            attacker.float_texts.append(FloatText(
                attacker.rect.centerx + random.randint(-15, 15),
                attacker.rect.top - 20, f"+{heal}", color))

    def _apply_screen_shake(self, amplitude, duration):
        self._shake_amplitude = max(self._shake_amplitude, float(amplitude))
        self._shake_duration = max(self._shake_duration, int(duration))

    def _tick_screen_shake(self):
        if self._shake_duration > 0 and self._shake_amplitude > 0:
            amp = max(1, int(self._shake_amplitude))
            self._screen_offset_x = random.randint(-amp, amp)
            self._screen_offset_y = random.randint(-amp, amp)
            self._shake_amplitude *= 0.85
            self._shake_duration -= 1
        else:
            self._screen_offset_x = 0
            self._screen_offset_y = 0
            self._shake_amplitude = 0.0
            self._shake_duration = 0

    def _restore_boss_hp(self):
        if self.boss and self._intro_saved_hp > 0:
            self.boss.max_hp = self._intro_saved_max_hp
            self.boss.hp = self._intro_saved_hp
            self._boss_hp_display = self.boss.hp
            self._boss_phantom_dmg = 0

    def _update_intro(self):
        self.intro_text_timer += 1
        self._intro_timer += 1
        self._intro_total_frames += 1
        if self.manager.weather:
            self.manager.weather.paused = True
        if self.boss:
            self.boss._intro_locked = True
            self._restore_boss_hp()

        if self._intro_zap_handle is None and self._intro_state != "battle_begin":
            snd = _load_sound("lightning_strike.mp3.mp3", "lightning_strike.mp3")
            if snd:
                try:
                    snd.set_volume(0.35)
                    snd.play(loops=-1)
                    self._intro_zap_handle = snd
                except Exception:
                    pass

        fill_duration = 1300
        if self._intro_total_frames <= fill_duration:
            self._intro_hp_bar_fill = min(1.0, self._intro_total_frames / 800.0)

        st = self._intro_state
        if st == "boss_appear":
            self._update_intro_appear()
        elif st == "storm_warning":
            self._update_intro_storm_warning()
        elif st == "pin_trident":
            self._update_intro_pin()
        elif st == "hold_dread":
            self._update_intro_hold_dread()
        elif st == "emp_wave":
            self._update_intro_emp()
        elif st == "merge_trident":
            self._update_intro_merge()
        elif st == "body_burst":
            self._update_intro_burst()
        elif st == "shrink_settle":
            self._update_intro_shrink()
        elif st == "battle_begin":
            self._update_intro_battle_begin()

    def _update_boss_scale_sync(self):
        if self.boss:
            self.boss._intro_scale = self._intro_boss_merge_scale

    def _update_intro_appear(self):
        t = self._intro_timer
        if t >= 80:
            self._advance_intro("storm_warning")

    def _update_intro_storm_warning(self):
        t = self._intro_timer
        if t % 12 == 1 and t < 70:
            self._apply_screen_shake(1, 6)
        if t in (10, 35, 60):
            _safe_play(self._intro_sfx_lightning, 0.08)
        if t == 25:
            _safe_play(self._intro_sfx_lightning, 0.12)
            self._apply_screen_shake(4, 14)
        if t == 55:
            _safe_play(self._intro_sfx_lightning, 0.16)
            self._apply_screen_shake(6, 18)
        if t >= 80:
            self._intro_pin_idx = 0
            self._advance_intro("pin_trident")

    def _update_intro_pin(self):
        t = self._intro_timer
        idx = self._intro_pin_idx
        if idx >= 4:
            self._advance_intro("hold_dread")
            return
        pin = self._intro_pins[idx]
        tx, ty = pin["target"]
        duration = 65
        descend_frames = duration - 10
        if t < descend_frames:
            progress = min(1.0, t / float(descend_frames - 8))
            pin["y"] = -120 + (ty + 120) * (progress ** 2.0)
            pin["x"] = float(tx)
        if t == descend_frames - 2:
            pin["landed"] = True
            pin["y"] = float(ty)
            amp = 22 + idx * 5
            self._apply_screen_shake(amp, 28 + idx * 4)
            _safe_play(self._intro_sfx_lightning, 0.7)
            _safe_play(random.choice(self._intro_sfx_drop), 0.9)
            for _ in range(4):
                ex = pin["target"][0] + random.uniform(-18, 18)
                ey = pin["target"][1] + random.uniform(-18, 18)
                self._intro_arcs.append([tx, ty, ex, ey, 4, 200])
        if t >= duration:
            self._intro_pin_idx += 1
            self._advance_intro("pin_trident")

    def _update_intro_hold_dread(self):
        t = self._intro_timer
        if t % 40 == 1 and t > 5:
            _safe_play(self._intro_sfx_lightning, 0.14)
        if t % 10 == 1 and t < 80:
            self._apply_screen_shake(1, 5)
        if t >= 100:
            self._advance_intro("emp_wave")

    def _update_intro_emp(self):
        t = self._intro_timer
        bx, by = self.boss.rect.center if self.boss else (self.width//2, self.height//2)
        max_radius = math.hypot(self.width, self.height) * 0.75
        if t <= 50:
            self._intro_emp_ring_radius = 10.0 + max_radius * (t / 50.0) ** 0.7
            self._intro_emp_alpha = min(0.55, t / 40.0)
            if t % 2 == 0:
                _safe_play(self._intro_sfx_lightning, 0.04)
            if t == 50:
                for pin in self._intro_pins:
                    if pin["landed"]:
                        self._intro_marked_pins.add(self._intro_pins.index(pin))
                self._apply_screen_shake(12, 30)
                _safe_play(self._intro_sfx_lightning, 0.5)
                _safe_play(random.choice(self._intro_sfx_drop), 0.85)
        elif t <= 65:
            self._intro_emp_alpha = 0.55
            if t == 51:
                for _ in range(80):
                    ang = random.random() * math.tau
                    rr = random.uniform(50, max_radius)
                    px = bx + math.cos(ang) * rr
                    py = by + math.sin(ang) * rr
                    self._intro_emp_particles.append({
                        "x": px, "y": py,
                        "vx": random.uniform(-1, 1),
                        "vy": random.uniform(-1, 1),
                        "life": random.randint(40, 90),
                        "alpha": random.randint(60, 160),
                    })
        elif t <= 110:
            self._intro_emp_alpha = 0.55 - 0.55 * min(1.0, (t - 65) / 35.0)
            dead = []
            for i, ep in enumerate(self._intro_emp_particles):
                ep["vx"] += (bx - ep["x"]) * 0.015
                ep["vy"] += (by - ep["y"]) * 0.015
                ep["x"] += ep["vx"]
                ep["y"] += ep["vy"]
                ep["life"] -= 1
                ep["alpha"] = max(0, ep["alpha"] - 2.5)
                if ep["life"] <= 0 or ep["alpha"] <= 0:
                    dead.append(i)
            for i in reversed(dead):
                self._intro_emp_particles.pop(i)
            if t % 3 == 0:
                for _ in range(15):
                    ang = random.random() * math.tau
                    rr = random.uniform(30, max_radius * 0.6)
                    px = bx + math.cos(ang) * rr
                    py = by + math.sin(ang) * rr
                    self._intro_emp_particles.append({
                        "x": px, "y": py,
                        "vx": (bx - px) * random.uniform(0.03, 0.08),
                        "vy": (by - py) * random.uniform(0.03, 0.08),
                        "life": random.randint(30, 60),
                        "alpha": random.randint(80, 200),
                    })
        if t >= 110:
            self._intro_emp_particles[:] = []
            self._intro_emp_alpha = 0.0
            self._intro_merge_idx = 0
            self._advance_intro("merge_trident")

    def _update_intro_merge(self):
        t = self._intro_timer
        idx = self._intro_merge_idx
        if idx >= 4:
            if self._intro_merge_arc_sfx:
                try:
                    self._intro_merge_arc_sfx.stop()
                except Exception:
                    pass
                self._intro_merge_arc_sfx = None
            self._advance_intro("body_burst")
            return
        if t == 1 and self._intro_merge_arc_sfx is None:
            snd = _load_sound("trident_throw.mp3")
            if snd:
                try:
                    snd.set_volume(0.25)
                    snd.play(loops=-1)
                    self._intro_merge_arc_sfx = snd
                except Exception:
                    pass
        pin = self._intro_pins[idx]
        tx, ty = pin["target"]
        bx, by = self.boss.rect.center if self.boss else (self.width//2, self.height//2)
        duration = 85
        active_frames = duration - 12
        if t < active_frames:
            progress = min(1.0, t / float(active_frames - 6))
            eased = progress ** 1.5
            pin["x"] = tx + (bx - tx) * eased
            pin["y"] = ty + (by - ty) * eased - abs(math.sin(eased * math.pi)) * 80
            pin["merge_rot"] += 18.0
            if t % 4 == 0:
                for _ in range(3):
                    arc_end_x = bx + random.uniform(-50, 50)
                    arc_end_y = by + random.uniform(-50, 50)
                    self._intro_arcs.append([bx, by, arc_end_x, arc_end_y, 6, 200])
                for _ in range(2):
                    self._intro_arcs.append([pin["x"], pin["y"], bx + random.uniform(-25, 25), by + random.uniform(-25, 25), 4, 230])
            if t % 6 == 0:
                _safe_play(self._intro_sfx_lightning, 0.12)
        if t == active_frames - 2:
            _safe_play(self._intro_sfx_lightning, 0.55 + idx * 0.05)
            _safe_play(random.choice(self._intro_sfx_drop), 0.75)
            self._apply_screen_shake(20 + idx * 6, 22)
            pin["merged"] = True
            pin["x"] = float(bx)
            pin["y"] = float(by)
            scale_inc = 0.08 + idx * 0.03
            self._intro_boss_merge_scale += scale_inc
            self._intro_boss_aura_alpha = min(1.0, self._intro_boss_aura_alpha + 0.25)
            self._intro_hand_glow_alpha = min(1.0, self._intro_hand_glow_alpha + 0.18)
            self._update_boss_scale_sync()
            for _ in range(20 + idx * 4):
                ang = random.random() * math.tau
                r = random.uniform(60, 160)
                arc_x2 = bx + math.cos(ang) * r
                arc_y2 = by + math.sin(ang) * r
                self._intro_arcs.append([bx, by, arc_x2, arc_y2, 8, 230])
        if t >= duration:
            self._intro_merge_idx += 1
            self._advance_intro("merge_trident")

    def _update_intro_burst(self):
        t = self._intro_timer
        bx, by = self.boss.rect.center if self.boss else (self.width//2, self.height//2)
        fx, fy = self.boss._facing if self.boss else (1.0, 0.0)
        hx = bx + fx * 34
        hy = by + fy * 34
        if t == 1:
            _safe_play(self._intro_sfx_lightning, 1.0)
            _safe_play(random.choice(self._intro_sfx_drop), 1.0)
            self._apply_screen_shake(40, 55)
            for _ in range(50):
                ang = random.random() * math.tau
                r = random.uniform(40, 250)
                arc_x2 = bx + math.cos(ang) * r
                arc_y2 = by + math.sin(ang) * r
                self._intro_arcs.append([bx, by, arc_x2, arc_y2, 6, 255])
        if t <= 30:
            if t % 6 == 0:
                for _ in range(10):
                    ang = random.random() * math.tau
                    r = random.uniform(80, 220)
                    arc_x2 = bx + math.cos(ang) * r
                    arc_y2 = by + math.sin(ang) * r
                    self._intro_arcs.append([bx, by, arc_x2, arc_y2, 5, 240])
        if t <= 20:
            peak = self._intro_boss_merge_scale + 0.15
            self._intro_boss_merge_scale += (peak - self._intro_boss_merge_scale) * 0.12
            self._update_boss_scale_sync()
        if t == 35:
            for arc in self._intro_arcs:
                arc[2] = hx + random.uniform(-12, 12)
                arc[3] = hy + random.uniform(-12, 12)
            self._intro_boss_aura_alpha = 0.5
        if t > 35:
            self._intro_boss_aura_alpha = max(0.2, self._intro_boss_aura_alpha - 0.006)
            self._intro_hand_glow_alpha = min(1.0, self._intro_hand_glow_alpha + 0.02)
        if t >= 80:
            self._advance_intro("shrink_settle")

    def _update_intro_shrink(self):
        t = self._intro_timer
        if t == 1:
            bx, by = self.boss.rect.center if self.boss else (self.width//2, self.height//2)
            for i in range(3):
                self._intro_shockwaves.append({"cx": bx, "cy": by, "radius": 10.0, "speed": 12.0 + i * 6, "alpha": 220 + i * 30, "fade": 2.5 + i * 0.6})
            _safe_play(self._intro_sfx_lightning, 0.6)
            _safe_play(random.choice(self._intro_sfx_drop), 0.9)
            self._apply_screen_shake(25, 35)
        if t >= 20 and self._intro_boss_merge_scale > 1.01:
            target = 1.0
            self._intro_boss_merge_scale += (target - self._intro_boss_merge_scale) * 0.06
            self._update_boss_scale_sync()
        if t > 30:
            self._intro_boss_aura_alpha = max(0.15, self._intro_boss_aura_alpha - 0.008)
        if t >= 80:
            self._advance_intro("battle_begin")

    def _update_intro_battle_begin(self):
        t = self._intro_timer
        if self._intro_zap_handle:
            try:
                self._intro_zap_handle.stop()
            except Exception:
                pass
            self._intro_zap_handle = None
        if self._intro_merge_arc_sfx:
            try:
                self._intro_merge_arc_sfx.stop()
            except Exception:
                pass
            self._intro_merge_arc_sfx = None
        self._intro_hp_bar_fill = min(1.0, 1.0 + (t - 30) * 0.04 if t > 30 else self._intro_hp_bar_fill + 0.015)
        self._intro_boss_aura_alpha = max(0.0, self._intro_boss_aura_alpha - 0.015)
        if t > 40:
            self._intro_hp_bar_fill = 1.0
        if t >= 55:
            self._restore_boss_hp()
            self._boss_hp_display = self.boss.hp if self.boss else 0
            if self.boss:
                self.boss._intro_locked = False
                self.boss.rect.center = (self.width//2, self.height//2)
                self.boss._intro_scale = 1.0
                self._intro_boss_merge_scale = 1.0
                if hasattr(self.boss, "hand_vfx_alpha"):
                    self.boss.hand_vfx_alpha = self._intro_hand_glow_alpha
            self.intro_phase = False
            self.state = "BATTLE"
            if self.manager.weather:
                self.manager.weather.paused = False
            self._intro_grace_frames = 90

    def _advance_intro(self, state):
        self._intro_state = state
        self._intro_timer = 0

    def _ensure_water_prison(self, target, vfx=None):
        for prison in self.water_prisons:
            if prison.target is target:
                prison.refresh()
                return prison
        prison = vfx if isinstance(vfx, WaterPrisonVFX) else WaterPrisonVFX(target)
        self.water_prisons.append(prison)
        return prison

    def _update_water_prisons(self):
        for prison in self.water_prisons[:]:
            if not prison.update():
                self.water_prisons.remove(prison)

    def _update_light_pillars(self):
        for pillar in self.light_pillars[:]:
            pillar.update()
            if pillar.is_done():
                self.light_pillars.remove(pillar)

    def _spawn_recall_particles(self, tridents, boss):
        for trident in tridents:
            self._recall_particles.append(RecallParticle(trident.x, trident.y, boss))

    def _update_recall_particles(self):
        for particle in self._recall_particles[:]:
            particle.update()
            if particle.is_done():
                self._recall_particles.remove(particle)

    def _start_ripple_detonation(self, tridents, boss, data):
        active = [trident for trident in tridents if getattr(trident, "active", False)]
        active.sort(key=lambda trident: math.hypot(trident.x - boss.rect.centerx, trident.y - boss.rect.centery))
        self._ripple_queue = active
        self._ripple_data = dict(data or {})
        self._ripple_boss = boss
        self._ripple_timer = 0
        self._ripple_post_timer = 20
        self._ripple_active = bool(active)
        if active:
            self._apply_screen_shake(18, 30)

    def _update_ripple_detonation(self):
        if not self._ripple_active:
            return
        if self._ripple_queue:
            self._ripple_timer -= 1
            if self._ripple_timer > 0:
                return
            trident = self._ripple_queue.pop(0)
            self._detonate_trident(trident)
            self._ripple_timer = self._ripple_interval
            return
        self._ripple_post_timer -= 1
        if self._ripple_post_timer <= 0:
            self._ripple_active = False
            self._ripple_boss = None
            self._ripple_data = {}
            self.trident_list[:] = [trident for trident in self.trident_list if getattr(trident, "active", False)]
            self.manager.drowned_king_tridents = self.trident_list

    def _detonate_trident(self, trident):
        boss = self._ripple_boss or self.boss
        if not boss or not getattr(trident, "active", False):
            return
        radius = self._ripple_data.get("radius", 120)
        base_damage = self._ripple_data.get("base_damage", 18)
        damage_multiplier = self._ripple_data.get("damage_multiplier", 0.8)
        damage = max(1, int(round(base_damage * damage_multiplier)))
        self.light_pillars.append(LightPillarVFX(trident.x, trident.y))
        if hasattr(boss, "add_lightning_burst"):
            boss.add_lightning_burst(trident.x, trident.y, radius)
        self._apply_screen_shake(12, 14)
        for fighter in self.manager.fighters:
            if fighter is boss or getattr(fighter, "hp", 0) <= 0:
                continue
            dist = math.hypot(fighter.rect.centerx - trident.x, fighter.rect.centery - trident.y)
            if dist <= radius + fighter.size * 0.5:
                self._damage_fighter(fighter, damage, boss)
        trident.destroy()

    def update(self):
        mgr = self.manager
        self._tick_screen_shake()

        if self.intro_phase:
            self._update_intro()
            return

        if self._intro_grace_frames > 0:
            if self.boss:
                self.boss.hp = self._intro_saved_hp
                self._boss_hp_display = self.boss.hp
            self._intro_grace_frames -= 1

        freeze_for_ult = (
            self.boss
            and getattr(self.boss, "state", None) == "ULTIMATE"
            and getattr(self.boss, "state_age", 999) < 30
        )

        for f in mgr.fighters:
            f.update_buffs()
            clsname = f.__class__.__name__
            if freeze_for_ult and f is not self.boss:
                continue

            if clsname == self._boss_char:
                tridents_out = []
                if clsname == "DrownedKing":
                    result = f.update(mgr.fighters, self.width, self.height, tridents_out, weather=mgr.weather)
                else:
                    result = f.update(mgr.fighters, self.width, self.height, tridents_out)
                for t in tridents_out:
                    t.shooter = f
                    if getattr(t, "is_drowned_king_trident", False):
                        self.trident_list.append(t)
                    else:
                        mgr.arrows.append(t)
                if clsname == "DrownedKing":
                    self._resolve_drowned_king_flags(f)
                if result:
                    self._apply_boss_attack_result(result, f)
            elif clsname == "Illusioner":
                boss_plus_clones = [f for f in mgr.fighters if f is self.boss or f.__class__.__name__ == "IllusionerClone"]
                if not boss_plus_clones and self.boss:
                    boss_plus_clones = [self.boss]
                result = f.update(boss_plus_clones, self.width, self.height)
                if result:
                    proj = result.get("projectile")
                    if proj:
                        mgr.arrows.append(proj)
                    projs = result.get("projectiles")
                    if projs:
                        for p in projs:
                            mgr.arrows.append(p)
                    spawns = result.get("spawns")
                    if spawns:
                        for spawn in spawns:
                            mgr.fighters.append(spawn)
                        f.current_enemies = mgr.fighters
            elif clsname == "IllusionerClone":
                result = f.update([self.boss] if self.boss and self.boss.hp > 0 else mgr.fighters, self.width, self.height)
                if result:
                    proj = result.get("projectile")
                    if proj:
                        mgr.arrows.append(proj)
            elif clsname == "Zombie":
                result = f.update([self.boss] if self.boss and self.boss.hp > 0 else mgr.fighters, self.width, self.height)
                if result:
                    self._apply_boss_result(result, f)
            elif clsname == "Enderman":
                result = f.update([self.boss] if self.boss and self.boss.hp > 0 else mgr.fighters, self.width, self.height)
                if result:
                    self._apply_boss_result(result, f)
            elif clsname == "Creeper":
                tr = self._closest_rect(f)
                result = f.update(tr, self.width, self.height)
                if result:
                    self._creeper_boom(result, f)
            elif clsname == "Skeleton":
                f.update(self.width, self.height, self._closest_rect(f), mgr.arrows)
            elif clsname == "MaoDie":
                result = f.update([self.boss] if self.boss and self.boss.hp > 0 else mgr.fighters, self.width, self.height)
                if result:
                    self._apply_boss_result(result, f)

        self._update_drowned_king_tridents()
        self._update_ripple_detonation()
        self._update_water_prisons()
        self._update_light_pillars()
        self._update_recall_particles()

        for a in mgr.arrows[:]:
            try:
                a.update()
            except TypeError:
                try:
                    a.update(self.width, self.height)
                except Exception:
                    pass
            if hasattr(a, 'is_dead') and a.is_dead():
                mgr.arrows.remove(a)
                continue
            ax = getattr(a, 'x', -999)
            ay = getattr(a, 'y', -999)
            if not (0 < ax < self.width and 0 < ay < self.height):
                mgr.arrows.remove(a)
                continue

            arrow_hit_block = False
            for b in mgr.map_mgr.blocks:
                if b.active and getattr(b, 'rect', None):
                    if b.rect.collidepoint(ax, ay):
                        b.hit(mgr.map_mgr.particles)
                        arrow_hit_block = True
                        break
            if arrow_hit_block:
                mgr.arrows.remove(a)
                continue

            for ef in mgr.fighters:
                if getattr(a, 'damage', 0) > 0 and ef.hp > 0:
                    shooter = getattr(a, 'shooter', None)
                    is_boss_arrow = (shooter is self.boss)
                    if is_boss_arrow and ef is self.boss:
                        continue
                    if not is_boss_arrow and ef is not self.boss:
                        continue
                    if math.hypot(ef.rect.centerx - ax, ef.rect.centery - ay) < getattr(a, 'size', 20) + ef.size // 2:
                        dmg = a.damage
                        is_crit = False
                        if shooter and shooter is not self.boss and shooter.hp > 0:
                            dmg_buff = shooter.get_buff_value("atk_up")
                            dmg += dmg_buff
                            amp = shooter.get_buff_value("dmg_amp")
                            dmg += amp
                            crit = shooter.get_buff_value("crit_up")
                            if crit > 0 and random.random() < 0.25:
                                dmg = int(dmg * 1.8)
                                is_crit = True
                                from entity import FloatText
                                shooter.float_texts.append(FloatText(
                                    shooter.rect.centerx + random.randint(-15, 15),
                                    shooter.rect.top - 35,
                                    "会心!", (255, 215, 0)))
                        try:
                            ef.take_damage(dmg, attacker=shooter)
                        except Exception:
                            ef.take_damage(dmg)
                        if ef is self.boss:
                            self._boss_phantom_dmg = min(self._boss_phantom_dmg + dmg, self.boss.max_hp * 2)
                            from entity import FloatText
                            ox = ef.rect.centerx + random.randint(-30, 30)
                            oy = ef.rect.top - 15 - random.randint(0, 40)
                            if is_crit:
                                ef.float_texts.append(FloatText(ox, oy, f"-{dmg}!", (255, 20, 0)))
                                ef.float_texts.append(FloatText(ox + 2, oy - 2, f"-{dmg}!", (255, 60, 20)))
                                ef.float_texts.append(FloatText(ox - 1, oy - 1, f"-{dmg}!", (255, 200, 40)))
                            else:
                                ef.float_texts.append(FloatText(ox, oy, f"-{dmg}", (255, 255, 255)))
                            if shooter and shooter is not self.boss and shooter.hp > 0:
                                self._do_lifesteal(shooter, dmg, getattr(a, 'from_clone', False))
                        mgr.arrows.remove(a)
                        break

        for b in mgr.map_mgr.blocks:
            if b.active:
                b.update()
                for f in mgr.fighters:
                    if getattr(f, 'hp', 0) <= 0:
                        continue
                    if Referee.process_collision(f, b):
                        b.hit(mgr.map_mgr.particles)
                        if hasattr(f, 'play_bounce_sfx'):
                            f.play_bounce_sfx()

        mgr.map_mgr.update()

        for i in range(len(mgr.fighters)):
            for j in range(i + 1, len(mgr.fighters)):
                fi, fj = mgr.fighters[i], mgr.fighters[j]
                if fi.hp > 0 and fj.hp > 0:
                    if fi is self.boss or fj is self.boss:
                        if fi is self.boss:
                            boss, other = fi, fj
                        else:
                            boss, other = fj, fi
                        self._boss_challenger_collision(boss, other)
                    else:
                        self._challenger_collision(fi, fj)

        mgr.weather.update()

        if mgr.enchant_altar and mgr.enchant_altar.active:
            mgr.enchant_altar.update()
            for f in mgr.fighters:
                if f.__class__.__name__ == "MaoDie" and f.hp > 0:
                    if getattr(f, '_enchanted', False):
                        mgr.enchant_altar.active = False
                    elif f._boss_mode and mgr.enchant_altar.rect.colliderect(f.rect):
                        f.apply_enchant_buff()
                        mgr.enchant_altar.active = False

        for f in mgr.fighters[:]:
            if f.__class__.__name__ == "IllusionerClone" and (f.hp <= 0 or f.parent.hp <= 0):
                mgr.fighters.remove(f)

        for f in mgr.fighters:
            if getattr(f, '_pending_speech', None):
                if f.hp > 0:
                    text = f._pending_speech
                    if len(text) > 18:
                        mid = len(text) // 2
                        bp = text.rfind("。", 0, mid + 1)
                        if bp < 0:
                            bp = text.rfind("，", 0, mid + 1)
                        if bp > 2:
                            part1, part2 = text[:bp + 1], text[bp + 1:]
                            mgr.weather.speech_bubble.set(part1, f, duration=260, priority=PRIORITY_HIGH)
                            f._speech_followup = part2
                            f._pending_speech = None
                            continue
                    mgr.weather.speech_bubble.set(text, f, duration=360, priority=PRIORITY_HIGH)
                f._pending_speech = None

            if getattr(f, '_speech_followup', None) and not mgr.weather.speech_bubble.is_fighter_speaking(f):
                text = f._speech_followup
                f._speech_followup = None
                mgr.weather.speech_bubble.set(text, f, duration=260, priority=PRIORITY_HIGH)

        self._boss_phantom_dmg = max(0, self._boss_phantom_dmg - 1.5)

        self._poetic_timer += 1
        if self._poetic_timer >= 600:
            self._poetic_timer = 0
            if random.random() < 0.50:
                alive = [f for f in mgr.fighters if f.hp > 0
                         and not mgr.weather.speech_bubble.is_fighter_speaking(f)
                         and not getattr(f, '_pending_speech', None)]
                if alive:
                    if self.boss and self.boss.hp > 0 and random.random() < 0.6:
                        speaker = self.boss
                        from i18n import t as _lt
                        boss_line_keys = [f"boss_line_{i}" for i in range(1, 12)]
                        line = None
                        for _ in range(12):
                            line = _lt(random.choice(boss_line_keys))
                            if not line.startswith("boss_line_") and line != self._poetic_last:
                                break
                        if not line or line.startswith("boss_line_"):
                            line = None
                        if line is None:
                            pass
                        else:
                            self._poetic_last = line
                            if len(line) > 18:
                                mid = len(line) // 2
                                bp = line.rfind("。", 0, mid + 1)
                                if bp < 0:
                                    bp = line.rfind("，", 0, mid + 1)
                                if bp > 2:
                                    part1, part2 = line[:bp + 1], line[bp + 1:]
                                    mgr.weather.speech_bubble.set(part1, speaker, duration=260, priority=PRIORITY_HIGH)
                                    speaker._speech_followup = part2
                                else:
                                    mgr.weather.speech_bubble.set(line, speaker, duration=300, priority=PRIORITY_HIGH)
                            else:
                                mgr.weather.speech_bubble.set(line, speaker, duration=300, priority=PRIORITY_HIGH)
                    else:
                        challengers = [f for f in alive if f is not self.boss]
                        if challengers:
                            speaker = random.choice(challengers)
                            from i18n import t as _lt
                            retort_keys = [f"boss_retort_line_{i}" for i in range(1, 6)]
                            line = _lt(random.choice(retort_keys))
                            if not line.startswith("boss_retort_line_"):
                                mgr.weather.speech_bubble.set(line, speaker, duration=200, priority=PRIORITY_HIGH)

        self._check_panel_announcement()
        self._update_panel_announcement()

    def draw(self):
        game_surf = pygame.Surface((self.width, self.height))
        if self.bg_img:
            game_surf.blit(self.bg_img, (0, 0))
        else:
            game_surf.fill((30, 30, 30))
        self._draw_battle_layers(game_surf)
        if self.intro_phase:
            self._draw_intro(game_surf)
        elif self._ripple_active or (self.boss and getattr(self.boss, "state", None) == "ULTIMATE"):
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((30, 90, 160, 48))
            game_surf.blit(overlay, (0, 0))

        if self.global_bg:
            self.screen.blit(self.global_bg, (0, 0))
        else:
            self.screen.fill((10, 10, 10))

        self.screen.blit(game_surf, (
            self.offset_x + self._screen_offset_x,
            self.offset_y + self._screen_offset_y,
        ))

        border_rect = pygame.Rect(self.offset_x, self.offset_y, self.width, self.height)
        season_color = (168, 184, 100)
        try:
            w = self.manager.weather
            sk = w.current_season if hasattr(w, 'current_season') else None
            if sk:
                from Ditu.weather.season import SEASON_COLORS
                season_color = SEASON_COLORS.get(sk, season_color)
        except Exception:
            pass
        pygame.draw.rect(self.screen, season_color, border_rect, width=4)
        self.manager.weather.speech_bubble.draw(self.screen, self.offset_x, self.offset_y)
        self._draw_left_panel()
        if self.boss and self.boss.hp > 0:
            self._draw_boss_hp_bar()

    def _draw_battle_layers(self, surface):
        mgr = self.manager
        mgr.weather.draw_bottom(surface)
        if mgr.env_mechanics:
            mgr.env_mechanics.draw_bottom(surface)
        mgr.map_mgr.draw(surface)
        if self.intro_phase and self.boss:
            for fighter in mgr.fighters:
                if fighter is self.boss:
                    continue
                fighter.draw(surface)
            self.boss.draw(surface)
        else:
            for fighter in mgr.fighters:
                fighter.draw(surface)
        self._draw_taunt_indicator(surface)
        for prison in self.water_prisons:
            prison.draw(surface)
        for arrow in mgr.arrows:
            arrow.draw(surface)
        for trident in self.trident_list:
            trident.draw(surface)
        for particle in self._recall_particles:
            particle.draw(surface)
        for pillar in self.light_pillars:
            pillar.draw(surface)
        if mgr.enchant_altar and mgr.enchant_altar.active:
            mgr.enchant_altar.draw(surface)
        if mgr.env_mechanics:
            mgr.env_mechanics.draw_top(surface)
        mgr.weather.draw_top(surface)

    def _draw_taunt_indicator(self, surface):
        if not self.boss or self.boss.hp <= 0:
            return
        target = getattr(self.boss, "_taunt_target", None)
        if not target or target.hp <= 0:
            return
        cx, cy = target.rect.center
        radius = target.size // 2 + 14
        pulse = int(6 * abs(math.sin(pygame.time.get_ticks() * 0.012)))
        alpha = 160 + pulse * 4
        indicator = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
        center = radius + 6
        pygame.draw.circle(indicator, (255, 40, 40, alpha), (center, center), radius, 5)
        pygame.draw.circle(indicator, (255, 80, 80, alpha // 2), (center, center), radius + 4, 2)
        s = int(radius * 0.3)
        pygame.draw.line(indicator, (255, 60, 60, alpha), (center - radius - 2, center - s), (center - radius - 2, center + s), 4)
        pygame.draw.line(indicator, (255, 60, 60, alpha), (center + radius + 2, center - s), (center + radius + 2, center + s), 4)
        pygame.draw.line(indicator, (255, 60, 60, alpha), (center - s, center - radius - 2), (center + s, center - radius - 2), 4)
        pygame.draw.line(indicator, (255, 60, 60, alpha), (center - s, center + radius + 2), (center + s, center + radius + 2), 4)
        surface.blit(indicator, indicator.get_rect(center=(cx, cy)))

    def _draw_intro(self, surface):
        st = self._intro_state
        if st in ("pin_trident", "hold_dread", "emp_wave", "merge_trident", "body_burst", "shrink_settle", "battle_begin"):
            for pin in self._intro_pins:
                if pin["merged"]:
                    continue
                if st == "merge_trident" and self._intro_merge_idx < 4:
                    active_pin = self._intro_pins[self._intro_merge_idx]
                    if pin is active_pin:
                        continue
                self._draw_intro_trident_static(surface, pin)

        if st == "merge_trident":
            idx = self._intro_merge_idx
            if idx < 4:
                pin = self._intro_pins[idx]
                if not pin["merged"]:
                    self._draw_merge_trail(surface, pin)

        for arc in self._intro_arcs[:]:
            x1, y1, x2, y2, life, alpha = arc
            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)
            if dist < 4 or life <= 0:
                self._intro_arcs.remove(arc)
                continue
            arc_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            a = min(255, alpha)
            segments = max(3, int(dist / 16))
            pts = [(x1, y1)]
            for s in range(1, segments):
                t = s / float(segments)
                jx = x1 + (x2 - x1) * t + random.uniform(-dist * 0.08, dist * 0.08)
                jy = y1 + (y2 - y1) * t + random.uniform(-dist * 0.08, dist * 0.08)
                pts.append((jx, jy))
            pts.append((x2, y2))
            ip = [(int(p[0]), int(p[1])) for p in pts]
            pygame.draw.lines(arc_surf, (160, 210, 255, min(255, a * 2 // 3)), False, ip, 3)
            pygame.draw.lines(arc_surf, (255, 255, 255, a), False, ip, 1)
            surface.blit(arc_surf, (0, 0))
            arc[4] -= 1
            arc[5] -= 10

        if self._intro_boss_aura_alpha > 0.01 and self.boss:
            bx, by = self.boss.rect.center
            aura = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            a = int(140 * self._intro_boss_aura_alpha)
            radius = int(65 + 35 * math.sin(self.intro_text_timer * 0.12))
            for r_offset in range(3):
                ra = int(a // (r_offset + 2))
                pygame.draw.circle(aura, (60, 190, 255, ra), (bx, by), radius + r_offset * 10, max(1, 6 - r_offset * 2))
            for _ in range(6):
                ang = random.random() * math.tau
                rx = bx + math.cos(ang) * (radius - 2)
                ry = by + math.sin(ang) * (radius - 2)
                pygame.draw.circle(aura, (190, 250, 255, a), (int(rx), int(ry)), random.randint(3, 7))
            surface.blit(aura, (0, 0))

        for sw in self._intro_shockwaves[:]:
            sw["radius"] += sw["speed"]
            sw["alpha"] -= sw["fade"]
            if sw["alpha"] <= 0:
                self._intro_shockwaves.remove(sw)
                continue
            ring = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            a = min(255, int(sw["alpha"]))
            r = int(sw["radius"])
            num_arcs = max(16, int(r * 0.5))
            for i in range(num_arcs):
                angle = math.tau * i / num_arcs
                arc_len = random.uniform(8, 22)
                angle_jitter = (arc_len / max(1, r)) * random.uniform(-0.6, 0.6)
                a1 = angle + angle_jitter
                a2 = angle + (arc_len / max(1, r)) + angle_jitter * 0.5
                sx = sw["cx"] + math.cos(a1) * r
                sy = sw["cy"] + math.sin(a1) * r
                ex = sw["cx"] + math.cos(a2) * r
                ey = sw["cy"] + math.sin(a2) * r
                segs = 3
                pts = [(sx, sy)]
                for s in range(1, segs):
                    t = s / float(segs)
                    pts.append((sx + (ex - sx) * t + random.uniform(-5, 5),
                                sy + (ey - sy) * t + random.uniform(-5, 5)))
                pts.append((ex, ey))
                ip = [(int(p[0]), int(p[1])) for p in pts]
                color = (255, 255, 255, min(255, a)) if i % 3 == 0 else (140, 200, 255, min(255, a * 3 // 4))
                pygame.draw.lines(ring, color, False, ip, 1)
            surface.blit(ring, (0, 0))

        if self._intro_emp_alpha > 0.01:
            bx, by = self.boss.rect.center if self.boss else (self.width//2, self.height//2)
            r = int(self._intro_emp_ring_radius)
            if r > 0:
                emp_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                a = int(50 * self._intro_emp_alpha)
                for rr in range(8, min(r, int(r * 0.97) if r > 30 else r), 22):
                    fa = min(a, a - int(a * rr / max(1, r)))
                    if fa > 2:
                        pygame.draw.circle(emp_surf, (40, 110, 200, fa), (bx, by), rr, 0)
                pygame.draw.circle(emp_surf, (80, 160, 240, int(50 * self._intro_emp_alpha)), (bx, by), r, 4)
                pygame.draw.circle(emp_surf, (140, 210, 255, int(90 * self._intro_emp_alpha)), (bx, by), r, 2)
                surface.blit(emp_surf, (0, 0))
            for ep in self._intro_emp_particles:
                epa = min(255, int(ep["alpha"]))
                pygame.draw.circle(surface, (120, 190, 255, epa), (int(ep["x"]), int(ep["y"])), 3)
            if self._intro_marked_pins and self._intro_emp_alpha > 0.15:
                for idx in self._intro_marked_pins:
                    if idx < len(self._intro_pins):
                        pin = self._intro_pins[idx]
                        px, py = int(pin["target"][0]), int(pin["target"][1])
                        glow_a = int(70 + 50 * math.sin(self.intro_text_timer * 0.2))
                        pygame.draw.circle(surface, (100, 180, 255, glow_a), (px, py), 18, 3)
                        pygame.draw.circle(surface, (180, 230, 255, glow_a // 2), (px, py), 24, 1)

    def _draw_intro_trident_static(self, surface, pin):
        x, y = int(pin["x"]), int(pin["y"])
        if self._intro_trident_img and self.boss:
            bx, by = self.boss.rect.center
            angle = math.degrees(math.atan2(by - y, bx - x))
            img = pygame.transform.rotate(self._intro_trident_img, angle)
            surface.blit(img, img.get_rect(center=(x, y)))

    def _draw_merge_trail(self, surface, pin):
        x, y = int(pin["x"]), int(pin["y"])
        tx, ty = pin["target"]
        if self._intro_fly_frames:
            frame = self._intro_fly_frames[self.intro_text_timer % len(self._intro_fly_frames)]
            angle = pin["merge_rot"]
            rotated = pygame.transform.rotate(frame, angle)
            rotated.set_alpha(190)
            surface.blit(rotated, rotated.get_rect(center=(x, y)))

    def _draw_boss_hp_bar(self):
        bar_w = self.width
        bar_h = 18
        bx = self.offset_x
        by = self.offset_y - bar_h - 10
        if by < 2:
            by = max(2, self.offset_y - bar_h - 6)
        hp_ratio = max(0, self.boss.hp / self.boss.max_hp)
        fill_mult = self._intro_hp_bar_fill if self.intro_phase else 1.0
        self._boss_hp_display += (self.boss.hp - self._boss_hp_display) * 0.08
        display_ratio = max(0, self._boss_hp_display / self.boss.max_hp) * fill_mult
        phantom_ratio = min(1.0, max(0, (self._boss_hp_display + self._boss_phantom_dmg) / self.boss.max_hp))
        self._boss_hp_bar_glow += 1
        glow_pulse = 0.6 + 0.4 * abs(math.sin(self._boss_hp_bar_glow * 0.04))
        bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(bar, (10, 8, 18, 240), (0, 0, bar_w, bar_h), border_radius=9)
        if hp_ratio < 0.25:
            hp_color = (240, 30, 20)
            glow_color = (255, 80, 50)
        elif hp_ratio < 0.50:
            hp_color = (240, 140, 25)
            glow_color = (255, 180, 60)
        else:
            hp_color = (200, 50, 40)
            glow_color = (255, 100, 70)
        fill_w = max(4, int(bar_w * display_ratio))
        phantom_fill = max(fill_w + 1, int(bar_w * phantom_ratio))
        if self._boss_phantom_dmg > 1:
            phantom_color = (255, 220, 60)
            pygame.draw.rect(bar, phantom_color, (0, 0, min(phantom_fill, bar_w), bar_h), border_radius=9)
        for i in range(3):
            off = i * 2
            alpha = int(60 * glow_pulse) if i == 0 else int(30 * glow_pulse)
            gp = pygame.Surface((fill_w + 8, bar_h + 4), pygame.SRCALPHA)
            gp.fill((*glow_color, alpha))
            bar.blit(gp, (-4 + off, -2 + off))
        pygame.draw.rect(bar, hp_color, (0, 0, fill_w, bar_h), border_radius=9)
        if fill_w > 20:
            shine = pygame.Surface((fill_w, bar_h // 3), pygame.SRCALPHA)
            shine.fill((255, 255, 255, int(25 * glow_pulse)))
            bar.blit(shine, (0, 2))
        pygame.draw.rect(bar, (180, 180, 200, 200), (0, 0, bar_w, bar_h), width=3, border_radius=9)

        try:
            from config import get_font
            name_font = get_font(20)
        except Exception:
            name_font = pygame.font.Font(None, 20)

        hp_text = f"HP: {int(self._boss_hp_display)} / {self.boss.max_hp}"
        hp_surf = name_font.render(hp_text, True, (255, 255, 255))
        bar.blit(hp_surf, hp_surf.get_rect(midleft=(12, bar_h // 2)))
        self.screen.blit(bar, (bx, by))

        from i18n import t
        boss_name = t(self.boss.__class__.__name__.lower())
        if boss_name == self.boss.__class__.__name__.lower():
            boss_name = self.boss.__class__.__name__
        nm = name_font.render(boss_name, True, (255, 215, 0))
        self.screen.blit(nm, nm.get_rect(midleft=(bx + 8, by - 14)))

    def _boss_challenger_collision(self, boss, other):
        dx = other.rect.centerx - boss.rect.centerx
        dy = other.rect.centery - boss.rect.centery
        dist = math.hypot(dx, dy)
        boss_r = boss.rect.width * 0.42
        other_r = other.rect.width * 0.42
        min_dist = boss_r + other_r + 2
        if dist < min_dist and dist > 0:
            overlap = min_dist - dist + 1
            nx, ny = dx / dist, dy / dist
            other.rect.x += int(nx * overlap)
            other.rect.y += int(ny * overlap)
            other.rect.left = max(0, other.rect.left)
            other.rect.right = min(self.width, other.rect.right)
            other.rect.top = max(0, other.rect.top)
            other.rect.bottom = min(self.height, other.rect.bottom)
            other.vx += nx * 0.20
            other.vy += ny * 0.20
        boss.rect.left = max(0, boss.rect.left)
        boss.rect.right = min(self.width, boss.rect.right)
        boss.rect.top = max(0, boss.rect.top)
        boss.rect.bottom = min(self.height, boss.rect.bottom)

    def _challenger_collision(self, a, b):
        dx = a.rect.centerx - b.rect.centerx
        dy = a.rect.centery - b.rect.centery
        dist = math.hypot(dx, dy)
        min_dist = (a.size + b.size) / 2 + 6
        if dist < min_dist and dist > 0:
            overlap = (min_dist - dist) / 2 + 1
            nx, ny = dx / dist, dy / dist
            a.rect.x += int(nx * overlap)
            a.rect.y += int(ny * overlap)
            b.rect.x -= int(nx * overlap)
            b.rect.y -= int(ny * overlap)
        for e in (a, b):
            e.rect.left = max(0, e.rect.left)
            e.rect.right = min(self.width, e.rect.right)
            e.rect.top = max(0, e.rect.top)
            e.rect.bottom = min(self.height, e.rect.bottom)

    def _closest_rect(self, me):
        if me is self.boss:
            best, best_d = None, 9999
            for f in self.manager.fighters:
                if f is not me and f.hp > 0:
                    d = math.hypot(f.rect.centerx - me.rect.centerx, f.rect.centery - me.rect.centery)
                    if d < best_d:
                        best_d, best = d, f
            return best.rect if best else None
        if self.boss and self.boss.hp > 0:
            return self.boss.rect
        return None

    def _apply_boss_attack_result(self, res, boss):
        aoe = res.get("aoe_hits")
        if aoe:
            kb_vec = res.get("knockback")
            for hit in aoe:
                target = hit.get("target")
                if not target or target not in self.manager.fighters or target.hp <= 0:
                    continue
                dmg = hit.get("damage", 25)
                self._damage_fighter(target, dmg, boss)
                if kb_vec:
                    kb = getattr(target, 'kb_res', 0)
                    target.vx += kb_vec[0] * (1.0 - kb)
                    target.vy += kb_vec[1] * (1.0 - kb)
            return

        target = res.get("target")
        if not target or target not in self.manager.fighters or target.hp <= 0:
            return
        dmg = res.get("damage", 25)
        extra_hits = res.get("extra_hits", 0)
        self._damage_fighter(target, dmg, boss)
        for _ in range(extra_hits):
            nearby = [f for f in self.manager.fighters
                      if f is not target and f is not boss and f.hp > 0
                      and math.hypot(f.rect.centerx - target.rect.centerx, f.rect.centery - target.rect.centery) < 180]
            if nearby:
                extra_target = random.choice(nearby)
                self._damage_fighter(extra_target, max(1, int(dmg * 0.6)), boss)
        kb_vec = res.get("knockback")
        if kb_vec:
            kb = getattr(target, 'kb_res', 0)
            target.vx += kb_vec[0] * (1.0 - kb)
            target.vy += kb_vec[1] * (1.0 - kb)

    def _damage_fighter(self, target, dmg, attacker):
        try:
            target.take_damage(dmg, attacker=attacker)
        except TypeError:
            target.take_damage(dmg)

    def _update_drowned_king_tridents(self):
        if not hasattr(self, "trident_list"):
            return
        mgr = self.manager
        self.trident_list[:] = [t for t in self.trident_list if getattr(t, "active", False)]
        mgr.drowned_king_tridents = self.trident_list
        for trident in self.trident_list[:]:
            try:
                hits = trident.update(self.width, self.height, mgr.map_mgr.blocks, mgr.fighters)
            except TypeError:
                hits = trident.update(self.width, self.height, mgr.map_mgr.blocks)
            for hit in hits or []:
                self._apply_trident_hit(hit, trident)
            if hasattr(trident, "is_dead") and trident.is_dead():
                if trident in self.trident_list:
                    self.trident_list.remove(trident)

    def _apply_trident_hit(self, hit, trident):
        target = hit.get("target")
        if not target or target not in self.manager.fighters or target.hp <= 0:
            return
        shooter = getattr(trident, "shooter", self.boss)
        if target is shooter:
            return
        dmg = hit.get("damage", getattr(trident, "damage", 0))
        if hit.get("water_prison"):
            self._ensure_water_prison(target, hit.get("water_prison_vfx"))
        if dmg <= 0:
            return
        self._damage_fighter(target, dmg, shooter)

    def _resolve_drowned_king_flags(self, boss):
        if getattr(boss, "_recall_flag", False):
            active = [t for t in self.trident_list if getattr(t, "active", False)]
            self._spawn_recall_particles(active, boss)
            for trident in active:
                trident.destroy()
            self.trident_list[:] = []
            self.manager.drowned_king_tridents = self.trident_list
            heal = len(active) * getattr(boss, "_recall_heal_per", 15)
            if heal > 0 and boss.hp > 0:
                before = boss.hp
                boss.hp = min(boss.max_hp, boss.hp + heal)
                if boss.hp > before:
                    from entity import FloatText
                    boss.float_texts.append(FloatText(boss.rect.centerx, boss.rect.top - 30, f"+{int(boss.hp - before)}", (80, 255, 160)))
            boss._recall_flag = False
            boss._thunder_charge_flag = False
            boss._ultimate_flag = False
            self._apply_screen_shake(10, 18)
            return

        if getattr(boss, "_thunder_charge_flag", False):
            data = getattr(boss, "_thunder_charge_data", None) or {}
            radius = data.get("pulse_radius", 80)
            damage = data.get("pulse_damage", 8)
            duration = data.get("duration", 300)
            for trident in self.trident_list:
                if getattr(trident, "state", None) == "pinned":
                    if trident.electrify(duration=duration, pulse_radius=radius, pulse_damage=damage):
                        if hasattr(boss, "add_lightning_burst"):
                            boss.add_lightning_burst(trident.x, trident.y, radius)
            self._apply_screen_shake(14, 22)
            boss._thunder_charge_flag = False

        if getattr(boss, "_ultimate_flag", False):
            active = [t for t in self.trident_list if getattr(t, "active", False)]
            data = getattr(boss, "_ultimate_data", None) or {}
            self._start_ripple_detonation(active, boss, data)
            boss._ultimate_flag = False

    def _apply_boss_result(self, res, attacker):
        target = res.get("target")
        extra_hits = res.get("extra_hits", 0)
        if target and target in self.manager.fighters and target.hp > 0:
            dmg = res.get("damage", 10)
            is_crit = False
            if attacker and attacker is not self.boss and attacker.hp > 0:
                dmg += attacker.get_buff_value("atk_up")
                amp = attacker.get_buff_value("dmg_amp")
                dmg += amp
                crit = attacker.get_buff_value("crit_up")
                if crit > 0 and random.random() < 0.25:
                    dmg = int(dmg * 1.8)
                    is_crit = True
                    from entity import FloatText
                    attacker.float_texts.append(FloatText(
                        attacker.rect.centerx + random.randint(-15, 15),
                        attacker.rect.top - 35, "会心!", (255, 215, 0)))
            total_dmg = dmg
            for _ in range(extra_hits):
                total_dmg += max(1, int(dmg * 0.6))
            try:
                target.take_damage(total_dmg, attacker=attacker)
            except TypeError:
                target.take_damage(total_dmg)
            if attacker and attacker.hp > 0 and getattr(attacker, '_boss_mode', False):
                cls = attacker.__class__.__name__
                if cls == "Skeleton":
                    from entity import FloatText
                    heal = max(1, int(total_dmg * 0.12))
                    attacker.hp = min(attacker.max_hp if hasattr(attacker, 'max_hp') else attacker.hp, attacker.hp + heal)
                    attacker.float_texts.append(FloatText(attacker.rect.centerx, attacker.rect.top - 30, f"+{heal}", (100, 255, 100)))
            if target is self.boss:
                self._boss_phantom_dmg = min(self._boss_phantom_dmg + total_dmg, self.boss.max_hp * 2)
                from entity import FloatText
                ox = target.rect.centerx + random.randint(-30, 30)
                oy = target.rect.top - 15 - random.randint(0, 40)
                if is_crit:
                    target.float_texts.append(FloatText(ox, oy, f"-{total_dmg}!", (255, 20, 0)))
                    target.float_texts.append(FloatText(ox + 2, oy - 2, f"-{total_dmg}!", (255, 60, 20)))
                    target.float_texts.append(FloatText(ox - 1, oy - 1, f"-{total_dmg}!", (255, 200, 40)))
                else:
                    target.float_texts.append(FloatText(ox, oy, f"-{total_dmg}", (255, 255, 255)))
                if attacker and attacker is not self.boss and attacker.hp > 0:
                    self._do_lifesteal(attacker, total_dmg)
            kb = getattr(target, 'kb_res', 0)
            target.vx += (target.rect.centerx - attacker.rect.centerx) * 0.1 * (1.0 - kb)
            target.vy += (target.rect.centery - attacker.rect.centery) * 0.1 * (1.0 - kb)

    def _creeper_boom(self, data, src):
        if not data:
            return
        ex_x = data.get("x", src.rect.centerx)
        ex_y = data.get("y", src.rect.centery)
        ex_radius = data.get("radius", 160)
        ex_mult = data.get("mult", 1)
        for f in self.manager.fighters:
            if f is src:
                continue
            is_boss_explosion = (src is self.boss)
            if is_boss_explosion and f is self.boss:
                continue
            if not is_boss_explosion and f is not self.boss:
                continue
            d = math.hypot(f.rect.centerx - ex_x, f.rect.centery - ex_y)
            if d < ex_radius:
                dmg = data.get("damage", 20 * ex_mult)
                try:
                    f.take_damage(dmg, attacker=src)
                except TypeError:
                    f.take_damage(dmg)
                if f is self.boss:
                    self._boss_phantom_dmg = min(self._boss_phantom_dmg + dmg, self.boss.max_hp * 2)
                    from entity import FloatText
                    f.float_texts.append(FloatText(f.rect.centerx + random.randint(-20, 20), f.rect.top - 20, f"-{dmg}", (255, 100, 50)))
                    if src and src is not self.boss and src.hp > 0:
                        self._do_lifesteal(src, dmg)
                kb = getattr(f, 'kb_res', 0)
                force = dmg * (1.0 - kb)
                dx = f.rect.centerx - ex_x
                dy = f.rect.centery - ex_y
                dist = max(1, math.hypot(dx, dy))
                f.vx += (dx / dist) * force * 0.5
                f.vy += (dy / dist) * force * 0.5
