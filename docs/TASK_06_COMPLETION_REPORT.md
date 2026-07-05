# TASK_06 Completion Report

## Scope

TASK_06 implements a NavRL-guided multi-scenario PPO diagnostic training path
with random-vs-trained evaluation and case replay. It is still not a formal
baseline, not a NavRL reproduction, not an EGO comparison, and not a paper
experiment. The numbers below are local debug observations only.

## Implemented

- Added seed-controlled static, dynamic, latent_dynamic, and mixed
  scenario generation in `pirl_navrl/scenarios/dynamic_curriculum.py`.
- Added TASK_06 config files under `configs/`, including curriculum,
  case selection, and separate static/dynamic/latent PPO configs.
- Added `Task06CurriculumEnv`, which runs on the existing
  `Task04GymPybulletDronesRLEnv` / gym-pybullet-drones physical backend.
- Added NavRL-inspired scaled observations:
  19 TASK_04 features plus 6 dynamic-relative features.
- Added a closer NavRL-style observation path with separate `state`, `lidar`,
  `direction`, and `dynamic_obstacle` tensors, plus an SB3
  `MultiInputPolicy` feature extractor inspired by NavRL's CNN/MLP fusion.
- Replaced the previous NavRL-style geometry-only lidar approximation with a
  live PyBullet `rayTestBatch` lidar path when a gym-pybullet-drones client is
  available; offline/schema helpers still fall back to scenario geometry.
- Added multi-env `DummyVecEnv` support through `num_envs` and multi-level
  curriculum rotation through `curriculum_levels`.
- Added reward profiles for static avoidance, dynamic avoidance, and latent
  dynamic risk in `pirl_navrl/evaluation/reward_profiles.py`.
- Added VecEnv / VecNormalize training and checkpoint evaluation support.
- Added random-vs-trained batch evaluation, JSONL rollout summaries, automatic
  case selection, and GIF/fallback case replay.
- Added scripts for training, evaluation, rollout analysis, case selection,
  summary plotting, and GIF rendering.

## Local Training Runs

Each run below used the debug PPO config with `total_timesteps=100000` and
8 local eval episodes for random and trained policies. SB3 on-policy rollout
collection may round internal collection to rollout boundaries, but the config
target is 100k timesteps.

| Scenario group | Curriculum level | Run directory | Random observation | Trained observation |
| --- | --- | --- | --- | --- |
| static | `static_obstacle_easy` | `outputs/task06/20260704_231154_static_static_obstacle_easy_seed0` | 0/8 success, 0/8 collision, mean final distance 2.447 m | 0/8 success, 5/8 collision, mean final distance 1.398 m |
| dynamic | `dynamic_crossing_easy` | `outputs/task06/20260704_230220_dynamic_dynamic_crossing_easy_seed0` | 0/8 success, 0/8 collision, mean final distance 2.981 m | 0/8 success, 1/8 collision, mean final distance 2.319 m |
| latent_dynamic | `latent_dynamic_easy` | `outputs/task06/20260704_230611_latent_dynamic_latent_dynamic_easy_seed0` | 0/8 success, 0/8 collision, mean final distance 3.011 m | 0/8 success, 0/8 collision, mean final distance 2.506 m |

Observed debug learning effect: all three trained checkpoints moved closer to
the goal than the random policy. This is not a solved policy: no true success
case was found in the 8-episode eval batches, and the static policy still trades
goal progress for unsafe collisions.

These early 100k runs are retained as historical diagnostics only. They are no
longer the current best TASK_06 policy observations.

## NavRL-Style Recheck

After reviewing NavRL more closely, TASK_06 added a second training path that is
closer to NavRL's successful design:

- structured observation: `state`, `lidar`, `direction`, `dynamic_obstacle`;
- CNN/MLP fusion feature extractor for SB3 `MultiInputPolicy`;
- PPO parameters aligned with NavRL scale where possible: `learning_rate=5e-4`,
  `gamma=0.99`, `gae_lambda=0.95`, `clip_range=0.1`, `ent_coef=1e-3`,
  `n_epochs=4`, and `max_speed=2.0`;
- local configs:
  `configs/task06_navrl_style_static_ppo.json`,
  `configs/task06_navrl_style_dynamic_ppo.json`, and
  `configs/task06_navrl_style_latent_dynamic_ppo.json`.

The local machine does not have NavRL's TorchRL/Isaac training stack available,
so this is an SB3/PyBullet adaptation rather than direct NavRL training.
The current live gym-pybullet-drones route now uses PyBullet raycast lidar.
This is closer to NavRL's lidar contract than the previous geometry fallback,
but it is still not Isaac RayCaster or a NavRL reproduction.

After the raycast/vectorized update, the NavRL-style configs are longer local
diagnostic configs: `num_envs=4`, `total_timesteps=1000000`, and
`max_timesteps=4000000`. Static training rotates over
`static_obstacle_easy` / `static_obstacle_medium`; dynamic training rotates over
`dynamic_crossing_easy` / `mixed_static_dynamic_easy`; latent remains on
`latent_dynamic_easy` until the easier static/dynamic policies show success.

Static NavRL-style training was interrupted after the 350k checkpoint for
diagnostic evaluation:

| Scenario group | Curriculum level | Checkpoint | Observation |
| --- | --- | --- | --- |
| static | `static_obstacle_easy` | `outputs/task06/20260704_234246_static_static_obstacle_easy_seed0/checkpoints/task06_navrl_style_static_ppo_debug_350000_steps.zip` | 0/8 success, 1/8 collision, mean final distance 2.328 m |
| static random | `static_obstacle_easy` | random policy | 0/8 success, 0/8 collision, mean final distance 2.359 m |

This is not an acceptable trained result. It shows that the interface and
NavRL-style training path run, but the policy has only marginally improved final
distance over random and still does not solve the easy static scenario.
Full dynamic and latent_dynamic NavRL-style runs should wait until static has a
clear success signal.

The raycast/vectorized/longer-curriculum update was smoke-tested after this
350k result. It established the live PyBullet raycast lidar and multi-env
training route, but the 350k checkpoint itself is still a failed static result.

## NavRL-Guided Diagnosis Update

After the 350k failure, the next changes were made by comparing failures with
NavRL design choices instead of blindly increasing reward weights:

- Dynamic and latent easy scenes were corrected to isolate one moving obstacle.
  They previously also included a static obstacle, which made the "easy dynamic"
  diagnosis ambiguous.
- Static, dynamic, and latent easy horizons were increased to 1100 steps. This
  follows NavRL's much longer episode budget in spirit and avoids labeling a
  slow but safe approach as a planner failure too early.
- Dynamic and latent rewards kept the reach-oriented profiles with an altitude
  error penalty. This improved goal approach without claiming intent prediction.
- Static failure traces showed high action saturation near obstacles. NavRL's
  actor uses bounded actions; the local SB3 Gaussian policy with clipping was
  often at the action limit. A targeted near-obstacle action penalty was added
  in `static_avoidance_navrl_speed_safety` to reduce speed near obstacle
  surfaces.

Current best local diagnostic observations:

| Scenario group | Run / eval directory | Config / profile | Diagnostic observation |
| --- | --- | --- | --- |
| static | `outputs/task06_gate_check/static_gate_easy_offset_v2_eval` | `static_avoidance_navrl_speed_safety`, gate-easy static scene | 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.348 m; mean min clearance 0.949 m; mean action norm 0.680 |
| dynamic | `outputs/task06_gate_check/dynamic_gate_easy_small_obstacle_final_eval` | `dynamic_avoidance_reach`, gate-easy dynamic scene | 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.348 m; mean min clearance 0.930 m; mean action norm 0.998 |
| latent_dynamic | `outputs/task06_gate_check/latent_gate_easy_small_obstacle_eval` | `latent_risk_reach`, gate-easy latent scene | 16/16 success, 0/16 collision, 0/16 timeout; mean final distance 0.349 m; mean min clearance 1.078 m; mean action norm 0.895 |

These are still diagnostic observations, not formal success rates. The gate-easy
scenes were simplified after failure analysis: static obstacles were offset away
from the path centerline, dynamic/latent obstacles were made smaller/slower, and
the gym-pybullet-drones adapter now uses altitude hold so the policy can focus on
horizontal navigation and obstacle reaction. This meets the current training gate
for simple scenes, but it is not a paper-level baseline result.

## Case Replay Artifacts

The current best run set contains true success and representative failure GIFs
for all three scenario groups. The GIFs are local outputs under ignored
`outputs/`; they are generated from JSONL traces recorded during
gym-pybullet-drones eval, not direct GUI screen recordings.

Representative current best trained GIFs:

```text
outputs/task06/20260705_133819_static_static_obstacle_easy_seed0/eval/trained/cases/static/success_case.gif
outputs/task06_horizon_check/dynamic_1100_eval_trained/cases/dynamic/success_case.gif
outputs/task06/20260705_124930_latent_dynamic_latent_dynamic_easy_seed0/eval/trained/cases/latent_dynamic/success_case.gif
```

The unified local visual review folder also contains copied GIFs for quick
inspection:

```text
outputs/task06_visual_review/current_best/static_success.gif
outputs/task06_visual_review/current_best/static_failure.gif
outputs/task06_visual_review/current_best/dynamic_success.gif
outputs/task06_visual_review/current_best/dynamic_failure.gif
outputs/task06_visual_review/current_best/latent_success.gif
outputs/task06_visual_review/current_best/latent_failure.gif
outputs/task06_visual_review/current_best/manifest.json
```

The current gate-easy review GIFs are grouped here:

```text
outputs/task06_visual_review/gate_easy_final/static_gate_easy_success.gif
outputs/task06_visual_review/gate_easy_final/dynamic_gate_easy_success.gif
outputs/task06_visual_review/gate_easy_final/latent_gate_easy_success.gif
```

## Verification

Local regression:

```text
pytest -q
66 passed, 12 warnings
```

Warnings are Gymnasium `Box` precision warnings and a local Matplotlib 3D
projection warning during GIF rendering.

## Current Boundary

TASK_06 is suitable as a diagnostic training and case-replay stage. It does not
yet provide a publishable policy or baseline. Before using it for paper results,
the next work should freeze the gate-easy protocol, add multi-seed evaluation,
increase obstacle count and scene complexity gradually, and compare against fixed
baselines under a frozen evaluation protocol.
