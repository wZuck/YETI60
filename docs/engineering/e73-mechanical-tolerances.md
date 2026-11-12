English | [Chinese](e73-mechanical-tolerances.zh-CN.md)

# E73 nominal assembly and unresolved tolerance limits

The NiZ 1.6 mm plate preserves 60 sensing centers and uses 28 mounting sets, with H26 unused. Its nominal CAD solids do not intersect either shell. **The present external plate profile and SW100 floor do not meet the reserved clearance after known tolerances. Do not manufacture the plate/case as a tolerance-qualified set.** Raytac's C04 inset and switch relief are separate design outputs; they have not been inherited by this E73 revision.

The [current diagnostic](../audit/e73-tolerance-diagnostic.json) measures the actual plate perimeter against each shell and the E73 SW100 envelope against the bottom. The calculation is:

`optimistic remaining gap = measured nominal gap − sum of known directional allowances`

`minimum extra clearance = max(0, 0.15 mm − optimistic remaining gap)`

The 0.15 mm reserve is a project requirement, not a fabricator guarantee. The following subtotals exclude the unresolved terms and therefore cannot be treated as complete worst-case acceptance.

| Interface | Nominal gap | Known allowances | Remaining gap | Extra clearance needed before unknown terms |
|---|---:|---|---:|---:|
| Plate / upper shell | 0.2500 mm | 0.15 mm local shell-wall error + 0.002 mm profile approximation | 0.0980 mm | At least 0.0520 mm |
| Plate / lower shell | 0.2500 mm | Same | 0.0980 mm | At least 0.0520 mm |
| SW100 / lower floor | 0.4100 mm | 0.1538 mm finished-board growth + 0.03 mm shoulder + 0.02 mm insulation + 0.15 mm floor error | 0.0562 mm | At least 0.0938 mm |

The board-growth term is **1.7600 − 1.6062 = 0.1538 mm**, retaining the ordinary JLC 1.44–1.76 mm board-thickness range and a fixed PCB top datum. It must not be replaced with a rounded 1.6 mm CAD thickness.

Plate cutting/registration, installed XY translation/rotation, Z setting and foam compliance remain unquantified. SW100 additionally needs a maximum installed height including solder and actuator, mounted-board bow and a complete service-port clearance. These are separate from the positive nominal hole/screw margins. Actual NiZ N+ clips, housing skirts, wire bends, dome preload and full key travel require received-part samples.

Repair the plate's external locator clearance while preserving every key/stabilizer opening and 28 tapped axes. Establish an installed switch envelope, then relieve only the internal lower floor with a checked remaining wall. Regenerate the full case/plate envelopes and continuous installation/service paths. Do not alter the existing C5 daughterboard or solve the deficit by lowering the PCB into the battery.

The [diagnostic implementation](../../scripts/study_e73_mechanical_tolerances.py) and [ten fault tests](../../tests/audit/test_e73_tolerances.py) reject omitted terms, missing shell interfaces and relabelled manufacturing approval. Passing these tests means the deficit is recorded correctly. The [E73 review](../audit/e73-review.md) retains the design hold.

CAD evidence is reproduced with **CPython 3.14.7** and `requirements-audit.txt`; the audit/review defaults select that interpreter through uv. A CPython 3.11 execution produced two wire-length differences of about 3e-14 mm while all geometry and other report fields were identical. These differences are immaterial geometrically but change whole-report hashes. Keep report and mesh generation on one runtime; changing runtimes requires regenerating affected evidence, never rewriting stored hashes. Native KiCad export and Blender use their own declared runtimes.

The [M01 repair candidate](e73-mechanical-fit-candidate.md) now passes the three interfaces using enlarged installed-part envelopes. It preserves the selected canonical files while integration is pending; it does not retrospectively change this baseline diagnostic.
