# referee.py
import math
import random

class Referee:
    @staticmethod
    def get_valid_target(target):
        if target is None or target.hp <= 0: 
            return None
        return target.rect

    @staticmethod
    def process_collision(a, b):
        if hasattr(a, 'hp') and a.hp <= 0: return False
        if hasattr(b, 'hp') and b.hp <= 0: return False
        if hasattr(b, 'active') and not b.active: return False

        dx, dy = a.rect.centerx - b.rect.centerx, a.rect.centery - b.rect.centery
        dist = math.hypot(dx, dy)
        min_dist = (a.size + b.size) / 2
        
        if dist < min_dist and dist > 0:
            off = (min_dist - dist) / 2 + 4
            nx, ny = dx/dist, dy/dist
            
            a.rect.x += nx * off
            a.rect.y += ny * off
            
            if hasattr(b, 'vx'): 
                b.rect.x -= nx * off
                b.rect.y -= ny * off
                a.vx, b.vx = b.vx, a.vx
                a.vy, b.vy = b.vy, a.vy
            else:
                dot = a.vx * nx + a.vy * ny
                if dot < 0:
                    a.vx -= 2 * nx * dot
                    a.vy -= 2 * ny * dot
                else:
                    if abs(nx) > abs(ny): a.vx *= -1
                    else: a.vy *= -1
            
            if hasattr(a, 'vx'):
                a.vx += random.uniform(-0.2, 0.2)
            
            # 【核心修改】：发生实质碰撞时，返回 True
            return True 
            
        return False