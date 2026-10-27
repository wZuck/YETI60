English | [简体中文](README.zh-CN.md)

# YETI60 audit index

Start with the [comprehensive electrical / firmware / assembly review](yeti60-comprehensive-review.md). Current CAD connectivity passes; the power-loop layout, target application and final mechanical/manufacturing stack are not production-approved.

| Scope | Evidence | Boundary |
|---|---|---|
| Current PCB | [Strict CAD](../../hardware/ec60-nrf52840/audit-current.json), [functional review](yeti60-electrical.json) | 0 DRC errors/opens and 268 physical pairs; power-path measurements are not stability or SI proof |
| Current nRF control core | [Simulation](yeti60-firmware-simulation.json), [trace](yeti60-firmware-trace.csv) | Actual portable C under host ASan/UBSan; peripheral and transport mocks, no target/radio claim |
| Current fit | [Assembly](yeti60-assembly.json), [metadata](yeti60-pcb-mechanical-metadata.json) | Conditional Z stack, source PCB/plate/case checks and provisional pack envelope; manufacturing tolerance not approved |
| Assembly images | [Renders](../../renders/yeti60-assembly/README.md) | Source-derived shell/plate/PCB, illustrative remaining bodies |
| STM32 reference | [Repaired tests](firmware.json), [upstream reproduction](firmware-upstream-reproduction.json) | Original row/column bounds, hysteresis and config repairs; not nRF firmware |
| Historical SPI interface | [BLE-IF validation](../../hardware/ec60-ble-interface/validation.json) | Superseded two-controller prototype, not the current architecture |
| Upstream BOM/CPL | [Manufacturing reference](manufacturing-reference.json) | OPA350 mislabeled U1 restored to U3; 51 original BOM refs, not the new PCB |
| Plate/source CAD | [Plate](plate.json), [mechanical](mechanical.json), [case registration](case-assembly.json) | Three owner-handle metadata repairs, 63 closed profiles, 29 holes, source shell validity; not resin print approval |
| Rear USB | [Datums](typec-location.json), [original path](case-assembly.json) | Rear-only daughterboard; old 8×2 mm probe does not qualify plug/cable/CC assembly |
| Original fabrication files | [Gerber reference](gerber-reference.json) | 38 outline primitives, 653 PTH and 28 NPTH matched quantization; copper/mask/paste parity remained open |

The older upstream PCB report has 25 DRC errors and two plate files each have an Edge.Cuts text error. Those are reference-source findings, not the current YETI60 board's zero-error CAD result. Do not mix their manufacturing files.

Run `python3 scripts/run_audit.py` with KiCad CLI/Python, clang, uv and pinned `requirements-audit.txt`. It records stage failures separately, skips dependent stages after failure and does not turn a partial green result into a production approval. The final command remains nonzero while the overall production review is incomplete. `outcome.json` and `source-inventory.json` describe that broad audit; an inventory hash is not semantic or functional review. Local upstream submodule settings are not published as design changes.

SI/RF analysis remains deferred; no chosen resin insert, complete plug/wire assembly, cell pack, qualified EC stack or on-device firmware/RF result is asserted.
