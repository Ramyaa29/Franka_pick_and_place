# 🤖 Autonomous Franka Emika Panda Color Sorting Robot with Web GUI Dashboard

[![ROS 2](https://img.shields.io/badge/ROS_2-Humble-3498DB?style=for-the-badge&logo=ros&logoColor=white)](https://docs.ros.org/en/humble/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Fortress_Sim-FF6F00?style=for-the-badge&logo=gazebo&logoColor=white)](https://gazebosim.org/)
[![MoveIt 2](https://img.shields.io/badge/MoveIt_2-Motion_Planning-8E44AD?style=for-the-badge)](https://moveit.picknik.ai/)
[![Docker](https://img.shields.io/badge/Docker-Desktop_Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Flask](https://img.shields.io/badge/Flask-Web_Controller-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

An advanced, end-to-end autonomous robotic manipulation and sorting system using the **7-DoF Franka Emika Panda** robot in **Gazebo Sim Fortress**. 

Built on **ROS 2 Humble** and **MoveIt 2**, this system features a **custom real-time Flask Web GUI Dashboard** that provides live overhead RealSense video streaming, real-time 3D object coordinate tracking, one-click color sorting commands (**Red**, **Green**, **Blue**), and an instant **Emergency Stop & Motion Preemption** mechanism.

---

## 🎥 Video Demonstrations

================================================================= 
### 🎥 VIDEO DEMO 1: ROBOT PICK AND PLACE SIMULATION  
  <!-- [▶️ Watch the GUI Demo](assets/GUI.mp4) -->
================================================================= 

---

=================================================================
### 🎥 VIDEO DEMO 2: FLASK WEB GUI DASHBOARD INTERACTION 
<!-- https://github.com/Ramyaa29/Franka_pick_and_place/blob/main/assets/GUI.mp4 -->
[▶️ Watch the GUI Demo](assets/GUI.mp4)
=================================================================

---

## Key Technologies Used

Languages: Python, HTML, CSS, JavaScript, Bash
Robotics: ROS 2 Humble, MoveIt 2, PyMoveIt2, ros2_control
Simulation: Gazebo Sim Fortress, RViz2
Computer Vision: OpenCV, HSV-based color detection, RealSense RGB-D camera
Web Development: Flask, real-time MJPEG streaming
DevOps and Environment: Docker, Docker Compose, Ubuntu, WSL2

## 🌟 Unique Features & Enhancements

This project significantly enhances standard robotic sorting pipelines with a complete human-machine interface and production containerization:

* 🎛️ **Flask Web Controller**: Control the robot from any browser (`http://localhost:5000`) without typing terminal commands.
* 🔴🟢🔵 **Interactive 3-Color Pick Triggers**: Dedicated **Pick Red (`🟥`)**, **Pick Green (`🟩`)**, and **Pick Blue (`🟦`)** buttons.
* 📹 **Live Overhead RealSense Video Feed**: Low-latency MJPEG video streaming of the camera feed (`/camera/image_raw`) directly on the web page.
* ⏹️ **Instant Emergency Stop & Preemption**: Real-time trajectory preemption halts the arm immediately without crashing the node.
* 📍 **Live 3D Telemetry**: Displays detected base-frame coordinates $(x, y, z)$ published dynamically by the OpenCV vision node.
* 🐳 **1-Click Docker Desktop Deployment**: Runs with Docker Compose and automatically supports **Windows 11 WSLg 3D graphics** as well as **headless cloud servers via Xvfb**.

---

## 🏗️ System Pipeline

```
                                ┌────────────────────────────────────────┐
                                │      Overhead RealSense RGB-D Camera   │
                                └───────────────────┬────────────────────┘
                                                    │ /camera/image_raw
                                                    ▼
                                ┌────────────────────────────────────────┐
                                │    OpenCV Color Detection (HSV Mask)   │
                                └───────────────────┬────────────────────┘
                                                    │ /color_coordinates (X, Y, Z)
                                                    ▼
┌─────────────────────────┐     ┌────────────────────────────────────────┐
│  Web GUI Dashboard      │────▶│    Pick & Place Sequencer (PyMoveIt2)  │
│  - Pick Red/Green/Blue  │◀────│    - Cartesian trajectory planning     │
│  - Start / Stop / Reset │     │    - Asynchronous worker threading     │
│  - Live MJPEG Stream    │     └───────────────────┬────────────────────┘
└─────────────────────────┘                         │ Joint Trajectories
                                                    ▼
                                ┌────────────────────────────────────────┐
                                │   MoveIt 2 MoveGroup & ros2_control    │
                                └───────────────────┬────────────────────┘
                                                    │ Joint Commands
                                                    ▼
                                ┌────────────────────────────────────────┐
                                │ Franka Emika Panda (Gazebo Sim + RViz) │
                                └────────────────────────────────────────┘
```

---

## ⚡ Quick Start: Running on Your Laptop

You can run this project either via **Docker Desktop** (no ROS 2 installation needed) or **locally via WSL2 / Ubuntu 22.04**.

---

### Method A: Running with Docker Desktop (Recommended)

#### Option 1: 1-Click Batch Script (Windows)
1. In Windows Explorer, open:
   ```text
   \\wsl$\Ubuntu\home\ramya\panda_ws
   ```
2. Double-click **`deploy_docker_desktop.bat`**.
3. It will build and launch the container into your Docker Desktop application and open your browser automatically!

#### Option 2: From Terminal
```bash
cd ~/panda_ws
docker compose up --build -d
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

> [!NOTE]
> * **On Windows 11**: The real **Gazebo 3D simulation window** and **RViz2 window** will open natively on your Windows desktop through WSLg display forwarding!
> * **In Docker Desktop**: You can see `panda_robot_stack` running green, monitor container logs, and click the `5000:5000` port shortcut.

---

### Method B: Running Natively on Your Local PC (WSL2 / Ubuntu 22.04)

#### 1. Sourcing Environment & Launching All-in-One:
In a single terminal command, start Gazebo, RViz, MoveIt 2, vision detection, and the Web GUI:

```bash
cd ~/panda_ws
source setup_env.sh
ros2 launch panda_bringup pick_and_place.launch.py auto_start:=false gui:=true
```

#### 2. Open the Web GUI:
Open your browser and navigate to:
👉 **[http://localhost:5000](http://localhost:5000)**

---

### Method C: Running Modally (Separate Backend & Frontend)

If you prefer having separate terminals for debugging:

* **Terminal 1: Simulation & MoveIt Backend**
  ```bash
  source ~/panda_ws/setup_env.sh
  ros2 launch panda_bringup pick_and_place.launch.py auto_start:=false gui:=false
  ```

* **Terminal 2: Flask Web GUI Dashboard**
  ```bash
  ~/panda_ws/flask_gui/run_gui.sh
  ```

---

## 🎮 How to Use the Web Dashboard

When you open **`http://localhost:5000`**, you have access to:

| Button / Element | Function |
| :--- | :--- |
| **Pick Red (`🟥`)** | Directs the robot arm to pick the detected Red cube and place it into the trash bin. |
| **Pick Green (`🟩`)** | Directs the robot arm to pick the detected Green cube and place it into the trash bin. |
| **Pick Blue (`🟦`)** | Directs the robot arm to pick the detected Blue cube and place it into the trash bin. |
| **Start Robot (`▶️`)** | Clears any emergency stop / paused state and enables motion. |
| **Stop Robot (`⏹️`)** | Immediately cancels the active MoveIt trajectory and halts the robot in place. |
| **Home Posture (`🔄`)** | Safely opens the gripper and commands the arm back to its default standby joint posture. |
| **Live Camera Feed** | Displays real-time streaming video directly from `/camera/image_raw`. |
| **Vision Coordinates** | Displays real-time 3D coordinates $(x, y, z)$ in the robot's base frame. |

---

## 📁 Repository Structure

```
panda_ws/
├── Dockerfile                     # Headless & WSLg compatible container build
├── docker-compose.yml             # 1-click Docker orchestration
├── docker-entrypoint.sh           # Auto-display routing (WSLg desktop / Xvfb cloud)
├── deploy_docker_desktop.bat      # Windows 1-click deploy launcher
├── deploy_docker_desktop.ps1      # PowerShell deploy launcher
├── setup_env.sh                   # Sourcing script for ros2_control & Gazebo
├── .gitignore                     # Git tracking exclusions
├── flask_gui/
│   ├── app.py                     # Flask server with ROS 2 bridge & MJPEG streamer
│   ├── templates/index.html       # Responsive dark-theme dashboard UI
│   └── run_gui.sh                 # Standalone GUI startup script
└── src/
    ├── panda_bringup/             # Main launch files orchestrating the full system
    ├── panda_description/         # Franka Panda URDF, Xacro, meshes, and world models
    ├── panda_controller/          # ros2_control joint trajectory and gripper controllers
    ├── panda_moveit/              # MoveIt 2 configs, SRDF, kinematic constraints
    ├── panda_vision/              # OpenCV color detection node
    └── pymoveit2/                 # Python MoveIt 2 Cartesian trajectory sequencer
```

---

## 📡 Key ROS 2 Topics

| Topic | Message Type | Description |
| :--- | :--- | :--- |
| `/robot_command` | `std_msgs/msg/String` | Commands sent from the Web GUI (`START`, `STOP`, `PICK_R`, `PICK_G`, `PICK_B`, `RESET`). |
| `/robot_status` | `std_msgs/msg/String` | Real-time JSON telemetry stream (`IDLE`, `RUNNING`, `STOPPED`, step descriptions). |
| `/color_coordinates` | `std_msgs/msg/String` | Detected 3D object positions formatted as `Color,X,Y,Z`. |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | Overhead RealSense camera image stream. |
| `/joint_states` | `sensor_msgs/msg/JointState` | Current 7-DoF robot joint angles and finger states. |

---

## ⚙️ Prerequisites & Installation (For Manual Setup)

### System Requirements
* **OS**: Ubuntu 22.04 LTS or Windows 11 with WSL2
* **ROS**: ROS 2 Humble Desktop Full
* **Simulation**: Gazebo Sim Fortress (`ign gazebo`)
* **Motion Planning**: MoveIt 2 (`ros-humble-moveit`)

### Dependency Installation
```bash
sudo apt-get update && sudo apt-get install -y \
  ros-humble-moveit \
  ros-humble-ros-gz \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-ign-ros2-control \
  ros-humble-cv-bridge

pip3 install flask opencv-python numpy
```

### Build Instructions
```bash
cd ~/panda_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source setup_env.sh
```

---

## ⚠️ Troubleshooting

* **Q: Gazebo says `Joint states are not available yet!` on startup?**  
  **A**: This is normal during the first 15–20 seconds while Gazebo loads the 3D meshes and initializes the hardware controllers. It will automatically resolve once `joint_state_broadcaster` activates.

* **Q: The browser cannot connect to `http://localhost:5000`?**  
  **A**: Ensure the Flask server has launched (wait ~6 seconds after launching ROS 2). You can also run `~/panda_ws/flask_gui/run_gui.sh` in a separate terminal.

* **Q: How to reset robot after pressing Emergency Stop?**  
  **A**: Simply click **Start Robot (`▶️`)** or **Home Posture (`🔄`)** in the Web GUI.

---

## 📚 Credits & Acknowledgments

* **Base Reference**: Derived and extended from the [Franka_Panda_Color_Sorting_Robot](https://github.com/MechaMind-Labs/Franka_Panda_Color_Sorting_Robot) by **MechaMind-Labs** / [Curious-Utkarsh](https://github.com/Curious-Utkarsh).
* **Unique Contributions in this Repository**:
  * Designed and built the complete **Flask Web GUI Controller** with live camera streaming and telemetry.
  * Implemented non-blocking **asynchronous MoveIt 2 worker threading** with instant emergency stop trajectory preemption.
  * Engineered a production **multi-stage Docker container** with dynamic dual-display support (Windows WSLg desktop forwarding + headless cloud Xvfb).
  * Automated 1-click launch workflows and environment configuration.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
