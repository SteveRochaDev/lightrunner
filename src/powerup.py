import pygame
import math
import random

class PowerUp:
    """Simple pickup that either grants an instant effect (health) or a timed buff.
    Types: 'health', 'rapid_fire', 'shield', 'speed', 'damage'
    """
    def __init__(self, x, y, kind=None):
        self.x = int(x)
        self.y = int(y)
        self.radius = 14
        self.kind = kind if kind is not None else random.choice(['health','rapid_fire','shield','speed','damage'])
        # durations in seconds for timed effects
        self.durations = {
            'rapid_fire': 6,
            'shield': 6,
            'speed': 5,
            'damage': 6
        }
        self.duration = self.durations.get(self.kind, 0)
        # life on ground in frames
        self.life = 60 * 12  # 12 seconds
        self.spawn_tick = pygame.time.get_ticks()
        # visual mapping
        self.colors = {
            'health': (80, 200, 120),
            'rapid_fire': (255, 180, 50),
            'shield': (100, 200, 255),
            'speed': (200, 120, 255),
            'damage': (255, 100, 120)
        }
        self.icon_letters = {
            'health': '+',
            'rapid_fire': 'R',
            'shield': 'S',
            'speed': 'V',
            'damage': 'D'
        }
        self.bob_phase = random.uniform(0, math.pi*2)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)

    def update(self):
        self.life -= 1
        # bobbing motion for visual
        t = (pygame.time.get_ticks() / 240.0) + self.bob_phase
        self._bob = int(math.sin(t) * 4)

    def draw(self, surface):
        col = self.colors.get(self.kind, (200,200,200))
        # draw glow
        glow = pygame.Surface((self.radius*4, self.radius*4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col, 24), (self.radius*2, self.radius*2), self.radius*2)
        surface.blit(glow, (self.x - self.radius*2, self.y - self.radius*2 + getattr(self, '_bob', 0)))
        # main circle
        pygame.draw.circle(surface, col, (self.x, self.y + getattr(self, '_bob', 0)), self.radius)
        # inner ring
        pygame.draw.circle(surface, (255,255,255), (self.x, self.y + getattr(self, '_bob', 0)), self.radius-4, width=2)
        # draw a simple letter to indicate type
        try:
            font = pygame.font.Font(None, 22)
            txt = font.render(self.icon_letters.get(self.kind, '?'), True, (30,30,30))
            rect = txt.get_rect(center=(self.x, self.y + getattr(self, '_bob', 0)))
            surface.blit(txt, rect)
        except Exception:
            pass
