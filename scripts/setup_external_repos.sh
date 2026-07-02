#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DIR="${ROOT_DIR}/external"

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
}

mkdir -p "${EXTERNAL_DIR}"

clone_or_report "https://github.com/learnsyslab/gym-pybullet-drones.git" \
  "${EXTERNAL_DIR}/gym-pybullet-drones" "gym-pybullet-drones"

clone_or_report "https://github.com/Zhefan-Xu/NavRL.git" \
  "${EXTERNAL_DIR}/NavRL" "NavRL"

cat <<'EOF'

Environment setup:
  conda create -n pirl-navrl-drones python=3.10
  conda activate pirl-navrl-drones
  pip install -e external/gym-pybullet-drones
  pip install -e .

If the network is slow, retry with:
  GIT_CLONE_FLAGS="--depth 1" bash scripts/setup_external_repos.sh
EOF
