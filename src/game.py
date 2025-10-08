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
        self.font = pygame.font.Font(None, 36)
        self.large_font = pygame.font.Font(None, 72)

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

    def update(self):
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
        for k in list(self.active_buffs.keys()):
            self.active_buffs[k] -= 1
            if self.active_buffs[k] <= 0:
                # expire effect
                if k == 'shield':
                    self.player_invulnerable = False
                elif k == 'speed':
                    try:
                        self.player.speed = max(1, self.player.speed - 3)
                    except Exception:
                        pass
                elif k == 'damage':
                    self.projectile_damage = self.base_projectile_damage
                # remove key
                del self.active_buffs[k]

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

    def draw_hud(self, surface=None):
        target = surface if surface is not None else self.screen
        # Energy bar
        bar_width, bar_height = 200, 20
        pygame.draw.rect(target, (50,50,50), (10,10,bar_width,bar_height))
        current_width = int((self.player.energy/100)*bar_width)
        pygame.draw.rect(target, (0,255,0), (10,10,current_width,bar_height))

        # Score / Orbs
        score_text = self.font.render(f"Score: {self.score}", True, (255,255,255))
        orbs_text = self.font.render(f"Orbs: {self.orbs_collected}", True, (0,255,255))
        target.blit(score_text, (10,40))
        target.blit(orbs_text, (10,70))

        # High score (top-right)
        high_text = self.font.render(f"High: {self.high_score}", True, (255,215,0))
        target.blit(high_text, (WIDTH - high_text.get_width() - 10, 10))

        # Active power-up/buff icons (top-right, below high score)
        x = WIDTH - 10
        y = 40
        if hasattr(self, 'active_buffs') and self.active_buffs:
            for i, (k, t) in enumerate(self.active_buffs.items()):
                # small icon box
                box_w = 80
                box_h = 20
                bx = x - box_w
                by = y + i * (box_h + 6)
                pygame.draw.rect(target, (30,30,30), (bx, by, box_w, box_h), border_radius=6)
                pygame.draw.rect(target, (80,80,100), (bx, by, box_w, box_h), width=1, border_radius=6)
                # label and timer
                lbl = self.font.render(f"{k} {int(t/60)}s", True, (220,220,220))
                target.blit(lbl, (bx + 6, by + 2))

    def handle_event(self, event):
        """Handle key events for menus, settings and game states."""
        if event.type != pygame.KEYDOWN:
            return

        # If Settings overlay is open, let it handle keys first
        if self.show_settings:
            old_idx = self.settings_selected
            if event.key in (pygame.K_UP, pygame.K_w):
                self.settings_selected = (self.settings_selected - 1) % len(self.settings_options)
                self.hovered_settings = self.settings_selected
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.settings_selected = (self.settings_selected + 1) % len(self.settings_options)
                self.hovered_settings = self.settings_selected
            elif event.key in (pygame.K_LEFT,):
                # decrement currently selected setting
                opt = self.settings_options[self.settings_selected]
                if opt == "Music Volume":
                    self.music_volume = max(0.0, round((self.music_volume - 0.1), 2))
                    try:
                        pygame.mixer.music.set_volume(self.music_volume)
                    except Exception:
                        pass
                elif opt == "Difficulty":
                    self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_levels)
                    self.apply_difficulty_settings()
                elif opt == "Player Color":
                    self.player_color_index = (self.player_color_index - 1) % len(self.player_colors)
                    try:
                        self.player.color = self.player_colors[self.player_color_index]
                    except Exception:
                        pass
            elif event.key in (pygame.K_RIGHT,):
                # increment currently selected setting
                opt = self.settings_options[self.settings_selected]
                if opt == "Music Volume":
                    self.music_volume = min(1.0, round((self.music_volume + 0.1), 2))
                    try:
                        pygame.mixer.music.set_volume(self.music_volume)
                    except Exception:
                        pass
                elif opt == "Difficulty":
                    self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_levels)
                    self.apply_difficulty_settings()
                elif opt == "Player Color":
                    self.player_color_index = (self.player_color_index + 1) % len(self.player_colors)
                    try:
                        self.player.color = self.player_colors[self.player_color_index]
                    except Exception:
                        pass
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                opt = self.settings_options[self.settings_selected]
                if getattr(self, 'confirm_sound', None):
                    try:
                        self.confirm_sound.play()
                    except Exception:
                        pass
                if opt == "Music Volume":
                    self.music_volume = min(1.0, round((self.music_volume + 0.1), 2))
                    try:
                        pygame.mixer.music.set_volume(self.music_volume)
                    except Exception:
                        pass
                elif opt == "Difficulty":
                    self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_levels)
                    self.apply_difficulty_settings()
                elif opt == "Player Color":
                    self.player_color_index = (self.player_color_index + 1) % len(self.player_colors)
                    try:
                        self.player.color = self.player_colors[self.player_color_index]
                    except Exception:
                        pass
                elif opt == "Back":
                    self.show_settings = False
                    self.overlay_target_alpha = 0
                    self.hovered_settings = None
            elif event.key == pygame.K_ESCAPE:
                # close settings
                self.show_settings = False
                self.overlay_target_alpha = 0
                self.hovered_settings = None
            if old_idx != self.settings_selected and getattr(self, 'navigate_sound', None):
                try:
                    self.navigate_sound.play()
                except Exception:
                    pass
            return

        # Start/menu screen input (only if settings not open)
        if self.game_state == STATE_START:
            old = self.selected_menu
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_menu = (self.selected_menu - 1) % len(self.menu_options)
                self.hovered_menu = self.selected_menu
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_menu = (self.selected_menu + 1) % len(self.menu_options)
                self.hovered_menu = self.selected_menu
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = self.menu_options[self.selected_menu]
                if getattr(self, 'confirm_sound', None):
                    try:
                        self.confirm_sound.play()
                    except Exception:
                        pass
                if choice == "Start Game":
                    self.game_state = STATE_PLAYING
                    self.reset()
                elif choice == "Settings":
                    self.show_settings = True
                    self.overlay_target_alpha = 220
                    self.settings_selected = 0
                    self.hovered_settings = 0
                elif choice == "Quit":
                    self.request_quit = True
            elif event.key == pygame.K_ESCAPE:
                pass
            if old != self.selected_menu and getattr(self, 'navigate_sound', None):
                try:
                    self.navigate_sound.play()
                except Exception:
                    pass
            return

        # Handle input when on the gameover screen
        if self.game_state == STATE_GAMEOVER:
            old = self.selected_menu_gameover
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_menu_gameover = (self.selected_menu_gameover - 1) % len(self.gameover_options)
                self.hovered_gameover = self.selected_menu_gameover
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_menu_gameover = (self.selected_menu_gameover + 1) % len(self.gameover_options)
                self.hovered_gameover = self.selected_menu_gameover
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = self.gameover_options[self.selected_menu_gameover]
                if getattr(self, 'confirm_sound', None):
                    try:
                        self.confirm_sound.play()
                    except Exception:
                        pass
                if choice == "Restart":
                    self.game_state = STATE_PLAYING
                    self.reset()
                elif choice == "Main Menu":
                    self.game_state = STATE_START
                    self.selected_menu = 0
                    self.hovered_menu = 0
                elif choice == "Quit":
                    self.request_quit = True
            elif event.key == pygame.K_ESCAPE:
                self.game_state = STATE_START
                self.selected_menu = 0
                self.hovered_menu = 0
            if old != self.selected_menu_gameover and getattr(self, 'navigate_sound', None):
                try:
                    self.navigate_sound.play()
                except Exception:
                    pass
            return

        # Playing state shortcuts
        if self.game_state == STATE_PLAYING:
            if event.key in (pygame.K_p,):
                self.game_state = STATE_START
            elif event.key in (pygame.K_m,):
                # quick toggle music
                self.toggle_music()
            elif event.key in (pygame.K_r,):
                self.reset()

    def handle_mouse(self, event):
        """Handle mouse clicks for menu items, settings and the sound icon."""
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        if event.button != 1:
            return
        pos = event.pos

        # Sound icon (top-right) toggle
        if hasattr(self, 'sound_icon_rect') and self.sound_icon_rect.collidepoint(pos):
            # Only toggle when on the start menu (but allow if visible)
            if self.game_state == STATE_START:
                self.toggle_music()
                return

        # Start menu clickable items
        if self.game_state == STATE_START:
            menu_start_y = HEIGHT//3
            for i, opt in enumerate(self.menu_options):
                text = self.font.render(opt, True, (255,255,255))
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                rect = pygame.Rect(x-12, y-6, text.get_width()+24, text.get_height()+8)
                if rect.collidepoint(pos):
                    if getattr(self, 'confirm_sound', None):
                        try:
                            self.confirm_sound.play()
                        except Exception:
                            pass
                    if opt == "Start Game":
                        self.game_state = STATE_PLAYING
                        self.reset()
                    elif opt == "Settings":
                        self.show_settings = True
                        self.overlay_target_alpha = 220
                        self.settings_selected = 0
                    elif opt == "Quit":
                        self.request_quit = True
                    return

        # Game over menu clickable items
        if self.game_state == STATE_GAMEOVER:
            menu_start_y = HEIGHT//2
            for i, opt in enumerate(self.gameover_options):
                text = self.font.render(opt, True, (255,255,255))
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                rect = pygame.Rect(x-12, y-6, text.get_width()+24, text.get_height()+8)
                if rect.collidepoint(pos):
                    if getattr(self, 'confirm_sound', None):
                        try:
                            self.confirm_sound.play()
                        except Exception:
                            pass
                    if opt == "Restart":
                        self.game_state = STATE_PLAYING
                        self.reset()
                    elif opt == "Main Menu":
                        self.game_state = STATE_START
                        self.selected_menu = 0
                    elif opt == "Quit":
                        self.request_quit = True
                    return

        # Settings overlay clicks (left/right half = decrement/increment, click back to close)
        if self.show_settings:
            panel_w, panel_h = WIDTH - 240, HEIGHT - 240
            panel_x, panel_y = 120, 120
            for idx, opt in enumerate(self.settings_options):
                txt = self.font.render(opt, True, (255,255,255))
                rect = pygame.Rect(panel_x + 40 - 6, panel_y + 90 + idx*48 - 6, txt.get_width()+12, txt.get_height()+8)
                if rect.collidepoint(pos):
                    # determine left/right half click
                    mid_x = rect.left + rect.width // 2
                    left_click = pos[0] < mid_x
                    # play confirm
                    if getattr(self, 'confirm_sound', None):
                        try:
                            self.confirm_sound.play()
                        except Exception:
                            pass
                    if opt == "Music Volume":
                        # left = decrease, right = increase
                        if left_click:
                            self.music_volume = max(0.0, round((self.music_volume - 0.1), 2))
                        else:
                            self.music_volume = min(1.0, round((self.music_volume + 0.1), 2))
                        try:
                            pygame.mixer.music.set_volume(self.music_volume)
                        except Exception:
                            pass
                    elif opt == "Difficulty":
                        if left_click:
                            self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_levels)
                        else:
                            self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_levels)
                        self.apply_difficulty_settings()
                    elif opt == "Player Color":
                        if left_click:
                            self.player_color_index = (self.player_color_index - 1) % len(self.player_colors)
                        else:
                            self.player_color_index = (self.player_color_index + 1) % len(self.player_colors)
                        try:
                            self.player.color = self.player_colors[self.player_color_index]
                        except Exception:
                            pass
                    elif opt == "Back":
                        self.show_settings = False
                        self.overlay_target_alpha = 0
                    return

    def handle_mouse_motion(self, event):
        """Handle mouse motion for hover effects and cursor changes."""
        pos = event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos()
        cursor_should_be_hand = False

        # Start/menu hover
        if self.game_state == STATE_START:
            menu_start_y = HEIGHT//3
            found = False
            for i, opt in enumerate(self.menu_options):
                text = self.font.render(opt, True, (255,255,255))
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                rect = pygame.Rect(x-12, y-6, text.get_width()+24, text.get_height()+8)
                if rect.collidepoint(pos):
                    self.hovered_menu = i
                    cursor_should_be_hand = True
                    found = True
                    break
            if not found:
                self.hovered_menu = None
        else:
            self.hovered_menu = None

        # Game over menu hover
        if self.game_state == STATE_GAMEOVER:
            menu_start_y = HEIGHT//2
            found = False
            for i, opt in enumerate(self.gameover_options):
                text = self.font.render(opt, True, (255,255,255))
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                rect = pygame.Rect(x-12, y-6, text.get_width()+24, text.get_height()+8)
                if rect.collidepoint(pos):
                    self.hovered_gameover = i
                    cursor_should_be_hand = True
                    found = True
                    break
            if not found:
                self.hovered_gameover = None
        else:
            self.hovered_gameover = None

        # Settings overlay hover
        if self.show_settings:
            panel_w, panel_h = WIDTH - 240, HEIGHT - 240
            panel_x, panel_y = 120, 120
            found = False
            for idx, opt in enumerate(self.settings_options):
                txt = self.font.render(opt, True, (255,255,255))
                rect = pygame.Rect(panel_x + 40 - 6, panel_y + 90 + idx*48 - 6, txt.get_width()+12, txt.get_height()+8)
                if rect.collidepoint(pos):
                    self.hovered_settings = idx
                    cursor_should_be_hand = True
                    found = True
                    break
            if not found:
                self.hovered_settings = None
        else:
            self.hovered_settings = None

        # Sound icon hover
        if hasattr(self, 'sound_icon_rect') and self.sound_icon_rect.collidepoint(pos):
            self.hovered_sound_icon = True
            cursor_should_be_hand = True
        else:
            self.hovered_sound_icon = False

        # Apply system cursor change if available
        try:
            if cursor_should_be_hand and getattr(self, 'cursor_hand', None):
                pygame.mouse.set_cursor(self.cursor_hand)
            elif getattr(self, 'cursor_arrow', None):
                pygame.mouse.set_cursor(self.cursor_arrow)
        except Exception:
            pass

    def toggle_music(self):
        """Toggle background music on/off safely."""
        self.music_enabled = not getattr(self, 'music_enabled', True)
        try:
            if self.music_enabled:
                # try to (re)start music if available
                music_path = os.path.join(ASSETS_PATH, "music.mp3")
                if os.path.exists(music_path):
                    if not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(-1)
                    pygame.mixer.music.set_volume(getattr(self, 'music_volume', 0.3))
            else:
                pygame.mixer.music.stop()
        except Exception:
            pass

    def draw(self):
        # Clear
        self.screen.fill((10,10,30))

        if self.game_state == STATE_START:
            # Animated title
            t = pygame.time.get_ticks() / 600.0
            pulse = 1.0 + 0.06 * math.sin(t)
            title_surf = self.large_font.render("LightRunner", True, (255,255,0))
            title_rect = title_surf.get_rect()
            title_pos = (WIDTH//2 - int(title_rect.width * pulse)//2, HEIGHT//6)
            # draw subtle glow behind title
            glow = pygame.Surface((int(title_rect.width*pulse)+40, int(title_rect.height*pulse)+40), pygame.SRCALPHA)
            glow.fill((0,0,0,0))
            gcol = (255, 200, 50, 30)
            pygame.draw.ellipse(glow, gcol, glow.get_rect())
            self.screen.blit(glow, (title_pos[0]-20, title_pos[1]-20))
            # draw title scaled
            scaled = pygame.transform.smoothscale(title_surf, (int(title_rect.width*pulse), int(title_rect.height*pulse)))
            self.screen.blit(scaled, title_pos)

            # show high score under title
            hs = self.font.render(f"High Score: {self.high_score}", True, (220,220,180))
            self.screen.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//3 - 40))

            # Menu options
            menu_start_y = HEIGHT//3
            for i, opt in enumerate(self.menu_options):
                is_selected = (i == self.selected_menu)
                is_hover = (i == getattr(self, 'hovered_menu', None))
                if is_selected:
                    color = (255,255,255)
                elif is_hover:
                    color = (235,235,235)
                else:
                    color = (200,200,200)
                text = self.font.render(opt, True, color)
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                # Selected gets a stronger background, hovered gets a subtle background
                if is_selected:
                    pygame.draw.rect(self.screen, (40,40,60), (x-12, y-6, text.get_width()+24, text.get_height()+8), border_radius=8)
                elif is_hover:
                    pygame.draw.rect(self.screen, (30,30,50), (x-12, y-6, text.get_width()+24, text.get_height()+8), border_radius=8)
                self.screen.blit(text, (x, y))
                if i == self.selected_menu:
                    # animated arrow
                    pulse_a = 6 * math.sin(pygame.time.get_ticks() / self.cursor_pulse_speed)
                    ax = x - 28 + int(pulse_a)
                    ay = y + text.get_height()//2
                    pygame.draw.polygon(self.screen, (255,255,255), [(ax, ay), (ax+10, ay-8), (ax+10, ay+8)])

                hint = self.font.render("Use Up/Down to navigate — Enter to select", True, (180,180,180))
                self.screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 70))

            # draw sound icon in top-right of the menu (clickable)
            # simple speaker glyph + waves; draw an X overlay when muted
            icon_x = WIDTH - self.sound_icon_padding - self.sound_icon_size
            icon_y = self.sound_icon_padding
            rect = pygame.Rect(icon_x, icon_y, self.sound_icon_size, self.sound_icon_size)
            # background circle
            pygame.draw.rect(self.screen, (18,18,22), rect, border_radius=8)
            pygame.draw.rect(self.screen, (90,90,100), rect, width=2, border_radius=8)
            # speaker triangle
            cx = icon_x + 8
            cy = icon_y + self.sound_icon_size//2
            pygame.draw.polygon(self.screen, (230,230,230), [(cx, cy-8), (cx+6, cy-8), (cx+12, cy-14), (cx+12, cy+14), (cx+6, cy+8), (cx, cy+8)])
            # waves when enabled
            if self.music_enabled:
                pygame.draw.arc(self.screen, (200,200,200), (icon_x+12, icon_y+6, 18, 24), math.radians(300), math.radians(60), 2)
                pygame.draw.arc(self.screen, (200,200,200), (icon_x+6, icon_y+4, 26, 28), math.radians(300), math.radians(60), 1)
            else:
                # draw small X to indicate muted
                pygame.draw.line(self.screen, (220,80,80), (icon_x+8, icon_y+8), (icon_x+28, icon_y+28), 3)
                pygame.draw.line(self.screen, (220,80,80), (icon_x+28, icon_y+8), (icon_x+8, icon_y+28), 3)
            # store rect for click checks
            self.sound_icon_rect = rect

        elif self.game_state == STATE_GAMEOVER:
            # Game over screen
            gameover_text = self.large_font.render("Game Over!", True, (255,50,50))
            score_text = self.font.render(f"Score: {self.score}", True, (255,255,255))
            self.screen.blit(gameover_text, (WIDTH//2 - gameover_text.get_width()//2, HEIGHT//4))
            self.screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//4 + 80))

            # New high flash
            if self.new_high:
                ratio = self.new_high_timer / 120.0
                pulse = 1.0 + 0.18 * math.sin(pygame.time.get_ticks() / 120.0)
                nh_text = self.large_font.render("NEW HIGH SCORE!", True, (255,215,0))
                nh_w = int(nh_text.get_width() * pulse)
                nh_h = int(nh_text.get_height() * pulse)
                nh_surf = pygame.transform.smoothscale(nh_text, (nh_w, nh_h))
                nh_x = WIDTH//2 - nh_w//2
                nh_y = HEIGHT//4 - nh_h - 10
                glow = pygame.Surface((nh_w+40, nh_h+20), pygame.SRCALPHA)
                glow.fill((0,0,0,0))
                gcol = (255, 220, 80, int(160 * ratio))
                pygame.draw.ellipse(glow, gcol, glow.get_rect())
                self.screen.blit(glow, (nh_x-20, nh_y-10))
                self.screen.blit(nh_surf, (nh_x, nh_y))

            # game over menu options
            menu_start_y = HEIGHT//2
            for i, opt in enumerate(self.gameover_options):
                is_selected = (i == self.selected_menu_gameover)
                is_hover = (i == getattr(self, 'hovered_gameover', None))
                if is_selected:
                    color = (255,255,255)
                elif is_hover:
                    color = (235,235,235)
                else:
                    color = (200,200,200)
                text = self.font.render(opt, True, color)
                x = WIDTH//2 - text.get_width()//2
                y = menu_start_y + i*48
                if is_selected:
                    pygame.draw.rect(self.screen, (40,40,60), (x-12, y-6, text.get_width()+24, text.get_height()+8), border_radius=8)
                elif is_hover:
                    pygame.draw.rect(self.screen, (30,30,50), (x-12, y-6, text.get_width()+24, text.get_height()+8), border_radius=8)
                self.screen.blit(text, (x, y))
                if i == self.selected_menu_gameover:
                    pulse_a = 6 * math.sin(pygame.time.get_ticks() / self.cursor_pulse_speed)
                    ax = x - 28 + int(pulse_a)
                    ay = y + text.get_height()//2
                    pygame.draw.polygon(self.screen, (255,255,255), [(ax, ay), (ax+10, ay-8), (ax+10, ay+8)])

            hint = self.font.render("Use Up/Down to choose — Enter to confirm", True, (180,180,180))
            self.screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 70))

        elif self.game_state == STATE_PLAYING:
            # Draw game content to an offscreen surface so we can apply screen shake
            play_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            play_surf.fill((10,10,30))

            # draw game objects onto play_surf
            self.player.draw(play_surf)
            self.orb.draw(play_surf)
            for pu in self.powerups:
                try:
                    pu.draw(play_surf)
                except Exception:
                    pass
            for ob in self.obstacles:
                ob.draw(play_surf)

            for proj in self.projectiles:
                proj.draw(play_surf)

            # HUD
            self.draw_hud(play_surf)

            # compute shake offset
            offset_x = 0
            offset_y = 0
            if self.shake_timer > 0:
                mag = self.shake_magnitude
                offset_x = random.randint(-mag, mag)
                offset_y = random.randint(-mag, mag)

            # blit the play surface
            self.screen.blit(play_surf, (offset_x, offset_y))

        # Settings overlay drawing (distinct panel + full-screen dim when active)
        if self.show_settings or self.overlay_alpha > 0:
            # full-screen dim to separate background from settings
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim_alpha = int(min(200, max(0, self.overlay_alpha))) if self.overlay_alpha is not None else 180
            dim.fill((0, 0, 0, dim_alpha))
            self.screen.blit(dim, (0,0))

            # panel
            panel_w, panel_h = WIDTH - 240, HEIGHT - 240
            panel_x, panel_y = 120, 120
            panel = pygame.Surface((panel_w, panel_h))
            panel.fill((18,18,22))
            # border
            pygame.draw.rect(panel, (80,80,90), panel.get_rect(), width=2, border_radius=8)
            self.screen.blit(panel, (panel_x, panel_y))

            # settings contents
            title = self.large_font.render("Settings", True, (255,255,255))
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, panel_y + 12))
            for idx, opt in enumerate(self.settings_options):
                color = (200,200,200) if idx != self.settings_selected else (255,255,255)
                # hover highlight for settings list
                if idx == getattr(self, 'hovered_settings', None) and idx != self.settings_selected:
                    pygame.draw.rect(self.screen, (36,36,48), (panel_x + 34, panel_y + 90 + idx*48 - 6,  self.font.size(opt)[0] + 12, self.font.get_height() + 8), border_radius=6)
                if opt == "Music Volume":
                    txt = self.font.render(f"{opt}: {int(self.music_volume*100)}%", True, color)
                    self.screen.blit(txt, (panel_x + 40, panel_y + 90 + idx*48))
                elif opt == "Difficulty":
                    txt = self.font.render(f"{opt}: {self.difficulty_levels[self.difficulty_index]}", True, color)
                    self.screen.blit(txt, (panel_x + 40, panel_y + 90 + idx*48))
                elif opt == "Player Color":
                    txt = self.font.render(f"{opt}", True, color)
                    self.screen.blit(txt, (panel_x + 40, panel_y + 90 + idx*48))
                    # draw swatch
                    sw = 40
                    sw_x = panel_x + panel_w - 40 - sw
                    sw_y = panel_y + 90 + idx*48
                    pygame.draw.rect(self.screen, self.player_colors[self.player_color_index], (sw_x, sw_y, sw, sw), border_radius=6)
                    pygame.draw.rect(self.screen, (180,180,180), (sw_x, sw_y, sw, sw), width=2, border_radius=6)
                else:
                    txt = self.font.render(opt, True, color)
                    self.screen.blit(txt, (panel_x + 40, panel_y + 90 + idx*48))

        # Draw tooltip at bottom
        if self.tooltip_text:
            tip = self.font.render(self.tooltip_text, True, (180,180,180))
            self.screen.blit(tip, (WIDTH//2 - tip.get_width()//2, HEIGHT - 40))

        # Credits scrolling advance handled in update() or when opening credits
        # ensure display updated by caller
