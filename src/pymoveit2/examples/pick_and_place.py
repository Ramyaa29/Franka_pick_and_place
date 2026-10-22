#!/usr/bin/env python3
"""
Pick and place node combining Cartesian and joint-space moves with smooth joint transitions.
Supports dynamic command inputs via /robot_command (START, STOP, PICK_R, PICK_G, PICK_B, RESET).
Publishes state feedback on /robot_status.
"""

from threading import Thread, Lock
import math
import time
import json
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from std_msgs.msg import String

from pymoveit2 import MoveIt2, GripperInterface
from pymoveit2.robots import panda


class PickAndPlace(Node):
    def __init__(self):
        super().__init__("pick_and_place")

        # Parameters
        self.declare_parameter("target_color", "")
        self.target_color = self.get_parameter("target_color").value.upper()

        self.declare_parameter("auto_start", False)
        self.auto_start = bool(self.get_parameter("auto_start").value)

        self.declare_parameter("approach_offset", 0.215)
        self.approach_offset = float(
            self.get_parameter("approach_offset").value
        )

        # State management
        self.latest_coords = {}  # {'R': [x, y, z], 'G': [x, y, z], 'B': [x, y, z]}
        self.robot_state = "IDLE"  # "IDLE", "RUNNING", "STOPPED"
        self.current_action = "Robot ready at start posture"
        self.is_stopped = False
        self.current_target = None
        self.auto_started = False
        self.worker_thread = None
        self.worker_lock = Lock()

        self.callback_group = ReentrantCallbackGroup()

        # Arm MoveIt2 interface
        self.moveit2 = MoveIt2(
            node=self,
            joint_names=panda.joint_names(),
            base_link_name=panda.base_link_name(),
            end_effector_name=panda.end_effector_name(),
            group_name=panda.MOVE_GROUP_ARM,
            callback_group=self.callback_group,
        )

        # Set lower velocity & acceleration for smooth motion
        self.moveit2.max_velocity = 0.1
        self.moveit2.max_acceleration = 0.1

        # Gripper interface
        self.gripper = GripperInterface(
            node=self,
            gripper_joint_names=panda.gripper_joint_names(),
            open_gripper_joint_positions=panda.OPEN_GRIPPER_JOINT_POSITIONS,
            closed_gripper_joint_positions=panda.CLOSED_GRIPPER_JOINT_POSITIONS,
            gripper_group_name=panda.MOVE_GROUP_GRIPPER,
            callback_group=self.callback_group,
            gripper_command_action_name="gripper_action_controller/gripper_cmd",
        )

        # Subscribers
        self.coords_sub = self.create_subscription(
            String, "/color_coordinates", self.coords_callback, 10, callback_group=self.callback_group
        )
        self.cmd_sub = self.create_subscription(
            String, "/robot_command", self.command_callback, 10, callback_group=self.callback_group
        )

        # Publishers
        self.status_pub = self.create_publisher(
            String, "/robot_status", 10
        )

        # Periodic status timer (1 Hz)
        self.status_timer = self.create_timer(1.0, self.publish_status, callback_group=self.callback_group)

        # Predefined joint positions (in radians)
        self.start_joints = [0.0, 0.0, 0.0, -0.1, 0.0, 0.0, math.radians(-125.0)]
        self.home_joints  = [0.0, 0.0, 0.0, math.radians(-90.0), 0.0, math.radians(92.0), math.radians(50.0)]
        self.drop_joints  = [math.radians(-155.0), math.radians(30.0), math.radians(-20.0),
                             math.radians(-124.0), math.radians(44.0), math.radians(163.0), math.radians(7.0)]

        self.get_logger().info("PickAndPlace node initialized. Waiting for executor to start motion...")

    def initialize_robot(self):
        """Move robot to initial start posture once executor is spinning."""
        try:
            # Give executor a moment to receive first joint states
            time.sleep(1.0)
            self.get_logger().info("Moving to initial start joint configuration...")
            self.current_action = "Moving to start posture..."
            self.publish_status()
            self.moveit2.move_to_configuration(self.start_joints)
            self.moveit2.wait_until_executed()
            self.current_action = "Robot ready at start posture"
            self.get_logger().info("Robot initialized at start position. Listening for GUI commands on /robot_command.")
            self.publish_status()
        except Exception as e:
            self.get_logger().error(f"Error during initialization: {e}")

    def publish_status(self):
        """Publish real-time status as a JSON string on /robot_status."""
        try:
            status_data = {
                "state": self.robot_state,
                "action": self.current_action,
                "is_stopped": self.is_stopped,
                "robot_enabled": not self.is_stopped,
                "target": self.current_target,
                "coords": self.latest_coords
            }
            msg = String()
            msg.data = json.dumps(status_data)
            self.status_pub.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Error publishing status: {e}")

    def coords_callback(self, msg: String):
        """Receive live color detections from /color_coordinates."""
        try:
            parts = msg.data.split(",")
            if len(parts) == 4:
                color_id = parts[0].strip().upper()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                self.latest_coords[color_id] = [x, y, z]

                # If auto_start is configured and matches target_color
                if self.auto_start and not self.auto_started and (color_id == self.target_color):
                    self.auto_started = True
                    self.get_logger().info(f"Auto-start triggered for {color_id}")
                    self.dispatch_pick(color_id)
        except Exception as e:
            self.get_logger().error(f"Error parsing /color_coordinates: {e}")

    def command_callback(self, msg: String):
        """Receive user GUI commands on /robot_command."""
        cmd = msg.data.strip().upper()
        self.get_logger().info(f"Received /robot_command: {cmd}")

        if cmd == "STOP":
            self.is_stopped = True
            self.robot_state = "STOPPED"
            self.current_action = "Emergency Stop: Robot paused by user"
            try:
                self.moveit2.cancel_execution()
            except Exception:
                pass
            self.get_logger().warn("EMERGENCY STOP ACTIVATED!")
            self.publish_status()

        elif cmd == "START":
            self.is_stopped = False
            if self.robot_state == "STOPPED":
                self.robot_state = "IDLE"
                self.current_action = "Robot enabled / Ready"
            self.get_logger().info("ROBOT ENABLED / STARTED")
            self.publish_status()

        elif cmd in ["PICK_R", "PICK_RED"]:
            self.dispatch_pick("R")

        elif cmd in ["PICK_G", "PICK_GREEN"]:
            self.dispatch_pick("G")

        elif cmd in ["PICK_B", "PICK_BLUE"]:
            self.dispatch_pick("B")

        elif cmd in ["RESET", "HOME"]:
            self.dispatch_reset()

        else:
            self.get_logger().warn(f"Unknown command: {cmd}")

    def dispatch_pick(self, color: str):
        """Dispatch a pick-and-place task in a separate worker thread."""
        if self.is_stopped:
            self.is_stopped = False
            self.robot_state = "IDLE"
            self.get_logger().info(f"Auto-starting robot from STOP for picking {color}")

        with self.worker_lock:
            if self.worker_thread is not None and self.worker_thread.is_alive():
                self.get_logger().warn("Robot is currently busy executing another task.")
                return
            self.worker_thread = Thread(target=self.execute_pick_sequence, args=(color,), daemon=True)
            self.worker_thread.start()

    def dispatch_reset(self):
        """Dispatch a reset task in a separate worker thread."""
        if self.is_stopped:
            self.is_stopped = False
            self.robot_state = "IDLE"
            self.get_logger().info("Reset requested from STOPPED state: clearing stop flag and recovering.")

        with self.worker_lock:
            if self.worker_thread is not None and self.worker_thread.is_alive():
                self.get_logger().warn("Robot is currently busy executing another task.")
                return
            self.worker_thread = Thread(target=self.execute_reset, daemon=True)
            self.worker_thread.start()

    def execute_pick_sequence(self, color: str):
        """Full pick-and-place execution sequence."""
        try:
            self.robot_state = "RUNNING"
            self.current_target = color
            self.current_action = f"Waiting for {color} cube coordinates..."
            self.publish_status()

            # Wait up to 5 seconds for target coordinates if not yet received
            start_wait = time.time()
            while color not in self.latest_coords and (time.time() - start_wait < 5.0):
                if self.is_stopped:
                    self.robot_state = "STOPPED"
                    self.current_action = "Stopped during coordinate wait"
                    self.publish_status()
                    return
                time.sleep(0.1)

            if color not in self.latest_coords:
                self.get_logger().error(f"Coordinates for target {color} not found!")
                self.robot_state = "IDLE"
                self.current_action = f"Error: No vision coordinates detected for {color}"
                self.publish_status()
                return

            target_coords = list(self.latest_coords[color])
            self.get_logger().info(f"Target {color} locked at: [{target_coords[0]:.3f}, {target_coords[1]:.3f}, {target_coords[2]:.3f}]")

            pick_position = [target_coords[0], target_coords[1], 0.35]
            quat_xyzw = [0.0, 1.0, 0.0, 0.0]

            # 1. Move to home joint configuration and open gripper
            if self.is_stopped: return
            self.current_action = f"1/6 Moving to home posture ({color})"
            self.publish_status()
            self.gripper.open()
            self.moveit2.move_to_configuration(self.home_joints)
            self.moveit2.wait_until_executed()
            self.gripper.wait_until_executed()

            # 2. Move above target (Cartesian)
            if self.is_stopped: return
            self.current_action = f"2/6 Aligning above {color} cube [{target_coords[0]:.2f}, {target_coords[1]:.2f}]"
            self.publish_status()
            self.moveit2.move_to_pose(position=pick_position, quat_xyzw=quat_xyzw)
            self.moveit2.wait_until_executed()

            # 3. Lower down in Cartesian space to approach object
            if self.is_stopped: return
            self.current_action = f"3/6 Descending to grasp {color} cube"
            self.publish_status()

            approach_position = [
                pick_position[0],
                pick_position[1],
                pick_position[2] - self.approach_offset
            ]
            self.moveit2.move_to_pose(
                position=approach_position,
                quat_xyzw=quat_xyzw,
                cartesian=True
            )
            self.moveit2.wait_until_executed()

            # 4. Close gripper on object
            if self.is_stopped: return
            self.current_action = f"4/6 Gripping {color} cube"
            self.publish_status()
            self.gripper.close()
            self.gripper.wait_until_executed()
            time.sleep(0.5)  # Allow contact forces and friction to settle

            # 4b. RETREAT / LIFT STEP: Lift vertically in Cartesian space before any joint-space motion!
            if self.is_stopped: return
            self.current_action = f"4b/6 Lifting {color} cube vertically above table"
            self.publish_status()
            lift_position = [approach_position[0], approach_position[1], pick_position[2]]
            self.moveit2.move_to_pose(
                position=lift_position,
                quat_xyzw=quat_xyzw,
                cartesian=True
            )
            self.moveit2.wait_until_executed()
            time.sleep(0.2)

            # 5. Move to home joint configuration then to drop configuration (now safe from table collision)
            if self.is_stopped: return
            self.current_action = f"5/6 Transporting {color} cube to trash bin"
            self.publish_status()
            self.moveit2.move_to_configuration(self.home_joints)
            self.moveit2.wait_until_executed()

            if self.is_stopped: return
            self.moveit2.move_to_configuration(self.drop_joints)
            self.moveit2.wait_until_executed()

            # 6. Open gripper to release into bin, then close
            self.gripper.open()
            self.gripper.wait_until_executed()
            time.sleep(0.5)
            self.gripper.close()
            self.gripper.wait_until_executed()

            # 7. Return to start joint configuration
            if self.is_stopped: return
            self.current_action = f"6/6 Returning to start configuration"
            self.publish_status()
            self.moveit2.move_to_configuration(self.start_joints)
            self.moveit2.wait_until_executed()

            self.robot_state = "IDLE"
            self.current_target = None
            self.current_action = f"Successfully picked and placed {color} cube! Ready for next command."
            self.get_logger().info(f"Pick-and-place sequence for {color} complete!")
            self.publish_status()

        except Exception as e:
            self.get_logger().error(f"Error during pick-and-place: {e}")
            self.robot_state = "IDLE"
            self.current_action = f"Error during execution: {e}"
            self.publish_status()

    def execute_reset(self):
        """Move robot safely to start configuration."""
        try:
            self.robot_state = "RUNNING"
            self.current_action = "Resetting: Opening gripper and returning to start posture"
            self.publish_status()

            self.gripper.open()
            self.gripper.wait_until_executed()
            self.gripper.close()
            self.gripper.wait_until_executed()

            self.moveit2.move_to_configuration(self.start_joints)
            self.moveit2.wait_until_executed()

            self.robot_state = "IDLE"
            self.current_action = "Robot reset to start posture. Ready."
            self.publish_status()
        except Exception as e:
            self.get_logger().error(f"Error during reset: {e}")
            self.robot_state = "IDLE"
            self.current_action = f"Error during reset: {e}"
            self.publish_status()


def main():
    rclpy.init()
    node = PickAndPlace()

    executor = rclpy.executors.MultiThreadedExecutor(4)
    executor.add_node(node)

    # Launch initial robot posture in worker thread while executor is spinning
    Thread(target=node.initialize_robot, daemon=True).start()

    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    except Exception as e:
        node.get_logger().error(f"Executor error: {e}")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
