import pygame
import sys
from game import Game, STATE_PLAYING, STATE_START, STATE_GAMEOVER

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("LightRunner")

game = Game(screen)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # delegate most key handling to the Game (menus / gameover)
        elif event.type == pygame.KEYDOWN:
            game.handle_event(event)
            if getattr(game, 'request_quit', False):
                pygame.quit()
                sys.exit()
        # forward mouse clicks to the game (e.g. sound icon in main menu)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(game, 'handle_mouse'):
                game.handle_mouse(event)
                if getattr(game, 'request_quit', False):
                    pygame.quit()
                    sys.exit()

    if game.game_state == STATE_PLAYING:
        game.update()

    game.draw()
    pygame.display.flip()
    game.clock.tick(60)
