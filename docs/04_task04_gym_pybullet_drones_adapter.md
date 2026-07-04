# TASK_04 设计：Pre-Training Gym-PyBullet-Drones RL-Ready Adapter

## 1. 阶段定位

TASK_04 是训练前置准备阶段，不开始训练。

TASK_03 已完成统一 `ScenarioConfig`、`PolicyLike`、diagnostic env、rollout recorder 和可视化。TASK_04 的目标是把这套统一框架接到真实 `gym-pybullet-drones` 平台，并补齐下一阶段 SB3 / PPO debug training 之前必须稳定的 action、observation、reward、termination、env checker 和 rollout smoke test。

本阶段仍然只生成 diagnostic JSONL，不生成论文指标，不做 baseline，不报告 success rate。

当前实现状态：

- `GymPybulletDronesSimpleAdapter` 已接入真实 `VelocityAviary`，平台 ID 为
  `gym_pybullet_drones_velocity_adapter_debug`。
- 对外 action 固定为 `(3,)` normalized desired velocity，范围 `[-1, 1]`；
  内部转换为 `VelocityAviary` 的 `(1, 4)` velocity command。
- observation adapter 输出固定 19 维 flattened observation，并保留 dict schema。
- reward module 输出 finite reward 和 `reward_terms`。
- `Task04GymPybulletDronesRLEnv` 满足 Gymnasium reset/step API，并提供
  check script；当 `stable_baselines3` 可用时，该脚本可运行 `check_env`
  smoke check。
- 自定义障碍物已按 `ScenarioConfig` 注入 VelocityAviary 使用的 PyBullet
  client，作为静态 sphere/cylinder collision body；同时继续计算任务级
  clearance / safety collision metric。

## 2. 开源项目调研参考范围

TASK_04 可以仔细参考以下项目和文档：

### gym-pybullet-drones

重点参考：

- `examples/pid.py`
- `examples/pid_velocity.py`
- `examples/learn.py`
- `BaseAviary`
- `CtrlAviary`
- `VelocityAviary`
- `BaseRLAviary`

重点理解：

- reset / step / render / close 调用方式；
- drone state 读取方式；
- PID / velocity reference / target-position 控制方式；
- observation/action shape；
- 和 SB3 训练示例的接口边界。

### Stable-Baselines3

重点参考：

- `check_env`
- `Monitor`
- `EvalCallback`
- `VecNormalize`
- PPO example

TASK_04 不训练 PPO，但要让 env 具备下一阶段接 SB3 的条件。

### Gymnasium

重点参考：

- `reset(seed=None, options=None) -> (obs, info)`；
- `step(action) -> (obs, reward, terminated, truncated, info)`；
- `observation_space` / `action_space`；
- `terminated` 与 `truncated` 分离。

### NavRL

NavRL 可以作为详细实现参考，尤其是：

- env wrapper；
- observation design；
- reward shaping；
- runner / config / logging；
- visualization organization；
- collision / clearance metrics。

允许复制小段通用 helper、schema、adapter pattern 或参数组织方式，但必须适配到 PIRL-NavRL 自己的命名、类型、平台和测试，并处理 attribution / license。不得整包迁移 NavRL 训练栈，不得声称复现 NavRL。

## 3. 核心设计原则

### 3.1 优先 desired_velocity，不直接做 RPM policy

PIRL、PPO debug policy、EGO sidecar 和后续 shield 都更自然地产生 high-level desired velocity。因此 TASK_04 优先实现：

```text
PolicyLike desired_velocity
  -> action adapter
  -> gym-pybullet-drones velocity / PID / target-position control layer
```

不要在本阶段直接训练 RPM-level policy。RPM 会把低层控制和导航学习混在一起，增加调试成本。

TASK_04 的 RL wrapper 使用 normalized desired velocity 作为 action：

```text
[-1, 1]^3 action -> desired_velocity = action * max_speed
```

rollout smoke test 中的 `goal_seeking_velocity_debug` 仍是无避障 debug policy。
它只用于检查真实 env 接口、reward、termination 和 logging 链路，不代表导航
性能。

### 3.2 保持 TASK_03 接口不变

TASK_04 不重写 TASK_03 框架，只替换 platform adapter：

```text
ScenarioConfig
  -> GymPyBulletDronesAdapter
  -> PolicyLike desired_velocity
  -> RolloutJsonlWriter
```

`RolloutStepRecord` 和 JSONL schema 应尽量兼容 TASK_03。

### 3.3 不静默 fallback

如果 `gym-pybullet-drones` 不可用，真实 adapter 和脚本必须明确报错或显式 skip integration test。不要静默退回 `diagnostic_kinematic_env`，避免用户误以为真实平台已接入。

## 4. 必须补齐的模块

### 4.1 Real adapter

更新：

```text
pirl_navrl/platforms/gym_pybullet_drones/simple_adapter.py
```

实现：

- `GymPybulletDronesSimpleAdapter`
- `reset(scenario)`
- `step(desired_velocity)`
- `get_observation()`
- `close()`

`platform_id` 使用：

```text
gym_pybullet_drones_velocity_adapter_debug
```

当前 adapter 会把 `ScenarioConfig` 中的 sphere / cylinder 障碍物创建为
PyBullet 静态 collision body。`collision` 同时考虑 PyBullet contact 和
基于 `collision_radius` 的 safety clearance；后者用于保留可解释的任务级
安全边界。

### 4.2 Action adapter

新增：

```text
pirl_navrl/platforms/gym_pybullet_drones/action_adapter.py
```

实现：

- `clip_desired_velocity(desired_velocity, max_speed)`
- `normalize_desired_velocity(desired_velocity, max_speed)`
- `desired_velocity_to_action(desired_velocity, action_mode)`

要求：

- action shape 固定为 `(3,)`；
- normalized action 在 `[-1, 1]`；
- `max_speed <= 0` 必须报错；
- 输出或 info 中保留 raw desired velocity、clipped desired velocity、applied action。

### 4.3 Observation adapter

新增：

```text
pirl_navrl/platforms/gym_pybullet_drones/observation_adapter.py
```

统一 observation dict 至少包括：

- `position`
- `velocity`
- `goal`
- `relative_goal`
- `distance_to_goal`
- `nearest_obstacle_relative_position`
- `nearest_obstacle_distance`
- `min_clearance`
- `step_fraction`

同时提供：

- `flatten_observation(obs_dict) -> np.ndarray`
- `observation_space_for_scenario(scenario) -> gymnasium.spaces.Box`

要求 shape 固定、数值 finite，方便 TASK_05 直接接 PPO。

### 4.4 Reward

新增：

```text
pirl_navrl/evaluation/reward.py
```

实现：

```text
compute_task04_reward(previous_obs, current_obs, action, event_flags, config)
```

初版 reward terms：

- progress_to_goal reward；
- distance penalty；
- action norm penalty；
- clearance penalty；
- collision penalty；
- success bonus；
- timeout penalty。

要求：

- reward finite；
- `info["reward_terms"]` 包含分项；
- 不调参追求训练效果，只保证可解释、可运行、可检查。

### 4.5 Gymnasium RL env wrapper

新增：

```text
pirl_navrl/platforms/gym_pybullet_drones/rl_env.py
```

实现：

- `Task04GymPybulletDronesRLEnv(gymnasium.Env)`
- `observation_space`
- `action_space`
- `reset(seed=None, options=None)`
- `step(action)`
- `render` optional
- `close`

要求：

- `reset` 返回 `(observation, info)`；
- `step` 返回 `(observation, reward, terminated, truncated, info)`；
- `terminated = success or collision`；
- `truncated = timeout only`；
- `action_space = Box(low=-1, high=1, shape=(3,))`；
- observation 可以先用 flattened observation vector；
- info 包含 position、velocity、distance_to_goal、min_clearance、collision、success、timeout、reward_terms、platform_id、scenario_id、seed。

### 4.6 Env checker

新增：

```text
scripts/check_task04_rl_ready_env.py
```

检查：

- reset 正常；
- random action step 若干步；
- observation shape 固定；
- reward finite；
- terminated / truncated 类型正确；
- info 包含 diagnostic metrics；
- 若 stable_baselines3 可用，运行 `check_env`；
- 若 gym-pybullet-drones 不可用，明确报错或 skip integration，不要伪装通过。

### 4.7 Rollout smoke test

新增：

```text
scripts/run_task04_gym_pybullet_drones_rollout.py
configs/task04_gym_pybullet_static_nav_debug.json
```

默认运行：

```text
scenario_id: task03_static_nav_v0
policy_id: goal_seeking_velocity_debug
platform_id: gym_pybullet_drones_velocity_adapter_debug
output_path: results/task04_gym_pybullet_static_nav_rollout.jsonl
```

要求：

- 不训练；
- 不报告 success rate；
- 不生成视频；
- 不提交 results。

运行命令：

```bash
python3 scripts/check_task04_rl_ready_env.py
python3 scripts/run_task04_gym_pybullet_drones_rollout.py
```

依赖缺失时脚本必须明确报错，不会 fallback 到 TASK_03 diagnostic kinematic env。

真实 PyBullet GUI：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui
```

`--gui` 只显示 live gym-pybullet-drones 物理仿真，不自动打开 trace replay
viewer。GUI 默认约运行 60 秒，并在 rollout 结束后保持窗口打开，直到手动
关闭窗口或按 Ctrl+C；如需自动关闭可使用 `--hold-seconds 5`。起点、终点和
rollout 长度可以直接通过 CLI 覆盖：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py \
  --gui \
  --start -4 0 1 \
  --goal 3 2 1 \
  --max-steps 240
```

live GUI 中蓝色小球是 start，绿色小球是 goal，红色 sphere/cylinder 是
PyBullet collision body 障碍物，真实 Crazyflie 模型是无人机。默认 GUI
目标使用 `(3, 2, 1)`，避免无避障 debug policy 直线撞上中间障碍后立刻结束。
默认 TASK_04 障碍物尺寸已缩小，物理 collision body 和 visual body 保持一致，
避免视觉比例相对 Crazyflie 过大。
需要 replay JSONL 时显式加 `--replay-gui`。

相机和面板选项：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode manual
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode follow
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-control pybullet --enable-mouse-picking
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode fixed
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode manual --show-pybullet-ui
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --show-camera-preview --show-pybullet-ui
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --onboard-camera
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --show-drone-marker
```

`--camera-mode manual` 是默认模式，只在初始化时设置一次观察角度，之后不再
重置视角。默认 `--camera-control orbit` 是查看优先模式：关闭 PyBullet
mouse picking，左键/右键拖动旋转视角，中键上下拖动或滚轮缩放。`follow`
模式会每步把 debug visualizer camera 重新对准无人机，因此不能同时用于
自由鼠标拖拽。`--camera-control pybullet --enable-mouse-picking` 才使用
PyBullet 原始 picking 行为；此时左键会优先拖动态物体，无人机可被拖动，
静态障碍物不会被拖动。

TASK_04 默认保留 PyBullet 官方棋盘地面，同时对 start / goal / obstacle
visual 做了更清楚的颜色、阴影和高面数圆柱显示；碰撞体仍保持原 PyBullet
几何体。

`--show-camera-preview` 打开 PyBullet debug visualizer 的 RGB/depth/
segmentation preview 面板。`--onboard-camera` 会额外采样一个朝向 goal 的
轻量机载相机，并把 `onboard_camera` 统计写入 JSONL step record；GUI 中的
青色线段表示该相机的 eye-to-target 方向。当前只做 diagnostic camera hook，
不把图像接入训练 observation，也不保存图片或视频。

### 4.8 Visualization

TASK_04 可以复用 TASK_03 viewer，或新增 `scripts/view_task04_rollout.py`。

可视化至少显示：

- drone position；
- goal；
- obstacles；
- desired velocity；
- applied action；
- trajectory；
- collision / success / timeout。

可视化仍然是 diagnostic，不是论文图。

## 5. 明确不做

TASK_04 不做：

- 不训练 PPO；
- 不训练 PIRL；
- 不接 EGO baseline；
- 不做多 seed benchmark；
- 不做正式 baseline；
- 不报告 success rate；
- 不调参追求效果；
- 不提交 results、videos、checkpoints、TensorBoard、wandb。

## 6. TASK_04 完成后的标准表述

完成后可以说：

```text
We prepared an RL-ready gym-pybullet-drones adapter and diagnostic rollout path that can be checked before SB3/PPO training.
```

不能说：

```text
We trained an effective policy.
We completed a baseline.
We completed the PIRL method.
```

## 7. 进入 TASK_05 的条件

TASK_04 完成后，进入 TASK_05 前应满足：

1. RL env 能 reset/step/close。
2. observation_space / action_space 固定。
3. reward finite 且分项可解释。
4. terminated/truncated 语义正确。
5. diagnostic rollout 能写统一 JSONL。
6. `check_task04_rl_ready_env.py` 能运行。
7. 文档明确当前还未训练。

满足这些条件后，TASK_05 才开始 SB3 / PPO debug training。
