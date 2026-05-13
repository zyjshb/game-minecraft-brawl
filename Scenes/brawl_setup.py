import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
from Scenes.button import Button
from i18n import t

class BrawlSetup:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.theme_color = (168, 184, 100)
        self.font_title = get_font(60)
        self.font_hint = get_font(28)

        stone_skin = "选择框石质.png"

        btn_w, btn_h = 200, 80
        cx = w // 2 - btn_w // 2
        cy = h // 2 - 20
        spacing = 230
        
        self.btn_3 = Button(cx - spacing, cy, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="brawl_3p")
        self.btn_4 = Button(cx,           cy, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="brawl_4p")
        self.btn_5 = Button(cx + spacing, cy, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="brawl_5p")

        self.btn_back = Button(w // 2 - 120, h - 150, 240, 70, "", font_size=30, custom_image=stone_skin, i18n_key="btn_back")

    def update_and_draw(self, surface):
        surface.fill((20, 20, 25))
        
        title = self.font_title.render(t("brawl_title"), True, (255, 215, 0))
        surface.blit(title, title.get_rect(center=(self.w // 2, self.h // 2 - 150)))

        hint = self.font_hint.render(t("brawl_hint"), True, self.theme_color)
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h // 2 - 80)))

        self.btn_3.draw(surface)
        self.btn_4.draw(surface) 
        self.btn_5.draw(surface)
        self.btn_back.draw(surface)

    def handle_event(self, event):
        if self.btn_3.is_clicked(event): return 3
        if self.btn_4.is_clicked(event): return 4
        if self.btn_5.is_clicked(event): return 5
        
        if self.btn_back.is_clicked(event):
            return "BACK"
        
        return None
