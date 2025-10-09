import pygame
import random
import os
import math
import json
from player import Player
from orb import Orb
from obstacle import Obstacle
from particle import ParticleSystem
from projectile import Projectile  # added

ASSETS_PATH = os.path.join(os.path.dirname(__file__), "../assets")

WIDTH, HEIGHT = 800, 600
STATE_START = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        # slightly larger fonts for improved readability
        self.font = pygame.font.Font(None, 40)
        self.large_font = pygame.font.Font(None, 84)

        self.game_state = STATE_START
        self.player = Player(WIDTH//2, HEIGHT//2)
        self.orb = Orb(screen_width=WIDTH, screen_height=HEIGHT)
        self.obstacles = []
        self.particles = ParticleSystem()
        self.spawn_timer = 0
        self.spawn_interval = 60
        self.score = 0
        self.orbs_collected = 0
        self.start_ticks = 0

        # projectile / shooting
        self.projectiles = []
        self.shoot_cooldown = 0
        self.SHOOT_COOLDOWN = 12  # frames between shots
        self.projectile_damage = 1

        # Power-ups
        from powerup import PowerUp
        self.powerups = []                 # active pickups on the map
        self.active_buffs = {}             # buff_name -> remaining frames
        self.base_shoot_cooldown = self.SHOOT_COOLDOWN
        self.base_projectile_damage = self.projectile_damage
        self.player_invulnerable = False

        # Sound
        try:
            music_path = os.path.join(ASSETS_PATH, "music.mp3")
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.3)

            orb_sound_path = os.path.join(ASSETS_PATH, "orb.wav")
            self.orb_sound = pygame.mixer.Sound(orb_sound_path) if os.path.exists(orb_sound_path) else None

            # Optional menu sounds (place files in assets/ to enable)
            nav_path = os.path.join(ASSETS_PATH, "menu_nav.wav")
            confirm_path = os.path.join(ASSETS_PATH, "menu_confirm.wav")
            self.navigate_sound = pygame.mixer.Sound(nav_path) if os.path.exists(nav_path) else None
            self.confirm_sound = pygame.mixer.Sound(confirm_path) if os.path.exists(confirm_path) else None
        except Exception as e:
            print("⚠️ Sound loading issue:", e)
            self.orb_sound = None
            self.navigate_sound = None
            self.confirm_sound = None

        # Menu / UI state
        self.music_enabled = pygame.mixer.music.get_busy()
        # Simplified menu: Credits removed; music is controlled via clickable icon
        self.menu_options = ["Start Game", "Settings", "Quit"]
        self.selected_menu = 0
        # Sound icon for main menu (drawn top-right)
        self.sound_icon_size = 36
        self.sound_icon_padding = 18
        self.sound_icon_rect = pygame.Rect(WIDTH - self.sound_icon_padding - self.sound_icon_size,
                                           self.sound_icon_padding,
                                           self.sound_icon_size, self.sound_icon_size)
        self.request_quit = False

        # Settings overlay
        self.show_settings = False
        self.settings_options = ["Music Volume", "Difficulty", "Player Color", "Back"]
        self.settings_selected = 0
        self.music_volume = 0.3
        self.difficulty_levels = ["Easy", "Normal", "Hard"]
        self.difficulty_index = 1
        # player customization
        self.player_colors = [(255,255,0), (0,255,255), (255,100,100), (180,120,255)]
        self.player_color_index = 0
        self.player.color = self.player_colors[self.player_color_index]

        # Game over specific menu
        self.gameover_options = ["Restart", "Main Menu", "Quit"]
        self.selected_menu_gameover = 0

        # High score persistence
        self.high_score_file = os.path.join(os.path.dirname(__file__), "../highscore.json")
        self.high_score = 0
        try:
            if os.path.exists(self.high_score_file):
                with open(self.high_score_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.high_score = int(data.get("high_score", 0))
        except Exception as e:
            print("⚠️ High score load issue:", e)

        # New-high animation state
        self.new_high = False
        self.new_high_timer = 0

        # Screen shake state
        self.shake_timer = 0
        self.shake_magnitude = 0

        # Difficulty affects obstacle speed/spawn
        self.base_obstacle_speed = 4
        self.apply_difficulty_settings()

        self.vel_x = 0
        self.vel_y = 0

        # UI overlay/fade state
        self.overlay_alpha = 0
        self.overlay_target_alpha = 0
        self.overlay_fade_speed = 12  # per frame
        self.show_overlay = False

        # Animated cursor
        self.cursor_pulse_speed = 180.0

        # Tooltip/help text
        self.tooltip_text = ""

        # Hover state for interactive elements
        self.hovered_menu = None
        self.hovered_gameover = None
        self.hovered_settings = None
        self.hovered_sound_icon = False
        # Pre-create system cursors if available
        try:
            self.cursor_hand = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND)
            self.cursor_arrow = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            self.cursor_hand = None
            self.cursor_arrow = None

    def apply_difficulty_settings(self):
        level = self.difficulty_levels[self.difficulty_index]
        if level == "Easy":
            self.spawn_interval = 90
            self.base_obstacle_speed = 3
        elif level == "Normal":
            self.spawn_interval = 60
            self.base_obstacle_speed = 4
        elif level == "Hard":
            self.spawn_interval = 40
            self.base_obstacle_speed = 5

    def reset(self):
        self.player = Player(WIDTH//2, HEIGHT//2)
        # apply selected player color so changes in Settings persist across restarts
        try:
            self.player.color = self.player_colors[self.player_color_index]
        except Exception:
            pass
        # clear powerups/buffs on restart
        self.powerups = []
        self.active_buffs = {}
        self.player_invulnerable = False
        self.projectile_damage = self.base_projectile_damage
        self.SHOOT_COOLDOWN = self.base_shoot_cooldown
        self.orb = Orb(screen_width=WIDTH, screen_height=HEIGHT)
        self.obstacles = []
        self.particles = ParticleSystem()
        self.spawn_timer = 0
        self.score = 0
        self.orbs_collected = 0
        self.start_ticks = pygame.time.get_ticks()

    def spawn_obstacle(self):
        # pass difficulty-based speed into obstacle
        ob = Obstacle(screen_width=WIDTH, screen_height=HEIGHT, speed=self.base_obstacle_speed, hp=1)
        self.obstacles.append(ob)
        # occasionally spawn smarter enemies on Normal/Hard
        if self.difficulty_index >= 1 and random.random() < 0.2:
            from obstacle import Enemy
            en = Enemy(screen_width=WIDTH, screen_height=HEIGHT, speed=2.0 + self.difficulty_index, player=self.player, hp=3)
            self.obstacles.append(en)

    def save_high_score(self):
        try:
            with open(self.high_score_file, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception as e:
            print("⚠️ High score save issue:", e)

    def get_current_cooldown(self):
        """Return the current shoot cooldown in frames, accounting for active buffs.
        Called from the gameplay update/shooting logic.
        """
        try:
            cd = int(self.base_shoot_cooldown)
            # rapid_fire halves cooldown (but keep at least 2 frames)
            if self.active_buffs.get('rapid_fire', 0) > 0:
                cd = max(2, int(cd * 0.5))
            return cd
        except Exception:
            return int(self.SHOOT_COOLDOWN)

    def apply_powerup(self, powerup):
        """Apply effects from a PowerUp and create a rich UI notification.
        Stores both remaining frames in self.active_buffs and the original total in
        self.active_buff_totals to render progress bars. Creates a top-centered
        notification with icon, name and slide/fade animation.
        """
        try:
            kind = getattr(powerup, 'kind', None)
            if not kind:
                return
            # ensure helper structures exist
            if not hasattr(self, 'powerup_notifications'):
                self.powerup_notifications = []  # list of dicts: {kind, text, timer, alpha, y}
            if not hasattr(self, 'active_buff_totals'):
                self.active_buff_totals = {}

            if kind == 'health':
                # instant heal
                self.player.energy = min(100, getattr(self.player, 'energy', 100) + 35)
                note_text = 'Health Restored'
                note_icon = '+'
                note_color = (80,200,120)
                note_dur = 0
            else:
                # timed buff
                duration = getattr(powerup, 'duration', 5)
                frames = int(duration * 60)
                self.active_buffs[kind] = frames
                self.active_buff_totals[kind] = frames
                note_text = kind.replace('_', ' ').title()
                # simple icons / colors mapping
                mapping = {
                    'rapid_fire': ('R', (255,180,50)),
                    'shield': ('S', (100,200,255)),
                    'speed': ('V', (200,120,255)),
                    'damage': ('D', (255,100,120))
                }
                note_icon, note_color = mapping.get(kind, ('?', (200,200,200)))
                note_dur = frames
                # immediate effects
                if kind == 'shield':
                    self.player_invulnerable = True
                elif kind == 'speed':
                    try:
                        self.player.speed = min(12, self.player.speed + 2)
                    except Exception:
                        pass
                elif kind == 'damage':
                    self.projectile_damage = max(1, int(self.base_projectile_damage * 2))
                # rapid_fire handled dynamically via get_current_cooldown

            # add a notification (top-center) that slides down then fades
            self.powerup_notifications.insert(0, {
                'kind': kind,
                'text': note_text,
                'icon': note_icon,
                'color': note_color,
                'timer': 180,      # frames to show (~3s)
                'alpha': 0,
                'y': -36
            })

            # celebratory confetti at player
            try:
                px = int(self.player.x + getattr(self.player, 'width', 24) // 2)
                py = int(self.player.y + getattr(self.player, 'height', 24) // 2)
                self.particles.burst_confetti(px, py, count=30)
            except Exception:
                pass
        except Exception:
            pass

    def draw_hud(self, surface=None):
        try:
            surf = surface if surface is not None else self.screen
            # Energy bar (top-left)
            eb_w, eb_h = 220, 14
            ex, ey = 16, 12
            try:
                pygame.draw.rect(surf, (22,22,24), (ex, ey, eb_w, eb_h), border_radius=6)
                fill_w = int(((getattr(self.player, 'energy', 100) or 0) / 100.0) * (eb_w - 4))
                pygame.draw.rect(surf, (80,200,120), (ex + 2, ey + 2, max(0, fill_w), eb_h - 4), border_radius=6)
                e_txt = self.font.render(f"Energy: {int(getattr(self.player, 'energy', 0))}", True, (230,230,230))
                surf.blit(e_txt, (ex + 6, ey + eb_h + 6))
            except Exception:
                pass

            # Score / Orbs (top-right)
            try:
                score_s = self.font.render(f"Score: {self.score}", True, (240,240,220))
                orbs_s = self.font.render(f"Orbs: {self.orbs_collected}", True, (180,220,255))
                sx = WIDTH - score_s.get_width() - 18
                surf.blit(score_s, (sx, 12))
                surf.blit(orbs_s, (sx, 12 + score_s.get_height() + 6))
            except Exception:
                pass

            # Active buffs (bottom-left) with progress bars
            try:
                bx = 16
                by = HEIGHT - 120
                line_h = 28
                small_font = pygame.font.Font(None, 20)
                i = 0
                for k, rem in list(getattr(self, 'active_buffs', {}).items()):
                    total = getattr(self, 'active_buff_totals', {}).get(k, max(1, rem))
                    icon_w = 36
                    label_w = 120
                    padding = 10
                    # compute bar width so row fits on screen
                    max_row_w = WIDTH - 32 - bx
                    bar_w = max(60, min(160, max_row_w - (icon_w + label_w + padding)))
                    ix = bx
                    iy = by + i * line_h
                    row_w = min(max_row_w, icon_w + label_w + bar_w + padding*2)
                    # background row
                    pygame.draw.rect(surf, (18,18,22), (ix, iy, row_w, 22), border_radius=6)
                    # icon
                    mapping = {
                        'rapid_fire': ('R', (255,180,50)),
                        'shield': ('S', (100,200,255)),
                        'speed': ('V', (200,120,255)),
                        'damage': ('D', (255,100,120))
                    }
                    icon_letter, icon_col = mapping.get(k, (k[0].upper() if k else '?', (200,200,200)))
                    try:
                        pygame.draw.circle(surf, icon_col, (ix+14, iy+11), 8)
                    except Exception:
                        pass
                    # label
                    lbl = small_font.render(k.replace('_',' ').title(), True, (240,240,240))
                    surf.blit(lbl, (ix+32, iy+2))
                    # progress bar
                    bar_x = ix + icon_w + label_w - 12
                    max_bar_w = max(48, min(bar_w, WIDTH - (bar_x + 80)))
                    pygame.draw.rect(surf, (40,40,48), (bar_x, iy+4, max_bar_w, 14), border_radius=6)
                    ratio = max(0.0, min(1.0, rem / float(total))) if total > 0 else 0.0
                    pygame.draw.rect(surf, (120,200,255), (bar_x+2, iy+6, int((max_bar_w-4)*ratio), 10), border_radius=6)
                    # time label clamped
                    seconds = rem / 60.0
                    time_lbl = small_font.render(f"{seconds:.1f}s", True, (220,220,220))
                    time_x = bar_x + max_bar_w + 8
                    if time_x + time_lbl.get_width() > WIDTH - 12:
                        time_x = WIDTH - 12 - time_lbl.get_width()
                    surf.blit(time_lbl, (time_x, iy+2))
                    i += 1
            except Exception:
                pass

            # Top-Center notifications (recent pickups) - clamped fully on screen
            try:
                if not hasattr(self, 'powerup_notifications'):
                    return
                max_w = min(420, WIDTH - 40)
                notif_font = pygame.font.Font(None, 24)
                spacing = 6
                for idx, n in enumerate(list(self.powerup_notifications)):
                    t = n.get('timer', 0)
                    alpha = int(255 * (min(1.0, t / 180.0)))
                    target_y = 12 + idx * (34 + spacing)
                    n['y'] = int(n.get('y', -36) + (target_y - n.get('y', -36)) * 0.22)
                    box_h = 34
                    box_w = max(160, max_w)
                    box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                    box.fill((12,12,16, int(220 * (alpha/255.0))))
                    try:
                        pygame.draw.rect(box, n.get('color',(200,200,200)), (8, 6, 22, 22), border_radius=6)
                        ic = notif_font.render(str(n.get('icon','?')), True, (18,18,20))
                        box.blit(ic, (12, 6))
                    except Exception:
                        pass
                    # text with ellipsis if too wide
                    raw_text = n.get('text','')
                    txt = notif_font.render(raw_text, True, (240,240,240))
                    max_text_w = box_w - 64
                    if txt.get_width() > max_text_w:
                        text_str = raw_text
                        while notif_font.size(text_str + '...')[0] > max_text_w and len(text_str) > 0:
                            text_str = text_str[:-1]
                        txt = notif_font.render(text_str + '...', True, (240,240,240))
                    box.blit(txt, (44, 6))
                    sx = max(12, min(WIDTH - box_w - 12, WIDTH//2 - box_w//2))
                    surf.blit(box, (sx, n['y']))
            except Exception:
                pass
        except Exception:
            pass

    def draw(self):
        """Main render entry. Keeps drawing simple and defensive so the game
        always has a draw implementation even if other parts are incomplete.
        """
        try:
            # clear background
            self.screen.fill((10, 10, 30))

            if self.game_state == STATE_START:
                try:
                    # title
                    title_surf = self.large_font.render("LightRunner", True, (255, 220, 40))
                    tr = title_surf.get_rect(center=(WIDTH//2, HEIGHT//6))
                    self.screen.blit(title_surf, tr)
                    # high score
                    hs = self.font.render(f"High Score: {self.high_score}", True, (220,220,200))
                    self.screen.blit(hs, (WIDTH//2 - hs.get_width()//2, tr.bottom + 8))
                    # menu
                    start_y = HEIGHT//3
                    for i, opt in enumerate(getattr(self, 'menu_options', [])):
                        is_sel = (i == getattr(self, 'selected_menu', 0))
                        col = (255,255,255) if is_sel else (180,180,180)
                        txt = self.font.render(opt, True, col)
                        tx = WIDTH//2 - txt.get_width()//2
                        ty = start_y + i * 48
                        # background for selected
                        if is_sel:
                            try:
                                pygame.draw.rect(self.screen, (22,22,26), (tx-12, ty-6, txt.get_width()+24, txt.get_height()+12), border_radius=8)
                            except Exception:
                                pass
                        self.screen.blit(txt, (tx, ty))
                    # simple hint
                    try:
                        hint_font = pygame.font.Font(None, 22)
                        h1 = hint_font.render("Use Up/Down to navigate", True, (200,200,200))
                        h2 = hint_font.render("Use the mouse to attack enemies", True, (200,200,200))
                        self.screen.blit(h1, (WIDTH//2 - h1.get_width()//2, HEIGHT - 64))
                        self.screen.blit(h2, (WIDTH//2 - h2.get_width()//2, HEIGHT - 44))
                    except Exception:
                        pass
                except Exception:
                    pass

            elif self.game_state == STATE_PLAYING:
                try:
                    # draw orb
                    try:
                        self.orb.draw(self.screen)
                    except Exception:
                        pass
                    # draw obstacles
                    for ob in list(getattr(self, 'obstacles', [])):
                        try:
                            ob.draw(self.screen)
                        except Exception:
                            pass
                    # draw projectiles
                    for p in list(getattr(self, 'projectiles', [])):
                        try:
                            p.draw(self.screen)
                        except Exception:
                            pass
                    # draw player (on top)
                    try:
                        self.player.draw(self.screen)
                    except Exception:
                        pass
                    # particles
                    try:
                        # particles are drawn during their update; call update with no effect if needed
                        pass
                    except Exception:
                        pass
                    # HUD
                    try:
                        self.draw_hud(self.screen)
                    except Exception:
                        pass
                except Exception:
                    pass

            elif self.game_state == STATE_GAMEOVER:
                try:
                    go = self.large_font.render("Game Over", True, (255,80,80))
                    self.screen.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//4))
                    sc = self.font.render(f"Score: {self.score}", True, (255,255,255))
                    self.screen.blit(sc, (WIDTH//2 - sc.get_width()//2, HEIGHT//4 + 80))
                    # options
                    start_y = HEIGHT//2
                    for i, opt in enumerate(getattr(self, 'gameover_options', [])):
                        is_sel = (i == getattr(self, 'selected_menu_gameover', 0))
                        col = (255,255,255) if is_sel else (180,180,180)
                        txt = self.font.render(opt, True, col)
                        tx = WIDTH//2 - txt.get_width()//2
                        ty = start_y + i * 48
                        if is_sel:
                            try:
                                pygame.draw.rect(self.screen, (22,22,26), (tx-12, ty-6, txt.get_width()+24, txt.get_height()+12), border_radius=8)
                            except Exception:
                                pass
                        self.screen.blit(txt, (tx, ty))
                    # show HUD overlay too
                    try:
                        self.draw_hud(self.screen)
                    except Exception:
                        pass
                except Exception:
                    pass

            # ensure particles are drawn on top
            try:
                # particle system draws during update; call update with current surface to render remaining particles
                self.particles.update(self.screen, WIDTH, HEIGHT)
            except Exception:
                pass
        except Exception:
            pass

    def update(self):
        """Per-frame housekeeping for timers, buff expiry and particle updates.
        This augments gameplay update logic and keeps the powerup UI in sync.
        """
        keys = pygame.key.get_pressed()

        # Shooting input: left mouse or spacebar
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if (mouse_pressed or keys[pygame.K_SPACE]) and self.shoot_cooldown == 0 and self.game_state == STATE_PLAYING:
            mx, my = pygame.mouse.get_pos()
            # spawn projectile from player's center aimed at mouse
            px = self.player.x + self.player.width//2
            py = self.player.y + self.player.height//2
            proj = Projectile(px, py, mx, my, speed=12, damage=self.projectile_damage)
            self.projectiles.append(proj)
            # respect active rapid-fire buff
            self.shoot_cooldown = self.get_current_cooldown()

        # Movement
        self.vel_x = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.vel_y = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.player.move(self.vel_x, self.vel_y, WIDTH, HEIGHT)
        self.player.update_trail()

        # Energy
        self.player.energy -= 0.1
        if self.player.energy <= 0:
            self.game_state = STATE_GAMEOVER
            self.selected_menu_gameover = 0
            # update high score if needed
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()
                # trigger new-high animation and sound
                self.new_high = True
                self.new_high_timer = 120  # frames (~2s at 60fps)
                if self.confirm_sound:
                    self.confirm_sound.play()

        # Obstacles
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.spawn_obstacle()

        for ob in self.obstacles[:]:
            ob.update()
            # remove if offscreen
            if ob.rect.right < -100 or ob.rect.left > WIDTH + 100 or ob.rect.top > HEIGHT + 100 or ob.rect.bottom < -100:
                try:
                    self.obstacles.remove(ob)
                except ValueError:
                    pass

        # Projectiles update and collisions with obstacles/enemies
        for proj in self.projectiles[:]:
            proj.update()
            # remove if expired or offscreen
            if proj.life <= 0 or proj.x < -50 or proj.x > WIDTH + 50 or proj.y < -50 or proj.y > HEIGHT + 50:
                try:
                    self.projectiles.remove(proj)
                except ValueError:
                    pass
                continue

            hit_any = False
            for ob in self.obstacles[:]:
                if proj.rect.colliderect(ob.rect):
                    # apply damage; if dead remove and spawn particles/score
                    dead = False
                    try:
                        dead = ob.take_damage(proj.damage)
                    except Exception:
                        # fallback: remove obstacle if it doesn't implement take_damage
                        dead = True
                    if dead:
                        try:
                            self.obstacles.remove(ob)
                        except ValueError:
                            pass
                        # reward points for kills
                        self.score += 150
                        # small confetti / particles
                        self.particles.burst_confetti(ob.rect.centerx, ob.rect.centery, count=12)
                        # small chance to spawn a power-up where the obstacle died
                        if random.random() < 0.15:
                            try:
                                from powerup import PowerUp
                                pu = PowerUp(ob.rect.centerx, ob.rect.centery)
                                self.powerups.append(pu)
                            except Exception:
                                pass
                        if getattr(self, 'confirm_sound', None):
                            try:
                                self.confirm_sound.play()
                            except Exception:
                                pass
                    # remove projectile on hit
                    try:
                        self.projectiles.remove(proj)
                    except ValueError:
                        pass
                    hit_any = True
                    break
            if hit_any:
                continue

        # Collision detection with orb and player collisions (unchanged)
        if self.player.rect.colliderect(self.orb.rect):
            self.orb.respawn()
            self.player.energy = min(self.player.energy + 20, 100)
            self.orbs_collected += 1
            if self.orb_sound:
                self.orb_sound.play()

        for ob in self.obstacles[:]:
            if self.player.rect.colliderect(ob.rect):
                # if shield active, ignore damage
                if not self.player_invulnerable:
                    self.player.energy -= 20
                try:
                    self.obstacles.remove(ob)
                except ValueError:
                    pass
                # trigger small screen shake
                self.shake_timer = 18
                self.shake_magnitude = 8
                if self.player.energy <= 0:
                    self.game_state = STATE_GAMEOVER
                    self.selected_menu_gameover = 0
                    # update high score if needed
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self.save_high_score()
                        # confetti + new-high
                        self.particles.burst_confetti(self.player.x + self.player.width//2, self.player.y + self.player.height//2, count=60)
                        self.new_high = True
                        self.new_high_timer = 120
                        if self.confirm_sound:
                            self.confirm_sound.play()

        # Score
        elapsed_seconds = (pygame.time.get_ticks() - self.start_ticks)/1000
        self.score = int(elapsed_seconds*10 + self.orbs_collected*100)

        # Particles
        speed_mag = abs(self.vel_x) + abs(self.vel_y)
        if speed_mag > 0:
            self.particles.emit(self.player.x+self.player.width/2,
                                self.player.y+self.player.height/2,
                                self.vel_x, self.vel_y,
                                self.player.energy/100)
        self.particles.update(self.screen, WIDTH, HEIGHT)

        # Power-ups: update on-ground pickups and check for pickup by player
        for pu in self.powerups[:]:
            try:
                pu.update()
            except Exception:
                pass
            # remove if expired
            if getattr(pu, 'life', 0) <= 0:
                try:
                    self.powerups.remove(pu)
                except ValueError:
                    pass
                continue
            # pickup check
            if self.player.rect.colliderect(pu.rect):
                # apply effect
                try:
                    self.apply_powerup(pu)
                except Exception:
                    pass
                try:
                    self.powerups.remove(pu)
                except ValueError:
                    pass
                # confetti/audio on pickup
                self.particles.burst_confetti(self.player.x + self.player.width//2, self.player.y + self.player.height//2, count=12)
                if getattr(self, 'confirm_sound', None):
                    try:
                        self.confirm_sound.play()
                    except Exception:
                        pass

        # Active buffs expiration (decrement timers and cleanup)
        expired = []
        try:
            for k in list(self.active_buffs.keys()):
                try:
                    self.active_buffs[k] -= 1
                except Exception:
                    # if value corrupted, schedule removal
                    expired.append(k)
                    continue
                if self.active_buffs[k] <= 0:
                    expired.append(k)
            for k in expired:
                try:
                    # revert any one-time changes
                    if k == 'shield':
                        self.player_invulnerable = False
                    elif k == 'speed':
                        try:
                            # best-effort revert: subtract the boost we applied earlier
                            self.player.speed = max(3, getattr(self.player, 'speed', 5) - 2)
                        except Exception:
                            pass
                    elif k == 'damage':
                        self.projectile_damage = int(self.base_projectile_damage)
                    elif k == 'rapid_fire':
                        # nothing to revert besides timer
                        pass
                    # cleanup bookkeeping
                    if hasattr(self, 'active_buff_totals') and k in self.active_buff_totals:
                        try:
                            del self.active_buff_totals[k]
                        except Exception:
                            pass
                    try:
                        del self.active_buffs[k]
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        # Decrease new-high timer
        if self.new_high_timer > 0:
            self.new_high_timer -= 1
        else:
            self.new_high = False

        # Decrease shake timer
        if self.shake_timer > 0:
            self.shake_timer -= 1

        # Animate overlay alpha towards target
        if self.overlay_alpha < self.overlay_target_alpha:
            self.overlay_alpha = min(self.overlay_target_alpha, self.overlay_alpha + self.overlay_fade_speed)
            self.show_overlay = True
        elif self.overlay_alpha > self.overlay_target_alpha:
            self.overlay_alpha = max(self.overlay_target_alpha, self.overlay_alpha - self.overlay_fade_speed)
            if self.overlay_alpha == 0:
                self.show_overlay = False

        # --- cleanup top-center powerup notifications so they disappear when timer ends ---
        try:
            if hasattr(self, 'powerup_notifications') and isinstance(self.powerup_notifications, list):
                for n in list(self.powerup_notifications):
                    try:
                        n['timer'] = n.get('timer', 0) - 1
                        if n['timer'] <= 0:
                            try:
                                self.powerup_notifications.remove(n)
                            except Exception:
                                pass
                    except Exception:
                        # if a notification is malformed, remove it
                        try:
                            self.powerup_notifications.remove(n)
                        except Exception:
                            pass
        except Exception:
            pass

    def handle_event(self, event):
        """Handle KEYDOWN for menu navigation and activation.
        Safe to call from the main loop.
        """
        try:
            if event.type != pygame.KEYDOWN:
                return
            k = event.key
            # Global back/escape handling
            if k == pygame.K_ESCAPE:
                # if in settings overlay, close it; otherwise go to main menu
                if getattr(self, 'show_overlay', False):
                    self.show_overlay = False
                    return
                self.game_state = STATE_START
                return

            if self.game_state == STATE_START:
                if k in (pygame.K_UP, pygame.K_w):
                    self.selected_menu = (self.selected_menu - 1) % len(self.menu_options)
                elif k in (pygame.K_DOWN, pygame.K_s):
                    self.selected_menu = (self.selected_menu + 1) % len(self.menu_options)
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    idx = self.selected_menu
                    opt = self.menu_options[idx]
                    if opt.lower().startswith('start'):
                        try:
                            self.reset()
                            self.game_state = STATE_PLAYING
                            self.start_ticks = pygame.time.get_ticks()
                        except Exception:
                            pass
                    elif opt.lower().startswith('settings'):
                        self.show_overlay = not getattr(self, 'show_overlay', False)
                    elif opt.lower().startswith('quit'):
                        self.request_quit = True
            elif self.game_state == STATE_GAMEOVER:
                if k in (pygame.K_UP, pygame.K_w):
                    self.selected_menu_gameover = (self.selected_menu_gameover - 1) % len(self.gameover_options)
                elif k in (pygame.K_DOWN, pygame.K_s):
                    self.selected_menu_gameover = (self.selected_menu_gameover + 1) % len(self.gameover_options)
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    idx = self.selected_menu_gameover
                    opt = self.gameover_options[idx]
                    if opt.lower().startswith('restart'):
                        try:
                            self.reset()
                            self.game_state = STATE_PLAYING
                            self.start_ticks = pygame.time.get_ticks()
                        except Exception:
                            pass
                    elif opt.lower().startswith('main'):
                        self.game_state = STATE_START
                    elif opt.lower().startswith('quit'):
                        self.request_quit = True
            else:
                # In-game keys: allow quick toggle of music with M
                if k == pygame.K_m:
                    try:
                        if hasattr(self, 'toggle_music'):
                            self.toggle_music()
                    except Exception:
                        pass
        except Exception:
            pass

    def handle_mouse(self, event):
        """Handle mouse button presses for clickable UI (sound icon, menu selection).
        """
        try:
            if event.type != pygame.MOUSEBUTTONDOWN:
                return
            if event.button != 1:
                return
            mx, my = event.pos
            # sound icon click
            try:
                if getattr(self, 'sound_icon_rect', None) and self.sound_icon_rect.collidepoint((mx, my)):
                    try:
                        if hasattr(self, 'toggle_music'):
                            self.toggle_music()
                    except Exception:
                        pass
                    return
            except Exception:
                pass

            # click menu items on Start screen
            if self.game_state == STATE_START:
                try:
                    start_y = HEIGHT//3
                    for i, opt in enumerate(getattr(self, 'menu_options', [])):
                        txt = self.font.render(opt, True, (255,255,255))
                        x = WIDTH//2 - txt.get_width()//2
                        y = start_y + i*48
                        rect = pygame.Rect(x-12, y-6, txt.get_width()+24, txt.get_height()+12)
                        if rect.collidepoint((mx, my)):
                            self.selected_menu = i
                            # perform selection
                            if opt.lower().startswith('start'):
                                try:
                                    self.reset()
                                    self.game_state = STATE_PLAYING
                                    self.start_ticks = pygame.time.get_ticks()
                                except Exception:
                                    pass
                            elif opt.lower().startswith('settings'):
                                self.show_overlay = not getattr(self, 'show_overlay', False)
                            elif opt.lower().startswith('quit'):
                                self.request_quit = True
                            return
                except Exception:
                    pass

            # click gameover menu
            if self.game_state == STATE_GAMEOVER:
                try:
                    start_y = HEIGHT//2
                    for i, opt in enumerate(getattr(self, 'gameover_options', [])):
                        txt = self.font.render(opt, True, (255,255,255))
                        x = WIDTH//2 - txt.get_width()//2
                        y = start_y + i*48
                        rect = pygame.Rect(x-12, y-6, txt.get_width()+24, txt.get_height()+12)
                        if rect.collidepoint((mx, my)):
                            self.selected_menu_gameover = i
                            if opt.lower().startswith('restart'):
                                try:
                                    self.reset()
                                    self.game_state = STATE_PLAYING
                                    self.start_ticks = pygame.time.get_ticks()
                                except Exception:
                                    pass
                            elif opt.lower().startswith('main'):
                                self.game_state = STATE_START
                            elif opt.lower().startswith('quit'):
                                self.request_quit = True
                            return
                except Exception:
                    pass
        except Exception:
            pass

    def handle_mouse_motion(self, event):
        """Track hovered menu item and sound icon for UI hover effects.
        """
        try:
            mx, my = event.pos
            self.hovered_menu = None
            self.hovered_gameover = None
            self.hovered_sound_icon = False
            # sound icon
            try:
                if getattr(self, 'sound_icon_rect', None) and self.sound_icon_rect.collidepoint((mx, my)):
                    self.hovered_sound_icon = True
            except Exception:
                pass
            # start menu hover
            if self.game_state == STATE_START:
                try:
                    start_y = HEIGHT//3
                    for i, opt in enumerate(getattr(self, 'menu_options', [])):
                        txt = self.font.render(opt, True, (255,255,255))
                        x = WIDTH//2 - txt.get_width()//2
                        y = start_y + i*48
                        rect = pygame.Rect(x-12, y-6, txt.get_width()+24, txt.get_height()+12)
                        if rect.collidepoint((mx, my)):
                            self.hovered_menu = i
                            break
                except Exception:
                    pass
            # gameover hover
            if self.game_state == STATE_GAMEOVER:
                try:
                    start_y = HEIGHT//2
                    for i, opt in enumerate(getattr(self, 'gameover_options', [])):
                        txt = self.font.render(opt, True, (255,255,255))
                        x = WIDTH//2 - txt.get_width()//2
                        y = start_y + i*48
                        rect = pygame.Rect(x-12, y-6, txt.get_width()+24, txt.get_height()+12)
                        if rect.collidepoint((mx, my)):
                            self.hovered_gameover = i
                            break
                except Exception:
                    pass
        except Exception:
            pass