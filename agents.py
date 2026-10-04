"""Agents. Each has choose_move(state) -> move and a .name / .last_info."""
import random
import time

from search import evaluate, generate_moves, minimax_search, WIN


class RandomAgent:
    name = "Random AI"

    def __init__(self):
        self.last_info = ""

    def choose_move(self, state):
        pl = state.turn
        if state.walls_left[pl] > 0 and random.random() < 0.25:
            for _ in range(40):
                o = random.choice('hv')
                r, c = random.randrange(8), random.randrange(8)
                if state.try_wall(o, r, c) is not None:
                    return ('w', o, r, c)
        moves = state.legal_pawn_moves()
        return ('m', random.choice(moves)) if moves else ('p',)


class GreedyAgent:
    """One-step lookahead: pick the move with the best evaluation right after
    playing it (equivalent to Minimax at depth 1). Walls are scored by their
    net effect on both paths, so a wall is only used when it gains more than
    simply stepping forward."""
    name = "Greedy AI"

    def __init__(self, wall_limit=10):
        self.wall_limit = wall_limit
        self.last_info = ""

    def choose_move(self, state):
        t0 = time.time()
        s = state.copy()
        me = s.turn
        best_val, best = float('-inf'), []
        for mv in generate_moves(s, self.wall_limit):
            rec = s.apply(mv)
            w = s.winner()
            v = WIN if w == me else evaluate(s, me)
            s.undo(mv, rec)
            if v > best_val:
                best_val, best = v, [mv]
            elif v == best_val:
                best.append(mv)
        self.last_info = "eval %.1f, %.2fs" % (best_val, time.time() - t0)
        return random.choice(best)


class MinimaxAgent:
    def __init__(self, depth=2, wall_limit=6):
        self.depth = depth
        self.wall_limit = wall_limit
        self.name = "Minimax (depth %d)" % depth
        self.last_info = ""

    def choose_move(self, state):
        t0 = time.time()
        move, val, nodes = minimax_search(state, self.depth, self.wall_limit, random)
        self.last_info = "nodes %d, eval %.1f, %.2fs" % (nodes, val, time.time() - t0)
        return move


def make_agent(kind):
    """'human' -> None, 'random', 'greedy', 'minimax:N'."""
    if kind == 'human':
        return None
    if kind == 'random':
        return RandomAgent()
    if kind == 'greedy':
        return GreedyAgent()
    if kind.startswith('minimax'):
        depth = int(kind.split(':')[1]) if ':' in kind else 2
        return MinimaxAgent(depth)
    raise ValueError("unknown player type: %s" % kind)


def kind_label(kind):
    agent = make_agent(kind)
    return "Human" if agent is None else agent.name
