# Scenes/char_select.py
import os
import sys

import pygame

import audio_manager
from config import get_font
from i18n import t

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_DIR = os.path.join(BASE_DIR, "SFX")
UI_DIR = os.path.join(BASE_DIR, "Scenes", "UI")


def _draw_bamboo_frame(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool = False,
    taken: bool = False,
    highlight: bool = False,
) -> None:
    bamboo = (120, 170, 85) if not taken else (90, 110, 90)
    bamboo_dark = (70, 110, 55) if not taken else (65, 75, 70)
    stroke = (255, 215, 0) if highlight else (28, 32, 28)

    if active or highlight:
        pygame.draw.rect(surface, (255, 215, 0, 50), rect.inflate(12, 12), border_radius=18)
        pygame.draw.rect(surface, (255, 215, 0, 80), rect.inflate(8, 8), border_radius=16)

    pygame.draw.rect(surface, bamboo_dark, rect.inflate(6, 6), border_radius=16)
    pygame.draw.rect(surface, bamboo, rect.inflate(2, 2), border_radius=14)

    band_h = max(4, rect.h // 14)
    for y in (rect.top + rect.h // 3, rect.top + (rect.h * 2) // 3):
        band = pygame.Rect(rect.left - 3, y - band_h // 2, rect.w + 6, band_h)
        pygame.draw.rect(surface, bamboo_dark, band, border_radius=10)

    pygame.draw.rect(surface, stroke, rect.inflate(8, 8), width=2, border_radius=18)


class CharacterSelect:
    def __init__(self, w: int, h: int, num_players: int = 2, exclude_list: list = None, boss_only: bool = False):
        self.w, self.h = w, h
        self.num_players = num_players
        self.current_turn = 0
        self.exclude_list = exclude_list or []
        self._excluded_ids = set(self.exclude_list)
        self.boss_only = boss_only

        self.selections: list[str | None] = [None] * self.num_players
        if self.exclude_list:
            self.selections[0] = self.exclude_list[0]
        self.temp_highlight: str | None = None
        self.last_click_time = 0
        self.last_clicked_id: str | None = None
        self.double_threshold = 300

        if boss_only:
            self.char_info = [
                {"id": "Drowned", "img": "溺尸王.png", "sfx": "jiang-shi/僵尸的撞击声1.mp3", "boss_path": os.path.join(BASE_DIR, "Boss", "溺尸王", "溺尸王.png")},
            ]
        else:
            self.char_info = [
                {"id": "Zombie", "img": "僵尸.webp", "sfx": "jiang-shi/僵尸的撞击声1.mp3"},
                {"id": "Skeleton", "img": "小白.webp", "sfx": "xiao-bai/小白撞击音效1.mp3"},
                {"id": "Creeper", "img": "苦力怕.webp", "sfx": "ku-li-pa/苦力怕即将爆炸音效.mp3"},
                {"id": "Illusioner", "img": "幻术师.webp", "sfx": "huan-shu-shi/幻术师发动分影法术音效.mp3"},
                {"id": "Enderman", "img": "小黑.webp", "sfx": "xiao-hei/小黑的传送音效1.mp3"},
                {"id": "MaoDie", "img": "耄耋.png", "sfx": "mao-die/耄耋哈气.mp3"},
            ]

        # Industrial layout
        self.icon_size = 82
        self.frame_size = 112
        self.grid_cols = 6
        self.grid_gap = 34

        # Fonts
        self.font = get_font(36)
        self.font_title = get_font(56)
        self.font_sub = get_font(26)

        # Panel image (bamboo frame)
        self.panel_img = None
        try:
            self.panel_img = pygame.image.load(os.path.join(UI_DIR, "选人框.png")).convert_alpha()
        except Exception:
            self.panel_img = None

        # Load characters
        self.chars: list[dict] = []
        for info in self.char_info:
            try:
                img_path = info.get("boss_path") or os.path.join(SPRITES_DIR, info["img"])
                img = pygame.image.load(img_path).convert_alpha()
                surf = pygame.transform.smoothscale(img, (self.icon_size, self.icon_size))
                gray_surf = surf.copy()
                gray_surf.fill((40, 40, 40), special_flags=pygame.BLEND_RGBA_MULT)
                sound = pygame.mixer.Sound(os.path.join(SFX_DIR, info["sfx"]))
            except Exception:
                surf = pygame.Surface((self.icon_size, self.icon_size), pygame.SRCALPHA)
                gray_surf = surf.copy()
                sound = None

            self.chars.append(
                {
                    "id": info["id"],
                    "rect": pygame.Rect(0, 0, self.frame_size, self.frame_size),
                    "surf": surf,
                    "gray": gray_surf,
                    "sound": sound,
                }
            )

        self._layout()

    def _layout(self) -> None:
        panel_w = int(self.w * 0.78)
        panel_h = int(self.h * 0.74)
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (self.w // 2, self.h // 2)

        self.panel_scaled = None
        if self.panel_img:
            self.panel_scaled = pygame.transform.smoothscale(self.panel_img, (panel_w, panel_h))

        grid_top = self.panel_rect.top + 170
        grid_left = self.panel_rect.left + 95
        grid_right = self.panel_rect.right - 95
        grid_w = grid_right - grid_left

        cols = min(self.grid_cols, max(1, len(self.chars)))
        needed_w = cols * self.frame_size + (cols - 1) * self.grid_gap
        start_x = grid_left + max(0, (grid_w - needed_w) // 2)

        for i, ch in enumerate(self.chars):
            col = i % cols
            x = start_x + col * (self.frame_size + self.grid_gap)
            y = grid_top
            ch["rect"] = pygame.Rect(x, y, self.frame_size, self.frame_size)

        self.slots_rect = pygame.Rect(0, 0, self.panel_rect.w - 190, 140)
        self.slots_rect.midbottom = (self.panel_rect.centerx, self.panel_rect.bottom - 50)

        self._random_btn_rect = pygame.Rect(0, 0, 72, 34)
        self._random_btn_rect.bottomright = (self.slots_rect.right - 12, self.slots_rect.top + 38)

        self._carousel_images = None
        self._carousel_index = 0
        self._carousel_timer = 0
        self._carousel_alpha = 255

        self._slot_ha_qi_img = None
        self._slot_ha_qi_timer = 0
        self._slot_ha_qi_slot = -1

    def _init_carousel(self):
        if self._carousel_images is not None:
            return
        images = []
        bg_dir = os.path.join(BASE_DIR, "Wallpapers")
        for name in ["丛林地府地图.png", "沙漠地图.png", "洞穴背景.png"]:
            try:
                img = pygame.image.load(os.path.join(bg_dir, name)).convert()
                img = pygame.transform.smoothscale(img, (self.w, self.h))
                darken = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                darken.fill((0, 0, 0, 160))
                img.blit(darken, (0, 0))
                images.append(img)
            except Exception:
                pass
        self._carousel_images = images or [None]

    def _draw_slots_bg(self, surface):
        sr = self.slots_rect
        bg = pygame.Surface((sr.w, sr.h), pygame.SRCALPHA)
        for row in range(sr.h):
            ratio = row / sr.h
            r = int(22 + ratio * 16)
            g = int(28 + ratio * 20)
            b = int(42 + ratio * 16)
            pygame.draw.line(bg, (r, g, b, 220), (0, row), (sr.w, row))
        pygame.draw.rect(bg, (255, 215, 0, 40), (0, 0, sr.w, sr.h), border_radius=16)
        bg.set_alpha(200)
        surface.blit(bg, sr.topleft)

    def _draw_random_btn(self, surface, mouse_pos):
        r = self._random_btn_rect
        hovered = r.collidepoint(mouse_pos)
        available = [ch for ch in self.chars if ch["id"] not in self.selections]
        if not available:
            return

        btn = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        if hovered:
            pygame.draw.rect(btn, (100, 180, 80), (0, 0, r.w, r.h), border_radius=12)
            pygame.draw.rect(btn, (180, 255, 150), (0, 0, r.w, r.h), width=2, border_radius=12)
        else:
            pygame.draw.rect(btn, (40, 100, 50), (0, 0, r.w, r.h), border_radius=12)
            pygame.draw.rect(btn, (140, 200, 120), (0, 0, r.w, r.h), width=2, border_radius=12)
        label = self.font_sub.render(t("select_random"), True, (255, 255, 230) if hovered else (210, 240, 200))
        btn.blit(label, label.get_rect(center=(r.w // 2, r.h // 2)))
        surface.blit(btn, r.topleft)

    def _try_random_pick(self):
        available = [ch for ch in self.chars if ch["id"] not in self.selections]
        if not available:
            return False
        import random as _rand
        ch = _rand.choice(available)
        if ch["sound"]:
            ch["sound"].play()
        slot_idx = self.current_turn
        self.selections[self.current_turn] = ch["id"]
        if ch["id"] == "MaoDie":
            self._trigger_slot_ha_qi(slot_idx)
        self.current_turn += 1
        self.temp_highlight = None
        self.last_clicked_id = None
        if self.current_turn >= self.num_players:
            return self.selections
        return None

    def _trigger_slot_ha_qi(self, slot_idx):
        self._slot_ha_qi_slot = slot_idx
        self._slot_ha_qi_timer = 40
        if self._slot_ha_qi_img is None:
            try:
                raw = pygame.image.load(os.path.join(SPRITES_DIR, "耄耋哈气.png")).convert_alpha()
                self._slot_ha_qi_img = pygame.transform.scale(raw, (80, 60))
            except Exception:
                self._slot_ha_qi_img = pygame.Surface((80, 60), pygame.SRCALPHA)
                self._slot_ha_qi_img.fill((180, 180, 200, 120))

    def _draw_slot_ha_qi(self, surface, cx, cy):
        self._slot_ha_qi_timer -= 1
        if self._slot_ha_qi_timer <= 0 or not self._slot_ha_qi_img:
            return
        progress = 1.0 - self._slot_ha_qi_timer / 40.0
        scale = 1.0
        if progress < 0.15:
            scale = progress / 0.15
        elif progress > 0.7:
            scale = 1.0 - (progress - 0.7) / 0.3
        alpha = int(200 * (1.0 - abs(progress - 0.4) * 2.0))
        sw = int(self._slot_ha_qi_img.get_width() * scale)
        sh = int(self._slot_ha_qi_img.get_height() * scale)
        if sw < 4 or sh < 4:
            return
        scaled = pygame.transform.smoothscale(self._slot_ha_qi_img, (sw, sh))
        scaled.set_alpha(alpha)
        r = scaled.get_rect(center=(cx, cy))
        surface.blit(scaled, r)

    def update_and_draw(self, surface: pygame.Surface) -> None:
        self._init_carousel()

        self._carousel_timer += 1
        if self._carousel_timer > 540:
            if self._carousel_images and len(self._carousel_images) > 1:
                self._carousel_index = (self._carousel_index + 1) % len(self._carousel_images)
            self._carousel_timer = 0

        if self._carousel_images and self._carousel_images[0]:
            surface.blit(self._carousel_images[self._carousel_index], (0, 0))
        else:
            surface.fill((32, 46, 30))
            shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 70))
            surface.blit(shade, (0, 0))

        # Panel
        if self.panel_scaled:
            surface.blit(self.panel_scaled, self.panel_rect.topleft)
        else:
            pygame.draw.rect(surface, (15, 20, 15), self.panel_rect, border_radius=18)
            pygame.draw.rect(surface, (120, 170, 85), self.panel_rect, width=3, border_radius=18)

        # Titles
        if self.boss_only:
            title_key = "boss_select"
        elif self.exclude_list:
            title_key = "boss_challengers"
        else:
            title_key = "select_chars"
        title_surf = self.font_title.render(t(title_key), True, (255, 215, 0))
        surface.blit(title_surf, title_surf.get_rect(midtop=(self.panel_rect.centerx, self.panel_rect.top + 28)))

        if self.num_players == 2:
            prompt = t("select_turn_1_p1") if self.current_turn == 0 else t("select_turn_1_p2")
        else:
            prompt = t("select_turn_multi").replace("{n}", str(self.current_turn + 1))
        colors = [(100, 255, 140), (255, 120, 120), (120, 170, 255), (255, 235, 120), (255, 140, 255)]
        p_surf = self.font.render(prompt, True, colors[self.current_turn % len(colors)])
        surface.blit(p_surf, p_surf.get_rect(midtop=(self.panel_rect.centerx, self.panel_rect.top + 92)))

        hint = self.font_sub.render(t("select_hint"), True, (235, 235, 235))
        surface.blit(hint, hint.get_rect(midtop=(self.panel_rect.centerx, self.panel_rect.top + 140)))

        mouse_pos = pygame.mouse.get_pos()

        # Character grid
        for ch in self.chars:
            is_taken = ch["id"] in self.selections or ch["id"] in self._excluded_ids
            hovered = ch["rect"].collidepoint(mouse_pos) and not is_taken and ch["id"] not in self._excluded_ids
            highlight = (ch["id"] == self.temp_highlight) and not is_taken

            inner = ch["rect"].inflate(-24, -24)
            _draw_bamboo_frame(surface, inner, active=hovered, taken=is_taken, highlight=highlight)

            avatar = ch["gray"] if is_taken else ch["surf"]
            surface.blit(avatar, avatar.get_rect(center=inner.center))

            name_key = ch["id"].lower()
            display_name = t(name_key) if t(name_key) != name_key else ch["id"]
            name_surf = self.font_sub.render(display_name, True, (235, 235, 235) if not is_taken else (160, 160, 160))
            surface.blit(name_surf, name_surf.get_rect(midtop=(inner.centerx, inner.bottom + 8)))

            if is_taken:
                tag = self.font_sub.render(t("select_taken"), True, (210, 210, 210))
                surface.blit(tag, tag.get_rect(center=(inner.centerx, inner.centery + 4)))

        # Selected slots
        self._draw_slots_bg(surface)
        pygame.draw.rect(surface, (255, 215, 0), self.slots_rect, width=2, border_radius=16)
        bar_title = self.font_sub.render(t("select_selected"), True, (245, 245, 245))
        surface.blit(bar_title, bar_title.get_rect(midtop=(self.slots_rect.centerx, self.slots_rect.top + 10)))

        self._draw_random_btn(surface, mouse_pos)

        slot_gap = 24
        total_w = self.num_players * self.frame_size + (self.num_players - 1) * slot_gap
        sx = self.slots_rect.centerx - total_w // 2
        sy = self.slots_rect.top + 46
        for i in range(self.num_players):
            r = pygame.Rect(sx + i * (self.frame_size + slot_gap), sy, self.frame_size, self.frame_size)
            inner = r.inflate(-24, -24)
            active = i == self.current_turn
            _draw_bamboo_frame(surface, inner, active=active, taken=False, highlight=False)
            label = self.font_sub.render(f"P{i+1}", True, (255, 215, 0) if active else (220, 220, 220))
            surface.blit(label, label.get_rect(midtop=(r.centerx, r.bottom + 4)))

            sel = self.selections[i] if i < len(self.selections) else None
            if sel:
                for ch in self.chars:
                    if ch["id"] == sel:
                        surface.blit(ch["surf"], ch["surf"].get_rect(center=inner.center))
                        break

            if sel == "MaoDie" and self._slot_ha_qi_timer > 0 and self._slot_ha_qi_slot == i:
                self._draw_slot_ha_qi(surface, inner.centerx, inner.centery)

    def handle_event(self, event: pygame.event.Event):
        # Auto-reset if reused from previous match
        if self.current_turn >= self.num_players:
            self.current_turn = 0
            self.selections = [None] * self.num_players
            self.temp_highlight = None
            self.last_clicked_id = None
            self.last_click_time = 0

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            now = pygame.time.get_ticks()

            if self._random_btn_rect.collidepoint(event.pos):
                result = self._try_random_pick()
                if result is not None:
                    return result
                self.last_click_time = now
                return None

            for ch in self.chars:
                if ch["id"] in self.selections or ch["id"] in self._excluded_ids:
                    continue
                if not ch["rect"].collidepoint(event.pos):
                    continue

                # Double click to confirm
                if ch["id"] == self.last_clicked_id and (now - self.last_click_time) < self.double_threshold:
                    if ch["sound"]:
                        ch["sound"].play()

                    slot_idx = self.current_turn
                    self.selections[self.current_turn] = ch["id"]
                    if ch["id"] == "MaoDie":
                        self._trigger_slot_ha_qi(slot_idx)
                    self.current_turn += 1
                    self.temp_highlight = None
                    self.last_clicked_id = None

                    if self.current_turn >= self.num_players:
                        return self.selections
                else:
                    if audio_manager.audio:
                        audio_manager.audio.play_ui_click()
                    self.temp_highlight = ch["id"]
                    self.last_click_time = now
                    self.last_clicked_id = ch["id"]

        if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
            result = self._try_random_pick()
            if result is not None:
                return result

        return None