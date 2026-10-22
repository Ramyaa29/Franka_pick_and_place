import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import Command, LaunchConfiguration
from launch.conditions import UnlessCondition, IfCondition
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    is_sim = LaunchConfiguration("is_sim")

    is_sim_arg = DeclareLaunchArgument(
        "is_sim",
        default_value="True"
    )

    robot_description = ParameterValue(
        Command(
            [
                "xacro ",
                os.path.join(
                    get_package_share_directory("panda_description"),
                    "urdf",
                    "panda.urdf.xacro",
                ),
                " is_sim:=True",
                " is_ignition:=True"  # Ignition/Gazebo Sim (ROS 2 Humble)
            ]
        ),
        value_type=str,
    )

    # Only start robot_state_publisher when NOT in sim mode
    # (in sim mode, gazebo.launch.py already starts it)
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        condition=UnlessCondition(is_sim),
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": is_sim}],
    )

    # Only start hardware controller_manager when NOT in sim
    # (in sim mode, ign_ros2_control plugin manages this)
    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        condition=UnlessCondition(is_sim),
        parameters=[
            {"robot_description": robot_description,
             "use_sim_time": is_sim},
            os.path.join(
                get_package_share_directory("panda_controller"),
                "config",
                "panda_controllers.yaml",
            ),
        ],
    )

    # Spawners with timeout
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "gripper_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    # In sim mode, wait 18s for Gazebo to load, then spawn sequentially
    delayed_joint_state_broadcaster = TimerAction(
        period=18.0,
        actions=[joint_state_broadcaster_spawner],
        condition=IfCondition(is_sim),
    )

    arm_controller_on_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner],
        )
    )

    gripper_controller_on_arm = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_controller_spawner,
            on_exit=[gripper_controller_spawner],
        )
    )

    # When NOT in sim, start JSB immediately after controller_manager starts
    immediate_jsb_not_sim = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[joint_state_broadcaster_spawner],
        ),
        condition=UnlessCondition(is_sim),
    )

    return LaunchDescription(
        [
            is_sim_arg,
            robot_state_publisher_node,
            controller_manager,
            delayed_joint_state_broadcaster,
            arm_controller_on_jsb,
            gripper_controller_on_arm,
            immediate_jsb_not_sim,
        ]
    )