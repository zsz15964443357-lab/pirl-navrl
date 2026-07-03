# 项目管理规则

本文档规定 PIRL-NavRL 的任务、审查、实验和产物管理方式。

## 1. 仓库定位

`pirl-navrl` 是新的主线研究仓库。旧 `pirl-nav-research` 只作为历史探索记录，不作为有效代码来源。

除非某个任务明确允许引用旧仓库中的某个文档片段，否则不得迁移旧仓库的 active code。

## 2. 任务管理

- 所有实现工作必须由 `codex_tasks/` 下的编号任务驱动。
- 不允许无任务实现。
- 当前任务没有实现、审查、修正和确认前，原则上不执行下一阶段任务。
- 可以提前整理下一阶段任务文档，但必须标注为“计划中”，并说明执行前置条件。
- 每个任务必须写清楚：目标、范围、禁止项、验收标准、最终报告要求。
- 每个任务必须标注输出性质：环境诊断、训练诊断、论文候选结果，三者不能混淆。

## 3. 平台管理

第一阶段使用 gym-pybullet-drones 作为轻量级无人机 PyBullet 训练底座。NavRL 仅作为长期参考。

第二阶段允许在任务边界内探索 EGO-Planner 官方 ROS sidecar bridge，但该探索仅用于 diagnostic，不代表当前主训练平台切换到 ROS。

当前原则：

- gym-pybullet-drones 是早期主平台。
- EGO-Planner 是 official sidecar bridge 可行性验证对象，后续是否作为 official baseline 取决于 TASK_02 结论。
- NavRL 是链路、结构、模块划分、部署路径和参数组织参考，不作为 baseline。

当前禁止：

- 不使用 Isaac Sim 训练
- 不做 ROS 部署
- 不从零写仿真器
- 不复制旧 `pirl-nav-research` 的有效代码
- 不把 NavRL 当作 baseline
- 不声称论文级结果

## 4. 产物管理

默认不提交大文件和不可审查产物。

未明确批准前禁止提交：

- 模型 checkpoint
- 视频
- GIF
- TensorBoard 日志
- wandb 运行记录
- 大型 rollout dump
- 二进制实验归档

默认允许提交：

- Markdown 文档
- 小型 YAML/JSON 配置
- 小型 JSON/JSONL smoke-test 结果
- 源码和测试

## 5. 实验追踪

任何会产生实验结果的脚本，至少要记录：

- git commit
- task id
- platform id
- algorithm id
- seed
- environment id
- config path
- metric source
- 输出性质：diagnostic 或 paper-candidate

## 6. 审查门槛

任务完成报告必须包含：

- 修改文件
- 运行命令
- 测试结果
- 外部依赖
- 生成产物
- 当前限制
- 下一步需要人工决定的问题

## 7. 论文级升级规则

第一阶段和第二阶段输出都不是论文结果。进入论文级实验前，必须另开任务并明确：

- 固定 train/eval protocol
- baseline matrix
- ablation matrix
- multi-seed 计划
- 结果聚合方式
- 图表生成方式
- 可复现记录
- 产物提交策略

如果使用 EGO-Planner official sidecar 作为论文 baseline，必须另开任务并明确官方代码 commit、bridge 改动、平台差异和结果解释边界。

NavRL 不进入 baseline matrix。NavRL 只能作为参考架构或未来跨平台迁移路线的参考对象。

## 8. 结构简约原则

仓库目录宁可少，不要提前堆空目录。

第一阶段只保留：

```text
README.md
THIRD_PARTY_NOTICES.md
docs/
external/
codex_tasks/
```

源码、脚本、配置和测试只在任务真正需要时创建。