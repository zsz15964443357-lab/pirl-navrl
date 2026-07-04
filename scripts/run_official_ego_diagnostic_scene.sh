#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EGO_DIR="${ROOT_DIR}/external/ego-planner"
IMAGE="${EGO_DOCKER_IMAGE:-osrf/ros:noetic-desktop-full}"
SCENARIO="ego_static_obstacle_v0"
SEED="${EGO_DIAGNOSTIC_SEED:-127}"
MAP_POINTS="${EGO_MIRROR_MAP_POINTS:-20000}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_static_obstacle_v0
  bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_dynamic_obstacle_v0
  bash scripts/run_official_ego_diagnostic_scene.sh --scenario ego_sudden_motion_obstacle_v0

This is the TASK_02 main route. It runs official EGO planner/controller/
simulator nodes inside Docker Noetic with a PIRL-NavRL custom pointcloud scene
and opens a host PyBullet diagnostic mirror.

Notes:
  - All three scenarios publish custom obstacle pointclouds to official EGO.
  - PyBullet renders the same scene primitives for visual inspection.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario)
      SCENARIO="${2:?missing value for --scenario}"
      shift 2
      ;;
    --seed)
      SEED="${2:?missing value for --seed}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "${EGO_DIR}/.git" ]]; then
  echo "[error] Missing ${EGO_DIR}. Run setup_external_repos.sh --include-ego first." >&2
  exit 1
fi

if [[ ! -f "${EGO_DIR}/devel/setup.bash" ]]; then
  bash "${ROOT_DIR}/scripts/run_ego_planner_noetic_docker.sh" build
fi

eval "$(
  PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}" python3 - "${SCENARIO}" "${SEED}" <<'PY'
import json
import shlex
import sys

from pirl_navrl.scenarios.ego_official_diagnostic_scenarios import (
    make_ego_official_diagnostic_scenario,
)

scenario = make_ego_official_diagnostic_scenario(sys.argv[1], seed=int(sys.argv[2]))
metadata = scenario.to_trace_metadata()
items = {
    "SCENARIO_ID": metadata["scenario_id"],
    "OBSTACLE_MODE": metadata["obstacle_mode"],
    "DURATION": metadata["duration"],
    "START_X": metadata["start"][0],
    "START_Y": metadata["start"][1],
    "START_Z": metadata["start"][2],
    "GOAL_X": metadata["goal"][0],
    "GOAL_Y": metadata["goal"][1],
    "GOAL_Z": metadata["goal"][2],
    "MAP_SIZE_X": metadata["map_size"][0],
    "MAP_SIZE_Y": metadata["map_size"][1],
    "MAP_SIZE_Z": metadata["map_size"][2],
    "SCENARIO_NOTES": metadata["notes"],
    "SCENARIO_OBSTACLES_JSON": json.dumps(metadata["obstacles"], sort_keys=True),
}
for key, value in items.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

RESULTS_DIR="${ROOT_DIR}/results/official_ego_diagnostic/${SCENARIO_ID}"
TRACE_PATH="${RESULTS_DIR}/trace.jsonl"
ROS_LOG_PATH="${RESULTS_DIR}/official_ego_ros.log"
CONTAINER_RESULTS_DIR="/repo/results/official_ego_diagnostic/${SCENARIO_ID}"
CONTAINER_TRACE_PATH="${CONTAINER_RESULTS_DIR}/trace.jsonl"
CONTAINER_ROS_LOG_PATH="${CONTAINER_RESULTS_DIR}/official_ego_ros.log"

mkdir -p "${RESULTS_DIR}"
rm -f "${TRACE_PATH}" "${ROS_LOG_PATH}"

docker run --rm \
  --net=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "${ROOT_DIR}:/repo" \
  -v "${EGO_DIR}:/ego" \
  -w /repo \
  "${IMAGE}" \
  bash -lc "
    set -e
    mkdir -p '${CONTAINER_RESULTS_DIR}'
    source /opt/ros/noetic/setup.bash
    source /ego/devel/setup.bash
    roslaunch /repo/pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch \
      init_x:='${START_X}' \
      init_y:='${START_Y}' \
      init_z:='${START_Z}' \
      map_size_x:='${MAP_SIZE_X}' \
      map_size_y:='${MAP_SIZE_Y}' \
      map_size_z:='${MAP_SIZE_Z}' \
      > '${CONTAINER_ROS_LOG_PATH}' 2>&1 &
    launch_pid=\$!
    trap 'kill -INT \$launch_pid >/dev/null 2>&1 || true; wait \$launch_pid >/dev/null 2>&1 || true' EXIT
    sleep 8
    python3 /repo/scripts/mirror_official_ego_ros_trace.py \
      --output '${CONTAINER_TRACE_PATH}' \
      --duration '${DURATION}' \
      --goal-x '${GOAL_X}' \
      --goal-y '${GOAL_Y}' \
      --goal-z '${GOAL_Z}' \
      --map-topic /pirl_navrl/custom_scene_cloud \
      --map-points '${MAP_POINTS}' \
      --scenario-id '${SCENARIO_ID}' \
      --obstacle-mode '${OBSTACLE_MODE}' \
      --scenario-notes '${SCENARIO_NOTES}' \
      --scenario-obstacles-json '${SCENARIO_OBSTACLES_JSON}' \
      --source-launch 'pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch' \
      --publish-custom-map
  " &
docker_pid=$!

cleanup() {
  docker kill "${docker_pid}" >/dev/null 2>&1 || true
  wait "${docker_pid}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python3 "${ROOT_DIR}/scripts/view_official_ego_pybullet_mirror.py" --trace "${TRACE_PATH}"

wait "${docker_pid}" || true

echo "[ok] scenario: ${SCENARIO_ID}"
echo "[ok] trace: ${TRACE_PATH}"
echo "[ok] ros log: ${ROS_LOG_PATH}"
