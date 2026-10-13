#!/usr/bin/env bash
#
# One-command deploy: pull the branch on a server, rebuild the image,
# recreate the container and wait until /api/health answers.
#
# Usage:
#   scripts/deploy.sh <host>
#   DEPLOY_HOST=<host> scripts/deploy.sh
#
# Environment:
#   DEPLOY_HOST    target host (same as the positional argument)
#   DEPLOY_DIR     remote checkout directory   (default: ~/downtify)
#   BRANCH         branch to fast-forward to    (default: feat/collections)
#   HEALTH_URL     health endpoint polled locally
#                  (default: http://<host>:8000/api/health)
#
# No secrets are ever passed on the command line: ssh uses its own config,
# so authentication is whatever your ~/.ssh/config and agent already hold.

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-~/downtify}"
BRANCH="${BRANCH:-feat/collections}"
SERVICE="downtify"
HEALTH_ATTEMPTS=30
HEALTH_INTERVAL=12
HEALTH_TIMEOUT=6
LOG_TAIL=20

log() {
	printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
	log "ERROR: $*"
	exit 1
}

usage() {
	cat <<USAGE
Usage: ${0##*/} <host>
       DEPLOY_HOST=<host> ${0##*/}

Deploys ${BRANCH} to <host>: stashes a local docker-compose.yml edit,
git pull --ff-only, docker compose build, docker compose up -d ${SERVICE},
then polls the health endpoint until it answers.

Environment:
  DEPLOY_HOST   target host, when not passed as the first argument
  DEPLOY_DIR    remote checkout directory (default: ~/downtify)
  BRANCH        branch to deploy          (default: ${BRANCH})
  HEALTH_URL    health endpoint polled from this machine
                (default: http://<host>:8000/api/health)
USAGE
}

expand_tilde() {
	case "$1" in
		'~') printf '%s\n' "$HOME" ;;
		'~/'*) printf '%s\n' "$HOME/${1#\~/}" ;;
		*) printf '%s\n' "$1" ;;
	esac
}

case "${1:-}" in
	-h | --help)
		usage
		exit 0
		;;
esac

host="${1:-${DEPLOY_HOST:-}}"
if [ -z "$host" ]; then
	printf '%s\n' "${0##*/}: no target host given." >&2
	printf '%s\n' '' >&2
	usage >&2
	exit 2
fi

remote_dir="$(expand_tilde "$DEPLOY_DIR")"
health_url="${HEALTH_URL:-http://$host:8000/api/health}"
ssh_opts=(-o BatchMode=yes -o ConnectTimeout=10)

log "deploying ${BRANCH} to ${host}:${remote_dir}"

status=0
ssh "${ssh_opts[@]}" "$host" bash -s -- \
	"$remote_dir" "$BRANCH" "$SERVICE" <<'REMOTE' || status=$?
set -euo pipefail

deploy_dir="$1"
branch="$2"
service="$3"

cd "$deploy_dir"

stashed=0
if [ -n "$(git status --porcelain -- docker-compose.yml)" ]; then
	echo "local docker-compose.yml edit detected, stashing it"
	git stash push -m compose-image -- docker-compose.yml
	stashed=1
fi

git pull --ff-only origin "$branch"

if [ "$stashed" -eq 1 ]; then
	if ! git stash pop; then
		echo "ERROR: 'git stash pop' conflicted with the newly pulled" >&2
		echo "ERROR: docker-compose.yml. Nothing was rebuilt, and the" >&2
		echo "ERROR: stash was KEPT, so the server-local image: override" >&2
		echo "ERROR: is still recoverable. Finish it by hand on the server:" >&2
		echo "ERROR:   cd $deploy_dir && git status" >&2
		echo "ERROR: keep the local image: line, 'git add" >&2
		echo "ERROR: docker-compose.yml', then 'git stash drop' and" >&2
		echo "ERROR: re-run this deploy." >&2
		exit 3
	fi
fi

docker compose build
docker compose up -d "$service"
REMOTE

if [ "$status" -ne 0 ]; then
	if [ "$status" -eq 3 ]; then
		die "remote deploy aborted: 'git stash pop' conflicted (exit 3); the tree on $host needs a manual fix"
	fi
	die "remote deploy failed on $host (ssh exit $status); the health check was not attempted"
fi

log "remote steps done, waiting for health: ${health_url}"
started="$(date +%s)"
attempt=1
while [ "$attempt" -le "$HEALTH_ATTEMPTS" ]; do
	if curl -sf -m "$HEALTH_TIMEOUT" "$health_url" 2>/dev/null |
		grep -q '"status"'; then
		elapsed=$(($(date +%s) - started))
		log "healthy after ${elapsed}s (${attempt} of ${HEALTH_ATTEMPTS} attempts)"
		exit 0
	fi
	log "not healthy yet (attempt ${attempt}/${HEALTH_ATTEMPTS}), retrying in ${HEALTH_INTERVAL}s"
	sleep "$HEALTH_INTERVAL"
	attempt=$((attempt + 1))
done

elapsed=$(($(date +%s) - started))
log "ERROR: ${health_url} did not report a healthy status after ${elapsed}s (${HEALTH_ATTEMPTS} attempts)"
log "last ${LOG_TAIL} lines of 'docker compose logs ${SERVICE}':"
ssh "${ssh_opts[@]}" "$host" \
	"cd '$remote_dir' && docker compose logs --tail ${LOG_TAIL} ${SERVICE}" ||
	log "WARNING: could not read container logs from $host"
exit 1