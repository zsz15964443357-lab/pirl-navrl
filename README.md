# PIRL-NavRL

PIRL-NavRL 是一个新的、干净的研究仓库，用于推进 **基于预测意图-风险的无人机局部导航强化学习**。

本仓库取代旧的 `pirl-nav-research` 作为后续主线。旧仓库里的轻量仿真器、手写策略、合成训练器和审查产物不再作为本仓库的有效实现代码。

## 当前平台与外部项目定位

第一阶段使用 **gym-pybullet-drones** 作为轻量级无人机 PyBullet 训练底座。

- 第一阶段主底座：<https://github.com/learnsyslab/gym-pybullet-drones>
- EGO-Planner：后续作为外部 ROS sidecar 桥接可行性验证对象；如果可行，再考虑发展为 official EGO baseline
- NavRL：长期参考仓库，用于参考训练链路、代码结构、模块划分、部署路径和关键参数；**不作为 baseline**
- 当前训练依赖：gym-pybullet-drones + Stable-Baselines3 + PyBullet
- 第一阶段不引入：Isaac Sim、ROS1/ROS2、NavRL 训练栈

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
- 尝试 ROS 部署
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

## 项目结构原则

仓库结构保持简单：

```text
pirl-navrl/
  README.md
  THIRD_PARTY_NOTICES.md
  docs/
  external/
  codex_tasks/
```

第一阶段只放文档和任务文件。源码、脚本、配置和测试由编号任务执行时再按需创建，避免提前堆目录。

## 项目管理

项目管理规则见 [`docs/PROJECT_MANAGEMENT.md`](docs/PROJECT_MANAGEMENT.md)。

第一阶段任务见 [`codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md`](codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md)。

## 第一阶段本地环境

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
python scripts/run_phase1_simple_pirl_navrl_demo.py \
  --config configs/phase1_simple_demo.json
```

该 demo 只输出小型 JSONL 诊断记录，默认路径为
`results/phase1_simple_demo_metrics.jsonl`。第一阶段输出均为 `diagnostic`，
不是论文级结果。
