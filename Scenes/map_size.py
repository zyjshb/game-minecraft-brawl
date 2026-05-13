import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
from Scenes.button import Button
from i18n import t

class MapSizeSelect:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.font_title = get_font(50)
        
        btn_w, btn_h = 220, 80
        cx = w // 2 - btn_w // 2
        cy = h // 2 - 40
        
        stone_skin = "选择框石质.png"
        
        self.btn_large = Button(cx, cy - 100, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="size_large")
        self.btn_medium = Button(cx, cy, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="size_medium")
        self.btn_small = Button(cx, cy + 100, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="size_small")

    def update_and_draw(self, surface):
        surface.fill((25, 25, 30))
        title = self.font_title.render(t("size_title"), True, (255, 215, 0))
        surface.blit(title, title.get_rect(center=(self.w//2, self.h//2 - 200)))
        self.btn_large.draw(surface)
        self.btn_medium.draw(surface)
        self.btn_small.draw(surface)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.btn_large.is_clicked(event): return (1024, 1024)
            if self.btn_medium.is_clicked(event): return (800, 800)
            if self.btn_small.is_clicked(event): return (640, 640)

        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_w or k == pygame.K_UP:
                return (640, 640)
            elif k == pygame.K_s or k == pygame.K_DOWN:
                return (1024, 1024)
            elif k == pygame.K_SPACE or k == pygame.K_RETURN:
                return (800, 800)

        return None
