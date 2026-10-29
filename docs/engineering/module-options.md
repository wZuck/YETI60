English | [Chinese](module-options.zh-CN.md)

# Controller module alternatives

## Select a design

Each keyboard uses one nRF52840 module. The two module footprints and pin assignments differ; a module cannot be swapped on the same PCB.

| Alternative | Branch | Current checkpoint | Stock allocation |
|---|---|---|---|
| Raytac MDBT50Q-1MV2 | [master](https://github.com/wZuck/YETI60/tree/master) | Existing routed PCB, normal/calibrator ARM firmware and 28-step assembly guide; physical qualification remains open | 10 mainboard passives planned from stock, 66 parts to buy |
| Ebyte E73-2G4M08S1C | [codex/e73-variant](https://github.com/wZuck/YETI60/tree/codex/e73-variant) | Native schematic, footprint, pin contract and both ARM targets implemented; PCB routing and full integration are being completed | Shared-passive allocation is inherited provisionally; an E73 module is not in the supplied stock snapshot |

**This implementation branch is not ready for fabrication.** E73 normal/calibrator firmware builds and HEX/USB500 checks pass, using internal LF RC and REG1 LDO. PCB strict-DRC closure, manufacturing files, assembly illustrations and full reports are being refreshed. Existing Raytac images and old reports are not E73 validation. See the [vendor reference check](../audit/yeti60-e73-reference.json), [current module contract](../audit/yeti60-e73-variant.json) and [firmware build record](../audit/yeti60-target-build.json).

## E73 source and pin checkpoint

The [module profile](../../hardware/module-options/e73.json) records all 43 vendor lands, their dimensions, location and proposed logical net. The [imported reference footprint](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) preserves the vendor library origin and geometry. The nominal body is 18 x 13 x 3 mm; use the stated dimension tolerance in future assembly checks. Manufacturer sources are the [Ebyte product page](https://www.ebyte.com/product/444.html), [manual](https://www.ebyte.com/downpdf/444.html) and [native footprint download](https://www.ebyte.com/pdf-down/2158.html). Source and converted-file SHA-256 hashes are recorded in the profile.

The proposal retains 21 GPIO functions, USB, SWD, reset, battery sensing and charger control. Of the 43 lands, 28 are outer castellations and 15 are underneath the module. The proposed design connects 27 outer and **five bottom lands: 12, 24, 28, 32 and 34**. E73 therefore still requires a controlled underside soldering process and hidden-joint inspection; outer castellations do not make this an iron-only assembly.

VDD/VCC pin 19 and VDDH/VDH pin 23 are proposed on regulated 3.3 V, VBUS pin 27 on USB 5 V, with DCCH/DCH pin 25 unconnected. Current firmware selects REG1 LDO and disables REG0 DC/DC, avoiding any assumption about undocumented internal inductors; power scenarios are recalculated for LDO operation. P0.00/P0.01 are used as GPIO, requiring the internal LF RC clock; P0.09/P0.10 require NFC-to-GPIO configuration. Scan ADC changes to AIN4 and battery ADC to AIN3, so an existing Raytac calibration or binary cannot be reused.

Run `scripts/check_e73_reference.py` and `scripts/check_e73_variant.py` using KiCad Python to check the 43-pad reference, unique assignments and dedicated USB/SWD/power pins. This check does not run DRC, simulate the completed PCB or build E73 firmware. Once routing is complete, regenerate and pass the complete repository audit, both firmware targets, pin/ADC contracts, mechanical clearances, variant-specific manufacturing files and illustrated instructions. RF/SI and physical qualification remain separate pending work.

## Pin assignments

| Logical net | Module land | SoC pin | Land location |
|---|---:|---|---|
| ROW_DRV1 | 1 | P1.11 | outer |
| CHG_N | 2 | P1.10 | outer |
| CHG_EN1 | 3 | P0.03 | outer |
| ADC | 4 | P0.28 | outer |
| GND | 5 | GND | outer |
| CHG_CE_N | 6 | P1.13 | outer |
| CHG_EN2 | 7 | P0.02 | outer |
| BAT_MEAS_EN | 8 | P0.29 | outer |
| AFE_EN | 9 | P0.31 | outer |
| STATUS_LED | 10 | P0.30 | outer |
| ROW_DRV4 | 11 | P0.00 | outer |
| APLEX_OUT_PIN_0 | 12 | P0.26 | bottom |
| APLEX_EN_PIN_0 | 13 | P0.01 | outer |
| BAT_ADC | 15 | P0.05 | outer |
| ROW_DRV3 | 17 | P1.09 | outer |
| +3.3V | 19 | VDD | outer |
| GND | 21 | GND | outer |
| +3.3V | 23 | VDDH | outer |
| GND | 24 | GND | bottom |
| RESET_N | 26 | P0.18 | outer |
| USB_5V | 27 | VBUS | outer |
| AMUX_SEL_2 | 28 | P0.15 | bottom |
| USB_DM | 29 | D- | outer |
| USB_DP | 31 | D+ | outer |
| AMUX_SEL_0 | 32 | P0.20 | bottom |
| ROW_DRV0 | 33 | P0.13 | outer |
| AMUX_SEL_1 | 34 | P0.22 | bottom |
| ROW_DRV2 | 35 | P0.24 | outer |
| SWDIO | 37 | SWDIO | outer |
| SWDCLK | 39 | SWDCLK | outer |
| APLEX_EN_PIN_1 | 41 | P0.09 | outer |
| PGOOD_N | 43 | P0.10 | outer |
