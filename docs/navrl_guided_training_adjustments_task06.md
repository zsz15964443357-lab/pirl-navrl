# TASK_06 NavRL-Guided Training Adjustments

TASK_06 uses NavRL as a close engineering reference for multi-scenario PPO stabilization. This document is the required adjustment log for every scenario, observation, reward, PPO, runner, action constraint, evaluation, and visualization change made during TASK_06.

This document is not a NavRL baseline report and does not claim reproduction of NavRL results. Do not import NavRL checkpoints, pretrained policies, paper metrics, or training results.

## Required Review Table

Every meaningful TASK_06 change must add or update a row here. A row must name a concrete NavRL file, module, config, script, or documented behavior. A generic reference such as `NavRL does this` is not enough.

| Date / Commit | Scenario Group | NavRL reference | Observed setting | PIRL-NavRL adaptation | Reason | Result / observation | Next change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-04 / local | static | `external/NavRL/quick-demos/env.py`, `generate_obstacles_grid`, `sample_free_start`, `sample_free_goal` | Bounded random start/goal, obstacle radius ranges, rejection sampling, and clearance checks. | Added `pirl_navrl/scenarios/dynamic_curriculum.py` and `static_obstacle_easy` / `static_obstacle_medium` in `configs/task06_multiscenario_curriculum.json`. | TASK_05 fixed/no-obstacle training did not produce useful behavior; static obstacles need controlled, repeatable cases near the start-goal path. | Static scenario generation is deterministic by seed and uses 1-5 small Crazyflie-scale sphere/cylinder obstacles. | Run smoke training, then inspect best non-success and failure traces before increasing training scale. |
| 2026-07-04 / local | dynamic | `external/NavRL/isaac-training/training/scripts/env.py`, dynamic obstacle block; `external/NavRL/isaac-training/training/cfg/train.yaml`, `env_dyn` | Dynamic obstacles have origin/goal/velocity state and configurable velocity ranges. | Added `dynamic_crossing_easy` with one linear crossing obstacle and current-state motion through existing `ObstacleConfig.position_at`. | TASK_06 needs a minimal moving obstacle case without implementing full NavRL dynamic obstacle stack or intent prediction. | Dynamic obstacle is observable through current position/clearance and helper features in `feature_scaling.py`; no future intent label is leaked. | Add policy-side dynamic feature integration after basic VecNormalize smoke is stable. |
| 2026-07-04 / local | latent_dynamic | `external/NavRL/isaac-training/training/scripts/env.py` dynamic obstacle motion state; PIRL project risk objective | NavRL exposes moving obstacle state, while PIRL needs hidden-risk/sudden-motion diagnostics. | Added `latent_dynamic_easy`: obstacle is stationary until `trigger_step`, then moves linearly across the route. | This creates a replayable sudden-motion failure mode without claiming full intent prediction. | Scenario config supports latent trigger via `ObstacleConfig.start_time`; failure classification can emit `latent_trigger_failure`. | Inspect late-reaction traces and decide whether additional history features are required. |
| 2026-07-04 / local | mixed_static_dynamic | `external/NavRL/isaac-training/training/scripts/env.py`, static terrain plus dynamic obstacle section | NavRL combines dense static terrain with dynamic obstacles in Isaac. | Added `mixed_static_dynamic_easy` with multiple static obstacles and one crossing dynamic obstacle. | Mixed eval is useful only after static/dynamic smoke paths exist separately. | Provided config and scenario generator; not used as a formal mixed baseline. | Use as diagnostic eval or smoke only until static/dynamic policies are interpretable. |
| 2026-07-04 / local | observation | `external/NavRL/quick-demos/agent.py`, `Agent.init_model`; `external/NavRL/quick-demos/ppo.py`, `PPO.__call__` | NavRL separates state, lidar, goal direction, and dynamic obstacle tensors. | Added `pirl_navrl/platforms/gym_pybullet_drones/feature_scaling.py` for scaled TASK_04 flat observations and nearest dynamic relative features. | Current gym-pybullet-drones adapter does not yet produce NavRL-style lidar tensors; scaling is the first stabilization step. | Scaling helper is tested independently and can be used by future env wrappers. | Integrate scaled observations into a dedicated Task06 env wrapper if PPO remains unstable. |
| 2026-07-04 / local | observation | `external/NavRL/quick-demos/agent.py`, `Agent.init_model`; `external/NavRL/isaac-training/training/scripts/env.py`, observation assembly | NavRL exposes goal-relative robot state and obstacle state to the policy rather than relying on raw simulator state. | Integrated scaling directly into `Task06CurriculumEnv`: 19 scaled TASK_04 features plus 6 nearest dynamic-obstacle relative features. | The earlier helper-only path did not guarantee the PPO policy actually consumed the NavRL-inspired dynamic features. | PPO training/eval now uses a 25-D observation; dynamic and latent eval traces include current obstacle positions, velocities, and relative features. | Add lidar/raycast-like obstacle sectors later if point-obstacle features remain too weak. |
| 2026-07-04 / local | reward | `external/NavRL/isaac-training/training/scripts/env.py`, `_compute_reward_and_done` | Reward combines progress, safety/clearance, smoothness, and terminal conditions. | Added `pirl_navrl/evaluation/reward_profiles.py` with `goal_only`, `static_avoidance`, `dynamic_avoidance`, and `latent_risk`. | TASK_05 reward was too weak for reliable goal-reaching; TASK_06 needs explicit profile names and dynamic-risk hooks. | Profiles wrap local tested TASK_04 reward and add optional dynamic/latent penalties. | Tune only after rollout metrics show which failure type dominates. |
| 2026-07-04 / local | reward | `external/NavRL/isaac-training/training/scripts/env.py`, `_compute_reward_and_done`; `external/NavRL/isaac-training/training/cfg/train.yaml`, reward coefficients | NavRL balances goal progress against collision, clearance, and action regularization. | Added goal-alignment reward, vertical-action penalty, stronger clearance margins, stronger collision penalty, and dynamic/latent risk terms. | Early 100k dynamic training moved toward the goal but collided too often, so safety terms needed more weight before reporting TASK_06. | Dynamic collision count dropped in the later 100k run, while static still shows unsafe goal-seeking behavior. | Static needs staged curriculum or stronger near-obstacle avoidance before it can be called solved. |
| 2026-07-04 / local | PPO / runner | `external/NavRL/isaac-training/training/cfg/ppo.yaml`, `train.yaml`, `training/scripts/train.py` | NavRL uses config-driven training, checkpointing, eval cadence, and logging. | Added TASK_06 config files, `pirl_navrl/training/vec_env.py`, and `pirl_navrl/training/task06_multiscenario.py`. | TASK_06 needs DummyVecEnv / VecNormalize hooks and separate static/dynamic/latent configs. | Configs now use 100k diagnostic PPO runs with ignored local outputs under `outputs/task06`. | Increase timesteps only with documented reason and intermediate eval. |
| 2026-07-04 / local | PPO / runner | `external/NavRL/isaac-training/training/cfg/train.yaml`, simulator step settings | NavRL keeps simulator/control timing explicit in config. | Aligned TASK_06 curriculum `dt` with the gym-pybullet-drones 48 Hz control step and increased scenario `max_steps`. | The previous short horizon made even a direct goal-seeking controller unable to reach the goal in easy scenes. | Static/dynamic/latent episodes now last long enough for a policy to show goal progress. | Later formal eval should freeze horizon and speed limits before comparing methods. |
| 2026-07-04 / local | PPO / runner | `external/NavRL/isaac-training/training/scripts/eval.py`, normalized eval setup | NavRL keeps training and eval wrappers consistent. | Checkpoint eval now loads the saved `vecnormalize.pkl` around a `DummyVecEnv` and sets `training=False`, `norm_reward=False`. | The trained PPO policy was trained on normalized observations; raw-observation eval was not a valid checkpoint test. | Random-vs-trained summaries now compare the checkpoint under the same observation normalization used during training. | Keep VecNormalize artifact with every local debug run; do not commit it. |
| 2026-07-04 / local | eval / case replay | `external/NavRL/quick-demos/simple-navigation.py`; `external/NavRL/isaac-training/training/scripts/eval.py` | NavRL separates evaluation/demo inspection from training. | Added rollout metrics, case selector, GIF/fallback renderer, and TASK_06 CLI scripts. | TASK_06 requires success/best-non-success and representative failure cases rather than a single aggregate metric. | Case summaries classify timeout/collision/near-miss/dynamic/latent failures; GIF renderer falls back to JSON if optional deps are missing. | Use selected cases to decide whether observation or reward is the next bottleneck. |
| 2026-07-04 / local | eval / case replay | `external/NavRL/quick-demos/simple-navigation.py`; `external/NavRL/isaac-training/training/scripts/eval.py` | NavRL-style inspection separates aggregate metrics from replayable cases. | Batch eval now writes random/trained summaries, `random_vs_trained_summary.json`, selected JSONL cases, and GIF/fallback files per scenario group. | TASK_06 needs evidence beyond a single rollout, while still avoiding formal success-rate reporting. | Static, dynamic, and latent_dynamic 100k runs all show lower trained mean final distance than random, but no true success case yet. | Treat current GIFs as diagnostic case replay; next tuning should target static collision and timeout-to-success conversion. |
| 2026-07-04 / local | observation / policy | `external/NavRL/isaac-training/training/scripts/env.py`, observation assembly; `external/NavRL/isaac-training/training/scripts/ppo.py`, `FeatureExtractor` | NavRL uses separate `state`, `lidar`, `direction`, and `dynamic_obstacle` inputs and a CNN/MLP fusion feature extractor. | Added `navrl_style_observation`, `Task06NavRLStyleEnv`, `NavRLStyleFeatureExtractor`, and `configs/task06_navrl_style_*_ppo.json` using SB3 `MultiInputPolicy`. | The flat 25-D PPO path was too weak and did not reflect NavRL's successful observation/policy structure closely enough. | Static 350k NavRL-style checkpoint reached 0/8 success, 1/8 collision, mean final distance 2.328 m; random reached 0/8 success, 0/8 collision, mean final distance 2.359 m. This is not a solved policy. | Replace approximate geometry scan with real PyBullet raycast lidar, add vectorized training scale, or run the original NavRL Isaac/TorchRL stack before claiming good training. |
| 2026-07-04 / local | PPO / config | `external/NavRL/isaac-training/training/cfg/ppo.yaml`, `train.yaml` | NavRL uses lr `5e-4`, gamma `0.99`, GAE lambda `0.95`, clip ratio `0.1`, entropy `1e-3`, 4 PPO epochs, and much larger training scale. | Added NavRL-style configs with `max_speed=2.0`, `learning_rate=5e-4`, `gamma=0.99`, `gae_lambda=0.95`, `clip_range=0.1`, `ent_coef=1e-3`, `n_epochs=4`, and 500k debug target timesteps. | This aligns local SB3 debug PPO with NavRL parameter scale while staying inside PyBullet/SB3 constraints. | CPU training was interrupted at 350k static checkpoint for diagnostic evaluation; the result showed only marginal final-distance improvement over random. | Do not scale to dynamic/latent full runs until the static scene has a meaningful success signal. |
| 2026-07-05 / local | observation / lidar | `external/NavRL/isaac-training/training/scripts/env.py`, lidar observation; `external/NavRL/isaac-training/training/cfg/drone.yaml`, lidar range/beam shape | NavRL uses a real lidar-style range tensor rather than obstacle-center bins. | Added PyBullet `rayTestBatch` lidar for live gym-pybullet-drones clients, keeping the `(1, 36, 4)` NavRL-style tensor and retaining scenario-geometry fallback only for offline/schema tests. | The previous geometry-only lidar did not give the policy true line-of-sight sensing and was a likely reason training did not improve. | Unit test verifies a DIRECT PyBullet sphere is detected by raycast lidar; live env smoke reports `task06_lidar_source=pybullet_raycast`. | Run longer static training before expanding dynamic/latent claims. |
| 2026-07-05 / local | PPO / runner | `external/NavRL/isaac-training/training/cfg/train.yaml`, parallel env and long training scale | NavRL trains at much larger scale than one local SB3 env. | Added `num_envs` support in TASK_06 config/runner and set NavRL-style configs to `num_envs=4`, `total_timesteps=1000000`, `max_timesteps=4000000`. | Single-env CPU PPO was too slow and under-sampled scenario seeds. | Two-env smoke verified Dict observations are batched and both envs use PyBullet raycast lidar. | Use 4-env local training as the next diagnostic run; do not report as baseline. |
| 2026-07-05 / local | curriculum | `external/NavRL/isaac-training/training/cfg/train.yaml`, obstacle-count and environment diversity; `training/scripts/env.py`, mixed static/dynamic world | NavRL exposes varied obstacle layouts rather than one fixed easy level. | Added `curriculum_levels` config support with per-episode level rotation. Static NavRL-style training rotates easy/medium; dynamic rotates dynamic crossing and mixed static-dynamic; latent remains latent easy. | The static 350k single-level run overfit to moving slowly and timing out rather than solving. | Config/schema tests enforce NavRL-style configs use >=4 envs and >=1M timesteps. | Add success-gated progression later if fixed rotation is too noisy. |
| 2026-07-05 / local | dynamic / latent_dynamic | `external/NavRL/isaac-training/training/cfg/train.yaml`, `env_dyn`; `external/NavRL/isaac-training/training/scripts/env.py`, dynamic obstacle state | NavRL separates dynamic obstacle configuration from static terrain density. | Corrected `dynamic_crossing_easy` and `latent_dynamic_easy` to use `static_obstacle_count=0`; kept mixed static + dynamic in `mixed_static_dynamic_easy`. | The previous easy dynamic scenes were confounded by a static obstacle, so poor results could not be attributed cleanly to moving-obstacle reasoning. | Dynamic/latent easy now isolate one moving or sudden-moving obstacle; tests enforce this split. | Keep mixed scenes for later stress testing after isolated dynamic/latent behavior is stable. |
| 2026-07-05 / local | horizon / curriculum | `external/NavRL/isaac-training/training/cfg/train.yaml`, `env.max_episode_length: 2200` | NavRL gives policies a much longer episode budget than the earlier local easy scenes. | Increased static/dynamic/latent easy `max_steps` to 1100 and rechecked dynamic with a 1100-step horizon. | The 800-step dynamic eval was horizon-limited; a policy could be moving correctly but time out before reaching the goal. | The same dynamic checkpoint improved to 10/16 success, 2/16 collision, and 4/16 timeout under the 1100-step diagnostic eval. | Freeze a final horizon before formal baseline work; do not mix horizon checks into paper metrics. |
| 2026-07-05 / local | reward / static | `external/NavRL/isaac-training/training/scripts/ppo.py`, `BetaActor`; `external/NavRL/isaac-training/training/cfg/ppo.yaml`, `action_limit` | NavRL uses bounded action distributions and explicit action limits. | Added `static_avoidance_navrl_speed_safety`, including a near-obstacle action penalty when clearance is below a threshold; used `log_std_init=-0.8` and kept `max_speed=1.4`. | Static failure traces showed action saturation near obstacles. Directly increasing collision/clearance penalties made training worse, so the targeted fix reduced unsafe speed near obstacle surfaces. | Static easy improved to 13/16 success, 3/16 collision, 0/16 timeout; mean action norm dropped to 0.676. This is better but not solved. | Consider a closer bounded-action actor or additional staged curriculum if static collisions remain. |
| 2026-07-05 / local | reward / dynamic | `external/NavRL/isaac-training/training/scripts/env.py`, progress and obstacle penalties | NavRL reward balances goal progress with safety and smoothness rather than optimizing only clearance. | Kept `dynamic_avoidance_reach` with altitude error penalty and isolated moving-obstacle scenes. | The dynamic bottleneck was scenario/horizon ambiguity more than a clear reward-weight failure. | Best diagnostic dynamic eval reached 10/16 success, 2/16 collision, 4/16 timeout with mean final distance 0.741 m. | Improve timeouts with staged dynamic curriculum before adding harder mixed scenes. |
| 2026-07-05 / local | reward / latent_dynamic | `external/NavRL/isaac-training/training/scripts/env.py`, dynamic obstacle state; PIRL hidden-risk objective | NavRL exposes current dynamic state; PIRL needs sudden-motion risk cases without leaking future labels. | Kept `latent_risk_reach` and the sudden-motion obstacle trigger while isolating the scene from static obstacles. | Latent failures were mostly timeouts after safe reactions, not collisions, so the next issue is completion efficiency. | Best diagnostic latent eval reached 10/16 success, 0/16 collision, 6/16 timeout with mean final distance 0.466 m. | Add history/risk features later only after confirming remaining failures are late-reaction, not speed/horizon artifacts. |
| 2026-07-05 / local | eval / visualization | `external/NavRL/isaac-training/training/scripts/eval.py`; `external/NavRL/quick-demos/simple-navigation.py` | NavRL keeps inspection artifacts separate from training outputs and formal metrics. | Copied current best success/failure GIFs into `outputs/task06_visual_review/current_best/` with a `manifest.json`. | Earlier GIF paths were scattered across run directories and hard to audit. | The review folder now contains static/dynamic/latent success and failure GIFs for quick local inspection. | Keep these artifacts ignored; do not commit GIFs or use them as formal benchmark evidence. |
| 2026-07-05 / local | static / dynamic / latent_dynamic | NavRL separates high-level navigation from low-level flight stabilization and increases difficulty progressively. | Strict recomputation caught a latent false success: traces with `min_clearance < collision_radius` are failures even if the rollout summary said success. Remaining failures were static near-boundary clearances and latent altitude drift, not reward-only problems. | Added strict metric recomputation, success requires no collision, added adapter altitude hold, simplified gate-easy scenes by offsetting static obstacles and using smaller/slower moving obstacles, and fixed case selection when all episodes succeed. | The current stage target is 100% success on three simple scene families before increasing obstacle count or complexity. | Gate-easy strict eval now reaches 16/16 success, 0/16 collision, 0/16 timeout for static, dynamic, and latent_dynamic. GIFs are grouped under `outputs/task06_visual_review/gate_easy_final/`. | Freeze this gate protocol for review, then increase difficulty gradually; do not treat the gate-easy result as a formal baseline. |

## Mandatory NavRL Re-check Rule

When training performs poorly, do not only change PPO hyperparameters. First inspect NavRL again and update the table above. The update must answer:

1. Which NavRL file/module/config/script was inspected?
2. What setting or structure looked relevant?
3. What was adapted into PIRL-NavRL?
4. Why was it adapted instead of copied wholesale?
5. Did the follow-up run improve the target metric or case replay?

## Minimum Coverage

The completed TASK_06 implementation must document concrete NavRL references for:

- static obstacle sampling and parameter ranges;
- dynamic obstacle motion patterns;
- latent, sudden-motion, or hidden-risk scenario analogs;
- observation design for robot state, goal, obstacle, and dynamic obstacle features;
- reward shaping for progress, collision, clearance, smoothness, and dynamic risk;
- action scaling, velocity constraints, safety margins, or gate-like control logic;
- PPO or runner settings such as rollout length, normalization, checkpointing, and eval cadence;
- evaluation and visualization conventions, especially case replay.

## Full Training Execution Log

For each scenario group, record the full training status here. A short smoke run is not enough.

| Scenario group | Mode | Timesteps reached | Required min timesteps | Status | Checkpoint | Eval summary | Notes |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| static | TODO | 0 | 100000 | TODO | TODO | TODO | TODO |
| dynamic | TODO | 0 | 150000 | TODO | TODO | TODO | TODO |
| latent_dynamic | TODO | 0 | 150000 | TODO | TODO | TODO | TODO |

Valid status values:

```text
completed_full_training
blocked
smoke_only_not_complete
```

If a scenario group is `blocked`, add or update `docs/TASK_06_BLOCKED_TRAINING_REPORT.md`.

## Top-Down Case Replay Notes

For each scenario group, record where TASK_06 outputs the following local artifacts under `outputs/task06/...`:

- random policy summary;
- trained policy summary;
- success case or best non-success case JSONL;
- representative failure case JSONL;
- top-down gym-pybullet GIF or video path;
- fallback summary path if GIF/video rendering failed;
- failure classification and next suggested fix.

These artifacts must remain local and must not be committed to git.

## Adoption Boundary

Allowed:

- reference NavRL module structure and parameter scale;
- adapt small helper patterns with attribution and tests;
- compare design intent with PIRL-NavRL implementation choices;
- use NavRL as guidance for scenario design, reward, observation, runner structure, and gate-like control ideas.

Forbidden:

- wholesale migration of NavRL training stack;
- using NavRL as a baseline;
- claiming NavRL reproduction;
- using NavRL checkpoints, pretrained policies, or published results;
- copying code without adaptation, testing, and license review.
