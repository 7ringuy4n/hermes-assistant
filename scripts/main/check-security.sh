#!/usr/bin/env bash
# Smoke-check Security / Monitor / OpenBao components (localhost).
# Feature toggles: active|inactive (legacy 1/0 accepted via _env_active).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=architect/backup-restore/lib/workers.sh
source "${ROOT}/architect/backup-restore/lib/workers.sh"
assistant_migrate_enable_active

fail=0
check() {
  local name="$1" url="$2"
  if curl -fsS -m 8 "$url" >/dev/null 2>&1; then
    echo "OK  ${name}  ${url}"
  else
    echo "FAIL ${name}  ${url}"
    fail=1
  fi
}

compose_service_running() {
  # Optional workers use compose-scoped names (assistant-zalo-api-1), not legacy zalo-api.
  local svc="$1" project="${COMPOSE_PROJECT_NAME:-assistant}"
  [[ -n "$(docker ps -q \
    --filter "label=com.docker.compose.service=${svc}" \
    --filter "label=com.docker.compose.project=${project}" 2>/dev/null)" ]] && return 0
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$svc" && return 0
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "${project}-${svc}-1" && return 0
  return 1
}

echo "WORKER_SECURITY=${WORKER_SECURITY:-inactive} WORKER_MONITOR=${WORKER_MONITOR:-inactive} ENABLE_OPENBAO=${ENABLE_OPENBAO:-inactive}"
check openbao   "http://127.0.0.1:${OPENBAO_PORT:-8200}/v1/sys/health"
if _env_active "${ENABLE_GRAFANA:-}"; then
  check grafana "http://127.0.0.1:${GRAFANA_HOST_PORT:-23000}/api/health"
  # Enabling the monitor must not leave Grafana on the insecure compose
  # fallback; verify the admin credential is real and the login works.
  gf_c="$(docker ps -q \
    --filter "label=com.docker.compose.service=grafana" \
    --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-assistant}" 2>/dev/null | head -1)"
  gf_pw=""
  [[ -n "$gf_c" ]] && gf_pw="$(docker exec "$gf_c" printenv GF_SECURITY_ADMIN_PASSWORD 2>/dev/null || true)"
  case "${gf_pw}" in
    ""|changeme-set-in-env)
      echo "FAIL grafana-admin  empty or insecure fallback password (set GRAFANA_ADMIN_PASSWORD / bash run.sh install grafana)"
      fail=1
      ;;
    *)
      if curl -fsS -m 8 -u "${GRAFANA_ADMIN_USER:-admin}:${gf_pw}" \
          "http://127.0.0.1:${GRAFANA_HOST_PORT:-23000}/api/user" >/dev/null 2>&1; then
        echo "OK  grafana-admin  authenticated"
      else
        echo "FAIL grafana-admin  admin login rejected"
        fail=1
      fi
      ;;
  esac
else
  echo "INFO grafana skipped (ENABLE_GRAFANA=inactive)"
fi
check security  "http://127.0.0.1:${SECURITY_PORT:-8093}/health"
check authz     "http://127.0.0.1:${AUTHZ_PORT:-8097}/health"
if _env_active "${ENABLE_ZALO:-}"; then
  if ! compose_service_running zalo-api; then
    echo "FAIL zalo-api  container missing (ENABLE_ZALO=active requires zalo-api compose service)"
    fail=1
  fi
  check zalo-api "http://127.0.0.1:${ZALO_API_PORT:-${ADMIN_API_PORT:-8100}}/health"
else
  echo "INFO zalo-api skipped (ENABLE_ZALO=inactive)"
fi
check siem      "http://127.0.0.1:${SIEM_PORT:-8105}/health"
check policy    "http://127.0.0.1:${POLICY_PORT:-8106}/health"

if _env_active "${ENABLE_ANTIVIRUS:-}"; then
  check av "http://127.0.0.1:${AV_GATEWAY_PORT:-8098}/health"
else
  echo "INFO antivirus disabled (ENABLE_ANTIVIRUS=inactive)"
fi
echo "INFO sandbox=${SECURITY_SANDBOX:-inactive} llm_judge=${SECURITY_LLM_JUDGE:-inactive} (defaults off; not a security boundary)"

if _env_active "${ENABLE_NOTIFY:-}"; then
  check notify "http://127.0.0.1:${NOTIFY_PORT:-8092}/health"
else
  echo "INFO notify disabled (ENABLE_NOTIFY=inactive)"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "Security/monitor smoke failed — check: bash run.sh ps"
  exit 1
fi
echo "OK: Security/monitor smoke passed"
