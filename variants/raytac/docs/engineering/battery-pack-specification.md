English | [Chinese](battery-pack-specification.zh-CN.md)

# YETI60-BAT-1600-1S supplier drawing and acceptance specification

This is a review/RFQ specification for one custom protected single-cell pack per keyboard. No supplier has accepted it and no order is authorized. The [assembly specification](../../../../mechanical/assembly-spec.json), [interconnect specification](../../../../mechanical/interconnect-spec.json), [power calculation](power-budget.md) and [battery study](battery-study.md) are its controlled inputs.

## Cell and complete package

Reference cell: Honcell HCP404074, sheet dated 2024-04-01, 3.7 V nominal, minimum 1600 mAh/typical 1620 mAh under its stated test protocol. It is a cell reference, not an accepted finished pack. Its 0.2C=270 mA and 1C=1350 mA current rows conflict with the capacity rating. Require a corrected manufacturer sheet or signed clarification before procurement; do not reinterpret these numbers as confirmed 320/1600 mA limits. [Manufacturer sheet](https://www.honcell.com/Public/Uploads/uploadfile/files/20240401/DATASHEETHCP4040743.7V1600mAhCELL2024.pdf)

The **entire finished pack must remain within 85 x 43 x 4.8 mm**, including PCM, thermal protection, thermistor, weld/tab folds, wrap, insulation, adhesives, strain relief and the specified life/growth condition. The source cell's delivered/cycled thickness allowances must be included, not added later. Confirm full length including tabs and fold geometry; the bare-cell nominal outline is not the finished-pack envelope. Provide an orthographic dimensioned drawing with tolerances and sections through the thickest protection/tab/sensor areas, usable removal surfaces, mass and wire-exit datums.

The nominal pack bounds in the case are `[228.5,-149,-9.4]` to `[313.5,-106,-4.6]` mm. Do not scale the enclosure or clamp the pouch. Nominal floor-to-pack space is 0.20 mm in total; retention tape/insulation/assembly allowance must share it. The current pocket already belongs to the canonical bottom shell.

## Electrical and temperature requirements

| Item | Required response/acceptance |
|---|---|
| Charge protocol | 1S lithium-ion, nominal 4.2 V CC/CV; supplier must approve the BQ24074 **4.16/4.20/4.23 V min/typ/max** regulation range, with the corrected cell's absolute voltage and protection limits |
| Continuous charge capability | At least **500 mA** in the accepted actual temperature window; this is a requested rating, not a verified supplier rating. Programmed charger maximum is 445.63 mA; the separate engineering ceiling is 450 mA |
| Termination | R56=1.69k/1%, calculated USB500 termination 16.87/22.94/29.26 mA; supplier must accept the actual protocol and prove termination within the configured timer under the test conditions |
| Capacity | State cell/finished-pack capacity protocol and acceptance temperature, rate, cutoff and charger voltage. The 1600 mAh source label does not prove 1600 mAh delivered at the charger's 4.16 V corner; characterize this corner explicitly |
| Independent temperature protection | Factory pack must interrupt charging without the MCU or third-wire NTC circuitry. Including all sensor/IC errors and thermal lag, the actual allowed charging window must lie within **15–43 C**, with an **18–40 C** nominal target |
| Separate NTC feedback | Third-wire **10k 103AT-2 electrically compatible** thermistor, thermally coupled to the cell; provide R/T table, R25/B tolerances and attachment drawing. A thin compatible sensor may be needed to fit; do not add a protruding bead outside the envelope |
| Protection | Supply PCM/protection schematic, exact IC/MOSFET/sensor models, voltage/current/temperature thresholds, worst-case errors, delays, recovery conditions and leakage over voltage/temperature |
| Evidence | Signed corrected limits, pack drawing, capacity/charging curves, temperature interruption/recovery records and production inspection criteria |

The independent protector and BQ24074 feedback need **separate sensing arrangements**. Do not connect a protector divider to the BQ thermistor node without a validated electrical design: its biasing can change the measured temperature. Voltage/current-only PCM and two-wire packs do not meet the temperature requirement. The charger IC's die thermal regulation is not cell thermal protection. [TI BQ24074 SLUS810N, electrical characteristics and sections 9.3.5/9.3.7](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Leads and assembly interface

Use one PHR-3 housing with three SPH-004T-P0.5S contacts, AWG28 stranded copper, insulation OD <=0.8 mm. Pin 1 is red PACK+, pin 2 black PACK-, pin 3 yellow NTC to PACK-. Supply a drawing showing **pin numbers and the latch/viewing direction**; wire colors alone are insufficient. The pack leads/housing/contacts are included in the pack quantity, not additional loose purchases. [JST PH drawing](https://www.jst.com/wp-content/uploads/2025/06/ePH.pdf)

Pack local origin is its minimum X/Y/Z corner. Required strain-relief lead-exit datum is **[0,14,4.4] mm**, outward along -X, with pin endpoints offset by +2/0/-2 mm in Y. This is an engineering interface request requiring supplier confirmation. The conductor/insulation exit must remain within the 4.8 mm complete envelope. Use the per-wire free lengths and case-frame paths in [the interconnect report](../audit/yeti60-interconnects.json); they are insulation lengths between exit planes, not crimp cut lengths. Nominal free-length tolerance is +/-0.5 mm; the harness must additionally be preformed and retained within the controlled route. Length alone does not guarantee fit. Supplier must approve the chosen >=4 mm static bend radius and a >=5 mm pack lead transition zone without bending cell tabs or stressing welds.

## Qualification sequence

Inspect the signed drawing, polarity, NTC resistance and complete envelope before connection. Exercise the charger with a battery simulator first. On qualified packs, record full CC/CV/termination and timer behavior with board-on configured USB500 and separately with board-off USB100, across accepted source voltage, system load and temperature conditions. Verify independent hot/cold interruption/recovery and closed-case charger/cell temperatures. Record switch-off leakage, capacity and normal-firmware battery-side current with USB/debugger disconnected. First-article testing and acceptance remain open; calculation is not a substitute.
