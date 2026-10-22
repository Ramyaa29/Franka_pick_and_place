import os
from os import pathsep
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    panda_description = get_package_share_directory("panda_description")

    model_arg = DeclareLaunchArgument(
        name="model", default_value=os.path.join(
                panda_description, "urdf", "panda.urdf.xacro"
            ),
        description="Absolute path to robot urdf file"
    )

    world_name_arg = DeclareLaunchArgument(name="world_name", default_value="empty")

    world_path = PathJoinSubstitution([
            panda_description,
            "worlds",
            PythonExpression(expression=["'", LaunchConfiguration("world_name"), "'", " + '.world'"])
        ]
    )

    model_path = str(Path(panda_description).parent.resolve())
    model_path += pathsep + os.path.join(get_package_share_directory("panda_description"), 'models')

    plugin_path = os.environ.get("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", "")
    ws_dir = os.environ.get("PANDA_WS", "/home/ramya/panda_ws")
    control_lib_path = os.path.join(ws_dir, "install", "ros2_control_plugins", "opt", "ros", "humble", "lib")
    if control_lib_path not in plugin_path:
        plugin_path = control_lib_path + (pathsep + plugin_path if plugin_path else "")

    # Export directly to os.environ so included launch files (like gz_sim.launch.py)
    # can read IGN_GAZEBO_RESOURCE_PATH and plugin paths via os.environ.get()
    current_ign_res = os.environ.get("IGN_GAZEBO_RESOURCE_PATH", "")
    if model_path not in current_ign_res:
        os.environ["IGN_GAZEBO_RESOURCE_PATH"] = model_path + (pathsep + current_ign_res if current_ign_res else "")
    current_gz_res = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    if model_path not in current_gz_res:
        os.environ["GZ_SIM_RESOURCE_PATH"] = model_path + (pathsep + current_gz_res if current_gz_res else "")
    os.environ["IGN_GAZEBO_SYSTEM_PLUGIN_PATH"] = plugin_path
    os.environ["GZ_SIM_SYSTEM_PLUGIN_PATH"] = plugin_path
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

    gazebo_resource_path = SetEnvironmentVariable(
        "GZ_SIM_RESOURCE_PATH",
        os.environ["GZ_SIM_RESOURCE_PATH"]
    )
    ign_resource_path = SetEnvironmentVariable(
        "IGN_GAZEBO_RESOURCE_PATH",
        os.environ["IGN_GAZEBO_RESOURCE_PATH"]
    )
    ign_plugin_path = SetEnvironmentVariable(
        "IGN_GAZEBO_SYSTEM_PLUGIN_PATH",
        plugin_path
    )
    gz_plugin_path = SetEnvironmentVariable(
        "GZ_SIM_SYSTEM_PLUGIN_PATH",
        plugin_path
    )
    libgl_software = SetEnvironmentVariable(
        "LIBGL_ALWAYS_SOFTWARE",
        "1"
    )

    ros_distro = os.environ.get("ROS_DISTRO", "humble")
    is_ignition = "True" if ros_distro == "humble" else "False"

    robot_description = ParameterValue(Command([
            "xacro ",
            LaunchConfiguration("model"),
            " is_ignition:=",
            is_ignition
        ]),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": True}]
    )

    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory("ros_gz_sim"), "launch"), "/gz_sim.launch.py"]),
                launch_arguments={
                    "gz_args": PythonExpression(["'", world_path, " -v 4 -r'"])
                }.items()
             )


    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-name", "panda",
            "-x", "0.0",  
            "-y", "0.0",  
            "-z", "0.0",  
            "-R", "0.0", 
            "-P", "0.0",
            "-Y", "0.0", # Yaw (in radians, e.g., 1.57 for 90 degrees)
        ],
    )

    gz_ros2_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo"
        ],
    )

    ros_gz_image_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        arguments=["/camera/image_raw"]
    )

    return LaunchDescription([
        libgl_software,
        model_arg,
        world_name_arg,
        gazebo_resource_path,
        ign_resource_path,
        ign_plugin_path,
        gz_plugin_path,
        robot_state_publisher_node,
        gazebo,
        gz_spawn_entity,
        gz_ros2_bridge,
        ros_gz_image_bridge
    ])