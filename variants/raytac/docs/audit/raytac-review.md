English | [Chinese](raytac-review.zh-CN.md)

# Raytac review conclusions

**All 52 implemented software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.

| Area | Result |
|---|---|
| PCB | 0 errors / 0 opens; 267 signal pairs |
| DRC | 102 disclosed noncomponent courtyard warnings |
| ERC | 0 errors; 183 inherited off-grid warnings |
| JLC | 816 ordinary through vias; >=0.50/0.30 mm land/drill |
| USB / BLE | Normal/calibrator ARM builds and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested |
| RF | All four layers clear in vendor minimum antenna projection; physical RF open |
| BOM | 75 parts; 10 planned from stock, 65 net purchases |

## Repairs and image inspection

- USB mainboard D1 and long branches removed after actual C5 protected-channel/ground verification; C5 D1/U1/F1 retained
- Shared analog/discharge net labels unified without changing exported pin connectivity
- 75-part purchase, stock allocation, placement and illustrated guide contracts reconciled
- Complete explosion includes 75 electronic bodies, battery, seven wires, 60 domes/springs and hardware; tray camera/desk bounds checked
- NiZ ordinary housings/sliders and separate Cherry plate-mounted stabilizers selected; 1.6 mm plate, 28 mounts and H26 unused; 60 sensing centers and exterior preserved; actual wire/clip/stroke fit awaits a first article
- Second review corrected stale 29-fastener inventory/acceptance prose and 1.2 mm render descriptions in both languages; negative tests now reject their return
- Current RF status distinguishes passing minimum antenna-copper clearance from unqualified USB signal integrity and enclosed RF; historical reviews remain labeled snapshots
- Broken tracked Raytac third_party/zmk link repaired to the pinned repository submodule; all tracked shared links now checked and missing-source fault injected

## Functional coverage and test boundaries

| Function | Evidence and remaining boundary |
|---|---|
| 60-key scan | [Geometry/map](yeti60-key-geometry.json); host core tests all 75 matrix positions, hysteresis, debounce and ADC frame abort. Real EC waveforms remain unmeasured. |
| Calibration | [Guard tests](calibration.json); inspect the target release/press/save flow, 128-frame capture, saturation/overlap rejection and persistent thresholds. First-article capture and flash retention remain open. |
| USB priority | [Actual adapter host regression](yeti60-firmware-simulation.json) covers configured charging plus USB preference, retained BLE preference, suspend/resume/reset/detach and failure retries. USB/BLE interfaces are mocks. |
| Power | [Current/timer arithmetic](yeti60-power-budget.json), enable-net and adapter review agree with BQ24074 input modes. Off-state USB100 charging differs from firmware-controlled charging. Actual thermal/current behavior remains open. |
| Firmware | [Existing normal/calibrator ARM artifacts](yeti60-target-check.json) rechecked against current source hashes, flash ranges and linked USB500 descriptors. No firmware source changed or rebuild was required in this mechanical review; this is not target execution. |
| Assembly | [Native fit](yeti60-assembly.json), [plate](plate-mount.json), 28 mounts / H26 omission, 1.6 mm plate, seven conductors and image provenance checked. Actual NiZ skirts/clips, 6U bends, preload and local stiffness remain open. |

## Specific USB routing limitation

Mainboard D+ / D− actual trace centerlines are approximately **253.541 / 249.122 mm**, through **4 / 6 vias**. The pad-access/contact-bridge geometric path difference is **2.165 mm**, not propagation-delay skew. C5, harness, connector and module internals are excluded. Protected connectivity and DRC do not establish differential impedance, continuous return, common-mode behavior or a passing USB eye. Review the complete link and measure it with the final harness before manufacturing release.

[Charger primary datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Regulator primary datasheet](https://www.ti.com/lit/ds/symlink/tps63031.pdf). Datasheet review does not replace board waveform or thermal measurements.

## Supplier and physical work still open

- Final capacitor effective capacitance, fuse thermal derating, LED and exact-part qualification.
- Supplier-signed complete pack envelope, charge limits and independent thermal interruption.
- Actual housings/domes/springs/stabilizers, resin tolerances and harness/mechanical samples.
- Physical USB enumeration/eye, concurrent charge/input, BLE, per-key calibration, thermal/runtime and enclosed interference tests.
- Upstream C5 default DRC review items remain; protected-channel verification is not C5 manufacturing or ESD certification.

[Build entry](../../BUILD.md) · [complete explosion and part index](../engineering/exploded.md) · [first-article acceptance](../testing/README.md) · [machine evidence/hashes](raytac-review.json)
