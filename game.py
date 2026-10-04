"""Quoridor rules: board state, pawn moves, jumps and wall placement.

Coordinates are (row, col), both 0..8. Row 0 is the TOP of the board.
  Player 0 (Blue) starts at the bottom (8, 4) and must reach row 0.
  Player 1 (Red)  starts at the top    (0, 4) and must reach row 8.

Walls live BETWEEN cells, so they are stored in two 8x8 boolean arrays.
Each array entry is an "anchor" (the intersection point of four cells):
  h_walls[r][c]: horizontal wall on the boundary between row r and r+1,
                 covering columns c and c+1.
  v_walls[r][c]: vertical wall on the boundary between column c and c+1,
                 covering rows r and r+1.

Moves are tuples:
  ('m', (r, c))      move pawn to cell
  ('w', 'h'|'v', r, c)  place a wall
  ('p',)             pass (only when a pawn has literally no legal move)
"""
from pathfinding import astar

SIZE = 9
WALL_ANCHORS = 8
WALLS_PER_PLAYER = 10
GOAL_ROW = (0, 8)
START = ((8, 4), (0, 4))
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class State:
    def __init__(self):
        self.pawns = [START[0], START[1]]
        self.walls_left = [WALLS_PER_PLAYER, WALLS_PER_PLAYER]
        self.h_walls = [[False] * WALL_ANCHORS for _ in range(WALL_ANCHORS)]
        self.v_walls = [[False] * WALL_ANCHORS for _ in range(WALL_ANCHORS)]
        self.turn = 0

    def copy(self):
        s = State.__new__(State)
        s.pawns = list(self.pawns)
        s.walls_left = list(self.walls_left)
        s.h_walls = [row[:] for row in self.h_walls]
        s.v_walls = [row[:] for row in self.v_walls]
        s.turn = self.turn
        return s

    # ------------------------------------------------------------------
    # Edges between cells (walls only, pawns are not considered here)
    # ------------------------------------------------------------------
    def _blocked_down(self, r, c):
        """Edge between (r, c) and (r+1, c). r in 0..7, c in 0..8."""
        h = self.h_walls
        return (c < 8 and h[r][c]) or (c > 0 and h[r][c - 1])

    def _blocked_right(self, r, c):
        """Edge between (r, c) and (r, c+1). r in 0..8, c in 0..7."""
        v = self.v_walls
        return (r < 8 and v[r][c]) or (r > 0 and v[r - 1][c])

    def can_step(self, a, b):
        """True if b is on the board, adjacent to a, and no wall is between."""
        r2, c2 = b
        if not (0 <= r2 < SIZE and 0 <= c2 < SIZE):
            return False
        r, c = a
        if r2 == r + 1:
            return not self._blocked_down(r, c)
        if r2 == r - 1:
            return not self._blocked_down(r2, c)
        if c2 == c + 1:
            return not self._blocked_right(r, c)
        return not self._blocked_right(r, c2)

    def neighbors(self, cell):
        """Adjacent cells reachable without crossing a wall (used by A*)."""
        r, c = cell
        out = []
        if r > 0 and not self._blocked_down(r - 1, c):
            out.append((r - 1, c))
        if r < 8 and not self._blocked_down(r, c):
            out.append((r + 1, c))
        if c > 0 and not self._blocked_right(r, c - 1):
            out.append((r, c - 1))
        if c < 8 and not self._blocked_right(r, c):
            out.append((r, c + 1))
        return out

    # ------------------------------------------------------------------
    # Pawn moves (including jumps)
    # ------------------------------------------------------------------
    def legal_pawn_moves(self, player=None):
        pl = self.turn if player is None else player
        p = self.pawns[pl]
        o = self.pawns[1 - pl]
        moves = []
        for dr, dc in DIRS:
            n = (p[0] + dr, p[1] + dc)
            if not self.can_step(p, n):
                continue
            if n != o:
                moves.append(n)
                continue
            # Opponent is adjacent: try to jump straight over.
            j = (n[0] + dr, n[1] + dc)
            if self.can_step(n, j):
                moves.append(j)
            else:
                # Blocked behind (wall or edge): side-step diagonally.
                for sr, sc in ((dc, dr), (-dc, -dr)):
                    m = (n[0] + sr, n[1] + sc)
                    if self.can_step(n, m):
                        moves.append(m)
        return moves

    # ------------------------------------------------------------------
    # Walls
    # ------------------------------------------------------------------
    def wall_slot_free(self, o, r, c):
        """Slot is on the board and doesn't overlap or cross another wall."""
        if not (0 <= r < WALL_ANCHORS and 0 <= c < WALL_ANCHORS):
            return False
        h, v = self.h_walls, self.v_walls
        if o == 'h':
            return not (h[r][c] or v[r][c]
                        or (c > 0 and h[r][c - 1])
                        or (c < 7 and h[r][c + 1]))
        return not (v[r][c] or h[r][c]
                    or (r > 0 and v[r - 1][c])
                    or (r < 7 and v[r + 1][c]))

    def shortest(self, player, want_path=False):
        """A* shortest path length (or (length, path)) for a player."""
        return astar(self, self.pawns[player], GOAL_ROW[player], want_path)

    def try_wall(self, o, r, c):
        """Temporarily place a wall and return (len_p0, len_p1) of the
        shortest paths afterwards, or None if the wall is illegal
        (bad slot, or it seals either pawn off from its goal row).
        The board is left unchanged."""
        if not self.wall_slot_free(o, r, c):
            return None
        arr = self.h_walls if o == 'h' else self.v_walls
        arr[r][c] = True
        try:
            l0 = self.shortest(0)
            if l0 is None:
                return None
            l1 = self.shortest(1)
            if l1 is None:
                return None
            return (l0, l1)
        finally:
            arr[r][c] = False

    def is_legal_wall(self, o, r, c, player=None):
        pl = self.turn if player is None else player
        if self.walls_left[pl] <= 0:
            return False
        return self.try_wall(o, r, c) is not None

    # ------------------------------------------------------------------
    # Moves: validate / apply / undo
    # ------------------------------------------------------------------
    def is_legal_move(self, move):
        if move[0] == 'm':
            return move[1] in self.legal_pawn_moves()
        if move[0] == 'w':
            return self.is_legal_wall(move[1], move[2], move[3])
        if move[0] == 'p':
            return not self.legal_pawn_moves()
        return False

    def apply(self, move):
        """Apply a move in place and return an undo record for undo()."""
        pl = self.turn
        rec = None
        if move[0] == 'm':
            rec = self.pawns[pl]
            self.pawns[pl] = move[1]
        elif move[0] == 'w':
            _, o, r, c = move
            (self.h_walls if o == 'h' else self.v_walls)[r][c] = True
            self.walls_left[pl] -= 1
        self.turn = 1 - pl
        return rec

    def undo(self, move, rec):
        self.turn = 1 - self.turn
        pl = self.turn
        if move[0] == 'm':
            self.pawns[pl] = rec
        elif move[0] == 'w':
            _, o, r, c = move
            (self.h_walls if o == 'h' else self.v_walls)[r][c] = False
            self.walls_left[pl] += 1

    def winner(self):
        if self.pawns[0][0] == GOAL_ROW[0]:
            return 0
        if self.pawns[1][0] == GOAL_ROW[1]:
            return 1
        return None


def move_to_str(move):
    if move[0] == 'm':
        return "moves to (%d,%d)" % move[1]
    if move[0] == 'w':
        kind = "horizontal" if move[1] == 'h' else "vertical"
        return "wall %s @(%d,%d)" % (kind, move[2], move[3])
    return "passes"
