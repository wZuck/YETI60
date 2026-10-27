English | [简体中文](pcb-review-2026-10-27.zh-CN.md)

# Single-nRF52840 CAD closure checkpoint

Historical review dated 2026-10-27, compared with commit `12d9d5819602ab5d5a3da412bc2454cc18c48f26`. This closes CAD errors; the later [YETI60 functional and assembly review](yeti60-comprehensive-review.md) adds findings that DRC cannot establish.

The earlier 2 SWDIO clearance violations and 17 opens were resolved. Strict native DRC reported **0 errors, 0 opens and no schematic parity errors**. All 268 physical pin pairs passed, with 0 regressions and 98 improved non-ground pairs versus the historical baseline. The 176-symbol netlist has one nRF52840. The 74 sensing-related footprints, outline, holes, thickness and four-layer structure matched the retained EC60 geometry. ERC had 0 errors and 184 warnings. No report category reached the truncation limit.

Strict checking enables previously ignored checks in a scratch project without weakening or overwriting the real rules. Source hashes are in [audit-current.json](../../hardware/ec60-nrf52840/audit-current.json); raw results are in [DRC-strict.json](../../hardware/ec60-nrf52840/DRC-strict.json).

## Repairs at that checkpoint

Power, charging, temperature/current-setting, ADC, mux/discharge, five row drivers, USB D− and MCU VBUS were connected. L1 was rotated 180 degrees to face the appropriate U6 switch nodes. R40 moved beside ISET and C40 moved to preserve assembly clearance. U1.39/U1.51 use filled/capped vias-in-pad to avoid an insufficient 0.4 mm escape channel at the 0.127/0.15 mm rules. U5 thermal ground, local libraries, component attributes, silk clearance, hole clearance and project-save behavior were also corrected. Dangling copper cleanup was followed by full pin-pair and regression checks; full dangling segments can contain intermediate junctions and must not be deleted without connectivity validation.

## Warnings and limits

The strict report retained 102 missing-courtyard warnings for non-assembled electrodes, holes, contacts and outline geometry, and 5 off-center via-endpoint warnings whose copper connection and clearance passed. Assembled components did not lack courtyards. ERC warnings were 183 endpoint-grid issues and one intentional shared-discharge net alias.

[Special fabrication instructions](../../hardware/ec60-nrf52840/fabrication-notes.md) apply to the two module vias-in-pad. These tests do not certify capacitor DC bias, regulator stability, charging temperature, actual Type-C CC/plug/wire assembly, switch/case fit, firmware or RF performance. No mass-production approval was given. Original checkpoint evidence remains under `checkpoints/`.
