#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from builtin_interfaces.msg import Duration

class SliderControl(Node):
    def __init__(self):
        super().__init__("slider_control")
        self.arm_pub_ = self.create_publisher(JointTrajectory, "arm_controller/joint_trajectory", 10)
        self.gripper_pub_ = self.create_publisher(JointTrajectory, "gripper_controller/joint_trajectory", 10)
        self.sub_ = self.create_subscription(JointState, "joint_commands", self.sliderCallback, 10)
        self.get_logger().info("Slider Control Node started")

    def sliderCallback(self, msg):
        if not msg.name or not msg.position:
            return

        joint_map = dict(zip(msg.name, msg.position))

        arm_joints = ["panda_joint1", "panda_joint2", "panda_joint3", "panda_joint4", "panda_joint5", "panda_joint6", "panda_joint7"]
        if all(j in joint_map for j in arm_joints):
            arm_msg = JointTrajectory()
            arm_msg.joint_names = arm_joints
            arm_goal = JointTrajectoryPoint()
            arm_goal.positions = [float(joint_map[j]) for j in arm_joints]
            arm_goal.time_from_start = Duration(sec=0, nanosec=100_000_000)
            arm_msg.points.append(arm_goal)
            self.arm_pub_.publish(arm_msg)

        if "panda_finger_joint1" in joint_map:
            gripper_msg = JointTrajectory()
            gripper_msg.joint_names = ["panda_finger_joint1", "panda_finger_joint2"]
            f1 = float(joint_map["panda_finger_joint1"])
            f2 = float(joint_map.get("panda_finger_joint2", f1))
            gripper_goal = JointTrajectoryPoint()
            gripper_goal.positions = [f1, f2]
            gripper_goal.time_from_start = Duration(sec=0, nanosec=100_000_000)
            gripper_msg.points.append(gripper_goal)
            self.gripper_pub_.publish(gripper_msg)

def main():
    rclpy.init()
    simple_publisher = SliderControl()
    try:
        rclpy.spin(simple_publisher)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        simple_publisher.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()