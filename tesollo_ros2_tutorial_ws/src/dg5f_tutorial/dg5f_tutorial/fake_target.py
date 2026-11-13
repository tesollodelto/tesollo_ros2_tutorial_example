import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState

FLEX = [f'rj_dg_{f}_{j}' for f in range(2, 6) for j in (3, 4)]


class FakeTarget(Node):
    """리타겟팅 노드 대신 손가락을 천천히 쥐었다 펴는 목표를 30 Hz로 발행합니다."""
    """ Instead of retargeting node, it publishes a target that slowly closes and opens the fingers at 30 Hz. """

    def __init__(self):
        super().__init__('fake_target')
        self.pub = self.create_publisher(JointState, 'hand_target', 10)
        self.t0 = self.get_clock().now()
        self.create_timer(1.0 / 30.0, self.on_timer)

    def on_timer(self):
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        q = 0.45 * (1.0 - math.cos(2.0 * math.pi * 0.25 * t))  # 0~0.9 rad, 4 sec
        msg = JointState(name=FLEX, position=[q] * len(FLEX))
        msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FakeTarget()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
