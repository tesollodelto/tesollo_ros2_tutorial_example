import math
import xml.etree.ElementTree as ET

from builtin_interfaces.msg import Duration
from control_msgs.msg import MultiDOFCommand
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

JOINTS = [f'rj_dg_{f}_{j}' for f in range(1, 6) for j in range(1, 5)]


class HandCommandBridge(Node):
    """상위 노드(리타겟팅 등)의 관절 목표를 검사하여 컨트롤러로 전달합니다."""

    """ Checks the joint targets from the upper node (retargeting, etc.)
    and passes them to the controller. """

    def __init__(self):
        super().__init__('hand_command_bridge')
        self.mode = self.declare_parameter('output_mode', 'jtc').value  # jtc | pid
        self.rate = float(self.declare_parameter('rate_hz', 50.0).value)
        self.max_vel = float(self.declare_parameter('max_velocity', 2.0).value)  # rad/s
        self.timeout = float(self.declare_parameter('input_timeout', 0.3).value)  # s
        if self.mode not in ('jtc', 'pid'):
            raise ValueError(f"output_mode must be 'jtc' or 'pid', got '{self.mode}'")
        for name, value in (('rate_hz', self.rate), ('max_velocity', self.max_vel),
                            ('input_timeout', self.timeout)):
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f'{name} must be a positive number, got {value}')

        self.limits = {}
        # every cycle command (starting from current pose)
        self.command = None      # 매 주기 발행하는 명령 (현재 자세에서 시작)
        # target requested by the upper node (after applying limits)
        self.target = None       # 상위 노드가 요청한 목표 (한계 적용 후)
        # timestamp of the last accepted target
        self.last_input = None   # 마지막으로 수락한 목표의 수신 시각

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, '/dg5f_right/robot_description',
                                 self.on_description, latched)
        self.create_subscription(JointState, '/dg5f_right/joint_states',
                                 self.on_state, 10)
        self.create_subscription(JointState, 'hand_target', self.on_target, 10)
        if self.mode == 'jtc':
            self.pub = self.create_publisher(
                JointTrajectory,
                '/dg5f_right/dg5f_right_controller/joint_trajectory', 10)
        else:
            self.pub = self.create_publisher(
                MultiDOFCommand, '/dg5f_right/rj_dg_pospid/reference', 10)
        self.create_timer(1.0 / self.rate, self.on_timer)

    def ready(self):
        return len(self.limits) == len(JOINTS) and self.command is not None

    def on_description(self, msg):
        limits = {}
        for j in ET.fromstring(msg.data).iter('joint'):
            lim = j.find('limit')
            name = j.get('name')
            if name in JOINTS and lim is not None:
                limits[name] = (float(lim.get('lower')), float(lim.get('upper')))
        self.limits = limits
        self.get_logger().info(f'loaded limits for {len(self.limits)} joints')

    def on_state(self, msg):
        if self.command is not None:
            return
        if len(msg.name) != len(msg.position) or not set(JOINTS) <= set(msg.name):
            return
        pos = dict(zip(msg.name, msg.position))
        current = [pos[n] for n in JOINTS]
        if not all(math.isfinite(q) for q in current):
            return
        # 현재 자세에서 출발: 명령과 목표를 모두 현재 자세로 초기화
        # Start from the current pose: initialize both command and target to the current pose
        self.command = list(current)
        self.target = list(current)
        self.get_logger().info('initialized from current joint state')

    def reject(self, reason):
        self.get_logger().warn(f'target rejected: {reason}', throttle_duration_sec=2.0)

    def on_target(self, msg):
        if not self.ready():
            self.reject('waiting for robot_description and joint_states')
            return
        if len(msg.name) != len(msg.position):
            self.reject('name and position lengths differ')
            return
        if len(set(msg.name)) != len(msg.name):
            self.reject('duplicate joint names')
            return
        goal = {n: q for n, q in zip(msg.name, msg.position) if n in self.limits}
        if not goal:
            self.reject('no known joint names')
            return
        if not all(math.isfinite(q) for q in goal.values()):
            self.reject('non-finite position')
            return
        unknown = set(msg.name) - set(goal)
        if unknown:
            self.get_logger().warn(f'ignoring unknown joints: {sorted(unknown)}',
                                   throttle_duration_sec=2.0)
        # 생략된 관절은 직전 목표를 유지하고, 모든 값을 URDF 한계 범위로 제한
        # Omitted joints retain the previous target, and all values are limited to the URDF range
        self.target = [
            min(max(goal.get(n, t), self.limits[n][0]), self.limits[n][1])
            for n, t in zip(JOINTS, self.target)]
        self.last_input = self.get_clock().now()

    def on_timer(self):
        if not self.ready() or self.last_input is None:
            return
        age = (self.get_clock().now() - self.last_input).nanoseconds * 1e-9
        if age > self.timeout:
            self.get_logger().warn('input timeout: holding last command',
                                   throttle_duration_sec=2.0)
            return
        step = self.max_vel / self.rate
        self.command = [c + max(-step, min(step, t - c))
                        for c, t in zip(self.command, self.target)]
        if self.mode == 'jtc':
            msg = JointTrajectory(joint_names=JOINTS)
            dt = 2.0 / self.rate
            msg.points = [JointTrajectoryPoint(
                positions=self.command,
                time_from_start=Duration(nanosec=int(dt * 1e9)))]
        else:
            msg = MultiDOFCommand(dof_names=JOINTS, values=self.command,
                                  values_dot=[0.0] * 20)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = HandCommandBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
