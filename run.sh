#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧹 Cleaning up any previous dangling simulation or ROS 2 processes..."
killall -9 ign gazebo ruby rviz2 2>/dev/null || true
sleep 1

# Check if build and install exist
if [ ! -f "$SCRIPT_DIR/install/setup.bash" ]; then
    echo "📦 Building workspace first..."
    cd "$SCRIPT_DIR"
    source /opt/ros/humble/setup.bash
    colcon build --symlink-install
fi

echo "📦 Sourcing environment from: $SCRIPT_DIR/setup_env.sh"
source "$SCRIPT_DIR/setup_env.sh"

echo "========================================================================"
echo "🚀 Starting Franka Emika Panda Autonomous Sorting Stack..."
echo "👉 Interactive Web Dashboard: http://localhost:5000"
echo "========================================================================"

exec ros2 launch panda_bringup pick_and_place.launch.py auto_start:=false gui:=true
