import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font 
from Scenes.button import Button
from i18n import t

class GameOver:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.theme_color = (168, 184, 100)
        self.font_big = get_font(80) 
        
        btn_w, btn_h = 320, 90
        cx = self.w // 2 - btn_w // 2
        start_y = self.h // 2 - 50 
        spacing = 115 
        
        stone_skin = "选择框石质.png"
        
        self.btn_restart = Button(cx, start_y, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="btn_restart")
        self.btn_menu    = Button(cx, start_y + spacing, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="btn_main_menu")
        self.btn_quit    = Button(cx, start_y + spacing*2, btn_w, btn_h, "", custom_image=stone_skin, i18n_key="btn_quit_game")

    def update_and_draw(self, surface, winner_name):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190)) 
        surface.blit(overlay, (0, 0))
        
        title_text = t("battle_over").replace("{name}", winner_name)
        t_surf = self.font_big.render(title_text, True, self.theme_color)
        t_rect = t_surf.get_rect(center=(self.w // 2, self.h // 2 - 180))
        
        shadow = self.font_big.render(title_text, True, (20, 20, 20))
        surface.blit(shadow, (t_rect.x + 4, t_rect.y + 4))
        surface.blit(t_surf, t_rect)
        
        self.btn_restart.draw(surface)
        self.btn_menu.draw(surface)
        self.btn_quit.draw(surface)

    def handle_event(self, event):
        if self.btn_restart.is_clicked(event): return "RESTART"
        if self.btn_menu.is_clicked(event):    return "MENU"
        if self.btn_quit.is_clicked(event):    return "QUIT"
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: return "RESTART"
            if event.key == pygame.K_m: return "MENU"
            if event.key == pygame.K_q: return "QUIT"
        return None
