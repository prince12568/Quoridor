"""Run with:  python tests.py   (no pygame needed)"""
import random
import unittest

from game import State
from search import minimax_search, evaluate, generate_moves
from agents import make_agent


def fresh(p0=None, p1=None, turn=0):
    s = State()
    if p0:
        s.pawns[0] = p0
    if p1:
        s.pawns[1] = p1
    s.turn = turn
    return s


class TestPawnMoves(unittest.TestCase):
    def test_start_moves(self):
        self.assertEqual(set(State().legal_pawn_moves()), {(7, 4), (8, 3), (8, 5)})

    def test_wall_blocks_forward_both_columns(self):
        for anchor_col in (3, 4):             # h wall covers cols c and c+1
            s = State()
            s.h_walls[7][anchor_col] = True
            self.assertEqual(set(s.legal_pawn_moves()), {(8, 3), (8, 5)})

    def test_straight_jump(self):
        s = fresh((4, 4), (3, 4))
        m = set(s.legal_pawn_moves())
        self.assertIn((2, 4), m)
        self.assertNotIn((3, 4), m)

    def test_diagonal_when_wall_behind(self):
        s = fresh((4, 4), (3, 4))
        s.h_walls[2][4] = True                # wall behind opponent (rows 2|3, cols 4-5)
        m = set(s.legal_pawn_moves())
        self.assertEqual(m, {(3, 3), (3, 5), (4, 3), (4, 5), (5, 4)})

    def test_diagonal_at_board_edge(self):
        s = fresh((1, 4), (0, 4))
        m = set(s.legal_pawn_moves())
        self.assertEqual(m, {(0, 3), (0, 5), (1, 3), (1, 5), (2, 4)})

    def test_side_step_blocked_by_wall(self):
        s = fresh((4, 4), (3, 4))
        s.h_walls[2][4] = True
        s.v_walls[2][3] = True                # blocks (3,3)|(3,4)
        m = set(s.legal_pawn_moves())
        self.assertNotIn((3, 3), m)
        self.assertIn((3, 5), m)


class TestWalls(unittest.TestCase):
    def test_overlap_and_cross_rejected(self):
        s = State()
        s.h_walls[4][4] = True
        self.assertFalse(s.wall_slot_free('h', 4, 4))   # same slot
        self.assertFalse(s.wall_slot_free('h', 4, 3))   # overlaps right half
        self.assertFalse(s.wall_slot_free('h', 4, 5))   # overlaps left half
        self.assertFalse(s.wall_slot_free('v', 4, 4))   # crosses
        self.assertTrue(s.wall_slot_free('h', 4, 2))    # touching ends is fine
        self.assertTrue(s.wall_slot_free('v', 3, 4))

    def test_out_of_range(self):
        s = State()
        self.assertFalse(s.wall_slot_free('h', 8, 0))
        self.assertFalse(s.wall_slot_free('v', 0, -1))

    def test_sealing_wall_is_illegal(self):
        s = fresh((8, 0), (0, 4))
        s.h_walls[7][0] = True                # blocks (8,0) and (8,1) going up
        self.assertIsNotNone(s.shortest(0))
        self.assertIsNone(s.try_wall('v', 7, 1))   # would seal pawn in {(8,0),(8,1)}
        self.assertTrue(s.wall_slot_free('v', 7, 1))
        self.assertFalse(s.is_legal_wall('v', 7, 1))

    def test_try_wall_leaves_board_unchanged(self):
        s = State()
        before = [r[:] for r in s.h_walls]
        s.try_wall('h', 3, 3)
        self.assertEqual(before, s.h_walls)

    def test_walls_run_out(self):
        s = State()
        s.walls_left[0] = 0
        self.assertFalse(s.is_legal_wall('h', 3, 3))


class TestAStar(unittest.TestCase):
    def test_open_board(self):
        s = State()
        self.assertEqual(s.shortest(0), 8)
        self.assertEqual(s.shortest(1), 8)

    def test_detour_around_wall(self):
        s = State()
        s.h_walls[7][4] = True                # blocks cols 4,5 in front of P0
        self.assertEqual(s.shortest(0), 9)    # one sidestep to col 3, then straight

    def test_path_cells_are_connected(self):
        s = State()
        s.h_walls[3][3] = True
        s.v_walls[5][5] = True
        n, path = s.shortest(0, True)
        self.assertEqual(n, len(path) - 1)
        for a, b in zip(path, path[1:]):
            self.assertTrue(s.can_step(a, b))


class TestApplyUndo(unittest.TestCase):
    def test_roundtrip(self):
        s = State()
        snap = s.copy()
        for mv in [('m', (7, 4)), ('w', 'h', 3, 3), ('m', (0, 3))]:
            rec = s.apply(mv)
            s.undo(mv, rec)
            self.assertEqual((s.pawns, s.walls_left, s.turn, s.h_walls, s.v_walls),
                             (snap.pawns, snap.walls_left, snap.turn, snap.h_walls, snap.v_walls))

    def test_winner(self):
        s = fresh((0, 2), (3, 3))
        self.assertEqual(s.winner(), 0)
        s = fresh((5, 5), (8, 1))
        self.assertEqual(s.winner(), 1)


class TestSearch(unittest.TestCase):
    def test_takes_immediate_win(self):
        s = fresh((1, 4), (6, 0))
        for depth in (1, 2):
            move, val, _ = minimax_search(s, depth)
            self.assertEqual(move, ('m', (0, 4)))
            self.assertGreater(val, 900)

    def test_blocks_imminent_loss(self):
        # Red (to move) is 1 step from winning... Blue at (3,3) far; Red at (7,4)
        # but Blue (P0) is about to win at (1,4) -> Red must wall or lose.
        s = fresh((1, 4), (5, 0), turn=1)
        move, val, _ = minimax_search(s, 2)
        self.assertEqual(move[0], 'w')

    def test_eval_symmetric_start(self):
        self.assertEqual(evaluate(State(), 0), 0)

    def test_generated_walls_are_legal(self):
        s = State()
        s.apply(('m', (7, 4)))
        for mv in generate_moves(s):
            self.assertTrue(s.is_legal_move(mv), mv)


class TestAgentsPlayFullGame(unittest.TestCase):
    def _play(self, kinds, max_plies=300):
        s = State()
        agents = [make_agent(k) for k in kinds]
        for _ in range(max_plies):
            if s.winner() is not None:
                break
            mv = agents[s.turn].choose_move(s)
            self.assertTrue(s.is_legal_move(mv), mv)
            s.apply(mv)
        return s.winner()

    def test_random_vs_random_finishes_legally(self):
        random.seed(1)
        self._play(['random', 'random'])

    def test_greedy_beats_random(self):
        random.seed(2)
        wins = sum(self._play(['greedy', 'random']) == 0 for _ in range(3))
        self.assertGreaterEqual(wins, 2)

    def test_minimax2_beats_random(self):
        random.seed(3)
        self.assertEqual(self._play(['minimax:2', 'random']), 0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
