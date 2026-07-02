# 外部仓库

本目录用于本地克隆外部仓库。

推荐本地结构：

```bash
external/gym-pybullet-drones/
external/NavRL/
```

这些目录默认被 `.gitignore` 忽略，不应直接提交。除非后续任务明确决定使用 submodule 或 vendored snapshot，否则只保留本地克隆。

## 克隆命令

```bash
git clone https://github.com/learnsyslab/gym-pybullet-drones.git external/gym-pybullet-drones
git clone https://github.com/Zhefan-Xu/NavRL.git external/NavRL
```

`gym-pybullet-drones` 是第一阶段训练底座。`NavRL` 在第一阶段只作为参考。