from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    def arg(name):
        return LaunchConfiguration(name)

    def num(name):
        return ParameterValue(LaunchConfiguration(name), value_type=float)

    return LaunchDescription([
        DeclareLaunchArgument('output_mode', default_value='jtc',
                              choices=['jtc', 'pid']),
        DeclareLaunchArgument('target_topic', default_value='/hand_target'),
        DeclareLaunchArgument('rate_hz', default_value='50.0'),
        DeclareLaunchArgument('max_velocity', default_value='2.0'),
        DeclareLaunchArgument('input_timeout', default_value='0.3'),
        Node(package='dg5f_tutorial', executable='hand_command_bridge',
             parameters=[{'output_mode': arg('output_mode'),
                          'rate_hz': num('rate_hz'),
                          'max_velocity': num('max_velocity'),
                          'input_timeout': num('input_timeout')}],
             remappings=[('hand_target', arg('target_topic'))], output='screen'),
    ])
