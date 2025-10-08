import pygame
import random

class Orb:
    def __init__(self, radius=15, color=(0,255,255), screen_width=800, screen_height=600):
        self.radius = radius
        self.color = color
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = random.randint(radius, screen_width-radius)
        self.y = random.randint(radius, screen_height-radius)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)

    def respawn(self):
        self.x = random.randint(self.radius, self.screen_width-self.radius)
        self.y = random.randint(self.radius, self.screen_height-self.radius)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius)
