# Ditu/manager.py
import pygame
import math
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from Jue_se.illusioner import Illusioner 
from Jue_se.creeper import Creeper
from Jue_se.skeleton import Skeleton
from Jue_se.zombie import Zombie
from Jue_se.enderman import Enderman
from Jue_se.mao_die import MaoDie
from Jue_se.drowned import Drowned
from Jue_se.drowned_king import DrownedKing
from referee import Referee
from world import DirtShieldBlock
from entity import Particle

from .map_manager import MapManager 
from .desert_env import DesertEnvironment
from .weather_system import WeatherSystem
from .weather.speech import PRIORITY_HIGH
from Jue_se.mao_die.enchant_altar import EnchantAltar


ENCHANT_SPAWN_COUNT = 1

class LevelManager:
    def __init__(self, width, height, selected_chars=None, map_path="", target_size="中"):
        self.width = width
        self.height = height
        
        self.fighters = []
        self.arrows = []
        self.drowned_king_tridents = []
        
        # 1. 雇佣地图管家
        self.map_mgr = MapManager(width, height)
        
        # 2. 安排出生点
        pad_x, pad_y = self.width // 6, self.height // 6
        spawn_points = [
            (pad_x, pad_y),                             
            (self.width - pad_x, pad_y),                
            (pad_x, self.height - pad_y),               
            (self.width - pad_x, self.height - pad_y),  
            (self.width // 2, self.height // 2),
            (self.width // 2, pad_y),
        ]
        
        # 3. 演员进场
        if selected_chars:
            for i, name in enumerate(selected_chars):
                if i >= len(spawn_points): break 
                pos = spawn_points[i]
                
                if name == "Zombie": self.fighters.append(Zombie(pos[0], pos[1]))
                elif name == "Skeleton": self.fighters.append(Skeleton(pos[0], pos[1]))
                elif name == "Illusioner": self.fighters.append(Illusioner(pos[0], pos[1]))
                elif name == "Creeper": self.fighters.append(Creeper(pos[0], pos[1]))
                elif name == "Enderman": self.fighters.append(Enderman(pos[0], pos[1]))
                elif name == "MaoDie": self.fighters.append(MaoDie(pos[0], pos[1]))
                elif name == "Drowned": self.fighters.append(Drowned(pos[0], pos[1], size=80))
                elif name == "DrownedKing": self.fighters.append(DrownedKing(pos[0], pos[1]))
                else: self.fighters.append(Creeper(pos[0], pos[1]))
            
            self.js = next((f for f in self.fighters if f.__class__.__name__ == "Zombie"), None)
            self.xb = next((f for f in self.fighters if f.__class__.__name__ == "Skeleton"), None)
            self.cp = next((f for f in self.fighters if f.__class__.__name__ == "Creeper"), None)
        else:
            self.cp = Creeper(150, 300)
            self.xb = Skeleton(850, 300)
            self.js = Zombie(512, 800)
            self.fighters = [self.cp, self.xb, self.js]

        is_desert = map_path and ("沙漠" in map_path or "沙漠地图.png" in map_path)
        is_ocean = map_path and ("海底" in map_path or "深海圣殿" in map_path)

        if is_ocean:
            self.map_mgr.generate_ocean_blocks(self.fighters)
        elif not is_desert:
            self.map_mgr.generate_blocks(self.fighters)
        else:
            self.map_mgr.allow_regenerate = False

        self.env_mechanics = None 
        if is_desert:
            safe_zones = [pygame.Rect(p[0]-100, p[1]-100, 200, 200) for p in spawn_points]
            for b in self.map_mgr.blocks: 
                safe_zones.append(b.rect)
            self.env_mechanics = DesertEnvironment(self.width, self.height, safe_zones, target_size)

        # 天气系统初始化（洞穴地图自动禁用，沙漠地图允许沙尘暴，海底神殿禁用天气）
        self.weather = WeatherSystem(self.width, self.height, map_path, is_desert=is_desert)
        if is_ocean:
            self.weather.torch_sprite = "海晶灯.png"
            self.weather.enabled = False

        self.enchant_altar = None
        has_mao_die = any(f.__class__.__name__ == "MaoDie" for f in self.fighters)
        if has_mao_die:
            for _ in range(200):
                ax = random.randint(80, self.width - 80)
                ay = random.randint(80, self.height - 80)
                tr = pygame.Rect(ax, ay, 48, 48)
                blocked = False
                for b in self.map_mgr.blocks:
                    if tr.colliderect(b.rect.inflate(12, 12)):
                        blocked = True
                        break
                if blocked:
                    continue
                for f in self.fighters:
                    if tr.colliderect(f.rect.inflate(60, 60)):
                        blocked = True
                        break
                if not blocked:
                    self.enchant_altar = EnchantAltar(ax, ay)
                    break
            if not self.enchant_altar:
                ax = self.width // 2
                ay = self.height // 2
                self.enchant_altar = EnchantAltar(ax, ay)

    def _try_place_enderman_dirt(self, enderman):
        if not hasattr(enderman, "can_place_dirt_now") or not enderman.can_place_dirt_now():
            return

        threat = None
        nearest_dist = 999999
        ex, ey = enderman.rect.centerx, enderman.rect.centery

        for arrow in self.arrows:
            if not getattr(arrow, "active", False):
                continue
            dx = ex - arrow.rect.centerx
            dy = ey - arrow.rect.centery
            dist = math.hypot(dx, dy)
            if dist >= 360:
                continue

            if hasattr(arrow, "angle"):
                proj_speed = getattr(arrow, "speed", 0)
                avx = math.cos(arrow.angle) * proj_speed
                avy = math.sin(arrow.angle) * proj_speed
            else:
                avx = getattr(arrow, "vx", 0)
                avy = getattr(arrow, "vy", 0)

            closing_fast = (avx * dx + avy * dy) > 0
            if not closing_fast:
                continue

            if dist < nearest_dist:
                nearest_dist = dist
                threat = arrow

        if not threat:
            return

        if hasattr(threat, "angle"):
            proj_speed = getattr(threat, "speed", 0)
            vx = math.cos(threat.angle) * proj_speed
            vy = math.sin(threat.angle) * proj_speed
        else:
            vx = getattr(threat, "vx", 0.0)
            vy = getattr(threat, "vy", 0.0)
        v_norm = math.hypot(vx, vy) or 1.0
        nx, ny = vx / v_norm, vy / v_norm
        block_size = self.map_mgr.blocks[0].size if self.map_mgr.blocks else 50
        px = int(ex - nx * 58 - block_size / 2)
        py = int(ey - ny * 58 - block_size / 2)
        px = max(0, min(self.width - block_size, px))
        py = max(0, min(self.height - block_size, py))
        new_rect = pygame.Rect(px, py, block_size, block_size)

        for b in self.map_mgr.blocks:
            if getattr(b, "active", False) and new_rect.colliderect(b.rect.inflate(8, 8)):
                return
        for f in self.fighters:
            if f != enderman and f.hp > 0 and new_rect.colliderect(f.rect.inflate(6, 6)):
                return

        self.map_mgr.blocks.append(DirtShieldBlock(px, py, size=90))
        enderman.on_dirt_placed()

    def _get_closest_target(self, me):
        mao_die_boss = None
        for f in self.fighters:
            if f.__class__.__name__ == "MaoDie" and getattr(f, 'is_boss', lambda: False)():
                mao_die_boss = f
                break
        if mao_die_boss and me.__class__.__name__ != "MaoDie" and me.hp > 0:
            return mao_die_boss.rect

        closest = None
        min_d = 9999
        for f in self.fighters:
            if f != me and f.hp > 0:
                d = math.hypot(f.rect.centerx - me.rect.centerx, f.rect.centery - me.rect.centery)
                if d < min_d:
                    min_d = d; closest = f
        return closest.rect if closest else None

    def update(self):
        """核心物理与战斗循环"""
        self.fighters = [f for f in self.fighters if f.hp > 0
                         or getattr(f, '_phase2_pending', False)]
        
        cp_explosion_data = None
        cp_exploder = None  # 🌟 修复 1：记录是哪只苦力怕引发的爆炸
        
        new_fighters = [] 

        for f in self.fighters:
            res = None
            if f.__class__.__name__ in ["Zombie", "Illusioner", "IllusionerClone", "Enderman"]:
                res = f.update(self.fighters, self.width, self.height)
            elif f.__class__.__name__ == "Creeper":
                res = f.update(self._get_closest_target(f), self.width, self.height)
                if res: 
                    cp_explosion_data = res
                    cp_exploder = f
            elif f.__class__.__name__ == "Skeleton":
                f.update(self.width, self.height, self._get_closest_target(f), self.arrows)
            elif f.__class__.__name__ == "MaoDie":
                if self.enchant_altar and self.enchant_altar.active:
                    f.set_altar_target(self.enchant_altar.rect)
                else:
                    f.set_altar_target(None)
                res = f.update(self.fighters, self.width, self.height)

            if res:
                if "projectile" in res: self.arrows.append(res["projectile"])
                if "spawns" in res: new_fighters.extend(res["spawns"])
                if "push" in res:
                    push_target = res.get("push_target")
                    if push_target and push_target in self.fighters:
                        px, py = res["push"]
                        kb = getattr(push_target, 'kb_res', 0)
                        push_target.vx += px * (1.0 - kb)
                        push_target.vy += py * (1.0 - kb)
                if "target" in res and "damage" in res:
                    victim = res["target"]
                    if victim and victim in self.fighters:
                        dmg = res["damage"]
                        try:
                            victim.take_damage(dmg, attacker=f)
                        except TypeError:
                            victim.take_damage(dmg)
                        from entity import FloatText
                        victim.float_texts.append(FloatText(
                            victim.rect.centerx + random.randint(-15, 15),
                            victim.rect.top - 15 - random.randint(0, 25),
                            f"-{dmg}", (255, 255, 255)))
                        kb = getattr(victim, 'kb_res', 0)
                        victim.vx += (victim.rect.centerx - f.rect.centerx) * 0.1 * (1.0 - kb)
                        victim.vy += (victim.rect.centery - f.rect.centery) * 0.1 * (1.0 - kb)
                    if "second_damage" in res and victim and victim in self.fighters:
                        sdmg = res["second_damage"]
                        try:
                            victim.take_damage(sdmg, attacker=f)
                        except TypeError:
                            victim.take_damage(sdmg)
                        from entity import FloatText
                        victim.float_texts.append(FloatText(
                            victim.rect.centerx + random.randint(-15, 15),
                            victim.rect.top - 10 - random.randint(0, 20),
                            f"-{sdmg}", (255, 200, 100)))

        if new_fighters:
            self.fighters.extend(new_fighters)

        if self.env_mechanics:
            safe_rects = list(self.env_mechanics.base_safe_zones)
            for torch in self.weather.torches:
                if torch.active:
                    safe_rects.append(torch.rect)
            self.env_mechanics.base_safe_zones = safe_rects
            self.env_mechanics.update(self.fighters, self.map_mgr.blocks, self.map_mgr.particles)

        # 天气系统每帧更新
        self.weather.forbidden_rects = []
        if self.env_mechanics:
            for tnt in self.env_mechanics.tnts:
                if not tnt.exploded:
                    self.weather.forbidden_rects.append(tnt.rect)
        for torch in self.weather.torches:
            if torch.active:
                self.weather.forbidden_rects.append(torch.rect)
        for b in self.map_mgr.blocks:
            if b.active:
                self.weather.forbidden_rects.append(b.rect)
        self.weather.update()
        if self.weather.game_over:
            return

        if self.weather.pending_bubble_text:
            self.weather.pending_panel_text = self.weather.pending_bubble_text
            self.weather.pending_bubble_text = None

        for f in self.fighters:
            if getattr(f, '_pending_speech', None):
                if f.hp > 0:
                    self.weather.speech_bubble.set(f._pending_speech, f, duration=360, priority=PRIORITY_HIGH)
                f._pending_speech = None

        if not hasattr(self, '_poetic_timer'):
            self._poetic_timer = 0
            self._poetic_last = ""
        self._poetic_timer += 1

        if self.weather.enabled and self._poetic_timer >= 720:
            self._poetic_timer = 0
            if random.random() < 0.55:
                alive = [f for f in self.fighters if f.hp > 0 and not self.weather.speech_bubble.is_fighter_speaking(f) and not getattr(f, '_pending_speech', None)]
                if alive:
                    f = random.choice(alive)
                    try:
                        from Ditu.weather.constants import WeatherType
                        from i18n import get_text
                        wk = {
                            WeatherType.SUNNY: "sunny", WeatherType.CLOUDY: "cloudy",
                            WeatherType.OVERCAST: "overcast", WeatherType.LIGHT_RAIN: "light_rain",
                            WeatherType.MODERATE_RAIN: "moderate_rain", WeatherType.HEAVY_RAIN: "heavy_rain",
                            WeatherType.THUNDERSTORM: "thunderstorm", WeatherType.LIGHT_SNOW: "light_snow",
                            WeatherType.MODERATE_SNOW: "moderate_snow", WeatherType.HEAVY_SNOW: "heavy_snow",
                            WeatherType.FOG: "fog", WeatherType.SANDSTORM: "sandstorm",
                        }
                        k = wk.get(self.weather.current_weather, "sunny")
                        line = get_text("weather_same", k)
                        tries = 0
                        while line == self._poetic_last and tries < 10:
                            line = get_text("weather_same", k)
                            tries += 1
                        self._poetic_last = line
                        self.weather.speech_bubble.set(line, f, duration=200)
                    except Exception:
                        pass

        # 🌟 修复 3：处理苦力怕爆炸，供出真凶
        if cp_explosion_data:
            ex_x, ex_y = cp_explosion_data["x"], cp_explosion_data["y"]
            ex_radius, ex_mult = cp_explosion_data["radius"], cp_explosion_data["mult"]
            for f in self.fighters:
                if f.__class__.__name__ == "Creeper": continue 
                d = math.hypot(f.rect.centerx - ex_x, f.rect.centery - ex_y)
                if d < ex_radius:
                    try:
                        f.take_damage(20 * ex_mult, attacker=cp_exploder)
                    except TypeError:
                        f.take_damage(20 * ex_mult)
                    from entity import FloatText
                    f.float_texts.append(FloatText(
                        f.rect.centerx + random.randint(-15, 15),
                        f.rect.top - 10 - random.randint(0, 20),
                        f"-{20 * ex_mult}", (255, 140, 60)))
                    res = getattr(f, 'kb_res', 0)
                    force = (20 * ex_mult) * (1.0 - res)
                    f.vx += (f.rect.centerx - ex_x)/(d or 1) * force
                    f.vy += (f.rect.centery - ex_y)/(d or 1) * force

            for b in self.map_mgr.blocks:
                if b.active and math.hypot(b.rect.centerx - ex_x, b.rect.centery - ex_y) < ex_radius:
                    b.take_damage(999, self.map_mgr.particles)

        # 人物互碰
        for i in range(len(self.fighters)):
            for j in range(i + 1, len(self.fighters)):
                Referee.process_collision(self.fighters[i], self.fighters[j])

        # 小黑放泥土
        for f in self.fighters:
            if f.__class__.__name__ == "Enderman":
                self._try_place_enderman_dirt(f)
        
        # 人物撞方块
        for b in self.map_mgr.blocks:
            if b.active:
                b.update() 
                for f in self.fighters:
                    if Referee.process_collision(f, b): 
                        b.hit(self.map_mgr.particles) 
                        if f.__class__.__name__ != "Creeper" and hasattr(f, 'play_bounce_sfx'):
                            f.play_bounce_sfx()

        # 人物穿过火把（无碰撞，遮挡光源）
        for t in self.weather.torches:
            if t.active:
                for f in self.fighters:
                    if f.hp > 0 and t.rect.colliderect(f.rect):
                        if getattr(t, 'has_collision', False):
                            t.active = False
                            self.map_mgr.particles.append(Particle(t.rect.centerx, t.rect.centery, (80, 200, 160), speed_mult=1.8))
                            self.map_mgr.particles.append(Particle(t.rect.centerx, t.rect.centery, (80, 200, 160), speed_mult=1.8))
                        else:
                            t.blocked_timer = 10
                        break

        # 箭矢逻辑
        for arrow in self.arrows[:]:
            arrow.update()
            for f in self.fighters:
                is_immune = False
                if f.__class__.__name__ == "Skeleton" and arrow.__class__.__name__ != "MagicOrb": is_immune = True
                if f.__class__.__name__ in ["Illusioner", "IllusionerClone"] and arrow.__class__.__name__ == "MagicOrb": is_immune = True
                
                if not is_immune and arrow.active and arrow.rect.colliderect(f.rect):
                    arrow_shooter = getattr(arrow, 'shooter', None)
                    try:
                        f.take_damage(arrow.damage, attacker=arrow_shooter)
                    except TypeError:
                        f.take_damage(arrow.damage)
                    from entity import FloatText
                    f.float_texts.append(FloatText(
                        f.rect.centerx + random.randint(-10, 10),
                        f.rect.top - 10 - random.randint(0, 20),
                        f"-{arrow.damage}", (255, 255, 255)))
                    kb_power = getattr(arrow, 'knockback', 2) 
                    res = getattr(f, 'kb_res', 0)
                    if hasattr(arrow, 'angle'):
                        f.vx += math.cos(arrow.angle) * kb_power * (1.0 - res)
                        f.vy += math.sin(arrow.angle) * kb_power * (1.0 - res)
                    else:
                        f.vx += (arrow.vx / (arrow.speed or 1)) * kb_power * (1.0 - res)
                    arrow.active = False
                    break 
            
            # 射击通用地图方块
            for b in self.map_mgr.blocks:
                if arrow.active and b.active and arrow.rect.colliderect(b.rect):
                    b.take_damage(1, self.map_mgr.particles)
                    arrow.active = False
                    
            # 让沙漠场景生成的墙壁（砂岩、发射器）也能挡住箭矢
            if self.env_mechanics and arrow.active:
                solid_blocks = self.env_mechanics.blocks + self.env_mechanics.dispensers
                for sb in solid_blocks:
                    if arrow.rect.colliderect(sb.rect):
                        arrow.active = False
                        from .desert_env import DustParticle
                        for _ in range(3):
                            self.env_mechanics.particles.append(DustParticle(arrow.rect.centerx, arrow.rect.centery))
                        break

            if not arrow.active: 
                self.arrows.remove(arrow)

        if self.enchant_altar and self.enchant_altar.active:
            self.enchant_altar.update()
            for f in self.fighters:
                if f.__class__.__name__ == "MaoDie" and f.hp > 0:
                    if self.enchant_altar.rect.colliderect(f.rect):
                        f.apply_enchant_buff()
                        self.enchant_altar.active = False

        torch_rects = [t.rect for t in self.weather.torches if t.active]
        self.map_mgr.update(self.fighters, torch_rects)

    def draw_all(self, surface):
        """让所有实体把自己画到画布上"""
        # 第 0 层：天气的天空色和云层（画在角色下方）
        self.weather.draw_bottom(surface)

        if self.env_mechanics: 
            self.env_mechanics.draw_bottom(surface)

        self.map_mgr.draw(surface)
        
        for f in self.fighters: f.draw(surface)
        for arrow in self.arrows: arrow.draw(surface)
        for trident in getattr(self, "drowned_king_tridents", []): trident.draw(surface)

        if self.enchant_altar and self.enchant_altar.active:
            self.enchant_altar.draw(surface)

        if self.env_mechanics: 
            self.env_mechanics.draw_top(surface)

        # 最顶层：雨、雪、雾、沙尘、闪电（覆盖在角色上方）
        self.weather.draw_top(surface)
