#!/usr/bin/env python3
"""Check original case registration, intersection and rear aperture geometry.

Run: uv run --with cadquery-ocp python scripts/check_case_assembly.py
An 8x2mm diagnostic core proves an open path, not a real plug-envelope fit.
"""
import hashlib
import json
import math
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise ValueError(f"Cannot load STEP: {path}")
    shape = reader.OneShape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError(f"Invalid STEP shape: {path}")
    return shape


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    lower, upper = box.CornerMin(), box.CornerMax()
    return [lower.X(), lower.Y(), lower.Z(), upper.X(), upper.Y(), upper.Z()]


def cylinders(shape):
    cast = getattr(TopoDS, "Face_s", None) or TopoDS.Face
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    result = []
    while faces.More():
        face = cast(faces.Current())
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            point, direction = cylinder.Axis().Location(), cylinder.Axis().Direction()
            result.append({"radius_mm": cylinder.Radius(),
                           "axis_xyz": [point.X(), point.Y(), point.Z()],
                           "direction": [direction.X(), direction.Y(), direction.Z()],
                           "bounds_mm": bounds(face)})
        faces.Next()
    return result


def intersection_volume(first, second):
    operation = BRepAlgoAPI_Common(first, second)
    operation.Build()
    if not operation.IsDone():
        raise ValueError("Case intersection operation did not complete")
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(operation.Shape(), properties)
    return abs(properties.Mass())


def main():
    inputs = [ROOT / "felk60/felk60_bottom.step", ROOT / "felk60/felk60_top_hhkb.step"]
    bottom, top = map(load, inputs)
    bottom_cylinders, top_cylinders = cylinders(bottom), cylinders(top)
    top_bores = [c for c in top_cylinders if 1.25 < c["radius_mm"] < 1.28 and abs(c["direction"][2]) > .999]
    bottom_bores = [c for c in bottom_cylinders if abs(c["radius_mm"] - 1.7) < .0001 and abs(c["direction"][2]) > .999]
    if len(top_bores) != 4 or len(bottom_bores) != 4:
        raise ValueError("Expected four case screw bores in both halves")
    remaining = list(bottom_bores)
    registration = []
    for bore in top_bores:
        candidate = min(remaining, key=lambda c: math.dist(c["axis_xyz"][:2], bore["axis_xyz"][:2]))
        offset = math.dist(candidate["axis_xyz"][:2], bore["axis_xyz"][:2])
        if offset > .0001:
            raise ValueError("Case screw axes do not register in STEP coordinates")
        registration.append({"xy_mm": bore["axis_xyz"][:2], "axis_offset_mm": offset,
                             "top_pilot_diameter_mm": 2 * bore["radius_mm"],
                             "bottom_clearance_diameter_mm": 2 * candidate["radius_mm"]})
        remaining.remove(candidate)
    overlap = intersection_volume(bottom, top)
    if overlap > .00001:
        raise ValueError(f"Case halves intersect by {overlap} mm3")

    # These four cylinders are the rounded corners of the small USB aperture.
    aperture = [c for c in bottom_cylinders if abs(c["radius_mm"] - 1.255) < .0001
                and abs(c["direction"][1]) > .999 and c["bounds_mm"][1] > -104
                and c["bounds_mm"][4] < -102 and 200 < c["bounds_mm"][0] < 230]
    if len(aperture) != 4:
        raise ValueError("Cannot uniquely identify the original USB aperture")
    low = [min(c["bounds_mm"][i] for c in aperture) for i in range(3)]
    high = [max(c["bounds_mm"][i + 3] for c in aperture) for i in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high)]
    rear_y = bounds(bottom)[4]
    origin = [center[0] - 4, low[1] - .1, center[2] - 1]
    length = rear_y + 1 - origin[1]
    probe = BRepPrimAPI_MakeBox(gp_Pnt(*origin), 8.0, length, 2.0).Shape()
    collisions = [intersection_volume(case, probe) for case in (bottom, top)]
    if max(collisions) > .00001:
        raise ValueError(f"Rear diagnostic probe is obstructed: {collisions}")

    constraints_path = ROOT / "design-constraints.json"
    constraints = json.loads(constraints_path.read_text())["external_usb_c"]
    if constraints["required_face"] != "rear" or constraints["front_port_allowed"]:
        raise ValueError("Rear-only USB constraint was changed")
    if constraints["connector_path"] != "rear-daughterboard-to-J1" or constraints["onboard_USB1_external_port_allowed"]:
        raise ValueError("FELK60 aperture requires the rear USB daughterboard path")
    metadata = json.loads((ROOT / "docs/audit/pcb-metadata.json").read_text())
    pcb = next(b for b in metadata if b["source"].endswith("/EC60.kicad_pcb"))
    pcb_path = ROOT / pcb["source"]
    if hashlib.sha256(pcb_path.read_bytes()).hexdigest() != pcb["source_sha256"]:
        raise ValueError("Stale PCB metadata")
    parts = {p["reference"]: p for p in pcb["footprints"]}
    rear_row_world_y = [-parts[r]["xy_mm"][1] for r in constraints["baseline_rear_row_references"]]
    if not center[1] > max(rear_row_world_y):
        raise ValueError("Aperture is not behind the rear key row")
    report = {"status": "case-registration-no-volume-overlap-and-rear-path-checked-full-fit-unverified",
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [*inputs, constraints_path, pcb_path]},
              "PCB_to_STEP_xy": "STEP x = PCB x; STEP y = -PCB y; PCB z placement unverified",
              "case_screw_axes": registration, "case_intersection_volume_mm3": overlap,
              "volume_tolerance_mm3": .00001,
              "rear_USB_aperture": {"bounds_mm": [*low, *high], "center_mm": center,
                                    "width_mm": high[0] - low[0], "height_mm": high[2] - low[2],
                                    "outward_direction": "+STEP_Y (keyboard rear)",
                                    "diagnostic_probe_cross_section_mm": [8.0, 2.0],
                                    "probe_collision_volume_mm3": collisions,
                                    "onboard_USB1_x_offset_mm": abs(parts["USB1"]["xy_mm"][0] - center[0]),
                                    "required_connector_path": "rear USB daughterboard -> EC60 J1"},
              "unverified": ["actual daughterboard connector and plug/overmould envelope",
                             "PCB/plate/switch/gasket full Z assembly",
                             "resin inserts and fabrication tolerance; original top bores remain metal-thread pilots",
                             "battery, radio module, antenna and cables"]}
    destination = ROOT / "docs/audit/case-assembly.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
