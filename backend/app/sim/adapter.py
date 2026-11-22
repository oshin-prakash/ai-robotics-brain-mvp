from __future__ import annotations

from app.sim.planner import AStarPlanner, GridPoint
from app.sim.sensors import LidarReading, OccupancyGridSLAM, raycast_lidar
from app.sim.world import DEFAULT_DT, RobotPose, VelocityCmd, World2D


class SimRobotAdapter:
    """Hardware-agnostic robot control interface backed by the 2D simulator."""

    def __init__(self, world: World2D | None = None, resolution_m: float = 0.25) -> None:
        self.world = world if world is not None else World2D()
        self.slam = OccupancyGridSLAM(
            width_m=self.world.width,
            height_m=self.world.height,
            resolution_m=resolution_m,
        )
        self.planner = AStarPlanner(world=self.world, resolution_m=resolution_m)
        self._refresh_slam()

    def _refresh_slam(self) -> LidarReading:
        scan = self.read_lidar()
        self.slam.update(self.world.get_pose(), scan)
        return scan

    def get_pose(self) -> RobotPose:
        return self.world.get_pose()

    def send_velocity(self, cmd: VelocityCmd, dt: float = DEFAULT_DT) -> RobotPose:
        pose = self.world.step(cmd, dt=dt)
        self._refresh_slam()
        return pose

    def read_lidar(self) -> LidarReading:
        return raycast_lidar(self.world, self.world.get_pose())

    def get_slam_map(self) -> dict[str, object]:
        return self.slam.to_dict()

    def plan_path(self, goal_xy: GridPoint) -> list[GridPoint]:
        pose = self.world.get_pose()
        return self.planner.plan((pose.x, pose.y), goal_xy)

    def reset(self, pose: RobotPose | None = None) -> RobotPose:
        reset_pose = self.world.reset(pose=pose)
        self.slam = OccupancyGridSLAM(
            width_m=self.world.width,
            height_m=self.world.height,
            resolution_m=self.slam.resolution_m,
        )
        self._refresh_slam()
        return reset_pose