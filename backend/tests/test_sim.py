from app.sim import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    NAMED_ZONES,
    AStarPlanner,
    SimRobotAdapter,
    VelocityCmd,
    World2D,
    raycast_lidar,
)


def test_world_initial_pose_and_step_motion() -> None:
    world = World2D()
    assert world.width == ARENA_WIDTH
    assert world.height == ARENA_HEIGHT
    assert (world.pose.x, world.pose.y) == NAMED_ZONES["dock"]

    new_pose = world.step(VelocityCmd(vx=1.0, vy=0.0, omega=0.0), dt=0.5)
    assert new_pose.x > 1.0
    assert abs(new_pose.y - 1.0) < 1e-6


def test_world_blocks_obstacle_penetration() -> None:
    world = World2D()
    # Move straight into rack_1 (x=4.2..5.4, y=1.5..3.7) along y=2.0
    world.reset()
    world.step(VelocityCmd(vx=0.0, vy=1.0, omega=0.0), dt=1.0)  # y -> 2.0
    for _ in range(80):
        world.step(VelocityCmd(vx=1.0, vy=0.0, omega=0.0), dt=0.05)

    for obs in world.obstacles:
        assert not obs.contains(world.pose.x, world.pose.y, margin=0.0)


def test_lidar_and_slam_update() -> None:
    world = World2D()
    adapter = SimRobotAdapter(world=world)
    scan = raycast_lidar(world, world.get_pose(), num_rays=18, max_range_m=5.0)
    assert len(scan.angles_rad) == 18
    assert len(scan.ranges_m) == 18
    assert all(0.0 <= r <= 5.0 for r in scan.ranges_m)

    slam_dict = adapter.get_slam_map()
    assert slam_dict["rows"] == 32
    assert slam_dict["cols"] == 40
    assert isinstance(slam_dict["grid"], list)


def test_astar_planner_routes_around_obstacle() -> None:
    world = World2D()
    planner = AStarPlanner(world=world, resolution_m=0.25, inflation_margin_m=0.1)
    path = planner.plan(start_xy=(1.0, 2.0), goal_xy=(6.0, 2.0))

    assert len(path) > 0
    assert path[-1] == (6.0, 2.0)
    for px, py in path:
        for obs in world.obstacles:
            assert not obs.contains(px, py, margin=0.0)


def test_sim_robot_adapter_interface() -> None:
    adapter = SimRobotAdapter()
    initial_pose = adapter.get_pose()
    assert (initial_pose.x, initial_pose.y) == NAMED_ZONES["dock"]

    updated_pose = adapter.send_velocity(VelocityCmd(vx=0.5, omega=0.0), dt=0.2)
    assert updated_pose.x > initial_pose.x

    scan = adapter.read_lidar()
    assert len(scan.ranges_m) > 0
    assert adapter.get_slam_map() is not None