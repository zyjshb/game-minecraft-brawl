# world.py
import pygame
import os
import random
from entity import Particle  # 🌟 核心：把 entity 里做好的粒子类引进来

BASE_DIR = os.path.dirname(__file__)
SPRITES_DIR = os.path.join(BASE_DIR, "Sprites")
SFX_JIAOHU_DIR = os.path.join(BASE_DIR, "SFX", "jiao-hu")

# 全局加载音效，避免每个方块重复加载占用内存
hit_sounds = []

def load_jiao_hu_sounds():
    if hit_sounds: return
    try:
        for i in range(1, 4):
            path = os.path.join(SFX_JIAOHU_DIR, f"矿石破坏音效{i}.mp3")
            hit_sounds.append(pygame.mixer.Sound(path))
    except Exception as e:
        print(f"交互音效加载失败: {e}")

class MineralBlock:
    def __init__(self, x, y, name, size=50):
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.active = True
        self.name = name
        
        # --- 撞击破坏逻辑参数 ---
        self.hp = 3 # 撞 3 下就碎
        self.hit_cooldown = 0 # 受击冷却倒计时
        
        # 🌟 核心1：定义矿石的专属喷射颜色
        self.COLOR_MAP = {
            "铁矿石": (198, 175, 150),   # 浅棕色
            "砖石矿": (0, 255, 255),     # 青色亮片
            "金矿": (255, 215, 0),       # 金色闪粉
            "石头": (150, 150, 150),     # 灰暗石灰
            "青金石": (0, 0, 139)        # 深邃蓝粉
        }
        # 匹配颜色，没匹配到就默认灰色
        self.particle_color = self.COLOR_MAP.get(name, (150, 150, 150))
        
        load_jiao_hu_sounds()
        
        try:
            img_path = os.path.join(SPRITES_DIR, f"{name}.png")
            self.image = pygame.transform.scale(pygame.image.load(img_path).convert_alpha(), (size, size))
        except:
            self.image = pygame.Surface((size, size))
            self.image.fill((150, 150, 150))

    def update(self):
        """每一帧调用，用来减少冷却时间"""
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

    def hit(self, global_particle_list=None):
        """处理被角色撞击的逻辑"""
        if not self.active or self.hit_cooldown > 0:
            return
        
        self.hp -= 1
        self.hit_cooldown = 30 
        
        if hit_sounds:
            random.choice(hit_sounds).play()
            
        # 🌟 核心2：撞击时的粒子反馈
        if global_particle_list is not None:
            # 如果这下撞碎了，爆 12 个大碎屑；如果没碎，掉 3 个小碎屑
            num_shards = random.randint(10, 15) if self.hp <= 0 else random.randint(2, 4)
            # 碎裂瞬间的冲击力（碎了就喷得远一点）
            speed_m = 1.5 if self.hp <= 0 else 0.5
            
            for _ in range(num_shards):
                px = self.rect.centerx + random.randint(-10, 10)
                py = self.rect.centery + random.randint(-10, 10)
                new_particle = Particle(px, py, self.particle_color, speed_mult=speed_m)
                global_particle_list.append(new_particle)
            
        if self.hp <= 0:
            self.active = False
            print(f"{self.name} 被撞碎了！")

    def take_damage(self, amount, global_particle_list=None):
        """处理被苦力怕炸毁、或被箭矢射坏的逻辑"""
        if not self.active:
            return
        
        self.hp -= amount
        
        if self.hp <= 0:
            self.active = False
            print(f"{self.name} 灰飞烟灭了！")
            
            # 🌟 核心3：被炸毁时爆出超大范围的核爆碎屑
            if global_particle_list is not None:
                for _ in range(random.randint(15, 25)):
                    px = self.rect.centerx + random.randint(-15, 15)
                    py = self.rect.centery + random.randint(-15, 15)
                    # 爆炸的威力极大，碎屑横飞
                    new_particle = Particle(px, py, self.particle_color, speed_mult=2.5)
                    global_particle_list.append(new_particle)

    def draw(self, surface):
        if self.active:
            surface.blit(self.image, self.rect)


class PrismarineBlock(MineralBlock):
    def __init__(self, x, y, size=48):
        super().__init__(x, y, "海晶石", size=size)
        self.COLOR_MAP["海晶石"] = (80, 200, 160)
        self.particle_color = (80, 200, 160)
        try:
            img_path = os.path.join(SPRITES_DIR, "海晶石.png")
            self.image = pygame.transform.scale(pygame.image.load(img_path).convert_alpha(), (size, size))
        except Exception:
            pass


class DirtShieldBlock:
    """小黑临时放置的泥土护盾：只挡一发远程后消散。"""
    def __init__(self, x, y, size=70):
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.active = True
        self.hp = 1
        self.hit_cooldown = 0
        self.name = "泥土护盾"
        self.particle_color = (120, 90, 60)
        try:
            img_path = os.path.join(SPRITES_DIR, "泥土.png")
            raw_img = pygame.image.load(img_path).convert_alpha()
            self.image = pygame.transform.scale(raw_img, (size, size))
        except Exception:
            self.image = pygame.Surface((size, size))
            self.image.fill((120, 90, 60))

    def update(self):
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

    def hit(self, global_particle_list=None):
        # 近战撞击只产生阻挡效果，不消耗护盾。
        return

    def take_damage(self, amount, global_particle_list=None):
        if not self.active:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.active = False
            if global_particle_list is not None:
                for _ in range(random.randint(10, 16)):
                    px = self.rect.centerx + random.randint(-10, 10)
                    py = self.rect.centery + random.randint(-10, 10)
                    global_particle_list.append(Particle(px, py, self.particle_color, speed_mult=1.1))

    def draw(self, surface):
        if self.active:
            surface.blit(self.image, self.rect)

# （GoldenArrowPickup 的代码我原封不动保留了，虽然现在大乱斗里用不上了，但留着不影响）
class GoldenArrowPickup:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.active = True
        try:
            orig_img = pygame.image.load(os.path.join(SPRITES_DIR, "灵光箭.png")).convert_alpha()
            scaled = pygame.transform.scale(orig_img, (50, 50))
            self.image = pygame.transform.rotate(scaled, -45)
        except:
            self.image = pygame.Surface((40, 40))
            self.image.fill((255, 215, 0))

    def draw(self, surface):
        if self.active:
            surface.blit(self.image, self.rect)