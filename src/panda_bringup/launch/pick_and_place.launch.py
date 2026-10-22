import os
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    TimerAction,
    DeclareLaunchArgument,
    ExecuteProcess,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    # ------------------- Launch Arguments -------------------
    target_color_arg = DeclareLaunchArgument(
        "target_color",
        default_value="B",
        description="Default target cube color to pick (R, G, or B)",
    )

    auto_start_arg = DeclareLaunchArgument(
        "auto_start",
        default_value="false",
        description="Automatically start pick-and-place on launch without waiting for GUI",
    )

    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="true",
        description="Whether to automatically launch the Flask Web GUI on http://localhost:5000",
    )

    # ------------------- Gazebo -------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("panda_description"),
                "launch",
                "gazebo.launch.py",
            )
        )
    )

    # ------------------- Controllers -------------------
    controller = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("panda_controller"),
                "launch",
                "panda_controller.launch.py",
            )
        ),
        launch_arguments={"is_sim": "True"}.items(),
    )

    # ------------------- MoveIt -------------------
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("panda_moveit"),
                "launch",
                "moveit.launch.py",
            )
        ),
        launch_arguments={"is_sim": "True"}.items(),
    )

    # ------------------- Vision Node -------------------
    vision_node = Node(
        package="panda_vision",
        executable="color_detector",
        name="color_detector",
        output="screen",
    )

    # ------------------- Pick and Place Node -------------------
    color_picker_node = Node(
        package="pymoveit2",
        executable="pick_and_place.py",
        name="pick_and_place",
        output="screen",
        parameters=[
            {"target_color": LaunchConfiguration("target_color")},
            {"auto_start": LaunchConfiguration("auto_start")},
        ],
    )

    # Delay pick_and_place node by 28 seconds so Gazebo, controllers and MoveIt are ready
    delayed_color_picker_node = TimerAction(
        period=28.0, actions=[color_picker_node]
    )

    # ------------------- Flask Web GUI -------------------
    workspace_dir = os.environ.get("PANDA_WS", "/home/ramya/panda_ws")
    flask_gui_script = os.path.join(workspace_dir, "flask_gui", "run_gui.sh")
    flask_gui_process = ExecuteProcess(
        cmd=["bash", flask_gui_script],
        output="screen",
        condition=IfCondition(LaunchConfiguration("gui")),
    )

    # Delay Flask GUI by 6 seconds so ROS graph starts
    delayed_flask_gui = TimerAction(period=6.0, actions=[flask_gui_process])

    return LaunchDescription(
        [
            target_color_arg,
            auto_start_arg,
            gui_arg,
            gazebo,
            controller,
            moveit,
            vision_node,
            delayed_color_picker_node,
            delayed_flask_gui,
        ]
    )
