# Scenes/battle.py
import pygame
import os
import sys

# 🌟 引入中央控制塔
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import get_font

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UI_DIR = os.path.join(BASE_DIR, "Scenes", "UI")

class BattleScene:
    def __init__(self, w, h, map_size, map_path, p1_id, p2_id):
        """
        w, h: 屏幕尺寸 (通常 1024, 1024)
        map_size: 玩家选的竞技场尺寸 (如 640, 800)
        map_path: 玩家选的地图图片路径 (如 洞穴背景.png)
        p1_id, p2_id: 玩家选的角色 ID (如 'Zombie', 'Enderman')
        """
        self.w, self.h = w, h
        self.map_size = map_size # 这是一个元组，如 (800, 800)
        
        # ==========================================
        # 1. 🌟 渲染底板：铺满全屏的战斗背景图
        # ==========================================
        # 严格执行你的指令：虽然你发的是 .jpg，但咱们代码里按 .png 逻辑走
        bg_file = "战斗背景图.png" 
        bg_path = os.path.join(UI_DIR, bg_file)
        
        self.global_bg = None
        try:
            raw_bg = pygame.image.load(bg_path).convert()
            # 铺满全屏 (1024x1024)
            self.global_bg = pygame.transform.scale(raw_bg, (self.w, self.h))
            
            # 给大背景加一层很薄的暗色滤镜 (不抢戏，增加高级感)
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60)) 
            self.global_bg.blit(overlay, (0, 0))
        except Exception as e:
            print(f"[WARN] 无法加载全局背景 {bg_file}: {e}")

        # ==========================================
        # 2. 🌟 战斗擂台：居中的竞技场
        # ==========================================
        self.arena_surf = None
        try:
            raw_arena = pygame.image.load(map_path).convert()
            # 缩放到玩家选的尺寸 (比如 640x640)
            self.arena_surf = pygame.transform.scale(raw_arena, self.map_size)
            # 计算居中位置
            self.arena_rect = self.arena_surf.get_rect(center=(self.w // 2, self.h // 2))
        except Exception as e:
            print(f"[WARN] 无法加载擂台地图: {e}")

        # ==========================================
        # 3. 🌟 初始化角色 (后续可以在这里加角色类)
        # ==========================================
        self.p1_char = p1_id
        self.p2_char = p2_id
        
        # 提示字体
        self.font = get_font(30)

    def update_and_draw(self, surface):
        # 🌟 第一层：画全屏大背景
        if self.global_bg:
            surface.blit(self.global_bg, (0, 0))
        else:
            surface.fill((20, 20, 25))

        # 🌟 第二层：在正中间画战斗擂台
        if self.arena_surf:
            surface.blit(self.arena_surf, self.arena_rect.topleft)
            # 给擂台加一个细细的描边，把它和背景区分开
            pygame.draw.rect(surface, (168, 184, 100), self.arena_rect, 3) 

        # 🌟 第三层：画角色信息 (暂时先用文字占位)
        p1_text = self.font.render(f"P1: {self.p1_char}", True, (255, 255, 255))
        p2_text = self.font.render(f"P2: {self.p2_char}", True, (255, 255, 255))
        surface.blit(p1_text, (20, 20))
        surface.blit(p2_text, (self.w - 200, 20))

    def handle_event(self, event):
        # 处理战斗中的按键 (比如 A/D 移动，J 攻击等)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # 后面可以写返回主菜单逻辑
                pass