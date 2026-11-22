from __future__ import annotations

import math
from dataclasses import dataclass

from app.sim.world import RobotPose, World2D


@dataclass
class LidarReading:
    angles_rad: list[float]
    ranges_m: list[float]
    max_range_m: float


def raycast_lidar(
    world: World2D,
    pose: RobotPose,
    num_rays: int = 36,
    max_range_m: float = 5.0,
    step_m: float = 0.05,
) -> LidarReading:
    angles: list[float] = []
    ranges: list[float] = []

    for i in range(num_rays):
        rel_angle = -math.pi + (2.0 * math.pi * i) / max(num_rays, 1)
        world_angle = pose.theta + rel_angle
        cos_a = math.cos(world_angle)
        sin_a = math.sin(world_angle)

        dist = 0.0
        hit_dist = max_range_m
        while dist <= max_range_m:
            px = pose.x + dist * cos_a
            py = pose.y + dist * sin_a

            if px <= 0.0 or px >= world.width or py <= 0.0 or py >= world.height:
                hit_dist = dist
                break

            hit_obs = False
            for obs in world.obstacles:
                if obs.contains(px, py, margin=0.0):
                    hit_obs = True
                    break

            if hit_obs:
                hit_dist = dist
                break

            dist += step_m

        angles.append(rel_angle)
        ranges.append(round(hit_dist, 4))

    return LidarReading(angles_rad=angles, ranges_m=ranges, max_range_m=max_range_m)


class OccupancyGridSLAM:
    """Lightweight 2D occupancy grid mapper updated from pose + LIDAR scans."""

    def __init__(
        self,
        width_m: float,
        height_m: float,
        resolution_m: float = 0.25,
    ) -> None:
        self.width_m = width_m
        self.height_m = height_m
        self.resolution_m = resolution_m
        self.cols = max(1, int(math.ceil(width_m / resolution_m)))
        self.rows = max(1, int(math.ceil(height_m / resolution_m)))
        # 0 = unknown, 1 = free, 2 = occupied
        self.grid: list[list[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def world_to_cell(self, x: float, y: float) -> tuple[int, int] | None:
        col = int(x / self.resolution_m)
        row = int(y / self.resolution_m)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return (row, col)
        return None

    def update(self, pose: RobotPose, scan: LidarReading) -> None:
        robot_cell = self.world_to_cell(pose.x, pose.y)
        if robot_cell is not None:
            self.grid[robot_cell[0]][robot_cell[1]] = 1

        for rel_angle, rng in zip(scan.angles_rad, scan.ranges_m):
            world_angle = pose.theta + rel_angle
            cos_a = math.cos(world_angle)
            sin_a = math.sin(world_angle)

            free_limit = max(0.0, rng - self.resolution_m)
            d = self.resolution_m
            while d < free_limit:
                fx = pose.x + d * cos_a
                fy = pose.y + d * sin_a
                f_cell = self.world_to_cell(fx, fy)
                if f_cell is not None and self.grid[f_cell[0]][f_cell[1]] == 0:
                    self.grid[f_cell[0]][f_cell[1]] = 1
                d += self.resolution_m

            if rng < scan.max_range_m:
                ox = pose.x + rng * cos_a
                oy = pose.y + rng * sin_a
                o_cell = self.world_to_cell(ox, oy)
                if o_cell is not None:
                    self.grid[o_cell[0]][o_cell[1]] = 2

    def to_dict(self) -> dict[str, object]:
        return {
            "width_m": self.width_m,
            "height_m": self.height_m,
            "resolution_m": self.resolution_m,
            "rows": self.rows,
            "cols": self.cols,
            "grid": self.grid,
        }