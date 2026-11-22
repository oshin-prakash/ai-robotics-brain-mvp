from app.sim.engine import SimulationEngine
from app.sim.safety import SafetySupervisor
from app.sim.sensors import LidarReading
from app.sim.world import VelocityCmd, World2D


def test_estop_blocks_ai_velocity_commands() -> None:
    sup = SafetySupervisor()
    sup.set_estop("robot_01", True)

    decision = sup.check_and_clamp(
        robot_id="robot_01",
        vx=1.0,
        vy=0.5,
        omega=1.5,
        pose_xy=(2.0, 2.0),
    )
    assert decision.vx == 0.0
    assert decision.vy == 0.0
    assert decision.omega == 0.0
    assert decision.state == "E_STOP"


def test_lidar_halt_blocks_forward_motion_and_cancels_path() -> None:
    sup = SafetySupervisor()
    sup.set_active_path("robot_01", [(3.0, 2.0), (5.0, 2.0)])
    close_lidar = LidarReading(angles_rad=[0.0, 0.1], ranges_m=[0.30, 0.35], max_range_m=5.0)

    decision = sup.check_and_clamp(
        robot_id="robot_01",
        vx=0.8,
        vy=0.0,
        omega=0.0,
        pose_xy=(2.0, 2.0),
        lidar_angles=close_lidar.angles_rad,
        lidar_ranges=close_lidar.ranges_m,
    )
    assert decision.vx == 0.0
    assert decision.state == "SAFETY_HALT"
    assert decision.alert == "SAFETY_HALT"
    assert decision.cancel_path is True
    assert sup.robots["robot_01"].active_path == []


def test_restricted_lab_geofence_blocks_without_override() -> None:
    sup = SafetySupervisor(restricted_lab_rect=(5.0, 1.0, 8.0, 4.0))
    # Moving right from x=4.95 with vx=1.0, dt=0.1 -> next_x=5.05 (inside restricted_lab)
    blocked = sup.check_and_clamp(
        robot_id="robot_01",
        vx=1.0,
        vy=0.0,
        omega=0.0,
        pose_xy=(4.95, 2.0),
        dt=0.1,
    )
    assert blocked.vx == 0.0
    assert blocked.state == "GEOFENCE_BLOCKED"

    sup.set_override_token("robot_01", True)
    allowed = sup.check_and_clamp(
        robot_id="robot_01",
        vx=1.0,
        vy=0.0,
        omega=0.0,
        pose_xy=(4.95, 2.0),
        dt=0.1,
    )
    assert allowed.state == "OK"
    assert allowed.vx == 1.0


def test_velocity_clamping_and_fleet_handoff_below_20_percent() -> None:
    engine = SimulationEngine(world=World2D())
    remaining_wps = [(4.0, 3.0), (7.5, 5.5)]
    engine.assign_task("robot_01", remaining_wps)
    engine.robots["robot_01"].battery = 15.0

    _, decision = engine.tick(
        robot_id="robot_01",
        cmd=VelocityCmd(vx=5.0, vy=0.0, omega=4.0),
        dt=0.05,
    )
    assert abs(decision.vx) <= 1.2
    assert abs(decision.omega) <= 2.0
    assert engine.robots["robot_01"].paused is True
    assert engine.robots["robot_02"].waypoints == remaining_wps
    assert engine.robots["robot_02"].task_active is True