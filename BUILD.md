English | [Chinese](BUILD.zh-CN.md)

# YETI60 E73: review and build entry

**Current development direction: [move E73 to the unused lower-right HHKB corner](docs/engineering/e73-hhkb-corner.md).** The new front-mounted candidate is not yet a fabrication release. Its routing, harness and assembly evidence must be completed; the upper-right source-board results below do not qualify the new placement.

**E73 remains on design hold. Do not fabricate the current mainboard as an accepted build.** The [current review](docs/audit/e73-review.md) separates passing electrical/firmware checks from measured USB and connector-service defects. The matching [machine-readable gates](docs/audit/e73-readiness.json) are authoritative for this revision. Raytac acceptance does not qualify E73.

The existing **UDB-C-JSH C5 daughterboard is retained**. Its PCB, connector and mounting pattern need no change for this work. Preserve its fuse/USB protection and verify its four output pins before connecting a mainboard.

| Task | Controlled entry |
|---|---|
| Current findings and remaining work | [E73 review](docs/audit/e73-review.md), [full audit](docs/audit/outcome.json) |
| USB repair checkpoint | [Isolated E73 candidate, native checks and material difference](docs/engineering/e73-usb-repair.md) — unreleased; canonical CAM/firmware unchanged |
| E73 module, pads and MCU configuration | [Vendor land reference](hardware/module-options/e73.json), [pin contract](docs/audit/yeti60-e73-variant.json) |
| Current PCB and manufacturing review files | [Native PCB](hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb), [ordinary four-layer requirements](hardware/ec60-nrf52840/fabrication-notes.md), [DFM review ZIP](hardware/fabrication/yeti60-e73-p2-dfm-review.zip) — design hold applies |
| Parts, package specifications, quantities and inventory | [Preparation list](README.md#complete-materials-for-one-keyboard), [purchase CSV](hardware/bom/mainboard-purchase.csv), [stock allocation](docs/engineering/inventory-allocation.md) |
| Existing daughterboard | [C5 parts](hardware/bom/daughterboard.csv); reuse the already-made board |
| Bare PCB soldering | [Illustrated soldering and assembly guide](docs/assembly/build-guide.md); NiZ, 1.6 mm plate and 28 mounting sets are integrated |
| Current firmware | [Target build/flash instructions](firmware/target/README.md), [normal HEX](firmware/releases/normal/yeti60-e73.hex), [calibrator HEX](firmware/releases/calibrator/yeti60-e73.hex) |
| USB charging and wired priority | [Event/fault evidence](docs/audit/usb-event-policy.json); charging and USB HID coexist after accepted configuration |
| Battery supplier confirmation | [Pack specification](docs/engineering/battery-pack-specification.md); supplier must confirm the stated limits |
| Assembly and signal checks | [Nominal assembly](docs/audit/yeti60-assembly.json), [USB paths](docs/audit/USB-signal-paths.json), [PH withdrawal](docs/audit/e73-service-motion.json) |
| Requested NiZ and plate stabilizers | [E73 mechanism specification](docs/build/key-mechanism.md); 60 sensing centers, three stabilizer pairs, 28 mounts, H26 unused; physical fit pending |
| Verification commands | `YETI_CAD_PYTHON=/path/to/cad/python python3 scripts/run_audit.py --baseline HEAD --refresh-guide`; then `python3 scripts/review_e73_readiness.py --require-design` |

The existing mainboard is ordinary four-layer FR-4, nominal 1.6 mm with mechanically drilled through vias. No blind/buried vias, resin filling or copper capping are required. These process parameters do not remove the design hold. Do not reuse a Raytac mainboard Gerber or firmware image for E73.

E73's USB/charging adapter uses GPIO0 for EN1/EN2 and **GPIO1.13 for CE_N**. Normal/calibrator builds must retain internal RC LFCLK, REG1 LDO and the explicit NFC-pin GPIO UICR setting. The module has five connected bottom lands; edge-only hand soldering is insufficient to connect them. Follow a qualified paste/reflow and inspection process.

Reproduce the complete review with `YETI_CAD_PYTHON=/path/to/cad/python python3 scripts/run_e73_review.py --require-design`. It runs the native/firmware/assembly artifact audit, then RF geometry, USB paths, analog-front-end SPICE, continuous withdrawal and fault gates. After a successful artifact audit for the same inputs, `--reuse-artifact-audit` rechecks current links and integration before reusing it. Design holds return 2; execution failures return 1.

[Current E73 firmware builds, regression evidence and calibration migration](docs/testing/e73-firmware-validation.md).

[Selected M01 plate/floor repair and CAD](docs/engineering/e73-mechanical-fit-candidate.md) now feed the assembly, calibration identity and renders. The [pre-M01 deficit regression](docs/engineering/e73-mechanical-tolerances.md) remains for comparison; full mechanical/service qualification is open.
