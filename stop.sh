#!/usr/bin/env bash
set -uo pipefail

# =============================================================================
# Stop everything start.sh started.
#
#   ./stop.sh              stop the API, the UI and the log monitor
#   ./stop.sh --ollama     also stop the Ollama server
#
# Ollama is left alone by default: it is commonly shared with other things on
# the machine, and killing it because you stopped this app would be surprising.
# =============================================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDDIR="${ROOT}/.pids"
APIPORT="${APIPORT:-8100}"
UIPORT="${UIPORT:-8054}"

color_echo() {
  local color="$1"; shift
  case "$color" in
    red)    echo -e "\033[1;31m$*\033[0m" ;;
    green)  echo -e "\033[1;32m$*\033[0m" ;;
    yellow) echo -e "\033[1;33m$*\033[0m" ;;
    blue)   echo -e "\033[1;34m$*\033[0m" ;;
    *)      echo "$*" ;;
  esac
}

STOP_OLLAMA=0
[[ "${1:-}" == "--ollama" ]] && STOP_OLLAMA=1

stop_pid_file() {
  local label="$1" file="$2" pid
  [[ -f "${file}" ]] || return 0
  pid="$(cat "${file}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    # Give it a second to close its sockets before insisting.
    for _ in 1 2 3; do
      kill -0 "${pid}" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
      color_echo yellow "  ${label} (pid ${pid}) force killed"
    else
      color_echo green "  ${label} (pid ${pid}) stopped"
    fi
  else
    color_echo yellow "  ${label} was not running"
  fi
  rm -f "${file}"
}

# Streamlit and uvicorn --reload both fork workers that do not die with the
# parent, so the recorded pid is not the whole story: sweep the ports too.
free_port() {
  local port="$1" pids pid
  pids=$(ss -ltnp 2>/dev/null | grep ":${port} " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
  [[ -z "${pids}" ]] && return 0
  for pid in ${pids}; do
    kill "${pid}" 2>/dev/null && color_echo green "  freed port ${port} (pid ${pid})" \
      || color_echo yellow "  ⚠ port ${port} held by pid ${pid}, could not free"
  done
}

color_echo blue "Stopping YES AI CAN..."
stop_pid_file "UI"          "${PIDDIR}/ui.pid"
stop_pid_file "API"         "${PIDDIR}/api.pid"
stop_pid_file "log monitor" "${PIDDIR}/logmonitor.pid"

free_port "${UIPORT}"
free_port "${APIPORT}"

if [[ "${STOP_OLLAMA}" -eq 1 ]]; then
  stop_pid_file "Ollama" "${PIDDIR}/ollama.pid"
  pkill -f "ollama serve" 2>/dev/null && color_echo green "  ollama serve stopped" || true
else
  pgrep -f "ollama serve" >/dev/null 2>&1 && \
    color_echo yellow "  Ollama left running (./stop.sh --ollama to stop it too)"
fi

sleep 1
REMAINING=$(ss -ltn 2>/dev/null | grep -cE ":(${APIPORT}|${UIPORT}) " || true)
if [[ "${REMAINING}" -eq 0 ]]; then
  color_echo green "✅ All stopped. Ports ${APIPORT} and ${UIPORT} are free."
else
  color_echo red "⚠ Something is still listening on ${APIPORT}/${UIPORT}:"
  ss -ltnp 2>/dev/null | grep -E ":(${APIPORT}|${UIPORT}) "
  exit 1
fi
