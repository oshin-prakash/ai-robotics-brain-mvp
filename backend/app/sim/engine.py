from __future__ import annotations

from dataclasses import dataclass, field

from app.sim.safety import SafetyDecision, SafetySupervisor
from app.sim.sensors import LidarReading, raycast_lidar
from app.sim.world import DEFAULT_DT, NAMED_ZONES, RobotPose, VelocityCmd, World2D


@dataclass
class FleetRobot:
    robot_id: str
    pose: RobotPose
    battery: float = 100.0
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    paused: bool = False
    task_active: bool = False


class SimulationEngine:
    """20 Hz multi-robot simulation engine with SafetySupervisor and Fleet Handoff."""

    LOW_BATTERY_THRESHOLD: float = 20.0

    def __init__(
        self,
        world: World2D | None = None,
        supervisor: SafetySupervisor | None = None,
    ) -> None:
        self.world = world if world is not None else World2D()
        self.supervisor = supervisor if supervisor is not None else SafetySupervisor()
        dock_x, dock_y = NAMED_ZONES["dock"]
        self.robots: dict[str, FleetRobot] = {
            "robot_01": FleetRobot(robot_id="robot_01", pose=RobotPose(dock_x, dock_y, 0.0), battery=100.0),
            "robot_02": FleetRobot(robot_id="robot_02", pose=RobotPose(dock_x, dock_y + 0.6, 0.0), battery=100.0),
        }
        self.handoff_events: list[dict[str, object]] = []

    def assign_task(self, robot_id: str, waypoints: list[tuple[float, float]]) -> None:
        robot = self.robots[robot_id]
        robot.waypoints = list(waypoints)
        robot.task_active = len(robot.waypoints) > 0
        robot.paused = False
        self.supervisor.set_active_path(robot_id, robot.waypoints)

    def check_and_execute_handoff(self) -> bool:
        r1 = self.robots.get("robot_01")
        r2 = self.robots.get("robot_02")
        if not r1 or not r2:
            return False

        if r1.task_active and r1.battery < self.LOW_BATTERY_THRESHOLD:
            remaining = list(r1.waypoints)
            dock_xy = NAMED_ZONES["dock"]
            r1.paused = True
            r1.task_active = False
            r1.waypoints = [dock_xy]
            self.supervisor.set_active_path("robot_01", r1.waypoints)

            r2.waypoints = remaining
            r2.task_active = len(remaining) > 0
            r2.paused = False
            self.supervisor.set_active_path("robot_02", r2.waypoints)

            self.handoff_events.append(
                {
                    "from": "robot_01",
                    "to": "robot_02",
                    "battery_r1": r1.battery,
                    "transferred_waypoints": remaining,
                }
            )
            return True
        return False

    def tick(
        self,
        robot_id: str,
        cmd: VelocityCmd,
        dt: float = DEFAULT_DT,
        lidar: LidarReading | None = None,
        battery_drain: float = 0.0,
        manual_mode: bool = False,
    ) -> tuple[RobotPose, SafetyDecision]:
        robot = self.robots[robot_id]
        robot.battery = max(0.0, robot.battery - battery_drain)

        if robot_id == "robot_01":
            self.check_and_execute_handoff()

        scan = lidar if lidar is not None else raycast_lidar(self.world, robot.pose)
        decision = self.supervisor.check_and_clamp(
            robot_id=robot_id,
            vx=cmd.vx,
            vy=cmd.vy,
            omega=cmd.omega,
            pose_xy=(robot.pose.x, robot.pose.y),
            theta=robot.pose.theta,
            dt=dt,
            lidar_angles=scan.angles_rad,
            lidar_ranges=scan.ranges_m,
            manual_mode=manual_mode,
        )

        if decision.cancel_path:
            robot.waypoints.clear()
            robot.task_active = False

        # Apply clamped velocity safely through World2D
        self.world.reset(robot.pose)
        updated_pose = self.world.step(
            VelocityCmd(vx=decision.vx, vy=decision.vy, omega=decision.omega),
            dt=dt,
        )
        robot.pose = updated_pose
        return updated_pose, decision