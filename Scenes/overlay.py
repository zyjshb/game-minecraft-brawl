import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
import config
import audio_manager
from i18n import t

class _SettingsButton:
    def __init__(self, rect, text, font, base_color=(200, 200, 200), hovering_color=(255, 215, 0), i18n_key=None):
        self.rect = pygame.Rect(rect)
        self._raw_text = text
        self._i18n_key = i18n_key
        self.font = font
        self.base_color, self.hovering_color = base_color, hovering_color
        self._render(base_color)

    def _get_text(self):
        if self._i18n_key:
            try:
                from i18n import t
                return t(self._i18n_key)
            except Exception:
                pass
        return self._raw_text

    def _render(self, color):
        self.text = self.font.render(self._get_text(), True, color)
        self.text_rect = self.text.get_rect(center=self.rect.center)

    def update(self, surface):
        self._render(self.base_color)
        surface.blit(self.text, self.text_rect)

    def changeColor(self, position):
        if self.rect.collidepoint(position):
            self._render(self.hovering_color)
        else:
            self._render(self.base_color)

    def is_clicked(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos):
                return True
        return False

class SettingsOverlay:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.active = False
        
        ui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Scenes", "UI")
        try:
            path = os.path.join(ui_dir, "木板.png")
            self.wood_board_raw = pygame.image.load(path).convert_alpha()
            self.wood_board_raw.set_colorkey((0, 0, 0)) 
        except Exception as e:
            print(f"[WARN] 木板加载失败: {e}")
            self.wood_board_raw = pygame.Surface((400, 300))
            self.wood_board_raw.fill((139, 69, 19)) 
            
        board_w = int(w * 0.35) 
        board_h = int(h * 0.45)
        self.wood_board = pygame.transform.smoothscale(self.wood_board_raw, (board_w, board_h))
        self.board_rect = self.wood_board.get_rect()
        self.board_rect.x = (self.w - board_w) // 2 
        
        self.anim_speed = 35 
        self.target_y = 0
        self.current_y = -board_h 
        
        self.dark_mask = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.dark_mask.fill((0, 0, 0, 160)) 
        
        try:
            self.font_btn = get_font(50) 
        except:
            self.font_btn = pygame.font.Font(None, 50)
            
        btn_w, btn_h = 300, 70
        self.btn_continue = _SettingsButton((0, 0, btn_w, btn_h), "", self.font_btn, i18n_key="settings_resume")
        self.btn_main_menu = _SettingsButton((0, 0, btn_w, btn_h), "", self.font_btn, i18n_key="settings_back")
        self._btn_intro_rect = pygame.Rect(0, 0, 260, 56)
        self._intro_toggle_font = get_font(28)

        self.font_label = get_font(34)
        self.font_pct = get_font(28)
        self._slider_dragging = False
        self.music_volume = audio_manager.audio.get_music_volume_user() if audio_manager.audio else 0.7
        self._slider_rect = pygame.Rect(0, 0, int(board_w * 0.78), 10)
        self._slider_knob_radius = 12
        self._slider_panel_rect = pygame.Rect(0, 0, int(board_w * 0.82), 92)

    def activate(self):
        self.active = True
        self.current_y = -self.board_rect.h 
        fake_pos = (-1000, -1000)
        self.btn_continue.changeColor(fake_pos)
        self.btn_main_menu.changeColor(fake_pos)

    def deactivate(self):
        self.active = False

    def handle_event(self, event, mouse_pos):
        if not self.active: return None
        if self.current_y < self.target_y: return None
        
        self.btn_continue.changeColor(mouse_pos)
        self.btn_main_menu.changeColor(mouse_pos)
        
        if self.btn_continue.is_clicked(event, mouse_pos):
            if audio_manager.audio:
                audio_manager.audio.play_ui_click()
            self.deactivate()
            return "RESUME"
            
        if self.btn_main_menu.is_clicked(event, mouse_pos):
            if audio_manager.audio:
                audio_manager.audio.play_ui_click()
            self.deactivate()
            return "BACK_TO_MENU"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._slider_hit_test(mouse_pos):
                self._slider_dragging = True
                if audio_manager.audio:
                    audio_manager.audio.play_ui_click()
                self._set_volume_from_mouse(mouse_pos[0])
                return None
            if self._btn_intro_rect.collidepoint(mouse_pos):
                new_val = not config.SKIP_BOSS_INTRO
                config.SKIP_BOSS_INTRO = new_val
                config.set_setting("skip_boss_intro", new_val)
                if audio_manager.audio:
                    audio_manager.audio.play_ui_click()
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._slider_dragging = False

        if event.type == pygame.MOUSEMOTION and self._slider_dragging:
            self._set_volume_from_mouse(mouse_pos[0])
            
        return None

    def update_and_draw(self, surface):
        if not self.active: return
        
        surface.blit(self.dark_mask, (0, 0))
        
        if self.current_y < self.target_y:
            self.current_y += self.anim_speed
            if self.current_y > self.target_y:
                self.current_y = self.target_y
                
        self.board_rect.y = int(self.current_y)
        surface.blit(self.wood_board, self.board_rect)

        bx = self.board_rect.centerx
        wooden_area_center_y = self.board_rect.y + int(self.board_rect.h * 0.62)
        
        slider_y = wooden_area_center_y - 135
        self._slider_rect.center = (bx, slider_y)
        self._slider_panel_rect.center = (bx, slider_y + 18)

        self.btn_continue.rect.center = (bx, wooden_area_center_y - 45)
        self.btn_continue.text_rect.center = self.btn_continue.rect.center
        
        self.btn_main_menu.rect.center = (bx, wooden_area_center_y + 45)
        self.btn_main_menu.text_rect.center = self.btn_main_menu.rect.center

        panel = pygame.Surface(self._slider_panel_rect.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        pygame.draw.rect(panel, (10, 10, 10, 120), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (255, 215, 0, 110), panel.get_rect(), width=2, border_radius=14)
        surface.blit(panel, self._slider_panel_rect.topleft)

        label = self.font_label.render(t("settings_music"), True, (245, 245, 245))
        surface.blit(label, label.get_rect(midtop=(bx, self._slider_panel_rect.top + 10)))

        track_rect = self._slider_rect.copy()
        track_rect.y = self._slider_panel_rect.top + 48
        self._slider_rect = track_rect

        pygame.draw.rect(surface, (0, 0, 0), self._slider_rect.inflate(8, 8), border_radius=10)
        pygame.draw.rect(surface, (210, 210, 210), self._slider_rect, width=2, border_radius=10)

        fill_w = int(self._slider_rect.w * self.music_volume)
        if fill_w > 0:
            fill_rect = pygame.Rect(self._slider_rect.x, self._slider_rect.y, fill_w, self._slider_rect.h)
            pygame.draw.rect(surface, (255, 215, 0), fill_rect, border_radius=10)

        knob_x = self._slider_rect.x + int(self._slider_rect.w * self.music_volume)
        knob_y = self._slider_rect.centery
        pygame.draw.circle(surface, (255, 215, 0), (knob_x, knob_y), self._slider_knob_radius + 6)
        pygame.draw.circle(surface, (255, 255, 255), (knob_x, knob_y), self._slider_knob_radius + 2)
        pygame.draw.circle(surface, (40, 40, 40), (knob_x, knob_y), self._slider_knob_radius + 2, width=2)

        pct = int(self.music_volume * 100)
        pct_surf = self.font_pct.render(f"{pct}%", True, (235, 235, 235))
        surface.blit(pct_surf, pct_surf.get_rect(midtop=(bx, self._slider_panel_rect.top + 58)))

        self.btn_continue.update(surface)
        self.btn_main_menu.update(surface)

        intro_btn_y = self.board_rect.y + int(self.board_rect.h * 0.88)
        self._btn_intro_rect.centerx = bx
        self._btn_intro_rect.centery = intro_btn_y

        mx, my = pygame.mouse.get_pos()
        hovered = self._btn_intro_rect.collidepoint(mx, my)
        bg_color = (55, 55, 65) if hovered else (35, 35, 45)
        border_color = (255, 215, 0) if hovered else (120, 120, 130)
        pygame.draw.rect(surface, bg_color, self._btn_intro_rect, border_radius=14)
        pygame.draw.rect(surface, border_color, self._btn_intro_rect, width=2, border_radius=14)

        skip = config.SKIP_BOSS_INTRO
        toggle_text = t("settings_intro_off") if skip else t("settings_intro_on")
        status_color = (255, 120, 100) if skip else (120, 255, 140)
        ts = self._intro_toggle_font.render(toggle_text, True, (235, 235, 235))
        surface.blit(ts, ts.get_rect(center=(bx, intro_btn_y - 8)))
        status_label = self._intro_toggle_font.render("●", True, status_color)
        surface.blit(status_label, status_label.get_rect(center=(bx + ts.get_width() // 2 + 18, intro_btn_y - 8)))

    def _slider_hit_test(self, mouse_pos):
        knob_x = self._slider_rect.x + int(self._slider_rect.w * self.music_volume)
        knob_y = self._slider_rect.centery
        knob_rect = pygame.Rect(0, 0, self._slider_knob_radius * 2, self._slider_knob_radius * 2)
        knob_rect.center = (knob_x, knob_y)
        return self._slider_rect.inflate(30, 30).collidepoint(mouse_pos) or knob_rect.collidepoint(mouse_pos)

    def _set_volume_from_mouse(self, mouse_x):
        t = (mouse_x - self._slider_rect.x) / max(1, self._slider_rect.w)
        self.music_volume = max(0.0, min(1.0, t))
        if audio_manager.audio:
            audio_manager.audio.set_music_volume_user(self.music_volume)
