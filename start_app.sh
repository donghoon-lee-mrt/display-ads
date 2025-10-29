#!/bin/bash
# Marketing Video Generator - Streamlit App Launcher
# Converted from START_APP.bat for macOS/Linux

set -e  # Exit on error

# ===== Ensure we run from the script directory =====
cd "$(dirname "$0")"

# ===== Config =====
PORT=${1:-3000}  # Default port 3000 (changed from 8511)
BIND_HOST="0.0.0.0"
OPEN_HOST="127.0.0.1"
LOG_FILE=".streamlit_server.log"

# ===== Load .env.local if present =====
if [ -f ".env.local" ]; then
  echo "[INFO] Loading .env.local"
  # Export variables from .env.local, ignoring comments and empty lines
  export $(grep -v '^#' .env.local | grep -v '^$' | xargs)
fi

echo ""
echo "[INFO] Bind host: $BIND_HOST  port: $PORT"

# ===== Detect Python venv =====
# Check if venv has pip module available
if [ -f ".venv/bin/python" ] && .venv/bin/python -m pip --version &> /dev/null; then
  PY_EXE=".venv/bin/python"
  PIP_EXE="$PY_EXE -m pip"
  STREAMLIT_EXE=".venv/bin/streamlit"
  echo "[INFO] Using venv Python: $PY_EXE"
else
  PY_EXE="python3"
  PIP_EXE="$PY_EXE -m pip"
  STREAMLIT_EXE="streamlit"
  echo "[INFO] Using system Python: $PY_EXE"

  # Check if python3 is available
  if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3."
    exit 1
  fi
fi

# ===== Kill processes using the port =====
echo "[INFO] Checking for processes using port $PORT..."
if lsof -ti:$PORT &> /dev/null; then
  echo "[INFO] Killing processes using port $PORT"
  lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
else
  echo "[INFO] Port $PORT is free"
fi

# ===== Ensure requirements are installed =====
echo "[INFO] Ensuring dependencies with $PIP_EXE ..."
$PIP_EXE install -r requirements.txt --disable-pip-version-check -q

# ===== Run Streamlit =====
if ! $PIP_EXE show streamlit &> /dev/null; then
  echo "[INFO] Installing streamlit via $PIP_EXE ..."
  $PIP_EXE install streamlit --disable-pip-version-check -q
fi

echo "[INFO] Starting Streamlit on $BIND_HOST:$PORT"

# Clear old log file
[ -f "$LOG_FILE" ] && rm -f "$LOG_FILE"

# Log versions
echo "[INFO] Python/Streamlit versions" > "$LOG_FILE"
$PY_EXE --version >> "$LOG_FILE" 2>&1
$PY_EXE -m streamlit --version >> "$LOG_FILE" 2>&1

# Start Streamlit in background
echo "[INFO] Launching Streamlit..."
$PY_EXE -m streamlit run app.py \
  --server.address="$BIND_HOST" \
  --server.port="$PORT" \
  --server.headless=true \
  >> "$LOG_FILE" 2>&1 &

STREAMLIT_PID=$!
echo "[INFO] Streamlit started with PID: $STREAMLIT_PID"

# ===== Wait for server to be ready =====
echo "[INFO] Waiting for server to listen on port $PORT ..."
_waited=0
SERVER_READY=false

while [ $_waited -lt 90 ]; do
  if lsof -ti:$PORT &> /dev/null; then
    SERVER_READY=true
    break
  fi
  sleep 1
  _waited=$((_waited + 1))
  if [ $((_waited % 10)) -eq 0 ]; then
    echo "[INFO] Still waiting... (${_waited}s)"
  fi
done

# ===== Check if server started successfully =====
if [ "$SERVER_READY" = true ]; then
  SERVER_PID=$(lsof -ti:$PORT 2>/dev/null | head -1)
  echo "[INFO] Server is ready (PID $SERVER_PID)"
  echo "[INFO] Opening browser..."

  # Open browser (macOS)
  if command -v open &> /dev/null; then
    open "http://$OPEN_HOST:$PORT/"
  # Open browser (Linux)
  elif command -v xdg-open &> /dev/null; then
    xdg-open "http://$OPEN_HOST:$PORT/"
  else
    echo "[INFO] Please open your browser to: http://$OPEN_HOST:$PORT/"
  fi

  echo ""
  echo "=========================================="
  echo "  🚀 Streamlit App is Running!"
  echo "=========================================="
  echo "  URL: http://$OPEN_HOST:$PORT/"
  echo "  PID: $SERVER_PID"
  echo "  Log: $LOG_FILE"
  echo "=========================================="
  echo ""
  echo "Press Ctrl+C to stop the server"
  echo ""

  # Keep script running and tail logs
  tail -f "$LOG_FILE"
else
  echo "[WARN] Server did not start within ${_waited}s. Showing logs below:"
  if [ -f "$LOG_FILE" ]; then
    cat "$LOG_FILE"
  fi
  echo "[HINT] Fix errors above and re-run start_app.sh"
  exit 1
fi
