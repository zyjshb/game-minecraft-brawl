import math
import os
import random
import sys

import pygame

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from i18n import t as _t

from .constants import (
    DESERT_FORBIDDEN,
    SEASON_NAMES,
    SEASON_WEATHER_POOLS,
    TIME_SKY_COLORS,
    WEATHER_CONFIGS,
    WeatherType,
)
from .dialog import WEATHER_BUBBLE_TEXT, WEATHER_SAME_LINES
from .particles import CloudOverlay, RainParticle, SandParticle, SnowParticle, Torch
from .resources import get_weather_sfx_dir
from .season import SeasonEffect
from .sky import draw_celestial, draw_celestial_compact
from .speech import SpeechBubble
from .ui import WeatherAlertBanner


class WeatherSystem:
    GAME_DURATION_SEC = 240
    WEATHER_TIMER_RANGE = (600, 1200)
    NIGHT_START = 0.78
    NIGHT_END = 0.22
    TORCH_SPAWN_PADDING = 100
    TORCH_MIN_DISTANCE = 250
    TORCH_MAX_ATTEMPTS = 30
    _global_time_frame = 5400
    _global_season_index = 0

    def __init__(
        self,
        width,
        height,
        map_path="",
        is_desert=False,
        weather_configs=None,
        season_weather_pools=None,
    ):
        self.width = width
        self.height = height
        self._weather_configs = weather_configs or WEATHER_CONFIGS
        self._season_weather_pools = season_weather_pools or SEASON_WEATHER_POOLS

        is_cave = map_path and "洞穴" in map_path
        self._always_dark = is_cave
        self.enabled = True
        self.is_desert = is_desert

        if is_cave:
            self.current_weather = WeatherType.SUNNY
            self.target_weather = WeatherType.SUNNY
            self.transition_progress = 1.0
            self.time_remaining = self.GAME_DURATION_SEC
            self.game_over = False
            self.torches = []
            self.forbidden_rects = []
            self.rain_sound = None
            self.thunder_sound = None
            self.sandstorm_sound = None
            self.snow_sound = None
            self.current_config = dict(self._weather_configs[WeatherType.SUNNY])
            self.target_config = dict(self._weather_configs[WeatherType.SUNNY])
            self.frame_count = 0
            self.total_frames = self.GAME_DURATION_SEC * 60
            self.night_notified = False
            self.day_notified = False
            self._darkness_smooth = 180.0
            self.alert_banner = WeatherAlertBanner(width)
            self._pending_initial_alert = 0
            self.weather_timer = 0
            self.weather_timer_max = 1200
            self.season_effect = SeasonEffect(width, height)
            self.speech_bubble = SpeechBubble()
            self.pending_bubble_text = None
            self.pending_panel_text = None
            seasons = ["spring", "summer", "autumn", "winter"]
            self.current_season = seasons[int((WeatherSystem._global_season_index / 3600)) % 4]
            self.season_timer = WeatherSystem._global_season_index
            return

        self.sfx_dir = get_weather_sfx_dir()

        self.frame_count = 0
        self.total_frames = self.GAME_DURATION_SEC * 60
        self.time_remaining = self.GAME_DURATION_SEC
        self.game_over = False

        seasons = ["spring", "summer", "autumn", "winter"]
        self.current_season = seasons[int((WeatherSystem._global_season_index / 3600)) % 4]
        self.season_timer = WeatherSystem._global_season_index

        self.current_weather = WeatherType.SUNNY
        self.target_weather = WeatherType.SUNNY
        self.transition_progress = 1.0
        self.transition_speed = 0.006
        self.weather_timer = 0
        self.weather_timer_max = 1200

        self.current_config = dict(self._weather_configs[WeatherType.SUNNY])
        self.target_config = dict(self._weather_configs[WeatherType.SUNNY])

        self.rain_particles = []
        self.snow_particles = []
        self.sand_dust = []

        self.cloud_overlay = CloudOverlay(width, height)

        self.flash_alpha = 0
        self.flash_timer = 0
        self.thunder_delay = 0
        self.thunder_cooldown = 0

        self.alert_banner = WeatherAlertBanner(width)

        self.rain_sound = None
        self.thunder_sound = None
        self.sandstorm_sound = None
        self.snow_sound = None
        self._load_audio()

        self.rain_vol = 0.0
        self.sand_vol = 0.0
        self.snow_vol = 0.0
        self.target_rain_vol = 0.0
        self.target_sand_vol = 0.0
        self.target_snow_vol = 0.0

        self._pending_initial_alert = 0
        self.torches = []
        self.was_night = False
        self.night_notified = False
        self.day_notified = False
        self.forbidden_rects = []
        self._darkness_smooth = 0.0
        self._schedule_initial_weather()
        self.season_effect = SeasonEffect(width, height)
        self.speech_bubble = SpeechBubble()
        self.pending_bubble_text = None
        self.pending_panel_text = None

    @staticmethod
    def _lerp(a, b, t):
        t = max(0, min(1, t))
        return a + (b - a) * t

    def _schedule_initial_weather(self):
        pool = self._build_weather_pool(self.current_season)
        initial = random.choice(pool)
        self.current_config = dict(self._weather_configs[initial])
        self.target_config = dict(self._weather_configs[initial])
        self.current_weather = initial
        self.target_weather = initial
        self.transition_progress = 1.0
        self._update_audio_targets()
        self.weather_timer = random.randint(*self.WEATHER_TIMER_RANGE)
        self.weather_timer_max = self.weather_timer
        self._pending_initial_alert = 90

    def _build_weather_pool(self, season, include_desert_boost=False):
        pool = self._season_weather_pools.get(season, [WeatherType.SUNNY])
        if self.is_desert:
            pool = [w for w in pool if w not in DESERT_FORBIDDEN]
            if include_desert_boost and season != "winter":
                pool = pool + [WeatherType.SANDSTORM] * 3
        else:
            pool = [w for w in pool if w != WeatherType.SANDSTORM]
        return pool or [WeatherType.SUNNY]

    def _load_audio(self):
        try:
            path = os.path.join(self.sfx_dir, "The sound of rain", "暴雨声.mp3")
            if os.path.exists(path):
                self.rain_sound = pygame.mixer.Sound(path)
                self.rain_sound.set_volume(0)
                self.rain_sound.play(loops=-1)
        except Exception:
            self.rain_sound = None

        try:
            path = os.path.join(self.sfx_dir, "Lightning", "闪电打雷声.mp3")
            if os.path.exists(path):
                self.thunder_sound = pygame.mixer.Sound(path)
                self.thunder_sound.set_volume(0.45)
        except Exception:
            self.thunder_sound = None

        try:
            path = os.path.join(self.sfx_dir, "Sandstorm", "沙尘暴.mp3")
            if os.path.exists(path):
                self.sandstorm_sound = pygame.mixer.Sound(path)
                self.sandstorm_sound.set_volume(0)
                self.sandstorm_sound.play(loops=-1)
        except Exception:
            self.sandstorm_sound = None

        try:
            path = os.path.join(self.sfx_dir, "snowflake", "雪花.mp3")
            if os.path.exists(path):
                self.snow_sound = pygame.mixer.Sound(path)
                self.snow_sound.set_volume(0)
                self.snow_sound.play(loops=-1)
        except Exception:
            self.snow_sound = None

    def _update_audio_targets(self):
        w = self.target_weather
        if w == WeatherType.LIGHT_RAIN:
            self.target_rain_vol = 0.15
        elif w == WeatherType.MODERATE_RAIN:
            self.target_rain_vol = 0.30
        elif w in (WeatherType.HEAVY_RAIN, WeatherType.THUNDERSTORM):
            self.target_rain_vol = 0.45
        else:
            self.target_rain_vol = 0.0

        self.target_sand_vol = 0.35 if w == WeatherType.SANDSTORM else 0.0

        if w == WeatherType.LIGHT_SNOW:
            self.target_snow_vol = 0.08
        elif w == WeatherType.MODERATE_SNOW:
            self.target_snow_vol = 0.18
        elif w == WeatherType.HEAVY_SNOW:
            self.target_snow_vol = 0.28
        else:
            self.target_snow_vol = 0.0

    def _smooth_audio(self):
        spd = 0.01
        for attr, tgt in [
            ("rain_vol", "target_rain_vol"),
            ("sand_vol", "target_sand_vol"),
            ("snow_vol", "target_snow_vol"),
        ]:
            cur = getattr(self, attr)
            t = getattr(self, tgt)
            if abs(cur - t) < spd:
                setattr(self, attr, t)
            elif cur < t:
                setattr(self, attr, cur + spd)
            else:
                setattr(self, attr, cur - spd)

        if self.rain_sound:
            self.rain_sound.set_volume(self.rain_vol * 0.45)
        if self.sandstorm_sound:
            self.sandstorm_sound.set_volume(self.sand_vol * 0.55)
        if self.snow_sound:
            self.snow_sound.set_volume(self.snow_vol * 0.40)

    def _get_time_of_day(self):
        if self._always_dark:
            return 0.0
        day_cycle = 18000
        return (WeatherSystem._global_time_frame % day_cycle) / day_cycle

    def get_time_of_day(self):
        return self._get_time_of_day()

    def _get_sky_colors(self):
        t = self._get_time_of_day()
        colors = TIME_SKY_COLORS
        n = len(colors)
        idx_f = t * n
        idx = min(int(idx_f), n - 1)
        nxt = (idx + 1) % n
        frac = idx_f - idx
        top_src, bot_src = colors[idx]
        top_dst, bot_dst = colors[nxt]
        top = tuple(int(self._lerp(top_src[i], top_dst[i], frac)) for i in range(3))
        bot = tuple(int(self._lerp(bot_src[i], bot_dst[i], frac)) for i in range(3))
        return top, bot

    def _weather_intensity(self):
        if self.weather_timer_max <= 0:
            return 1.0
        progress = 1.0 - (self.weather_timer / self.weather_timer_max)
        progress = max(0.0, min(1.0, progress))
        return math.sin(progress * math.pi)

    def _sync_particles(self):
        t = self.transition_progress
        intensity = self._weather_intensity()
        target_rain = min(120, int(
            self._lerp(
                self.current_config["rain_density"], self.target_config["rain_density"], t
            )
            * intensity
        ))
        target_snow = min(100, int(
            self._lerp(
                self.current_config["snow_density"], self.target_config["snow_density"], t
            )
            * intensity
        ))
        wind = self._lerp(self.current_config["wind"], self.target_config["wind"], t)
        rain_spd = self._lerp(self.current_config["rain_speed"], self.target_config["rain_speed"], t)
        rain_ang = self._lerp(self.current_config["rain_angle"], self.target_config["rain_angle"], t)
        snow_spd = self._lerp(self.current_config["snow_speed"], self.target_config["snow_speed"], t)
        bw, bh = self.width, self.height

        while len(self.rain_particles) < target_rain:
            self.rain_particles.append(
                RainParticle(random.uniform(-30, bw + 30), random.uniform(-30, bh), rain_spd, rain_ang)
            )
        while len(self.rain_particles) > target_rain:
            self.rain_particles.pop()

        for p in self.rain_particles:
            p.speed = rain_spd
            p.angle = rain_ang
            rad = math.radians(rain_ang)
            p.vx = math.sin(rad) * rain_spd * 0.3
            p.vy = rain_spd
            p.update(bw, bh, wind)

        while len(self.snow_particles) < target_snow:
            self.snow_particles.append(SnowParticle(random.uniform(0, bw), random.uniform(-15, bh), snow_spd))
        while len(self.snow_particles) > target_snow:
            self.snow_particles.pop()

        for p in self.snow_particles:
            p.speed = snow_spd
            p.update(bw, bh, wind)

        sand_target = 25 if self.target_weather == WeatherType.SANDSTORM else 0
        cur = len(self.sand_dust)
        if cur < sand_target:
            for _ in range(sand_target - cur):
                self.sand_dust.append(SandParticle(random.uniform(0, bw), random.uniform(0, bh), wind))
        while len(self.sand_dust) > sand_target:
            self.sand_dust.pop()
        for p in self.sand_dust:
            p.update(bw, bh, wind)

    def set_weather(self, weather_type, silent=False):
        if weather_type not in self._weather_configs:
            weather_type = WeatherType.SUNNY
        if weather_type == self.target_weather:
            return
        self.target_weather = weather_type
        self.target_config = dict(self._weather_configs[weather_type])
        self.transition_progress = 0.0
        self._update_audio_targets()
        if not silent:
            try:
                text = WEATHER_BUBBLE_TEXT[weather_type]
            except Exception:
                text = ""
            self.pending_bubble_text = text
            self.pending_panel_text = text

    def trigger_lightning(self):
        if self.thunder_cooldown > 0:
            return
        if self.flash_timer <= 0:
            self.flash_alpha = 255
            self.flash_timer = random.randint(3, 6)
            self.thunder_cooldown = random.randint(40, 90)
            if self.thunder_sound:
                self.thunder_delay = random.randint(8, 40)

    def _is_night(self, t):
        return t > self.NIGHT_START or t < self.NIGHT_END

    def is_night(self):
        return self._is_night(self._get_time_of_day())

    def draw_celestial_ext(self, surface, cx, cy):
        t = self._get_time_of_day()
        is_night = self._is_night(t)
        draw_celestial(surface, t, is_night, cx, cy, self.current_season)

    def _draw_time_label_ext(self, surface, t, x, y):
        from .sky import _draw_time_label as sky_draw_time_label
        sky_draw_time_label(surface, t, x, y, self.current_season)

    def _try_spawn_torch(self):
        for _ in range(self.TORCH_MAX_ATTEMPTS):
            tx = random.randint(self.TORCH_SPAWN_PADDING, self.width - self.TORCH_SPAWN_PADDING)
            ty = random.randint(self.TORCH_SPAWN_PADDING, self.height - self.TORCH_SPAWN_PADDING)
            test_rect = pygame.Rect(tx, ty, 30, 40)

            too_close = any(
                math.hypot(tx - ot.rect.centerx, ty - ot.rect.centery) < self.TORCH_MIN_DISTANCE
                for ot in self.torches
            )
            if too_close:
                continue
            blocked = any(test_rect.colliderect(fr.inflate(30, 30)) for fr in self.forbidden_rects)
            if blocked:
                continue

            sprite = getattr(self, 'torch_sprite', '火把.png')
            self.torches.append(Torch(tx, ty, sprite_name=sprite))
            return True
        return False

    def _ensure_torches(self):
        active_count = sum(1 for tr in self.torches if tr.active)
        missing = max(0, Torch.MAX_TORCHES - active_count)
        for _ in range(missing):
            self._try_spawn_torch()

    def _apply_torch_darkness(self, surface, darkness_alpha, quadratic=True):
        if darkness_alpha <= 0:
            return
        dark = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark.fill((8, 8, 20, darkness_alpha))
        if any(tr.active for tr in self.torches):
            step = 16
            for y in range(0, self.height, step):
                for x in range(0, self.width, step):
                    best_light = 0.0
                    for tr in self.torches:
                        if tr.active:
                            dx = (x + step // 2) - tr.rect.centerx
                            dy = (y + step // 2) - tr.rect.centery
                            dist = math.hypot(dx, dy)
                            r = tr.light_radius * (0.0 if tr.blocked_timer > 0 else 1.0)
                            if dist < r:
                                fade = 1.0 - (dist / r)
                                if quadratic:
                                    fade = fade * fade
                                if fade > best_light:
                                    best_light = fade
                    if best_light > 0.05:
                        a = int(darkness_alpha * (1.0 - best_light))
                        if a < darkness_alpha:
                            pygame.draw.rect(dark, (8, 8, 20, a), (x, y, step, step))
        surface.blit(dark, (0, 0))

    def update(self):
        if self._always_dark:
            self.frame_count += 1
            if self.frame_count >= self.total_frames:
                self.game_over = True
                return
            self.time_remaining = max(0, self.GAME_DURATION_SEC - self.frame_count / 60.0)
            if not self.night_notified:
                self.pending_bubble_text = _t("cave_torch")
                self.pending_panel_text = _t("cave_torch")
                self.night_notified = True
            self._ensure_torches()
            for tr in self.torches:
                tr.update()
            self.alert_banner.update()

            WeatherSystem._global_season_index += 1
            old_season = self.current_season
            elapsed = WeatherSystem._global_season_index / 60.0
            idx = int(elapsed / 60) % 4
            self.current_season = ["spring", "summer", "autumn", "winter"][idx]
            self.season_timer = WeatherSystem._global_season_index
            if self.current_season != old_season:
                pass  # 四季提示动画已禁用
            self.season_effect.update()
            self.speech_bubble.update()
            return

        if not self.enabled:
            if getattr(self, 'torch_sprite', None):
                self._ensure_torches()
                for tr in self.torches:
                    tr.update()
            return

        WeatherSystem._global_time_frame += 1
        self.frame_count += 1
        if self.frame_count >= self.total_frames:
            self.game_over = True
            return

        self.time_remaining = max(0, self.GAME_DURATION_SEC - self.frame_count / 60.0)

        if self._pending_initial_alert > 0:
            self._pending_initial_alert -= 1
            if self._pending_initial_alert <= 0:
                self.pending_bubble_text = WEATHER_BUBBLE_TEXT.get(self.current_weather, "")

        t = self._get_time_of_day()
        is_night = self._is_night(t)
        if is_night and not self.night_notified:
            self.pending_bubble_text = _t("night_falls")
            self.pending_panel_text = _t("night_falls")
            self.night_notified = True
            self.day_notified = False
        elif not is_night and not self.day_notified:
            self.pending_bubble_text = _t("dawn_breaks")
            self.pending_panel_text = _t("dawn_breaks")
            self.day_notified = True
            self.night_notified = False

        if is_night:
            self._ensure_torches()
        else:
            self.torches.clear()

        for tr in self.torches:
            tr.update()

        old_season = self.current_season
        elapsed = WeatherSystem._global_season_index / 60.0
        idx = int(elapsed / 60) % 4
        self.current_season = ["spring", "summer", "autumn", "winter"][idx]
        WeatherSystem._global_season_index += 1
        self.season_timer = WeatherSystem._global_season_index

        if self.current_season != old_season:
            pass  # 四季提示动画已禁用
            pool = self._build_weather_pool(self.current_season, include_desert_boost=True)
            if self.target_weather not in pool:
                self.set_weather(random.choice(pool), silent=True)

        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + self.transition_speed)
            if self.transition_progress >= 1.0:
                self.current_config = dict(self.target_config)
                self.current_weather = self.target_weather
            else:
                t = self.transition_progress
                for key in self.current_config:
                    if key == "sky_color":
                        continue
                    self.current_config[key] = self._lerp(self.current_config[key], self.target_config[key], t)

        self._sync_particles()

        if self.flash_timer > 0:
            self.flash_timer -= 1
            self.flash_alpha = max(0, self.flash_alpha - 75) if self.flash_timer > 0 else 0

        if self.thunder_cooldown > 0:
            self.thunder_cooldown -= 1

        chance = self.current_config["lightning_chance"]
        if chance > 0 and random.random() < chance:
            self.trigger_lightning()

        if self.thunder_delay > 0:
            self.thunder_delay -= 1
            if self.thunder_delay <= 0 and self.thunder_sound:
                self.thunder_sound.play()

        self.weather_timer -= 1
        if self.weather_timer <= 0 and self.transition_progress >= 1.0:
            if self.is_desert and random.random() < 0.35:
                self.set_weather(WeatherType.SANDSTORM)
            else:
                pool = self._build_weather_pool(self.current_season)
                if self.is_desert:
                    pool = pool + [WeatherType.SANDSTORM] * 2
                self.set_weather(random.choice(pool))
            self.weather_timer = random.randint(*self.WEATHER_TIMER_RANGE)
            self.weather_timer_max = self.weather_timer

        self.alert_banner.update()
        self._smooth_audio()
        self.season_effect.update()
        self.speech_bubble.update()

    def draw_bottom(self, surface):
        if self._always_dark:
            self._apply_torch_darkness(surface, 180, quadratic=True)
            return

        if not self.enabled:
            return

        top_col, bot_col = self._get_sky_colors()
        key = (top_col, bot_col)
        if getattr(self, '_sky_cache_key', None) != key:
            self._sky_cache_key = key
            self._sky_cache = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            steps = 24
            for i in range(steps):
                nr = i / (steps - 1) if steps > 1 else 0
                r = int(self._lerp(top_col[0], bot_col[0], nr))
                g = int(self._lerp(top_col[1], bot_col[1], nr))
                b = int(self._lerp(top_col[2], bot_col[2], nr))
                y0 = int(self.height * i / steps)
                y1 = int(self.height * ((i + 1) / steps))
                if y1 - y0 > 0:
                    pygame.draw.rect(self._sky_cache, (r, g, b, 48), (0, y0, self.width, y1 - y0))
        surface.blit(self._sky_cache, (0, 0))

        cloud_alpha = int(self.current_config["cloud_alpha"])
        self.cloud_overlay.draw(surface, cloud_alpha)

        t = self._get_time_of_day()
        is_night = self._is_night(t)
        target_darkness = 180.0 if is_night else 0.0
        self._darkness_smooth = self._lerp(self._darkness_smooth, target_darkness, 0.03)
        darkness_alpha = int(self._darkness_smooth)
        self._apply_torch_darkness(surface, darkness_alpha, quadratic=True)

    def _draw_celestial(self, surface):
        t = self._get_time_of_day()
        is_night = self._is_night(t)
        cx = self.width - 60
        cy = 60
        draw_celestial_compact(surface, t, is_night, cx, cy)
        self._draw_time_label(surface, t, cx, cy + 36)

    def _draw_time_label(self, surface, t, x, y):
        from .sky import _draw_time_label as sky_draw_time_label
        sky_draw_time_label(surface, t, x, y, self.current_season)

    def draw_top(self, surface):
        if self._always_dark:
            for torch in self.torches:
                torch.draw(surface)
            self.season_effect.draw(surface)
            self.alert_banner.draw(surface)
            return

        if not self.enabled:
            for torch in self.torches:
                torch.draw(surface)
            return

        for torch in self.torches:
            torch.draw(surface)

        for p in self.rain_particles:
            p.draw(surface)
        for p in self.snow_particles:
            p.draw(surface)
        if self.target_config["sand_alpha"] > 0 or self.current_config["sand_alpha"] > 0:
            for p in self.sand_dust:
                p.draw(surface)

        fog_alpha = int(self.current_config["fog_alpha"])
        if fog_alpha > 0:
            fkey = ("fog", fog_alpha)
            if getattr(self, '_fog_cache_key', None) != fkey:
                self._fog_cache_key = fkey
                self._fog_cache = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                self._fog_cache.fill((175, 175, 180, fog_alpha))
            surface.blit(self._fog_cache, (0, 0))

        sand_alpha = int(self.current_config["sand_alpha"])
        if sand_alpha > 0:
            skey = ("sand", sand_alpha)
            if getattr(self, '_sand_cache_key', None) != skey:
                self._sand_cache_key = skey
                self._sand_cache = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                self._sand_cache.fill((190, 150, 85, sand_alpha))
            surface.blit(self._sand_cache, (0, 0))

        if self.flash_alpha > 0:
            fl = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(self.flash_alpha)))
            surface.blit(fl, (0, 0))

        self.season_effect.draw(surface)

        self.alert_banner.draw(surface)

        if self.weather_timer_max > 0:
            bw = int(self.width * 0.55)
            bh = 5
            bx = (self.width - bw) // 2
            by = self.height - 18
            ratio = self.weather_timer / max(1, self.weather_timer_max)
            bg_rect = pygame.Rect(bx, by, bw, bh)
            pygame.draw.rect(surface, (20, 20, 30, 140), bg_rect)
            pygame.draw.rect(surface, (60, 60, 70, 160), bg_rect, 1)
            fill_w = int(bw * ratio)
            if fill_w > 0:
                fill_rect = pygame.Rect(bx, by, fill_w, bh)
                pygame.draw.rect(surface, (180, 160, 80, 180), fill_rect)
                pygame.draw.rect(surface, (200, 180, 100, 200), fill_rect, 1)

    def destroy(self):
        for s in [self.rain_sound, self.sandstorm_sound, self.snow_sound]:
            if s:
                try:
                    s.stop()
                except Exception:
                    pass
        if self.thunder_sound:
            try:
                self.thunder_sound.stop()
            except Exception:
                pass
