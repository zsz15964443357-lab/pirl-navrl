# Platform Decision: Phase 1

## Decision

Phase 1 uses **gym-pybullet-drones** as the primary lightweight UAV training platform.

NavRL is retained as a long-term reference for Isaac Sim, ROS, deployment, and full dynamic-navigation architecture. It is not a Phase 1 training dependency.

## Why not raw PyBullet

Raw PyBullet is a physics engine, not a complete UAV RL research platform. Starting directly from raw PyBullet would require building environment contracts, tasks, logging, training integration, and evaluation infrastructure from scratch. That would recreate the failure mode of the previous repository.

## Why gym-pybullet-drones

`gym-pybullet-drones` is selected because it already provides:

- PyBullet-based quadrotor simulation
- Gymnasium compatibility
- Stable-Baselines3 compatibility
- built-in PID and RL examples
- a route toward firmware/SITL-related integration
- a lighter setup than Isaac Sim

## Why not NavRL immediately

NavRL is closer to the desired long-term UAV dynamic-navigation system, but its training stack relies on Isaac Sim and heavier GPU infrastructure. Current Phase 1 work must avoid heavy hardware dependencies and focus on a local lightweight setup.

## Relationship to Safety-Gymnasium / OmniSafe

Safety-Gymnasium and OmniSafe remain useful as SafeRL benchmark references, but Phase 1 prioritizes UAV physics relevance over benchmark breadth.

## Phase 1 scope

Phase 1 does not attempt paper-grade results. It establishes:

- external repo setup
- local environment setup
- import checks
- built-in example checks
- a small PIRL-NavRL adapter/risk/shield demo around gym-pybullet-drones
