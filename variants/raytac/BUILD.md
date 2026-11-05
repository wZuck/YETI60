English | [Chinese](BUILD.zh-CN.md)

# YETI60 Raytac: current ordering and build entry

Start with the [current first-article files and ordering parameters](hardware/usb-short-route/FIRST-ARTICLE.md). This is the Raytac MDBT50Q-1MV2 board with repaired USB/power routing, the C04 plate and the revised bottom shell. The earlier long-route fabrication archive, seven-wire assembly and reference firmware are retained engineering references; use the current files linked here for this build.

The first board can be tested without an enclosure. Supplier DFM precedes fabrication; protected-pack confirmation precedes real-cell connection; real USB/BLE, charging, EC calibration and mechanical acceptance follow manufacture. Current software/CAD evidence does not establish physical operation or production approval.

## Find the required file

| Task | Current document/file |
|---|---|
| Order mainboard PCB and stencil; choose JLC parameters | [First-article order table and downloads](hardware/usb-short-route/FIRST-ARTICLE.md) |
| Buy mainboard parts and subtract inventory | [75-part purchase CSV](hardware/usb-short-route/mainboard-purchase.csv), [generic passive/LED specifications](hardware/usb-short-route/PASSIVES.md), [selected F1](hardware/usb-short-route/F1-SELECTION.md) |
| Obtain or solder C5 JSH | [Seven-part C5 BOM and inventory](hardware/bom/daughterboard.csv), [pinned C5 fabrication ZIP](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip) |
| Buy NiZ housings, domes, springs, plate stabilizers, wires and caps | [K01–K07 mechanism list](docs/build/key-mechanism.md); use the C04 plate below |
| Machine plate; print shell and guides; fit gasket strips | [C04 geometry, tolerances and eight strips](hardware/usb-short-route/MECHANICAL-FIT.md), [closed-case harness and 16 guide pieces](hardware/usb-short-route/CLOSED-CASE.md) |
| Solder from a bare PCB | [Soldering checks](docs/build/soldering.md), [28 illustrated reference steps](docs/assembly/build-guide.md); current [power placement](hardware/usb-short-route/POWER-LAYOUT.md), [F1](hardware/usb-short-route/F1-SELECTION.md) and [PCB surface/assembly maps](hardware/usb-short-route/ASSEMBLY.md) govern changed locations |
| Wire C5 and power jumper | [J4/J5/J1 pin table and connector quantities](hardware/usb-short-route/README.md#required-connection-map), [power-loss targets](hardware/usb-short-route/POWER-FEED.md) |
| Flash and calibrate | [Current matched firmware downloads](hardware/usb-short-route/firmware/README.md), [J3/SWD commands and 60-key procedure](docs/build/flashing.md) |
| Test without a shell, including a battery | [B0–B7 open-bench checks](OPEN-BENCH.md) |
| Check saved calibration and upgrade | [308-byte CRC record, legacy recapture and test limits](docs/testing/calibration-storage.md) |
| Check scanner faults and calibration commands | [Offline/fault handling, key releases and queue tests](docs/testing/scan-control.md) |
| Review analog GPIO and initialization cleanup | [Disconnected digital buffers, AFE shutdown and tests](docs/testing/gpio-mode-policy.md) |
| Review EC pulse and sampling timing | [Edge repair, RC model and first-board timing command](docs/testing/analog-waveform.md) |
| Understand USB charging, suspend and deconfiguration | [Actual USB event policy and test evidence](docs/testing/usb-event-policy.md) |
| Clear a Bluetooth slot / understand calibration changes | [Guarded recovery and version compatibility](docs/testing/firmware-recovery.md) |
| View current assembled/exploded keyboard and assembly steps | [Current candidate assembly guide](hardware/usb-short-route/ASSEMBLY.md) |
| Check battery requirements and runtime calculations | [Supplier checklist](docs/build/battery-vendor-checklist.md), [pack specification](docs/engineering/battery-pack-specification.md), [power calculations and assumptions](docs/engineering/power-budget.md) |
| Assess inspection evidence and remaining acceptance | [Current review](docs/audit/raytac-review.md), [machine outcome](docs/audit/outcome.json), [physical acceptance](docs/testing/README.md) |

## Prepare per keyboard

- One mainboard and optional bottom stencil: ordinary four-layer FR-4, 1.6 mm, 289.387 × 94.600 mm, JLC04161H-7628, ordinary through vias. Send the candidate ZIP from the first-article entry; obtain fabricator DFM. Do not crop the antenna wing.
- **75 fitted mainboard parts: 8 planned from inventory, 67 net purchases**, excluding spares. Count actual stock before ordering. R30/R31 are removed; JP1 stays open. Buy generic passives by the current specification rather than brand. IC/module, inductor, fuse and connector identities remain controlled.
- One populated C5 JSH; alternatively one C5 bare board plus seven components (two planned inventory resistors and five purchases). Retain C5 protection components and fuse. It is a separate PCB order.
- One four-wire C5→J4 USB harness and one two-wire J5→J1 power jumper; J1.2/J1.3 are unused. Prepare three SHR-04V-S housings, one SHR-02V-S housing and 12 fitted SSH-003T-P0.2-H contacts; 20 contacts allows eight spares. Add a USB data cable. Open-bench free lengths are 250 mm per USB wire and 300 mm per jumper wire; final enclosed lengths/radii follow the closed-case guide.
- One protected 1S 1600 mAh pack with three-wire PHR-3 interface, matched NTC and independent voltage/current/temperature protection. A supplier-qualified exact pack is still required. Six interconnect wires plus three pack leads make **nine wires** in the complete current assembly. Pack polarity is J2.1 PACK+, J2.2 PACK−, J2.3 NTC relative to PACK−.
- One C04 304 stainless plate, nominal 1.6 mm with finished thickness 1.55–1.60 mm and **28 M2×0.4 tapped axes**; H26 is unused. Order cutting and tapping, not only laser-cut pilot holes. Add 60 matched NiZ housings/sliders/rings, 60 conical springs, a 45g dome sheet, three plate stabilizer pairs, two short stabilizer wires, a centered 6U wire and matching keycaps as specified in K01–K07.
- 28 custom brass adapters, 28 polyimide rings, 28 PEEK washers and 28 M1.6×5 screws; exact dimensions follow the [mechanism/hardware specification](docs/build/key-mechanism.md). Complete the threads and deburring before approaching electronics.
- For the later enclosed assembly: one current top and one revised bottom shell; 16 routing-guide pieces; eight 33×3 mm gasket strips (four nominal 2.0 mm lower and four nominal 1.2 mm upper); specified M3 shell and M2 C5 inserts/screws/washers, feet, insulation and retention materials. Use the [shared hardware checklist](README.md#complete-materials-for-one-keyboard) with the current C04/closed-case revisions above. Foam properties, installed retention, full connector service and combined tolerances remain qualification items.
- Shared tools: ESD setup, magnifier/microscope, tweezers, soldering/reflow equipment and compatible consumables, meter, current-limited 5 V supply, source/sink battery simulator, USB data host and second keyboard, SWD probe/custom J3 fixture, calipers, current/temperature logging and oscilloscope. Self-crimping needs tools suitable for the chosen SH/PH contacts.

## Build sequence

1. Match the current PCB/CAM/BOM/firmware bundle. Obtain PCB DFM and confirm generic component specifications. Prepare one board first; defer quantity builds until the first board passes.
2. Inspect bare PCB, then solder power parts/F1 and check unpowered before controlled first power. Follow current power positions and surface maps for changed parts; the 28-step guide supplies the retained soldering order.
3. Install C5→J4 and J5→J1 wiring; verify every pin and polarity. Flash the current calibrator through J3. Do not parallel host VBUS with a separate 5 V supply or back-power through the probe.
4. Complete B0–B3 with instruments/simulator. Connect a real protected pack only after supplier acceptance. Complete B4–B5; suspend changes the system supply to the battery.
5. Assemble the real C04/NiZ/dome/spring/stabilizer mechanism on an insulating fixture. Complete B6 per-key capture, save and verify, then flash the matching current normal image while preserving the last 64 KiB settings partition. Changing calibration identifiers requires new capture.
6. Complete B7 and actual simultaneous charging/USB typing, deconfiguration, suspend/resume, detach-to-BLE and repeated attachment. Record physical results; compilation and simulation are separate evidence.
7. Prepare the enclosure only after open-bench acceptance. Use current shell/guide/plate files and bounded tolerances; measure actual parts and retention. Repeat all keys, charging, USB/BLE and interference checks in the enclosure. Do not force closure to overcome a failed fit.
