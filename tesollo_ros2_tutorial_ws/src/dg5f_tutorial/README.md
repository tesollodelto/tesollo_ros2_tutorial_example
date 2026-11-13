# dg5f_tutorial

**English** | [한국어](README_KR.md)

Example package for the TESOLLO technical guide "Tutorial: From ROS 2 Installation to DG-5F Control".
It contains Python nodes, launch files, and controller configuration for controlling the DELTO DG-5F right hand through the ros2_control driver (`dg5f_driver`).
The code blocks in the guide and the files in this repository are identical.

- Guide: [TESOLLO Technical Guides](https://www.tesollo.com/ko/resources/category/technical-guides)
- Driver: [tesollo_ros2](https://github.com/tesollodelto/tesollo_ros2)

## Contents

| File | Guide section | Description |
|---|---|---|
| `dg5f_tutorial/grasp_demo.py` | Step 8 | Runs a pose sequence (open → grasp → open) as a single `FollowJointTrajectory` action |
| `dg5f_tutorial/hand_command_bridge.py` | Step 9 | Bridge that validates joint targets from an upstream node (retargeting, etc.) and forwards them to the controller |
| `dg5f_tutorial/fake_target.py` | Step 10 | Test input used in place of a retargeting node |
| `launch/hand_bridge.launch.py` | Step 10 | Launches the bridge (arguments for output mode, input topic, publish rate, command rate limit, and timeout) |
| `launch/dg5f_right_tuning.launch.py` | Advanced B | Runs the real hand or the gain-check mock with a custom YAML |
| `urdf/dg5f_right_mock_effort.xacro` | Advanced B | Gain-check mock with an effort command interface |
| `config/dg5f_right_controller_tuned.yaml` | Advanced B–D | JTC configuration that explicitly sets the output limits and the anti-windup method |

## Verified Environment

| Item | Version |
|---|---|
| OS / ROS 2 | Ubuntu 24.04, ROS 2 Jazzy |
| ros2_control / ros2_controllers / control_toolbox | 4.45.2 / 4.40.1 / 4.11.0 (at the time of writing), 4.48.1 / 4.42.1 / 4.11.1 (re-verified 2026-11, mock hardware) |
| TESOLLO packages | tesollo_ros2 commit `7379063` (dg5f_ros2 `9e9af12`, dg_hardware `c068fe7`, dg_tcp_comm `4b937d3`) |

Package names and controller parameters may differ on other ROS 2 distributions.

## Prerequisites

ROS 2 Jazzy, ros2_control, and the DG-5F driver must be installed (Steps 1–2 of the guide).

```bash
sudo apt install ros-jazzy-ros2-control ros-jazzy-ros2-controllers ros-jazzy-xacro

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/tesollodelto/tesollo_ros2.git
cd tesollo_ros2
git checkout 7379063a4fa9      # optional: pin to the commit the guide was verified against
git submodule update --init dg5f_ros2 dg_common/dg_tcp_comm dg_common/dg_hardware

cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to dg5f_driver dg5f_description
```

## Build

Build in a terminal where the driver workspace has been sourced.

```bash
mkdir -p ~/hand_ws/src && cd ~/hand_ws/src
git clone <repository URL> dg5f_tutorial

source ~/ros2_ws/install/setup.bash
cd ~/hand_ws && colcon build --symlink-install
source install/setup.bash
```

In every new terminal after that, run `source ~/ros2_ws/install/setup.bash` and then `source ~/hand_ws/install/setup.bash`, in that order.

## Usage

### Checking with mock hardware (no device)

```bash
# Terminal 1
ros2 launch dg5f_driver dg5f_right_mock.launch.py

# Terminal 2: run the pose sequence → "result: 0 Goal successfully reached!"
ros2 run dg5f_tutorial grasp_demo
```

Check the bridge and the test input as follows.

```bash
# Terminal 2: confirm the "loaded limits for 20 joints" output
ros2 launch dg5f_tutorial hand_bridge.launch.py
# Terminal 3
ros2 run dg5f_tutorial fake_target
# Terminal 4: confirm that the joint values move back and forth within 0–0.9 rad
ros2 topic echo /dg5f_right/joint_states
```

### Gain-check mock (effort commands)

The joints do not move; only the controller output can be observed. Stop the mock launch above first.

```bash
ros2 launch dg5f_tutorial dg5f_right_tuning.launch.py hardware:=mock_effort
```

### Real hand

Set the hand to developer mode and EtherNET, connect the network, and then run the following (Steps 4–5 of the guide).
Start with a low command rate limit at first.

```bash
# Terminal 1: driver (to apply a custom YAML, use dg5f_right_tuning.launch.py hardware:=real)
ros2 launch dg5f_driver dg5f_right_driver.launch.py delto_ip:=169.254.186.72

# Terminal 2: bridge
ros2 launch dg5f_tutorial hand_bridge.launch.py max_velocity:=1.0 \
  target_topic:=/retarget/joint_command
```

When using the unified PID controller, launch the driver with `dg5f_right_pid_all_controller.launch.py` and pass `output_mode:=pid` to the bridge.

## Bridge Input Contract

| Item | Contract |
|---|---|
| Topic | `/hand_target` (change it with the `target_topic` launch argument) |
| Message | `sensor_msgs/msg/JointState` |
| Joint identification | Joint names in the `name` field (`rj_dg_F_J`). Order does not matter, and you may send only a subset of the joints. Omitted joints keep their previous target. |
| Values | `position` field, in rad. Out-of-range values are clamped to the URDF limits. |
| Rejected messages | Messages in which `name` and `position` differ in length, a name is duplicated, NaN or Inf is present, or none of the names is a registered joint |

| Launch argument | Default | Meaning |
|---|---|---|
| `output_mode` | `jtc` | `jtc`: the JTC `joint_trajectory` topic, `pid`: the `rj_dg_pospid/reference` topic |
| `target_topic` | `/hand_target` | Target topic from the upstream node |
| `rate_hz` | `50.0` | Command publish rate [Hz] |
| `max_velocity` | `2.0` | Upper limit on the command rate of change [rad/s] |
| `input_timeout` | `0.3` | Publishing stops if no valid input arrives within this time [s] |

## Notes

- The bridge assumes a single command path. Make sure no other node (an action client, MoveIt 2, etc.) sends commands to the same controller at the same time.
- The bridge initializes to the current pose only once, at startup. If the joints were moved through another path while the bridge was running, restart the bridge before connecting the input.
- Unit errors (sending deg as rad) cannot be detected. Units, joint mapping, and direction signs must be handled in the upstream node.
- The ±3.0 output limit in `config/dg5f_right_controller_tuned.yaml` is an example value for illustrating the control behavior. It does not guarantee an upper bound on the actual contact force or grasp force; the value to apply must be verified for your model and task conditions.
- Provide a means of cutting power to the hand that is independent of the software. The normal shutdown procedure does not run when the process is force-killed or communication is lost.

## Tests

```bash
cd ~/hand_ws
colcon test --packages-select dg5f_tutorial
colcon test-result --verbose
```

## License

BSD-3-Clause. See [LICENSE](LICENSE).
