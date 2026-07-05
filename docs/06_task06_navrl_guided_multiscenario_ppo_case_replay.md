# TASK_06 设计：NavRL-Guided Multi-Scenario PPO Training with Top-Down Case Replay

## 1. 阶段定位

TASK_06 是多场景 PPO 稳定化训练与案例回放阶段。TASK_06 直接朝论文级实现前置工作推进：场景、训练协议、评估、案例可视化、失败分析和记录标准都要更严格。

本阶段仍不发布正式论文结论，不接 EGO baseline，不声称复现 NavRL，不使用 NavRL checkpoint 或结果，不提交训练产物。

TASK_06 必须覆盖：

```text
static
dynamic
latent_dynamic
```

## 2. Smoke 不等于完成

2k、4k、10k step 以内只能算 smoke。Smoke 只用于依赖和脚本检查，不能算 TASK_06 完成，不能用于 final checkpoint，也不能用于最终 success/failure case selection。

有效执行状态只有：

```text
completed_full_training
blocked
smoke_only_not_complete
```

如果无法完成 full training，必须写：

```text
docs/TASK_06_BLOCKED_TRAINING_REPORT.md
```

如果只完成 smoke，必须写：

```text
docs/TASK_06_SMOKE_ONLY_REPORT.md
```

每个 scenario group 必须输出：

```text
training_completion_status.json
```

## 3. Training budget

必须新增：

```text
configs/task06_training_budget.json
```

最低预算：

```text
static: min_timesteps_required = 100000, initial_budget_timesteps = 300000
dynamic: min_timesteps_required = 150000, initial_budget_timesteps = 500000
latent_dynamic: min_timesteps_required = 150000, initial_budget_timesteps = 500000
```

配置必须包含：

```text
smoke_timesteps
smoke_is_completion = false
min_timesteps_required
initial_budget_timesteps
max_timesteps_safety_cap
eval_freq
patience_evals
```

训练可以继续延长，但必须记录原因、中间 eval 和 NavRL 参考。

## 4. 训练脚本模式

训练脚本必须支持：

```text
--mode full
--mode smoke
--scenario-group static|dynamic|latent_dynamic|mixed_static_dynamic
```

默认必须是 `--mode full`。只有用户显式传 `--mode smoke` 才允许短跑。

### 4.1 当前本地实现状态

当前实现已经完成 static、dynamic、latent_dynamic 三类 diagnostic PPO
训练、random-vs-trained batch eval、case selection 和 GIF replay。早期
100k / 350k 训练只看到接近目标的弱改善，没有成功案例；这些结果已作为失败
诊断保留，不再代表当前最佳状态。

根据 NavRL 重新补强的训练路线已经加入：

- live gym-pybullet-drones 下使用 PyBullet `rayTestBatch` lidar，保持
  NavRL-style `(1, 36, 4)` lidar tensor；
- schema/offline 测试保留 scenario-geometry fallback；
- `Task06NavRLStyleEnv` 使用 `state` / `lidar` / `direction` /
  `dynamic_obstacle` dict observation；
- `NavRLStyleFeatureExtractor` 使用 CNN/MLP fusion；
- `num_envs` 支持多 PyBullet DIRECT client 的 `DummyVecEnv`；
- `curriculum_levels` 支持 per-episode level rotation；
- NavRL-style configs 当前设为 4 env、1M diagnostic timesteps、4M local
  safety upper bound。

最近一次定位不是单纯调 reward，而是先对照 NavRL 和失败轨迹定位问题：

- dynamic / latent easy 场景去掉额外静态障碍，只保留一个 moving 或
  sudden-moving obstacle，避免把混合场景误当作 easy 动态场景；
- strict metrics 会按 `min_clearance <= collision_radius` 重算 collision，
  避免视觉上发生碰撞但 summary 仍写 success；
- latent 失败主要来自高度漂移，adapter 加入 altitude hold，让 PPO 重点处理
  水平导航和避障；
- static gate-easy 障碍从路径中心线偏移，dynamic/latent gate-easy 障碍减小
  并放慢，用于先通过三类简单场景 gate，再逐步增加复杂度。

当前最佳本地 diagnostic 观察：

| Scenario group | Best local observation |
| --- | --- |
| static | gate-easy strict eval: 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.348 m |
| dynamic | gate-easy strict eval: 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.348 m |
| latent_dynamic | gate-easy strict eval: 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.349 m |

这些结果说明三类简单 gate 场景已有可观察的 trained behavior，并且通过了
当前阶段的 strict diagnostic gate。它仍不是正式 baseline，也不是论文级
success rate；下一步应冻结 gate 协议后逐步增加障碍物数量、运动速度和场景
复杂度。

当前 GIF 是从 gym-pybullet-drones eval JSONL 生成的 case replay，用于快速
查看轨迹、障碍物、动态障碍物位置和失败类型；它不是 PyBullet GUI 录屏。
当前统一审查目录：

```text
outputs/task06_visual_review/current_best/
outputs/task06_visual_review/gate_easy_final/
```

## 5. NavRL-guided 调整要求

必须维护：

```text
docs/navrl_guided_training_adjustments_task06.md
```

训练中遇到问题时，必须回看 NavRL，而不是只盲调 PPO 参数。每次调整 scenario、observation、reward、training config、runner、action constraint、gate、case replay 或 visualization，都要记录具体 NavRL 文件/module/config/script，以及 PIRL-NavRL 如何适配。

可以密切参考 NavRL 的训练思路、结构、参数、runner、gate、observation、reward、curriculum、dynamic obstacle 组织和可视化流程。禁止整包迁移 NavRL 或声称复现 NavRL。

## 6. 场景要求

### Static

- seeded start / goal；
- 1-5 个静态障碍；
- 障碍物接近但不堵死 start-goal corridor；
- 支持 easy / medium；
- reward 包含 progress、clearance、collision、smoothness、success、timeout；
- 参考 NavRL 静态障碍采样和地图组织。

### Dynamic

- 至少一个 moving obstacle；
- 优先 linear crossing；
- 配置速度、起止点和 active time window；
- observation 包含动态障碍相对位置和相对速度；
- reward 包含 dynamic risk penalty；
- 参考 NavRL 动态障碍处理。

### Latent dynamic

- obstacle 初期静止或低风险；
- trigger_step 或 trigger_radius 后开始运动；
- 不向 policy 泄露未来 trigger label；
- eval 能识别 late reaction、near miss、latent_trigger_failure；
- 参考 NavRL 中 dynamic risk、gate、safe action 或运动障碍相关思路。

## 7. 稳定化模块

新增或更新：

```text
pirl_navrl/platforms/gym_pybullet_drones/feature_scaling.py
pirl_navrl/evaluation/reward_profiles.py
pirl_navrl/analysis/rollout_metrics.py
pirl_navrl/training/vec_env.py
pirl_navrl/training/task06_multiscenario.py
```

必须支持 feature scaling、DummyVecEnv、VecNormalize、separate eval env、checkpoint save/load、normalization stats save/load、NaN/divergence detection 和 intermediate checkpoint eval。

Reward profiles 至少包含：

```text
goal_only
static_avoidance
dynamic_avoidance
latent_risk
```

可参考 NavRL 实现轻量 action gate / safety gate / velocity gate，但必须可配置、可关闭、可记录，且不能泄露未来 latent trigger。

## 8. Top-down gym-pybullet GIF/video

案例可视化优先生成 gym-pybullet / PyBullet 俯视角视频或 GIF。

新增或更新：

```text
pirl_navrl/visualization/gif_renderer.py
scripts/render_task06_case_gif.py
```

要求：

- camera 固定在 arena 上方，向下看；
- 显示 start、goal、drone、trajectory、static obstacles、dynamic obstacles、latent trigger state；
- 显示 step、distance_to_goal、min_clearance、success/collision/timeout、failure_type；
- success/best_non_success 和 representative failure 都要有 GIF/video 或 fallback summary；
- 产物保存在 `outputs/task06/...`，不得提交。

## 9. Case selection

每个 scenario group 在 full training 后必须选择：

```text
success_case 或 best_non_success_case
representative failure_case
```

没有 true success 时必须输出 best_non_success_case，不能把失败伪装成成功。

Failure taxonomy 至少包括：

```text
collision_failure
timeout_failure
near_miss_failure
control_instability_failure
dynamic_late_reaction_failure
latent_trigger_failure
```

每个 failure summary 必须包含 suspected cause、NavRL reference consulted 和 next suggested fix。

## 10. Completion criteria

TASK_06 只有满足以下条件才算完成：

1. `pytest -q` 通过；
2. static / dynamic / latent_dynamic 三类场景可生成；
3. 三类场景均已 full training，或对未完成项写明 blocked；
4. 任一 2k/4k/10k smoke run 不得标记为完成；
5. 每类都有 random policy eval 和 trained checkpoint eval；
6. 每类都有 success 或 best_non_success case；
7. 每类都有 representative failure case；
8. 每类 case 都有 top-down gym-pybullet GIF/video 或明确 fallback summary；
9. 每类都有 random vs trained summary metrics；
10. 效果差时，必须写 failure taxonomy、NavRL reference 和下一步修正；
11. 不提交 outputs、checkpoints、GIF、videos、TensorBoard、wandb。

## 11. Required reports

Full training 完成后写：

```text
docs/TASK_06_TRAINING_EXECUTION_REPORT.md
```

Full training 未完成时写：

```text
docs/TASK_06_BLOCKED_TRAINING_REPORT.md
```

只完成 smoke 时写：

```text
docs/TASK_06_SMOKE_ONLY_REPORT.md
```

TASK_07 可以进入 PIRL risk / intent module prototype，但前提是 TASK_06 已经提供静态、动态、潜在动态三类可回放案例。
