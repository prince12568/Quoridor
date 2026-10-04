"""Search: evaluation function, candidate move generation, plain Minimax.

Only Minimax (no Alpha-Beta) and A* are used, as planned. Because plain
Minimax cannot prune, the branching factor is kept small by generating only
*useful* wall candidates (see candidate_walls).
"""
from game import GOAL_ROW, WALL_ANCHORS

WIN = 1000          # score for a won position
WALL_WEIGHT = 0.3   # value of having more walls left than the opponent


def evaluate(state, me):
    """Static score from `me`'s point of view.

    eval = opponent_path - my_path  (+ small bonus for spare walls)
    Both paths come from A*.
    """
    opp = 1 - me
    mine = state.shortest(me)
    theirs = state.shortest(opp)
    return (theirs - mine) + WALL_WEIGHT * (state.walls_left[me] - state.walls_left[opp])


def _blocking_walls(a, b):
    """The two walls (same orientation) that would block the edge a -> b."""
    (r1, c1), (r2, c2) = a, b
    if c1 == c2:                       # vertical step -> horizontal wall
        r = min(r1, r2)
        return [('h', r, c1), ('h', r, c1 - 1)]
    c = min(c1, c2)                    # horizontal step -> vertical wall
    return [('v', r1, c), ('v', r1 - 1, c)]


def candidate_walls(state, player, limit):
    """Walls worth considering for `player`.

    Candidates are walls that touch the opponent's current shortest path, plus
    walls around the opponent pawn. Each is scored by its net effect

        (opp_path_after - opp_path_before) - (my_path_after - my_path_before)

    Illegal walls (overlap / sealing a pawn in) are dropped, and so are walls
    that don't gain at least 1. The best `limit` walls are returned.
    """
    if state.walls_left[player] <= 0:
        return []
    opp = 1 - player
    opp_len, path = state.shortest(opp, True)
    my_len = state.shortest(player)

    cands = set()
    for a, b in zip(path, path[1:]):
        cands.update(_blocking_walls(a, b))
    orow, ocol = state.pawns[opp]
    for r in (orow - 1, orow):
        for c in (ocol - 1, ocol):
            cands.add(('h', r, c))
            cands.add(('v', r, c))

    scored = []
    for o, r, c in cands:
        if not (0 <= r < WALL_ANCHORS and 0 <= c < WALL_ANCHORS):
            continue
        res = state.try_wall(o, r, c)       # A* for both pawns; None if illegal
        if res is None:
            continue
        net = (res[opp] - opp_len) - (res[player] - my_len)
        if net >= 1:
            scored.append((-net, o, r, c))
    scored.sort()
    return [('w', o, r, c) for _, o, r, c in scored[:limit]]


def generate_moves(state, wall_limit=6):
    """All legal pawn moves + the best candidate walls for the side to move."""
    moves = [('m', cell) for cell in state.legal_pawn_moves()]
    moves += candidate_walls(state, state.turn, wall_limit)
    if not moves:
        moves = [('p',)]
    return moves


def minimax_search(state, depth, wall_limit=6, rng=None):
    """Plain Minimax. Returns (best_move, value, nodes_visited).

    The side to move at the root is the maximizer. Moves are applied and
    undone in place on a private copy of the state.
    """
    state = state.copy()
    me = state.turn
    nodes = [0]

    def value(d):
        nodes[0] += 1
        w = state.winner()
        if w is not None:                       # prefer faster wins / slower losses
            return (WIN + d) if w == me else -(WIN + d)
        if d == 0:
            return evaluate(state, me)
        maximizing = state.turn == me
        best = float('-inf') if maximizing else float('inf')
        for mv in generate_moves(state, wall_limit):
            rec = state.apply(mv)
            v = value(d - 1)
            state.undo(mv, rec)
            if maximizing:
                if v > best:
                    best = v
            elif v < best:
                best = v
        return best

    best_val = float('-inf')
    best_moves = []
    for mv in generate_moves(state, wall_limit):
        rec = state.apply(mv)
        v = value(depth - 1)
        state.undo(mv, rec)
        if v > best_val:
            best_val, best_moves = v, [mv]
        elif v == best_val:
            best_moves.append(mv)

    if rng is not None and len(best_moves) > 1:
        move = rng.choice(best_moves)
    else:
        move = best_moves[0]
    return move, best_val, nodes[0]
