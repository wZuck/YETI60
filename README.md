English | [Chinese](README.zh-CN.md)

# YETI60

A single-nRF52840 electrocapacitive keyboard PCB for the FELK60 case, derived from Cipulot EC60. The sensing geometry, board outline and mounting locations are retained; a rear USB daughterboard connects to J1.

> **P2 design checkpoint:** C5 JSH is retained. The default is now a custom 1600 mAh single-cell pack with a canonical recessed bottom, revised charger settings and USB500 firmware. Engineering sheets, PCB animation and assembly renders record their source hashes. See [checkpoint details](docs/design-checkpoint.md).

## Current review

**CAD connectivity passes; production and complete hardware operation are not approved.** The [comprehensive review](docs/audit/yeti60-comprehensive-review.md) documents the implemented P2 design and remaining supplier, tolerance, harness and physical acceptance.

| Scope | Evidence and result |
|---|---|
| PCB | Strict DRC 0 errors / 0 opens; 270 physical pin pairs pass. Inherited USB resistors corrected to 0 Ω; shortened local power routes use nine filled back-side microvias; HDI fabrication required |
| Firmware | New schematic-bound control core passes host ASan/UBSan simulation; normal/calibrator target binaries now build; on-device USB/BLE and EC calibration remain pending |
| Mechanical | Source PCB/plate/case nominal geometry has no overlap at the explicitly provisional Z stack; final dome/fastener/resin tolerances are unqualified |
| Battery | Default custom 1600 mAh, complete 85×43×4.8 mm; supplier drawing/current clarification and independent thermal protection approval pending |
| Visualization | Current source hashes tie PCB images/animation, separate engineering sheets and studio assembly renders to P2 |

- [Engineering assembly sheets and sequence](docs/engineering/assembly.md)
- [Battery recess feasibility](docs/engineering/battery-study.md)
- [Power, runtime and charging calculation](docs/engineering/power-budget.md)
- [Materials and procurement table](docs/engineering/materials.md)
- [PCB marking cleanup](docs/engineering/board-markings.md)
- [Complete review](docs/audit/yeti60-comprehensive-review.md)
- [Hardware and fabrication notes](hardware/ec60-nrf52840/README.md)
- [Firmware core, simulation and trace](firmware/yeti60/README.md)
- [Assembly renders](renders/yeti60-assembly/README.md)
- [PCB renders and 360° animation](renders/ec60-nrf52840/README.md)
- [Current audit index](docs/audit/README.md)

The case material is provisionally resin. SI/RF analysis remains deferred. Project-owned prose defaults to English with a parallel `.zh-CN.md`; machine-readable field names stay stable.

Based on [Cipulot/EC60](https://github.com/Cipulot/EC60) and [fredlb/felk60](https://github.com/fredlb/felk60). Upstream authors, licenses and original project names are retained. Existing `EC60-nRF52840.*` filenames and `YAECKB` library identifiers remain for technical compatibility; the public project name is **YETI60**.
