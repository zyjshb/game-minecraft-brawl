# config.py
import pygame
import os
import json

BASE_DIR = os.path.dirname(__file__)
FONT_PATH = os.path.join(BASE_DIR, "Fonts", "WenQuanWeiMiHei-1.ttf")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")

_settings = {}

def _load_settings():
    global _settings
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                _settings = json.load(f)
    except Exception:
        _settings = {}

def _save_settings():
    global _settings
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(_settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_setting(key, default=None):
    return _settings.get(key, default)

def set_setting(key, value):
    global _settings
    _settings[key] = value
    _save_settings()

_load_settings()

SKIP_BOSS_INTRO = get_setting("skip_boss_intro", False)

def get_font(size):
    """一键获取字体的魔法函数"""
    try:
        return pygame.font.Font(FONT_PATH, size)
    except:
        # 如果字体文件炸了，保底用系统字体
        return pygame.font.SysFont(["simhei", "WenQuanWeiMiHei-1.ttf"], size)