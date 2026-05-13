import pygame
import cv2
import os
import sys
from Scenes.button import Button
from config import get_font
from i18n import t, get_text
import math

class StartMenu:
    def __init__(self, w, h):
        self.w, self.h = w, h
        
        ui_dir = os.path.join(os.path.dirname(__file__), "UI")
        self.video_path = os.path.join(ui_dir, "开头动画.mp4")
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            print(f"[WARN] 未找到视频素材 {self.video_path}")

        try:
            self.font_title = get_font(100)
        except:
            self.font_title = pygame.font.Font(None, 100)
        self.font_hint = get_font(30)

        btn_w, btn_h = 360, 90 
        cx = self.w // 2 - btn_w // 2
        
        start_y = self.h // 2 - 80 
        spacing = 120 

        self.btn_1v1   = Button(cx, start_y,           btn_w, btn_h, "", i18n_key="btn_1v1")
        self.btn_brawl = Button(cx, start_y + spacing, btn_w, btn_h, "", i18n_key="btn_brawl")
        self.btn_boss  = Button(cx, start_y + spacing * 2, btn_w, btn_h, "", i18n_key="btn_boss")
        self.btn_quit  = Button(cx, start_y + spacing * 3, btn_w, btn_h, "", i18n_key="btn_quit_game")

    def update_and_draw(self, surface):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_surf = pygame.surfarray.make_surface(frame.transpose((1, 0, 2)))
            video_surf = pygame.transform.scale(video_surf, (self.w, self.h))
            surface.blit(video_surf, (0, 0))
        else:
            surface.fill((20, 20, 25))

        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60)) 
        surface.blit(overlay, (0, 0))

        title_text = t("game_title")
        shadow_surf = self.font_title.render(title_text, True, (20, 20, 20))
        surface.blit(shadow_surf, (self.w // 2 - shadow_surf.get_width() // 2 + 5, 185))
        title_surf = self.font_title.render(title_text, True, (255, 215, 0))
        title_pos = (self.w // 2 - title_surf.get_width() // 2, 180)
        surface.blit(title_surf, title_pos)

        hint_text = t("f11_hint")
        t_time = pygame.time.get_ticks()
        glow = 150 + int(80 * (0.5 + 0.5 * math.sin(t_time / 420)))
        hint_color = (255, glow, 40)

        scale = 1.02 + 0.06 * math.sin(t_time / 180)
        bob_y = int(3 * math.sin(t_time / 120))

        base = self.font_hint.render(hint_text, True, hint_color)
        shadow = self.font_hint.render(hint_text, True, (0, 0, 0))
        base_rot = pygame.transform.rotozoom(base, 0, scale)
        shadow_rot = pygame.transform.rotozoom(shadow, 0, scale)

        title_rect = title_surf.get_rect(topleft=title_pos)
        hx = title_rect.centerx
        hy = title_rect.bottom + 18 + bob_y

        for ox, oy in ((2, 2), (3, 2), (2, 3), (3, 3)):
            shadow_rect = shadow_rot.get_rect(center=(hx + ox, hy + oy))
            surface.blit(shadow_rot, shadow_rect)

        base_rect = base_rot.get_rect(center=(hx, hy))
        surface.blit(base_rot, base_rect)

        self.btn_1v1.draw(surface)
        self.btn_brawl.draw(surface)
        self.btn_boss.draw(surface)
        self.btn_quit.draw(surface)

    def handle_event(self, event):
        if self.btn_1v1.is_clicked(event): return "MODE_1V1"
        if self.btn_brawl.is_clicked(event): return "MODE_BRAWL"
        if self.btn_boss.is_clicked(event): return "MODE_BOSS"
        if self.btn_quit.is_clicked(event): return "QUIT"
        return None

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
