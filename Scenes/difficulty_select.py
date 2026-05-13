import pygame
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font
from Scenes.button import Button
from i18n import t


class DifficultySelect:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.font_title = get_font(56)
        self.font_sub = get_font(26)
        self.font_desc = get_font(20)

        btn_w, btn_h = 280, 160
        cx = w // 2 - btn_w // 2
        cy = h // 2 - 40
        gap = 320

        stone = "选择框石质.png"
        self.btn_easy = Button(cx - gap, cy, btn_w, btn_h, "", custom_image=stone, i18n_key="diff_easy")
        self.btn_hard = Button(cx, cy, btn_w, btn_h, "", custom_image=stone, i18n_key="diff_hard")
        self.btn_extreme = Button(cx + gap, cy, btn_w, btn_h, "", custom_image=stone, i18n_key="diff_extreme")

    def update_and_draw(self, surface):
        surface.fill((20, 20, 25))
        title = self.font_title.render(t("diff_title"), True, (255, 215, 0))
        surface.blit(title, title.get_rect(center=(self.w // 2, self.h // 2 - 150)))

        hint = self.font_sub.render(t("diff_hint"), True, (168, 184, 100))
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h // 2 - 90)))

        self.btn_easy.draw(surface)
        self.btn_hard.draw(surface)
        self.btn_extreme.draw(surface)

        desc_data = {
            "diff_easy": t("diff_easy_desc"),
            "diff_hard": t("diff_hard_desc"),
            "diff_extreme": t("diff_extreme_desc"),
        }
        mouse = pygame.mouse.get_pos()
        for btn, key in [(self.btn_easy, "diff_easy"), (self.btn_hard, "diff_hard"), (self.btn_extreme, "diff_extreme")]:
            if btn.rect.collidepoint(mouse):
                lines = desc_data[key].split("\n")
                for i, line in enumerate(lines):
                    ds = self.font_desc.render(line, True, (200, 200, 200))
                    surface.blit(ds, ds.get_rect(center=(self.w // 2, self.h - 120 + i * 26)))

    def handle_event(self, event):
        if self.btn_easy.is_clicked(event):
            return self._diff_build(0.7, 0.8, 0.7)
        if self.btn_hard.is_clicked(event):
            return self._diff_build(1.0, 1.0, 1.0)
        if self.btn_extreme.is_clicked(event):
            return self._diff_build(1.5, 1.4, 1.3)
        return None

    def _diff_build(self, hp_m, dmg_m, spd_m):
        return {"hp_mult": hp_m, "dmg_mult": dmg_m, "spd_mult": spd_m, "aggro_mult": spd_m}
