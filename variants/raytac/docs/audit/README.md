English | [Chinese](README.zh-CN.md)

# YETI60 current audit

The [P2 checkpoint](../design-checkpoint.md) describes the current design and remaining physical/supplier work. The comprehensive review records current evidence and acceptance limits. Passing checks is not production approval.

[Feasibility and component compatibility assessment](2026-10-28-feasibility-assessment.md)

| Scope | Current evidence |
|---|---|
| Interference and acceptance | [Current holds, simulations and physical procedure](../../../../docs/testing/README.md); CAD passes do not close RF acceptance |
| Unified result | [Stage outcomes](outcome.json), [integration](integration.json) |
| Schematic and PCB | [Fresh schematic parity/ERC](schematic-current.json), [strict CAD](../../hardware/ec60-nrf52840/audit-current.json), [electrical review](yeti60-electrical.json) |
| Firmware core | [Host sanitizer simulation](yeti60-firmware-simulation.json), [trace](yeti60-firmware-trace.csv) |
| Illustrated installation | [28-step guide](../assembly/build-guide.md), [image/reference validation](yeti60-build-guide-check.json), [plate/copper/firmware mapping](yeti60-key-geometry.json) |
| Mechanical | [Read-only plate comparison](plate.json), [PCB metadata](yeti60-pcb-mechanical-metadata.json), [conditional assembly](yeti60-assembly.json) |
| Render provenance | [Geometry](yeti60-render-geometry.json), [assembly images](../../renders/yeti60-assembly/README.md), [PCB images/animation](../../renders/ec60-nrf52840/README.md) |
| Documents and files | [Document checks](documentation-check.json), [source inventory](source-inventory.json) |

Run `python3 scripts/run_audit.py` from the root. Requires KiCad CLI/Python, clang and uv; CAD dependencies are pinned in `requirements-audit.txt`. `KICAD_PYTHON` and `YETI_CAD_PYTHON` select installed runtimes; KiCad Python defaults to its macOS path. `--baseline <commit>` selects a connectivity baseline. `--refresh-renders` rebuilds PCB and assembly images, using `requirements-render.txt` for Blender and ffmpeg for PCB animation.

Exit 0 means every implemented current-design check passed. Failed stages return 1 and block dependent stages. `--require-production` returns 2 when checks pass but production requirements remain open. Every run records unresolved `design-constraints.json` requirements; no run currently grants production approval.

Integration ties schematic, connectors, PCB, firmware pins, trace, fit geometry and each render output to current sources and recipes. Design files must remain byte-identical during validation. The inventory records files, not semantic approval; upstream submodule contents and local editor state are excluded.

Only the current single-nRF design is checked. Target firmware builds, C5 selection, battery/recess and charger calculations are implemented; supplier approval, complete harness/plug acceptance, part ratings, manufacturing and physical tests remain open. SI/RF screening has started; minimum antenna-copper clearance screening passes; USB SI and enclosed RF qualification remain open.

Fault-injection tests verify rejection of reversed USB data contracts, stale traces, component collisions, stale individual views and changed image bytes. They run only after the unmodified integration check passes.

A fresh checkout requires `git submodule update --init --recursive` for the pinned EC60 and FELK60 source geometry.

Procurement, default 1600 mAh recess/catalog screening, separate assembly sheets and power calculations are part of the same audit pipeline. [Engineering evidence](yeti60-engineering.json) checks current source/output hashes and arithmetic. Five negative engineering cases reject changed drawings, thin walls, unapproved drop-in claims, excessive charge current and excessive termination current; the target fault test rejects a USB100 linked descriptor.

[Ordinary-process checks](yeti60-ordinary-process.json) · [Fabrication archive](yeti60-fabrication.json) · [README materials parity](yeti60-materials.json) · [Interconnects](yeti60-interconnects.json) · [Assessment response](../engineering/assessment-response.md)

After changes to guide sources such as the scanner, key map or target firmware README, use `python3 scripts/run_audit.py --refresh-guide` to regenerate and verify the guide; do not overwrite hashes alone. The [USB event tests](usb-event-policy.json) compile the pinned ZMK USB callback; ARM checks decode actual init-to-wrapper and wrapper-to-stack calls. The earlier USB-event review's [follow-up record](usb-event-followup.json) retains its initial result and executed commands as a historical snapshot; it does not replace the current outcome. A failed check cannot become passed without execution.

The added [EC waveform study](../testing/analog-waveform.md) stage requires ngspice and host Clang on PATH, plus NumPy/Matplotlib in the CAD environment. It traces the actual core and models passive RC sensitivity using actual netlist values; it does not measure key capacitance or model op-amp dynamics.

The audit adds the [GPIO-mode/startup cleanup stage](../testing/gpio-mode-policy.md), checking actual callback/init sources and core against a host pin model. Physical leakage and rails remain first-board acceptance items.

Commands reject unavailable startup; runtime scan faults power down the AFE, release tracked keys and reject further capture/save. Both images use a 128-entry key-event queue. See [scanner lifecycle/fault regression](../testing/scan-control.md), including the actual worker, 60-key capture and a 120-event burst. Real host delivery remains first-board acceptance work.

Calibration now uses a 308-byte record with its own CRC-32; older 304-byte records require recapture. Global NVS settings formats and Bluetooth bonds are unchanged. See [calibration storage and upgrade](../testing/calibration-storage.md). Corruption is host-tested; physical flash power-loss acceptance remains open.

The [pinned NVS recovery model](../testing/nvs-powercut.md) executes actual NVS/calibration-load code across 14,795 selected interruption trials, including GC and a second cut during recovery, with sentinel preservation and successful later saves. It is not physical NVMC/brownout/Bluetooth acceptance. The NVS model itself is test-only; `--host-tests-only` can recheck existing candidate artifacts and republish tests, while changed firmware inputs require a full build.

The NVS-model review's [guide follow-up record](nvs-guide-followup.json) preserves the initial guide-hash failure, skipped stages and actual reruns. It is a historical snapshot of that run; the current outcome remains authoritative and unexecuted checks cannot become passed.
