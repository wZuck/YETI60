English | [Chinese](SERVICE-PATH.zh-CN.md)

# Service path: wing repaired; connected harness still open

**Enclosed service is not yet approved.** The previous right-wing trap is repaired in the current candidate bottom. Continuous nominal rigid extraction now passes, conditional on USB and battery leads already being disconnected and their loose plugs parked outside the moving envelope. This does not prove that disconnection is possible in the assembled case.

[Verification script](../../scripts/check_usb_short_vertical_motion.py) · [Motion evidence](audit/vertical-motion.json) · [Case/skin and insert protection](audit/closed-assembly.json)

## Implemented geometry

- A 0.5 mm corner-radius internal relief spans X 357.25–365.25, Y −132.75–−113.75, Z −4.45–12.30 mm. It removes the right internal step outside the guarded plate-bearing region. Original exterior bounding coordinates and insert-support volumes remain unchanged. Considering both new reliefs, checked remaining skin is at least 2.01 mm after the existing 0.15 mm case tolerance; this does not certify every original wall.
- The rear USB route is now Y −100.80 mm. Roof clips USB-R1/R2/R3 and their films have front/rear half-widths 2.35/2.70 mm. The minimum front groove wall is 0.35 mm nominal, or 0.30 mm after print tolerance. Do not mix old guides or old wire lengths with this case.
- PCB-to-rear-clip swept clearance is 0.75966 mm nominal. Subtracting PCB position 0.25, case 0.15, guide mounting 0.10 and guide print 0.05 mm leaves 0.20966 mm, against a 0.15 mm requirement. These are imposed fit limits to measure on real parts.

## What the continuous check proves

The checker extrudes exact planar PCB and plate footprints through the entire 22 mm travel, including intermediate poses. Conservative swept envelopes cover all 75 fitted mainboard parts, 28 mounting sets, the on-board power jumper, its two plugs and its guides/films: 172 moving envelopes in this revision. Power wires use separate primitive bounds so the low fan-out is not falsely projected into the high straight run. They clear the bottom and fixed guide solids nominally.

The old unrelieved bottom still intersects the PCB and module sweeps. Regression tests reject that bottom, old rear clips and an over-trimmed clip wall. This continuous check replaces the former discrete-pose diagnostic.

## Remaining work

1. Establish full USB J4 and battery J2 unmating/mating trajectories, holding plastic housings and keeping all conductors within a supported bend radius. Side-entry withdrawal changes the distance and direction to the first fixed guide; installed routes do not prove removability. Qualify loose-plug parking and actual tool access before prescribing service. No new access ports are released in this case.
2. Complete combined tolerance analysis. Nominal plate-to-case swept clearance is only 0.25 mm; SW100 has 0.41 mm. Nearest-point coordinates are recorded in the motion report: the plate limits occur on front/rear registration-tab sides, and SW100 is limited by the floor at Z −5.91 mm. The rear-clip calculation does not qualify these other interfaces or arbitrary resin shrinkage and supplier parts. The [directional diagnostic and repair requirements](TOLERANCES.md) confirm the 0.25 mm plate-ear limit in **both shells**. Already quantified terms leave only 0.098 mm at the ears and 0.0562 mm at SW100, before the unqualified terms. These are known reserve deficits, not tolerance acceptance.
3. Include qualified NiZ housings, caps, domes, stabilizers, cable springback and adhesive retention in final motion/first-article checks. The PCB/plate/electronics sweep does not certify these supplier-dependent moving bodies.

Manufacturing remains on hold. [Candidate entry](README.md) · [Assembly guide](ASSEMBLY.md) · [Revised routes](CLOSED-CASE.md)
