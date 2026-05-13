# Scenes/button.py
import pygame
import os
from config import get_font 
import audio_manager

class Button:
    def __init__(self, x, y, width, height, text, font_size=32, custom_image="岩石选择框.png", i18n_key=None):
        self.rect = pygame.Rect(x, y, width, height)
        self._raw_text = text
        self._i18n_key = i18n_key
        self.width = width
        self.height = height
        
        self.color_border = (200, 200, 200) 
        self.color_text = (255, 255, 255)   
        
        self.font = get_font(font_size)
            
        current_dir = os.path.dirname(__file__)
        base_dir = os.path.dirname(current_dir)
        
        ui_path = os.path.join(base_dir, "Scenes", "UI", custom_image)
        
        self.image_normal = None
        self.image_hover = None
        
        try:
            btn_surf = pygame.image.load(ui_path).convert_alpha()
            self.image_normal = pygame.transform.scale(btn_surf, (width, height))
            
            self.image_hover = self.image_normal.copy()
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 40)) 
            self.image_hover.blit(overlay, (0, 0))
            
        except Exception as e:
            print(f"[WARN] 无法加载按钮纹理 {custom_image}: {e}，将回退到普通矩形模式")

        self.is_hovered = False

    @property
    def text(self):
        if self._i18n_key:
            try:
                from i18n import t
                return t(self._i18n_key)
            except Exception:
                return self._raw_text
        return self._raw_text

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        if self.image_normal:
            img = self.image_hover if self.is_hovered else self.image_normal
            surface.blit(img, (self.rect.x, self.rect.y))
        else:
            color = (80, 100, 230) if self.is_hovered else (50, 50, 65)
            pygame.draw.rect(surface, color, self.rect, border_radius=12)
            pygame.draw.rect(surface, self.color_border, self.rect, width=2, border_radius=12)
        
        text_surf = self.font.render(self.text, True, self.color_text)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: 
            if self.is_hovered:
                if audio_manager.audio:
                    audio_manager.audio.play_ui_click()
                return True
        return False