#!/usr/bin/env python3
"""Split the Maker Arm assembly STEP into one STEP file per unique part.

    python tools/split_step.py                      # split, write parts/ and parts.csv, verify
    python tools/split_step.py --check              # verify only (re-reads the existing part files)
    python tools/split_step.py --steps-js PATH      # also check every PARTS key in the guide's steps.js is mapped

Needs the OpenCascade Python bindings (`pip install cadquery-ocp`). See tools/README.md.

How it works
------------
The assembly is read with XCAF so the Fusion component names and the assembly tree survive.
Each leaf component (a STEP product) is matched by name against PARTS below. Each PARTS row
says which solids of which component go into one output file. The file holds the part in the
component's own coordinate system (the instance placement is stripped), in mm, with the file
stem as the STEP product name.

Selections ("select"):
  all       every solid of the component; one copy per instance
  largest   only the largest solid (by volume); one copy per instance
  others    every solid except the largest; each solid is one copy
  each      every solid is one copy (the file holds one of them)
  half:+Z / half:-Z
            the component is two halves: the two largest solids are the halves' main bodies and
            every smaller solid (embossed lettering) goes with the main body it touches. +Z picks
            the half whose main body sits at larger Z in the assembly frame.

When several components (or several solids of one component) are copies of the same part, the
first one is written and the rest are checked against it (same volume and bounding-box size).

After writing, every part file is re-opened and checked against the assembly: for every
occurrence, the part file moved to that occurrence's placement must have the same bounding box
(size and centre, within TOL_MM) and volume as the matching solids in the assembly.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# Naming table. One row per output file. Edit this after a new Fusion export if names change.
#   file         file stem (lowercase kebab-case ASCII; MakerMods part number first if it has one)
#   pn           MakerMods part number, or "" if none
#   name         English name
#   category     printed | purchased
#   group        where it sits on the arm
#   sources      list of {"product": <Fusion component name as read by XCAF>, "select": ...}
#   guide        keys of PARTS in the assembly guide's steps.js that show this part
#   notes        free text for parts.csv
# ---------------------------------------------------------------------------------------------
PARTS = [
    # Base
    dict(file="MA01-101-01-base-plate", pn="MA01-101-01", name="Base plate", category="printed", group="Base",
         sources=[dict(product="MA01-101-01")], guide=["base-plate"],
         notes="200 x 100 x 10 mm plate under the arm. Printed vs another material unconfirmed."),
    dict(file="MA01-132-01-end-strip", pn="MA01-132-01", name="End strip", category="printed", group="Base",
         sources=[dict(product="MA01-132-01")],
         guide=["end-strip-front", "end-strip-back", "stand-strip-a", "stand-strip-b"],
         notes="Two under the arm base plate, two under the camera stand base plate; sits in a recess, "
               "three captured M3 nuts. Printed vs another material unconfirmed."),
    # J1
    dict(file="robstride-00", pn="", name="RobStride 00 actuator", category="purchased", group="J1",
         sources=[dict(product="RS00")],
         guide=["j1-actuator", "j4-actuator", "j5-actuator", "j6-actuator", "j7-actuator"],
         notes="J1, J4, J5, J6 and J7 (gripper)."),
    dict(file="j1-housing", pn="", name="J1 housing", category="printed", group="J1",
         sources=[dict(product="yaw电机外壳")], guide=["j1-housing"], notes=""),
    dict(file="j1-bearing-seat", pn="", name="J1 bearing seat", category="printed", group="J1",
         sources=[dict(product="yaw轴承底座")], guide=["j1-seat"], notes=""),
    dict(file="bearing-6807-35x44x5", pn="", name="Deep-groove ball bearing 6807, 35 x 44 x 5 mm", category="purchased",
         group="J1", sources=[dict(product="深沟球35*44*5")], guide=["j1-bearing"], notes=""),
    dict(file="j1-output-flange", pn="", name="J1 output flange", category="printed", group="J1",
         sources=[dict(product="yaw输出下部分")], guide=["j1-flange"], notes=""),
    # J2 shoulder
    dict(file="shoulder-bracket", pn="", name="Shoulder bracket", category="printed", group="J2 shoulder",
         sources=[dict(product="L2电机固定底板")], guide=["shoulder-bracket"], notes="Holds the J2 actuator."),
    dict(file="robstride-02", pn="", name="RobStride 02 actuator", category="purchased", group="J2 shoulder",
         sources=[dict(product="rs02")], guide=["j2-actuator", "j3-actuator"], notes="J2 and J3."),
    dict(file="rs02-rear-spacer", pn="", name="RS02 rear spacer / cable tie block", category="printed",
         group="J2 shoulder", sources=[dict(product="02后垫块-束线")],
         guide=["j2-spacer-top", "j2-spacer-bottom", "j3-spacer-top", "j3-spacer-bottom"],
         notes="Two on each RS02 (J2 and J3); also a cable tie-down point."),
    dict(file="bearing-6704-20x27x4", pn="", name="Deep-groove ball bearing 6704, 20 x 27 x 4 mm", category="purchased",
         group="J2 shoulder", sources=[dict(product="深沟球20，27，4")],
         guide=["j2-bearing", "j3-bearing", "j4-bearing"], notes="Passive side of J2, J3 and J4."),
    # Upper arm
    dict(file="upper-arm-front-half", pn="", name="Upper arm, front half", category="printed", group="Upper arm",
         sources=[dict(product="L2-P-旧", select="half:+Z")], guide=["upper-arm-front"],
         notes="Half of Fusion component L2-P-旧 (current part despite the 旧 'old' in the name). "
               "Includes its embossed lettering bodies. Frame: the component frame shared by both halves."),
    dict(file="upper-arm-back-half", pn="", name="Upper arm, back half", category="printed", group="Upper arm",
         sources=[dict(product="L2-P-旧", select="half:-Z")], guide=["upper-arm-back"],
         notes="Half of Fusion component L2-P-旧 (current part despite the 旧 'old' in the name). "
               "Includes its embossed lettering bodies. Frame: the component frame shared by both halves."),
    # Forearm
    dict(file="forearm-front-half", pn="", name="Forearm, front half", category="printed", group="Forearm",
         sources=[dict(product="L3-P", select="half:+Z")], guide=["forearm-front"],
         notes="Half of Fusion component L3-P. Includes its embossed text and logo bodies. "
               "Frame: the component frame shared by both halves."),
    dict(file="forearm-back-half", pn="", name="Forearm, back half", category="printed", group="Forearm",
         sources=[dict(product="L3-P", select="half:-Z")], guide=["forearm-back"],
         notes="Half of Fusion component L3-P. Includes its embossed text and logo bodies. "
               "Frame: the component frame shared by both halves."),
    # J4
    dict(file="j4-output-spacer", pn="", name="J4 output spacer", category="printed", group="J4",
         sources=[dict(product="末端输出轴垫块")], guide=["j4-out-spacer"],
         notes="STEP product id 2026-07-31-17-09-31-597."),
    dict(file="j4-bearing-spacer", pn="", name="J4 bearing spacer", category="printed", group="J4",
         sources=[dict(product="末端轴承垫块")], guide=["j4-brg-spacer"],
         notes="STEP product id 2026-07-31-16-45-47-097."),
    # Wrist
    dict(file="j4-j5-link", pn="", name="J4-J5 link", category="printed", group="Wrist",
         sources=[dict(product="J4-J5-P-3")], guide=["link-j4j5"], notes=""),
    dict(file="j5-rear-cap", pn="", name="J5 rear cap", category="printed", group="Wrist",
         sources=[dict(product="J5后端盖子")], guide=["j5-cap"], notes=""),
    dict(file="j5-j6-link", pn="", name="J5-J6 link", category="printed", group="Wrist",
         sources=[dict(product="J5-J6-P-L")], guide=["link-j5j6"], notes=""),
    dict(file="wrist-cable-guard", pn="", name="Wrist cable guard", category="printed", group="Wrist",
         sources=[dict(product="护腕")], guide=["wrist-guard"],
         notes="Wrist guard that also guides the cable. STEP product id 护腕-线缆导向."),
    dict(file="j6-output-head", pn="", name="J6 output head", category="printed", group="Wrist",
         sources=[dict(product="J6轴头-加强-P")], guide=["j6-head"], notes="Reinforced version."),
    # Gripper
    dict(file="j7-actuator-mount", pn="", name="J7 (gripper) actuator mount", category="printed", group="Gripper",
         sources=[dict(product="J7电机底座-P")], guide=["j7-mount"], notes=""),
    dict(file="gripper-crank", pn="", name="Gripper crank", category="printed", group="Gripper",
         sources=[dict(product="夹爪连杆底座-P", select="largest")], guide=["crank"],
         notes="Fusion name 夹爪连杆底座-P (linkage base). The component also holds the two pivot washers, "
               "which are in pivot-washer.step."),
    dict(file="pivot-washer", pn="", name="Pivot washer", category="purchased", group="Gripper",
         sources=[dict(product="夹爪连杆底座-P", select="others")], guide=["pivot-washers"],
         notes="Unconfirmed: separate bodies inside Fusion component 夹爪连杆底座-P, 5.5 mm OD x 3.5 mm ID x 1.0 mm, "
               "on the two crank-end pivots. Bought washer/shim vs printed is unconfirmed."),
    dict(file="gripper-linkage", pn="", name="Gripper linkage", category="printed", group="Gripper",
         sources=[dict(product="连杆-P")], guide=["linkage-a", "linkage-b"], notes=""),
    dict(file="bearing-mf84zz-4x8x3", pn="", name="Flanged ball bearing MF84ZZ, 4 x 8 x 3 mm", category="purchased",
         group="Gripper", sources=[dict(product="MF84ZZ 法兰轴承 4 8 3", select="each")],
         guide=["lk-bearings-a", "lk-bearings-b"],
         notes="Two back to back at each linkage pivot. The Fusion component is a pair (2 bodies, 4 instances); "
               "this file holds one bearing in the pair's frame (1.6 mm off the origin along its axis)."),
    dict(file="shoulder-bolt-4mm-m3", pn="", name="Shoulder bolt, 4 mm shoulder, M3 thread", category="purchased",
         group="Gripper", sources=[dict(product="M4塞打螺栓")], guide=[],
         notes="Linkage pivots. Fusion calls it M4; the model has a 4 mm shoulder, M3 thread and 7 mm head. "
               "The CAD has 2 (both on one linkage) for 4 pivots; check the count per arm."),
    dict(file="gripper-rail-base", pn="", name="Gripper rail base", category="printed", group="Gripper",
         sources=[dict(product="滑轨底座-P")], guide=["rail-base"], notes=""),
    dict(file="mgn7-linear-rail-160mm", pn="", name="Linear rail MGN7, 160 mm", category="purchased", group="Gripper",
         sources=[dict(product="7mm直线滑轨")], guide=["rail"], notes=""),
    dict(file="mgn7-carriage", pn="", name="Linear carriage MGN7", category="purchased", group="Gripper",
         sources=[dict(product="7mm直线滑块")], guide=["carriage-a", "carriage-b"], notes="MGN7C size (22.5 mm long)."),
    dict(file="finger-mount", pn="", name="Finger mount", category="printed", group="Gripper",
         sources=[dict(product="滑块底座-P")], guide=["finger-mount-a", "finger-mount-b"],
         notes="Mounts a finger on a carriage."),
    dict(file="gripper-finger", pn="", name="Gripper finger", category="printed", group="Gripper",
         sources=[dict(product="夹爪")], guide=["finger-a", "finger-b"],
         notes="STEP product id 2026-07-23-10-39-16-053."),
    # Wrist camera
    dict(file="wrist-camera-bracket", pn="", name="Wrist camera bracket", category="printed", group="Wrist camera",
         sources=[dict(product="Maker Arm摄像头支架-2")], guide=["wcam-bracket"], notes=""),
    dict(file="MA01-131-01-camera-cover", pn="MA01-131-01", name="Camera cover", category="printed",
         group="Wrist camera",
         sources=[dict(product="MA01-131-01"), dict(product="末端摄像头盖 单logo")],
         guide=["wcam-cover", "fcam-cover"],
         notes="Cover plate with logo over the camera board. One on the wrist camera (Fusion name 末端摄像头盖 单logo, "
               "same geometry, no part number there) and one on the front camera. Includes the logo bodies. "
               "The wrist one is in the RS02 print file; the MA01-131-01 copy is assumed printed the same way (unconfirmed)."),
    dict(file="usb-camera-module", pn="", name="USB camera module (KD-USB)", category="purchased", group="Wrist camera",
         sources=[dict(product="相机")], guide=["wcam-camera", "fcam-camera"],
         notes="One on the wrist, one on the front camera stand. The component origin is about 470 mm from the "
               "part; re-centre after import if needed."),
    # Front camera stand
    dict(file="MA01-127-01-camera-stand-base-plate", pn="MA01-127-01", name="Camera stand base plate",
         category="printed", group="Front camera stand", sources=[dict(product="MA01-127-01")], guide=["stand-plate"],
         notes="245 x 100 x 10 mm, includes its embossed lettering bodies. Printed vs another material unconfirmed."),
    dict(file="MA01-128-01-camera-stand-foot", pn="MA01-128-01", name="Camera stand foot", category="printed",
         group="Front camera stand", sources=[dict(product="MA01-128-01")], guide=["stand-foot"],
         notes="In the RS02 print file as 02-3d双臂相机底座."),
    dict(file="MA01-129-01-camera-stand-arm-1", pn="MA01-129-01", name="Camera stand arm 1", category="printed",
         group="Front camera stand", sources=[dict(product="MA01-129-01")], guide=["stand-arm1"],
         notes="In the RS02 print file as 相机支架-1."),
    dict(file="MA01-130-01-camera-stand-arm-2", pn="MA01-130-01", name="Camera stand arm 2", category="printed",
         group="Front camera stand", sources=[dict(product="MA01-130-01")], guide=["stand-arm2"],
         notes="Holds the front camera. In the RS02 print file as 相机支架-2."),
]

TOL_MM = 0.1          # bounding-box tolerance for the checks
VOL_REL_TOL = 1e-4    # relative volume tolerance for the checks and for "same part" matching

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ASSEMBLY = REPO / "assembly" / "maker-arm-rs02-single-arm.step"
WINDOWS_BAD = re.compile(r'[:?*"<>|/\\]|[. ]$')

# ---------------------------------------------------------------------------------------------
from OCP.BRep import BRep_Builder
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

try:  # OCP >= 7.8 / cadquery-ocp 8 moved the collection types
    from OCP.collections import Sequence_TDF_Label as LabelSeq
except ImportError:  # pragma: no cover
    from OCP.TDF import TDF_LabelSequence as LabelSeq

def quiet_occt():
    """Stop OpenCascade printing transfer statistics to the console."""
    try:
        from OCP.Message import Message
        Message.DefaultMessenger_s().ChangePrinters().Clear()
    except Exception:
        pass


COLOR_TYPES = (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen)


def new_doc():
    return TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))


def read_step(path):
    doc = new_doc()
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.SetColorMode(True)
    if r.ReadFile(str(path)) != IFSelect_RetDone:
        raise SystemExit(f"cannot read {path}")
    r.Transfer(doc)
    return doc


def label_name(lab):
    a = TDataStd_Name()
    return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""


def solids(shape):
    out, e = [], TopExp_Explorer(shape, TopAbs_SOLID)
    while e.More():
        out.append(e.Current())
        e.Next()
    return out


def volume(shape):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, p)
    return p.Mass()


def bbox(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b, False, False)
    lo, hi = b.CornerMin(), b.CornerMax()
    return (lo.X(), lo.Y(), lo.Z()), (hi.X(), hi.Y(), hi.Z())


def size_centre(shape):
    lo, hi = bbox(shape)
    return tuple(h - l for l, h in zip(lo, hi)), tuple((l + h) / 2 for l, h in zip(lo, hi))


def compound(shapes):
    if len(shapes) == 1:
        return shapes[0]
    c, b = TopoDS_Compound(), BRep_Builder()
    b.MakeCompound(c)
    for s in shapes:
        b.Add(c, s)
    return c


# ---------------------------------------------------------------------------------------------
def walk_assembly(doc):
    """Return (products, occurrences).

    products: {label entry: {"name", "label", "shape", "solids"}} for every leaf component.
    occurrences: list of {"entry", "loc" (TopLoc_Location in the assembly frame), "path"}.
    """
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    products, occurrences = {}, []

    def entry(lab):
        from OCP.TDF import TDF_Tool
        from OCP.TCollection import TCollection_AsciiString
        s = TCollection_AsciiString()
        TDF_Tool.Entry_s(lab, s)
        return s.ToCString()

    def visit(lab, loc, path):
        if st.IsAssembly_s(lab):
            comps = LabelSeq()
            st.GetComponents_s(lab, comps, False)
            for i in range(1, comps.Length() + 1):
                comp = comps.Value(i)
                ref = TDF_Label()
                st.GetReferredShape_s(comp, ref)
                child_loc = loc.Multiplied(st.GetLocation_s(comp))
                visit(ref, child_loc, path + [label_name(comp)])
        else:
            e = entry(lab)
            if e not in products:
                shp = st.GetShape_s(lab)
                products[e] = dict(name=label_name(lab), label=lab, shape=shp, solids=solids(shp))
            occurrences.append(dict(entry=e, loc=loc, path="/".join(path)))

    free = LabelSeq()
    st.GetFreeShapes(free)
    for i in range(1, free.Length() + 1):
        visit(free.Value(i), TopLoc_Location(), [label_name(free.Value(i))])
    return st, products, occurrences


def select_groups(prod, select, first_loc):
    """Split a component's solids into copies. Returns a list of lists of solid indices."""
    sol = prod["solids"]
    vols = [volume(s) for s in sol]
    order = sorted(range(len(sol)), key=lambda i: -vols[i])
    if select == "all":
        return [list(range(len(sol)))]
    if select == "largest":
        return [[order[0]]]
    if select == "others":
        return [[i] for i in order[1:]]
    if select == "each":
        return [[i] for i in range(len(sol))]
    if select.startswith("half:"):
        mains = order[:2]
        halves = {m: [m] for m in mains}
        for i in order[2:]:
            d = []
            for m in mains:
                ext = BRepExtrema_DistShapeShape(sol[i], sol[m])
                d.append(ext.Value())
            halves[mains[d.index(min(d))]].append(i)
        # which half is which: centre Z of the main body in the assembly frame
        zc = {m: size_centre(sol[m].Moved(first_loc))[1][2] for m in mains}
        hi, lo = sorted(mains, key=lambda m: -zc[m])
        return [sorted(halves[hi if select == "half:+Z" else lo])]
    raise SystemExit(f"unknown select {select!r}")


def plan(products, occurrences):
    """Resolve PARTS against the assembly. Returns (plan rows, unassigned solids)."""
    by_name = defaultdict(list)
    for e, p in products.items():
        by_name[p["name"]].append(e)
    occ_by_entry = defaultdict(list)
    for o in occurrences:
        occ_by_entry[o["entry"]].append(o)

    assigned = defaultdict(set)   # entry -> solid indices used
    rows = []
    for part in PARTS:
        copies = []   # each: dict(entry, idx list) ; first is canonical
        for src in part["sources"]:
            entries = by_name.get(src["product"], [])
            if not entries:
                raise SystemExit(f"{part['file']}: no component named {src['product']!r} in the assembly")
            for e in entries:
                first_loc = occ_by_entry[e][0]["loc"]
                for grp in select_groups(products[e], src.get("select", "all"), first_loc):
                    copies.append(dict(entry=e, idx=grp))
                    for i in grp:
                        if i in assigned[e]:
                            raise SystemExit(f"{part['file']}: solid {i} of {src['product']} already used")
                        assigned[e].add(i)
        rows.append(dict(part=part, copies=copies))

    unassigned = []
    for e, p in products.items():
        left = set(range(len(p["solids"]))) - assigned[e]
        if left:
            unassigned.append((p["name"], e, sorted(left), len(occ_by_entry[e])))
    return rows, unassigned, occ_by_entry


def copy_shape(products, c):
    return compound([products[c["entry"]]["solids"][i] for i in c["idx"]])


def bbox_dev(a, b):
    (sa, ca), (sb, cb) = size_centre(a), size_centre(b)
    return max(max(abs(x - y) for x, y in zip(sa, sb)), max(abs(x - y) for x, y in zip(ca, cb)))


def copy_frames(products, row, occ_by_entry):
    """Check every copy matches the first (canonical) one and return, for each copy, the placement
    of the canonical shape that reproduces it inside the component frame: a translation, or a
    half-turn about X, Y or Z plus a translation (for copies that are flipped, e.g. back-to-back
    bearings). Chosen by matching bounding boxes in the component frame and in the assembly frame."""
    canon = copy_shape(products, row["copies"][0])
    csz, ccen = size_centre(canon)
    cvol = volume(canon)
    out = []
    for c in row["copies"]:
        s = copy_shape(products, c)
        sz, cen = size_centre(s)
        v = volume(s)
        if max(abs(a - b) for a, b in zip(sorted(sz), sorted(csz))) > 0.01 or abs(v - cvol) > VOL_REL_TOL * cvol:
            raise SystemExit(f"{row['part']['file']}: copy {products[c['entry']]['name']} {c['idx']} "
                             f"does not match the first copy (size {sz} vs {csz}, volume {v:.2f} vs {cvol:.2f})")
        occ_loc = occ_by_entry[c["entry"]][0]["loc"]
        best = None
        for axis in (None, gp_Dir(1, 0, 0), gp_Dir(0, 1, 0), gp_Dir(0, 0, 1)):
            t = gp_Trsf()
            if axis is not None:
                t.SetRotation(gp_Ax1(gp_Pnt(*ccen), axis), math.pi)
            m = gp_Trsf()
            m.SetTranslation(gp_Vec(*[a - b for a, b in zip(cen, ccen)]))
            loc = TopLoc_Location(m.Multiplied(t))
            dev = max(bbox_dev(canon.Moved(loc), s), bbox_dev(canon.Moved(occ_loc.Multiplied(loc)), s.Moved(occ_loc)))
            if best is None or dev < best[0] - 1e-9:
                best = (dev, loc)
        if best[0] > 0.01:
            raise SystemExit(f"{row['part']['file']}: copy {products[c['entry']]['name']} {c['idx']} "
                             f"is not a translated or flipped copy of the first one (dev {best[0]:.3f} mm)")
        out.append(best[1])
    return out


def write_part(src_doc, products, row, path):
    ct_src = XCAFDoc_DocumentTool.ColorTool_s(src_doc.Main())
    c0 = row["copies"][0]
    prod = products[c0["entry"]]
    parts = [prod["solids"][i] for i in c0["idx"]]
    whole = len(c0["idx"]) == len(prod["solids"])
    shape = prod["shape"] if whole else compound(parts)

    doc = new_doc()
    try:
        from OCP.UnitsMethods import UnitsMethods_LengthUnit
        XCAFDoc_DocumentTool.SetLengthUnit_s(doc, 1.0, UnitsMethods_LengthUnit.UnitsMethods_LengthUnit_Millimeter)
    except Exception:
        pass
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    lab = st.AddShape(shape, False, False)
    TDataStd_Name.Set_s(lab, TCollection_ExtendedString(row["part"]["file"]))
    # carry over colours: the component's own colour, then per-solid colours
    c = Quantity_Color()
    for t in COLOR_TYPES:
        if ct_src.GetColor(prod["shape"], t, c):
            ct.SetColor(shape, c, t)
            break
    if len(parts) > 1:
        for s in parts:
            for t in COLOR_TYPES:
                if ct_src.GetColor(s, t, c):
                    st.AddSubShape(lab, s)
                    ct.SetColor(s, c, t)
                    break
    elif not whole:
        for t in COLOR_TYPES:
            if ct_src.GetColor(parts[0], t, c):
                ct.SetColor(shape, c, t)
                break

    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    w = STEPCAFControl_Writer()
    w.SetNameMode(True)
    w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.step")
    if w.Write(str(tmp)) != IFSelect_RetDone:
        raise SystemExit(f"cannot write {path}")
    tidy_header(tmp, path)


SOURCE_STAMP = {"time_stamp": "", "system": ""}


def tidy_header(tmp, path):
    """Make the header reproducible and free of local paths and placeholder names."""
    text = tmp.read_text(encoding="utf-8", errors="surrogateescape")
    head, sep, body = text.partition("ENDSEC;")
    head = re.sub(r"FILE_DESCRIPTION\(.*?\);",
                  lambda m: f"FILE_DESCRIPTION(('Maker Arm part {path.stem}'),'2;1');", head, count=1, flags=re.S)
    head = re.sub(r"FILE_NAME\(.*?\);",
                  lambda m: (f"FILE_NAME('{path.name}','{SOURCE_STAMP['time_stamp']}',(''),('MakerMods'),\n"
                             f"  'Open CASCADE STEP processor','tools/split_step.py','');"),
                  head, count=1, flags=re.S)
    path.write_text(head + sep + body, encoding="utf-8", errors="surrogateescape")
    tmp.unlink()


def read_source_stamp(assembly):
    with open(assembly, "r", encoding="latin-1") as f:
        head = f.read(4000)
    m = re.search(r"time_stamp \*/\s*'([^']*)'", head) or re.search(r"FILE_NAME\('[^']*','([^']*)'", head)
    SOURCE_STAMP["time_stamp"] = m.group(1) if m else ""


def file_path(part):
    return Path("parts") / part["category"] / f"{part['file']}.step"


# ---------------------------------------------------------------------------------------------
def verify(products, occurrences, rows, unassigned, occ_by_entry, steps_js=None):
    ok = True
    print("\n(a) part files re-opened and compared with the assembly, every occurrence")
    worst = 0.0
    n_checks = 0
    for row in rows:
        part = row["part"]
        p = REPO / file_path(part)
        if not p.exists():
            print(f"  MISSING {p}")
            ok = False
            continue
        d = read_step(p)
        st = XCAFDoc_DocumentTool.ShapeTool_s(d.Main())
        free = LabelSeq()
        st.GetFreeShapes(free)
        shp = compound([st.GetShape_s(free.Value(i)) for i in range(1, free.Length() + 1)])
        name = label_name(free.Value(1))
        nsol = len(solids(shp))
        fvol = volume(shp)
        offs = copy_frames(products, row, occ_by_entry)
        dev_part = 0.0
        for c, off in zip(row["copies"], offs):
            for o in occ_by_entry[c["entry"]]:
                asm = copy_shape(products, c).Moved(o["loc"])
                placed = shp.Moved(o["loc"].Multiplied(off))
                (sa, ca), (sp, cp) = size_centre(asm), size_centre(placed)
                dev = max(max(abs(x - y) for x, y in zip(sa, sp)), max(abs(x - y) for x, y in zip(ca, cp)))
                vdev = abs(volume(asm) - fvol) / fvol
                dev_part = max(dev_part, dev)
                n_checks += 1
                if dev > TOL_MM or vdev > VOL_REL_TOL or nsol != len(c["idx"]):
                    ok = False
                    print(f"  FAIL {part['file']} at {o['path']}: bbox dev {dev:.3f} mm, volume dev {vdev:.2e}, "
                          f"solids {nsol} vs {len(c['idx'])}")
        worst = max(worst, dev_part)
        if name != part["file"]:
            ok = False
            print(f"  FAIL {part['file']}: STEP product name is {name!r}")
        sz, _ = size_centre(shp)
        print(f"  ok  {str(file_path(part)):58s} solids={nsol:<3d} size={sz[0]:7.2f} x {sz[1]:7.2f} x {sz[2]:7.2f} mm  "
              f"max dev {dev_part:.4f} mm")
    print(f"  {n_checks} occurrence checks, worst bounding-box deviation {worst:.4f} mm (tolerance {TOL_MM} mm)")

    print("\n(b) counts")
    n_leaf = len(occurrences)
    n_solid_occ = sum(len(products[o["entry"]]["solids"]) for o in occurrences)
    qty_total = sum(row_qty(r, occ_by_entry) for r in rows)
    solids_from_csv = sum(row_qty(r, occ_by_entry) * len(r["copies"][0]["idx"]) for r in rows)
    occ_covered = {id(o) for r in rows for c in r["copies"] for o in occ_by_entry[c["entry"]]}
    print(f"  assembly: {n_leaf} leaf component instances, {len(products)} unique leaf components, "
          f"{n_solid_occ} solid bodies")
    print(f"  parts.csv: {len(rows)} files, total qty {qty_total}, accounting for {solids_from_csv} solid bodies")
    print(f"  instances covered by at least one file: {len(occ_covered)} of {n_leaf}")
    if solids_from_csv != n_solid_occ or len(occ_covered) != n_leaf:
        ok = False
        print("  FAIL: counts do not reconcile")

    print("\n(d) assembly components (or bodies) in no part file")
    if unassigned:
        ok = False
        for name, e, idx, n in unassigned:
            print(f"  {name} ({e}) solids {idx}, {n} instance(s)")
    else:
        print("  none")

    gm = json.loads((REPO / "guide-part-map.json").read_text())
    print("\n(c) guide part map")
    missing_files = [k for k, v in gm.items() if not (REPO / v).exists()]
    print(f"  {len(gm)} keys, {len(set(gm.values()))} distinct files, files missing: {missing_files or 'none'}")
    ok &= not missing_files
    if steps_js:
        src = Path(steps_js).read_text(encoding="utf-8")
        block = src[src.index("export const PARTS"):]
        block = block[:block.index("\n};")]
        keys = re.findall(r'^\s*"([^"]+)"\s*:', block, re.M)
        unmapped = [k for k in keys if k not in gm]
        extra = [k for k in gm if k not in keys]
        print(f"  steps.js PARTS keys: {len(keys)}; unmapped: {unmapped or 'none'}; map keys not in steps.js: {extra or 'none'}")
        ok &= not unmapped and not extra
    return ok


def row_qty(row, occ_by_entry):
    return sum(len(occ_by_entry[c["entry"]]) for c in row["copies"])


def write_csv(rows, occ_by_entry, products):
    with open(REPO / "parts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "part_number", "name", "fusion_name", "qty", "category", "group", "notes"])
        for r in rows:
            p = r["part"]
            fusion = []
            for c in r["copies"]:
                n = products[c["entry"]]["name"]
                if n not in fusion:
                    fusion.append(n)
            w.writerow([file_path(p).as_posix(), p["pn"], p["name"], "; ".join(fusion), row_qty(r, occ_by_entry),
                        p["category"], p["group"], p["notes"]])


def write_guide_map():
    gm = {}
    for p in PARTS:
        for k in p["guide"]:
            if k in gm:
                raise SystemExit(f"guide key {k} mapped twice")
            gm[k] = file_path(p).as_posix()
    (REPO / "guide-part-map.json").write_text(json.dumps(gm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_readme(rows, occ_by_entry):
    readme = REPO / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    a, b = "<!-- parts-table:start -->", "<!-- parts-table:end -->"
    if a not in text or b not in text:
        return
    lines = ["| File | Part number | Name | Qty | Type | Group |", "| --- | --- | --- | ---: | --- | --- |"]
    for r in rows:
        p = r["part"]
        fp = file_path(p).as_posix()
        lines.append(f"| [`{p['file']}.step`]({fp}) | {p['pn']} | {p['name']} | {row_qty(r, occ_by_entry)} | "
                     f"{p['category']} | {p['group']} |")
    new = text[:text.index(a) + len(a)] + "\n" + "\n".join(lines) + "\n" + text[text.index(b):]
    readme.write_text(new, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("assembly", nargs="?", default=str(DEFAULT_ASSEMBLY))
    ap.add_argument("--check", action="store_true", help="verify the existing files only, write nothing")
    ap.add_argument("--steps-js", help="path to the assembly guide's steps.js, to check every PARTS key is mapped")
    args = ap.parse_args()

    for p in PARTS:
        if WINDOWS_BAD.search(p["file"]) or not re.fullmatch(r"(MA01-\d{3}-\d{2}-)?[a-z0-9]+(-[a-z0-9]+)*", p["file"]):
            raise SystemExit(f"bad file name {p['file']!r}")
    if len({p["file"] for p in PARTS}) != len(PARTS):
        raise SystemExit("duplicate file names in PARTS")

    quiet_occt()
    read_source_stamp(args.assembly)
    print(f"reading {args.assembly}")
    doc = read_step(args.assembly)
    _, products, occurrences = walk_assembly(doc)
    rows, unassigned, occ_by_entry = plan(products, occurrences)
    for r in rows:
        copy_frames(products, r, occ_by_entry)   # fails early if copies differ

    if not args.check:
        for r in rows:
            out = REPO / file_path(r["part"])
            write_part(doc, products, r, out)
            print(f"wrote {file_path(r['part'])}")
        write_csv(rows, occ_by_entry, products)
        write_guide_map()
        update_readme(rows, occ_by_entry)
        # remove part files that are no longer in the table
        known = {(REPO / file_path(p)).resolve() for p in PARTS}
        for f in (REPO / "parts").rglob("*.step"):
            if f.resolve() not in known:
                print(f"removing stale {f.relative_to(REPO)}")
                f.unlink()

    ok = verify(products, occurrences, rows, unassigned, occ_by_entry, args.steps_js)
    print("\nALL CHECKS PASSED" if ok else "\nCHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
