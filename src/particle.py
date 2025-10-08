import random
import pygame
import math

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, vel_x, vel_y, energy_ratio):
        for _ in range(random.randint(2,5)):
            if energy_ratio > 0.6:
                color = (255, random.randint(200,255), random.randint(100,180))
            elif energy_ratio > 0.3:
                color = (150, random.randint(100,180), 255)
            else:
                color = (200, 50, 200)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": random.uniform(-2,2) - vel_x*0.3,
                "vy": random.uniform(-2,2) - vel_y*0.3,
                "life": random.randint(20,35),
                "color": color
            })

    def burst_confetti(self, x, y, count=40):
        """Create a celebratory confetti burst at (x,y)."""
        colors = [
            (255, 80, 80), (80, 255, 120), (80, 200, 255), (255, 200, 80), (200, 120, 255)
        ]
        for _ in range(count):
            ang = random.uniform(0, math.pi*2)
            speed = random.uniform(2, 6)
            vx = math.cos(ang) * speed + random.uniform(-1,1)
            vy = math.sin(ang) * speed + random.uniform(-2,1)
            col = random.choice(colors)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": vx,
                "vy": vy,
                "life": random.randint(40,80),
                "color": col
            })

    def update(self, screen, screen_width, screen_height):
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            # confetti affected by gravity
            p["vy"] += 0.06
            p["life"] -= 1
            if p["x"] <= 0 or p["x"] >= screen_width:
                p["vx"] *= -0.6
            if p["y"] <= 0 or p["y"] >= screen_height:
                p["vy"] *= -0.6
            if p["life"] <= 0:
                self.particles.remove(p)
            else:
                alpha = max(0, int(255 * (p["life"]/80)))
                # draw as small rectangle for confetti-like look
                try:
                    col = p["color"]
                    surf_col = (*col, alpha)
                    pygame.draw.rect(screen, surf_col, (int(p["x"]), int(p["y"]), 3, 3))
                except Exception:
                    pass
