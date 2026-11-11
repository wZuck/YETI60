English | [Chinese](OPEN-BENCH.zh-CN.md)

# Raytac open-bench prototype, including a battery

B0–B7 below use the current candidate: four C5→J4 wires, two J5→J1 wires and three battery leads, nine total; J1.2/J1.3 stay unused. Flash the [current matched calibrator/normal bundle](hardware/usb-short-route/firmware/README.md). Suspend/resume requires a qualified protected pack or suitable battery simulator: without a battery, disabling USB input can remove system power. [USB event/deconfiguration acceptance](docs/testing/usb-event-policy.md) covers host deconfiguration, reset, suspend and resume.

Battery supplier verification is user-owned: [send this parameter checklist](docs/build/battery-vendor-checklist.md). USB repair proceeds in parallel.


**Battery operation is required. An enclosure is optional for the first prototype.** Use the repaired board from the [current first-article entry](hardware/usb-short-route/FIRST-ARTICLE.md); obtain fabricator DFM before manufacture. The previous long-USB archive remains held. Obtain pack confirmation before connecting a real cell. DRC and manufacturing-file consistency do not replace physical acceptance.

This guide separates first power-up without a cell from the required battery, charging and 60-key tests. It does not omit the battery from the finished keyboard. A battery may sit in an insulated external tray during open-bench testing; this does not qualify its eventual fit inside FELK60.

## What to prepare

| Item | Quantity | Requirement |
|---|---:|---|
| Raytac mainboard | 1 for assembly | Use the [current candidate files/parameters](hardware/usb-short-route/FIRST-ARTICLE.md), ordinary JLC four-layer fabrication; supplier DFM before manufacture, physical measurements after the first board |
| C5 JSH | 1 populated board | Retain all seven fitted parts, especially data/power protection and fuse; [materials](hardware/bom/daughterboard.csv) |
| Mainboard electronics | 75 fitted parts | [Current inventory-aware list](hardware/usb-short-route/mainboard-purchase.csv); planned 8 stock, 67 purchases. Use [passive specifications](hardware/usb-short-route/PASSIVES.md) and the selected F1 |
| NiZ plate and mechanism | 1 plate and 60 active keys | [K01–K07](docs/build/key-mechanism.md) and [C04 plate](hardware/usb-short-route/MECHANICAL-FIT.md), three plate stabilizer pairs, two short wires, centered 6U wire and caps |
| Plate/PCB hardware | 28 sets | [Mechanical list](docs/engineering/materials.md); H26 unused. No resin enclosure screws/inserts/gaskets are needed for an open bench |
| Protected battery pack | **1, mandatory for battery acceptance** | Default 1600 mAh, 1S 4.2 V CC/CV, >=500 mA continuous charge rating, separate cell-coupled charger NTC and independent temperature interruption. [Full supplier specification](docs/engineering/battery-pack-specification.md); no accepted exact pack exists yet |
| Power/data harness | 1 complete set | Four C5→J4 wires, two J5→J1 jumper wires and three SHR-03V-S battery leads. Follow the [current pin table](hardware/usb-short-route/README.md#required-connection-map); nine wires total, J1.2/J1.3 unused |
| Computer / terminal with another working keyboard | 1 | USB data host and serial terminal; issue calibration commands with the laptop keyboard or a second keyboard while YETI60 is uncalibrated |
| SWD probe | 1 | nRF52840-compatible, 3.3 V VTref; custom six-pad J3 fixture |
| Insulating PCB fixture | 1 | Stable, nonconductive, components clear of the table; initial >=12 mm underside clearance, increase if actual connectors/heads require. Support at verified mechanical locations; no clamp on electrodes, components or antenna |
| Cell tray and retention | 1 | Nonconductive; no compression, exposed terminals, tab bending or weight suspended from leads |
| Bench instruments | 1 set | Meter, current-limited 5 V supply, protected USB data source/current measurement, oscilloscope and independent cell/charger temperature measurements |
| Battery simulator | 1 for protection testing | Must source **and sink** >=0.5 A over the required 1S range, or use a suitable SMU. A normal source-only bench supply is not a battery simulator |

Use the [current soldering sequence/changed positions](docs/build/soldering.md) with the [28-step reference guide](docs/assembly/build-guide.md). Keep calibrated firmware, plate, PCB and logs together. The present board has no qualified autonomous software low-voltage shutdown; battery reporting is disabled. Do not substitute a generic 2.4 V-cutoff PCM for the specified cell's 3.0 V operating cutoff.

## Sequence and recorded pass conditions

| Gate | Setup / action | Record before continuing |
|---|---|---|
| B0 incoming, unpowered | Check PCB outline/thickness/holes, plate thickness, 28 adapters, H26 omission, polarities, all rails and harness pins. Verify actual NiZ/stabilizer fit locally | No short; usable threads; no screw bottoming, washer/component contact or forced alignment. [Current C04 tolerances](hardware/usb-short-route/MECHANICAL-FIT.md) |
| B1 first power, no battery | C5 and host disconnected. Feed isolated, current-limited 5.0 V to mainboard J1 pin1 VBUS and pin4 GND, initially 100 mA; leave data pins alone. Check SW100 off/on, VSYS and 3.3 V | Correct polarity, stable rails, no abnormal heat or sustained current limit. Do not simply raise the limit after a fault. This direct-feed test does not exercise C5 protection |
| B2 SWD / host USB, no battery | Disconnect the bench supply. Connect populated C5→J4 and the mandatory J5→J1 jumper to a protected host USB data port; flash/verify calibrator through J3 with VTref only | Both firmware images enumerate correctly, descriptors request USB500 after configuration, CDC shell works on calibrator. **Never parallel an external 5 V source with host VBUS** |
| B3 battery interface simulation | Use a source/sink battery simulator at J2 pin1 PACK+, pin2 PACK−. Test third-pin NTC conditions with a resistor substitution fixture only while no real cell is attached | Measured charge-current direction, input limit, termination, suspend/reset/detach behavior, temperature-fault inhibition and no abnormal rails. See charging checks below |
| B4 actual battery discharge | After supplier pack acceptance and polarity/NTC checks, unplug USB and simulator; connect the protected pack. Put it in the insulated tray and power on | Stable 3.3 V, BLE advertisement/pairing/reconnection. Monitor cell voltage/current/temperature; initially stop manually at loaded 3.2 V. Do not deliberately deep-discharge a real pack to prove PCM cutoff |
| B5 actual concurrent charging / USB | At accepted room temperature and under supervision, connect C5 to a configured host while the accepted pack remains attached | Pack-side current is charging while USB enumeration/CDC traffic remains active; no resets or abnormal heat. Key reports are checked after B6 calibration. Repeat USB suspend/resume/reset/unplug and reconnection. USB500 is the shared input budget, not 500 mA into the cell |
| B6 complete EC mechanism, still no shell | Assemble the 60-key plate/PCB/dome/spring stack on the insulating fixture, using 28 sets and omitting H26. Calibrate all 60 keys | Every key and Fn/BLE-profile selection works; repeat B4/B5 using real key reports on BLE and while USB charging. Enter/left Shift/6U return from both ends without binding; neighboring keys stay released during wide-key operation |
| B7 full cycle and off-state behavior | Record an accepted pack's complete CC/CV/termination cycle with board on/configured USB; separately evaluate board-off USB100 charging | Termination before allowed timer behavior, approved cell/IC temperatures, no pack swelling, measured capacity/runtime and switch-off leakage. Do not toggle /CE or power repeatedly to defeat a timer fault |

The numeric current limit and fixture clearance are starting conditions, not measured results. Verify actual instrument behavior and component/connector heights. Open-bench success does not close enclosed RF/USB, resin shrinkage, insert strength or final battery fit.

## Charging and battery rules

- J2 is custom: **1 PACK+, 2 PACK−, 3 NTC referenced to PACK−**. A two-pin JST battery is not a direct substitute; housing fit and wire colors do not establish polarity.
- Main charging is 1S CC/CV with nominal 4.2 V; the supplier must accept actual 4.16–4.23 V regulation and calculated maximum 445.63 mA. No USB-PD/QC negotiation is implemented. Do not inject 9/12 V.
- After charger GPIO initialization, while firmware keeps running, host configuration enables USB500 charging and USB HID priority. Before configuration charging is disabled; suspend inhibits input/charging. A charge-only adapter does not configure USB. SW100 off permits hardware USB100 slow charging; this is a separate test, not a promised full-charge time.
- Simulated hot/cold, open/short sensor, timer and protection faults are tested with a simulator/resistor fixture, **not by abusing a real pouch**. Never leave an NTC bypass resistor installed with a real cell.
- The USB input fuse is not protection against a short directly across the battery connector. Independent pack voltage/current/temperature protection and verified cutoff/recovery are required.
- The default complete 85×43×4.8 mm package is still a supplier drawing request. Do not buy a bare HCP404074 and add PCM/sensors/wrap outside that envelope. A thicker external prototype pack may simplify bench handling only if its electrical/safety specification is independently accepted; it does not replace the final pack fit study.

## What can be proven without an enclosure

An open bench can verify programming, real USB/BLE operation, charging while typing, 60-key calibration, stabilizer travel, voltage/current/thermal behavior, and controlled battery cycles. It cannot guarantee that an unbuilt board will work. The current candidate supplies repaired routing and manufacturing files; fabricator DFM, pack qualification and first-board measurements remain separate requirements.

[Build handbook](BUILD.md) · [Current review](docs/audit/raytac-review.md) · [Machine-readable research](docs/audit/prototype-research.json) · [Physical acceptance](docs/testing/README.md)

Capture [startup, MCU reset and USB bus reset separately](docs/engineering/power-states.md): undriven charger GPIO permits hardware USB100 charging. B3 must also characterize loss of battery support during suspend, without a real cell; record reboot/rail/input-current behavior rather than accepting reboot as successful suspend. Off-current is not zero; a J2-output measurement excludes internal pack-protection consumption.
