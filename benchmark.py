"""Round-robin benchmark: win rate and average time per move.

Examples:
  python benchmark.py
  python benchmark.py --games 10 --agents random minimax:2 minimax:3 minimax:4
"""
import argparse
import itertools
import random
import time

from game import State
from agents import make_agent

MAX_PLIES = 200   # games longer than this count as a draw


def play(kind0, kind1):
    """Play one game. Returns (winner or None, [total_time, moves] per player)."""
    s = State()
    agents = [make_agent(kind0), make_agent(kind1)]
    timing = [[0.0, 0], [0.0, 0]]
    for _ in range(MAX_PLIES):
        if s.winner() is not None:
            break
        pl = s.turn
        t0 = time.time()
        mv = agents[pl].choose_move(s)
        timing[pl][0] += time.time() - t0
        timing[pl][1] += 1
        s.apply(mv)
    return s.winner(), timing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=6, help='games per pairing (even number)')
    ap.add_argument('--agents', nargs='+', default=['random', 'minimax:2', 'minimax:3'])
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()
    random.seed(args.seed)

    stats = {a: {'time': 0.0, 'moves': 0} for a in args.agents}
    print("%-12s vs %-12s  %s" % ("A", "B", "A wins / B wins / draws"))
    for a, b in itertools.combinations(args.agents, 2):
        wa = wb = dr = 0
        for g in range(args.games):
            first_is_a = g % 2 == 0          # alternate who moves first
            k0, k1 = (a, b) if first_is_a else (b, a)
            w, timing = play(k0, k1)
            for pl, kind in enumerate((k0, k1)):
                stats[kind]['time'] += timing[pl][0]
                stats[kind]['moves'] += timing[pl][1]
            if w is None:
                dr += 1
            elif (w == 0) == first_is_a:
                wa += 1
            else:
                wb += 1
        print("%-12s vs %-12s  %d / %d / %d" % (a, b, wa, wb, dr))

    print("\nAverage time per move")
    for a, st in stats.items():
        avg = st['time'] / max(1, st['moves'])
        print("  %-12s %.4f s" % (a, avg))


if __name__ == '__main__':
    main()
