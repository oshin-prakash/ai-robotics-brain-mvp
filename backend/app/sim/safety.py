from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class RobotSafetyState:
    robot_id: str
    estop: bool = False
    active_path: list[tuple[float, float]] = field(default_factory=list)
    paused: bool = False
    last_joystick_ts: float | None = None
    override_token_active: bool = False
    alerts: list[str] = field(default_factory=list)


@dataclass
class SafetyDecision:
    vx: float
    vy: float
    omega: float
    state: str
    alert: str | None = None
    cancel_path: bool = False


class SafetySupervisor:
    """Strict deterministic safety supervisor invoked on every simulation tick."""

    MAX_LINEAR_VEL: float = 1.2
    MAX_ANGULAR_VEL: float = 2.0
    MIN_LIDAR_CLEARANCE_M: float = 0.45
    JOYSTICK_TIMEOUT_S: float = 1.5

    def __init__(
        self,
        restricted_lab_rect: tuple[float, float, float, float] = (6.5, 1.0, 9.0, 3.5),
    ) -> None:
        # (x_min, y_min, x_max, y_max)
        self.restricted_lab_rect = restricted_lab_rect
        self.robots: dict[str, RobotSafetyState] = {}

    def _get_or_create(self, robot_id: str) -> RobotSafetyState:
        if robot_id not in self.robots:
            self.robots[robot_id] = RobotSafetyState(robot_id=robot_id)
        return self.robots[robot_id]

    def set_estop(self, robot_id: str, active: bool) -> RobotSafetyState:
        st = self._get_or_create(robot_id)
        st.estop = bool(active)
        if st.estop:
            st.active_path.clear()
        return st

    def set_override_token(self, robot_id: str, active: bool) -> None:
        st = self._get_or_create(robot_id)
        st.override_token_active = bool(active)

    def set_active_path(self, robot_id: str, waypoints: list[tuple[float, float]]) -> None:
        st = self._get_or_create(robot_id)
        st.active_path = list(waypoints)

    def record_joystick_heartbeat(self, robot_id: str, now: float | None = None) -> None:
        st = self._get_or_create(robot_id)
        st.last_joystick_ts = time.monotonic() if now is None else now

    def _in_restricted_lab(self, x: float, y: float) -> bool:
        x_min, y_min, x_max, y_max = self.restricted_lab_rect
        return x_min <= x <= x_max and y_min <= y <= y_max

    def _forward_min_lidar(
        self,
        lidar_angles: list[float] | None,
        lidar_ranges: list[float] | None,
        half_cone_rad: float = math.pi / 4.0,
    ) -> float | None:
        if not lidar_angles or not lidar_ranges:
            return None
        forward_dists = [
            rng
            for ang, rng in zip(lidar_angles, lidar_ranges)
            if abs(ang) <= half_cone_rad
        ]
        return min(forward_dists) if forward_dists else None

    def check_and_clamp(
        self,
        robot_id: str,
        vx: float,
        vy: float,
        omega: float,
        pose_xy: tuple[float, float],
        theta: float = 0.0,
        dt: float = 0.05,
        lidar_angles: list[float] | None = None,
        lidar_ranges: list[float] | None = None,
        manual_mode: bool = False,
        now: float | None = None,
    ) -> SafetyDecision:
        st = self._get_or_create(robot_id)

        # Rule 1: E-Stop latch always forces zero velocity & E_STOP state
        if st.estop:
            return SafetyDecision(0.0, 0.0, 0.0, state="E_STOP", cancel_path=True)

        # Rule 4a: Velocity clamping
        clamped_vx = max(-self.MAX_LINEAR_VEL, min(self.MAX_LINEAR_VEL, vx))
        clamped_vy = max(-self.MAX_LINEAR_VEL, min(self.MAX_LINEAR_VEL, vy))
        clamped_omega = max(-self.MAX_ANGULAR_VEL, min(self.MAX_ANGULAR_VEL, omega))

        # Rule 4b: 1.5-second manual joystick heartbeat watchdog
        if manual_mode:
            ts = time.monotonic() if now is None else now
            if st.last_joystick_ts is None or (ts - st.last_joystick_ts) > self.JOYSTICK_TIMEOUT_S:
                return SafetyDecision(
                    0.0,
                    0.0,
                    0.0,
                    state="JOYSTICK_TIMEOUT",
                    alert="JOYSTICK_HEARTBEAT_LOST",
                    cancel_path=False,
                )

        # Rule 2: Collision prevention on forward-arc LIDAR < 0.45m with linear velocity > 0
        fwd_dist = self._forward_min_lidar(lidar_angles, lidar_ranges)
        linear_speed = math.hypot(clamped_vx, clamped_vy)
        if fwd_dist is not None and fwd_dist < self.MIN_LIDAR_CLEARANCE_M and linear_speed > 0.0:
            st.active_path.clear()
            st.alerts.append("SAFETY_HALT")
            return SafetyDecision(
                0.0,
                0.0,
                0.0,
                state="SAFETY_HALT",
                alert="SAFETY_HALT",
                cancel_path=True,
            )

        # Rule 3: Restricted zone geofence check on predicted next position
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        next_x = pose_xy[0] + (clamped_vx * cos_t - clamped_vy * sin_t) * dt
        next_y = pose_xy[1] + (clamped_vx * sin_t + clamped_vy * cos_t) * dt

        if self._in_restricted_lab(next_x, next_y) and not st.override_token_active:
            st.active_path.clear()
            st.alerts.append("GEOFENCE_BLOCKED")
            return SafetyDecision(
                0.0,
                0.0,
                0.0,
                state="GEOFENCE_BLOCKED",
                alert="GEOFENCE_BLOCKED",
                cancel_path=True,
            )

        return SafetyDecision(
            vx=clamped_vx,
            vy=clamped_vy,
            omega=clamped_omega,
            state="OK",
            alert=None,
            cancel_path=False,
        )