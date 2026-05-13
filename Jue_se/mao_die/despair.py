import random


class DespairSystem:
    """已废弃 - 绝望判定机制已被移除"""
    def __init__(self):
        self.active = False
        self.timer = 0
        self.resolved = False
        self.survived = False
        self.veil = None
        self.immobilized = False
        self.triggered_once = False

    def trigger(self, w, h):
        pass

    def resolve(self, phase2):
        return True

    def is_immune(self):
        return False

    def update(self):
        pass

    def draw(self, surface):
        pass
