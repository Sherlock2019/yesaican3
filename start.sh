#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# YES AI CAN — Community LAB launcher
#
# Runs the same on a laptop and on a public host (EC2, a droplet, a VM).
# The difference is detected, not configured: on a desktop it opens a browser
# and binds for local use; on a headless box it skips the browser, works out the
# host's public address, and prints the URL you can actually reach it on.
#
# The services run in the background and the script returns, so it is safe to
# close the terminal or drop the SSH session. Use ./stop.sh to shut them down.
#
#   ./start.sh                     laptop: local, opens a browser
#   PUBLIC_HOST=1.2.3.4 ./start.sh public host, explicit address
#   PROD=1 ./start.sh              no --reload, no file watcher
#   FOLLOW=1 ./start.sh            stay attached and watch the error stream
#
# Everything below is overridable from the environment:
#
#   APIPORT=8100  UIPORT=8054
#   PUBLIC_HOST=<ip|dns>     the address people will type; auto-detected on EC2
#   BIND_ADDR=0.0.0.0        set to 127.0.0.1 to refuse remote connections
#   BASE_URL_PATH=lab        when behind a reverse proxy at /lab
#   WITH_OLLAMA=0|1          0 skips it entirely, 1 installs and pulls
#   OLLAMA_MODEL=gemma2:9b
#   NO_BROWSER=1             never open a browser
#   SKIP_INSTALL=1           skip pip install (fast restarts)
#   PROD=1                   production: no reload, no watcher
#   FOLLOW=1                 tail the logs instead of returning
# =============================================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"
LOGDIR="${ROOT}/.logs"
APIPORT="${APIPORT:-8100}"
UIPORT="${UIPORT:-8054}"
BIND_ADDR="${BIND_ADDR:-0.0.0.0}"
BASE_URL_PATH="${BASE_URL_PATH:-}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma2:9b}"
export SANDBOX_CHATBOT_MODEL="${SANDBOX_CHATBOT_MODEL:-${OLLAMA_MODEL}}"

mkdir -p "$LOGDIR" \
         "${ROOT}/services/api/.runs" \
         "${ROOT}/agents/credit_appraisal/models/production" \
         "${ROOT}/.pids"

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

# ─────────────────────────────────────────────
# Where is this running, and what address will people type?
# ─────────────────────────────────────────────
# A desktop wants a browser opened at localhost. A server wants neither — it
# wants to be told the address that actually resolves from outside. Guessing
# wrong in either direction is what makes a launcher annoying, so detect it.
is_headless() {
  [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]] && return 0
  grep -qi microsoft /proc/version 2>/dev/null && return 1   # WSL has a browser
  [[ "$(uname -s)" == "Darwin" ]] && return 1
  [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]] && return 0
  return 1
}

# EC2 instance metadata, IMDSv2 first. Every call is capped at one second so a
# machine that is not on EC2 does not stall the launch waiting for a link-local
# address that will never answer.
detect_public_host() {
  local token ip
  token=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
            -H "X-aws-ec2-metadata-token-ttl-seconds: 60" \
            --max-time 1 2>/dev/null || true)
  if [[ -n "${token}" ]]; then
    ip=$(curl -s -H "X-aws-ec2-metadata-token: ${token}" \
           "http://169.254.169.254/latest/meta-data/public-ipv4" \
           --max-time 1 2>/dev/null || true)
    [[ -n "${ip}" ]] && { echo "${ip}"; return 0; }
  fi
  # IMDSv1, for older instances that still allow it
  ip=$(curl -s "http://169.254.169.254/latest/meta-data/public-ipv4" \
         --max-time 1 2>/dev/null || true)
  [[ -n "${ip}" ]] && { echo "${ip}"; return 0; }
  return 1
}

HEADLESS=0
is_headless && HEADLESS=1

if [[ -z "${PUBLIC_HOST:-}" ]]; then
  if PUBLIC_HOST=$(detect_public_host); then
    color_echo blue "☁  EC2 detected — public address ${PUBLIC_HOST}"
  else
    PUBLIC_HOST="localhost"
  fi
fi
UI_URL="http://${PUBLIC_HOST}:${UIPORT}${BASE_URL_PATH:+/${BASE_URL_PATH}}"
API_URL="http://${PUBLIC_HOST}:${APIPORT}"

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
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

python -V
pip -V

# ─────────────────────────────────────────────
# Install deps
# ─────────────────────────────────────────────
if [[ -n "${SKIP_INSTALL:-}" ]]; then
  color_echo yellow "↷ SKIP_INSTALL set — not touching dependencies"
else
  python -m pip install -U pip wheel
  pip install -r "${ROOT}/services/api/requirements.txt"
  pip install -r "${ROOT}/services/ui/requirements.txt"
fi

export PYTHONPATH="${ROOT}"

# ─────────────────────────────────────────────
# Streamlit config for remote access
# ─────────────────────────────────────────────
# Three things break Streamlit on a public host, and all three are silent:
#
#  1. Without headless mode the first run prints an interactive "enter your
#     email" prompt and waits. Under nohup that blocks forever with no output.
#  2. Streamlit builds its websocket origin from browser.serverAddress. Left at
#     the default, a browser on a public IP is rejected by the XSRF check and
#     the page loads but never connects — the spinner just spins.
#  3. Usage stats phone home. Off by default here.
#
# XSRF protection stays ON. CORS goes off because Streamlit refuses to run with
# both enabled and warns; XSRF is the one that actually protects the session.
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

STREAMLIT_ARGS=(
  --server.port "${UIPORT}"
  --server.address "${BIND_ADDR}"
  --server.headless true
  --server.enableCORS false
  --server.enableXsrfProtection true
  --browser.serverAddress "${PUBLIC_HOST}"
  --browser.serverPort "${UIPORT}"
)
[[ -n "${BASE_URL_PATH}" ]] && STREAMLIT_ARGS+=(--server.baseUrlPath "${BASE_URL_PATH}")

# The file watcher costs CPU and, on a server with the repo on a network mount,
# can restart the app under load. Off in production.
if [[ -n "${PROD:-}" ]]; then
  STREAMLIT_ARGS+=(--server.fileWatcherType none --server.runOnSave false)
else
  STREAMLIT_ARGS+=(--server.fileWatcherType none)
fi

# ─────────────────────────────────────────────
# Warn before exposing an app that has no login
# ─────────────────────────────────────────────
# Said plainly rather than buried: this app has no authentication of its own.
# Binding it to a public interface makes every painpoint, name and cure readable
# by anyone who finds the port.
if [[ "${BIND_ADDR}" == "0.0.0.0" && "${PUBLIC_HOST}" != "localhost" ]]; then
  color_echo red "────────────────────────────────────────────────────────────"
  color_echo red "⚠  This app has NO built-in authentication."
  color_echo red "   It is about to listen on ${BIND_ADDR}:${UIPORT}, reachable at"
  color_echo red "   ${UI_URL}"
  color_echo red ""
  color_echo red "   Before leaving it up, do one of:"
  color_echo red "     • restrict the security group to your own IP"
  color_echo red "     • put it behind a reverse proxy that authenticates"
  color_echo red "     • run with BIND_ADDR=127.0.0.1 and reach it over an SSH tunnel:"
  color_echo red "         ssh -L ${UIPORT}:localhost:${UIPORT} user@${PUBLIC_HOST}"
  color_echo red "────────────────────────────────────────────────────────────"
fi

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
    return 0
  fi
  color_echo yellow "Ollama CLI not detected. Installing..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh || return 1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://ollama.com/install.sh | sh || return 1
  else
    color_echo red "Neither curl nor wget available to install Ollama automatically."
    return 1
  fi
  command -v ollama >/dev/null 2>&1
}

# ─────────────────────────────────────────────
# Ollama LLM backend — optional
# ─────────────────────────────────────────────
# Best-effort, and never fatal. The app uses a model in exactly one place (the
# AI baseline on a submitted painpoint) and degrades cleanly without it; every
# score, match and dashboard figure is computed in Python. Hard-failing the
# launch over a 5 GB model pull would strand a fresh EC2 box for a feature most
# of the app does not use.
#
#   WITH_OLLAMA=0  skip entirely
#   WITH_OLLAMA=1  install and pull even if absent, and complain loudly on failure
ensure_ollama() {
  if [[ "${WITH_OLLAMA:-auto}" == "0" ]]; then
    color_echo yellow "↷ WITH_OLLAMA=0 — skipping the model backend"
    color_echo yellow "   The AI baseline on new painpoints will be blank; nothing else changes."
    return 0
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    if [[ "${WITH_OLLAMA:-auto}" != "1" ]]; then
      color_echo yellow "↷ Ollama not installed — skipping (set WITH_OLLAMA=1 to install it)"
      color_echo yellow "   The AI baseline will be blank; scoring and matching are unaffected."
      return 0
    fi
    if ! install_ollama_cli; then
      color_echo red "Ollama install failed — continuing without it."
      return 0
    fi
    color_echo green "Ollama CLI installed."
  fi

  if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
    color_echo blue "Starting Ollama server..."
    nohup ollama serve > "${OLLAMA_LOG}" 2>&1 &
    echo $! > "${ROOT}/.pids/ollama.pid"
    sleep 2
  else
    color_echo yellow "Ollama server already running."
  fi

  color_echo blue "Checking Ollama endpoint at ${OLLAMA_HOST}..."
  local up=0 i
  for i in {1..10}; do
    if curl -s --max-time 2 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      up=1; break
    fi
    sleep 2
  done
  if [[ "${up}" -ne 1 ]]; then
    color_echo yellow "⚠ Ollama endpoint ${OLLAMA_HOST} unreachable — continuing without it."
    color_echo yellow "   Log: ${OLLAMA_LOG}"
    return 0
  fi

  if ! ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL%%:*}"; then
    if [[ "${WITH_OLLAMA:-auto}" == "1" ]]; then
      color_echo blue "Pulling '${OLLAMA_MODEL}' (this is a large download)..."
      ollama pull "${OLLAMA_MODEL}" || color_echo yellow "⚠ Pull failed — continuing."
    else
      color_echo yellow "↷ Model '${OLLAMA_MODEL}' not present — not pulling automatically."
      color_echo yellow "   Run: ollama pull ${OLLAMA_MODEL}   (or set WITH_OLLAMA=1)"
      return 0
    fi
  fi

  color_echo blue "Warming '${OLLAMA_MODEL}'..."
  curl -s --max-time 60 -X POST "${OLLAMA_HOST}/api/chat" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${OLLAMA_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"warm up\"}],\"stream\":false}" \
    >/dev/null 2>&1 || color_echo yellow "Could not warm the model; it will load on first request."

  color_echo green "✅ Ollama ready (logs: ${OLLAMA_LOG})"
}

ensure_ollama

# ─────────────────────────────────────────────
# Start API
# ─────────────────────────────────────────────
stop_if_running "API" "${ROOT}/.pids/api.pid"
UVICORN_ARGS=(services.api.main:app --host "${BIND_ADDR}" --port "${APIPORT}")
# --reload watches the tree and restarts on every write. That is right on a
# laptop and wrong on a server, where it burns CPU and can restart mid-request.
if [[ -z "${PROD:-}" ]]; then
  UVICORN_ARGS+=(--reload)
else
  UVICORN_ARGS+=(--workers "${API_WORKERS:-2}")
fi
nohup "${VENV}/bin/uvicorn" "${UVICORN_ARGS[@]}" > "${API_LOG}" 2>&1 &
echo $! > "${ROOT}/.pids/api.pid"
color_echo green "✅ API started (PID=$(cat "${ROOT}/.pids/api.pid")) | log: ${API_LOG}"

# ─────────────────────────────────────────────
# Start UI (Streamlit)
# ─────────────────────────────────────────────
stop_if_running "UI" "${ROOT}/.pids/ui.pid"
color_echo blue "Starting Streamlit UI..."
cd "${ROOT}/services/ui"
nohup "${VENV}/bin/streamlit" run "app.py" "${STREAMLIT_ARGS[@]}" > "${UI_LOG}" 2>&1 &
echo $! > "${ROOT}/.pids/ui.pid"
cd "${ROOT}"
color_echo green "✅ UI started (PID=$(cat "${ROOT}/.pids/ui.pid")) | log: ${UI_LOG}"

# ─────────────────────────────────────────────
# Info
# ─────────────────────────────────────────────
echo "----------------------------------------------------"
color_echo blue "🎯 All services running!"
color_echo blue "🌐 Web UI:  ${UI_URL}"
color_echo blue "📘 Swagger: ${API_URL}/docs"
color_echo blue "📂 Logs:    ${LOGDIR}"
[[ "${PUBLIC_HOST}" != "localhost" ]] && \
  color_echo blue "🔐 Open ports ${UIPORT} (and ${APIPORT}) in the security group to reach these."
echo "----------------------------------------------------"

# ─────────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────────
color_echo blue "🔎 Verifying service health..."

# Poll rather than checking once: uvicorn and Streamlit both take a few seconds
# to bind, so a single immediate curl reports a healthy service as failed
# (status 000) and sends people to read a log with nothing wrong in it.
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

# Always checked over the loopback, whatever we bind to: it proves the process
# is serving without depending on a firewall rule or a public DNS record.
# The API serves /health (services/api/main.py) — not /v1/health, which has
# never existed and made this step always report failure.
API_STATUS=$(wait_for_http "http://127.0.0.1:${APIPORT}/health" 20)
if [[ "${API_STATUS}" == "200" ]]; then
  color_echo green "API OK (HTTP 200) → ${API_URL}  (docs: ${API_URL}/docs)"
else
  color_echo red "API health check failed (status=${API_STATUS:-unreachable}) — check ${API_LOG}"
fi

# ─────────────────────────────────────────────
# Open the UI in a browser
# ─────────────────────────────────────────────
# Only called once the UI answers 200 — opening earlier lands on a connection
# error and people assume the launch failed. Every branch is `|| true`: failing
# to open a browser is not a failed start.
open_browser() {
  local url="$1"

  if [[ -n "${NO_BROWSER:-}" ]]; then
    color_echo yellow "↷ NO_BROWSER set — not opening ${url}"
    return 0
  fi
  if [[ "${HEADLESS}" -eq 1 ]]; then
    color_echo yellow "↷ Headless host — open ${url} from your own machine"
    return 0
  fi

  # wslview first: on WSL, xdg-open exists but hands the URL to a Linux browser
  # that usually is not installed, so it fails silently and nothing appears.
  # wslview goes to the Windows default browser instead.
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

UI_STATUS=$(wait_for_http "http://127.0.0.1:${UIPORT}" 30)
if [[ "${UI_STATUS}" == "200" ]]; then
  color_echo green "UI OK (HTTP 200) → ${UI_URL}"
  open_browser "${UI_URL}"
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

sleep 1
touch "${COMBINED_LOG}"

# ─────────────────────────────────────────────
# Done — the services run in the background
# ─────────────────────────────────────────────
# Returning is the default. Everything above was started with nohup, so the
# services outlive this shell: closing the terminal, dropping the SSH session or
# running this from systemd all leave the app up. A blocking tail as the last
# line would mean the command never returns, which is wrong for a server and
# merely annoying on a laptop.
#
# FOLLOW=1 opts back into the live error view when you want to watch a start-up.
if [[ -z "${FOLLOW:-}" ]]; then
  echo "----------------------------------------------------"
  color_echo green "✅ Running in the background."
  color_echo blue  "   UI      ${UI_URL}"
  color_echo blue  "   Follow  tail -f ${COMBINED_LOG}"
  color_echo blue  "   Errors  FOLLOW=1 ./start.sh"
  color_echo blue  "   Stop    ./stop.sh"
  echo "----------------------------------------------------"
  exit 0
fi

color_echo yellow "👁  Real-time ERROR view (press Ctrl+C to exit; services keep running)..."
tail -n 20 -f "${COMBINED_LOG}" | grep --line-buffered -E --color=always "ERROR|Exception|Traceback|CRITICAL" || true
