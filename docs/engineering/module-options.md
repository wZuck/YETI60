English | [Chinese](module-options.zh-CN.md)

# Controller module alternatives

## Select a design

Each keyboard uses one nRF52840 module. The two module footprints and pin assignments differ; a module cannot be swapped on the same PCB.

| Alternative | Branch | Current checkpoint | Stock allocation |
|---|---|---|---|
| Raytac MDBT50Q-1MV2 | [master](https://github.com/wZuck/YETI60/tree/master) | Existing routed PCB, normal/calibrator ARM firmware and 28-step assembly guide; physical qualification remains open | 10 mainboard passives planned from stock, 66 parts to buy |
| Ebyte E73-2G4M08S1C | [codex/e73-variant](https://github.com/wZuck/YETI60/tree/codex/e73-variant) | Vendor footprint imported and proposed pin assignments checked; E73 PCB routing, firmware and assembly validation remain unfinished | Shared-passive allocation is inherited provisionally; an E73 module is not in the supplied stock snapshot |

**Do not order or flash the copied Raytac PCB, Gerber archive or firmware as an E73 design.** Existing full-audit reports and illustrations in this development branch describe the Raytac baseline until regenerated from completed E73 hardware. The dedicated [E73 proposal report](../audit/e73-pin-proposal.json) explicitly records `PCB_routed: false` and `E73_firmware_built: false`.

## E73 source and pin checkpoint

The [module profile](../../hardware/module-options/e73.json) records all 43 vendor lands, their dimensions, location and proposed logical net. The [imported reference footprint](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) preserves the vendor library origin and geometry. The nominal body is 18 x 13 x 3 mm; use the stated dimension tolerance in future assembly checks. Manufacturer sources are the [Ebyte product page](https://www.ebyte.com/product/444.html), [manual](https://www.ebyte.com/downpdf/444.html) and [native footprint download](https://www.ebyte.com/pdf-down/2158.html). Source and converted-file SHA-256 hashes are recorded in the profile.

The proposal retains 21 GPIO functions, USB, SWD, reset, battery sensing and charger control. Of the 43 lands, 28 are outer castellations and 15 are underneath the module. The proposed design connects 27 outer and **five bottom lands: 12, 24, 28, 32 and 34**. E73 therefore still requires a controlled underside soldering process and hidden-joint inspection; outer castellations do not make this an iron-only assembly.

VDD/VCC pin 19 and VDDH/VDH pin 23 are proposed on regulated 3.3 V, VBUS pin 27 on USB 5 V, with DCCH/DCH pin 25 unconnected. The REG1 DC/DC component provision still needs confirmation before freezing firmware and power estimates. P0.00/P0.01 are used as GPIO, requiring the internal LF RC clock; P0.09/P0.10 require NFC-to-GPIO configuration. Scan ADC changes to AIN4 and battery ADC to AIN3, so an existing Raytac calibration or binary cannot be reused.

Run `scripts/check_e73_proposal.py` using KiCad Python to check the 43-pad reference, unique assignments and dedicated USB/SWD/power pins. This check does not run DRC, simulate the completed PCB or build E73 firmware. Once routing is complete, regenerate and pass the complete repository audit, both firmware targets, pin/ADC contracts, mechanical clearances, variant-specific manufacturing files and illustrated instructions. RF/SI and physical qualification remain separate pending work.
