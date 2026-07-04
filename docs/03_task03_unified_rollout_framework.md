# TASK_03 设计：Unified Gym-PyBullet-Drones Scenario / Policy / Rollout Framework

## 1. 阶段定位

TASK_03 开始进入 PIRL-NavRL 自己的主线实现准备阶段。

TASK_02 的 EGO-Planner Docker/ROS sidecar 已冻结为 diagnostic reference；TASK_03 不继续扩展 EGO，不做 EGO baseline。

TASK_03 的目标是先建立一套统一实验骨架：

```text
ScenarioConfig
  -> platform adapter / diagnostic env
  -> PolicyLike
  -> rollout recorder
  -> visualization
  -> diagnostic summary
```

本阶段仍然不是论文结果阶段，不训练正式模型，不生成 baseline matrix，不报告 success rate。

当前实现状态：

- `pirl_navrl/scenarios/core.py` 定义统一 `ScenarioConfig` 和
  `task03_static_nav_v0`。
- `pirl_navrl/interfaces/policy.py` 定义 `PolicyLike`。
- `pirl_navrl/policies/simple_policies.py` 提供 debug policies。
- `pirl_navrl/platforms/diagnostic_kinematic_env.py` 提供最小 diagnostic
  kinematic loop。
- `pirl_navrl/platforms/gym_pybullet_drones/simple_adapter.py` 仅保留显式
  skeleton，不静默 fallback。
- `pirl_navrl/evaluation/rollout_recorder.py` 写 TASK_03 diagnostic JSONL。
- `scripts/run_task03_gym_pybullet_rollout.py` 和
  `scripts/view_task03_rollout.py` 提供最小 rollout 与 PyBullet trace
  visualization。

## 2. NavRL 与其他开源项目的参考方式

NavRL 可以作为重要工程与算法实现参考源。允许仔细阅读 NavRL 代码，并在遵守许可证和归属边界的前提下，参考甚至复制小段实现思想或代码结构，再适配到 PIRL-NavRL 自己的模块中。

允许参考的内容包括：

- repository structure、module boundary、runner/trainer/evaluator separation；
- observation / action / reward design；
- dynamic obstacle 与 navigation task organization；
- policy、safety、rollout、logging、checkpoint、deployment modules；
- parameter ranges、config organization、seed handling；
- visualization、debugging、evaluation workflow；
- ROS / deployment boundary design。

允许复制的边界：

- 可以复制小段通用 helper、schema、adapter pattern 或参数组织方式；
- 必须改写并适配到本项目命名、类型、平台和测试；
- 必须保留必要 attribution / license note；
- 不得整包迁移 NavRL 训练栈；
- 不得把复制内容伪装为从零原创；
- 不得声称复现 NavRL 或把 NavRL 当 baseline。

其他 gym-pybullet / gymnasium / SB3 开源项目也可以用类似原则参考，重点学习 env wrapper、vectorized env、callback、logging、visualization 和 evaluation organization。

## 3. TASK_03 核心模块

### 3.1 ScenarioConfig

建议新增：

```text
pirl_navrl/scenarios/core.py
```

定义：

- `Vector3`
- `Bounds3D`
- `ObstacleConfig`
- `ScenarioConfig`

`ScenarioConfig` 至少包含：

- `scenario_id`
- `seed`
- `start`
- `goal`
- `bounds`
- `static_obstacles`
- `dynamic_obstacles`
- `max_steps`
- `dt`
- `success_radius`
- `collision_radius`

首个 debug 场景：

```text
task03_static_nav_v0
```

建议设定：

- start: `(-4.0, 0.0, 1.0)`
- goal: `(4.0, 0.0, 1.0)`
- bounds: `x=[-5, 5], y=[-5, 5], z=[0, 3]`
- 2 到 3 个静态 cylinder / sphere 障碍物
- `max_steps` 约 100

### 3.2 PolicyLike

建议新增：

```text
pirl_navrl/interfaces/policy.py
```

统一接口：

```python
reset(scenario: ScenarioConfig) -> None
act(observation: Mapping[str, Any]) -> Any
```

未来所有 policy 都走同一接口：

- `RandomVelocityPolicy`
- `GoalSeekingVelocityPolicy`
- `PIRLPolicy`
- `PPOPolicy`
- `ShieldedPolicy`
- `EgoSidecarPolicy`

### 3.3 Simple debug policies

建议新增：

```text
pirl_navrl/policies/simple_policies.py
```

实现：

- `RandomVelocityPolicy`
- `GoalSeekingVelocityPolicy`

要求：

- 不依赖 ROS；
- 不依赖 EGO；
- 可在 diagnostic env 中运行；
- 固定 seed 可复现；
- policy id 必须包含 `debug` 或 `diagnostic` 语义。

### 3.4 Diagnostic kinematic env

建议新增：

```text
pirl_navrl/platforms/diagnostic_kinematic_env.py
```

用于最小闭环调试：

```text
position_{t+1} = position_t + clipped_desired_velocity * dt
```

功能：

- bounds clamp；
- static obstacle clearance；
- collision 判断；
- success 判断；
- timeout 判断；
- 每步返回 observation 和 info。

该 env 只是 diagnostic fallback，不是论文实验平台。

### 3.5 Gym-PyBullet-Drones adapter skeleton

建议新增：

```text
pirl_navrl/platforms/gym_pybullet_drones/simple_adapter.py
```

目标：

- 为后续真实 gym-pybullet-drones 接入预留接口；
- 当前可以 skeleton 或显式 NotImplementedError；
- 依赖不可用时必须明确报错，不要静默 fallback；
- 不要把 diagnostic env 冒充为 gym-pybullet-drones。

### 3.6 Rollout recorder

建议新增：

```text
pirl_navrl/evaluation/rollout_recorder.py
```

定义：

- `RolloutStepRecord`
- `RolloutSummary`
- `RolloutJsonlWriter`

每步至少记录：

- `task_id`
- `output_type`
- `platform_id`
- `scenario_id`
- `seed`
- `policy_id`
- `step`
- `position`
- `velocity`
- `goal`
- `action`
- `distance_to_goal`
- `min_clearance`
- `collision`
- `success`
- `timeout`

输出 JSONL，`output_type` 固定为 `diagnostic`。

### 3.7 Visualization

TASK_03 必须提供可视化。建议新增：

```text
scripts/view_task03_rollout.py
```

或者在 rollout 脚本中提供：

```bash
python3 scripts/run_task03_gym_pybullet_rollout.py --gui
python3 scripts/run_task03_gym_pybullet_rollout.py --view-trace results/task03_static_nav_rollout.jsonl
```

可视化要求：

- 显示 start、goal、bounds；
- 显示静态障碍物；
- 显示无人机当前位置；
- 显示历史轨迹线；
- 显示 action / desired velocity 方向线；
- 显示 collision / success / timeout 状态；
- 支持 PyBullet GUI；
- 支持 `--direct` 或 headless 模式用于 CI / pytest。

可视化仍然是 diagnostic，不是论文图。

## 4. 最小运行脚本

建议新增：

```text
scripts/run_task03_gym_pybullet_rollout.py
```

默认行为：

```text
scenario_id: task03_static_nav_v0
policy_id: goal_seeking_velocity_debug
platform_id: diagnostic_kinematic_env
output_path: results/task03_static_nav_rollout.jsonl
visualization: optional PyBullet GUI
```

运行：

```bash
python3 scripts/run_task03_gym_pybullet_rollout.py
python3 scripts/run_task03_gym_pybullet_rollout.py --gui
python3 scripts/view_task03_rollout.py --trace results/task03_static_nav_rollout.jsonl
```

headless trace viewer 检查：

```bash
python3 scripts/view_task03_rollout.py --trace results/task03_static_nav_rollout.jsonl --direct
```

输出 summary：

- `steps`
- `final_distance_to_goal`
- `min_clearance`
- `collision`
- `success`
- `timeout`
- `platform_id`
- `policy_id`

summary 是 diagnostic，不是 success rate。

## 5. 配置文件

建议新增：

```text
configs/task03_static_nav_debug.json
```

内容包括：

- `task_id: TASK_03`
- `output_type: diagnostic`
- `scenario_id: task03_static_nav_v0`
- `seed: 0`
- `policy_id: goal_seeking_velocity_debug`
- `platform_id: diagnostic_kinematic_env`
- `output_path: results/task03_static_nav_rollout.jsonl`
- `visualize: false`

## 6. 明确不做

TASK_03 不做：

- 不训练 PPO；
- 不训练 PIRL；
- 不接 EGO baseline；
- 不做多 seed benchmark；
- 不生成论文表格；
- 不报告 success rate；
- 不提交 results、videos、checkpoints、大日志；
- 不把 diagnostic kinematic env 当正式环境；
- 不声称任何方法有效。

## 7. 验收标准

TASK_03 完成后应满足：

1. `pytest -q` 通过。
2. `python3 scripts/run_task03_gym_pybullet_rollout.py` 能运行并生成 JSONL。
3. `python3 scripts/run_task03_gym_pybullet_rollout.py --gui` 或 `scripts/view_task03_rollout.py` 能显示轨迹、障碍物、目标点。
4. ScenarioConfig、PolicyLike、simple policies、diagnostic env、rollout recorder 均有测试覆盖。
5. README / docs 明确 TASK_03 是 diagnostic framework，不是正式实验。
6. NavRL 参考范围明确：可以详细参考和适配代码，但不得整包迁移、不得声称 baseline 或复现。
