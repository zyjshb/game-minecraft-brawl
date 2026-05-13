import pygame

PRIORITY_HIGH = 10
PRIORITY_LOW = 5


class _BubbleSlot:
    def __init__(self, fighter, text, duration, priority):
        self.fighter = fighter
        self.text = text
        self.timer = duration
        self.max_timer = duration
        self.born = 0
        self.priority = priority

    def is_dead(self):
        return self.timer <= 0


class SpeechBubble:
    def __init__(self):
        self._slots = []
        self._font = None
        self._cooldowns = {}

    def _ensure_font(self):
        if self._font is None:
            try:
                from config import get_font
                self._font = get_font(34)
            except Exception:
                self._font = pygame.font.Font(None, 34)

    def is_fighter_speaking(self, f):
        fid = id(f)
        if fid in self._cooldowns and self._cooldowns[fid] > 0:
            return True
        for s in self._slots:
            if id(s.fighter) == fid:
                return True
        return False

    def set(self, text, fighter, duration=300, priority=PRIORITY_LOW):
        if fighter is None or not text:
            return
        if fighter.hp <= 0:
            return
        self._ensure_font()

        fid = id(fighter)

        for s in self._slots:
            if id(s.fighter) == fid:
                if priority >= s.priority:
                    s.text = text
                    s.timer = max(s.timer, duration)
                    s.max_timer = s.timer
                    s.priority = max(s.priority, priority)
                return

        self._slots.append(_BubbleSlot(fighter, text, duration, priority))
        self._cooldowns[fid] = 0

    def update(self):
        for s in self._slots[:]:
            s.timer -= 1
            s.born += 1
            if s.is_dead():
                fid = id(s.fighter)
                self._cooldowns[fid] = 60
                self._slots.remove(s)

        for fid in list(self._cooldowns.keys()):
            if self._cooldowns[fid] > 0:
                self._cooldowns[fid] -= 1
            else:
                del self._cooldowns[fid]

    @property
    def active(self):
        return len(self._slots) > 0

    def draw(self, surface, offset_x=0, offset_y=0):
        if not self._font:
            return
        for s in self._slots:
            if s.fighter is None or s.fighter.hp <= 0:
                continue
            self._draw_one(surface, s, offset_x, offset_y)

    def _draw_one(self, surface, s, offset_x=0, offset_y=0):
        if s.timer <= 0:
            return

        pop_scale = 1.0
        if s.born < 8:
            pop_scale = 0.6 + 0.4 * (s.born / 8.0)

        alpha = 255
        if s.timer < 35:
            alpha = int(255 * (s.timer / 35.0))

        pad_x, pad_y = 18, 14
        text_surf = self._font.render(s.text, True, (255, 255, 255))
        shadow_surf = self._font.render(s.text, True, (0, 0, 0))

        tw, th = text_surf.get_width(), text_surf.get_height()
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        bubble_w, bubble_h = int(bw * pop_scale), int(bh * pop_scale)

        if bubble_w < 8 or bubble_h < 8:
            return

        cx = s.fighter.rect.centerx
        cy = s.fighter.rect.top - 50
        bx = cx - bubble_w // 2
        by = cy - bubble_h - 6

        bubble = pygame.Surface((bubble_w, bubble_h + 10), pygame.SRCALPHA)

        bg_alpha = min(245, alpha + 20)
        border_alpha = alpha

        if s.priority >= PRIORITY_HIGH:
            border_color = (255, 180, 60)
        else:
            border_color = (180, 200, 220)

        pygame.draw.rect(bubble, (8, 10, 25, bg_alpha), (0, 0, bubble_w, bubble_h), border_radius=10)
        pygame.draw.rect(bubble, (*border_color, border_alpha), (0, 0, bubble_w, bubble_h), width=3, border_radius=10)

        tri_h = int(10 * pop_scale)
        tri_points = [
            (bubble_w // 2 - int(8 * pop_scale), bubble_h),
            (bubble_w // 2 + int(8 * pop_scale), bubble_h),
            (bubble_w // 2, bubble_h + tri_h),
        ]
        pygame.draw.polygon(bubble, (8, 10, 25, bg_alpha), tri_points)
        pygame.draw.polygon(bubble, (*border_color, border_alpha), tri_points, width=2)

        scaled_text = pygame.transform.smoothscale(text_surf, (int(tw * pop_scale), int(th * pop_scale)))
        scaled_shadow = pygame.transform.smoothscale(shadow_surf, (int(tw * pop_scale), int(th * pop_scale)))

        tx, ty = int(pad_x * pop_scale), int(pad_y * pop_scale)
        bubble.blit(scaled_shadow, (tx + 2, ty + 2))
        bubble.blit(scaled_text, (tx, ty))
        bubble.set_alpha(alpha)

        sw, sh = surface.get_width(), surface.get_height()
        bx = max(4, min(sw - bubble_w - 4, bx + offset_x))
        by = max(4, min(sh - bubble_h - 4, by + offset_y))
        surface.blit(bubble, (bx, by))
