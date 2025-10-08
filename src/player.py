import pygame

class Player:
    def __init__(self, x, y, width=50, height=50, color=(255, 255, 0), speed=5, max_trail=40):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.speed = speed
        self.energy = 100
        self.trail = []
        self.MAX_TRAIL_LENGTH = max_trail

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def move(self, vel_x, vel_y, screen_width, screen_height):
        self.x += vel_x * self.speed
        self.y += vel_y * self.speed
        self.x = max(0, min(screen_width - self.width, self.x))
        self.y = max(0, min(screen_height - self.height, self.y))

    def update_trail(self):
        self.trail.append((self.x + self.width // 2, self.y + self.height // 2))
        if len(self.trail) > self.MAX_TRAIL_LENGTH:
            self.trail.pop(0)

    def draw(self, surface):
        # Draw trail
        for i, pos in enumerate(self.trail):
            progress = i / len(self.trail)
            size = int(40 * progress + 10)
            glow_surface = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (255, 255, 200, max(0, 120 - i*3)), (size, size), size)
            pygame.draw.circle(glow_surface, (255, 240, 150, max(0, 80 - i*2)), (size, size), size//2)
            pygame.draw.circle(glow_surface, (255, 200, 100, max(0, 40 - i)), (size, size), size//4)
            surface.blit(glow_surface, (pos[0]-size, pos[1]-size))
        # Draw player
        pygame.draw.rect(surface, self.color, self.rect)
