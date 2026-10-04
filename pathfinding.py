"""A* shortest path for Quoridor.

The goal is "any cell in the target row", so the heuristic is the row
distance to that row. It never overestimates (every step moves at most one
row), so A* returns the true shortest path length.

Pawns are ignored here: the standard Quoridor path rule only cares about walls.
"""
import heapq


def astar(state, start, goal_row, want_path=False):
    """Return the shortest path length from `start` to `goal_row`.

    Returns None if no path exists (used to reject walls that seal a pawn in).
    If want_path is True, returns (length, [cells]) or (None, None).
    """
    open_heap = [(abs(start[0] - goal_row), 0, start)]
    best_g = {start: 0}
    parent = {}
    closed = set()

    while open_heap:
        _, g, cell = heapq.heappop(open_heap)
        if cell in closed:
            continue
        closed.add(cell)

        if cell[0] == goal_row:
            if not want_path:
                return g
            path = [cell]
            while cell in parent:
                cell = parent[cell]
                path.append(cell)
            path.reverse()
            return g, path

        ng = g + 1
        for nxt in state.neighbors(cell):
            if nxt in closed:
                continue
            if ng < best_g.get(nxt, 1 << 30):
                best_g[nxt] = ng
                parent[nxt] = cell
                heapq.heappush(open_heap, (ng + abs(nxt[0] - goal_row), ng, nxt))

    return (None, None) if want_path else None
