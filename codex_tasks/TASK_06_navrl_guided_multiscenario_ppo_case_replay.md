# TASK_06: NavRL-Guided Multi-Scenario PPO Training with Top-Down Case Replay

## 0. Positioning

TASK_06 is the multi-scenario PPO stabilization and case-replay stage. It builds on TASK_05, but it must not stop at a tiny smoke run. The goal is to move toward paper-grade implementation quality: stronger scenario design, longer training runs, robust evaluation, clear failure taxonomy, and top-down visual evidence for each scenario group.

This task is still not a formal paper result stage. Do not publish formal success-rate claims, do not use EGO as a baseline, do not claim NavRL reproduction, and do not use NavRL checkpoints or results. Training artifacts remain local under `outputs/`.

## 1. Non-negotiable execution rule

A 2k/4k/10k run is only a smoke check. It is not TASK_06 completion.

TASK_06 has three valid execution states:

```text
smoke: dependency and script check only
full: required training budget reached
blocked: full training could not be completed and a BLOCKED report explains why
```

Hard requirements:

- Smoke checkpoints must not be used as final trained checkpoints.
- Smoke runs must not be used for final success/failure case selection.
- If only smoke runs are completed, write `docs/TASK_06_SMOKE_ONLY_REPORT.md`; do not write a completion report.
- If full training cannot run, write `docs/TASK_06_BLOCKED_TRAINING_REPORT.md` with the reason, logs summary, timesteps reached, and next fix.
- Every scenario group must end with `training_completion_status.json` containing one of: `completed_full_training`, `blocked`, or `smoke_only_not_complete`.

## 2. Required training budget config

Create:

```text
configs/task06_training_budget.json
```

It must include at least:

```json
{
  "smoke_timesteps": 4096,
  "smoke_is_completion": false,
  "scenario_budgets": {
    "static": {
      "min_timesteps_required": 100000,
      "initial_budget_timesteps": 300000,
      "max_timesteps_safety_cap": 1000000,
      "eval_freq": 10000,
      "patience_evals": 10
    },
    "dynamic": {
      "min_timesteps_required": 150000,
      "initial_budget_timesteps": 500000,
      "max_timesteps_safety_cap": 1500000,
      "eval_freq": 10000,
      "patience_evals": 12
    },
    "latent_dynamic": {
      "min_timesteps_required": 150000,
      "initial_budget_timesteps": 500000,
      "max_timesteps_safety_cap": 1500000,
      "eval_freq": 10000,
      "patience_evals": 12
    }
  }
}
```

These are execution lower bounds for TASK_06, not final paper hyperparameters. If a longer run is needed, extend the budget and record why.

## 3. Training script mode

`scripts/train_task06_multiscenario_ppo.py` must support:

```text
--mode full
--mode smoke
--scenario-group static|dynamic|latent_dynamic|mixed_static_dynamic
```

Default mode must be `full`. Short training is allowed only when the user explicitly passes `--mode smoke`.

In `full` mode, the script must read `configs/task06_training_budget.json`. If it does not reach `min_timesteps_required`, it must not mark the run complete.

## 4. NavRL-guided adjustment requirement

Maintain:

```text
docs/navrl_guided_training_adjustments_task06.md
```

Every scenario, observation, reward, PPO, runner, action gate, safety gate, curriculum, evaluation, or visualization change must record:

```text
NavRL reference
Observed setting
PIRL-NavRL adaptation
Reason
Result / observation
Next change
```

When training performs poorly, Codex must consult NavRL again before changing PPO parameters blindly. The document must identify the concrete NavRL file/module/config inspected and explain how the design was adapted.

NavRL may be used as a close engineering reference for scenario structure, dynamic obstacle design, observation schema, reward shaping, runner structure, training parameters, action constraints, gate-like logic, checkpoint cadence, and visualization practice. Do not wholesale migrate NavRL and do not claim NavRL reproduction.

## 5. Scenario groups

Support at least:

```text
static
dynamic
latent_dynamic
mixed_static_dynamic
```

Recommended levels:

```text
static_obstacle_easy
static_obstacle_medium
dynamic_crossing_easy
latent_dynamic_easy
mixed_static_dynamic_easy
```

Static scenarios must include seeded start/goal and static obstacles near the navigation corridor. Dynamic scenarios must include at least one moving obstacle, preferably a linear crossing obstacle. Latent-dynamic scenarios must include an obstacle that initially appears static or low-risk and later starts moving after a trigger step or trigger distance. Future trigger labels must not be leaked directly to the policy.

## 6. Observation, reward, and stabilization modules

Add or update:

```text
pirl_navrl/platforms/gym_pybullet_drones/feature_scaling.py
pirl_navrl/evaluation/reward_profiles.py
pirl_navrl/analysis/rollout_metrics.py
pirl_navrl/training/vec_env.py
pirl_navrl/training/task06_multiscenario.py
```

Required reward profiles:

```text
goal_only
static_avoidance
dynamic_avoidance
latent_risk
```

Training must support DummyVecEnv, VecNormalize, separate eval env, checkpoint save/load, normalization stats save/load, random-vs-trained evaluation, and NaN/divergence detection.

A lightweight gate or action constraint is allowed when inspired by NavRL. If enabled, it must be configurable and recorded in the NavRL adjustment document. It must not leak future latent-trigger information.

## 7. Top-down gym-pybullet visualization

Case visualization should prioritize top-down gym-pybullet or PyBullet video/GIF.

Add or update:

```text
pirl_navrl/visualization/gif_renderer.py
scripts/render_task06_case_gif.py
```

Requirements:

- Prefer top-down / bird's-eye camera over side view.
- Camera should be fixed above the arena and point downward.
- Show start, goal, drone, trajectory, static obstacles, dynamic obstacles, latent trigger state, current step, distance-to-goal, min clearance, and final status.
- Generate videos or GIFs for success/best-non-success and representative failure cases.
- If rendering dependencies are missing, write a fallback summary JSON explaining why no GIF/video was produced.
- All GIF/video outputs stay under `outputs/task06/...` and must not be committed.

## 8. Case selection

For every scenario group after full training, select:

```text
success_case or best_non_success_case
representative failure_case
```

If no true success exists, do not fake one. Output `best_non_success_case` with:

```json
{
  "case_type": "best_non_success_case",
  "reason": "no_success_found"
}
```

Failure cases must be classified as one of:

```text
collision_failure
timeout_failure
near_miss_failure
control_instability_failure
dynamic_late_reaction_failure
latent_trigger_failure
```

Each failure summary must include the suspected cause, the NavRL reference consulted, and the next suggested fix.

## 9. Required scripts and configs

Add or update:

```text
scripts/train_task06_multiscenario_ppo.py
scripts/eval_task06_multiscenario.py
scripts/select_task06_cases.py
scripts/render_task06_case_gif.py
scripts/analyze_task06_rollout.py
scripts/plot_task06_multiscenario_summary.py
configs/task06_static_ppo.json
configs/task06_dynamic_ppo.json
configs/task06_latent_dynamic_ppo.json
configs/task06_case_selection.json
configs/task06_training_budget.json
configs/task06_multiscenario_curriculum.json
```

## 10. Required reports

Add or update:

```text
docs/TASK_06_TRAINING_EXECUTION_REPORT.md
```

If full training is not completed, add:

```text
docs/TASK_06_BLOCKED_TRAINING_REPORT.md
```

The execution report must state, for each scenario group, whether full training completed, timesteps reached, checkpoint path, eval summary path, top-down case GIF/video paths, and whether the trained policy improved over random/untrained policy.

## 11. Tests

Add tests for:

```text
static/dynamic/latent scenario generation
dynamic obstacle motion over time
latent trigger before/after behavior
rollout metrics
case selector
training budget parsing and smoke_is_completion=false
top-down renderer schema and fallback behavior
config output path safety
NavRL adjustment document coverage
```

## 12. Completion criteria

TASK_06 is complete only if:

1. `pytest -q` passes.
2. Static, dynamic, and latent_dynamic scenarios can be generated.
3. Static, dynamic, and latent_dynamic have full training status or explicit blocked reports.
4. No 2k/4k/10k smoke run is marked complete.
5. Each scenario group has random policy eval and trained checkpoint eval when full training completed.
6. Each scenario group has success or best-non-success case selection.
7. Each scenario group has a representative failure case.
8. Each selected case has a top-down gym-pybullet GIF/video or explicit fallback summary.
9. Random-vs-trained metrics exist for each scenario group.
10. Poor results are explained using failure taxonomy and additional NavRL references.
11. No outputs, checkpoints, GIFs, videos, TensorBoard files, or wandb runs are committed.

## 13. Out of scope

TASK_06 does not produce final paper claims, does not add EGO baseline, does not claim NavRL reproduction, and does not use NavRL pretrained artifacts. It does, however, require paper-grade training infrastructure, multi-scenario case replay, and NavRL-guided iteration.