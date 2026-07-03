#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EGO_DIR="${ROOT_DIR}/external/ego-planner"
IMAGE="${EGO_DOCKER_IMAGE:-osrf/ros:noetic-desktop-full}"
RESULTS_DIR="${ROOT_DIR}/results/ego_official_mirror"
TRACE_PATH="${RESULTS_DIR}/live_trace.jsonl"
ROS_LOG_PATH="${RESULTS_DIR}/official_ego_ros.log"
CONTAINER_RESULTS_DIR="/repo/results/ego_official_mirror"
CONTAINER_TRACE_PATH="${CONTAINER_RESULTS_DIR}/live_trace.jsonl"
CONTAINER_ROS_LOG_PATH="${CONTAINER_RESULTS_DIR}/official_ego_ros.log"
DURATION="${EGO_MIRROR_DURATION:-90}"
GOAL_X="${EGO_MIRROR_GOAL_X:--8.0}"
GOAL_Y="${EGO_MIRROR_GOAL_Y:-10.0}"
GOAL_Z="${EGO_MIRROR_GOAL_Z:-1.0}"
MAP_POINTS="${EGO_MIRROR_MAP_POINTS:-20000}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_official_ego_pybullet_mirror.sh

Runs official EGO-Planner run_in_sim.launch in the Noetic Docker container and
opens a host PyBullet GUI that mirrors the official odometry, command, and map.

Optional environment variables:
  EGO_MIRROR_DURATION=90
  EGO_MIRROR_GOAL_X=-8.0
  EGO_MIRROR_GOAL_Y=10.0
  EGO_MIRROR_GOAL_Z=1.0
  EGO_MIRROR_MAP_POINTS=20000
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -d "${EGO_DIR}/.git" ]]; then
  echo "[error] Missing ${EGO_DIR}. Run setup_external_repos.sh --include-ego first." >&2
  exit 1
fi

if [[ ! -f "${EGO_DIR}/devel/setup.bash" ]]; then
  bash "${ROOT_DIR}/scripts/run_ego_planner_noetic_docker.sh" build
fi

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
    roslaunch ego_planner run_in_sim.launch > '${CONTAINER_ROS_LOG_PATH}' 2>&1 &
    launch_pid=\$!
    trap 'kill -INT \$launch_pid >/dev/null 2>&1 || true; wait \$launch_pid >/dev/null 2>&1 || true' EXIT
    sleep 8
    python3 /repo/scripts/mirror_official_ego_ros_trace.py \
      --output '${CONTAINER_TRACE_PATH}' \
      --duration '${DURATION}' \
      --goal-x '${GOAL_X}' \
      --goal-y '${GOAL_Y}' \
      --goal-z '${GOAL_Z}' \
      --map-points '${MAP_POINTS}'
  " &
docker_pid=$!

cleanup() {
  docker kill "${docker_pid}" >/dev/null 2>&1 || true
  wait "${docker_pid}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python3 "${ROOT_DIR}/scripts/view_official_ego_pybullet_mirror.py" --trace "${TRACE_PATH}"

wait "${docker_pid}" || true

echo "[ok] trace: ${TRACE_PATH}"
echo "[ok] ros log: ${ROS_LOG_PATH}"
