# TASK_04 完成报告

## 结论

TASK_04 当前完成的是 pre-training gym-pybullet-drones RL-ready diagnostic
adapter。它把统一 `ScenarioConfig`、debug policy、reward、rollout recorder
接入真实 `gym-pybullet-drones` / PyBullet 物理后端。

本阶段不是训练阶段，不是正式 baseline，不报告 success rate，不提交
results、videos、checkpoints。

## 已完成内容

- `GymPybulletDronesSimpleAdapter` 接入真实 `VelocityAviary` 和 `Physics.PYB`。
- `Task04GymPybulletDronesRLEnv` 提供 Gymnasium-compatible `reset` / `step`。
- action 使用 normalized desired velocity，再转换为 `VelocityAviary` command。
- observation 输出固定 flattened vector，并保留 dict info。
- reward 输出 finite reward 和 `reward_terms`。
- 自定义 `ScenarioConfig` 障碍物注入到 PyBullet client，作为真实 collision body。
- sphere / cylinder 障碍物同时有 physical collision body 和 visual body。
- 默认 TASK_04 障碍物尺寸已缩小，避免相对 Crazyflie 视觉比例过大。
- GUI 默认使用查看优先 `--camera-control orbit`：
  - 关闭 mouse picking，避免左键拖动无人机；
  - 左键/右键拖动旋转视角；
  - 中键上下拖动或滚轮缩放；
  - 如需 PyBullet 原始 picking，可显式使用
    `--camera-control pybullet --enable-mouse-picking`。
- 可选 `--onboard-camera` 采样朝向 goal 的轻量相机，并把 `onboard_camera`
  统计写入 JSONL step record。
- GUI 默认保留 PyBullet 官方棋盘地面；障碍物 visual 使用更清楚的颜色和
  高面数圆柱显示，碰撞体仍保持 PyBullet 几何体。

## 运行命令

训练前 env check：

```bash
python3 scripts/check_task04_rl_ready_env.py
```

headless diagnostic rollout：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py
```

GUI 查看：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py \
  --gui \
  --camera-mode manual \
  --start -4 0 1 \
  --goal 3 2 1 \
  --max-steps 3000
```

GUI + 左侧 PyBullet preview + onboard camera diagnostic：

```bash
python3 scripts/run_task04_gym_pybullet_drones_rollout.py \
  --gui \
  --camera-mode manual \
  --show-pybullet-ui \
  --show-camera-preview \
  --onboard-camera \
  --start -4 0 1 \
  --goal 3 2 1 \
  --max-steps 3000
```

## 语义边界

- `terminated = success or collision`。
- `truncated = timeout only`。
- `platform_terminated` / `platform_truncated` 只保留在 `info`，不混入任务级
  termination。
- `goal_seeking_velocity_debug` 是无避障 debug policy；在含障碍物场景中发生
  collision 不代表框架失败。
- `collision_radius` 表示 agent safety radius from obstacle surface；
  `ObstacleConfig.radius` 表示障碍物几何半径。
- 当前 JSONL 是 diagnostic rollout trace，不是统一 baseline metrics。

## 验证结果

已通过：

```bash
python3 -m pytest -q
```

结果：

```text
37 passed
```

本阶段还做过短 rollout smoke，确认：

- 真实 gym-pybullet-drones 后端可 step；
- 自定义障碍物创建为 PyBullet body；
- `onboard_camera` diagnostic 字段可写入；
- 缩小后的障碍物尺寸进入 trace metadata。

这些 smoke 输出只用于本地验证，不作为提交产物。

## 未做内容

- 不训练 PPO。
- 不训练 PIRL。
- 不接 EGO baseline。
- 不做多 seed benchmark。
- 不报告 success rate。
- 不提交 results、videos、checkpoints、TensorBoard、wandb。

## 下一阶段前置

进入训练或 baseline 前还需要：

- 明确训练用 scenario suite 和多 seed 评估协议。
- 固化 collision / success / timeout 的论文级定义。
- 决定 observation 是否包含 camera / lidar / risk features。
- 决定 PPO debug training 的最小配置和 checkpoint 管理规则。
- 若接 EGO baseline，需要实现 EGO command -> gym-pybullet-drones action 的闭环。
