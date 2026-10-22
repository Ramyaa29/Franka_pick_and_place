#!/usr/bin/env python3
"""
Flask Web GUI for Franka Emika Panda Robot Pick-and-Place Control.
Provides live interactive controls:
- Pick Green, Pick Blue, Pick Red buttons
- Start Robot and Stop Robot (Emergency Stop)
- Live status telemetry & cube coordinates
- Live overhead camera feed
"""

import os
import sys
import json
import time
import threading
import numpy as np
import cv2

from flask import Flask, render_template, request, jsonify, Response

# ROS 2 imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

app = Flask(__name__)

# Global ROS 2 Bridge Node reference
bridge_node = None


class FlaskBridgeNode(Node):
    def __init__(self):
        super().__init__("flask_gui_bridge")
        self.bridge = CvBridge()
        self.frame_lock = threading.Lock()
        self.latest_frame_jpeg = None
        self.last_frame_time = 0.0

        self.status = {
            "state": "IDLE",
            "action": "Waiting for robot connection...",
            "is_stopped": False,
            "robot_enabled": True,
            "target": None,
            "coords": {
                "R": None,
                "G": None,
                "B": None
            },
            "last_command": "None"
        }

        # Publisher to send commands to pick_and_place node
        self.cmd_pub = self.create_publisher(String, "/robot_command", 10)

        # Subscribers
        self.status_sub = self.create_subscription(
            String, "/robot_status", self.status_callback, 10
        )
        self.coords_sub = self.create_subscription(
            String, "/color_coordinates", self.coords_callback, 10
        )
        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self.image_callback, 10
        )

        self.get_logger().info("Flask Bridge Node initialized and subscribed to topics.")

    def send_command(self, cmd: str):
        msg = String()
        msg.data = cmd.strip().upper()
        self.cmd_pub.publish(msg)
        self.status["last_command"] = cmd
        self.get_logger().info(f"Published to /robot_command: {msg.data}")

    def status_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.status["state"] = data.get("state", self.status["state"])
            self.status["action"] = data.get("action", self.status["action"])
            self.status["is_stopped"] = data.get("is_stopped", self.status["is_stopped"])
            self.status["robot_enabled"] = data.get("robot_enabled", not self.status["is_stopped"])
            self.status["target"] = data.get("target", self.status["target"])
            if "coords" in data and isinstance(data["coords"], dict):
                for k, v in data["coords"].items():
                    self.status["coords"][k] = v
        except Exception as e:
            self.get_logger().error(f"Error parsing status JSON: {e}")

    def coords_callback(self, msg: String):
        try:
            parts = msg.data.split(",")
            if len(parts) == 4:
                c = parts[0].strip().upper()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                self.status["coords"][c] = [round(x, 3), round(y, 3), round(z, 3)]
        except Exception:
            pass

    def image_callback(self, msg: Image):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            # Draw HUD info on frame
            h, w = cv_img.shape[:2]
            cv2.rectangle(cv_img, (10, 10), (310, 42), (20, 20, 20), -1)
            cv2.putText(
                cv_img,
                "OVERHEAD REALSENSE FEED",
                (18, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 180),
                2,
            )

            # Center target crosshair
            cx, cy = w // 2, h // 2
            cv2.drawMarker(cv_img, (cx, cy), (100, 100, 255), cv2.MARKER_CROSS, 20, 1)

            ret, jpeg = cv2.imencode(".jpg", cv_img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                with self.frame_lock:
                    self.latest_frame_jpeg = jpeg.tobytes()
                    self.last_frame_time = time.time()
        except Exception as e:
            self.get_logger().error(f"Error processing camera frame: {e}")

    def get_frame(self):
        with self.frame_lock:
            # If camera stream has not arrived or timed out, display a fallback canvas
            if self.latest_frame_jpeg is None or (time.time() - self.last_frame_time > 3.0):
                canvas = np.zeros((320, 640, 3), dtype=np.uint8)
                cv2.putText(
                    canvas,
                    "CAMERA STREAM INITIALIZING...",
                    (130, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (220, 220, 220),
                    2,
                )
                cv2.putText(
                    canvas,
                    "Listening on /camera/image_raw",
                    (170, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (120, 120, 120),
                    1,
                )
                ret, jpeg = cv2.imencode(".jpg", canvas)
                return jpeg.tobytes()
            return self.latest_frame_jpeg


def ros_spin_thread():
    """Background worker spinning the ROS 2 node."""
    global bridge_node
    rclpy.spin(bridge_node)


# ------------------- Flask Routes -------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    global bridge_node
    if bridge_node is None:
        return jsonify({"error": "ROS 2 bridge not ready"}), 503
    return jsonify(bridge_node.status)


@app.route("/api/command", methods=["POST"])
def send_command():
    global bridge_node
    if bridge_node is None:
        return jsonify({"error": "ROS 2 bridge not ready"}), 503

    data = request.get_json(force=True, silent=True) or {}
    command = data.get("command", "").strip().upper()

    valid_commands = [
        "START",
        "STOP",
        "PICK_R",
        "PICK_RED",
        "PICK_G",
        "PICK_GREEN",
        "PICK_B",
        "PICK_BLUE",
        "RESET",
        "HOME",
    ]

    if command not in valid_commands:
        return (
            jsonify(
                {
                    "error": f"Invalid command '{command}'. Valid: {valid_commands}"
                }
            ),
            400,
        )

    bridge_node.send_command(command)
    return jsonify({"success": True, "command": command})


def gen_frames():
    """Generator for MJPEG camera stream."""
    global bridge_node
    while True:
        if bridge_node is not None:
            frame = bridge_node.get_frame()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.06)  # ~16 FPS


@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def start_app():
    global bridge_node
    rclpy.init(args=None)
    bridge_node = FlaskBridgeNode()

    spin_thread = threading.Thread(target=ros_spin_thread, daemon=True)
    spin_thread.start()

    port = 5000
    print(f"\n========================================================")
    print(f"🚀 Franka Panda Flask GUI Server Starting...")
    print(f"👉 Local URL: http://localhost:{port}")
    print(f"👉 Network:   http://0.0.0.0:{port}")
    print(f"========================================================\n")

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    start_app()
