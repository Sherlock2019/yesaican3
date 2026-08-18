#!/usr/bin/env bash 
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"
LOGDIR="${ROOT}/.logs"
APIPORT="${APIPORT:-8100}"
UIPORT="${UIPORT:-8520}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma2:9b}"
export SANDBOX_CHATBOT_MODEL="${SANDBOX_CHATBOT_MODEL:-${OLLAMA_MODEL}}"

mkdir -p "$LOGDIR" \
         "${ROOT}/services/api/.runs" \
         "${ROOT}/agents/credit_appraisal/models/production" \
         "${ROOT}/.pids"

# ─────────────────────────────────────────────
# 🧹 PRE-CLEANUP — Kill old processes on used ports
# ─────────────────────────────────────────────
echo "🧹 Checking for existing processes on ports ${APIPORT} and ${UIPORT}..."

# Never use bare `sudo` here. It prompts for a password, and with no terminal
# attached (CI, nohup, an SSH command, a wrapper script) the prompt has nothing
# to read from, so the whole launch hangs forever at this line with no output.
# Our own services run as the current user, so a plain kill is enough; `sudo -n`
# is only a fallback and fails immediately rather than blocking.
free_port() {
  local port="$1" pids pid
  # `|| true` matters: the script runs under `set -euo pipefail`, and grep
  # exits 1 when a port is simply free — the common case. Without it, a clean
  # start aborts here with no message at all.
  pids=$(ss -ltnp 2>/dev/null | grep ":${port} " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
  if [ -z "${pids}" ]; then
    return 0
  fi
  for pid in ${pids}; do
    if kill "${pid}" 2>/dev/null; then
      echo "   freed port ${port} (pid ${pid})"
    elif sudo -n kill "${pid}" 2>/dev/null; then
      echo "   freed port ${port} (pid ${pid}, via sudo)"
    else
      echo "   ⚠ port ${port} is held by pid ${pid} and could not be freed"
    fi
  done
  sleep 1
}

free_port "${APIPORT}"
free_port "${UIPORT}"
echo "✅ Old processes cleaned up."

# ─────────────────────────────────────────────
# Timestamped logs
# ─────────────────────────────────────────────
TS=$(date +"%Y%m%d-%H%M%S")
API_LOG="${LOGDIR}/api_${TS}.log"
UI_LOG="${LOGDIR}/ui_${TS}.log"
COMBINED_LOG="${LOGDIR}/live_combined_${TS}.log"
OLLAMA_LOG="${LOGDIR}/ollama_${TS}.log"

# ─────────────────────────────────────────────
# Virtual environment
# ─────────────────────────────────────────────
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
source "${VENV}/bin/activate"

python -V
pip -V

# ─────────────────────────────────────────────
# Install deps
# ─────────────────────────────────────────────
python -m pip install -U pip wheel
pip install -r "${ROOT}/services/api/requirements.txt"
pip install -r "${ROOT}/services/ui/requirements.txt"

export PYTHONPATH="${ROOT}"

# ─────────────────────────────────────────────
# Color helper
# ─────────────────────────────────────────────
color_echo() {
  local color="$1"; shift
  local msg="$*"
  case "$color" in
    red) echo -e "\033[1;31m$msg\033[0m" ;;
    green) echo -e "\033[1;32m$msg\033[0m" ;;
    yellow) echo -e "\033[1;33m$msg\033[0m" ;;
    blue) echo -e "\033[1;34m$msg\033[0m" ;;
    *) echo "$msg" ;;
  esac
}

stop_if_running() {
  local label="$1"
  local pid_file="$2"
  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      color_echo yellow "Stopping existing ${label} (PID ${pid})..."
      kill "${pid}" 2>/dev/null || true
      sleep 1
      if kill -0 "${pid}" 2>/dev/null; then
        color_echo yellow "Force killing ${label} (PID ${pid})..."
        kill -9 "${pid}" 2>/dev/null || true
      fi
    fi
    rm -f "${pid_file}"
  fi
}

install_ollama_cli() {
  if command -v ollama >/dev/null 2>&1; then
    return
  fi
  color_echo yellow "Ollama CLI not detected. Installing..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://ollama.com/install.sh | sh
  else
    color_echo red "Neither curl nor wget available to install Ollama automatically."
    exit 1
  fi
  if ! command -v ollama >/dev/null 2>&1; then
    color_echo red "Ollama installation failed; install manually from https://ollama.com/download"
    exit 1
  fi
  color_echo green "Ollama CLI installed."
}

# ─────────────────────────────────────────────
# Ollama LLM backend
# ─────────────────────────────────────────────
ensure_ollama() {
  install_ollama_cli

  stop_if_running "Ollama" "${ROOT}/.pids/ollama.pid"
  if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
    color_echo blue "Starting Ollama server..."
    nohup ollama serve > "${OLLAMA_LOG}" 2>&1 &
    echo $! > "${ROOT}/.pids/ollama.pid"
    sleep 2
  else
    color_echo yellow "Ollama server already running."
  fi

  color_echo blue "Ensuring model '${OLLAMA_MODEL}' is available..."
  if ! ollama list | grep -q "${OLLAMA_MODEL}"; then
    ollama pull "${OLLAMA_MODEL}"
  fi

  color_echo blue "Checking Ollama endpoint at ${OLLAMA_HOST}..."
  for i in {1..10}; do
    if curl -s "${OLLAMA_HOST}/api/tags" >/dev/null; then
      break
    fi
    color_echo yellow "Waiting for Ollama to accept connections (attempt ${i}/10)..."
    sleep 2
  done
  if ! curl -s "${OLLAMA_HOST}/api/tags" >/dev/null; then
    color_echo red "❌ Ollama endpoint ${OLLAMA_HOST} is unreachable. Check ${OLLAMA_LOG}."
    exit 1
  fi

  color_echo blue "Warming model '${OLLAMA_MODEL}'..."
  if ! curl -s -X POST "${OLLAMA_HOST}/api/chat" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${OLLAMA_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"warm up\"}],\"stream\":false}" \
    >/dev/null; then
    color_echo yellow "Could not warm model automatically; it will load on first request."
  fi

  color_echo green "✅ Ollama ready (logs: ${OLLAMA_LOG})"
}

# Ensure Ollama backend (needs functions defined)
ensure_ollama

# ─────────────────────────────────────────────
# Start API
# ─────────────────────────────────────────────

stop_if_running "API" "${ROOT}/.pids/api.pid"
nohup "${VENV}/bin/uvicorn" services.api.main:app \
  --host 0.0.0.0 --port "${APIPORT}" --reload \
  > "${API_LOG}" 2>&1 &
echo $! > "${ROOT}/.pids/api.pid"
color_echo green "✅ API started (PID=$(cat "${ROOT}/.pids/api.pid")) | log: ${API_LOG}"

# ─────────────────────────────────────────────
# Start UI (Streamlit)
# ─────────────────────────────────────────────
stop_if_running "UI" "${ROOT}/.pids/ui.pid"
color_echo blue "Starting Streamlit UI..."
cd "${ROOT}/services/ui"
nohup "${VENV}/bin/streamlit" run "app.py" \
  --server.port "${UIPORT}" --server.address 0.0.0.0 \
  --server.fileWatcherType none \
  > "${UI_LOG}" 2>&1 &
echo $! > "${ROOT}/.pids/ui.pid"
cd "${ROOT}"
color_echo green "✅ UI started (PID=$(cat "${ROOT}/.pids/ui.pid")) | log: ${UI_LOG}"

# ─────────────────────────────────────────────
# Info
# ─────────────────────────────────────────────
echo "----------------------------------------------------"
color_echo blue "🎯 All services running!"
color_echo blue "📘 Swagger: http://localhost:${APIPORT}/docs"
color_echo blue "🌐 Web UI:  http://localhost:${UIPORT}"
color_echo blue "📂 Logs:    ${LOGDIR}"
echo "----------------------------------------------------"

# ─────────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────────
color_echo blue "🔎 Verifying service health..."

# Poll rather than checking once: uvicorn --reload and Streamlit both take a
# few seconds to bind, so a single immediate curl reports a healthy service as
# failed (status 000) and sends people to read a log with nothing wrong in it.
wait_for_http() {
  local url="$1" tries="${2:-20}" status=""
  for ((i = 0; i < tries; i++)); do
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "${url}" || true)
    [[ "${status}" == "200" ]] && { echo "200"; return 0; }
    sleep 1
  done
  echo "${status:-000}"
  return 1
}

# The API serves /health (services/api/main.py). The old check hit /v1/health,
# which has never existed, so this step always reported failure.
API_STATUS=$(wait_for_http "http://localhost:${APIPORT}/health" 20)
if [[ "${API_STATUS}" == "200" ]]; then
  color_echo green "API OK (HTTP 200) → http://localhost:${APIPORT}  (docs: http://localhost:${APIPORT}/docs)"
else
  color_echo red "API health check failed (status=${API_STATUS:-unreachable}) — check ${API_LOG}"
fi

# ─────────────────────────────────────────────
# Open the UI in a browser
# ─────────────────────────────────────────────
# Only called once the UI answers 200 — opening earlier lands on a connection
# error and people assume the launch failed. Every branch is `|| true`: a
# headless box has no browser, and failing to open one is not a failed start.
# Set NO_BROWSER=1 to skip (CI, SSH, a server you only want the ports on).
open_browser() {
  local url="$1"

  if [[ -n "${NO_BROWSER:-}" ]]; then
    color_echo yellow "↷ NO_BROWSER set — not opening ${url}"
    return 0
  fi

  # wslview first: on WSL, xdg-open exists but hands the URL to a Linux
  # browser that usually is not installed, so it fails silently and nothing
  # appears. wslview goes to the Windows default browser instead.
  if command -v wslview >/dev/null 2>&1; then
    wslview "${url}" >/dev/null 2>&1 || true
  elif grep -qi microsoft /proc/version 2>/dev/null && command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "Start-Process '${url}'" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${url}" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "${url}" >/dev/null 2>&1 || true
  else
    color_echo yellow "↷ No browser opener found — open ${url} yourself"
    return 0
  fi

  color_echo green "🌐 Opened ${url} in your browser"
}

UI_STATUS=$(wait_for_http "http://localhost:${UIPORT}" 30)
if [[ "${UI_STATUS}" == "200" ]]; then
  color_echo green "UI OK (HTTP 200) → http://localhost:${UIPORT}"
  open_browser "http://localhost:${UIPORT}"
else
  color_echo red "UI check returned ${UI_STATUS:-unreachable} — check ${UI_LOG}"
  color_echo yellow "   If it says 'failed to run command .../streamlit', the venv is missing UI"
  color_echo yellow "   dependencies. Install them with:"
  color_echo yellow "   ${VENV}/bin/pip install -r ${ROOT}/services/ui/requirements.txt"
fi

# ─────────────────────────────────────────────
# Combined Log Monitor
# ─────────────────────────────────────────────
color_echo blue "🧩 Starting live log monitor..."
nohup bash -c "tail -n 0 -F '${API_LOG}' '${UI_LOG}' | tee -a '${COMBINED_LOG}'" >/dev/null 2>&1 &
LOG_MONITOR_PID=$!
echo $LOG_MONITOR_PID > "${ROOT}/.pids/logmonitor.pid"
color_echo green "✅ Live log monitor running (PID=${LOG_MONITOR_PID})"
color_echo blue "📄 Combined live output → ${COMBINED_LOG}"

# Wait until combined log exists
sleep 1
touch "${COMBINED_LOG}"

# ─────────────────────────────────────────────
# Live Error View
# ─────────────────────────────────────────────
color_echo yellow "👁  Real-time ERROR view (press Ctrl+C to exit)..."
tail -n 20 -f "${COMBINED_LOG}" | grep --line-buffered -E --color=always "ERROR|Exception|Traceback|CRITICAL" || true
