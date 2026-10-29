English | [Chinese](module-options.zh-CN.md)

# Controller module alternatives

## Select a design

Both alternatives are stored in this branch. Each keyboard uses one nRF52840 module. E73 is the default in the main directories; Raytac has a separate directory and shares the source-sized case, plate, battery and upstream references. Footprints and pin assignments differ: choose matching PCB, module and firmware.

| Alternative | PCB and complete materials | Firmware | Process and status |
|---|---|---|---|
| Ebyte E73-2G4M08S1C | [Main preparation list](../../README.md), [native PCB](../../hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb) | [Normal](../../firmware/releases/normal/yeti60-e73.hex), [calibrator](../../firmware/releases/calibrator/yeti60-e73.hex) | Ordinary four-layer; 0 DRC errors / 0 opens; CAD/build audit passes |
| Raytac MDBT50Q-1MV2 | [Raytac preparation list](../../variants/raytac/README.md), [native PCB](../../variants/raytac/hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb) | [Normal](../../variants/raytac/firmware/releases/normal/yeti60-raytac.hex), [calibrator](../../variants/raytac/firmware/releases/calibrator/yeti60-raytac.hex) | Ordinary four-layer; 0 DRC errors / 0 opens; CAD/build audit passes |

Fabricate one selected mainboard per keyboard, with a populated or self-built C5 JSH as chosen. Do not count both mainboards in one keyboard. Each alternative allocates the same 10 stocked mainboard passives and requires 66 more components; these are mutually exclusive plans, not two inventory deductions. Neither module is present in the supplied inventory snapshot.

Run `python3 scripts/run_all_variants.py` to audit both alternatives sequentially, adding `--refresh-renders` to rebuild images. The combined record is written to `docs/audit/variants.json`. The [combined verification record](../audit/variants.json) confirms both designs and their matching manufacturing packages. Physical acceptance and RF/SI remain unverified.

## E73 source and pin checkpoint

The [module profile](../../hardware/module-options/e73.json) records all 43 vendor lands, their dimensions, location and proposed logical net. The [imported reference footprint](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) preserves the vendor library origin and geometry. The nominal body is 18 x 13 x 3 mm; use the stated dimension tolerance in future assembly checks. Manufacturer sources are the [Ebyte product page](https://www.ebyte.com/product/444.html), [manual](https://www.ebyte.com/downpdf/444.html) and [native footprint download](https://www.ebyte.com/pdf-down/2158.html). Source and converted-file SHA-256 hashes are recorded in the profile.

The design retains 21 GPIO functions, USB, SWD, reset, battery sensing and charger control. Of the 43 lands, 28 are outer castellations and 15 are underneath the module. The proposed design connects 27 outer and **five bottom lands: 12, 24, 28, 32 and 34**. E73 therefore still requires a controlled underside soldering process and hidden-joint inspection; outer castellations do not make this an iron-only assembly.

VDD/VCC pin 19 and VDDH/VDH pin 23 use regulated 3.3 V, VBUS pin 27 on USB 5 V, with DCCH/DCH pin 25 unconnected. Current firmware selects REG1 LDO and disables REG0 DC/DC, avoiding any assumption about undocumented internal inductors; power scenarios are recalculated for LDO operation. P0.00/P0.01 are used as GPIO, requiring the internal LF RC clock; P0.09/P0.10 require NFC-to-GPIO configuration. Scan ADC changes to AIN4 and battery ADC to AIN3, so an existing Raytac calibration or binary cannot be reused.

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

## Fabrication packages and conditional power

| Alternative | Fabrication package | Firmware power mode | Conditional 1600 mAh planning runtime |
|---|---|---|---|
| E73 | [E73 DFM review ZIP](../../hardware/fabrication/yeti60-e73-p2-dfm-review.zip) | REG1 LDO | 90.77 hours |
| Raytac | [Raytac DFM review ZIP](../../variants/raytac/hardware/fabrication/yeti60-raytac-p2-dfm-review.zip) | REG1 DC/DC | 106.64 hours |

Runtime figures are sensitivity-model points documented by each option, not measurements or guarantees. Both archives identify their module and contain four copper layers, zero blind drills and 76 placements; C5 is handled separately as listed in the complete materials table. E73/Raytac retain 114/108 DRC warnings respectively, with zero errors and opens; see their native audit reports.

[Acceptance and interference results](../testing/README.md): antenna layout holds remain open for both alternatives; both independent 28-step soldering/assembly guides link to the first-article procedure.
