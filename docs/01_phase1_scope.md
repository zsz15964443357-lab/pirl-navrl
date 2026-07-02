# 第一阶段范围

## 目标

围绕 gym-pybullet-drones 建立干净的 PIRL-NavRL 仓库，并完成一个简单集成演示。

## 外部仓库

- 主底座：`https://github.com/learnsyslab/gym-pybullet-drones`
- 长期参考：`https://github.com/Zhefan-Xu/NavRL`

## 交付物

- 本地 clone / setup 流程
- import 检查脚本
- gym-pybullet-drones 内置示例启动脚本或启动说明
- 简单 PIRL-NavRL adapter / risk / shield 演示
- import、配置、risk-shield contract 测试
- Codex 最终报告

## 非目标

- 不使用 Isaac Sim 训练
- 不做 ROS 部署
- 不写自定义仿真器
- 不声称论文结果
- 不提交大产物

## 简单演示定义

演示必须包裹 gym-pybullet-drones 已有环境或示例，不得重写仿真器。

演示应包含：

- observation / action adapter
- 简单 action-conditioned risk score
- shield threshold
- intervention logging
- 小型 JSON/JSONL 指标输出

## 完成门槛

只有当 `codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md` 的验收标准被满足，或阻塞项被明确记录后，第一阶段才算完成。