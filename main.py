"""Quoridor with A* + Minimax.

  python main.py                                  # start menu
  python main.py --p0 human --p1 minimax:3        # skip the menu
  python main.py --p0 greedy --p1 minimax:2       # watch AI vs AI

Player types: human, random, greedy, minimax:N   (N = search depth)
Player 0 (Blue) starts at the bottom and moves first.
"""
import argparse

import pygame

import ui


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--p0', help='Blue player type')
    ap.add_argument('--p1', help='Red player type')
    args = ap.parse_args()

    pygame.init()
    pygame.display.set_caption("Quoridor - A* + Minimax")
    screen = pygame.display.set_mode((ui.WIDTH, ui.HEIGHT))

    direct = (args.p0, args.p1) if args.p0 and args.p1 else None
    while True:
        kinds = direct or ui.run_menu(screen)
        if kinds is None:
            break
        if ui.run_game(screen, kinds) == 'quit':
            break
        direct = None            # after the first game, go back to the menu
    pygame.quit()


if __name__ == '__main__':
    main()
