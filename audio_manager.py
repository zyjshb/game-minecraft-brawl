import os
import random
from dataclasses import dataclass

import pygame


_SFX_NUM_CHANNELS = 16
_sfx_channels_initialized = False


def _init_sfx_channels():
    global _sfx_channels_initialized
    if not _sfx_channels_initialized:
        pygame.mixer.set_num_channels(_SFX_NUM_CHANNELS)
        _sfx_channels_initialized = True


def _sfx_channel_reserve():
    _init_sfx_channels()
    return pygame.mixer.find_channel(True)


_global_sfx_duck_factor = 1.0
_global_sfx_duck_end = 0


def start_sfx_duck(duration_ms, factor=0.3):
    global _global_sfx_duck_factor, _global_sfx_duck_end
    _global_sfx_duck_factor = _clamp01(factor)
    _global_sfx_duck_end = pygame.time.get_ticks() + int(duration_ms)
    _apply_duck_to_channels(_global_sfx_duck_factor)


def _apply_duck_to_channels(factor):
    try:
        for i in range(pygame.mixer.get_num_channels()):
            ch = pygame.mixer.Channel(i)
            if ch.get_busy():
                ch.set_volume(_clamp01(factor))
    except Exception:
        pass


def update_sfx_duck():
    global _global_sfx_duck_factor, _global_sfx_duck_end
    if _global_sfx_duck_factor < 1.0:
        now = pygame.time.get_ticks()
        if now >= _global_sfx_duck_end:
            _global_sfx_duck_factor = 1.0
            _apply_duck_to_channels(1.0)


def _get_effective_sfx_volume(volume):
    return _clamp01(volume * _global_sfx_duck_factor)


def play_sfx_managed(sound, volume=1.0):
    if sound is None:
        return None
    try:
        ch = _sfx_channel_reserve()
        if ch:
            ch.set_volume(_get_effective_sfx_volume(volume))
            ch.play(sound)
            return ch
    except Exception:
        pass
    return None


def _clamp01(v: float) -> float:
    try:
        v = float(v)
    except Exception:
        return 1.0
    return max(0.0, min(1.0, v))


@dataclass
class AudioPaths:
    base_dir: str
    music_dir_name: str = "Music"
    sfx_dir_name: str = "SFX"

    @property
    def music_dir(self) -> str:
        return os.path.join(self.base_dir, self.music_dir_name)

    @property
    def sfx_dir(self) -> str:
        return os.path.join(self.base_dir, self.sfx_dir_name)


class AudioManager:
    """
    Centralized audio manager:
    - Background music: loop if only 1 track, randomize if >=2 tracks.
    - UI click SFX and settlement SFX (optional; missing files are tolerated).
    - Music volume controlled by settings, with an additional in-game ducking factor.
    """

    def __init__(
        self,
        base_dir: str,
        music_end_event: int,
        default_music_volume: float = 0.7,
        ingame_duck_factor: float = 0.5,
    ) -> None:
        self.paths = AudioPaths(base_dir=base_dir)
        self.music_end_event = music_end_event

        self._music_volume_user = _clamp01(default_music_volume)
        self._ingame_duck_factor = _clamp01(ingame_duck_factor)
        self._ingame = False

        self._music_files: list[str] = []
        self._current_music: str | None = None

        self._ui_click_sound: pygame.mixer.Sound | None = None
        self._settlement_sound: pygame.mixer.Sound | None = None

        # Volume fade (music only)
        self._current_music_effective = self._calc_effective_music_volume()
        self._fade_active = False
        self._fade_from = self._current_music_effective
        self._fade_to = self._current_music_effective
        self._fade_start_ms = 0
        self._fade_duration_ms = 0
        self._music_muted = False
        self._is_boss_music = False
        self._crossfade_state = None
        self._crossfade_target = None
        self._crossfade_timer = 0
        self._crossfade_duration = 800

    def init(self) -> None:
        self._load_sfx()
        self.refresh_music_playlist()
        pygame.mixer.music.set_endevent(self.music_end_event)
        self._apply_music_volume(immediate=True)

    # -----------------------
    # SFX
    # -----------------------
    def _find_first_matching_audio(self, root_dirs: list[str], keywords: list[str]) -> str | None:
        keys = [k.lower() for k in keywords if k]
        for root in root_dirs:
            if not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    low = fn.lower()
                    if not low.endswith((".mp3", ".wav", ".ogg")):
                        continue
                    if keys and not any(k in low for k in keys):
                        continue
                    return os.path.join(dirpath, fn)
        return None

    def _load_sfx(self) -> None:
        # Optional; user can drop files here:
        # - SFX/ui_click.(mp3|wav|ogg)
        # - SFX/settlement.(mp3|wav|ogg)
        materials_dir = os.path.join(self.paths.base_dir, "Sound effects materials")

        for ext in ("mp3", "wav", "ogg"):
            p = os.path.join(self.paths.sfx_dir, f"ui_click.{ext}")
            if os.path.exists(p):
                try:
                    self._ui_click_sound = pygame.mixer.Sound(p)
                except Exception:
                    self._ui_click_sound = None
                break
        if self._ui_click_sound is None:
            p = self._find_first_matching_audio(
                [materials_dir, self.paths.sfx_dir],
                keywords=["按钮", "click", "button", "ui", "select"],
            )
            if p:
                try:
                    self._ui_click_sound = pygame.mixer.Sound(p)
                except Exception:
                    self._ui_click_sound = None

        for ext in ("mp3", "wav", "ogg"):
            p = os.path.join(self.paths.sfx_dir, f"settlement.{ext}")
            if os.path.exists(p):
                try:
                    self._settlement_sound = pygame.mixer.Sound(p)
                except Exception:
                    self._settlement_sound = None
                break
        if self._settlement_sound is None:
            p = self._find_first_matching_audio(
                [materials_dir, self.paths.sfx_dir],
                keywords=["结算", "结束", "game", "over", "win", "settle", "result"],
            )
            if p:
                try:
                    self._settlement_sound = pygame.mixer.Sound(p)
                except Exception:
                    self._settlement_sound = None

    def play_ui_click(self) -> None:
        if self._ui_click_sound:
            try:
                self._ui_click_sound.play()
            except Exception:
                pass

    def play_settlement(self) -> None:
        if self._settlement_sound:
            try:
                ch = _sfx_channel_reserve()
                if ch:
                    ch.play(self._settlement_sound)
            except Exception:
                pass

    # -----------------------
    # Music playlist
    # -----------------------
    def refresh_music_playlist(self) -> list[str]:
        files: list[str] = []
        if os.path.isdir(self.paths.music_dir):
            for name in os.listdir(self.paths.music_dir):
                low = name.lower()
                if low.endswith((".mp3", ".wav", ".ogg")):
                    files.append(os.path.join(self.paths.music_dir, name))
        files.sort()
        self._music_files = files
        return files

    def start_music_if_available(self) -> None:
        # Always refresh so newly added tracks are discovered.
        self.refresh_music_playlist()
        if not self._music_files:
            return

        if len(self._music_files) == 1:
            self._current_music = self._music_files[0]
            try:
                pygame.mixer.music.load(self._current_music)
                pygame.mixer.music.set_endevent(self.music_end_event)
                pygame.mixer.music.play(loops=-1)
                self._apply_music_volume(immediate=True)
            except Exception:
                self._current_music = None
            return

        self._start_random_track(exclude=self._current_music)

    def _start_random_track(self, exclude: str | None = None) -> None:
        # Refresh so newly added tracks are discovered between songs.
        self.refresh_music_playlist()
        if not self._music_files:
            return
        pool = [p for p in self._music_files if p != exclude] or list(self._music_files)
        choice = random.choice(pool)
        self._current_music = choice
        try:
            pygame.mixer.music.load(choice)
            # Defensive: some pygame builds reset endevent on load.
            pygame.mixer.music.set_endevent(self.music_end_event)
            pygame.mixer.music.play()
            # Important: pygame may reset music volume on load/play.
            self._apply_music_volume(immediate=True)
        except Exception:
            self._current_music = None

    def handle_music_end_event(self) -> None:
        if self._is_boss_music:
            return
        self.refresh_music_playlist()
        if len(self._music_files) <= 1:
            return
        self._start_random_track(exclude=self._current_music)

    # -----------------------
    # Volume + ducking
    # -----------------------
    def set_music_volume_user(self, vol01: float) -> None:
        self._music_volume_user = _clamp01(vol01)
        if self._music_muted:
            self._music_muted = False
        self._apply_music_volume(immediate=False, fade_ms=120)

    def get_music_volume_user(self) -> float:
        return float(self._music_volume_user)

    def toggle_music_mute(self):
        self._music_muted = not self._music_muted
        self._apply_music_volume(immediate=True)

    def is_music_muted(self) -> bool:
        return self._music_muted

    def play_boss_music(self, boss_music_path: str) -> None:
        self._is_boss_music = True
        try:
            volume = float(self._music_volume_user)
            pygame.mixer.music.set_volume(_clamp01(volume))
            pygame.mixer.music.fadeout(self._crossfade_duration)
            self._crossfade_state = "boss_loading"
            self._crossfade_target = boss_music_path
            self._crossfade_timer = pygame.time.get_ticks() + self._crossfade_duration
        except Exception:
            self._is_boss_music = False
            self.start_music_if_available()

    def restore_normal_music(self) -> None:
        self._is_boss_music = False
        try:
            pygame.mixer.music.fadeout(self._crossfade_duration)
            self._crossfade_state = "normal_loading"
            self._crossfade_target = None
            self._crossfade_timer = pygame.time.get_ticks() + self._crossfade_duration
        except Exception:
            self.start_music_if_available()

    def stop_all_sfx(self) -> None:
        try:
            for i in range(pygame.mixer.get_num_channels()):
                ch = pygame.mixer.Channel(i)
                ch.stop()
        except Exception:
            pass

    def set_ingame(self, ingame: bool, fade_ms: int = 450) -> None:
        self._ingame = bool(ingame)
        self._apply_music_volume(immediate=False, fade_ms=fade_ms)

    def _calc_effective_music_volume(self) -> float:
        effective = float(self._music_volume_user)
        if self._ingame and not self._is_boss_music:
            effective *= float(self._ingame_duck_factor)
        return _clamp01(effective)

    def update(self) -> None:
        update_sfx_duck()
        if self._crossfade_state:
            now = pygame.time.get_ticks()
            if now >= self._crossfade_timer:
                if self._crossfade_state == "boss_loading":
                    try:
                        pygame.mixer.music.load(self._crossfade_target)
                        pygame.mixer.music.play(loops=-1)
                        self._current_music_effective = 0.0
                        volume = float(self._music_volume_user)
                        target_vol = 0.0 if self._music_muted else volume
                        pygame.mixer.music.set_volume(0.0)
                        self._fade_active = True
                        self._fade_from = 0.0
                        self._fade_to = _clamp01(target_vol)
                        self._fade_start_ms = now
                        self._fade_duration_ms = self._crossfade_duration
                    except Exception:
                        self._is_boss_music = False
                        self.start_music_if_available()
                elif self._crossfade_state == "normal_loading":
                    self.start_music_if_available()
                    if pygame.mixer.music.get_busy():
                        volume = float(self._music_volume_user)
                        target_vol = 0.0 if self._music_muted else volume
                        self._fade_active = True
                        self._fade_from = 0.0
                        self._fade_to = _clamp01(target_vol)
                        self._fade_start_ms = now
                        self._fade_duration_ms = self._crossfade_duration
                        pygame.mixer.music.set_volume(0.0)
                self._crossfade_state = None
                return
            return
        if not self._fade_active:
            return
        now = pygame.time.get_ticks()
        t = (now - self._fade_start_ms) / max(1, self._fade_duration_ms)
        if t >= 1.0:
            self._fade_active = False
            self._current_music_effective = self._fade_to
        else:
            self._current_music_effective = (self._fade_from * (1.0 - t)) + (self._fade_to * t)
        try:
            final = 0.0 if self._music_muted else self._current_music_effective
            pygame.mixer.music.set_volume(_clamp01(final))
        except Exception:
            pass

    def _apply_music_volume(self, immediate: bool, fade_ms: int = 0) -> None:
        target = self._calc_effective_music_volume()
        if immediate or fade_ms <= 0:
            self._fade_active = False
            self._current_music_effective = target
            try:
                final = 0.0 if self._music_muted else target
                pygame.mixer.music.set_volume(_clamp01(final))
            except Exception:
                pass
            return

        self._fade_active = True
        self._fade_from = float(self._current_music_effective)
        self._fade_to = target
        self._fade_start_ms = pygame.time.get_ticks()
        self._fade_duration_ms = int(fade_ms)


audio: AudioManager | None = None


def init_audio(base_dir: str, music_end_event: int) -> AudioManager:
    global audio
    audio = AudioManager(base_dir=base_dir, music_end_event=music_end_event)
    audio.init()
    audio.start_music_if_available()
    return audio

