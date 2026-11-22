from __future__ import annotations

import math
from dataclasses import dataclass

ARENA_WIDTH: float = 10.0
ARENA_HEIGHT: float = 8.0
DEFAULT_DT: float = 0.05

NAMED_ZONES: dict[str, tuple[float, float]] = {
    "dock": (1.0, 1.0),
    "station_a": (3.0, 2.0),
    "station_b": (7.5, 5.5),
    "charge_pad": (1.5, 6.5),
}


@dataclass
class RobotPose:
    x: float
    y: float
    theta: float = 0.0  # radians; 0 faces +X (right), pi/2 faces +Y (down)


@dataclass
class VelocityCmd:
    vx: float = 0.0
    vy: float = 0.0
    omega: float = 0.0


@dataclass(frozen=True)
class ObstacleRect:
    x: float
    y: float
    width: float
    height: float
    label: str = "obstacle"

    def contains(self, px: float, py: float, margin: float = 0.0) -> bool:
        return (
            (self.x - margin) <= px <= (self.x + self.width + margin)
            and (self.y - margin) <= py <= (self.y + self.height + margin)
        )


class World2D:
    def __init__(
        self,
        width: float = ARENA_WIDTH,
        height: float = ARENA_HEIGHT,
        robot_radius: float = 0.25,
        obstacles: list[ObstacleRect] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.robot_radius = robot_radius
        self.obstacles: list[ObstacleRect] = (
            list(obstacles)
            if obstacles is not None
            else [
                ObstacleRect(x=4.2, y=1.5, width=1.2, height=2.2, label="rack_1"),
                ObstacleRect(x=5.8, y=4.2, width=1.4, height=1.5, label="rack_2"),
            ]
        )
        dock_x, dock_y = NAMED_ZONES["dock"]
        self.pose = RobotPose(x=dock_x, y=dock_y, theta=0.0)

    def reset(self, pose: RobotPose | None = None) -> RobotPose:
        if pose is not None:
            self.pose = RobotPose(x=pose.x, y=pose.y, theta=pose.theta)
        else:
            dock_x, dock_y = NAMED_ZONES["dock"]
            self.pose = RobotPose(x=dock_x, y=dock_y, theta=0.0)
        return self.get_pose()

    def get_pose(self) -> RobotPose:
        return RobotPose(x=self.pose.x, y=self.pose.y, theta=self.pose.theta)

    def is_position_free(self, x: float, y: float, extra_margin: float = 0.0) -> bool:
        clearance = self.robot_radius + extra_margin
        if x < clearance or x > (self.width - clearance):
            return False
        if y < clearance or y > (self.height - clearance):
            return False
        for obs in self.obstacles:
            if obs.contains(x, y, margin=clearance):
                return False
        return True

    def step(self, cmd: VelocityCmd, dt: float = DEFAULT_DT) -> RobotPose:
        if dt <= 0.0:
            return self.get_pose()

        cos_t = math.cos(self.pose.theta)
        sin_t = math.sin(self.pose.theta)

        # Body-frame (vx, vy) transformed into world-frame (dx, dy)
        world_dx = (cmd.vx * cos_t - cmd.vy * sin_t) * dt
        world_dy = (cmd.vx * sin_t + cmd.vy * cos_t) * dt

        target_x = self.pose.x + world_dx
        target_y = self.pose.y + world_dy

        # Slide along X or Y independently if blocked so collisions stay smooth
        if self.is_position_free(target_x, self.pose.y):
            self.pose.x = target_x
        if self.is_position_free(self.pose.x, target_y):
            self.pose.y = target_y

        new_theta = (self.pose.theta + cmd.omega * dt) % (2.0 * math.pi)
        self.pose.theta = new_theta
        return self.get_pose()