# Maker Arm URDF

`robot.urdf` describes one Maker Arm for simulators and kinematics: six revolute arm joints and a sliding parallel gripper. Load it directly and keep the `meshes/` folder beside it; mesh paths are relative to the URDF.

It is a copy of the URDF in the [Maker Arm SDK](https://github.com/makermods-robotics/maker-arm-sdk) (`maker_arm/urdf/robot.urdf` and `urdf/maker_arm/meshes/` at commit `606d46f`, 2026-11-19). The only change is the mesh paths, which point at `meshes/` here. The SDK is where the URDF is maintained, so check there for a newer revision.

## Joints

| Joint | Type | Range |
| --- | --- | --- |
| `link_002_joint` (J1) | revolute | -2.8 to 2.8 rad |
| `link_003_joint` (J2) | revolute | -3.14 to 0 rad |
| `link_004_joint` (J3) | revolute | 0 to 3.14 rad |
| `link_005_joint` (J4) | revolute | -1.6 to 1.73 rad |
| `link_006_joint` (J5) | revolute | -1.57 to 1.57 rad |
| `link_007_joint` (J6) | revolute | -2.7 to 2.7 rad |
| `gripper_left_joint` | prismatic | 0 to 0.0524125 m |
| `gripper_right_joint` | prismatic | mimics `gripper_left_joint` along the opposite axis |

- The jaws open 0 to 104.825 mm in total. Simulators must support URDF mimic joints, or enforce the same relationship themselves.
- `grasp_center` is a fixed frame midway between the jaws.
- The model keeps the CAD's coordinates, which are Y-up. Rotate it +90° about X to stand it on a Z-up floor.
- Meshes are in millimetres and scaled by 0.001 in the URDF.

## What it is good for

Use it for visual and kinematic work. It is **not yet validated for dynamics**:

- Forearm and wrist inertials and joint friction are fitted to real-arm motion, not measured. The per-jaw mass split is a CAD estimate.
- Gripper effort (20 N) and velocity (0.1 m/s) are placeholders.
- The arm joints keep the designer's axes, origins and limits. Their zero alignment and actuator limits still need checking against a real arm.
- Collision meshes are the visual meshes and have not been simplified. Friction, backlash and self-collision exclusions are unverified.
- The two finger-loop visuals are removed (their collision meshes and mass remain). The gripper's crank and linkages are not modelled; their inertia is lumped into the wrist.

## How it relates to the STEP files

The meshes are numbered solids from an earlier CAD export (`part_001_solid_001.stl` and so on), not the named part files in `parts/`. Use `parts/` and `assembly/` for manufacturing, and this folder for simulation.
