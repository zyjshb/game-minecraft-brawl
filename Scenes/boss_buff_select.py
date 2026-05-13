import random

import pygame

from config import get_font
from i18n import t

BUFF_POOL = [
    {"id": "atk_up", "icon": "⚔", "desc_key": "buff_atk_desc",
     "apply": lambda diff, tier: ("atk_up", max(1, int((2 + tier * 2 + (1 if tier == 1 else 0)) * diff["dmg_mult"])), 0, "buff")},
    {"id": "spd_up", "icon": "💨", "desc_key": "buff_spd_desc",
     "apply": lambda diff, tier: ("spd_up", max(1, int((2 + tier * 2 + (1 if tier == 1 else 0)) * diff["spd_mult"])), 0, "buff")},
    {"id": "crit_up", "icon": "💥", "desc_key": "buff_crit_desc",
     "apply": lambda diff, tier: ("crit_up", max(1, int((1 + tier * 2 + (1 if tier == 1 else 0)) * diff["dmg_mult"])), 0, "buff")},
    {"id": "lifesteal", "icon": "🩸", "desc_key": "buff_lifesteal_desc",
     "apply": lambda diff, tier: ("lifesteal", max(1, int((2 + tier * 1) * diff["hp_mult"] * 0.6)), 0, "buff")},
    {"id": "dmg_res", "icon": "🛡", "desc_key": "buff_dmg_res_desc",
     "apply": lambda diff, tier: ("dmg_res", max(1, int((2 + tier * 2 + (1 if tier == 1 else 0)) * diff["hp_mult"])), 0, "buff")},
    {"id": "thorn", "icon": "🌵", "desc_key": "buff_thorn_desc",
     "apply": lambda diff, tier: ("thorn", max(1, int((1 + tier * 2 + (1 if tier == 1 else 0)) * diff["dmg_mult"])), 0, "buff")},
    {"id": "dmg_amp", "icon": "🔥", "desc_key": "buff_dmg_amp_desc",
     "apply": lambda diff, tier: ("dmg_amp", max(1, int((2 + tier * 2 + (1 if tier == 1 else 0)) * diff["dmg_mult"])), 0, "buff")},
    {"id": "regen", "icon": "💚", "desc_key": "buff_regen_desc",
     "apply": lambda diff, tier: ("regen", max(1, int((2 + tier * 2 + (1 if tier == 1 else 0)) * diff["hp_mult"])), 0, "buff")},
    {"id": "fury", "icon": "😡", "desc_key": "buff_fury_desc",
     "apply": lambda diff, tier: ("fury", max(1, int((2 + tier * 3 + (1 if tier == 1 else 0)) * diff["dmg_mult"])), 0, "buff")},
    {"id": "barrier", "icon": "🔮", "desc_key": "buff_barrier_desc",
     "apply": lambda diff, tier: ("barrier", max(1, int((4 + tier * 3 + (2 if tier == 1 else 0)) * diff["hp_mult"])), 0, "buff")},
]

TIER_STARS = {0: "★☆☆", 1: "★★☆", 2: "★★★"}
TIER_NAMES = {0: "buff_tier_low", 1: "buff_tier_mid", 2: "buff_tier_high"}
TIER_CARD_COLORS = {0: (30, 32, 45), 1: (25, 35, 55), 2: (35, 28, 22)}
TIER_BORDER_COLORS = {0: (120, 130, 150), 1: (70, 160, 240), 2: (255, 170, 40)}
TIER_GLOW_COLORS = {0: None, 1: (70, 140, 230, 40), 2: (255, 180, 50, 70)}

RECOMMENDATION_TEXT = [
    "推荐组合: 吸血+暴击+攻击力 → 通用万金油",
    "推荐组合: 攻速+暴击+狂暴 → 残血爆发",
    "推荐组合: 防御+回复+护盾 → 站桩换血",
]

ROUNDS = 3
TIME_PER_ROUND = 360
MAX_REFRESHES = 5

_safety_net_enabled = True


class BossBuffSelect:
    def __init__(self, w, h, difficulty):
        self.w, self.h = w, h
        self.difficulty = difficulty
        self.round = 0
        self.choices = []
        self.tiers = []
        self.picked = []
        self.timer = 0
        self.refreshes_left = MAX_REFRESHES
        self._total_refreshes = 0
        self._refresh_history = []

        self.font_title = get_font(42)
        self.font_buff = get_font(26)
        self.font_desc = get_font(18)
        self.font_timer = get_font(34)
        self.font_tier = get_font(16)
        self.font_stat = get_font(20)
        self.font_refresh_btn = get_font(24)
        self.font_tiny = get_font(16)

        self._refresh_btn_rect = None
        self._choice_rects = []
        self._safety_toggle_rect = None

        self._start_round()

    def _roll_tier(self):
        r = random.random()
        if r < 0.02:
            return 2
        elif r < 0.16:
            return 1
        return 0

    def _start_round(self):
        available = [b for b in BUFF_POOL if b["id"] not in [p[0] for p in self.picked]]
        count = min(3, len(available))
        self.choices = random.sample(available, count)
        self.tiers = [self._roll_tier() for _ in range(count)]
        self.refreshes_left = MAX_REFRESHES
        self._total_refreshes = 0
        self._refresh_history = []
        self.timer = TIME_PER_ROUND

    @property
    def done(self):
        return self.round >= ROUNDS

    def handle_event(self, event):
        global _safety_net_enabled
        if self.done:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB and self.refreshes_left > 0:
                self.refreshes_left -= 1
                self._refresh()
            elif event.key == pygame.K_s:
                _safety_net_enabled = not _safety_net_enabled
            elif event.key in (pygame.K_1, pygame.K_KP1) and len(self.choices) >= 1:
                self._pick(0)
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(self.choices) >= 2:
                self._pick(1)
            elif event.key in (pygame.K_3, pygame.K_KP3) and len(self.choices) >= 3:
                self._pick(2)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            for i, r in enumerate(self._choice_rects):
                if r.collidepoint(mx, my):
                    self._pick(i)
                    return
            if self._refresh_btn_rect and self._refresh_btn_rect.collidepoint(mx, my) and self.refreshes_left > 0:
                self.refreshes_left -= 1
                self._refresh()
            if self._safety_toggle_rect and self._safety_toggle_rect.collidepoint(mx, my):
                _safety_net_enabled = not _safety_net_enabled

    def _refresh(self):
        global _safety_net_enabled
        self._refresh_history.append((list(self.choices), list(self.tiers)))
        self._total_refreshes += 1
        available = [b for b in BUFF_POOL if b["id"] not in [p[0] for p in self.picked]]
        count = min(3, len(available))
        self.choices = random.sample(available, count)
        self.tiers = [self._roll_tier() for _ in range(count)]
        self.timer = TIME_PER_ROUND
        if self.refreshes_left == 0 and _safety_net_enabled:
            if not any(t >= 2 for t in self.tiers):
                self._rollback_to_best()

    def _rollback_to_best(self):
        scored = []
        for choices, tiers in self._refresh_history:
            for ci in range(len(choices)):
                b = choices[ci]
                t = tiers[ci]
                if b["id"] in [p[0] for p in self.picked]:
                    continue
                scored.append((t, b, t * 1000 + ci))
        if not scored:
            scored.append((0, self.choices[0], 0))
        scored.sort(key=lambda x: -x[2])
        seen = set()
        result = []
        for t, b, _ in scored:
            if b["id"] not in seen:
                seen.add(b["id"])
                result.append((b, t))
                if len(result) >= 3:
                    break
        while len(result) < 3:
            for b in BUFF_POOL:
                if b["id"] not in seen and b["id"] not in [p[0] for p in self.picked]:
                    result.append((b, 0))
                    seen.add(b["id"])
                    if len(result) >= 3:
                        break
        self.choices = [b for b, _ in result]
        self.tiers = [t for _, t in result]

    def _pick(self, idx):
        b = self.choices[idx]
        tier = self.tiers[idx]
        name, val, dur, btype = b["apply"](self.difficulty, tier)
        self.picked.append((b["id"], name, val, dur, btype, tier))
        self.round += 1
        if self.round < ROUNDS:
            self._start_round()

    def update(self):
        if self.done:
            return
        self.timer -= 1
        if self.timer <= 0:
            self.round += 1
            if self.round < ROUNDS:
                self._start_round()

    def update_and_draw(self, surface):
        surface.fill((10, 12, 22))

        if self.done:
            return

        title = self.font_title.render(
            t("buff_round").replace("{n}", str(self.round + 1)).replace("{total}", str(ROUNDS)),
            True, (255, 215, 0),
        )
        surface.blit(title, title.get_rect(center=(self.w // 2, 55)))

        seconds = max(0, self.timer // 60 + 1)
        ts_color = (255, 255, 255) if seconds > 2 else (255, 80, 80)
        ts = self.font_timer.render(f"{seconds}s", True, ts_color)
        surface.blit(ts, ts.get_rect(center=(self.w // 2, 115)))

        bar_w, bar_h = 380, 8
        progress = max(0, self.timer / TIME_PER_ROUND)
        bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(bar, (35, 35, 48, 180), (0, 0, bar_w, bar_h), border_radius=4)
        bar_color = (255, 200, 50) if seconds > 2 else (255, 60, 40)
        pygame.draw.rect(bar, bar_color, (0, 0, int(bar_w * progress), bar_h), border_radius=4)
        surface.blit(bar, bar.get_rect(center=(self.w // 2, 145)))

        self._choice_rects = []
        card_w, card_h = 320, 175
        gap = 350
        for i, b in enumerate(self.choices):
            bx = self.w // 2 + (i - 1) * gap - card_w // 2
            by = self.h // 2 - 85
            card_rect = pygame.Rect(bx, by, card_w, card_h)
            self._choice_rects.append(card_rect)

            tier = self.tiers[i] if i < len(self.tiers) else 0
            bg_col = TIER_CARD_COLORS[tier]
            border_col = TIER_BORDER_COLORS[tier]
            glow_col = TIER_GLOW_COLORS[tier]

            pygame.draw.rect(surface, bg_col, card_rect, border_radius=14)

            if glow_col:
                glow = pygame.Surface(card_rect.inflate(10, 10).size, pygame.SRCALPHA)
                alpha = glow_col[3]
                glow.fill((glow_col[0], glow_col[1], glow_col[2], alpha))
                surface.blit(glow, (card_rect.x - 5, card_rect.y - 5))

            pygame.draw.rect(surface, border_col, card_rect, width=3, border_radius=14)

            stars = TIER_STARS[tier]
            star_color = {0: (140, 150, 160), 1: (80, 180, 240), 2: (255, 180, 40)}[tier]
            star_surf = self.font_tier.render(stars, True, star_color)
            surface.blit(star_surf, star_surf.get_rect(midtop=(card_rect.centerx, by + 8)))

            bname = t("buff_" + b["id"]) if t("buff_" + b["id"]) != "buff_" + b["id"] else b["id"]
            name_surf = self.font_buff.render(f"{b['icon']}  {bname}", True, (255, 255, 255))
            surface.blit(name_surf, name_surf.get_rect(center=(card_rect.centerx, int(by + card_h * 0.33))))

            tier_name = t(TIER_NAMES[tier])
            tier_s = self.font_tier.render(tier_name, True, star_color)
            surface.blit(tier_s, tier_s.get_rect(center=(card_rect.centerx, int(by + card_h * 0.50))))

            dummy_name, val, _, _ = b["apply"](self.difficulty, tier)
            display_name = t("buff_" + b["id"]) if t("buff_" + b["id"]) != "buff_" + b["id"] else b["id"]
            stat_text = f"+{val} {display_name}"
            stat_surf = self.font_stat.render(stat_text, True, (255, 255, 180))
            surface.blit(stat_surf, stat_surf.get_rect(center=(card_rect.centerx, int(by + card_h * 0.68))))

            desc = t(b["desc_key"])
            if desc == b["desc_key"]:
                desc = b["desc_key"]
            desc_surf = self.font_desc.render(desc, True, (160, 165, 185))
            surface.blit(desc_surf, desc_surf.get_rect(center=(card_rect.centerx, int(by + card_h * 0.85))))

            key_hint = self.font_tier.render(t("buff_press_key").replace("{n}", str(i + 1)), True, (200, 200, 100))
            surface.blit(key_hint, key_hint.get_rect(center=(card_rect.centerx, by + card_h - 14)))

        btn_w, btn_h = 240, 50
        btn_x = self.w // 2 - btn_w // 2
        btn_y = self.h - 95
        self._refresh_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        can_refresh = self.refreshes_left > 0
        btn_bg = (25, 60, 45) if can_refresh else (35, 35, 40)
        btn_border = (50, 180, 80) if can_refresh else (80, 80, 85)
        pygame.draw.rect(surface, btn_bg, self._refresh_btn_rect, border_radius=12)
        pygame.draw.rect(surface, btn_border, self._refresh_btn_rect, width=3, border_radius=12)

        refresh_text = t("buff_refresh_btn").replace("{n}", str(self.refreshes_left))
        refresh_color = (180, 255, 180) if can_refresh else (120, 120, 125)
        rf = self.font_refresh_btn.render(refresh_text, True, refresh_color)
        surface.blit(rf, rf.get_rect(center=self._refresh_btn_rect.center))

        rec_idx = self.round % len(RECOMMENDATION_TEXT)
        rec = self.font_tiny.render(RECOMMENDATION_TEXT[rec_idx], True, (140, 160, 200))
        surface.blit(rec, rec.get_rect(center=(self.w // 2, self.h - 135)))

        picked_y = self.h - 30
        picked_parts = []
        for p in self.picked:
            pname = t('buff_' + p[0]) if t('buff_' + p[0]) != 'buff_' + p[0] else p[0]
            stars = TIER_STARS.get(p[5], "★☆☆")
            picked_parts.append(f"{pname}({stars})+{p[2]}")
        picked_text = " | ".join(picked_parts)
        if picked_text:
            ps = self.font_tier.render(f"{t('buff_picked')}: {picked_text}", True, (130, 150, 90))
            ps_rect = ps.get_rect(center=(self.w // 2, picked_y))
            surface.blit(ps, ps_rect)

        toggle_w, toggle_h = 200, 26
        toggle_x = 14
        toggle_y = self.h - 60
        self._safety_toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
        st_text = f"回溯 {'ON' if _safety_net_enabled else 'OFF'} [S]"
        st_color = (120, 255, 120) if _safety_net_enabled else (180, 80, 80)
        st = self.font_tier.render(st_text, True, st_color)
        surface.blit(st, st.get_rect(midleft=(toggle_x + 4, toggle_y + toggle_h // 2)))
