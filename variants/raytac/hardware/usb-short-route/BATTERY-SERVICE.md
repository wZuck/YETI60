English | [Chinese](BATTERY-SERVICE.zh-CN.md)

# Low-profile SH3 battery connector and plug motion

Use the specified **SHR-03V-S without protrusions, 4.0 mm wide**. The catalogued **SHR-03V-S-B with protrusions is 6.0 mm wide** and is not covered by the present housing envelope; do not substitute it without a separate fit check. [JST housing table](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

**The SH3 revision has passed the complete artifact checks.** Native electrical checks, CAM round-trip, both matched firmware images, assembly, continuous rigid plug motion, harness documentation and renders were reverified together. Supplier, fabricator and physical qualification still apply below; this is not production release.

J2 now uses **JST SM03B-SRSS-TB(LF)(SN)**, **SHR-03V-S** and three **SSH-003T-P0.2-H** contacts. This is **SH, 1.0 mm pitch**, not the previous 2.0 mm PH interface. Position is **PCB X 155.5 / Y 129.0 mm, 0°, B.Cu**. Pin 1 remains protected PACK+, pin 2 PACK− and pin 3 NTC referenced to PACK−. The board outline, sensing lands, mounting axes and 28 installed mounting sets are retained.

## Why the connector changed

The original PH housing's axial withdrawal envelope hit H8 hardware and the lower shell. A first forward relocation fixed the withdrawal corridor and passed strict native electrical checks, but the actual PH STEP solid then intersected the shell by 7.341 mm³. That forward PH revision was not published. Rotating the PH part introduced further native-copper conflicts. The lower SH3 interface removes the height conflict while retaining three wires and the existing shell exterior.

[JST rates SH at 1 A with AWG28 and 1.0 mm pitch](https://www.jst-mfg.com/product/index.php?lang=2&series=231); the [SH drawing](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf) gives 2.95 mm side-entry height. The project's programmed maximum charge current is 445.63 mA, below its separate 450 mA ceiling. These nominal load/rating comparisons do not qualify fault-current duration, contact heating or protection performance. The pack and short-circuit tests remain required.

The installed header acceptance envelope is 3.20 mm below the local PCB, including solder. This is an imposed incoming/assembly limit, not a new manufacturer guarantee. Its standard KiCad model and all five soldering feet are checked against the replacement native lands. The [replay template](battery-service-j2.json) preserves the source identity and schematic path; the [repair contract](../../scripts/usb_short_battery_service.py) lists native reconnects.

## Electrical and fabrication changes

BAT_CELL, GND and BAT_NTC reconnect to the same numbered pins. Nearby APLEX_EN_PIN_0 travels through In2.Cu between two ordinary 0.30 mm drill / 0.50 mm land through vias, tented on both sides. This candidate has 815 vias. No blind/buried vias, filled vias or special JLC process is introduced. Use the current PCB and manufacturing files together; the older PH footprint and binaries do not describe this revision.

The bare-board connector is one fitted component, so the mainboard remains 75 parts, 8 planned stock credits and 67 net purchases. The protected pack includes one SH3 housing and three SH contacts, preferably supplier-crimped. Complete USB/power/battery wiring uses 15 SH contacts: 12 for the two interconnects and 3 supplied with the pack. Polarity requires a numbered supplier drawing and continuity checks.

## Cable and motion checks

The SH3 wire-exit datum is **case [155.5, −124.425, −3.60] mm**. The connector has 1 mm pin spacing, while the retained bulk battery route and pack exit use 2 mm spacing. A controlled fanout uses 4 mm radius and `sqrt(4*4*1 - 1) = 3.872983 mm` forward run, before the vertical transition. Pin 1/2/3 start at X 154.5/155.5/156.5 mm. USB and the board-side power jumper are retained.

Use the updated [closed-case free lengths](CLOSED-CASE.md): nominal battery wires are approximately **114.92 / 111.61 / 108.63 mm**, not cut lengths. Each has ±0.5 mm free-length tolerance and must be preformed to the controlled path. Existing guide positions and pack-side exit offsets remain; real wire bend limits and crimp/retention acceptance require supplier evidence.

[Continuous rigid-motion checks](audit/plug-motion.json) cover J2/J4 housing bodies at nominal, 1.44 and 1.76 mm PCB thickness. Withdrawal is an entire +Y box sweep with at least 0.50 mm final separation from the header envelope; reversing it covers rigid insertion. The 0.25 mm housing allowance preserves the intentional PCB seating datum. The original PH/H8 and PH/shell obstructions are retained as regression evidence.

This screen does not qualify fingers/tools, friction-lock forces, own-wire deformation, loose-plug parking or connected stack lifting. [JST handling precautions](https://www.jst-mfg.com/product/pdf/eng/handling_e.pdf) require supporting/holding connector bodies and adequate wire slack. Follow [the remaining service limits](SERVICE-PATH.md), the current [supplier checklist](../../docs/build/battery-vendor-checklist.md) and [open-bench tests](../../OPEN-BENCH.md). Rebuild both firmware images and recapture thresholds after this PCB fingerprint change.
