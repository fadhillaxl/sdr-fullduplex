#!/usr/bin/env bash
# ==============================================================================
# Pluto+ SDR Short-Range IP Radio & Mission Control UI Launcher
# Usage:
#   ./start_app.sh [all | backend | ui | background | stop | status]
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT=8000
UI_PORT=3000

# Color codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

find_python() {
    if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
        echo "$SCRIPT_DIR/.venv/bin/python"
    elif [ -f "$SCRIPT_DIR/MeshNetworkSDR/.venv/bin/python" ]; then
        echo "$SCRIPT_DIR/MeshNetworkSDR/.venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo "python"
    fi
}

has_npm() {
    command -v npm >/dev/null 2>&1
}

check_node_version() {
    if ! has_npm; then
        return 1 # No npm/node
    fi
    NODE_MAJOR=$(node -v 2>/dev/null | tr -d 'v' | cut -d'.' -f1 || echo "0")
    if [ "$NODE_MAJOR" -lt 20 ]; then
        return 2 # Node < 20
    fi
    return 0 # Node >= 20
}

get_my_ip() {
    hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}

start_backend_foreground() {
    PYTHON_BIN=$(find_python)
    echo -e "${CYAN}📡 Starting Pluto+ SDR FastAPI Backend on 0.0.0.0:${BACKEND_PORT}...${NC}"
    echo -e "${YELLOW}ℹ Note: TUN/TAP interface creation requires sudo privileges.${NC}"
    sudo "$PYTHON_BIN" -m pluto_radio.cli server --host 0.0.0.0 --port "$BACKEND_PORT"
}

start_ui_foreground() {
    check_node_version
    NODE_STATUS=$?
    if [ $NODE_STATUS -eq 1 ]; then
        echo -e "${RED}❌ npm / Node.js is not installed on this machine.${NC}"
        echo -e "${YELLOW}💡 Tip: Run the Next.js UI on your laptop and select this node at http://$(get_my_ip):${BACKEND_PORT}.${NC}"
        return 1
    elif [ $NODE_STATUS -eq 2 ]; then
        echo -e "${RED}❌ Node.js $(node -v) is too old for Next.js 16 (requires Node >= 20.9.0).${NC}"
        echo -e "${YELLOW}💡 Tip: Run the Next.js UI on your laptop and connect to this node via http://$(get_my_ip):${BACKEND_PORT}.${NC}"
        echo -e "   To upgrade Node on Linux: ${CYAN}curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs${NC}"
        return 1
    fi

    echo -e "${CYAN}🚀 Starting Next.js Mission Control UI on 0.0.0.0:${UI_PORT}...${NC}"
    cd "$SCRIPT_DIR/web-ui"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing npm dependencies first...${NC}"
        npm install
    fi
    npm run dev -- -H 0.0.0.0 -p "$UI_PORT"
}

start_background() {
    PYTHON_BIN=$(find_python)
    echo -e "${CYAN}📡 Starting Pluto+ SDR Backend in background (logs: backend.log)...${NC}"
    sudo nohup "$PYTHON_BIN" -u -m pluto_radio.cli server --host 0.0.0.0 --port "$BACKEND_PORT" > "$SCRIPT_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/pluto_backend.pid
    sleep 2

    MY_IP=$(get_my_ip)

    check_node_version
    NODE_STATUS=$?
    if [ $NODE_STATUS -eq 0 ]; then
        echo -e "${CYAN}🚀 Starting Next.js UI in background (logs: ui.log)...${NC}"
        cd "$SCRIPT_DIR/web-ui"
        if [ ! -d "node_modules" ]; then
            npm install
        fi
        nohup npm run dev -- -H 0.0.0.0 -p "$UI_PORT" > "$SCRIPT_DIR/ui.log" 2>&1 &
        UI_PID=$!
        echo $UI_PID > /tmp/pluto_ui.pid
        sleep 2
        echo -e "${GREEN}✅ All services started successfully!${NC}"
        echo -e "   • Mission UI:   ${CYAN}http://${MY_IP}:${UI_PORT}${NC}"
    else
        echo -e "${GREEN}✅ Backend started successfully!${NC}"
        if [ $NODE_STATUS -eq 2 ]; then
            echo -e "${YELLOW}ℹ (Node.js $(node -v) is < v20; skipping local UI build on this edge device to save RAM).${NC}"
        else
            echo -e "${YELLOW}ℹ (Node.js not installed; skipping local UI build on this edge device).${NC}"
        fi
        echo -e "${CYAN}💡 Open the Next.js UI on your laptop (http://localhost:3001) and select '${MY_IP}:${BACKEND_PORT}' in the top bar!${NC}"
    fi

    echo -e "   • Backend API:  ${CYAN}http://${MY_IP}:${BACKEND_PORT}${NC}"
    echo -e "   • Swagger UI:   ${CYAN}http://${MY_IP}:${BACKEND_PORT}/docs${NC}"
}

stop_all() {
    echo -e "${YELLOW}🛑 Stopping Pluto+ SDR services...${NC}"
    # Stop backend
    sudo pkill -f "pluto_radio.cli server" 2>/dev/null || true
    # Stop Next.js server
    pkill -f "next-server" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    rm -f /tmp/pluto_backend.pid /tmp/pluto_ui.pid
    echo -e "${GREEN}✅ All services stopped.${NC}"
}

check_status() {
    echo -e "${CYAN}=== Pluto+ SDR Service Status ===${NC}"
    echo -n "Backend API (:8000): "
    if curl -s "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        echo -e "${GREEN}RUNNING (Online)${NC}"
    else
        echo -e "${RED}STOPPED${NC}"
    fi

    echo -n "Next.js UI (:3000): "
    if curl -s "http://127.0.0.1:${UI_PORT}" >/dev/null 2>&1; then
        echo -e "${GREEN}RUNNING (Online)${NC}"
    else
        check_node_version
        NODE_STATUS=$?
        if [ $NODE_STATUS -eq 0 ]; then
            echo -e "${RED}STOPPED${NC}"
        elif [ $NODE_STATUS -eq 2 ]; then
            echo -e "${YELLOW}SKIPPED (Node.js $(node -v) is < v20 - run UI on laptop)${NC}"
        else
            echo -e "${YELLOW}NOT INSTALLED (Node.js not found - run UI on laptop)${NC}"
        fi
    fi
}

MODE="${1:-all}"

case "$MODE" in
    backend)
        start_backend_foreground
        ;;
    ui)
        start_ui_foreground
        ;;
    all)
        PYTHON_BIN=$(find_python)
        check_node_version
        if [ $? -eq 0 ]; then
            echo -e "${CYAN}📡 Starting Backend and UI concurrently...${NC}"
            sudo nohup "$PYTHON_BIN" -u -m pluto_radio.cli server --host 0.0.0.0 --port "$BACKEND_PORT" > "$SCRIPT_DIR/backend.log" 2>&1 &
            trap stop_all EXIT
            start_ui_foreground
        else
            echo -e "${YELLOW}ℹ Node.js >= v20 not present on this edge device. Running Backend only.${NC}"
            echo -e "${CYAN}💡 Open the Next.js UI on your laptop at http://localhost:3001 and select this node!${NC}"
            start_backend_foreground
        fi
        ;;
    background|daemon)
        start_background
        ;;
    stop)
        stop_all
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 [all | backend | ui | background | stop | status]"
        exit 1
        ;;
esac
