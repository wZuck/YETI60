English | [Chinese](e73-mechanical-fit-candidate.zh-CN.md)

# E73 selected M01 plate and switch-floor repair

**M01 is now selected by the canonical E73 assembly, calibration fingerprint and render pipeline.** The three measured plate/floor interfaces pass in the stated dimensional envelopes. This is not complete keyboard or manufacturing acceptance: whole-board extraction, flexible service motion and other part tolerances remain open. The existing C5 daughterboard, PCB, battery datum, sensing centers, stabilizer openings and mounting axes are unchanged.

## Reviewable outputs

- [M01 plate DXF](../../mechanical/e73-fit/yeti60-e73-niz-m01.dxf) and [STEP](../../mechanical/e73-fit/yeti60-e73-niz-m01.step): 1.6 mm 304 stainless steel, with the outer perimeter inset by 0.40 mm.
- [M01 lower shell STEP](../../mechanical/e73-fit/yeti60-e73-bottom-m01.step) and [STL](../../mechanical/e73-fit/yeti60-e73-bottom-m01.stl): internal switch-floor relief only; the original external bounds and eight guarded insert supports are preserved.
- [Acceptance limits](../../mechanical/e73-fit-spec.json), [build/measurement evidence](../audit/e73-fit-candidate.json), [implementation](../../scripts/build_e73_fit_candidate.py) and [ten regression tests](../../tests/audit/test_e73_fit_candidate.py).

The drawing retains all **88 internal DXF entities** verbatim: 60 key/stabilizer profiles and 28 mounting circles. H26 remains empty. The minimum exterior-to-cutout/hole metal web is **1.7498 mm**, above the 1.60 mm nominal design requirement. This is a geometric web check, not strength or plate-flex qualification.

## Dimensional calculation

The plate envelope includes 0.10 mm profile error plus 0.10 mm installed point-position error in XY. A circumscribing polygon adds 0.0001 mm to avoid understating the disk. Each installed upper/lower plate face must remain within ±0.10 mm Z of its nominal position, including thickness, flatness, mounting and gasket compression together.

For each clearance, subtract the shell's conservative three-axis displacement bound, `sqrt(3) × 0.15 = 0.2598076 mm`, and a 0.002 mm computation guard from the exact BRep distance to the enlarged part envelope:

| Interface | Enlarged-envelope distance | Remaining reserve | Required reserve |
|---|---:|---:|---:|
| Plate / lower shell | 0.449900 mm | 0.188092 mm | ≥0.15 mm |
| Plate / upper shell | 0.449900 mm | 0.188092 mm | ≥0.15 mm |
| SW100 / repaired floor | 0.656200 mm | 0.394392 mm | ≥0.15 mm |

SW100 has a required maximum installed height of **3.60 mm below its local PCB surface**, including solder/actuator. This is a measurement limit, not a claimed manufacturer guarantee. The downward allowance is:

```text
Finished PCB growth: 1.7600 − 1.6062 = 0.1538 mm
Shoulder + insulation:                0.0300 + 0.0200 mm
Installed plate face Z error:         0.1000 mm
Additional mounted PCB downward bow:  0.1500 mm
Installed switch height above the
previous 3.50 mm envelope:             0.1000 mm
Total downward enlargement:           0.5538 mm
```

SW100 XY allowance is 0.10 mm installed envelope growth plus 0.25 mm mounted-board point error on each axis. The relief box is X **104.975–119.025**, Y **−127.525 to −114.725**, Z **−6.710 to −5.400 mm**, with 0.50 mm corner radius. It removes **41.9270 mm³**. Distance to the inspected downward/rear/end exterior faces, after the three-axis shell allowance and guard, is **10.5604 mm**, exceeding the local 2.0 mm requirement. This measures the selected exterior skin, not every shell ligament, service-hole wall, impact load or resin strength.

Four **33 × 3 mm** gasket pads per layer remain fully on the plate and actual upper/lower shell bearing faces after the declared placement and profile allowances. Stock is 2.0 mm lower and 1.2 mm upper. Foam compression force, creep and adhesive retention are unqualified.

## Reproduce and integrate

Run `uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/build_e73_fit_candidate.py`, then the same runtime with `tests/audit/test_e73_fit_candidate.py`. The main audit runs both. Tests reject the actual original plate and original floor under these bounds, oversize inset, shifted gasket and an overheight installed switch. Successful execution proves only the reported bounded interfaces.

The assembly uses the M01 plate and bottom references. Normal/calibrator firmware and their calibration identity include the selected plate, fit limits, mechanism and stack specifications. Guides and four assembly views are regenerated from these selected inputs. The build order is acyclic: original shell/PCB metadata → M01 parts → selected plate contract → full nominal assembly → wiring/meshes/rendering. The RF/case screen also reads the selected shell, plate and full 1.6 mm plate height. The legacy `candidate` report/document filenames are retained for stable links; `selected_by_assembly` records the current selection.

The [original deficit calculation](e73-mechanical-tolerances.md) intentionally checks the retained pre-M01 plate and floor. It is regression evidence, not a current assembly result. Whole-PCB extraction, flexible service paths, other part tolerances, received NiZ/stabilizer dimensions and physical electrical/charging/RF tests remain open. See [the complete E73 review](../audit/e73-review.md).
