# dg5f_tutorial

TESOLLO 기술 가이드 「튜토리얼: ROS 2 설치부터 DG-5F 제어까지」의 예제 패키지입니다.
DELTO DG-5F 오른손을 ros2_control 드라이버(`dg5f_driver`)로 제어하는 Python 노드, 런치 파일, 컨트롤러 설정을 담고 있습니다.
문서의 코드 블록과 이 저장소의 파일은 내용이 같습니다.

- 가이드: [TESOLLO 기술 가이드](https://www.tesollo.com/ko/resources/category/technical-guides)
- 드라이버: [tesollo_ros2](https://github.com/tesollodelto/tesollo_ros2)

## 구성

| 파일 | 문서 위치 | 내용 |
|---|---|---|
| `dg5f_tutorial/grasp_demo.py` | 8단계 | 자세 시퀀스(펴기 → 쥐기 → 펴기)를 `FollowJointTrajectory` 액션 하나로 실행 |
| `dg5f_tutorial/hand_command_bridge.py` | 9단계 | 상위 노드(리타겟팅 등)의 관절 목표를 검사하여 컨트롤러로 전달하는 브리지 |
| `dg5f_tutorial/fake_target.py` | 10단계 | 리타겟팅 노드 대신 사용하는 테스트 입력 |
| `launch/hand_bridge.launch.py` | 10단계 | 브리지 실행 (출력 모드, 입력 토픽, 주기, 변화율, 타임아웃 인자) |
| `launch/dg5f_right_tuning.launch.py` | 심화 B | 사용자 정의 YAML로 실제 핸드 또는 이득 확인용 mock 실행 |
| `urdf/dg5f_right_mock_effort.xacro` | 심화 B | effort 명령 인터페이스를 가진 이득 확인용 mock |
| `config/dg5f_right_controller_tuned.yaml` | 심화 B~D | 출력 제한과 적분 포화 방지 방식을 명시한 JTC 설정 |

## 검토 환경

| 항목 | 버전 |
|---|---|
| OS / ROS 2 | Ubuntu 24.04, ROS 2 Jazzy |
| ros2_control / ros2_controllers / control_toolbox | 4.45.2 / 4.40.1 / 4.11.0 (문서 작성 시점), 4.48.1 / 4.42.1 / 4.11.1 (2026-11 재확인, mock 하드웨어) |
| TESOLLO 패키지 | tesollo_ros2 커밋 `7379063` (dg5f_ros2 `9e9af12`, dg_hardware `c068fe7`, dg_tcp_comm `4b937d3`) |

다른 ROS 2 배포판에서는 패키지 이름과 컨트롤러 파라미터가 다를 수 있습니다.

## 준비

ROS 2 Jazzy, ros2_control, DG-5F 드라이버가 설치되어 있어야 합니다(문서 1~2단계).

```bash
sudo apt install ros-jazzy-ros2-control ros-jazzy-ros2-controllers ros-jazzy-xacro

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/tesollodelto/tesollo_ros2.git
cd tesollo_ros2
git checkout 7379063a4fa9      # 선택: 문서를 검토한 커밋으로 고정
git submodule update --init dg5f_ros2 dg_common/dg_tcp_comm dg_common/dg_hardware

cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to dg5f_driver dg5f_description
```

## 빌드

드라이버 워크스페이스를 source한 터미널에서 빌드합니다.

```bash
mkdir -p ~/hand_ws/src && cd ~/hand_ws/src
git clone <저장소 주소> dg5f_tutorial

source ~/ros2_ws/install/setup.bash
cd ~/hand_ws && colcon build --symlink-install
source install/setup.bash
```

이후 새 터미널에서는 `source ~/ros2_ws/install/setup.bash`와 `source ~/hand_ws/install/setup.bash`를 차례로 실행합니다.

## 실행

### 장치 없이 mock 하드웨어로 확인

```bash
# 터미널 1
ros2 launch dg5f_driver dg5f_right_mock.launch.py

# 터미널 2: 자세 시퀀스 실행 → "result: 0 Goal successfully reached!"
ros2 run dg5f_tutorial grasp_demo
```

브리지와 테스트 입력은 다음과 같이 확인합니다.

```bash
# 터미널 2: "loaded limits for 20 joints" 출력 확인
ros2 launch dg5f_tutorial hand_bridge.launch.py
# 터미널 3
ros2 run dg5f_tutorial fake_target
# 터미널 4: 관절 값이 0~0.9 rad 구간을 오가는지 확인
ros2 topic echo /dg5f_right/joint_states
```

### 이득 확인용 mock (effort 명령)

관절은 움직이지 않으며 컨트롤러 출력만 확인할 수 있습니다. 먼저 위의 mock 런치를 종료합니다.

```bash
ros2 launch dg5f_tutorial dg5f_right_tuning.launch.py hardware:=mock_effort
```

### 실제 핸드

핸드를 개발자 모드와 EtherNET으로 설정하고 네트워크를 연결한 뒤 실행합니다(문서 4~5단계).
처음에는 명령 변화율을 낮추어 시작합니다.

```bash
# 터미널 1: 드라이버 (사용자 정의 YAML을 적용하려면 dg5f_right_tuning.launch.py hardware:=real)
ros2 launch dg5f_driver dg5f_right_driver.launch.py delto_ip:=169.254.186.72

# 터미널 2: 브리지
ros2 launch dg5f_tutorial hand_bridge.launch.py max_velocity:=1.0 \
  target_topic:=/retarget/joint_command
```

PID 통합 컨트롤러를 사용할 때는 `dg5f_right_pid_all_controller.launch.py`로 드라이버를 실행하고 브리지에 `output_mode:=pid`를 지정합니다.

## 브리지 입력 규약

| 항목 | 규약 |
|---|---|
| 토픽 | `/hand_target` (런치 인자 `target_topic`으로 변경) |
| 메시지 | `sensor_msgs/msg/JointState` |
| 관절 식별 | `name` 필드의 관절 이름(`rj_dg_F_J`). 순서는 무관하며 일부 관절만 전송해도 됩니다. 생략된 관절은 직전 목표를 유지합니다. |
| 값 | `position` 필드, 단위 rad. 범위 밖의 값은 URDF 한계값으로 제한됩니다. |
| 거부되는 메시지 | `name`과 `position` 길이가 다르거나, 이름이 중복되거나, NaN·Inf가 포함되거나, 등록된 관절 이름이 하나도 없는 메시지 |

| 런치 인자 | 기본값 | 의미 |
|---|---|---|
| `output_mode` | `jtc` | `jtc`: JTC의 `joint_trajectory` 토픽, `pid`: `rj_dg_pospid/reference` 토픽 |
| `target_topic` | `/hand_target` | 상위 노드의 목표 토픽 |
| `rate_hz` | `50.0` | 명령 발행 주기 [Hz] |
| `max_velocity` | `2.0` | 명령 변화율 상한 [rad/s] |
| `input_timeout` | `0.3` | 이 시간 동안 유효한 입력이 없으면 발행을 중단 [s] |

## 유의 사항

- 브리지는 단일 명령 경로를 전제로 합니다. 같은 컨트롤러에 다른 노드(액션 클라이언트, MoveIt 2 등)가 동시에 명령을 전달하지 않도록 합니다.
- 브리지는 시작할 때 한 번만 현재 자세로 초기화합니다. 브리지가 실행 중인 상태에서 다른 경로로 관절을 움직였다면 브리지를 다시 시작한 뒤 입력을 연결합니다.
- 단위 오류(deg를 rad으로 전송)는 판별하지 못합니다. 단위, 관절 대응, 방향 부호는 상위 노드에서 맞춥니다.
- `config/dg5f_right_controller_tuned.yaml`의 출력 제한 ±3.0은 제어 동작을 설명하기 위한 예제 값입니다. 실제 접촉력이나 파지력의 상한을 보장하지 않으며, 적용 값은 해당 모델과 작업 조건에서 확인해야 합니다.
- 소프트웨어와 독립된 핸드 전원 차단 수단을 구비합니다. 프로세스 강제 종료나 통신 단절 시에는 정상 종료 절차가 실행되지 않습니다.

## 테스트

```bash
cd ~/hand_ws
colcon test --packages-select dg5f_tutorial
colcon test-result --verbose
```

## 라이선스

BSD-3-Clause. [LICENSE](LICENSE)를 참고합니다.
