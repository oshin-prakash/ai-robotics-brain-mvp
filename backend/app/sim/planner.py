from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from app.sim.world import World2D

GridPoint = tuple[float, float]


@dataclass
class AStarPlanner:
    world: World2D
    resolution_m: float = 0.25
    inflation_margin_m: float = 0.15

    def _to_cell(self, x: float, y: float) -> tuple[int, int]:
        cols = max(1, int(math.floor(self.world.width / self.resolution_m)))
        rows = max(1, int(math.floor(self.world.height / self.resolution_m)))
        c = max(0, min(cols - 1, int(x / self.resolution_m)))
        r = max(0, min(rows - 1, int(y / self.resolution_m)))
        return (r, c)

    def _to_world(self, row: int, col: int) -> GridPoint:
        x = min(self.world.width, round((col + 0.5) * self.resolution_m, 4))
        y = min(self.world.height, round((row + 0.5) * self.resolution_m, 4))
        return (x, y)

    def _is_cell_free(self, row: int, col: int) -> bool:
        cols = int(math.floor(self.world.width / self.resolution_m))
        rows = int(math.floor(self.world.height / self.resolution_m))
        if not (0 <= row < rows and 0 <= col < cols):
            return False
        wx, wy = self._to_world(row, col)
        return self.world.is_position_free(wx, wy, extra_margin=self.inflation_margin_m)

    def plan(self, start_xy: GridPoint, goal_xy: GridPoint) -> list[GridPoint]:
        start = self._to_cell(start_xy[0], start_xy[1])
        goal = self._to_cell(goal_xy[0], goal_xy[1])

        if not self._is_cell_free(goal[0], goal[1]):
            return []

        if start == goal:
            return [(round(goal_xy[0], 4), round(goal_xy[1], 4))]

        neighbors = [
            (-1, 0, 1.0),
            (1, 0, 1.0),
            (0, -1, 1.0),
            (0, 1, 1.0),
            (-1, -1, math.sqrt(2.0)),
            (-1, 1, math.sqrt(2.0)),
            (1, -1, math.sqrt(2.0)),
            (1, 1, math.sqrt(2.0)),
        ]

        open_heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0.0}
        closed: set[tuple[int, int]] = set()

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current in closed:
                continue

            if current == goal:
                waypoints: list[GridPoint] = []
                node: tuple[int, int] | None = current
                while node is not None:
                    waypoints.append(self._to_world(node[0], node[1]))
                    node = came_from.get(node)
                waypoints.reverse()
                waypoints[-1] = (round(goal_xy[0], 4), round(goal_xy[1], 4))
                return waypoints

            closed.add(current)
            cr, cc = current

            for dr, dc, step_cost in neighbors:
                nxt = (cr + dr, cc + dc)
                if nxt in closed or not self._is_cell_free(nxt[0], nxt[1]):
                    continue
                tentative_g = g_score[current] + step_cost
                if tentative_g < g_score.get(nxt, float("inf")):
                    came_from[nxt] = current
                    g_score[nxt] = tentative_g
                    h = math.hypot(goal[0] - nxt[0], goal[1] - nxt[1])
                    heapq.heappush(open_heap, (tentative_g + h, nxt))

        return []