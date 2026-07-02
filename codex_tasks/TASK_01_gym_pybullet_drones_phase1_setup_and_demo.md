# TASK 01：gym-pybullet-drones 第一阶段环境配置与简单演示

## 状态

Open。

## 必须使用的技能

使用 academic-research-suite skill。

## 仓库

`https://github.com/zsz15964443357-lab/pirl-navrl`

## 目标

围绕 `gym-pybullet-drones` 初始化第一阶段。它是当前轻量级无人机 PyBullet 训练底座。NavRL 只作为长期参考。

本任务要完成环境配置、外部仓库拉取、基础检查，以及一个简单的 PIRL-NavRL adapter / risk / shield 集成演示。本任务不得声称论文级结果。

## 战略决策

- 不使用旧 `pirl-nav-research` 的有效代码。
- 不从零写自定义仿真器。
- 不使用 Isaac Sim 作为当前训练后端。
- 不使用 ROS1/ROS2 作为当前部署后端。
- 不训练 NavRL。
- 不声称论文结果。
- 不创建合成训练指标来冒充实验结果。
- 不提交大产物。

## 外部仓库

当前主底座：

- `https://github.com/learnsyslab/gym-pybullet-drones`

长期参考：

- `https://github.com/Zhefan-Xu/NavRL`

## 必做工作

### 1. 外部仓库 setup

创建或更新 `scripts/setup_external_repos.sh`，用于克隆：

```bash
git clone https://github.com/learnsyslab/gym-pybullet-drones.git external/gym-pybullet-drones
git clone https://github.com/Zhefan-Xu/NavRL.git external/NavRL
```

脚本必须具备幂等性，或在目录已存在时给出清晰提示。

### 2. 环境配置

文档和脚本应支持如下环境路径：

```bash
conda create -n pirl-navrl-drones python=3.10
conda activate pirl-navrl-drones
pip install -e external/gym-pybullet-drones
pip install -e .
```

创建 `scripts/check_gym_pybullet_drones_install.py`，检查导入：

- `gym_pybullet_drones`
- `stable_baselines3`
- `pybullet`
- `pirl_navrl`

如果依赖不存在，脚本必须优雅失败，并打印安装说明。

### 3. 内置示例检查

创建 `scripts/run_gym_pybullet_drones_examples.py`，用于说明或安全启动 gym-pybullet-drones 的内置示例。

可以使用 PID 或 RL 示例。脚本不得提交或默认生成视频、checkpoint、大日志。

### 4. PIRL-NavRL 简单演示

围绕 gym-pybullet-drones 创建一个小型集成演示，不得重写仿真器。

演示必须包含：

- observation / action adapter
- action-conditioned risk scorer
- threshold-based shield wrapper
- intervention logging
- 小型 JSON 或 JSONL 指标输出

建议源码路径：

- `pirl_navrl/adapters/gym_pybullet_drones_adapter.py`
- `pirl_navrl/risk/action_conditioned_risk.py`
- `pirl_navrl/shield/risk_shield.py`
- `pirl_navrl/metrics/episode_metrics.py`
- `scripts/run_phase1_simple_pirl_navrl_demo.py`

第一阶段的 risk / shield 可以是启发式实现，但输出必须标注为 diagnostic，不得标注为 paper result。

### 5. 测试

创建并运行：

- `tests/test_imports.py`
- `tests/test_phase1_config_schema.py`
- `tests/test_risk_shield_contract.py`

测试不得依赖 Isaac Sim、ROS、GPU、NavRL 训练或大型外部产物。

## 产物策略

禁止提交：

- checkpoint
- `.zip` 模型文件
- TensorBoard 日志
- wandb 运行记录
- 视频
- GIF
- 大型 rollout dump
- 被复制进仓库的外部项目源码

允许提交：

- 源码
- 测试
- Markdown 文档
- 小型 YAML 配置
- 小型 JSON/JSONL 诊断结果

## 验收标准

- 仓库 import 通过。
- 外部仓库 setup 脚本存在，并能拉取或清晰说明如何拉取两个仓库。
- 安装检查脚本能验证依赖，或在缺依赖时清晰提示。
- gym-pybullet-drones 内置示例流程被记录或可运行。
- 简单 PIRL-NavRL risk/shield demo 存在。
- 测试通过，或阻塞项被明确记录。
- 未创建自定义仿真器。
- 未复制旧仓库有效代码。
- 未引入 Isaac Sim 或 ROS 依赖。
- 未提交大产物。

## Codex 最终报告要求

报告必须包含：

- 分支和 commit
- 新增/修改文件
- 运行命令
- 依赖状态
- gym-pybullet-drones import 是否成功
- 内置示例是否运行
- 第一阶段 demo 是否运行
- 测试结果
- 生成产物
- 已知阻塞
- 下一步需要人工决定的问题