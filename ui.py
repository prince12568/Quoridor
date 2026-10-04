"""Pygame UI. Only draws the state and forwards input to game.py / agents.py."""
import random
import threading
import time

import pygame

from game import State, GOAL_ROW, move_to_str
from agents import make_agent, kind_label

# ---- layout ---------------------------------------------------------------
CELL = 56
GAP = 12
STEP = CELL + GAP
BOARD_PX = 9 * CELL + 8 * GAP
MARGIN = 30
BX = BY = MARGIN
SIDE_X = BX + BOARD_PX + MARGIN
SIDE_W = 270
WIDTH = SIDE_X + SIDE_W + MARGIN
HEIGHT = BOARD_PX + 2 * MARGIN

# ---- colours --------------------------------------------------------------
BG = (28, 31, 38)
PANEL = (40, 44, 54)
CELL_COL = (74, 80, 96)
CELL_HOVER = (96, 104, 124)
WALL_COL = (236, 190, 84)
OK_COL = (110, 200, 130)
BAD_COL = (225, 80, 80)
TEXT = (235, 237, 242)
DIM = (150, 156, 170)
PLAYER_COL = ((84, 154, 255), (240, 96, 96))
PLAYER_NAME = ("Blue", "Red")

_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def draw_text(surf, s, size, color, pos, center=False):
    img = font(size).render(s, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)
    return rect


def cell_rect(r, c):
    return pygame.Rect(BX + c * STEP, BY + r * STEP, CELL, CELL)


def cell_center(r, c):
    return cell_rect(r, c).center


def wall_rect(o, r, c):
    if o == 'h':
        return pygame.Rect(BX + c * STEP, BY + r * STEP + CELL, 2 * CELL + GAP, GAP)
    return pygame.Rect(BX + c * STEP + CELL, BY + r * STEP, GAP, 2 * CELL + GAP)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hit_test(mx, my, orient):
    """Map the mouse position to a board target.

    ('cell', (r, c))        mouse is over a cell
    ('wall', o, r, c)       mouse is in a gap -> wall under the cursor.
                            Over a horizontal gap -> horizontal wall, over a
                            vertical gap -> vertical wall, over the crossing
                            point -> whichever orientation is toggled (R).
    None                    outside the board
    """
    x, y = mx - BX, my - BY
    if x < 0 or y < 0 or x >= BOARD_PX or y >= BOARD_PX:
        return None
    col, ox = divmod(x, STEP)
    row, oy = divmod(y, STEP)
    in_x, in_y = ox < CELL, oy < CELL
    if in_x and in_y:
        return ('cell', (row, col))
    if in_x:                                    # gap below a cell -> horizontal wall
        c = col - 1 if ox < CELL / 2 else col
        return ('wall', 'h', _clamp(row, 0, 7), _clamp(c, 0, 7))
    if in_y:                                    # gap right of a cell -> vertical wall
        r = row - 1 if oy < CELL / 2 else row
        return ('wall', 'v', _clamp(r, 0, 7), _clamp(col, 0, 7))
    return ('wall', orient, _clamp(row, 0, 7), _clamp(col, 0, 7))


# ---------------------------------------------------------------------------
# Start menu
# ---------------------------------------------------------------------------
MENU_ITEMS = [
    ("Human vs Random AI", ("human", "random")),
    ("Human vs Greedy AI", ("human", "greedy")),
    ("Human vs Minimax AI  (depth 2, fast)", ("human", "minimax:2")),
    ("Human vs Minimax AI  (depth 3)", ("human", "minimax:3")),
    ("Human vs Minimax AI  (depth 4, slower)", ("human", "minimax:4")),
    ("AI vs AI:  Greedy vs Minimax (depth 2)", ("greedy", "minimax:2")),
    ("Human vs Human", ("human", "human")),
]


def run_menu(screen):
    """Returns (kind0, kind1) or None if the window was closed."""
    clock = pygame.time.Clock()
    bw, bh, gap = 540, 52, 12
    top = 170
    rects = [pygame.Rect((WIDTH - bw) // 2, top + i * (bh + gap), bw, bh)
             for i in range(len(MENU_ITEMS))]
    while True:
        mouse = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for rect, (_, kinds) in zip(rects, MENU_ITEMS):
                    if rect.collidepoint(e.pos):
                        return kinds
        screen.fill(BG)
        draw_text(screen, "QUORIDOR", 84, TEXT, (WIDTH // 2, 80), center=True)
        draw_text(screen, "A* pathfinding + Minimax search", 28, DIM, (WIDTH // 2, 130), center=True)
        for rect, (label, _) in zip(rects, MENU_ITEMS):
            hot = rect.collidepoint(mouse)
            pygame.draw.rect(screen, CELL_HOVER if hot else PANEL, rect, border_radius=10)
            draw_text(screen, label, 30, TEXT, rect.center, center=True)
        draw_text(screen, "Player 1 (Blue) starts at the bottom and moves first.",
                  24, DIM, (WIDTH // 2, HEIGHT - 40), center=True)
        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# Game screen
# ---------------------------------------------------------------------------
class GameScreen:
    def __init__(self, screen, kinds):
        self.screen = screen
        self.kinds = kinds
        self.orient = 'h'
        self.show_paths = False
        self.preview_cache = (None, False)
        self.reset()

    # ---- state -----------------------------------------------------------
    def reset(self):
        self.state = State()
        self.agents = [make_agent(k) for k in self.kinds]
        self.names = [kind_label(k) for k in self.kinds]
        self.thread = None
        self.box = None
        self.ready_at = time.time() + 0.3
        self.last_move = ""
        self.ai_info = ""
        self.plies = 0
        self.over = False
        self.refresh_info()

    def refresh_info(self):
        self.lens, self.paths = [], []
        for pl in (0, 1):
            n, path = self.state.shortest(pl, True)
            self.lens.append(n)
            self.paths.append(path)

    def both_ai(self):
        return all(a is not None for a in self.agents)

    def play(self, move):
        pl = self.state.turn
        self.state.apply(move)
        self.plies += 1
        self.last_move = "%s %s" % (PLAYER_NAME[pl], move_to_str(move))
        self.refresh_info()
        if self.state.winner() is not None:
            self.over = True
        self.ready_at = time.time() + (0.35 if self.both_ai() else 0.15)
        if not self.over and self.agents[self.state.turn] is None:
            # a human with no pawn move and no walls must pass
            s = self.state
            if not s.legal_pawn_moves() and s.walls_left[s.turn] == 0:
                self.play(('p',))

    # ---- AI in a background thread (keeps the window responsive) ---------
    def start_ai(self):
        agent = self.agents[self.state.turn]
        snapshot = self.state.copy()
        box = {}

        def work():
            box['move'] = agent.choose_move(snapshot)
            box['info'] = agent.last_info

        self.box = box
        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()

    def update(self):
        if self.over:
            return
        if self.agents[self.state.turn] is None:
            return
        if self.thread is None:
            if time.time() >= self.ready_at:
                self.start_ai()
        elif not self.thread.is_alive():
            move, info = self.box['move'], self.box['info']
            self.thread = None
            if not self.state.is_legal_move(move):       # safety net
                pawn = self.state.legal_pawn_moves()
                move = ('m', random.choice(pawn)) if pawn else ('p',)
            self.ai_info = info
            self.play(move)

    # ---- input -----------------------------------------------------------
    def human_turn(self):
        return (not self.over) and self.agents[self.state.turn] is None

    def handle_event(self, e):
        """Returns None, 'menu' or 'quit'."""
        if e.type == pygame.QUIT:
            return 'quit'
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_m):
                return 'menu'
            if e.key == pygame.K_n:
                self.reset()
            elif e.key == pygame.K_r:
                self.orient = 'v' if self.orient == 'h' else 'h'
            elif e.key == pygame.K_p:
                self.show_paths = not self.show_paths
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                self.orient = 'v' if self.orient == 'h' else 'h'
            elif e.button == 1 and self.human_turn():
                target = hit_test(e.pos[0], e.pos[1], self.orient)
                if target is None:
                    return None
                if target[0] == 'cell':
                    if target[1] in self.state.legal_pawn_moves():
                        self.play(('m', target[1]))
                else:
                    _, o, r, c = target
                    if self.state.is_legal_wall(o, r, c):
                        self.play(('w', o, r, c))
        return None

    def preview_legal(self, o, r, c):
        key = (o, r, c, self.plies)
        if self.preview_cache[0] != key:
            self.preview_cache = (key, self.state.is_legal_wall(o, r, c))
        return self.preview_cache[1]

    # ---- drawing ---------------------------------------------------------
    def draw(self):
        scr, st = self.screen, self.state
        scr.fill(BG)
        pygame.draw.rect(scr, PANEL, (BX - 8, BY - 8, BOARD_PX + 16, BOARD_PX + 16), border_radius=10)

        mouse = pygame.mouse.get_pos()
        target = hit_test(mouse[0], mouse[1], self.orient) if self.human_turn() else None
        legal = set(st.legal_pawn_moves()) if self.human_turn() else set()

        for r in range(9):
            for c in range(9):
                hot = target and target[0] == 'cell' and target[1] == (r, c) and (r, c) in legal
                pygame.draw.rect(scr, CELL_HOVER if hot else CELL_COL, cell_rect(r, c), border_radius=6)

        # goal edges
        pygame.draw.rect(scr, PLAYER_COL[0], (BX, BY - 7, BOARD_PX, 4), border_radius=2)
        pygame.draw.rect(scr, PLAYER_COL[1], (BX, BY + BOARD_PX + 3, BOARD_PX, 4), border_radius=2)

        # legal move dots
        for (r, c) in legal:
            pygame.draw.circle(scr, OK_COL, cell_center(r, c), 8)

        # shortest paths
        if self.show_paths:
            for pl in (0, 1):
                pts = [cell_center(*cell) for cell in self.paths[pl]]
                if len(pts) > 1:
                    pygame.draw.lines(scr, PLAYER_COL[pl], False, pts, 3)

        # placed walls
        for r in range(8):
            for c in range(8):
                if st.h_walls[r][c]:
                    pygame.draw.rect(scr, WALL_COL, wall_rect('h', r, c), border_radius=4)
                if st.v_walls[r][c]:
                    pygame.draw.rect(scr, WALL_COL, wall_rect('v', r, c), border_radius=4)

        # wall preview
        if target and target[0] == 'wall':
            _, o, r, c = target
            ok = self.preview_legal(o, r, c)
            pygame.draw.rect(scr, OK_COL if ok else BAD_COL, wall_rect(o, r, c), border_radius=4)

        # pawns
        for pl in (0, 1):
            cx, cy = cell_center(*st.pawns[pl])
            if st.turn == pl and not self.over:
                pygame.draw.circle(scr, TEXT, (cx, cy), 25, 3)
            pygame.draw.circle(scr, PLAYER_COL[pl], (cx, cy), 20)
            pygame.draw.circle(scr, (20, 20, 25), (cx, cy), 20, 2)

        self.draw_side()
        pygame.display.flip()

    def draw_side(self):
        scr, st = self.screen, self.state
        draw_text(scr, "QUORIDOR", 46, TEXT, (SIDE_X, BY - 6))

        y = BY + 48
        for pl in (0, 1):
            rect = pygame.Rect(SIDE_X, y, SIDE_W, 78)
            pygame.draw.rect(scr, PANEL, rect, border_radius=10)
            if st.turn == pl and not self.over:
                pygame.draw.rect(scr, PLAYER_COL[pl], rect, 3, border_radius=10)
            pygame.draw.circle(scr, PLAYER_COL[pl], (rect.x + 24, rect.y + 24), 12)
            draw_text(scr, "%s - %s" % (PLAYER_NAME[pl], self.names[pl]), 26, TEXT, (rect.x + 46, rect.y + 14))
            draw_text(scr, "Walls left: %d" % st.walls_left[pl], 24, DIM, (rect.x + 16, rect.y + 44))
            draw_text(scr, "A* path: %s" % self.lens[pl], 24, DIM, (rect.x + 150, rect.y + 44))
            y += 90

        # status
        if self.over:
            w = st.winner()
            msg, col = "%s wins!" % PLAYER_NAME[w], PLAYER_COL[w]
        elif self.agents[st.turn] is None:
            msg, col = "%s: your move" % PLAYER_NAME[st.turn], PLAYER_COL[st.turn]
        else:
            dots = "." * (1 + int(time.time() * 3) % 3)
            msg, col = "%s thinking%s" % (PLAYER_NAME[st.turn], dots), PLAYER_COL[st.turn]
        draw_text(scr, msg, 36, col, (SIDE_X, y + 6))
        y += 46
        if self.last_move:
            draw_text(scr, self.last_move, 22, DIM, (SIDE_X, y))
        y += 22
        if self.ai_info:
            draw_text(scr, self.ai_info, 20, DIM, (SIDE_X, y))
        y += 34

        mode = "horizontal" if self.orient == 'h' else "vertical"
        help_lines = [
            "Click a green dot to move",
            "Click a gap to place a wall",
            "R / right-click: rotate (%s)" % mode,
            "P: show shortest paths",
            "N: new game   M/Esc: menu",
        ]
        for i, line in enumerate(help_lines):
            draw_text(scr, line, 22, DIM, (SIDE_X, HEIGHT - MARGIN - 22 * (len(help_lines) - i) - 4))


def run_game(screen, kinds):
    """Returns 'menu' or 'quit'."""
    game = GameScreen(screen, kinds)
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            res = game.handle_event(e)
            if res:
                return res
        game.update()
        game.draw()
        clock.tick(60)
