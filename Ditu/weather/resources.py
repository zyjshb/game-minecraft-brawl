import os


def get_project_base_dir():
    # Ditu/weather/resources.py -> project root
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def get_weather_sfx_dir():
    return os.path.join(get_project_base_dir(), "SFX", "Weather system sound effects")


def get_sprite_path(filename):
    return os.path.join(get_project_base_dir(), "Sprites", filename)
