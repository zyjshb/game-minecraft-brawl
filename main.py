# main.py
import pygame
import os
import sys

sys.path.append(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(__file__)

import audio_manager
from i18n import t
import config

NAME_MAP_KEYS = {
    "Zombie": "zombie",
    "Skeleton": "skeleton",
    "Creeper": "creeper",
    "Illusioner": "illusioner",
    "Enderman": "enderman",
    "MaoDie": "maodie",
}

def get_character_name(raw_name):
    key = NAME_MAP_KEYS.get(raw_name)
    if key:
        return t(key)
    return raw_name

def _draw_globe_icon(surface, rect, color):
    """在给定rect内绘制地球图标"""
    import math
    cx, cy = rect.center
    r = min(rect.width, rect.height) // 2 - 6
    # 地球圆体
    pygame.draw.circle(surface, color, (cx, cy), r, width=2)
    # 赤道（水平椭圆）
    eq_rect = pygame.Rect(cx - r, cy - r // 3, r * 2, r * 2 // 3)
    pygame.draw.ellipse(surface, color, eq_rect, width=1)
    # 经线（垂直椭圆）
    mid_rect = pygame.Rect(cx - r // 3, cy - r, r * 2 // 3, r * 2)
    pygame.draw.ellipse(surface, color, mid_rect, width=1)
    # 上方纬线弧
    top_rect = pygame.Rect(cx - r + 2, cy - r + 3, r * 2 - 4, r * 2 - 6)
    pygame.draw.arc(surface, color, top_rect, math.pi * 0.15, math.pi * 0.85, width=1)
    # 下方纬线弧
    bot_rect = pygame.Rect(cx - r + 2, cy - r - 3, r * 2 - 4, r * 2 - 6)
    pygame.draw.arc(surface, color, bot_rect, math.pi * 1.15, math.pi * 1.85, width=1)

from config import get_font
from Jue_se.zombie import Zombie
from Jue_se.skeleton import Skeleton
from Jue_se.creeper import Creeper
from Ditu.mine_level import BattleLevel
from Ditu.boss_level import BossLevel, BOSS_NAME_BY_MAP
from Scenes.start_menu import StartMenu
from Scenes.char_select import CharacterSelect
from Scenes.map_select import MapSelect 
from Scenes.button import Button 
from Scenes.brawl_setup import BrawlSetup 
from Jue_se.illusioner import Illusioner
from Scenes.map_size import MapSizeSelect  
from Jue_se.enderman import Enderman
from Scenes.overlay import SettingsOverlay
from Scenes.lang_select import LanguageSelect
from Scenes.difficulty_select import DifficultySelect
from Scenes.boss_buff_select import BossBuffSelect

WIDTH, HEIGHT = 1920, 1080

_global_scale = 1.0
_global_offset_x = 0
_global_offset_y = 0
_original_get_pos = pygame.mouse.get_pos

def _mapped_get_pos():
    mx, my = _original_get_pos()
    lx = int((mx - _global_offset_x) / _global_scale)
    ly = int((my - _global_offset_y) / _global_scale)
    return (lx, ly)

pygame.mouse.get_pos = _mapped_get_pos

def main():
    global _global_scale, _global_offset_x, _global_offset_y 

    pygame.init()
    pygame.mixer.init()
    # 关闭 SDL 文本输入，避免输入法组合态吞掉方向键
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()
    MUSIC_END_EVENT = pygame.USEREVENT + 1
    audio_manager.init_audio(BASE_DIR, MUSIC_END_EVENT)
    screen = pygame.display.set_mode((1280, 720))
    canvas = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("Minecraft Brawl: 极简稳定版")
    clock = pygame.time.Clock()

    ui_dir = os.path.join(BASE_DIR, "Scenes", "UI")
    try:
        if os.path.exists(os.path.join(ui_dir, "齿轮.png")):
            gear_raw = pygame.image.load(os.path.join(ui_dir, "齿轮.png")).convert_alpha()
        else:
            gear_raw = pygame.image.load(os.path.join(ui_dir, "齿轮.jpg")).convert()
            gear_raw.set_colorkey((0, 0, 0)) 
    except Exception as e:
        print(f"齿轮加载失败: {e}")
        gear_raw = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(gear_raw, (150, 150, 150), (50, 50), 50)
        
    rw, rh = gear_raw.get_size()
    min_dim = min(rw, rh)
    crop_rect = pygame.Rect((rw - min_dim)//2, (rh - min_dim)//2, min_dim, min_dim)
    gear_square = gear_raw.subsurface(crop_rect).copy()

    gear_size = 80
    gear_surf = pygame.transform.smoothscale(gear_square, (gear_size, gear_size))
    
    gear_x = WIDTH - gear_size - 40 
    gear_y = 40 
    gear_rect = pygame.Rect(gear_x, gear_y, gear_size, gear_size)

    mute_btn_rect = pygame.Rect(gear_x + 16, gear_y + gear_size + 10, 48, 48)
    globe_rect = pygame.Rect(gear_x + 16, gear_y + gear_size + 64, 48, 48)

    gear_angle = 0
    is_gear_rotating = False

    overlay = SettingsOverlay(WIDTH, HEIGHT)
    lang_scene = LanguageSelect(WIDTH, HEIGHT)
    lang_active = False

    menu_scene = StartMenu(WIDTH, HEIGHT)
    brawl_setup_scene = BrawlSetup(WIDTH, HEIGHT) 
    select_scene = CharacterSelect(WIDTH, HEIGHT, 2) 
    map_scene = MapSelect(WIDTH, HEIGHT)
    boss_map_scene = MapSelect(WIDTH, HEIGHT, boss_mode=True)
    size_scene = MapSizeSelect(WIDTH, HEIGHT) 
    
    btn_restart = Button(0, 0, 200, 60, "", i18n_key="btn_restart")
    btn_menu = Button(0, 0, 200, 60, "", i18n_key="btn_main_menu")
    btn_quit_game = Button(0, 0, 200, 60, "", i18n_key="btn_quit_game") 
    
    current_level = None
    state = "MENU"
    player_selections = None 
    current_players = 2 
    final_path = None 
    match_over = False    
    fade_alpha = 0        
    font_title = get_font(50)
    settlement_sfx_played = False
    prev_state = state
    is_boss_mode = False
    boss_pick = None
    boss_diff = None
    diff_scene = None
    buff_scene = None
    boss_buffs = None
    boss_loading_needs_create = False
    boss_loading_all_chars = None
    boss_sfx_cleanup = False

    running = True
    while running:
        win_w, win_h = screen.get_size()
        _global_scale = min(win_w / WIDTH, win_h / HEIGHT)
        new_w = int(WIDTH * _global_scale)
        new_h = int(HEIGHT * _global_scale)
        _global_offset_x = (win_w - new_w) // 2
        _global_offset_y = (win_h - new_h) // 2

        phy_mx, phy_my = _original_get_pos()
        log_mx = int((phy_mx - _global_offset_x) / _global_scale)
        log_my = int((phy_my - _global_offset_y) / _global_scale)
        mouse_pos_log = (log_mx, log_my)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: running = False
            if event.type == MUSIC_END_EVENT and audio_manager.audio:
                audio_manager.audio.handle_music_end_event()

            log_event = None
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                new_dict = event.dict.copy()
                new_dict['pos'] = mouse_pos_log
                log_event = pygame.event.Event(event.type, new_dict)
            else:
                log_event = event

            # MAP 场景输入硬隔离：先于所有全局逻辑执行
            if state == "MAP":
                if hasattr(pygame.key, "stop_text_input"):
                    pygame.key.stop_text_input()
                kp_left = getattr(pygame, "K_KP_LEFT", None)
                kp_right = getattr(pygame, "K_KP_RIGHT", None)
                allowed_keys = {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_KP4, pygame.K_KP6, pygame.K_SPACE, pygame.K_RETURN}
                if kp_left is not None:
                    allowed_keys.add(kp_left)
                if kp_right is not None:
                    allowed_keys.add(kp_right)

                if log_event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    continue
                if log_event.type in (pygame.TEXTINPUT, pygame.TEXTEDITING):
                    continue
                if log_event.type == pygame.KEYDOWN:
                    if log_event.key in allowed_keys:
                        map_scene.handle_event(log_event)
                    continue
                if log_event.type == pygame.KEYUP:
                    continue

            # 全局快捷键
            if log_event.type == pygame.KEYDOWN:
                if log_event.key == pygame.K_F11:
                    is_fullscreen = screen.get_flags() & pygame.FULLSCREEN
                    if is_fullscreen: screen = pygame.display.set_mode((1280, 720))
                    else: screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                if log_event.key == pygame.K_ESCAPE:
                    if not overlay.active:
                        overlay.activate()
                        is_gear_rotating = True
                    else:
                        overlay.deactivate()
                        is_gear_rotating = True
                if log_event.key == pygame.K_m and (log_event.key.get_mods() & pygame.KMOD_CTRL):
                    pygame.display.iconify()

            # 🌟 重点防穿透逻辑：记住开始时的状态
            overlay_was_active = overlay.active
            gear_clicked = False

            # 齿轮点击判断
            if log_event.type == pygame.MOUSEBUTTONDOWN and log_event.button == 1:
                if gear_rect.collidepoint(mouse_pos_log):
                    gear_clicked = True
                    if not overlay.active:
                        overlay.activate() 
                        is_gear_rotating = True 
                    else:
                        overlay.deactivate() 
                        is_gear_rotating = True
                elif mute_btn_rect.collidepoint(mouse_pos_log):
                    if audio_manager.audio:
                        audio_manager.audio.toggle_music_mute()
                elif globe_rect.collidepoint(mouse_pos_log):
                    lang_active = not lang_active
                    if lang_active:
                        lang_scene._build_buttons() 

            # 处理 Overlay 按钮
            if overlay.active and not gear_clicked:
                result = overlay.handle_event(log_event, mouse_pos_log)
                if result == "RESUME":
                    is_gear_rotating = True 
                elif result == "BACK_TO_MENU":
                    if current_level:
                        if not is_boss_mode and hasattr(current_level, 'manager') and hasattr(current_level.manager, 'weather'):
                            current_level.manager.weather.destroy()
                    was_boss = is_boss_mode
                    was_playing_boss = was_boss and current_level is not None
                    state = "MENU"
                    current_level = None
                    is_boss_mode = False
                    boss_pick = None
                    boss_diff = None
                    boss_buffs = None
                    buff_scene = None
                    if audio_manager.audio:
                        if was_playing_boss:
                            audio_manager.audio.restore_normal_music()
                            boss_sfx_cleanup = True
                        else:
                            audio_manager.audio.set_ingame(False, fade_ms=0)
                    is_gear_rotating = True

            if lang_active and not gear_clicked:
                result = lang_scene.handle_event(log_event, mouse_pos_log)
                if result == "BACK":
                    lang_active = False 

            # 🌟🌟🌟 终极防火墙：如果覆盖层正开着，或者刚刚被点关掉，立刻跳过当前事件！
            if overlay_was_active or overlay.active or gear_clicked or lang_active:
                continue

            # 剩下的就是正常的底层游戏逻辑，上面的 continue 保证了它们绝不会被打扰
            if state == "MENU":
                mode = menu_scene.handle_event(log_event)
                if mode == "MODE_1V1": 
                    current_players = 2
                    select_scene = CharacterSelect(WIDTH, HEIGHT, current_players)
                    state = "SELECT"
                elif mode == "MODE_BRAWL": state = "BRAWL_SETUP"
                elif mode == "MODE_BOSS":
                    is_boss_mode = True
                    boss_sfx_cleanup = False
                    boss_pick = None
                    boss_diff = None
                    boss_buffs = None
                    buff_scene = None
                    boss_map_scene.__init__(WIDTH, HEIGHT, boss_mode=True)
                    state = "MAP_BOSS"
                elif mode == "QUIT": running = False
            
            elif state == "BRAWL_SETUP":
                num = brawl_setup_scene.handle_event(log_event)
                if num == "BACK": state = "MENU"
                elif num:
                    current_players = num
                    select_scene = CharacterSelect(WIDTH, HEIGHT, current_players)
                    state = "SELECT"

            elif state == "SELECT":
                selections = select_scene.handle_event(log_event)
                if selections:
                    player_selections = selections
                    map_scene.__init__(WIDTH, HEIGHT) 
                    state = "MAP"

            elif state == "SELECT_CHALLENGERS":
                selections = select_scene.handle_event(log_event)
                if selections:
                    player_selections = selections
                    if diff_scene is None:
                        diff_scene = DifficultySelect(WIDTH, HEIGHT)
                    state = "BOSS_DIFFICULTY"

            elif state == "BOSS_DIFFICULTY":
                result = diff_scene.handle_event(log_event)
                if result:
                    boss_diff = result
                    buff_scene = BossBuffSelect(WIDTH, HEIGHT, boss_diff)
                    state = "BOSS_BUFF"

            elif state == "BOSS_BUFF":
                buff_scene.handle_event(log_event)
                if buff_scene.done:
                    boss_buffs = buff_scene.picked
                    boss_loading_all_chars = [boss_pick] + player_selections
                    boss_loading_needs_create = True
                    state = "BOSS_LOADING"
                    boss_loading_start = pygame.time.get_ticks()
                    boss_loading_countdown = 3
                    if audio_manager.audio:
                        boss_music = os.path.join(BASE_DIR, "Boss", "Music", "5.wav")
                        audio_manager.audio.play_boss_music(boss_music)
            
            elif state == "MAP":
                map_scene.handle_event(log_event)

            elif state == "MAP_BOSS":
                boss_map_scene.handle_event(log_event)

            elif state == "MAP_SIZE":
                new_size = size_scene.handle_event(log_event)
                if new_size:
                    current_level = BattleLevel(canvas, final_path, player_selections, target_size=new_size)
                    match_over = False
                    fade_alpha = 0
                    settlement_sfx_played = False
                    if audio_manager.audio:
                        audio_manager.audio.set_ingame(True, fade_ms=0)
                    state = "PLAY"

            elif state == "PLAY":
                if not match_over:
                    if current_level: current_level.handle_event(log_event)
                else:
                    if btn_restart.is_clicked(log_event): 
                        if is_boss_mode:
                            if current_level: current_level.manager.weather.destroy()
                            if audio_manager.audio:
                                audio_manager.audio.restore_normal_music()
                                audio_manager.audio.stop_all_sfx()
                            boss_diff = None
                            boss_buffs = None
                            buff_scene = None
                            boss_map_scene.__init__(WIDTH, HEIGHT, boss_mode=True)
                            state = "MAP_BOSS"
                        else:
                            if current_level: current_level.manager.weather.destroy()
                            if audio_manager.audio: audio_manager.audio.set_ingame(False, fade_ms=0)
                            select_scene = CharacterSelect(WIDTH, HEIGHT, current_players)
                            state = "SELECT"
                    elif btn_menu.is_clicked(log_event):
                        if current_level: current_level.manager.weather.destroy()
                        if audio_manager.audio:
                            if is_boss_mode:
                                audio_manager.audio.restore_normal_music()
                                boss_sfx_cleanup = True
                            else:
                                audio_manager.audio.set_ingame(False, fade_ms=0)
                        is_boss_mode = False
                        state = "MENU"
                    elif btn_quit_game.is_clicked(log_event): running = False
                    
                    if log_event.type == pygame.KEYDOWN:
                        if log_event.key == pygame.K_r:
                            if is_boss_mode:
                                if current_level: current_level.manager.weather.destroy()
                                if audio_manager.audio:
                                    audio_manager.audio.restore_normal_music()
                                    audio_manager.audio.stop_all_sfx()
                                boss_diff = None
                                boss_buffs = None
                                buff_scene = None
                                boss_map_scene.__init__(WIDTH, HEIGHT, boss_mode=True)
                                state = "MAP_BOSS"
                            else:
                                if current_level: current_level.manager.weather.destroy()
                                if audio_manager.audio: audio_manager.audio.set_ingame(False, fade_ms=0)
                                select_scene = CharacterSelect(WIDTH, HEIGHT, current_players)
                                state = "SELECT"
                        elif log_event.key == pygame.K_m and not (log_event.key.get_mods() & pygame.KMOD_CTRL):
                            if current_level: current_level.manager.weather.destroy()
                            if audio_manager.audio:
                                if is_boss_mode:
                                    audio_manager.audio.restore_normal_music()
                                    boss_sfx_cleanup = True
                                else:
                                    audio_manager.audio.set_ingame(False, fade_ms=0)
                            is_boss_mode = False
                            state = "MENU"

        # --- 渲染与调度 ---
        if boss_sfx_cleanup and state == "MENU" and audio_manager.audio:
            audio_manager.audio.stop_all_sfx()
            boss_sfx_cleanup = False

        # MAP->MAP_SIZE should not depend on user input events.
        if state == "MAP":
            temp_path = map_scene.get_final_map()
            if temp_path:
                final_path = temp_path
                state = "MAP_SIZE"

        if state == "MAP_BOSS":
            temp_path = boss_map_scene.get_final_map()
            if temp_path:
                final_path = temp_path
                boss_pick = BOSS_NAME_BY_MAP.get(os.path.basename(temp_path), "DrownedKing")
                current_players = 5
                select_scene = CharacterSelect(WIDTH, HEIGHT, 5)
                state = "SELECT_CHALLENGERS"

        if not overlay.active:
            if is_gear_rotating:
                gear_angle -= 15
                if gear_angle <= -360:
                    gear_angle = 0
                    is_gear_rotating = False 

            if state == "PLAY" and current_level:
                if not match_over:
                    current_level.update() 
                if is_boss_mode:
                    boss_cls = getattr(current_level, "_boss_char", "DrownedKing")
                    alive = [f for f in current_level.fighters if f.hp > 0 and f.__class__.__name__ != boss_cls]
                    boss = any(f.hp > 0 and f.__class__.__name__ == boss_cls for f in current_level.fighters)
                    if not alive or not boss or current_level.time_up:
                        match_over = True
                        if not settlement_sfx_played and audio_manager.audio:
                            audio_manager.audio.play_settlement()
                            settlement_sfx_played = True
                else:
                    real_fighters = [f for f in current_level.fighters if f.__class__.__name__ != "IllusionerClone"]
                    if len(real_fighters) <= 1 or current_level.time_up:
                        match_over = True
                        if not settlement_sfx_played and audio_manager.audio:
                            audio_manager.audio.play_settlement()
                            settlement_sfx_played = True
                if match_over and fade_alpha < 180:
                    fade_alpha += 4

            if state == "BOSS_LOADING":
                elapsed = (pygame.time.get_ticks() - boss_loading_start) / 1000
                boss_loading_countdown = max(0, 3 - int(elapsed))
                if boss_loading_countdown <= 0:
                    state = "PLAY"

        if boss_loading_needs_create:
            boss_loading_needs_create = False
            current_level = BossLevel(canvas, final_path, boss_loading_all_chars, difficulty=boss_diff, buffs=boss_buffs)
            if not config.SKIP_BOSS_INTRO and current_level.intro_phase:
                current_level.intro_timer = 150
            match_over = False
            fade_alpha = 0
            settlement_sfx_played = False

        if state == "MENU": menu_scene.update_and_draw(canvas)
        elif state == "BRAWL_SETUP": brawl_setup_scene.update_and_draw(canvas) 
        elif state in ("SELECT", "SELECT_CHALLENGERS"): select_scene.update_and_draw(canvas)
        elif state == "MAP": map_scene.update_and_draw(canvas)
        elif state == "MAP_BOSS": boss_map_scene.update_and_draw(canvas)
        elif state == "MAP_SIZE": size_scene.update_and_draw(canvas)
        elif state == "BOSS_DIFFICULTY": diff_scene.update_and_draw(canvas) if diff_scene else None
        elif state == "BOSS_BUFF" and buff_scene:
            buff_scene.update()
            buff_scene.update_and_draw(canvas)
        elif state == "BOSS_LOADING":
            canvas.fill((10, 12, 20))
            load_bg = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            load_bg.fill((0, 0, 0, 180))
            canvas.blit(load_bg, (0, 0))
            load_title = font_title.render(t("loading_boss"), True, (255, 215, 0))
            canvas.blit(load_title, load_title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
            cd_text = str(boss_loading_countdown)
            cd_surf = font_title.render(cd_text, True, (255, 255, 255))
            canvas.blit(cd_surf, cd_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))
            ready = get_font(28).render(t("loading_ready"), True, (200, 200, 200))
            canvas.blit(ready, ready.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120)))
        elif state == "PLAY":
            if current_level: current_level.draw() 
            
            if match_over and fade_alpha > 0:
                overlay_sf = pygame.Surface((WIDTH, HEIGHT))
                overlay_sf.set_alpha(fade_alpha)
                overlay_sf.fill((0, 0, 0))
                canvas.blit(overlay_sf, (0, 0))
                
                if fade_alpha >= 150:
                    if is_boss_mode:
                        boss_cls = getattr(current_level, "_boss_char", "DrownedKing")
                        alive = [f for f in current_level.fighters if f.hp > 0 and f.__class__.__name__ != boss_cls]
                        boss_alive = any(f.hp > 0 and f.__class__.__name__ == boss_cls for f in current_level.fighters)
                        if alive and not boss_alive:
                            title = t("boss_clear")
                        else:
                            title = t("boss_fail")
                    else:
                        winner_name = t("draw")
                        real_fighters = [f for f in current_level.fighters if f.__class__.__name__ != "IllusionerClone"]
                        if len(real_fighters) == 1:
                            raw_name = real_fighters[0].__class__.__name__
                            winner_name = get_character_name(raw_name)
                        title = t("battle_over").replace("{name}", winner_name)
                    title_surf = font_title.render(title, True, (255, 215, 0))
                    canvas.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))
                    
                    btn_restart.rect.center = (WIDTH // 2, HEIGHT // 2 - 20)
                    btn_menu.rect.center = (WIDTH // 2, HEIGHT // 2 + 60)
                    btn_quit_game.rect.center = (WIDTH // 2, HEIGHT // 2 + 140)
                    btn_restart.draw(canvas); btn_menu.draw(canvas); btn_quit_game.draw(canvas)

        if overlay.active:
            overlay.update_and_draw(canvas)

        if lang_active:
            lang_scene.update_and_draw(canvas)

        rotated_gear_surf = pygame.transform.rotate(gear_surf, gear_angle)
        new_gear_rect = rotated_gear_surf.get_rect(center=gear_rect.center)
        canvas.blit(rotated_gear_surf, new_gear_rect)

        muted = audio_manager.audio.is_music_muted() if audio_manager.audio else False
        btn_color = (200, 70, 70) if muted else (100, 190, 100)
        pygame.draw.rect(canvas, (30, 30, 40, 180), mute_btn_rect, border_radius=10)
        pygame.draw.rect(canvas, btn_color, mute_btn_rect, width=2, border_radius=10)
        btn_label = get_font(22).render("♪" if not muted else "✕", True, btn_color)
        canvas.blit(btn_label, btn_label.get_rect(center=mute_btn_rect.center))

        pygame.draw.rect(canvas, (30, 30, 40, 180), globe_rect, border_radius=10)
        globe_color = (120, 180, 240) if lang_active else (100, 160, 220)
        pygame.draw.rect(canvas, globe_color, globe_rect, width=2, border_radius=10)
        _draw_globe_icon(canvas, globe_rect, globe_color)

        screen.fill((0, 0, 0)) 
        scaled_canvas = pygame.transform.smoothscale(canvas, (new_w, new_h))
        screen.blit(scaled_canvas, (_global_offset_x, _global_offset_y))
        
        pygame.display.flip()
        clock.tick(60)

        # Apply in-game music ducking based on state
        if state != prev_state:
            prev_state = state

        if audio_manager.audio:
            audio_manager.audio.update()

    pygame.quit()

if __name__ == "__main__":
    main()
