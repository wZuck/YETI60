English | [Chinese](README.zh-CN.md)

# YETI60 current audit

The [P2 checkpoint](../design-checkpoint.md) describes the current design and remaining physical/supplier work. The comprehensive review records current evidence and acceptance limits. Passing checks is not production approval.

| Scope | Current evidence |
|---|---|
| Unified result | [Stage outcomes](outcome.json), [integration](integration.json) |
| Schematic and PCB | [Fresh schematic parity/ERC](schematic-current.json), [strict CAD](../../hardware/ec60-nrf52840/audit-current.json), [electrical review](yeti60-electrical.json) |
| Firmware core | [Host sanitizer simulation](yeti60-firmware-simulation.json), [trace](yeti60-firmware-trace.csv) |
| Mechanical | [Read-only plate comparison](plate.json), [PCB metadata](yeti60-pcb-mechanical-metadata.json), [conditional assembly](yeti60-assembly.json) |
| Render provenance | [Geometry](yeti60-render-geometry.json), [assembly images](../../renders/yeti60-assembly/README.md), [PCB images/animation](../../renders/ec60-nrf52840/README.md) |
| Documents and files | [Document checks](documentation-check.json), [source inventory](source-inventory.json) |

Run `python3 scripts/run_audit.py` from the root. Requires KiCad CLI/Python, clang and uv; CAD dependencies are pinned in `requirements-audit.txt`. `KICAD_PYTHON` and `YETI_CAD_PYTHON` select installed runtimes; KiCad Python defaults to its macOS path. `--baseline <commit>` selects a connectivity baseline. `--refresh-renders` rebuilds PCB and assembly images, using `requirements-render.txt` for Blender and ffmpeg for PCB animation.

Exit 0 means every implemented current-design check passed. Failed stages return 1 and block dependent stages. `--require-production` returns 2 when checks pass but production requirements remain open. Every run records unresolved `design-constraints.json` requirements; no run currently grants production approval.

Integration ties schematic, connectors, PCB, firmware pins, trace, fit geometry and each render output to current sources and recipes. Design files must remain byte-identical during validation. The inventory records files, not semantic approval; upstream submodule contents and local editor state are excluded.

Only the current single-nRF design is checked. Target firmware builds, C5 selection, battery/recess and charger calculations are implemented; supplier approval, complete harness/plug acceptance, part ratings, manufacturing and physical tests remain open. SI/RF is deferred.

Fault-injection tests verify rejection of reversed USB data contracts, stale traces, component collisions, stale individual views and changed image bytes. They run only after the unmodified integration check passes.

A fresh checkout requires `git submodule update --init --recursive` for the pinned EC60 and FELK60 source geometry.

Procurement, default 1600 mAh recess/catalog screening, separate assembly sheets and power calculations are part of the same audit pipeline. [Engineering evidence](yeti60-engineering.json) checks current source/output hashes and arithmetic. Five negative engineering cases reject changed drawings, thin walls, unapproved drop-in claims, excessive charge current and excessive termination current; the target fault test rejects a USB100 linked descriptor.
