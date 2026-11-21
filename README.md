# Maker Arm hardware

CAD for the MakerMods Maker Arm as STEP files: the full assembly, plus one file for each part.

The Maker Arm is a robot arm made by [MakerMods](https://makermods.ai). It has seven actuators: six arm joints (J1 to J6) and a parallel gripper (J7). In this build most of the structure is 3D printed.

- Product page: https://makermods.ai/maker-arm.html
- Python SDK: https://github.com/makermods-robotics/maker-arm-sdk

## What this CAD shows

- **Build:** RS02. RobStride 02 actuators on J2 and J3, RobStride 00 actuators on J1, J4, J5, J6 and J7.
- **Configuration:** one follower arm, folded into its rest pose, with the wrist camera on the gripper and the front camera stand beside the arm.
- **Source:** exported from Fusion on 2026-11-20 (`assembly/maker-arm-rs02-single-arm.step`).
- **Units:** millimetres.
- **Not in the CAD:** fasteners (screws, nuts and square nuts), except the two shoulder bolts at the gripper linkage. Cables, the power supply, the emergency stop and the desk clamps are not modelled either.

## Folder layout

```
assembly/maker-arm-rs02-single-arm.step   the full assembly, as exported from Fusion
parts/printed/                            parts MakerMods prints or makes
parts/purchased/                          bought parts: actuators, bearings, linear rail and carriages,
                                          shoulder bolts, washers, camera modules
parts.csv                                 one row per part file: part number, name, Fusion name, qty, group, notes
guide-part-map.json                       which part file each part in the assembly guide uses
tools/split_step.py                       the script that makes parts/ and parts.csv from the assembly
tools/README.md                           how to run it after a new Fusion export
```

## Parts

One file per unique part. A part used four times has one file and a quantity of 4. Quantities are per arm, counted from the assembly, and include the front camera stand.

<!-- parts-table:start -->
| File | Part number | Name | Qty | Type | Group |
| --- | --- | --- | ---: | --- | --- |
| [`MA01-101-01-base-plate.step`](parts/printed/MA01-101-01-base-plate.step) | MA01-101-01 | Base plate | 1 | printed | Base |
| [`MA01-132-01-end-strip.step`](parts/printed/MA01-132-01-end-strip.step) | MA01-132-01 | End strip | 4 | printed | Base |
| [`robstride-00.step`](parts/purchased/robstride-00.step) |  | RobStride 00 actuator | 5 | purchased | J1 |
| [`j1-housing.step`](parts/printed/j1-housing.step) |  | J1 housing | 1 | printed | J1 |
| [`j1-bearing-seat.step`](parts/printed/j1-bearing-seat.step) |  | J1 bearing seat | 1 | printed | J1 |
| [`bearing-6807-35x44x5.step`](parts/purchased/bearing-6807-35x44x5.step) |  | Deep-groove ball bearing 6807, 35 x 44 x 5 mm | 1 | purchased | J1 |
| [`j1-output-flange.step`](parts/printed/j1-output-flange.step) |  | J1 output flange | 1 | printed | J1 |
| [`shoulder-bracket.step`](parts/printed/shoulder-bracket.step) |  | Shoulder bracket | 1 | printed | J2 shoulder |
| [`robstride-02.step`](parts/purchased/robstride-02.step) |  | RobStride 02 actuator | 2 | purchased | J2 shoulder |
| [`rs02-rear-spacer.step`](parts/printed/rs02-rear-spacer.step) |  | RS02 rear spacer / cable tie block | 4 | printed | J2 shoulder |
| [`bearing-6704-20x27x4.step`](parts/purchased/bearing-6704-20x27x4.step) |  | Deep-groove ball bearing 6704, 20 x 27 x 4 mm | 3 | purchased | J2 shoulder |
| [`upper-arm-front-half.step`](parts/printed/upper-arm-front-half.step) |  | Upper arm, front half | 1 | printed | Upper arm |
| [`upper-arm-back-half.step`](parts/printed/upper-arm-back-half.step) |  | Upper arm, back half | 1 | printed | Upper arm |
| [`forearm-front-half.step`](parts/printed/forearm-front-half.step) |  | Forearm, front half | 1 | printed | Forearm |
| [`forearm-back-half.step`](parts/printed/forearm-back-half.step) |  | Forearm, back half | 1 | printed | Forearm |
| [`j4-output-spacer.step`](parts/printed/j4-output-spacer.step) |  | J4 output spacer | 1 | printed | J4 |
| [`j4-bearing-spacer.step`](parts/printed/j4-bearing-spacer.step) |  | J4 bearing spacer | 1 | printed | J4 |
| [`j4-j5-link.step`](parts/printed/j4-j5-link.step) |  | J4-J5 link | 1 | printed | Wrist |
| [`j5-rear-cap.step`](parts/printed/j5-rear-cap.step) |  | J5 rear cap | 1 | printed | Wrist |
| [`j5-j6-link.step`](parts/printed/j5-j6-link.step) |  | J5-J6 link | 1 | printed | Wrist |
| [`wrist-cable-guard.step`](parts/printed/wrist-cable-guard.step) |  | Wrist cable guard | 1 | printed | Wrist |
| [`j6-output-head.step`](parts/printed/j6-output-head.step) |  | J6 output head | 1 | printed | Wrist |
| [`j7-actuator-mount.step`](parts/printed/j7-actuator-mount.step) |  | J7 (gripper) actuator mount | 1 | printed | Gripper |
| [`gripper-crank.step`](parts/printed/gripper-crank.step) |  | Gripper crank | 1 | printed | Gripper |
| [`pivot-washer.step`](parts/purchased/pivot-washer.step) |  | Pivot washer | 2 | purchased | Gripper |
| [`gripper-linkage.step`](parts/printed/gripper-linkage.step) |  | Gripper linkage | 2 | printed | Gripper |
| [`bearing-mf84zz-4x8x3.step`](parts/purchased/bearing-mf84zz-4x8x3.step) |  | Flanged ball bearing MF84ZZ, 4 x 8 x 3 mm | 8 | purchased | Gripper |
| [`shoulder-bolt-4mm-m3.step`](parts/purchased/shoulder-bolt-4mm-m3.step) |  | Shoulder bolt, 4 mm shoulder, M3 thread | 2 | purchased | Gripper |
| [`gripper-rail-base.step`](parts/printed/gripper-rail-base.step) |  | Gripper rail base | 1 | printed | Gripper |
| [`mgn7-linear-rail-160mm.step`](parts/purchased/mgn7-linear-rail-160mm.step) |  | Linear rail MGN7, 160 mm | 1 | purchased | Gripper |
| [`mgn7-carriage.step`](parts/purchased/mgn7-carriage.step) |  | Linear carriage MGN7 | 2 | purchased | Gripper |
| [`finger-mount.step`](parts/printed/finger-mount.step) |  | Finger mount | 2 | printed | Gripper |
| [`gripper-finger.step`](parts/printed/gripper-finger.step) |  | Gripper finger | 2 | printed | Gripper |
| [`wrist-camera-bracket.step`](parts/printed/wrist-camera-bracket.step) |  | Wrist camera bracket | 1 | printed | Wrist camera |
| [`MA01-131-01-camera-cover.step`](parts/printed/MA01-131-01-camera-cover.step) | MA01-131-01 | Camera cover | 2 | printed | Wrist camera |
| [`usb-camera-module.step`](parts/purchased/usb-camera-module.step) |  | USB camera module (KD-USB) | 2 | purchased | Wrist camera |
| [`MA01-127-01-camera-stand-base-plate.step`](parts/printed/MA01-127-01-camera-stand-base-plate.step) | MA01-127-01 | Camera stand base plate | 1 | printed | Front camera stand |
| [`MA01-128-01-camera-stand-foot.step`](parts/printed/MA01-128-01-camera-stand-foot.step) | MA01-128-01 | Camera stand foot | 1 | printed | Front camera stand |
| [`MA01-129-01-camera-stand-arm-1.step`](parts/printed/MA01-129-01-camera-stand-arm-1.step) | MA01-129-01 | Camera stand arm 1 | 1 | printed | Front camera stand |
| [`MA01-130-01-camera-stand-arm-2.step`](parts/printed/MA01-130-01-camera-stand-arm-2.step) | MA01-130-01 | Camera stand arm 2 | 1 | printed | Front camera stand |
<!-- parts-table:end -->

[`parts.csv`](parts.csv) has the same list with the original Fusion component names and notes.

About the part files:

- Each file holds the part in its own Fusion component coordinate system, not where it sits in the assembly. The upper arm and the forearm are each one Fusion component made of two halves, so each half has its own file, and both halves keep the shared frame of that component.
- The STEP product name in each file is the file name without `.step`.
- Raised lettering and logos are separate bodies inside the file of the part they belong to (upper arm, forearm, camera cover, camera stand base plate).
- Files that start with a part number (`MA01-1xx-xx`) use the MakerMods part number. Parts without one are named after what they are.
- Printed vs other material is not yet confirmed for some parts (the base plate, end strips, camera stand base plate, camera cover and pivot washers). `parts.csv` marks these "unconfirmed".

## Regenerating the part files

After a new Fusion export, replace `assembly/maker-arm-rs02-single-arm.step` and run:

```
python tools/split_step.py
```

It rewrites `parts/`, `parts.csv`, `guide-part-map.json` and the table above, then re-opens every part file and checks it against the assembly. See [tools/README.md](tools/README.md) for setup and what to do when component names change.

## Large files

STEP files are stored with [Git LFS](https://git-lfs.com). Run `git lfs install` once before cloning, or the STEP files will be small text pointers.

## License

To be decided before public release.

Before release, also confirm that the models of purchased parts in `parts/purchased/` (RobStride actuators, bearings, linear rail and carriages, shoulder bolts, camera module) can be redistributed.
