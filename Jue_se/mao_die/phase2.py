from .constants import (
    PHASE2_ATTACK_CD,
    PHASE2_DAMAGE,
    PHASE2_HP_DECAY_PER_LIFE,
    PHASE2_REGEN_HP,
    PHASE2_REGEN_INTERVAL,
    PHASE2_SECOND_CLAW_RATIO,
)


class Phase2System:
    def __init__(self):
        self.active = False
        self.activating = False
        self.lives_since_phase2 = 0
        self.regen_timer = 0
        self.vfx_list = []

    @property
    def attack_damage(self):
        return PHASE2_DAMAGE if self.active else None

    @property
    def second_claw_damage(self):
        return int(PHASE2_DAMAGE * (1.0 - PHASE2_SECOND_CLAW_RATIO)) if self.active else 0

    @property
    def attack_cd(self):
        return PHASE2_ATTACK_CD if self.active else None

    def get_decayed_max_hp(self, base_hp):
        if not self.active:
            return base_hp
        decay = 1.0 - PHASE2_HP_DECAY_PER_LIFE * self.lives_since_phase2
        return max(1, int(base_hp * decay))

    def complete_activation(self):
        self.activating = False
        self.active = True
        self.lives_since_phase2 = 0
        self.regen_timer = 0

    def on_life_lost(self):
        if self.active:
            self.lives_since_phase2 += 1

    def update_regen(self, hp, max_hp):
        if not self.active:
            return hp
        self.regen_timer += 1
        if self.regen_timer >= PHASE2_REGEN_INTERVAL:
            self.regen_timer = 0
            hp = min(max_hp, hp + PHASE2_REGEN_HP)
        return hp

    def update(self):
        for vfx in self.vfx_list[:]:
            vfx.update()
            if vfx.life <= 0:
                self.vfx_list.remove(vfx)

    def draw(self, surface):
        for vfx in self.vfx_list:
            vfx.draw(surface)
