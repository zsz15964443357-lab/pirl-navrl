# TASK 01: gym-pybullet-drones Phase 1 setup and simple PIRL-NavRL demo

## Status

Open.

## Required skill

Use the academic-research-suite skill.

## Repository

`https://github.com/zsz15964443357-lab/pirl-navrl`

## Objective

Initialize Phase 1 around `gym-pybullet-drones` as the lightweight UAV PyBullet training backbone, while pulling NavRL as a long-term reference only.

This task establishes environment setup, external repository references, and a simple PIRL-NavRL adapter/risk/shield integration demo. It must not claim paper-grade results.

## Strategic decisions

- Do not use old `pirl-nav-research` active code.
- Do not implement a custom simulator from scratch.
- Do not use Isaac Sim as the immediate training backend.
- Do not use ROS1/ROS2 as the immediate deployment backend.
- Do not train NavRL in this phase.
- Do not claim paper results.
- Do not create synthetic training metrics.
- Do not commit large generated artifacts.

## External repositories

Primary implementation backbone:

- `https://github.com/learnsyslab/gym-pybullet-drones`

Reference-only backbone:

- `https://github.com/Zhefan-Xu/NavRL`

## Required work

### 1. External setup

Create or update `scripts/setup_external_repos.sh` to clone:

```bash
git clone https://github.com/learnsyslab/gym-pybullet-drones.git external/gym-pybullet-drones
git clone https://github.com/Zhefan-Xu/NavRL.git external/NavRL
```

The script must be idempotent or fail gracefully with clear instructions if folders already exist.

### 2. Environment setup

Document and support this environment path:

```bash
conda create -n pirl-navrl-drones python=3.10
conda activate pirl-navrl-drones
pip install -e external/gym-pybullet-drones
pip install -e .
```

Create `scripts/check_gym_pybullet_drones_install.py` to verify imports:

- `gym_pybullet_drones`
- `stable_baselines3`
- `pybullet`
- `pirl_navrl`

If dependencies are absent, the script must fail gracefully and print setup instructions.

### 3. Built-in example check

Create `scripts/run_gym_pybullet_drones_examples.py` to document or safely launch built-in gym-pybullet-drones examples.

Acceptable examples include built-in PID or RL examples from the external repository. The script must avoid committing generated videos, checkpoints, or large outputs.

### 4. PIRL-NavRL simple demo

Create a small integration demo around gym-pybullet-drones without rewriting its simulator.

Required components:

- observation/action adapter
- action-conditioned risk scorer
- threshold-based shield wrapper
- intervention logging
- small JSON or JSONL metric output

Required source paths:

- `pirl_navrl/adapters/gym_pybullet_drones_adapter.py`
- `pirl_navrl/risk/action_conditioned_risk.py`
- `pirl_navrl/shield/risk_shield.py`
- `pirl_navrl/metrics/episode_metrics.py`
- `scripts/run_phase1_simple_pirl_navrl_demo.py`

The simple risk/shield demo may be heuristic in Phase 1, but it must clearly label outputs as diagnostic, not paper results.

### 5. Tests

Create and run tests:

- `tests/test_imports.py`
- `tests/test_phase1_config_schema.py`
- `tests/test_risk_shield_contract.py`

Tests must not require Isaac Sim, ROS, GPU, NavRL training, or large external artifacts.

## Artifact policy

Do not commit:

- checkpoints
- `.zip` model files
- TensorBoard logs
- wandb runs
- videos
- GIFs
- large rollout dumps
- copied external repositories

Allowed:

- source code
- tests
- Markdown documentation
- small YAML configs
- small JSON/JSONL diagnostic summaries

## Acceptance criteria

- Repository imports pass.
- External setup script exists and documents/pulls both repositories.
- Install check script verifies or gracefully explains missing dependencies.
- Built-in gym-pybullet-drones example flow is documented or runnable.
- Simple PIRL-NavRL risk/shield demo exists.
- Tests pass or blockers are explicitly documented.
- No custom simulator is created.
- No old repository active code is copied.
- No Isaac Sim or ROS dependency is introduced.
- No large generated artifacts are committed.

## Final report requirements

Codex final report must include:

- branch and commit
- files created/modified
- commands run
- dependency status
- whether gym-pybullet-drones import succeeded
- whether built-in examples ran
- whether Phase 1 demo ran
- test results
- artifacts generated
- known blockers
- next manual decision required
