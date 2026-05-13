# Ditu/mine_level.py
import pygame
import math
import os
import sys

# 🌟 从控制塔导入魔法函数
from config import get_font 

from Jue_se.creeper import Creeper
from Jue_se.skeleton import Skeleton
from Jue_se.zombie import Zombie
from world import MineralBlock
from referee import Referee

class BattleLevel:
    def __init__(self, screen, bg_path, selected_chars=None):
        self.screen = screen
        self.width, self.height = screen.get_size()
        
        # 🌟 字体一键搞定！
        self.font_ui = get_font(24) 
        
        # 背景和区域划分 (保持你之前喜欢的正方形逻辑)
        self.bg_img = pygame.transform.scale(pygame.image.load(bg_path).convert(), (self.width, self.height))
        self.ui_top_h = 75
        self.ui_bottom_h = 75
        side = min(self.width, self.height - self.ui_top_h - self.ui_bottom_h)
        self.battle_rect = pygame.Rect((self.width-side)//2, self.ui_top_h, side, side)
        
        self.fighters = []
        # 出生点改到正方形内
        sp = [
            (self.battle_rect.left + 100, self.battle_rect.centery),
            (self.battle_rect.right - 100, self.battle_rect.centery),
            (self.battle_rect.centerx, self.battle_rect.bottom - 100)
        ]

        if selected_chars:
            for i, name in enumerate(selected_chars):
                if i >= len(sp): break
                if name == "Zombie": f = Zombie(sp[i][0], sp[i][1])
                elif name == "Skeleton": f = Skeleton(sp[i][0], sp[i][1])
                else: f = Creeper(sp[i][0], sp[i][1])
                self.fighters.append(f)
        else:
            self.fighters = [Creeper(sp[0][0], sp[0][1]), Skeleton(sp[1][0], sp[1][1]), Zombie(sp[2][0], sp[2][1])]

        # 绑定快捷引用（加上安全检查）
        self.cp = next((f for f in self.fighters if isinstance(f, Creeper)), None)
        self.xb = next((f for f in self.fighters if isinstance(f, Skeleton)), None)
        self.js = next((f for f in self.fighters if isinstance(f, Zombie)), None)

        self.blocks = []
        self.arrows = []
        self.particles = []
        self._generate_random_blocks()
        self.game_started = True

    # ... 剩下的 draw 方法里 ...
    # 使用 self.font_ui.render("对话栏", True, ...) 就能显示中文了！