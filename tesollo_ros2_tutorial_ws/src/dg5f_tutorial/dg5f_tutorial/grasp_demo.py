from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectoryPoint

JOINTS = [f'rj_dg_{f}_{j}' for f in range(1, 6) for j in range(1, 5)]
OPEN = [0.0] * 20
GRASP = [0.0, -0.6, 0.5, 0.5,   # 엄지 Thumb
         0.0, 0.6, 0.9, 0.9,    # 검지 Index
         0.0, 0.6, 0.9, 0.9,    # 중지 Middle
         0.0, 0.6, 0.9, 0.9,    # 약지 Ring
         0.0, 0.0, 0.9, 0.9]    # 소지 Pinky


class GraspDemo(Node):
    def __init__(self):
        super().__init__('grasp_demo')
        self.client = ActionClient(
            self, FollowJointTrajectory,
            '/dg5f_right/dg5f_right_controller/follow_joint_trajectory')

    def send(self, poses_and_times, margin=5.0):
        """자세 시퀀스를 하나의 궤적으로 실행합니다. 파지 성공 여부는 판정하지 않습니다."""
        """ Executes a sequence of poses as a single trajectory.
        Does not judge whether the grasp was successful. """
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = JOINTS
        for pose, t in poses_and_times:
            p = JointTrajectoryPoint(positions=pose)
            p.time_from_start = Duration(sec=int(t), nanosec=int(t % 1 * 1e9))
            goal.trajectory.points.append(p)
        if not self.client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('action server not available (driver running?)')
            return False
        send_future = self.client.send_goal_async(
            goal, feedback_callback=self.on_feedback)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        handle = send_future.result()
        if handle is None or not handle.accepted:
            self.get_logger().error('goal rejected or no response')
            return False
        result_future = handle.get_result_async()
        duration = poses_and_times[-1][1] + margin
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=duration)
        if not result_future.done():
            self.get_logger().error(f'no result within {duration:.1f} s, canceling goal')
            cancel_future = handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=2.0)
            return False
        result = result_future.result().result
        self.get_logger().info(f'result: {result.error_code} {result.error_string}')
        return result.error_code == FollowJointTrajectory.Result.SUCCESSFUL

    def on_feedback(self, msg):
        err = max(abs(e) for e in msg.feedback.error.positions)
        self.get_logger().info(f'max position error {err:.3f} rad',
                               throttle_duration_sec=0.5)


def main():
    rclpy.init()
    node = GraspDemo()
    node.send([(OPEN, 1.0), (GRASP, 3.0), (GRASP, 4.0), (OPEN, 6.0)])
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
