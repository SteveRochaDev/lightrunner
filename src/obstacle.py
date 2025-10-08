import pygame
import random
import math

class Obstacle:
    def __init__(self, screen_width=800, screen_height=600, color=(255,50,50), speed=4, hp=1):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.color = color
        self.speed = speed
        self.hp = hp
        self.max_hp = max(1, hp)
        self.rect = self.spawn_rect()

    def spawn_rect(self):
        width = random.randint(20,60)
        height = random.randint(20,60)
        y = random.randint(0, self.screen_height - height)
        return pygame.Rect(self.screen_width, y, width, height)

    def update(self):
        self.rect.x -= self.speed

    def take_damage(self, dmg):
        self.hp -= dmg
        return self.hp <= 0

    def draw_health_bar(self, surface):
        if self.max_hp <= 1:
            return
        # small bar above obstacle
        bar_w = self.rect.width
        bar_h = 6
        bx = self.rect.x
        by = self.rect.y - bar_h - 6
        # background
        pygame.draw.rect(surface, (30,30,30), (bx, by, bar_w, bar_h), border_radius=3)
        # fill
        fill_w = max(0, int((self.hp / self.max_hp) * bar_w))
        pygame.draw.rect(surface, (200,50,50), (bx, by, fill_w, bar_h), border_radius=3)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        self.draw_health_bar(surface)

class Enemy:
    """A simple enemy that can chase the player."""
    def __init__(self, screen_width=800, screen_height=600, color=(180,50,200), speed=2.5, player=None, hp=3):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.color = color
        self.speed = speed
        self.player = player
        self.hp = hp
        self.max_hp = max(1, hp)
        self.rect = self.spawn_rect()

    def spawn_rect(self):
        size = random.randint(24,40)
        side = random.choice(['left','right','top','bottom'])
        if side == 'left':
            x = -size
            y = random.randint(0, self.screen_height - size)
        elif side == 'right':
            x = self.screen_width
            y = random.randint(0, self.screen_height - size)
        elif side == 'top':
            x = random.randint(0, self.screen_width - size)
            y = -size
        else:
            x = random.randint(0, self.screen_width - size)
            y = self.screen_height
        return pygame.Rect(x, y, size, size)

    def update(self):
        if self.player is not None:
            # move towards player's center
            px = self.player.x + self.player.width/2
            py = self.player.y + self.player.height/2
            dx = px - (self.rect.x + self.rect.width/2)
            dy = py - (self.rect.y + self.rect.height/2)
            dist = math.hypot(dx, dy) or 1
            self.rect.x += int(self.speed * (dx/dist))
            self.rect.y += int(self.speed * (dy/dist))
        else:
            # fallback to moving left
            self.rect.x -= int(self.speed)

    def take_damage(self, dmg):
        self.hp -= dmg
        return self.hp <= 0

    def draw_health_bar(self, surface):
        if self.max_hp <= 1:
            return
        bar_w = self.rect.width
        bar_h = 6
        bx = self.rect.x
        by = self.rect.y - bar_h - 6
        pygame.draw.rect(surface, (30,30,30), (bx, by, bar_w, bar_h), border_radius=3)
        fill_w = max(0, int((self.hp / self.max_hp) * bar_w))
        pygame.draw.rect(surface, (160,80,200), (bx, by, fill_w, bar_h), border_radius=3)

    def draw(self, surface):
        # draw as a rounded rect for variety
        try:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=6)
        except Exception:
            pygame.draw.rect(surface, self.color, self.rect)
        self.draw_health_bar(surface)
