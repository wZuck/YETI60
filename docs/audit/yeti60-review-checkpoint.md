# YETI60 comprehensive review — checkpoint

English | [Chinese](yeti60-review-checkpoint.zh-CN.md)

This checkpoint saves work in progress at the user's request. It is not a completed assembly or production review.

## Completed

- Confirmed that the existing STM32 host tests alone do not validate the current nRF52840 design.
- Added a portable nRF pin-bound control core and passing ASan/UBSan host simulation. All 75 scan positions and power/HID control scenarios are covered; real peripherals and transport stacks are mocked.
- Changed R30/R31 from 27 Ω to 0 Ω links following [Nordic's USB PHY guidance](https://devzone.nordicsemi.com/f/nordic-q-a/94955/resistors-for-d-and-d-). Schematic, PCB, frozen footprints, generator and netlist are synchronized.
- Added functional ADC/GPIO checks and conservative copper-path measurements. U6's second output capacitor and feedback connection still route around approximately 29–30 mm; charger input/battery capacitor paths also remain under review. DRC continuity does not certify a good power layout.
- Widened the inductor-side straight tracks to 0.35 mm; constrained diagonal/IC necks stay at 0.2 mm to preserve existing via clearance.
- Began public naming migration to **YETI60** and default-English documentation with parallel Chinese versions. Upstream attribution and technical compatibility identifiers are retained.

## Continuing after this checkpoint

- Improve blocked local power paths and recheck native DRC and all physical pin connections.
- Register the real FELK60 gasket/plate stack and evaluate PCB/component/case clearances over an explicit Z range.
- Find a provisional battery-space envelope. No battery is selected; pack protection, NTC, insulation, swelling allowance and cable routing remain requirements.
- Produce assembled and exploded renders based on the checked transforms, with any illustrative components clearly identified.
- Finish English/Chinese synchronization of project-owned documents and refresh renders for the current source. Previous PCB-only renders correspond to the earlier commit.

Current machine-readable evidence: [CAD](../../hardware/ec60-nrf52840/audit-current.json), [functional electrical review](yeti60-electrical.json), [firmware simulation](yeti60-firmware-simulation.json). The firmware report does not establish target compilation, USB enumeration, BLE pairing or RF performance. SI/RF simulation remains deferred as previously requested.
