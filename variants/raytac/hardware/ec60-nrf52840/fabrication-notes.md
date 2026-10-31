English | [Chinese](fabrication-notes.zh-CN.md)

# YETI60 ordinary JLC fabrication requirements

Use **ordinary four-layer FR-4, JLC04161H-7628, nominal order thickness 1.6 mm**. The user excludes HDI and special via fill/capping. The current PCB uses mechanically drilled F.Cu–B.Cu through vias only, minimum land/drill **0.50/0.30 mm**. There are **no blind/buried/laser vias and no module vias-in-pad**. Do not order older HDI exports.

The former nine local blind vias were removed. Local charger/capacitor/timer/termination routes were rerouted; R55/R56 and C40/C41 were relocated. U1.39 and U1.51 now use off-pad through vias; the SWDIO escape adds one intermediate ordinary through via. These routes require native DRC/netlist/physical-connectivity checks; no inference from hole count alone establishes correctness.

## Stock stack and thickness

[Published JLC stock stack](https://jlcpcb.com/impedance): F.Cu 0.035, 7628 prepreg 0.2104, In1.Cu 0.0152, FR-4 core 1.065, In2.Cu 0.0152, 7628 prepreg 0.2104, B.Cu 0.035 mm. CAD additionally models 0.010 mm mask on each face, yielding a **1.6062 mm CAD envelope**. This mask thickness is an engineering model, not a supplier guarantee. Order the ordinary **1.6 mm** product, not a custom 1.6062 mm laminate. [JLC specifies +/-10% finished thickness, 1.44–1.76 mm](https://jlcpcb.com/capabilities/pcb-capabilities/); inspect actual boards and retain the recorded assembly tolerance limits.

The 0.2104 mm sensing dielectric replaces the former 0.200 mm assumption. Electrode copper geometry is retained; capacitance and physical per-key calibration still require hardware qualification. No asymmetric 0.150 mm laser dielectric is requested.

## Assembly and process review

Use green mask and ordinary ENIG finish. Ordinary tenting is permitted; resin filling, planarization and copper capping are not required. U5 retains an ordinary open thermal via in the ground/exposed-pad area: the assembler must review stencil apertures, solder loss and thermal-pad wetting. Do not interpret a tentative CAD check as solder-process qualification.

The [review archive and checklist](../../docs/engineering/fabrication-review.md) include Gerbers, separate PTH/NPTH through drills, IPC-D-356 and 76-part placements. Supplier ordering review, final passive ratings/effective capacitance, waveform/temperature tests and mechanical first articles remain required. RF/SI screening has started; antenna layout blockers remain open.
