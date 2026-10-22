#!/usr/bin/env bash
set -e

# Detect host display (WSLg on Windows 11 / Linux X11)
if [ -n "$DISPLAY" ] && [ -e "/tmp/.X11-unix/X${DISPLAY#*:}" ]; then
    echo "=========================================================="
    echo "🖥️ Host GUI Display detected: $DISPLAY"
    echo "🪟 Gazebo & RViz2 windows will open on your Windows desktop!"
    echo "=========================================================="
elif [ -e "/tmp/.X11-unix/X0" ]; then
    export DISPLAY=:0
    echo "=========================================================="
    echo "🖥️ WSLg display socket detected: DISPLAY=:0"
    echo "🪟 Gazebo & RViz2 windows will open on your Windows desktop!"
    echo "=========================================================="
else
    # Fallback for cloud/headless servers without desktop display
    echo "=========================================================="
    echo "🖥️ No host display detected. Starting headless Xvfb..."
    echo "=========================================================="
    export DISPLAY=:99
    Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
    XVFB_PID=$!
    cleanup() {
        echo "Stopping background Xvfb..."
        kill $XVFB_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup SIGINT SIGTERM
fi

echo "=========================================================="
echo "🤖 Starting Franka Emika Panda Autonomous Pick & Place Stack"
echo "🌐 Flask Web Dashboard will be available at: http://localhost:5000"
echo "=========================================================="

# Source workspace environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "/workspace/panda_ws/setup_env.sh" ]; then
    source /workspace/panda_ws/setup_env.sh
elif [ -f "$SCRIPT_DIR/setup_env.sh" ]; then
    source "$SCRIPT_DIR/setup_env.sh"
elif [ -n "$PANDA_WS" ] && [ -f "$PANDA_WS/setup_env.sh" ]; then
    source "$PANDA_WS/setup_env.sh"
fi

# Launch simulation stack + Flask Web GUI
exec ros2 launch panda_bringup pick_and_place.launch.py auto_start:=false gui:=true
