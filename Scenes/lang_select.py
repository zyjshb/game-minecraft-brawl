import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
from i18n import LANGUAGES, get_lang_order, set_language, get_language, t
import audio_manager

class _LangButton:
    def __init__(self, x, y, w, h, lang_code):
        self.rect = pygame.Rect(x, y, w, h)
        self.lang_code = lang_code
        self._font = get_font(28)
        self.hovered = False

    def draw(self, surface, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        selected = (get_language() == self.lang_code)

        if selected:
            color = (255, 220, 50)
            bg = (55, 45, 25, 220)
            border_color = (255, 215, 0, 220)
        elif self.hovered:
            color = (230, 220, 180)
            bg = (40, 35, 20, 200)
            border_color = (180, 160, 80, 160)
        else:
            color = (190, 180, 160)
            bg = (28, 24, 18, 200)
            border_color = (80, 70, 50, 120)

        s = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        inner = s.get_rect().inflate(-2, -2)
        pygame.draw.rect(s, bg, s.get_rect(), border_radius=10)
        pygame.draw.rect(s, border_color, s.get_rect(), width=2, border_radius=10)
        if selected:
            pygame.draw.rect(s, (255, 215, 0, 80), inner, width=3, border_radius=8)

        name = LANGUAGES[self.lang_code]
        txt = self._font.render(name, True, color)
        tr = txt.get_rect(center=s.get_rect().center)
        s.blit(txt, tr)
        surface.blit(s, self.rect.topleft)

    def is_clicked(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos):
                return True
        return False


class LanguageSelect:
    def __init__(self, w, h):
        self.w, self.h = w, h

        ui_dir = os.path.join(os.path.dirname(__file__), "UI")
        self.global_bg = None
        try:
            raw = pygame.image.load(os.path.join(ui_dir, "战斗背景图.png")).convert()
            self.global_bg = pygame.transform.scale(raw, (w, h))
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            self.global_bg.blit(overlay, (0, 0))
        except Exception:
            self.global_bg = None

        try:
            self.font_title = get_font(64)
            self.font_hint = get_font(26)
        except:
            self.font_title = pygame.font.Font(None, 64)
            self.font_hint = pygame.font.Font(None, 26)

        self._lang_buttons = []
        self._build_buttons()

        btn_cx = w // 2
        self.btn_back_size = (260, 56)
        self.btn_back_rect = pygame.Rect(0, 0, *self.btn_back_size)
        self.btn_back_rect.center = (btn_cx, int(h * 0.88))
        self._btn_back_font = get_font(36)
        self._btn_back_hover = False

    def _build_buttons(self):
        self._lang_buttons = []
        order = get_lang_order()
        cols = 3
        rows = 3
        btn_w, btn_h = 300, 68
        margin_x = 24
        margin_y = 18

        total_w = cols * btn_w + (cols - 1) * margin_x
        total_h = rows * btn_h + (rows - 1) * margin_y

        start_x = (self.w - total_w) // 2 + btn_w // 2
        start_y = int(self.h * 0.32)

        for i, code in enumerate(order):
            col = i % cols
            row = i // cols
            x = start_x + col * (btn_w + margin_x) - btn_w // 2
            y = start_y + row * (btn_h + margin_y)
            self._lang_buttons.append(_LangButton(x, y, btn_w, btn_h, code))

    def handle_event(self, event, mouse_pos):
        for lb in self._lang_buttons:
            if lb.is_clicked(event, mouse_pos):
                set_language(lb.lang_code)
                if audio_manager.audio:
                    audio_manager.audio.play_ui_click()
                return "LANG_CHANGED"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_back_rect.collidepoint(mouse_pos):
                if audio_manager.audio:
                    audio_manager.audio.play_ui_click()
                return "BACK"

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "BACK"

        return None

    def update_and_draw(self, surface):
        if self.global_bg:
            surface.blit(self.global_bg, (0, 0))
        else:
            surface.fill((8, 8, 14))

        current_lang_name = LANGUAGES.get(get_language(), "简体中文")
        title_text = t("lang_title").replace("{name}", current_lang_name)
        title_surf = self.font_title.render(title_text, True, (255, 215, 0))
        shadow = self.font_title.render(title_text, True, (20, 20, 20))
        tx = self.w // 2 - title_surf.get_width() // 2
        ty = int(self.h * 0.10)
        surface.blit(shadow, (tx + 3, ty + 3))
        surface.blit(title_surf, (tx, ty))

        hint = self.font_hint.render(t("lang_hint"), True, (200, 200, 200))
        hx = self.w // 2 - hint.get_width() // 2
        surface.blit(hint, (hx, ty + 72))

        mouse_pos = pygame.mouse.get_pos()
        for lb in self._lang_buttons:
            lb.draw(surface, mouse_pos)

        self._btn_back_hover = self.btn_back_rect.collidepoint(mouse_pos)
        back_bg = (50, 40, 20) if self._btn_back_hover else (35, 28, 18)
        back_s = pygame.Surface(self.btn_back_size, pygame.SRCALPHA)
        pygame.draw.rect(back_s, (*back_bg, 210), back_s.get_rect(), border_radius=12)
        edge_color = (255, 215, 0) if self._btn_back_hover else (140, 120, 80)
        pygame.draw.rect(back_s, (*edge_color, 180), back_s.get_rect(), width=2, border_radius=12)

        back_text = self._btn_back_font.render(t("btn_back"), True, (245, 245, 245))
        br = back_text.get_rect(center=(self.btn_back_size[0] // 2, self.btn_back_size[1] // 2))
        back_s.blit(back_text, br)
        surface.blit(back_s, self.btn_back_rect.topleft)
