import math

from pirl_navrl.policies.simple_policies import GoalSeekingVelocityPolicy, RandomVelocityPolicy
from pirl_navrl.scenarios.core import make_task03_static_nav_v0


def norm(vector) -> float:
    return math.sqrt(sum(component * component for component in vector))


def test_goal_seeking_velocity_policy_points_toward_goal() -> None:
    scenario = make_task03_static_nav_v0(seed=0)
    policy = GoalSeekingVelocityPolicy(max_speed=0.7)
    policy.reset(scenario)

    action = policy.act({"position": scenario.start, "goal": scenario.goal})

    assert action[0] > 0.0
    assert abs(action[1]) < 1e-9
    assert abs(action[2]) < 1e-9
    assert norm(action) <= 0.7 + 1e-9
    assert "debug" in policy.policy_id


def test_random_velocity_policy_is_seed_reproducible() -> None:
    scenario = make_task03_static_nav_v0(seed=5)
    left = RandomVelocityPolicy(max_speed=0.5, seed=11)
    right = RandomVelocityPolicy(max_speed=0.5, seed=11)

    left.reset(scenario)
    right.reset(scenario)

    assert left.act({"position": scenario.start, "goal": scenario.goal}) == right.act(
        {"position": scenario.start, "goal": scenario.goal}
    )
    assert norm(left.act({"position": scenario.start, "goal": scenario.goal})) <= 0.5 + 1e-9
    assert "debug" in left.policy_id
