#!/usr/bin/env bash
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
#
# Start an example, check it, then stop it.
#
# Usage:
#   ./run_examples.sh                  # same as "service" with trpc_python.yaml
#   ./run_examples.sh service [conf]   # start trpc_main.py, run test_service_rpc.py, stop the server
#   ./run_examples.sh pull             # start pull_exporter.py, scrape /metrics, stop it
#   ./run_examples.sh modes            # "service" once per process/thread model config
#   ./run_examples.sh all              # pull, then modes
#   ./run_examples.sh list             # list example names and config files
#
# A conf path is a file name under this directory, or an absolute path.
# Greeter listens on 8000. The exporter listens on 8080.
#
# Environment:
#   PYTHON   interpreter to use (default: ../.venv/bin/python, then ../venv/bin/python, then python3)
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Package root first. A sibling checkout of the SDK (../trpc_sdk) is inserted
# ahead of site-packages so this example uses that source.
PYTHONPATH="${PKG_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
SDK_PARENT="$(cd "${PKG_DIR}/.." && pwd)"
if [[ -f "${SDK_PARENT}/trpc_sdk/__init__.py" ]]; then
  PYTHONPATH="${SDK_PARENT}:${PYTHONPATH}"
fi
export PYTHONPATH
export PYTHONUNBUFFERED=1

if [[ -n "${PYTHON:-}" ]]; then
  PY="${PYTHON}"
elif [[ -x "${PKG_DIR}/.venv/bin/python" ]]; then
  PY="${PKG_DIR}/.venv/bin/python"
elif [[ -x "${PKG_DIR}/venv/bin/python" ]]; then
  PY="${PKG_DIR}/venv/bin/python"
else
  PY="$(command -v python3)"
fi

SERVER_LOG="${SCRIPT_DIR}/.server_run.log"
HELLO_LOG="${SCRIPT_DIR}/hello.log"
SERVER_PID=""
STOP_PORTS=()
HOST="127.0.0.1"
RPC_PORT=8000
METRICS_PORT=8080
METRICS_URL="http://${HOST}:${METRICS_PORT}/metrics"
EXPORTER_MARK="prometheus exporter running at"

CONFIGS=(
  trpc_python.yaml
  trpc_python_merge_threads.yaml
  trpc_python_separate_thread.yaml
  trpc_python_separate.yaml
  trpc_python_merge_processes.yaml
)

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*" >&2; }
ok()  { printf '\033[1;32m[PASS]\033[0m %s\n' "$*" >&2; }
bad() { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; }

port_open() {
  local port="$1"
  "${PY}" -c "import socket; s=socket.create_connection(('${HOST}', ${port}), 0.2); s.close()" >/dev/null 2>&1
}

ports_busy() {
  local port
  for port in "$@"; do
    if port_open "${port}"; then
      bad "port ${port} is already in use; stop that process first"
      return 0
    fi
  done
  return 1
}

wait_ready() {
  local tries=60
  while (( tries-- > 0 )); do
    local port ready=1
    for port in "$@"; do
      port_open "${port}" || ready=0
    done
    [[ ${ready} -eq 1 ]] && return 0
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      return 1
    fi
    sleep 0.5
  done
  return 1
}

wait_ports_free() {
  local tries=20
  while (( tries-- > 0 )); do
    local port busy=0
    for port in "$@"; do
      port_open "${port}" && busy=1
    done
    [[ ${busy} -eq 0 ]] && return 0
    sleep 0.5
  done
  return 1
}

exporter_logged() {
  grep -q "${EXPORTER_MARK}" "${SERVER_LOG}" 2>/dev/null && return 0
  grep -q "${EXPORTER_MARK}" "${HELLO_LOG}" 2>/dev/null
}

wait_exporter() {
  local tries=20
  while (( tries-- > 0 )); do
    exporter_logged && return 0
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done
  exporter_logged
}

is_multi_process() {
  grep -E '^[[:space:]]*mode:[[:space:]]*multi_process([[:space:]]|#|$)' "$1" >/dev/null 2>&1
}

resolve_conf() {
  local conf="${1:-${SCRIPT_DIR}/trpc_python.yaml}"
  if [[ "${conf}" != /* ]]; then
    if [[ -f "${SCRIPT_DIR}/${conf}" ]]; then
      conf="${SCRIPT_DIR}/${conf}"
    fi
  fi
  if [[ ! -f "${conf}" ]]; then
    bad "config not found: ${conf}"
    return 1
  fi
  printf '%s\n' "${conf}"
}

fetch_metrics() {
  "${PY}" -c '
import sys
import urllib.request
url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=5) as rsp:
        if getattr(rsp, "status", 200) != 200:
            sys.exit(1)
        sys.stdout.write(rsp.read().decode())
except Exception as exc:
    sys.stderr.write("%s\n" % exc)
    sys.exit(1)
' "$1"
}

metric_samples_ok() {
  printf '%s\n' "$1" | "${PY}" -c '
import sys
needles = ("system_cpu_usage_percent ", "http_requests_total{", "http_response_time_seconds_count")
lines = [line for line in sys.stdin.read().splitlines() if line and not line.startswith("#")]
for needle in needles:
    if not any(line.startswith(needle) for line in lines):
        sys.exit(1)
'
}

rpc_metric_ok() {
  local need="$1"
  "${PY}" -c '
import sys
need = float(sys.argv[1])
total = 0.0
found = False
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("rpc_server_started_total{"):
        continue
    found = True
    total += float(line.rsplit(" ", 1)[-1])
if not found or total + 1e-9 < need:
    sys.stderr.write("rpc_server_started_total sum %s, want >= %s\n" % (total if found else "missing", int(need)))
    sys.exit(1)
' "${need}"
}

start_process() {
  local label="$1"
  shift
  if ports_busy "$@"; then
    return 1
  fi
  STOP_PORTS=("$@")
  : > "${SERVER_LOG}"
  : > "${HELLO_LOG}"
  if [[ "${label}" == pull ]]; then
    log "starting pull exporter"
    ( cd "${SCRIPT_DIR}" && exec "${PY}" pull_exporter.py ) >>"${SERVER_LOG}" 2>&1 &
  else
    log "starting server: ${label}"
    ( cd "${SCRIPT_DIR}" && exec "${PY}" trpc_main.py --conf "${label}" ) >>"${SERVER_LOG}" 2>&1 &
  fi
  SERVER_PID=$!
  if ! wait_ready "$@"; then
    bad "process did not start listening; last log lines:"
    tail -n 40 "${SERVER_LOG}" || true
    stop_server
    return 1
  fi
}

stop_server() {
  [[ -z "${SERVER_PID}" ]] && return 0
  pkill -TERM -P "${SERVER_PID}" 2>/dev/null || true
  kill -TERM "${SERVER_PID}" 2>/dev/null || true
  local _
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    kill -0 "${SERVER_PID}" 2>/dev/null || break
    sleep 0.5
  done
  pkill -KILL -P "${SERVER_PID}" 2>/dev/null || true
  kill -KILL "${SERVER_PID}" 2>/dev/null || true
  wait "${SERVER_PID}" 2>/dev/null || true
  SERVER_PID=""
  if ((${#STOP_PORTS[@]} > 0)); then
    local -a ports=("${STOP_PORTS[@]}")
    STOP_PORTS=()
    if ! wait_ports_free "${ports[@]}"; then
      bad "port still in use after stopping the server: ${ports[*]}"
      return 1
    fi
  fi
}

wait_metric_samples() {
  local tries=20 body=""
  while (( tries-- > 0 )); do
    body="$(fetch_metrics "${METRICS_URL}" 2>/dev/null || true)"
    if metric_samples_ok "${body}"; then
      printf '%s\n' "${body}"
      return 0
    fi
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done
  printf '%s\n' "${body}"
  return 1
}

run_service() {
  local conf
  conf="$(resolve_conf "${1:-}")" || return 1
  start_process "${conf}" "${RPC_PORT}" "${METRICS_PORT}" || return 1
  log "running example: service (test_service_rpc.py)"
  local rc=0 client_out="" calls=""
  client_out="$(cd "${SCRIPT_DIR}" && "${PY}" test_service_rpc.py 2>&1)" || rc=$?
  printf '%s\n' "${client_out}"
  if [[ ${rc} -eq 0 ]]; then
    calls="$(printf '%s\n' "${client_out}" | sed -n 's/^\([0-9][0-9]*\) SayHello calls succeeded$/\1/p' | head -n 1)"
    if [[ -z "${calls}" ]]; then
      bad "client output missing SayHello success line"
      rc=1
    elif ! is_multi_process "${conf}"; then
      if ! printf '%s\n' "${client_out}" | rpc_metric_ok "${calls}"; then
        bad "exporter missing rpc_server_started_total for ${calls} calls"
        rc=1
      fi
    fi
  fi
  if ! wait_exporter; then
    bad "server log missing '${EXPORTER_MARK}'"
    tail -n 40 "${SERVER_LOG}" || true
    rc=1
  fi
  stop_server || rc=1
  if [[ ${rc} -eq 0 ]]; then
    ok "service $(basename "${conf}")"
  else
    bad "service $(basename "${conf}") (exit ${rc}); server log: ${SERVER_LOG}"
  fi
  return ${rc}
}

run_pull() {
  local rc=0 body=""
  start_process pull "${METRICS_PORT}" || return 1
  log "scraping ${METRICS_URL}"
  body="$(wait_metric_samples)" || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    printf '%s\n' "${body}" | grep -E '^(http_requests_total\{|http_response_time_seconds_count|system_cpu_usage_percent )' || true
  else
    bad "exporter missing Counter, Gauge, or Summary samples"
    printf '%s\n' "${body}" | tail -n 40 >&2 || true
    tail -n 40 "${SERVER_LOG}" >&2 || true
  fi
  if ! wait_exporter; then
    bad "pull log missing '${EXPORTER_MARK}'"
    tail -n 40 "${SERVER_LOG}" || true
    rc=1
  fi
  stop_server || rc=1
  if [[ ${rc} -eq 0 ]]; then
    ok "pull"
  else
    bad "pull (exit ${rc}); server log: ${SERVER_LOG}"
  fi
  return ${rc}
}

run_modes() {
  local rc=0 conf
  for conf in "${CONFIGS[@]}"; do
    run_service "${conf}" || rc=1
  done
  return ${rc}
}

run_all() {
  local rc=0
  run_pull || rc=1
  run_modes || rc=1
  return ${rc}
}

trap 'stop_server' EXIT INT TERM

main() {
  case "${1:-service}" in
    list)
      echo "Available examples: service pull modes all"
      echo "Configs:"
      printf '  %s\n' "${CONFIGS[@]}"
      ;;
    service)
      run_service "${2:-}"
      ;;
    pull)
      run_pull
      ;;
    modes)
      run_modes
      ;;
    all)
      run_all
      ;;
    *)
      bad "unknown example: $1 (try: ./run_examples.sh list)"
      return 2
      ;;
  esac
}

main "$@"
