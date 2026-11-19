English | [Chinese](e73-project-files.zh-CN.md)

# Open the correct E73 PCB project

The current lower-right, front-mounted E73 board is **CORNER-04**. Its controlled source is [the corner project](../../hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pro), with the [PCB](../../hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb) in the same directory. Open that project in KiCad, then its PCB editor. The delivery snapshot includes the project, all schematic sheets, local symbol/footprint libraries and local models under `01-pcb/source/`.

Do not identify revisions from the common filename `EC60-nRF52840`: several historical candidates use it. `hardware/ec60-nrf52840` is the old baseline, `hardware/e73-usb-repair` is the intermediate source, and `variants/raytac` is the other module option. They are not the selected corner board.

| Native-board check | Expected selected revision |
|---|---|
| U1 module | Front, origin X332 / Y195 mm, angle 0°; body at PCB X332–350 / Y182–195 mm |
| J5 power bridge header | Back, X335.5 / Y117.5 mm, angle 180° |
| J4 USB header | Back, X346.1 / Y110.7 mm, angle 90° |
| Outline | 285.0 ×94.6 mm, removed old upper-right wing |
| Key layout | 60 active HHKB sensing positions; unused SW72/SW73 electrodes removed |
| Fabrication | Ordinary 4-layer FR-4, nominal 1.6 mm; mechanical through vias |

`b523e60` introduced the corner PCB on 2026-11-14. `7d8b826` completed routing/reference repair; `91aa2f1` removed copper stubs; `d8c1bf0` committed the reversed J5 and its local routing repair on 2026-11-17. Subsequent retainer/film work changes mechanical assets without changing copper.

The `.kicad_pro` file stores project configuration. Its modification time does not track every footprint or trace edit; the actual PCB geometry is in `.kicad_pcb`. Use Git content/history and the SHA-256 entries in the delivery `manifest.json` to identify the snapshot, rather than Finder timestamps. The copied PCB and the firmware manifest must share the same board digest.

The PCB's historic switch 3D model links are not the selected NiZ mechanism, and some depend on old local KiCad model paths. A native 3D preview is not complete assembly evidence. Use the current [mechanism](key-mechanism.md), [harness](../engineering/e73-corner-harness.md) and [retainer](../engineering/e73-retention.md) documents; see the [current assembly views](e73-assembly-views.md) for the complete stack. Service qualification remains open.
