# ==============================================================================
# Franka Emika Panda Autonomous Pick-and-Place with MoveIt 2 & Flask Web GUI
# Multi-stage production Dockerfile
# ==============================================================================

FROM osrf/ros:humble-desktop AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV PANDA_WS=/workspace/panda_ws
ENV LIBGL_ALWAYS_SOFTWARE=1

# Install system dependencies, Gazebo Fortress libraries, Xvfb virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    xvfb \
    mesa-utils \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    ros-${ROS_DISTRO}-moveit \
    ros-${ROS_DISTRO}-ros-gz \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-ign-ros2-control \
    ros-${ROS_DISTRO}-cv-bridge \
    python3-pip \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements for Flask Web GUI
RUN pip3 install --no-cache-dir \
    flask \
    opencv-python-headless \
    numpy

# Setup workspace directory
WORKDIR ${PANDA_WS}

# Copy workspace source files, plugins, and configurations
COPY src/ ${PANDA_WS}/src/
COPY install/ros2_control_plugins/ ${PANDA_WS}/install/ros2_control_plugins/
COPY flask_gui/ ${PANDA_WS}/flask_gui/
COPY setup_env.sh ${PANDA_WS}/setup_env.sh
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Ensure execution permissions on scripts
RUN chmod +x ${PANDA_WS}/setup_env.sh \
             ${PANDA_WS}/flask_gui/run_gui.sh \
             ${PANDA_WS}/flask_gui/app.py \
             /docker-entrypoint.sh

# Build all 6 ROS 2 packages inside container
RUN /bin/bash -c "source /opt/ros/${ROS_DISTRO}/setup.bash && colcon build --symlink-install"

# Expose Flask Web Dashboard Port
EXPOSE 5000

# Set entrypoint to headless virtual framebuffer runner
ENTRYPOINT ["/docker-entrypoint.sh"]
