#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
import cv2
import numpy as np
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import String
from cv_bridge import CvBridge
import tf2_ros
import tf_transformations

# Minimum contour area (pixels) to consider a detection valid
MIN_CONTOUR_AREA = 100


class ColorDetector(Node):
    def __init__(self):
        super().__init__('color_detector')

        # Subscriber — camera image
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)

        # Subscriber — camera info (to get real intrinsics)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 1)

        # Publisher — detected object coordinates in robot base frame
        self.coords_pub = self.create_publisher(String, '/color_coordinates', 10)

        # OpenCV bridge
        self.bridge = CvBridge()

        # TF2 setup
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Camera intrinsics — computed from CameraInfo or fallback defaults.
        # Camera: 640×320, horizontal_fov=1.0 rad
        #   fx = (width/2) / tan(hfov/2)  = 320 / tan(0.5) ≈ 574.1
        #   fy = fx (square pixels assumed by Gazebo)
        #   cx = width/2  = 320
        #   cy = height/2 = 160
        self.fx = 574.1
        self.fy = 574.1
        self.cx = 320.0
        self.cy = 160.0
        self.intrinsics_received = False

        # Assumed depth (m) of objects in the camera frame.
        # Camera is fixed at (0.6, 0, 1.0) m above panda_link0, pointing
        # straight down (pitch ≈ π/2).  Objects rest on the table at ~0.04 m
        # height → ~0.96 m below the camera → depth ≈ 0.96 m in camera Z.
        self.object_depth = 0.96

        self.get_logger().info("Color Detector Node Started with TF2 lookup transform")

    # ------------------------------------------------------------------ #
    #  Camera-info callback: grab real intrinsics once and unsubscribe    #
    # ------------------------------------------------------------------ #
    def camera_info_callback(self, msg: CameraInfo):
        if self.intrinsics_received:
            return
        k = msg.k  # 3×3 row-major
        if k[0] > 0.0:
            self.fx = k[0]
            self.fy = k[4]
            self.cx = k[2]
            self.cy = k[5]
            self.intrinsics_received = True
            self.get_logger().info(
                f"Camera intrinsics received: fx={self.fx:.1f} fy={self.fy:.1f} "
                f"cx={self.cx:.1f} cy={self.cy:.1f}"
            )
            # Unsubscribe — we only need these once
            self.destroy_subscription(self.info_sub)

    # ------------------------------------------------------------------ #
    #  Main image callback                                                 #
    # ------------------------------------------------------------------ #
    def image_callback(self, msg: Image):
        try:
            # Convert ROS Image → OpenCV BGR
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")
            return

        # Convert to HSV for colour segmentation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # ---- HSV colour ranges -----------------------------------------
        # Tuned for bright solid-colour objects in Gazebo's default lighting.
        # Red wraps around the HSV hue axis → use two ranges merged.
        color_ranges = {
            "R": [
                (np.array([0,   120,  70]), np.array([10,  255, 255])),
                (np.array([170, 120,  70]), np.array([180, 255, 255])),
            ],
            "G": [
                (np.array([50,  150, 150]), np.array([80,  255, 255])),
            ],
            "B": [
                (np.array([100, 150, 150]), np.array([130, 255, 255])),
            ],
        }
        # ---------------------------------------------------------------

        # Look up the transform once per frame (re-use if valid)
        T = self._get_transform("panda_link0", "camera_link_optical")

        for color_id, ranges in color_ranges.items():
            # Build combined mask (handles multi-range like red)
            mask = None
            for (lower, upper) in ranges:
                m = cv2.inRange(hsv, lower, upper)
                mask = m if mask is None else cv2.bitwise_or(mask, m)

            # Morphological noise removal
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                continue

            # Pick the largest contour for this colour
            cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(cnt) < MIN_CONTOUR_AREA:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            px, py = x + w // 2, y + h // 2  # pixel centre of object

            # Draw bounding box + label
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(frame, color_id, (x, max(y - 10, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # ---------- pixel → camera optical frame 3-D point ----------
            # Standard pinhole back-projection:
            #   Xc = (px - cx) * Z / fx
            #   Yc = (py - cy) * Z / fy
            #   Zc = Z  (depth along optical axis)
            Z = self.object_depth
            Xc = (px - self.cx) * Z / self.fx
            Yc = (py - self.cy) * Z / self.fy

            if T is None:
                continue  # no transform yet — skip publishing

            # Transform to panda_link0 frame
            pt_cam = np.array([Xc, Yc, Z, 1.0])
            pt_base = T @ pt_cam

            # Publish: "COLOR_ID,x,y,z"
            msg_str = (f"{color_id},"
                       f"{pt_base[0]:.3f},"
                       f"{pt_base[1]:.3f},"
                       f"{pt_base[2]:.3f}")
            self.coords_pub.publish(String(data=msg_str))
            self.get_logger().info(f"Detected {color_id}: {msg_str}")

        # Show image (non-blocking)
        try:
            cv2.namedWindow("Color Detection", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Color Detection", 640, 320)
            cv2.imshow("Color Detection", frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().warn(f"OpenCV display error: {e}")

    # ------------------------------------------------------------------ #
    #  Helper: look up transform and return 4×4 matrix (or None)          #
    # ------------------------------------------------------------------ #
    def _get_transform(self, target_frame: str, source_frame: str):
        try:
            t = self.tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.1))  # short timeout — non-blocking

            trans = np.array([
                t.transform.translation.x,
                t.transform.translation.y,
                t.transform.translation.z,
            ])
            rot = [
                t.transform.rotation.x,
                t.transform.rotation.y,
                t.transform.rotation.z,
                t.transform.rotation.w,
            ]
            T = tf_transformations.quaternion_matrix(rot)
            T[:3, 3] = trans
            return T

        except (tf2_ros.LookupException,
                tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException) as e:
            self.get_logger().warn(f"TF lookup failed: {e}", throttle_duration_sec=5.0)
            return None
        except Exception as e:
            self.get_logger().error(f"Unexpected TF error: {e}")
            return None


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
