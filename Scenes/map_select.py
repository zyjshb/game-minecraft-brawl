import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
from i18n import t

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WALL_DIR = os.path.join(BASE_DIR, "Wallpapers")

class MapSelect:
    def __init__(self, w, h, boss_mode=False):
        self.w, self.h = w, h
        self.boss_mode = boss_mode
        self.maps = self._build_maps()
        self.current_idx = 0

        self.is_fading = False
        self.fade_alpha = 0
        self.confirmed = False

        self.font = get_font(40)
        self.font_small = get_font(28)
        self._frame_rect = None

        self.preview_size = (600, 400)
        self.previews = []
        self.blurred_bgs = []
        self._vignette = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(self._vignette, (0, 0, 0, 110), (0, 0, self.w, self.h), width=180)

        for m in self.maps:
            try:
                load_dir = m.get("dir", WALL_DIR)
                f = m.get("file")
                if f is None:
                    raise Exception("locked")
                original_img = pygame.image.load(os.path.join(load_dir, f)).convert()
                p = pygame.transform.smoothscale(original_img, self.preview_size)
                self.previews.append(p)
                small_blur = pygame.transform.smoothscale(original_img, (self.w // 20, self.h // 20))
                full_blur = pygame.transform.smoothscale(small_blur, (self.w, self.h))
                dark_overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                dark_overlay.fill((10, 12, 20, 175))
                full_blur.blit(dark_overlay, (0, 0))
                self.blurred_bgs.append(full_blur)
            except Exception:
                locked = pygame.Surface(self.preview_size)
                locked.fill((30, 30, 35))
                lk = self.font_small.render("???", True, (100, 100, 100))
                locked.blit(lk, lk.get_rect(center=(self.preview_size[0] // 2, self.preview_size[1] // 2)))
                self.previews.append(locked)
                fb = pygame.Surface((self.w, self.h))
                fb.fill((12, 14, 22))
                self.blurred_bgs.append(fb)

    def _build_maps(self):
        if self.boss_mode:
            boss_file = "boss对战_平原要塞.png"
            boss_path = os.path.join(WALL_DIR, boss_file)
            if os.path.isfile(boss_path):
                return [
                    {"id": "boss_plain_fortress", "i18n_key": "map_boss", "file": boss_file, "dir": WALL_DIR, "locked": False},
                ]
            return []

        search_dir = WALL_DIR
        png_files = [f for f in os.listdir(search_dir)
                     if f.lower().endswith(".png") and "boss" not in f.lower()] if os.path.isdir(search_dir) else []
        used = set()

        def pick_file(prefer_name=None, keyword=None):
            files = png_files
            if prefer_name and prefer_name in files and prefer_name not in used:
                used.add(prefer_name)
                return prefer_name
            if keyword:
                for f in files:
                    if keyword in f and f not in used:
                        used.add(f)
                        return f
            for f in files:
                if f not in used:
                    used.add(f)
                    return f
            return None

        candidates = [
            {"id": "desert", "i18n_key": "map_desert", "prefer": "沙漠地图.png", "keyword": "沙漠"},
            {"id": "cave", "i18n_key": "map_cave", "prefer": "洞穴背景.png", "keyword": "洞穴"},
            {"id": "ocean", "i18n_key": "map_ocean", "prefer": "深海圣殿溺尸地图.png", "keyword": "海底"},
            {"id": "jungle", "i18n_key": "map_jungle", "prefer": "丛林地府地图.png", "keyword": "丛林"},
            {"id": "ruins", "i18n_key": "map_ruins", "prefer": None, "keyword": None},
        ]

        maps = []
        for c in candidates:
            file_name = pick_file(c["prefer"], c["keyword"])
            if file_name:
                maps.append({"id": c["id"], "i18n_key": c["i18n_key"], "file": file_name})

        if not maps:
            maps.append({"id": "fallback", "i18n_key": "map_fallback", "file": None})
        return maps

    def update_and_draw(self, surface):
        surface.blit(self.blurred_bgs[self.current_idx], (0, 0))
        surface.blit(self._vignette, (0, 0))

        p_img = self.previews[self.current_idx]
        p_rect = p_img.get_rect(center=(self.w // 2, self.h // 2))
        frame_rect = p_rect.inflate(24, 24)
        self._frame_rect = frame_rect
        glass = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
        glass.fill((36, 40, 52, 165))
        surface.blit(glass, frame_rect.topleft)
        pygame.draw.rect(surface, (235, 225, 190), frame_rect, 3, border_radius=8)
        pygame.draw.rect(surface, (110, 120, 140), frame_rect.inflate(-10, -10), 1, border_radius=6)
        surface.blit(p_img, p_rect)

        arrow_color = (255, 232, 172)
        left_arrow = self.font.render("<", True, arrow_color)
        right_arrow = self.font.render(">", True, arrow_color)
        surface.blit(left_arrow, (frame_rect.left - 80, frame_rect.centery - 20))
        surface.blit(right_arrow, (frame_rect.right + 45, frame_rect.centery - 20))

        m = self.maps[self.current_idx]
        m_name = t(m.get("i18n_key", "map_fallback"))
        locked = m.get("locked", False)
        n_color = (120, 120, 120) if locked else (198, 210, 144)
        n_surf = self.font.render(m_name, True, n_color)
        n_rect = n_surf.get_rect(center=(self.w // 2, p_rect.bottom + 50))
        surface.blit(n_surf, n_rect)

        idx_text = t("map_idx").replace("{n}", str(self.current_idx + 1)).replace("{total}", str(len(self.maps)))
        idx_surf = self.font_small.render(idx_text, True, (185, 185, 185))
        surface.blit(idx_surf, idx_surf.get_rect(center=(self.w // 2, n_rect.bottom + 30)))

        hint_key = "map_locked_hint" if locked else "map_hint"
        hint = self.font_small.render(t(hint_key), True, (220, 220, 220) if not locked else (140, 140, 140))
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h - 80)))

        if locked:
            lock_label = self.font.render(t("map_locked"), True, (180, 50, 50))
            surface.blit(lock_label, lock_label.get_rect(center=(self.w // 2, p_rect.centery)))

        if self.is_fading:
            self.fade_alpha += 10
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.confirmed = True

            black_surf = pygame.Surface((self.w, self.h))
            black_surf.set_alpha(self.fade_alpha)
            black_surf.fill((0, 0, 0))
            surface.blit(black_surf, (0, 0))

    def handle_event(self, event):
        if self.is_fading:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_a, pygame.K_d):
                return
            kp_left = getattr(pygame, "K_KP_LEFT", None)
            kp_right = getattr(pygame, "K_KP_RIGHT", None)
            left_keys = {pygame.K_LEFT, pygame.K_KP4}
            right_keys = {pygame.K_RIGHT, pygame.K_KP6}
            if kp_left is not None:
                left_keys.add(kp_left)
            if kp_right is not None:
                right_keys.add(kp_right)

            if event.key in left_keys:
                self.current_idx = (self.current_idx - 1) % len(self.maps)
            elif event.key in right_keys:
                self.current_idx = (self.current_idx + 1) % len(self.maps)
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if not self.maps[self.current_idx].get("locked", False):
                    self.is_fading = True

    def get_final_map(self):
        if self.confirmed:
            m = self.maps[self.current_idx]
            load_dir = m.get("dir", WALL_DIR)
            f = m.get("file")
            if f is None:
                return None
            return os.path.join(load_dir, f)
        return None
