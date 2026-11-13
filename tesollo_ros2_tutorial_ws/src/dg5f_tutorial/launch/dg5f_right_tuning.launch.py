from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import xacro

NS = 'dg5f_right'


def make_nodes(context):
    hw = LaunchConfiguration('hardware').perform(context)
    yaml = LaunchConfiguration('controllers_file').perform(context)
    ctrl = LaunchConfiguration('controller').perform(context)
    if hw == 'real':
        urdf = FindPackageShare('dg5f_driver').perform(context) + \
            '/urdf/dg5f_right_ros2_control.xacro'
        mappings = {
            'delto_ip': LaunchConfiguration('delto_ip').perform(context),
            'delto_port': LaunchConfiguration('delto_port').perform(context)}
    else:  # mock_effort
        urdf = FindPackageShare('dg5f_tutorial').perform(context) + \
            '/urdf/dg5f_right_mock_effort.xacro'
        mappings = {}
    description = xacro.process_file(urdf, mappings=mappings).toxml()
    cm = f'/{NS}/controller_manager'
    return [
        Node(package='controller_manager', executable='ros2_control_node',
             namespace=NS, parameters=[yaml], output='screen',
             remappings=[('~/robot_description', f'/{NS}/robot_description')]),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             namespace=NS, parameters=[{'robot_description': description}]),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster', '-c', cm]),
        Node(package='controller_manager', executable='spawner',
             arguments=[ctrl, '-c', cm]),
    ]


def generate_launch_description():
    default_yaml = FindPackageShare('dg5f_tutorial').find('dg5f_tutorial') + \
        '/config/dg5f_right_controller_tuned.yaml'
    return LaunchDescription([
        DeclareLaunchArgument('hardware', default_value='mock_effort',
                              choices=['mock_effort', 'real']),
        DeclareLaunchArgument('controllers_file', default_value=default_yaml),
        DeclareLaunchArgument('controller', default_value='dg5f_right_controller'),
        DeclareLaunchArgument('delto_ip', default_value='169.254.186.72'),
        DeclareLaunchArgument('delto_port', default_value='502'),
        OpaqueFunction(function=make_nodes),
    ])
