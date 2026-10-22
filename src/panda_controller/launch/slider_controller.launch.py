import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # 1. Properly wrap the included launch file with PythonLaunchDescriptionSource
    controller = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("panda_controller"),
                "launch",
                "panda_controller.launch.py"
            )
        ),
        launch_arguments={"is_sim": "True"}.items()
    )

    # 2. Joint State Publisher GUI (publishes to /joint_commands for slider_controller)
    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        remappings=[
            ('/joint_states', '/joint_commands')
        ]
    )

    # 3. Your custom bridge/slider controller node
    slider_control_node = Node(
        package="panda_controller",
        executable="slider_controller.py"
    )

    return LaunchDescription(
        [
            controller,
            joint_state_publisher_gui_node,
            slider_control_node
        ]
    )