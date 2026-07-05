# PIRL-NavRL

PIRL-NavRL 是一个新的、干净的研究仓库，用于推进 **基于预测意图-风险的无人机局部导航强化学习**。

本仓库取代旧的 `pirl-nav-research` 作为后续主线。旧仓库里的轻量仿真器、手写策略、合成训练器和审查产物不再作为本仓库的有效实现代码。

## 当前平台与外部项目定位

第一阶段使用 **gym-pybullet-drones** 作为轻量级无人机 PyBullet 训练底座。

- 第一阶段主底座：<https://github.com/learnsyslab/gym-pybullet-drones>
- EGO-Planner：已在第二阶段作为 official Docker/ROS sidecar diagnostic 验证对象；后续如果完成统一 action / scenario / metrics 闭环，再考虑发展为 official EGO baseline
- NavRL：重要工程与算法实现参考源，可以仔细阅读、参考和适配其模块方法、参数组织、训练流程、动态导航实现和部署边界；**不作为 baseline**
- 当前训练依赖：gym-pybullet-drones + Stable-Baselines3 + PyBullet
- 当前不引入：Isaac Sim 训练、NavRL 训练栈、论文级结果声称

NavRL 的参考边界见 [`docs/navrl_reference_scope.md`](docs/navrl_reference_scope.md)。

## 第一阶段目标

第一阶段是环境配置和集成验证阶段，不是论文结果阶段。

目标：

1. 拉取并记录 NavRL 和 gym-pybullet-drones。
2. 配置可复现的本地 gym-pybullet-drones 环境。
3. 验证 gym-pybullet-drones 自带示例。
4. 在 gym-pybullet-drones 集成层上实现一个简单的 PIRL-NavRL adapter / risk / shield 演示。
5. 先建立项目管理、产物管理和实验管理规则，再进入正式实验。

## 第一阶段边界

允许：

- 在 `external/` 下本地克隆外部仓库
- 围绕 gym-pybullet-drones 写 adapter / wrapper
- 生成小型 JSON/JSONL 诊断结果
- 写导入检查、smoke test 和简单演示脚本
- 把 NavRL 作为长期参考架构记录下来

禁止：

- 复制旧 `pirl-nav-research` 的有效实现代码
- 从零写新的仿真器
- 使用 Isaac Sim 训练
- 提交 checkpoint、视频、GIF、TensorBoard、wandb 或其他大产物
- 声称论文级结果

## 第二阶段计划

第二阶段是 **EGO-Planner 官方 Docker sidecar 与简单障碍场景诊断**，仍然不是论文结果阶段。

第二阶段目标：

1. 将官方 EGO-Planner 作为 Docker Noetic ROS sidecar 运行。
2. 用 PyBullet mirror 显示 official odom / command / map trace。
3. 定义 future gym-pybullet-drones baseline 所需的 bridge contract。
4. 维护 static / dynamic / sudden-motion diagnostic scene config。
5. 生成 official EGO diagnostic JSONL，不作为论文 baseline。

第二阶段明确不做：正式 baseline 对比、论文级指标、多 seed 统计、NavRL baseline、NavRL 训练栈、EGO-Planner 论文结果复现。

第二阶段设计见 [`docs/02_phase2_ego_sidecar_plan.md`](docs/02_phase2_ego_sidecar_plan.md)。第二阶段任务见 [`codex_tasks/TASK_02_ego_planner_sidecar_bridge_and_egolike_scene.md`](codex_tasks/TASK_02_ego_planner_sidecar_bridge_and_egolike_scene.md)。

## 第三阶段计划

第三阶段是 **Unified Gym-PyBullet-Drones Scenario / Policy / Rollout Framework**。

第三阶段目标：

1. 定义统一 `ScenarioConfig`。
2. 定义统一 `PolicyLike` 接口。
3. 实现 diagnostic simple policies。
4. 实现 diagnostic kinematic env 作为最小闭环。
5. 预留 gym-pybullet-drones adapter skeleton。
6. 实现 JSONL rollout recorder。
7. 提供 PyBullet 可视化，显示场景、障碍物、轨迹、目标点和动作方向。

第三阶段允许详细参考 NavRL 和其他 gym-pybullet / Gymnasium / SB3 开源项目。可以复制小段通用 helper、schema、adapter pattern 或参数组织方式，但必须适配本项目、补测试、处理 attribution / license，不能整包迁移训练栈，也不能声称复现或比较 NavRL。

第三阶段明确不做：训练 PPO、训练 PIRL、接 EGO baseline、多 seed benchmark、论文表格、success rate 报告、提交结果大产物。

第三阶段设计见 [`docs/03_task03_unified_rollout_framework.md`](docs/03_task03_unified_rollout_framework.md)。第三阶段任务见 [`codex_tasks/TASK_03_unified_scenario_policy_rollout_framework.md`](codex_tasks/TASK_03_unified_scenario_policy_rollout_framework.md)。

运行第三阶段 diagnostic rollout：

```bash
python3 scripts/run_task03_gym_pybullet_rollout.py
python3 scripts/view_task03_rollout.py --trace results/task03_static_nav_rollout.jsonl
```

打开 PyBullet GUI：

```bash
python3 scripts/run_task03_gym_pybullet_rollout.py --gui
```

这些命令只生成 diagnostic JSONL 和本地可视化，不产生论文指标或 success rate。

默认 policy `goal_seeking_velocity_debug` 是无避障 debug policy，只朝目标
方向输出速度。在含障碍物场景中默认可能 `collision: true`；这不代表框架
失败，只代表该 debug policy 没有 obstacle reasoning。

PyBullet GUI 播放完成后会保持窗口打开，方便检查场景、轨迹和最终状态；
需要手动关闭窗口。`--direct` headless viewer 会自动退出。

## 第四阶段计划

第四阶段是 **Pre-Training Gym-PyBullet-Drones RL-Ready Adapter**。

第四阶段不开始训练，而是补齐训练前置工程：把第三阶段的统一 scenario / policy / rollout 框架接到真实 `gym-pybullet-drones` 平台，并稳定 action、observation、reward、termination、env checker 和 diagnostic rollout smoke test。

第四阶段目标：

1. 实现真实 `gym_pybullet_drones_velocity_adapter_debug`，不再只是 skeleton。
2. 实现 desired velocity 到 gym-pybullet-drones action 的 adapter，优先 high-level velocity / PID / target-position，不直接训练 RPM policy。
3. 实现 observation adapter 和 flatten observation，准备给 SB3/PPO 使用。
4. 实现 reward module，包含 progress、distance、action、clearance、collision、success、timeout 等 reward terms。
5. 实现 Gymnasium-compatible RL env wrapper，明确 `terminated = success or collision`，`truncated = timeout only`。
6. 提供 `check_task04_rl_ready_env.py`，能在训练前检查 reset/step、space、reward finite 和 SB3 check_env。
7. 提供 gym-pybullet-drones diagnostic rollout smoke test，并继续写统一 JSONL。

第四阶段明确不做：训练 PPO、训练 PIRL、接 EGO baseline、多 seed benchmark、正式 baseline、success rate 报告、调参追求效果、提交 checkpoint/video/TensorBoard/wandb。

第四阶段设计见 [`docs/04_task04_gym_pybullet_drones_adapter.md`](docs/04_task04_gym_pybullet_drones_adapter.md)。第四阶段任务见 [`codex_tasks/TASK_04_pretraining_gym_pybullet_drones_rl_ready_adapter.md`](codex_tasks/TASK_04_pretraining_gym_pybullet_drones_rl_ready_adapter.md)。
第四阶段完成报告见 [`docs/TASK_04_COMPLETION_REPORT.md`](docs/TASK_04_COMPLETION_REPORT.md)。

运行第四阶段 RL-ready env 检查：

```bash
python3 scripts/check_task04_rl_ready_env.py
```

运行第四阶段真实 gym-pybullet-drones diagnostic rollout：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py
```

该 rollout 使用 `VelocityAviary` 和 normalized desired velocity action，不训练
PPO，不报告 success rate。当前自定义障碍物会注入到 VelocityAviary 的
PyBullet client，作为静态 sphere/cylinder collision body；同时保留
diagnostic clearance / safety collision 统计。

打开真实 gym-pybullet-drones / PyBullet 物理窗口：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui
```

`--gui` 默认约运行 60 秒，并在 rollout 结束后保持窗口打开，直到手动关闭窗口
或按 Ctrl+C。live GUI 中蓝色球是 start，绿色球是 goal，红色物体是
PyBullet collision body 障碍物，真实 Crazyflie 模型是无人机；默认 GUI
目标会设为 `(3, 2, 1)`，避免 debug policy 直线撞上中间障碍后立刻停止。
默认 TASK_04 障碍物已缩小到更接近无人机诊断场景的视觉比例，物理碰撞体和
显示尺寸一致。
如果希望自动关闭：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --hold-seconds 5
```

自定义起点、终点和步数：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py \
  --gui \
  --start -4 0 1 \
  --goal 3 2 1 \
  --max-steps 240
```

可视化选项：

```bash
# 查看优先的鼠标视角控制，默认；左/右键拖动旋转，中键拖动或滚轮缩放
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode manual

# 跟随无人机；该模式会每步重置视角，因此不适合鼠标自由拖动
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode follow

# 使用 PyBullet 原始 mouse picking；左键会优先拖动态物体
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-control pybullet --enable-mouse-picking

# 固定相机
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode fixed

# 使用 PyBullet 官方 GUI 控件，并保留左侧面板
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --camera-mode manual --show-pybullet-ui

# 左侧原位置显示 PyBullet RGB/depth/segmentation preview
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --show-camera-preview --show-pybullet-ui

# 采样一个朝向 goal 的轻量机载相机，并在 GUI 里画青色视线
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --onboard-camera

# 如果觉得真实无人机模型太小，可以额外显示黄色跟踪 marker
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --gui --show-drone-marker
```

`--show-camera-preview` 是 PyBullet debug visualizer 左侧原位置的 RGB/depth/
segmentation preview 面板。`--onboard-camera` 是本项目侧额外采样的无人机
相机 diagnostic hook，当前只记录相机统计和可视方向，不把图像作为训练
observation，也不保存视频。

默认 `--camera-control orbit` 是查看优先模式：关闭 PyBullet mouse picking，
左键/右键拖动旋转视角，中键上下拖动或滚轮缩放。`--camera-control pybullet
--enable-mouse-picking` 才使用 PyBullet 原始 picking 行为；此时左键会优先
拖动态物体，无人机可被拖动，静态障碍物不会被拖动。

TASK_04 默认保留 PyBullet 官方棋盘地面，同时对 start / goal / obstacle
visual 做了更清楚的颜色、阴影和高面数圆柱显示；碰撞体仍保持原 PyBullet
几何体。

`--gui` 只显示真实物理仿真窗口，不再自动打开 trace replay viewer。需要回放
JSONL 时再显式使用：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py --replay-gui
```

## 第五阶段计划

第五阶段是 **NavRL-Informed PPO Debug Training and Visualization**。

第五阶段先阅读 NavRL 代码并做训练前置审查，然后才接入最小 SB3 PPO debug
training。当前阶段不是 baseline，不做多 seed benchmark，不报告正式 success
rate，不提交 checkpoint、TensorBoard、视频或 eval JSONL。

第五阶段新增：

- NavRL 参考审查：[`docs/navrl_code_review_for_task05.md`](docs/navrl_code_review_for_task05.md)
- 训练前置审查：[`docs/task05_training_readiness_review.md`](docs/task05_training_readiness_review.md)
- curriculum 配置：[`configs/task05_curriculum_levels.json`](configs/task05_curriculum_levels.json)
- PPO debug 配置：[`configs/task05_ppo_debug_train.json`](configs/task05_ppo_debug_train.json)

运行一次随机策略 eval，用来确认可视化和 JSONL 链路：

```bash
python3 scripts/eval_task05_ppo_debug.py \
  --random-policy \
  --curriculum-level level_0_no_obstacle_short \
  --output outputs/task05/eval/random_rollout.jsonl
```

打开 GUI 直接看 TASK_05 策略 rollout：

```bash
python3 scripts/eval_task05_ppo_debug.py \
  --random-policy \
  --curriculum-level level_0_no_obstacle_short \
  --gui
```

开始一次小规模 PPO debug training：

```bash
python3 scripts/train_task05_ppo_debug.py --config configs/task05_ppo_debug_train.json
```

训练后 eval checkpoint：

```bash
python3 scripts/eval_task05_ppo_debug.py \
  --checkpoint outputs/task05/<run_id>/checkpoints/final_model.zip \
  --output outputs/task05/<run_id>/eval/eval_rollout.jsonl
```

回放 eval JSONL：

```bash
python3 scripts/view_task03_rollout.py --trace outputs/task05/<run_id>/eval/eval_rollout.jsonl
```

画训练曲线：

```bash
python3 scripts/plot_task05_training_curves.py --run-dir outputs/task05/<run_id>
```

## 第六阶段计划

第六阶段是 **NavRL-Guided Multi-Scenario PPO Training with Case Replay**。

第六阶段在 TASK_05 的训练链路上增加 static / dynamic / latent_dynamic /
mixed_static_dynamic 场景、reward profiles、VecEnv / VecNormalize hooks、随机
策略与 checkpoint eval、case selection、rollout metrics 和 GIF/fallback
replay。训练和 eval 跑在 `Task04GymPybulletDronesRLEnv` / gym-pybullet-drones
物理后端上；GIF 是从 eval JSONL 生成的 case replay，不是 GUI 录屏。

它仍然不是正式 baseline，不报告正式 success rate，不提交训练产物。早期
100k / 350k debug 训练只观察到弱改善或失败案例；后续通过对照 NavRL 和
失败轨迹定位问题，已经在三类场景得到初步可观察的 diagnostic trained
behavior，但仍不能当论文结果使用。

如果要更密切参考 NavRL，优先使用 `task06_navrl_style_*_ppo.json` 配置。
这一路线使用结构化 `state` / `lidar` / `direction` / `dynamic_obstacle`
观测、live PyBullet `rayTestBatch` lidar、SB3 `MultiInputPolicy` feature
extractor、4-env `DummyVecEnv` 和更长的 multi-level curriculum，参数也按
NavRL 的 PPO 尺度对齐。当前最佳本地诊断结果为：static 13/16 success
但仍有 3/16 collision；dynamic 10/16 success、2/16 collision、4/16
timeout；latent_dynamic 10/16 success、0/16 collision、6/16 timeout。
这些数字只用于本地问题定位，不是正式 success rate。

第六阶段文档：

- 设计：[`docs/06_task06_navrl_guided_multiscenario_ppo_case_replay.md`](docs/06_task06_navrl_guided_multiscenario_ppo_case_replay.md)
- NavRL-guided 调整记录：[`docs/navrl_guided_training_adjustments_task06.md`](docs/navrl_guided_training_adjustments_task06.md)
- 完成报告：[`docs/TASK_06_COMPLETION_REPORT.md`](docs/TASK_06_COMPLETION_REPORT.md)

运行 static PPO diagnostic training，默认 100k debug timesteps：

```bash
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_static_ppo.json
```

运行更接近 NavRL 结构的 static PPO diagnostic training，默认 1M debug
timesteps：

```bash
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_navrl_style_static_ppo.json
```

运行 dynamic / latent_dynamic，默认也是 100k debug timesteps：

```bash
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_dynamic_ppo.json
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_latent_dynamic_ppo.json
```

对应的 NavRL-style dynamic / latent_dynamic 配置：

```bash
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_navrl_style_dynamic_ppo.json
python3 scripts/train_task06_multiscenario_ppo.py --config configs/task06_navrl_style_latent_dynamic_ppo.json
```

NavRL-style 训练配置默认：

```text
num_envs: 4
total_timesteps: 1000000
max_timesteps: 4000000
lidar: live PyBullet rayTestBatch when gym-pybullet-drones is active
static curriculum_levels: static_obstacle_easy, static_obstacle_medium
dynamic curriculum_levels: dynamic_crossing_easy, mixed_static_dynamic_easy
latent curriculum_levels: latent_dynamic_easy
```

训练脚本会自动写入 random/trained eval summary、case JSONL 和 GIF/fallback
到 `outputs/task06/<run_id>/eval/...`。如果只想单独跑随机策略 batch eval：

```bash
python3 scripts/eval_task06_multiscenario.py \
  --curriculum-level dynamic_crossing_easy \
  --random-policy \
  --episodes 8 \
  --render-gifs \
  --output outputs/task06/eval/dynamic_random_batch
```

单独跑 checkpoint batch eval 时需要同时加载训练时保存的 VecNormalize：

```bash
python3 scripts/eval_task06_multiscenario.py \
  --curriculum-level dynamic_crossing_easy \
  --checkpoint outputs/task06/<run_id>/checkpoints/final_model.zip \
  --vecnormalize outputs/task06/<run_id>/vecnormalize.pkl \
  --episodes 8 \
  --render-gifs \
  --output outputs/task06/<run_id>/eval/dynamic_checkpoint_batch
```

NavRL-style 配置默认不使用 VecNormalize，单独 eval 时需要指定
`--observation-style navrl_style`，并且不传 `--vecnormalize`：

```bash
python3 scripts/eval_task06_multiscenario.py \
  --curriculum-level static_obstacle_easy \
  --checkpoint outputs/task06/<run_id>/checkpoints/task06_navrl_style_static_ppo_debug_350000_steps.zip \
  --episodes 8 \
  --render-gifs \
  --max-speed 2.0 \
  --observation-style navrl_style \
  --output outputs/task06/<run_id>/eval/navrl_style_checkpoint_batch
```

查看本地 GIF：

```bash
xdg-open outputs/task06_visual_review/current_best/static_success.gif
xdg-open outputs/task06_visual_review/current_best/dynamic_success.gif
xdg-open outputs/task06_visual_review/current_best/latent_success.gif
xdg-open outputs/task06_visual_review/current_best/manifest.json
```

如果只想把某个 JSONL 重新渲染为 GIF 或 fallback summary：

```bash
python3 scripts/render_task06_case_gif.py \
  --trace outputs/task06/<run_id>/eval/trained/episode_000.jsonl \
  --output outputs/task06/<run_id>/eval/trained/episode_000.gif
```

## 项目结构原则

仓库结构保持简单：

```text
pirl-navrl/
  README.md
  THIRD_PARTY_NOTICES.md
  docs/
  external/
  codex_tasks/
  pirl_navrl/
  scripts/
  tests/
  configs/
```

源码、脚本、配置和测试按编号任务逐步创建。不要提前堆目录，不提交 checkpoint、视频、GIF、TensorBoard、wandb 或其他大产物。

## 项目管理

项目管理规则见 [`docs/PROJECT_MANAGEMENT.md`](docs/PROJECT_MANAGEMENT.md)。

第一阶段任务见 [`codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md`](codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md)。

## 本地环境

推荐环境：

```bash
conda create -n pirl-navrl-drones python=3.10
conda activate pirl-navrl-drones
bash scripts/setup_external_repos.sh
pip install -e external/gym-pybullet-drones
pip install -e .
```

检查安装：

```bash
python scripts/check_gym_pybullet_drones_install.py
```

查看 gym-pybullet-drones 内置示例：

```bash
python scripts/run_gym_pybullet_drones_examples.py
```

安全启动某个内置示例：

```bash
python scripts/run_gym_pybullet_drones_examples.py --run --example pid.py
```

运行第一阶段 PIRL-NavRL diagnostic demo：

```bash
python scripts/run_phase1_simple_pirl_navrl_demo.py
```
