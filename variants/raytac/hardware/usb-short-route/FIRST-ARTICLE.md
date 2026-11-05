English | [Chinese](FIRST-ARTICLE.zh-CN.md)

# Raytac first article: files, order settings and open-bench build

Firmware recovery: [Fn + guarded double-tap for selected-profile clearing and calibration v3 update rules](../../docs/testing/firmware-recovery.md). Ordinary Backspace is preserved; older calibration must be recaptured using the matched candidate pair.

Use this repaired mainboard for the next engineering prototype. Its short USB input, revised fuse, seven 0805 power capacitors and relocated power stage are included in the files below. The previous `yeti60-raytac-p2-dfm-review.zip` describes different routing and is not this board.

**The case is not required for initial electrical validation.** Supplier DFM confirmation precedes PCB production; battery supplier confirmation precedes connecting a real pack. Actual USB/BLE, charging, key calibration and thermal acceptance follow manufacture. These are separate steps: a passing physical keyboard is not a prerequisite for making the first board, and CAM parity is not proof of physical operation or production approval.

## Files to send

Use the [C04 steel plate, revised lower shell and eight gasket strips](MECHANICAL-FIT.md) for the candidate assembly. The previous plate-ear and switch-floor deficits are repaired under the documented dimensional limits. Full keyboard fit, foam/adhesive behavior and connected service remain unqualified; the open-bench sequence below is available.

| Purpose | File | Quantity per keyboard |
|---|---|---:|
| Mainboard PCB; upload to the PCB fabricator | [Candidate Gerbers and separate PTH/NPTH drills](fabrication/yeti60-raytac-candidate-gerbers.zip) | 1 |
| Mainboard bottom stencil; separate stencil order | [Bottom paste and board outline](fabrication/yeti60-raytac-candidate-bottom-stencil.zip) | 1 optional stencil |
| Bare-board electrical-test reference | [IPC-D-356](fabrication/mainboard.ipc) | Accompanies mainboard |
| Placement review | [75-component CSV](fabrication/positions.csv) | Accompanies mainboard |
| Purchasing and stock allocation | [Complete mainboard purchase table](mainboard-purchase.csv), [generic passive specifications](PASSIVES.md) | 75 fitted; 8 planned stock; 67 net purchases |
| Native engineering source | [PCB](EC60-nRF52840.kicad_pcb), [schematic](EC60-nRF52840.kicad_sch), [project](EC60-nRF52840.kicad_pro) | Same candidate |
| Export identification and verification | [Export hashes](audit/fabrication-export.json), [independent CAM readback](audit/fabrication-check.json), [drill summary](fabrication/drill-report.txt) | Keep with order |

The mainboard archive contains nine Gerbers, two drill files and their Gerber job. It contains no C5 board and no previous mainboard Gerbers. The stencil archive contains only B.Paste and Edge.Cuts. JP1's two paste apertures are deliberately omitted in an isolated paste-only export; its PCB copper is retained and JP1 stays open. Do not combine the two ZIPs or mirror their coordinates by hand.

Also use one **C5 JSH**: buy it populated, or separately fabricate the [pinned upstream C5 PCB](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip) and fit its [seven parts](../bom/daughterboard.csv). C5 is 18.0 × 16.5 mm, four layers, 1.6 mm; its stencil is **F.Paste**. Its upstream DFM findings still require review if self-fabricating; a populated C5 is the simpler first-article route. Keep C5's USB protection devices and fuse. No additional SWD PCB is required: J3 is on the mainboard. The 1.6 mm metal plate is a separate [mechanical order](../../docs/build/key-mechanism.md), not another PCB.

## Mainboard order selections

| Field | Selection |
|---|---|
| Board/material | Ordinary rigid FR-4, **4 layers** |
| Layer order | F.Cu → In1.Cu → In2.Cu → B.Cu |
| Finished thickness | **1.6 mm**; the 1.6062 mm CAD envelope is not an ordering option |
| Stack | **JLC04161H-7628**; confirm the stock stack on the returned production drawing |
| Copper | 1 oz outer / stock approximately 0.5 oz inner |
| Size | **289.387 × 94.600 mm** including the RF wing; never crop the wing |
| Finish and mask | ENIG, green mask, white functional silkscreen |
| Vias | Ordinary mechanical through vias; minimum hole/land **0.30/0.50 mm** |
| Slots | Two existing **5.0 × 2.2 mm plated through slots**, included in PTH drilling |
| Special processes | No blind/buried/laser vias, backdrilling, resin filling or copper capping |
| Via covering | Follow the supplied Gerber masks. U5/U6 thermal holes are front-tented, back-open; no filled-via substitution |
| Factory mark | Place outside sensing copper, antenna clearance, holes and component contact areas; request production-file confirmation |
| Electrical test | Test against the supplied IPC/native nets; confirm coordinate alignment |
| SMT assembly | Disable for self-soldering. Placement CSV is review data, not an automatically qualified JLC CPL/BOM |
| Stencil | Bottom side; 0.10 mm stainless is the process-review starting point; review U5/U6 open-via wicking |
| Quantity | One net board per keyboard; account for the platform minimum and desired spares |

The stack and ordinary fabrication choices were checked against [JLC's stack information](https://jlcpcb.com/impedance) and [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities). These are design selections, not a quote or supplier DFM acceptance. Require the actual production preview to preserve the full outline, holes, masks and layer order. If the portal's via-covering option conflicts with the supplied mask pattern, have the supplier confirm the two thermal-via exceptions before production; [JLC distinguishes covering and filling processes](https://jlcpcb.com/help/article/pcb-via-covering).

The drill files contain **846 drill/slot features: 816 plated and 30 nonplated**, including 813 vias and two plated slots. The 29 mounting centres include H26, which remains unused in assembly; four additional nonplated holes locate switches. Use the actual files and drill report rather than inferring hole counts from the 28 installed mounting sets.

## Coordinate and stencil inspection

Gerbers, drills and placement data use the same absolute origin; bottom X is not negated. Gerber/drill/placement lengths are millimetres. IPC-D-356 retains its declared inch encoding, but its auxiliary origin is normalized to zero in a temporary export copy and the reader converts units before comparison. The source PCB is unchanged.

Independent readback compares 289 fitted copper lands and nets, all 75 placements and packages, all drill/slot locations, the outer contour, the two thermal-via mask openings and all 1,444 IPC records. The contour joins require unique endpoint neighbours within 0.001 mm; the maximum observed original gap is approximately 0.000060 mm. This numerical joining is disclosed, not a claim that every Gerber endpoint is identical. See [machine evidence](audit/fabrication-check.json).

U5 thermal via: PCB (117.65, 145.00) mm. U6 thermal via: (133.00, 140.80) mm. Both are ordinary 0.30 mm holes, with front mask coverage and back openings inside their thermal pads. Review paste loss and wetting during the first reflow; do not pay for filling/capping to replace this design. Use the supplied bottom stencil, not the unfiltered default paste export that includes JP1.

## Materials needed before a case exists

Use the complete [shared mechanical/tool checklist](../../README.md#complete-materials-for-one-keyboard), with this candidate's [75-part table](mainboard-purchase.csv), [F1](F1-SELECTION.md), [power positions](POWER-LAYOUT.md), J4/J5 and wiring overriding the previous mainboard rows. Generic passives may be purchased by specification; the selected IC/module/connector identities remain controlled.

For the loose fixture, prepare the [specified SH housings and contacts](README.md#additional-and-changed-materials), four AWG28 USB conductors at **250 mm free length each**, and two AWG28 power-jumper conductors at **300 mm each**. These are housing-exit-to-exit fixture lengths; a crimp supplier calculates cut lengths. Twist D−/D+, keep untwisted ends short and finished data conductors matched within 1 mm. Use stranded copper and compatible insulation OD; for a common SH/PH wire specification use **0.5–0.8 mm OD**. Apply the [resistance purchasing targets](POWER-FEED.md). For the open bench, keep standalone leads and breakouts at **at least 10 mm** bend radius. Form a gently touching data pair with **twist pitch at least 20 mm** and **pair-centreline bend radius at least 25 mm**; a tight twist can overbend each conductor even when the bundle looks gentle. The selected wire's published minimum must be no greater than 10 mm, and every actual wire bend must meet it; larger supplier minima require larger loops and gentler twists. This does not qualify the tighter 4 mm enclosed routes or USB impedance. No mandatory wire brand is imposed.

The protected **1S/4.2 V, 1600 mAh pack remains required**. Obtain the [supplier confirmations](../../docs/build/battery-vendor-checklist.md), including independent thermal interruption, voltage/current limits, cutoff/recovery and pin order. It may sit beside the board on insulation during bench tests; a bare cell is not a substitute. J2.1 = PACK+, J2.2 = PACK−, J2.3 = NTC referenced to PACK−. Do not infer polarity from wire colour. No case, insert bonding or enclosed guides are needed for initial electrical tests. Meaningful 60-key testing still requires the complete specified NiZ/plate/dome/spring/stabilizer stack.

## Start here after the boards arrive

1. Compare incoming boards with this candidate's outline, drill report and native references; inspect holes, mask, exposed pads and shorts. Keep USB and battery disconnected, and JP1 open.
2. Follow the [illustrated soldering order](../../docs/assembly/build-guide.md) for unchanged parts, replacing power positions with [POWER-LAYOUT](POWER-LAYOUT.md) and omitting R30/R31. Solder and inspect U5/U6 and their power passives before the module/AFE. Use [current F1 lands](F1-SELECTION.md).
3. Fit J4/J5, then meter the [candidate connection map](README.md#required-connection-map). The power jumper is mandatory: **J5.1 → J1.1; J5.2 → J1.4**. J1.2/3 stay empty. C5 JSH 1/2/3/4 → J4.1/2/3/4.
4. Support the board and C5 on insulation with all underside parts clear. Keep the loose harness clear of sensing springs, bare solder points and the antenna. Follow [B0–B3 limits](../../OPEN-BENCH.md); this page's wiring replaces the previous J1 data connection. OFF does not isolate the charger: remove USB and battery before resistance checks.
5. Use the [candidate calibrator and SWD instructions](firmware/README.md), then check USB enumeration. These builds are tied to this candidate's board source; use neither E73 binaries nor the previous Raytac release folder.
6. Only after confirming pack identity, polarity and supplier limits, disconnect USB, connect the protected pack, and perform B4–B5 battery/charge checks. Measure current, rails and temperature. Reconnect USB and verify the calibration console remains wired while charging.
7. Complete B6 real-key calibration, flash the candidate normal build, and run B7 USB typing while charging, unplug-to-BLE and reconnect tests. Record results before making the case. Electrical-only bring-up does not certify the complete key mechanism.

The [closed-case assembly](ASSEMBLY.md) is a later stage: plug service trajectories, combined tolerances, wire springback, retention and supplier mechanical parts remain open. The previous fabrication archive stays held, and production acceptance is still false. A supplier-reviewed first article exists to obtain the measurements these remaining qualifications require.

## Reproduce the manufacturing-file checks

Run from the repository root with Git history and initialized submodules. The first command refreshes native checks; export/readback require matching sources. `requirements-cam.txt` pins the independent readers. The example uses this project's macOS KiCad Python path; use the equivalent Python with `pcbnew` on other systems. PCB/firmware changes also require the corresponding firmware rebuild and full audit; CAM checks alone do not release the complete project.

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 variants/raytac/scripts/check_usb_short_route.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 variants/raytac/scripts/export_usb_short_fabrication.py
uv run --python 3.11 --with-requirements variants/raytac/requirements-cam.txt python variants/raytac/scripts/check_usb_short_fabrication.py
uv run --python 3.11 --with-requirements variants/raytac/requirements-cam.txt python variants/raytac/tests/audit/test_usb_short_fabrication.py
```
