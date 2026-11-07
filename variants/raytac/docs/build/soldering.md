English | [Chinese](soldering.zh-CN.md)

# Solder from a bare board

For the current candidate use the [power locations/ordinary thermal vias](../../hardware/usb-short-route/POWER-LAYOUT.md), [75-part table and packages](../../hardware/usb-short-route/mainboard-purchase.csv), [revised F1 land](../../hardware/usb-short-route/F1-SELECTION.md) and [current board/assembly maps](../../hardware/usb-short-route/ASSEMBLY.md). The 28-step images retain reference positions; their old R30/R31, power capacitors and USB wiring do not override this candidate. Use the [current bottom stencil with JP1 excluded](../../hardware/usb-short-route/fabrication/yeti60-raytac-candidate-bottom-stencil.zip).

Return to the [handbook](../../BUILD.md). Use the [28 illustrated steps](../assembly/build-guide.md) for actual reference positions/orientation. Keep the battery disconnected throughout soldering and do not solder a powered board.

Start on the **rear component face**. The front is the sensing face: no mechanical switches, per-key diodes or hotswap sockets are soldered there. Sort parts, print B.Paste, place parts, then perform controlled reflow. Placement order does not mean reheating the complete board after every group. Hidden-pad U5/U6 and module connections require a suitable process and inspection; use an assembler if those are unavailable.

| Order / illustrated steps | Operation and inspection stop |
|---|---|
| 01–02 | Identify Raytac board/module, thickness, outline, 29 holes and clean electrodes; no E73 parts/firmware |
| 03 | Support flat, print B.Paste with JP1 omitted; inspect bridges, missing deposits, exposed-pad aperture plan and open-via wicking |
| 04 | Place 41 resistors. R30/R31 are removed; R40=2.21k, R55=69.8k, R56=1.69k, 1%. Check every reference; JP1 empty |
| 05 | Place 17 ceramics; C10=220 pF C0G. Separate 0402/0603/0805; seven power positions use the current 0805 specifications. Verify effective capacitance and allowed stock |
| 06 | Place U5 BQ24074, U6 TPS63031, U7/U8 TPS22919, L1=1.5 uH and F1; align actual pin 1 to native lands. **No mainboard D1** |
| 07 | Place U2/U4 74HC4051 and U3 OPA350; check orientation; no HCT/dual-amplifier substitution |
| 08 | Place U1 MDBT50Q-1MV2; check antenna direction, actual pin 1 and LED polarity |
| 09 | Place connectors/switches and D2, or reserve them for later soldering if their thermal limits require it; decide this before reflow |
| 10 | Reflow under a profile compatible with paste, module and most sensitive part. Record actual board temperature, cool fully; no assumed universal 260 C profile |
| 11 | Unpowered electrical checks, magnified inspection and appropriate hidden-joint inspection; repair bridges/tombstones/wrong parts, clean compatible residues without scraping/tinning electrodes |
| 12–13 optional | C5: small R1/R2, U1, F1, D1 before connectors, with F.Paste and illustrated procedure. All seven parts including C5 D1/U1 mandatory |
| 14–16 | Verify harness pin continuity and unpowered rail shorts; first power from current-limited supply, inspect 3.3 V/current/temperature, then SWD. Avoid back-power from probe |
| 17–24 | Qualify local mechanism samples and fit housings/domes/springs, standoffs, insulation, C5 and harnesses; no pinching, bottoming or forced closure |
| 25 | Flash Raytac calibrator; release and 60 individually labelled held-key captures; all valid and save successful |
| 26–28 | Concurrent USB typing/charging, BLE, suspend/resume; normal firmware preserving settings; repeat after closure. Complete electrical/mechanical acceptance records |

Before power check VBUS/GND, SYS/GND, 3V3/GND and connector pins. Brief meter beeps may reflect charging capacitors; no invented fixed resistance establishes acceptance. Investigate persistent shorts. Start USB 5 V under a conservative adjustable current limit without a real battery; stop on current limiting, unstable rails or abnormal heat instead of repeatedly raising the limit. Charger defaults before firmware differ from active-firmware USB policy.

Flash the [calibrator HEX](../../hardware/usb-short-route/firmware/releases/calibrator/yeti60-raytac.hex), follow [firmware release/press/status/save instructions](../../firmware/target/README.md), then flash [normal HEX](../../hardware/usb-short-route/firmware/releases/normal/yeti60-raytac.hex) preserving the last 64 KiB. Do not mass erase and expect calibration to survive. J3 is a custom six-pad pattern; use the native diagram/illustrated guide, not an assumed standard header pinout.

References: [TI QFN/SON attachment](https://www.ti.com/lit/an/slua271c/slua271c.pdf), [Raytac documentation](https://www.raytac.com/product/ins.php?index_id=24). No universal measured reflow profile exists for arbitrary substitutions or equipment.

Before printing, inspect U5/U6 islands and the matched stencil using the [package/mask revision](../../hardware/usb-short-route/PACKAGE-MODELS.md). Retain the islands; previous open-hole stencil instructions are superseded.
