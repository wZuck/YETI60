#!/usr/bin/env python3
"""Project-owned nominal package illustrations from manufacturer dimensions.

These are dimensioned visual models, not OEM tooling/tolerance models. The
separate maximum installed envelopes remain the physical acceptance contract.
"""
from pathlib import Path
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from cad_geometry import load, bounds
from check_yeti60_assembly import box
from check_yeti60_interconnects import write_step

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/usb-short-route/models'


def compound(shapes):
    builder = BRep_Builder()
    result = TopoDS_Compound()
    builder.MakeCompound(result)
    for shape in shapes:
        builder.Add(result, shape)
    return result


def charger():
    # TI RGT 16-lead 3 x 3 mm VQFN: 0.5 mm pitch, 1.68 mm nominal EP (RGT0016C, 2025),
    # seated height at the drawing's 1.0 mm maximum. Small pin-1 recess is
    # an illustrative locator, not an asserted OEM mold detail.
    body = box([-1.5, -1.5, .05, 1.5, 1.5, 1.0])
    mark = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(-1.1, 1.1, .97), gp_Dir(0, 0, 1)), .12, .05).Shape()
    body = BRepAlgoAPI_Cut(body, mark).Shape()
    parts = [body, box([-.84, -.84, 0, .84, .84, .05])]
    for at in [-.75, -.25, .25, .75]:
        parts += [box([-1.5, at-.115, 0, -1.1, at+.115, .05]),
                  box([1.1, at-.115, 0, 1.5, at+.115, .05]),
                  box([at-.115, -1.5, 0, at+.115, -1.1, .05]),
                  box([at-.115, 1.1, 0, at+.115, 1.5, .05])]
    return compound(parts)


def switch():
    # C&K JS series, JS102011SAQN drawing (page 4): 8.5 x 3.5 body,
    # nominal 3.5 mm seated height; 2.5 mm contact pitch, 6.8 mm peg pitch,
    # 0.8 mm nominal pegs and 2.0 mm actuator travel. Shell splits and the
    # nonfunctional recess are visual approximations; selected position A.
    housing = box([-4.25, -1.75, .3, 4.25, 1.75, 3.5])
    opening = box([-1.7, -1.8, 1.1, 1.7, -1.25, 2.2])
    housing = BRepAlgoAPI_Cut(housing, opening).Shape()
    actuator = box([-1.6, -3.75, 1.25, -.4, -1.25, 2.05])
    parts = [housing, actuator]
    for at in [-2.5, 0, 2.5]:
        parts.append(box([at-.3, 1.5, 0, at+.3, 3.5, .3]))
    for at in [-3.4, 3.4]:
        parts.append(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(at, 0, -1.5), gp_Dir(0, 0, 1)), .4, 1.8).Shape())
    return compound(parts)


def main():
    for name, shape in [('TI_RGT16_3x3_EP1p68_dimensioned.step', charger()),
                        ('CK_JS102011SAQN_dimensioned.step', switch())]:
        path = OUT / name
        write_step(shape, path)
        print(name, bounds(load(path)))


if __name__ == '__main__':
    main()
