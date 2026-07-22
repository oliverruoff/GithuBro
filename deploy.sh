#!/usr/bin/env bash
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/oliverruoff/githubro.git}"
IMAGE_NAME="github-bro"
IMAGE_TAG="latest"
CONTAINER_NAME="githubro"

backup_state() {
  # Kept for deploy-script parity; githubro has no persistent runtime state.
  return 0
}

[[ -f .env ]] || { echo "Missing .env; copy .env.example and configure it." >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Run deploy.sh from a clone of ${REPO_URL}." >&2; exit 1; }
git pull --ff-only
docker build --build-arg "CACHEBUST=$(date +%s)" -t "${IMAGE_NAME}:${IMAGE_TAG}" .
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker run -d --name "${CONTAINER_NAME}" --restart unless-stopped --env-file .env "${IMAGE_NAME}:${IMAGE_TAG}"
echo "${CONTAINER_NAME} deployed from ${REPO_URL}"
