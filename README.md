# PIRL-NavRL

PIRL-NavRL is a clean research repository for **Predictive Intent-Risk Learning for UAV local navigation**.

This repository replaces the previous `pirl-nav-research` implementation as the forward route. The old lightweight simulator, deterministic policies, synthetic trainer, and review artifacts are not active components here.

## Current platform decision

Phase 1 uses **gym-pybullet-drones** as the lightweight UAV PyBullet training backbone.

- Primary Phase 1 backbone: <https://github.com/learnsyslab/gym-pybullet-drones>
- Long-term reference only: <https://github.com/Zhefan-Xu/NavRL>
- Immediate training dependency: gym-pybullet-drones + Stable-Baselines3/PyBullet
- Not immediate dependencies: Isaac Sim, ROS1/ROS2, NavRL training stack

## Phase 1 objective

Phase 1 is a setup and integration phase, not a paper-result phase.

The objective is to:

1. Pull and document NavRL and gym-pybullet-drones as external references.
2. Configure a reproducible local environment for gym-pybullet-drones.
3. Verify built-in gym-pybullet-drones examples.
4. Implement a simple PIRL-NavRL adapter/risk/shield proof-of-concept inside the gym-pybullet-drones integration layer.
5. Establish project-management, artifact, and experiment rules before formal experiments begin.

## Scope boundaries

Allowed in Phase 1:

- local cloning of external repositories under `external/`
- adapter/wrapper code around gym-pybullet-drones
- small JSON/JSONL diagnostic outputs
- import checks, smoke tests, and simple demo scripts
- documentation of NavRL as a reference architecture

Forbidden in Phase 1:

- copying old `pirl-nav-research` active implementation code
- writing a new simulator from scratch
- training with Isaac Sim
- attempting ROS deployment
- committing checkpoints, videos, GIFs, TensorBoard logs, wandb runs, or large artifacts
- claiming paper-level results

## Repository management

Project-management rules are defined in [`docs/PROJECT_MANAGEMENT.md`](docs/PROJECT_MANAGEMENT.md).

The first managed task is [`codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md`](codex_tasks/TASK_01_gym_pybullet_drones_phase1_setup_and_demo.md).
