#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DIR="${ROOT_DIR}/external"
INCLUDE_EGO=0

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_external_repos.sh [--include-ego]

Default clones only Phase 1 dependencies:
  - gym-pybullet-drones
  - NavRL reference checkout

Use --include-ego for the Phase 2 EGO-Planner sidecar bridge spike.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-ego)
      INCLUDE_EGO=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

clone_or_report() {
  local url="$1"
  local dest="$2"
  local name="$3"

  if [[ -d "${dest}/.git" ]]; then
    if ! git -C "${dest}" rev-parse --verify HEAD >/dev/null 2>&1; then
      echo "[error] ${dest} looks like an incomplete git clone." >&2
      echo "        Remove it, then rerun this script." >&2
      return 1
    fi
    if [[ -n "$(git -C "${dest}" status --porcelain)" ]]; then
      echo "[error] ${dest} exists but has uncommitted changes or an incomplete checkout." >&2
      echo "        Inspect it with: git -C ${dest} status --short" >&2
      echo "        If this is a failed clone, remove it and rerun this script." >&2
      return 1
    fi
    echo "[ok] ${name} already exists at ${dest}"
    git -C "${dest}" remote -v | sed 's/^/[remote] /'
    git -C "${dest}" rev-parse --short HEAD | sed "s/^/[commit] ${name} /"
    return 0
  fi

  if [[ -e "${dest}" ]]; then
    echo "[error] ${dest} exists but is not a git repository." >&2
    echo "        Move it aside or remove it, then rerun this script." >&2
    return 1
  fi

  echo "[clone] ${url} -> ${dest}"
  if [[ -n "${GIT_CLONE_FLAGS:-}" ]]; then
    # shellcheck disable=SC2206
    local clone_flags=(${GIT_CLONE_FLAGS})
    git clone "${clone_flags[@]}" "${url}" "${dest}"
  else
    git clone "${url}" "${dest}"
  fi
  git -C "${dest}" rev-parse --short HEAD | sed "s/^/[commit] ${name} /"
}

mkdir -p "${EXTERNAL_DIR}"

clone_or_report "https://github.com/learnsyslab/gym-pybullet-drones.git" \
  "${EXTERNAL_DIR}/gym-pybullet-drones" "gym-pybullet-drones"

clone_or_report "https://github.com/Zhefan-Xu/NavRL.git" \
  "${EXTERNAL_DIR}/NavRL" "NavRL"

if [[ "${INCLUDE_EGO}" == "1" ]]; then
  clone_or_report "https://github.com/ZJU-FAST-Lab/ego-planner.git" \
    "${EXTERNAL_DIR}/ego-planner" "ego-planner"
fi

cat <<'EOF'

Environment setup:
  conda create -n pirl-navrl-drones python=3.10
  conda activate pirl-navrl-drones
  pip install -e external/gym-pybullet-drones
  pip install -e .

If the network is slow, retry with:
  GIT_CLONE_FLAGS="--depth 1" bash scripts/setup_external_repos.sh

For Phase 2 EGO-Planner sidecar preparation:
  bash scripts/setup_external_repos.sh --include-ego
EOF
