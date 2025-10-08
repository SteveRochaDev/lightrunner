# ...new file...
import pygame
import math

class Projectile:
    def __init__(self, x, y, target_x, target_y, speed=10, life=90, color=(255,220,100), radius=6, damage=1):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.color = color
        self.speed = speed
        self.life = life
        self.damage = damage
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy) or 1.0
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius*2, self.radius*2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        try:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        except Exception:
            pass
# ...new file...