English | [Chinese](yeti60-comprehensive-review.zh-CN.md)

# YETI60 P2 electrical, firmware and assembly review

The current single-nRF52840 design has native CAD checks, buildable USB/BLE targets and conditional assembly evidence. No physical sample exists; passing these checks does not approve production. See [the checkpoint](../design-checkpoint.md) for the selected configuration and [stage outcomes](outcome.json) for the complete current run.

## Electrical and routing

Strict DRC and schematic parity have **0 errors and 0 opens**, with **270 physical pin pairs** connected. Regression checks preserve previously connected baseline pairs and separately identify new component pairs. Functional EC electrodes, the PCB outline and all mounting centers remain at their source geometry. The removed central branding was decoration; electrode rings and ground shielding remain functional copper.

U1 is one Raytac MDBT50Q-1MV2. U1.20 uses P0.04/AIN2 for scan data; U1.21 uses P0.05/AIN3 for the battery divider. R30/R31 remain 0 Ω because the nRF USB PHY incorporates termination. Mux channel mapping comes from the schematic nets. U8 gates the analog front end and U7 gates the 1M:1M divider; firmware avoids back-powering the unpowered AFE and allows battery measurement to settle.

Power routes now use ordinary through-via construction. Input capacitor C40 and charger control resistors were relocated for ordinary routing. The input-capacitor path retains at least 0.25 mm copper; low-current ITERM can use 0.127 mm. [Electrical evidence](yeti60-electrical.json) records current conservative contacted-primitive lengths/widths/via counts, without claiming return inductance, transient or thermal acceptance. Current warning counts are recorded in the strict audit rather than assumed unchanged.

The former nine blind vias and two module signal vias-in-pad have been removed. Use [ordinary JLC four-layer fabrication](../../hardware/ec60-nrf52840/fabrication-notes.md), nominal order 1.6 mm, CAD envelope 1.6062 mm, 0.2104 mm sensing dielectric and mechanically drilled through vias only. Capacitor derating, soldering and regulator/charger thermal performance remain unqualified; RF/SI is deferred.

## Battery, charging and power

Default **1600 mAh** uses the HCP404074 reference cell and a custom complete **85×43×4.8 mm** pack. [Selection evidence](../engineering/battery-study.md) states the bounded 651-model catalog search, full-pack allowance and source discrepancies. The original charge-row rates do not match their mA values; supplier correction is required. A generic two-wire cell or voltage/current-only PCM is not equivalent to the specified independent thermal protection and third-wire NTC.

R40=2.21k, R55/TMR=69.8k and R56/ITERM=1.69k, all 1%, program 402.71 mA nominal / 445.63 mA maximum, a 6.9102 h minimum fast timer, and at most 29.26 mA termination. The factory pack must guarantee an actual cell charging window within 15…43°C. [Equations and scenarios](../engineering/power-budget.md) include tolerance limits, USB input reserve, ideal CC/CV arithmetic and a planning runtime of 106.64 h. These are calculations, not a full-charge or runtime guarantee. Signed pack dimensions/protection and complete physical charging acceptance remain open.

## Firmware

Normal and USB-CDC calibrator ARM ELF/BIN/HEX build from frozen ZMK/Zephyr dependencies. The linked configuration descriptor in each ELF requests 500 mA; before host configuration, charging is disabled with USB100 selected. Suspend disables charging/input, and resume retains accepted configuration. A negative test rejects an ELF descriptor requesting only 100 mA. HEX checks preserve the settings partition.

The actual portable C core runs under ASan/UBSan with scan/mux sequencing, hysteresis/debounce, fault shutdown, report switching, USB modes and reentry tests; HAL behavior is mocked there. Target code supplies GPIO/SAADC, ZMK HID/BLE and persistent calibration. On-device enumeration, bonding, thresholds and key travel remain untested. The [target instructions](../../firmware/target/README.md) define SWD and release/press/save calibration; no pre-calibrated threshold claim is made.

## Assembly, materials and render provenance

The derived resin case retains the FELK60 exterior union **325.700×125.200×31.190 mm**, with bonded insert seats, SW100 access and the default battery recess. The 1.2 mm steel plate, 4.50 mm standoff plus 0.10 mm insulation, 1.6062 mm CAD PCB envelope and M1.6 underside screws form the specified 4.60 mm gap. All 29 mounting centers match; the imposed worst radial screw budget is approximately 0.06163 mm. Actual donor housings/domes, threads and resin shrinkage still require first articles.

The selected pack clears the checked shells, component and fastener envelopes. After ±0.40 mm XY allowance, minimum component gap is 0.555 mm; nominal head clearance is 0.700 mm. Exact pocket-floor distance leaves 3.6585 mm wall after the 0.30 mm allowance. The wall target does not certify strength, creep or impact behavior. Keep the **C5 JSH** daughterboard and four M2 positions; the complete mating plug/harness bend/service route remains an acceptance item.

The [76-part mainboard BOM and mechanical materials](../engineering/materials.md), [separate engineering assembly sheets](../engineering/assembly.md), [PCB animation](../../renders/ec60-nrf52840/README.md) and [studio assembly views](../../renders/yeti60-assembly/README.md) share current source hashes. Case/plate/PCB geometry is unscaled; caps, housings, finishes, component bodies and battery construction have explicitly illustrative parts. Full integration rejects stale individual views or changed image bytes. English and Chinese documents remain separate, with upstream attribution and compatibility library identifiers retained.
