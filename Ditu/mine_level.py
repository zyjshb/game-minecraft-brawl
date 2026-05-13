# Ditu/mine_level.py
import pygame
import os
import sys

# 引入场务管家
from.manager import LevelManager 

class BattleLevel:
    def __init__(self, screen, bg_path, selected_chars=None, target_size=(1024, 1024)):
        self.screen = screen
        self.width, self.height = target_size
        
        screen_w, screen_h = screen.get_size()
        self.offset_x = max(0, (screen_w - self.width) // 2)
        self.offset_y = max(0, (screen_h - self.height) // 2)

        self.bg_img = self._create_acrylic_bg(bg_path)
        
        try:
            from config import get_font
            self.font = get_font(40)
        except:
            self.font = pygame.font.Font(None, 40)
            
        # ==========================================
        # 🌟 UI 加载区：全屏大背景图
        # ==========================================
        ui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Scenes", "UI")
        self.global_bg = None
        try:
            raw_global_bg = pygame.image.load(os.path.join(ui_dir, "战斗背景图.png")).convert()
            self.global_bg = pygame.transform.scale(raw_global_bg, (screen_w, screen_h))
            overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            # ✅ 修正：补齐括号
            overlay.fill((0, 0, 0, 100))
            self.global_bg.blit(overlay, (0, 0))
        except Exception as e:
            print(f"[WARN] 全局大背景加载失败: {e}")
        
        # 🌟 核心交接：叫场务进场接管物理和逻辑
        self.manager = LevelManager(self.width, self.height, selected_chars, map_path=bg_path)
        
        # 🌟 修改点 1：出生即战斗，不再等待空格
        self.game_started = True
        self._panel_announce_text = None
        self._panel_announce_timer = 0
        self._panel_announce_alpha = 0

    @property
    def fighters(self):
        """桥梁属性，确保 main.py 依然能找到演员名单"""
        return self.manager.fighters

    @property
    def time_up(self):
        return self.manager.weather.game_over

    def _create_acrylic_bg(self, path):
        try:
            raw = pygame.image.load(path).convert()
            raw_w, raw_h = raw.get_width(), raw.get_height()
            if raw_w > 0 and raw_h > 0 and (raw_w != self.width or raw_h != self.height):
                scale = max(self.width / raw_w, self.height / raw_h)
                new_w = int(raw_w * scale)
                new_h = int(raw_h * scale)
                scaled = pygame.transform.smoothscale(raw, (new_w, new_h))
                crop_x = (new_w - self.width) // 2
                crop_y = (new_h - self.height) // 2
                cropped = scaled.subsurface(pygame.Rect(crop_x, crop_y, self.width, self.height))
                small = pygame.transform.smoothscale(cropped, (self.width // 15, self.height // 15))
                blurred = pygame.transform.smoothscale(small, (self.width, self.height))
            else:
                small = pygame.transform.smoothscale(raw, (self.width // 15, self.height // 15))
                blurred = pygame.transform.smoothscale(small, (self.width, self.height))
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            # ✅ 修正：补齐括号
            overlay.fill((255, 255, 255, 40)) 
            blurred.blit(overlay, (0, 0))
            return blurred
        except: return None

    def handle_event(self, event):
        """目前已实现即时开始，此处可留空"""
        pass

    def draw(self):
        # 1. 准备虚拟画布（竞技场内部）
        game_surf = pygame.Surface((self.width, self.height))
        
        # ✅ 修正：所有 fill 均已加双括号
        if self.bg_img: 
            game_surf.blit(self.bg_img, (0, 0))
        else: 
            game_surf.fill((30, 30, 30))
        
        # 2. 叫场务把所有实体画到虚拟画布上
        self.manager.draw_all(game_surf)

        # 3. 最终组装渲染
        # 第一层：底层全屏背景
        if self.global_bg:
            self.screen.blit(self.global_bg, (0, 0))
        else:
            self.screen.fill((10, 10, 10)) 
        
        # 第二层：中间竞技场
        self.screen.blit(game_surf, (self.offset_x, self.offset_y))

        # 第三层：季节动态边框
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

        # 对话框画在边框之上，不被遮挡，offset 让坐标对齐屏幕
        self.manager.weather.speech_bubble.draw(self.screen, self.offset_x, self.offset_y)

        # 第四层：战斗框左侧 - 太阳/月亮 + 天气图标
        self._draw_left_panel()

    def _draw_left_panel(self):
        weather = self.manager.weather
        if not weather:
            return
        if weather._always_dark:
            return
        if not weather.enabled:
            return

        from Ditu.weather.season import SEASON_COLORS, get_season_char

        gap = 20
        panel_w = 140
        px = self.offset_x - gap

        if px - panel_w < 5:
            return

        py = self.offset_y + 20
        panel_top_h = 146
        panel_bot_h = 96
        panel_h = panel_top_h + panel_bot_h

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

        bg_color_1 = (18, 20, 38)
        bg_color_2 = (28, 30, 48)
        for row in range(panel_h):
            ratio = row / panel_h
            r = int(bg_color_1[0] + (bg_color_2[0] - bg_color_1[0]) * ratio)
            g = int(bg_color_1[1] + (bg_color_2[1] - bg_color_1[1]) * ratio)
            b = int(bg_color_1[2] + (bg_color_2[2] - bg_color_1[2]) * ratio)
            pygame.draw.line(panel, (r, g, b, 220), (0, row), (panel_w, row))

        inner_margin = 4
        pygame.draw.rect(panel, (180, 160, 80, 160), (0, 0, panel_w, panel_h), width=2, border_radius=16)
        pygame.draw.rect(panel, (220, 200, 100, 60), (inner_margin, inner_margin, panel_w - inner_margin * 2, panel_h - inner_margin * 2), width=1, border_radius=14)
        pygame.draw.rect(panel, (180, 160, 80, 60), (inner_margin + 5, inner_margin + 5, panel_w - (inner_margin + 5) * 2, panel_h - (inner_margin + 5) * 2), width=1, border_radius=11)

        season_key = weather.current_season
        season_color = SEASON_COLORS.get(season_key, (180, 180, 180))
        season_char = get_season_char(season_key)
        season_h = 22
        for row in range(season_h):
            a = int(80 * (1.0 - row / season_h * 0.5))
            sr, sg, sb = int(season_color[0] * 0.2), int(season_color[1] * 0.2), int(season_color[2] * 0.2)
            pygame.draw.line(panel, (sr, sg, sb, a), (inner_margin + 2, inner_margin + 2 + row), (panel_w - inner_margin - 2, inner_margin + 2 + row))
        if not hasattr(self, '_season_font'):
            try:
                from config import get_font
                self._season_font = get_font(16)
            except:
                self._season_font = pygame.font.Font(None, 16)
        stxt = self._season_font.render(season_char, True, season_color)
        sr = stxt.get_rect(center=(panel_w // 2, inner_margin + 2 + season_h // 2))
        panel.blit(stxt, sr)

        sun_offset = inner_margin + 2 + season_h + 4
        sun_cx = panel_w // 2
        sun_cy = sun_offset + 34

        sep_y = sun_offset + 96
        pygame.draw.line(panel, (140, 130, 80, 160), (12, sep_y), (panel_w - 12, sep_y), 2)
        for i in range(3):
            dot_x = panel_w // 2 - 12 + i * 12
            pygame.draw.circle(panel, (200, 180, 100, 200), (dot_x, sep_y), 3)

        wea = weather
        t = wea.get_time_of_day()
        is_night = wea.is_night()

        import math
        rotation_angle = (wea._global_time_frame * 1.5) % 360

        if not is_night:
            sun_layer = pygame.Surface((56, 56), pygame.SRCALPHA)
            scx = scy = 28
            for i in range(8):
                angle_rad = math.radians(rotation_angle + i * 45)
                tip_x = scx + math.cos(angle_rad) * 19
                tip_y = scy + math.sin(angle_rad) * 19
                mid_x = scx + math.cos(angle_rad) * 14
                mid_y = scy + math.sin(angle_rad) * 14
                pygame.draw.line(sun_layer, (255, 230, 110, 200), (mid_x, mid_y), (tip_x, tip_y), 3)
            pygame.draw.circle(sun_layer, (255, 240, 110), (scx, scy), 16)
            pygame.draw.circle(sun_layer, (255, 250, 180), (scx, scy), 11)
            pygame.draw.circle(sun_layer, (255, 255, 230), (scx, scy), 7)
            panel.blit(sun_layer, (sun_cx - 28, sun_cy - 28))
        else:
            moon_layer = pygame.Surface((56, 56), pygame.SRCALPHA)
            mcx = mcy = 28
            pygame.draw.circle(moon_layer, (210, 215, 235), (mcx, mcy), 18)
            pygame.draw.circle(moon_layer, (230, 235, 245), (mcx, mcy), 12)
            crescent_mask = pygame.Surface((26, 26), pygame.SRCALPHA)
            pygame.draw.circle(crescent_mask, (15, 20, 45, 200), (8, 7), 14)
            moon_layer.blit(crescent_mask, (mcx - 13, mcy - 13))
            for i in range(4):
                angle_rad = math.radians(rotation_angle + i * 90)
                star_x = mcx + math.cos(angle_rad) * 22
                star_y = mcy + math.sin(angle_rad) * 22
                alpha = 120 + int(80 * abs(math.sin(rotation_angle * 0.1 + i)))
                pygame.draw.circle(moon_layer, (255, 255, 255, alpha), (int(star_x), int(star_y)), 2)
            panel.blit(moon_layer, (sun_cx - 28, sun_cy - 28))

        wea._draw_time_label_ext(panel, t, sun_cx, sun_cy + 38)

        from Ditu.weather.ui import draw_weather_icon

        wx = panel_w // 2
        wy = sep_y + 32
        draw_weather_icon(panel, wea, wx, wy, big=True)

        if not hasattr(self, '_panel_label_font'):
            try:
                from config import get_font
                self._panel_label_font = get_font(18)
            except:
                self._panel_label_font = pygame.font.Font(None, 18)
        from Ditu.weather.constants import WeatherType
        from i18n import t
        wmap = {
            WeatherType.SUNNY: "weather_sunny", WeatherType.CLOUDY: "weather_cloudy",
            WeatherType.OVERCAST: "weather_overcast", WeatherType.LIGHT_RAIN: "weather_light_rain",
            WeatherType.MODERATE_RAIN: "weather_moderate_rain", WeatherType.HEAVY_RAIN: "weather_heavy_rain",
            WeatherType.THUNDERSTORM: "weather_thunderstorm", WeatherType.LIGHT_SNOW: "weather_light_snow",
            WeatherType.MODERATE_SNOW: "weather_moderate_snow", WeatherType.HEAVY_SNOW: "weather_heavy_snow",
            WeatherType.FOG: "weather_fog", WeatherType.SANDSTORM: "weather_sandstorm",
        }
        wt_name = t(wmap.get(wea.current_weather, ""))
        if wt_name:
            nm = self._panel_label_font.render(wt_name, True, (255, 240, 180))
            nr = nm.get_rect(center=(panel_w // 2, wy + 32))
            shadow = self._panel_label_font.render(wt_name, True, (0, 0, 0))
            panel.blit(shadow, (nr.x + 1, nr.y + 1))
            panel.blit(nm, nr)

        self.screen.blit(panel, (px - panel_w, py))
        self._draw_panel_announcement(px - panel_w, py + panel_h + 10, panel_w)

    def update(self):
        if self.game_started:
            self.manager.update()
        self._check_panel_announcement()
        self._update_panel_announcement()

    def _check_panel_announcement(self):
        text = self.manager.weather.pending_panel_text
        if text:
            self.manager.weather.pending_panel_text = None
            self._panel_announce_text = text
            self._panel_announce_timer = 180
            self._panel_announce_alpha = 0

    def _update_panel_announcement(self):
        if self._panel_announce_timer > 0:
            self._panel_announce_timer -= 1
            if not hasattr(self, '_announce_frame'):
                self._announce_frame = 0
            self._announce_frame += 1
            if self._panel_announce_timer > 155:
                self._panel_announce_alpha = min(255, self._panel_announce_alpha + 20)
            elif self._panel_announce_timer > 20:
                self._panel_announce_alpha = 255
            else:
                self._panel_announce_alpha = max(0, self._panel_announce_alpha - 15)
        else:
            self._panel_announce_text = None
            self._panel_announce_alpha = 0

    def _draw_panel_announcement(self, ax, ay, panel_w):
        if not self._panel_announce_text or self._panel_announce_alpha <= 0:
            return
        if not hasattr(self, '_announce_font'):
            try:
                from config import get_font
                self._announce_font = get_font(18)
            except:
                self._announce_font = pygame.font.Font(None, 18)

        import math
        text = self._panel_announce_text
        alpha = self._panel_announce_alpha
        pulse = int(math.sin(getattr(self, '_announce_frame', 0) * 0.08) * 30 + 30)

        txt_surf = self._announce_font.render(text, True, (255, 255, 230))
        tw = txt_surf.get_width()
        th = txt_surf.get_height()
        pad = 16
        bw = max(tw + pad * 2, panel_w + 12)
        bh = th + pad * 2 + 6

        bubble = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        glow_alpha = min(80, pulse)
        pygame.draw.rect(bubble, (255, 215, 80, glow_alpha), (2, 2, bw + 4, bh + 4), border_radius=14)
        pygame.draw.rect(bubble, (255, 215, 80, glow_alpha // 2), (0, 0, bw + 8, bh + 8), border_radius=16)

        inner = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(inner, (8, 10, 28, min(230, alpha + 30)), (0, 0, bw, bh), border_radius=10)
        pygame.draw.rect(inner, (255, 215, 100, min(alpha + pulse, 255)), (0, 0, bw, bh), width=2, border_radius=10)
        txt_surf.set_alpha(alpha)
        tx = (bw - tw) // 2
        ty = (bh - th) // 2
        shadow = self._announce_font.render(text, True, (5, 5, 15))
        shadow.set_alpha(int(alpha * 0.5))
        inner.blit(shadow, (tx + 2, ty + 2))
        inner.blit(txt_surf, (tx, ty))
        inner.set_alpha(alpha)
        bubble.blit(inner, (4, 4))
        bubble.set_alpha(alpha)
        bx = ax + (panel_w - bw) // 2 - 4
        self.screen.blit(bubble, (bx, ay - 4))
