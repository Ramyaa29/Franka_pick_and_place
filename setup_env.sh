#!/usr/bin/env bash
# Source ROS 2 Humble base and panda_ws install space
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PANDA_WS="${PANDA_WS:-$SCRIPT_DIR}"

source /opt/ros/humble/setup.bash
if [ -f "$PANDA_WS/install/setup.bash" ]; then
    source "$PANDA_WS/install/setup.bash"
fi

# Export environment paths for ros2_control & Ignition Gazebo integration
CONTROL_PLUGIN_DIR="$PANDA_WS/install/ros2_control_plugins/opt/ros/humble"
if [ -d "$CONTROL_PLUGIN_DIR" ]; then
    export AMENT_PREFIX_PATH="$CONTROL_PLUGIN_DIR:${AMENT_PREFIX_PATH}"
    export LD_LIBRARY_PATH="$CONTROL_PLUGIN_DIR/lib:${LD_LIBRARY_PATH}"
    export IGN_GAZEBO_SYSTEM_PLUGIN_PATH="$CONTROL_PLUGIN_DIR/lib:${IGN_GAZEBO_SYSTEM_PLUGIN_PATH}"
    export GZ_SIM_SYSTEM_PLUGIN_PATH="$CONTROL_PLUGIN_DIR/lib:${GZ_SIM_SYSTEM_PLUGIN_PATH}"
fi

PANDA_MODELS="$PANDA_WS/install/panda_description/share/panda_description/models:$PANDA_WS/install/panda_description/share:$PANDA_WS/src/panda_description/models:$PANDA_WS/src/panda_description"
export IGN_GAZEBO_RESOURCE_PATH="$PANDA_MODELS:${IGN_GAZEBO_RESOURCE_PATH}"
export GZ_SIM_RESOURCE_PATH="$PANDA_MODELS:${GZ_SIM_RESOURCE_PATH}"

# Force software rendering for Gazebo / Ogre on WSL2 / Docker to avoid GL crashes
export LIBGL_ALWAYS_SOFTWARE=1
