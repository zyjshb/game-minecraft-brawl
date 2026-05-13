import math

from .constants import (
    HA_QI_COOLDOWN,
    HA_QI_DURATION,
    HA_QI_PUSH_FORCE,
    HA_QI_RANGE,
    HA_QI_SPEED_BUFF,
    TRIPLE_HA_QI_GAP,
)
from .vfx import HaQiAirWave


class HaQiSystem:
    def __init__(self):
        self.active = False
        self.timer = 0
        self.is_triple = False
        self.triple_index = 0
        self.triple_cooldown = 0
        self.vfx_list = []
        self.buff_active = False
        self.buff_timer = 0
        self.cooldown = 0

    def trigger_single(self, my_rect, enemy_rect):
        self.active = True
        self.timer = HA_QI_DURATION
        self.is_triple = False
        if not self.buff_active:
            self.buff_active = True
            self.buff_timer = HA_QI_DURATION
        self.cooldown = HA_QI_COOLDOWN
        facing_right = enemy_rect.centerx >= my_rect.centerx
        vfx_x = my_rect.centerx + (40 if facing_right else -40)
        vfx_y = my_rect.centery - 10
        self.vfx_list.append(HaQiAirWave(vfx_x, vfx_y, facing_right))
        return self._make_push_result(my_rect, enemy_rect)

    def trigger_triple_start(self):
        self.active = True
        self.is_triple = True
        self.triple_index = 0
        self.triple_cooldown = TRIPLE_HA_QI_GAP
        self.timer = TRIPLE_HA_QI_GAP * 4
        if not self.buff_active:
            self.buff_active = True
            self.buff_timer = TRIPLE_HA_QI_GAP * 5
        self.cooldown = HA_QI_COOLDOWN * 2

    def trigger_triple(self, my_rect, enemy_rect):
        self.active = True
        self.is_triple = True
        self.triple_index = 0
        self.triple_cooldown = 0
        self.timer = TRIPLE_HA_QI_GAP * 4
        if not self.buff_active:
            self.buff_active = True
            self.buff_timer = TRIPLE_HA_QI_GAP * 5
        self.cooldown = HA_QI_COOLDOWN * 2
        return self._fire_triple_burst(my_rect, enemy_rect)

    def _fire_triple_burst(self, my_rect, enemy_rect):
        self.triple_index += 1
        self.triple_cooldown = TRIPLE_HA_QI_GAP
        facing_right = enemy_rect.centerx >= my_rect.centerx
        vfx_x = my_rect.centerx + (40 if facing_right else -40)
        vfx_y = my_rect.centery - 10 + (self.triple_index - 1) * 14
        self.vfx_list.append(HaQiAirWave(vfx_x, vfx_y, facing_right))
        return self._make_push_result(my_rect, enemy_rect)

    def _make_push_result(self, my_rect, enemy_rect):
        dx = enemy_rect.centerx - my_rect.centerx
        dy = enemy_rect.centery - my_rect.centery
        dist = math.hypot(dx, dy) or 1.0
        nx = dx / dist
        ny = dy / dist
        return {
            "target": None,
            "damage": 0,
            "push": (nx * HA_QI_PUSH_FORCE, ny * HA_QI_PUSH_FORCE),
        }

    def get_attack_cd_multiplier(self):
        if self.buff_active:
            return 1.0 - HA_QI_SPEED_BUFF
        return 1.0

    def should_trigger(self, my_rect, enemy_rect):
        if enemy_rect is None:
            return False
        if self.cooldown > 0:
            return False
        dist = math.hypot(
            enemy_rect.centerx - my_rect.centerx,
            enemy_rect.centery - my_rect.centery,
        )
        return dist < HA_QI_RANGE

    def update(self):
        for vfx in self.vfx_list[:]:
            vfx.update()
            if vfx.life <= 0:
                self.vfx_list.remove(vfx)

        if self.cooldown > 0:
            self.cooldown -= 1

        if self.buff_active:
            self.buff_timer -= 1
            if self.buff_timer <= 0:
                self.buff_active = False

        if not self.active:
            return None

        self.timer -= 1
        if self.is_triple and self.triple_cooldown > 0:
            self.triple_cooldown -= 1

        if self.timer <= 0:
            self.active = False
            self.is_triple = False
            self.triple_index = 0

        return None

    def draw(self, surface):
        for vfx in self.vfx_list:
            vfx.draw(surface)
