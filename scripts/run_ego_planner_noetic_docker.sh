#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EGO_DIR="${ROOT_DIR}/external/ego-planner"
IMAGE="${EGO_DOCKER_IMAGE:-osrf/ros:noetic-desktop-full}"
MODE="${1:-rviz}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_ego_planner_noetic_docker.sh [rviz|headless|build]

Modes:
  rviz      Run official EGO-Planner simple_run.launch with RViz through X11.
  headless  Run official EGO-Planner run_in_sim.launch without RViz.
  build     Install common Noetic dependencies inside a disposable container and catkin_make.

The host is Ubuntu 22.04, so this uses a ROS Noetic Ubuntu 20.04 Docker image
instead of installing ROS1 Noetic packages directly on the host.
EOF
}

if [[ "${MODE}" == "-h" || "${MODE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -d "${EGO_DIR}/.git" ]]; then
  echo "[error] Missing ${EGO_DIR}. Run:" >&2
  echo "        GIT_CLONE_FLAGS=\"--depth 1\" bash scripts/setup_external_repos.sh --include-ego" >&2
  exit 1
fi

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[error] docker is required for the Noetic sidecar on Ubuntu 22.04." >&2
    exit 1
  fi
}

build_ego() {
  require_docker
  docker run --rm \
    -v "${EGO_DIR}:/ego" \
    -w /ego \
    "${IMAGE}" \
    bash -lc '
      set -e
      apt-get update
      DEBIAN_FRONTEND=noninteractive apt-get install -y \
        libarmadillo-dev qtbase5-dev \
        ros-noetic-cmake-modules ros-noetic-pcl-ros ros-noetic-pcl-conversions \
        ros-noetic-cv-bridge ros-noetic-image-transport ros-noetic-tf \
        ros-noetic-nodelet ros-noetic-laser-geometry ros-noetic-dynamic-reconfigure
      source /opt/ros/noetic/setup.bash
      catkin_make -DCMAKE_BUILD_TYPE=Release
    '
}

run_launch() {
  local launch_file="$1"
  shift
  require_docker
  if [[ ! -f "${EGO_DIR}/devel/setup.bash" ]]; then
    echo "[info] EGO-Planner is not built yet; building now."
    build_ego
  fi
  docker run --rm \
    --net=host \
    "$@" \
    -v "${EGO_DIR}:/ego" \
    -w /ego \
    "${IMAGE}" \
    bash -lc "source /opt/ros/noetic/setup.bash; source /ego/devel/setup.bash; roslaunch ego_planner ${launch_file}"
}

case "${MODE}" in
  build)
    build_ego
    ;;
  headless)
    run_launch run_in_sim.launch
    ;;
  rviz)
    if [[ -z "${DISPLAY:-}" ]]; then
      echo "[error] DISPLAY is not set; use headless mode or run from a desktop session." >&2
      exit 1
    fi
    if command -v xhost >/dev/null 2>&1; then
      xhost +local:root >/dev/null
    fi
    run_launch simple_run.launch \
      -e "DISPLAY=${DISPLAY}" \
      -e QT_X11_NO_MITSHM=1 \
      -v /tmp/.X11-unix:/tmp/.X11-unix:rw
    ;;
  *)
    echo "[error] Unknown mode: ${MODE}" >&2
    usage >&2
    exit 2
    ;;
esac
