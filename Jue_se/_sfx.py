try:
    from audio_manager import play_sfx_managed as _managed
except ImportError:
    def _managed(sound, volume=1.0):
        if sound:
            try:
                sound.play()
            except Exception:
                pass


def play_sfx(sound, volume=1.0):
    return _managed(sound, volume)
