from setuptools import find_packages, setup

package_name = 'dg5f_tutorial'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/hand_bridge.launch.py',
            'launch/dg5f_right_tuning.launch.py']),
        ('share/' + package_name + '/config',
            ['config/dg5f_right_controller_tuned.yaml']),
        ('share/' + package_name + '/urdf',
            ['urdf/dg5f_right_mock_effort.xacro']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='TESOLLO',
    maintainer_email='support@tesollo.com',
    description='DG-5F ROS 2 tutorial nodes',
    license='BSD-3-Clause',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'grasp_demo = dg5f_tutorial.grasp_demo:main',
            'hand_command_bridge = dg5f_tutorial.hand_command_bridge:main',
            'fake_target = dg5f_tutorial.fake_target:main',
        ],
    },
)
