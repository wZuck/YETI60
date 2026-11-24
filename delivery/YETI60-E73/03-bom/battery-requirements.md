English | [Chinese](battery-requirements.zh-CN.md)

# YETI60-BAT-1600-1S supplier drawing and acceptance specification

This is a review/RFQ specification for one custom protected single-cell pack per keyboard. No supplier has accepted it and no order is authorized. The [assembly specification](../02-mechanical/assembly-spec.json), [interconnect specification](../02-mechanical/interconnect-spec.json), [power calculation](https://github.com/wZuck/YETI60/blob/master/docs/engineering/power-budget.md) and [battery study](https://github.com/wZuck/YETI60/blob/master/docs/engineering/battery-study.md) are its controlled inputs.

## Cell and complete package

Reference cell **Honcell HCP404074** is rated 3.7 V, with 1600 mAh minimum and 1620 mAh typical under the stated test protocol. The later manufacturer file lists 320 mA standard charge at 0–45 °C and 1600 mA maximum at 15–45 °C for the bare cell. It lists **4.20 V** as the charge endpoint. The finished-pack supplier still needs to approve the full BQ24074 regulation range, including **4.23 V**. [Honcell bare-cell sheet, pp. 1–2](https://www.honcell.com/Public/Uploads/uploadfile/files/20250219/DATASHEETHCP4040743.7V1600mAhCELL2024.pdf) · [TI BQ24074 §8.5](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

The **entire finished pack must remain within 85 x 43 x 4.8 mm**, including PCM, thermal protection, thermistor, weld/tab folds, wrap, insulation, adhesives, strain relief and the specified life/growth condition. The source cell's delivered/cycled thickness allowances must be included, not added later. Confirm full length including tabs and fold geometry; the bare-cell nominal outline is not the finished-pack envelope. Provide an orthographic dimensioned drawing with tolerances and sections through the thickest protection/tab/sensor areas, usable removal surfaces, mass and wire-exit datums.

The nominal pack bounds in the case are `[228.5,-149,-9.4]` to `[313.5,-106,-4.6]` mm. Do not scale the enclosure or clamp the pouch. Nominal floor-to-pack space is 0.20 mm in total; retention tape/insulation/assembly allowance must share it. The current pocket already belongs to the canonical bottom shell.

The maximum cycled bare-cell body is **74.5 × 40.5 × 4.32 mm**, excluding tabs. Subtraction from the finished envelope leaves **10.5 mm length, 2.5 mm width and 0.48 mm thickness** in total, before pack parts and tolerances. With the longest 7 mm straight tabs, 3.5 mm remains in the length direction. Confirm the stack-ups, tab section and aged pack thickness on the supplier drawing. [Source values and arithmetic](../06-validation/pack-source-review.json)

## Compare the published Honcell pack

Honcell publishes an **HCP404074NZC** pack drawing. Its **77.0 × 40.5 × 4.2 mm** body fits within the design envelope on paper. The drawing gives a PHR-3 connector and a 50 ±3 mm lead dimension. M05 uses the SH3 housing below and individual free leads of 107.229–113.512 mm. The stock pack rates maximum charging at 800 mA over 15–45 °C. Its circuit shows one external NTC feedback lead and a voltage/current PCM. The sheet leaves independent hot/cold charge interruption, the complete cycled envelope and approval for 4.23 V regulation open. Use this drawing as a supplier reference for a **custom finished pack**. [Honcell pack sheet, pp. 4–7](https://www.honcell.com/Public/Uploads/uploadfile/files/20250219/DATASHEETHCP404074NZC3.7V1600mAhPACK2024.pdf)

Resolve the published protection limits in writing. The stock pack's overcharge detector is specified at **4.28 ±0.025 V**, so its lowest published trip is **4.255 V**. The same sheet gives **4.20 V** for normal charging and **4.25 V** as the absolute maximum and the ceiling for the protection threshold. Ask for the signed normal charge range, the initial and including-tolerance detector limits, and the peak cell voltage before interruption under the worst-case fault and delay. Evaluate the corrected limits for the exact pack revision before applying charge. [Honcell pack sheet, pp. 7, 12 and 14](https://www.honcell.com/Public/Uploads/uploadfile/files/20250219/DATASHEETHCP404074NZC3.7V1600mAhPACK2024.pdf)

## Sample quotation

Ask each supplier to quote its minimum engineering-sample quantity and return the signed data below against the offered pack part number and drawing revision. Request the highest documented single-cell capacity that meets the complete aged envelope and all charge limits, with **1600 mAh** as the reference target. Ask for the available capacity under **4.16 V** charging, the lowest regulation point of this board.

| Supplier | What its public page supports |
|---|---|
| Honcell | Source of the reference cell and pack drawings. The general FAQ lists a 3,000-piece production minimum. Ask separately about engineering samples. [Honcell FAQ](https://www.honcell.com/resources/faqs) |
| A&S Power | Offers custom connectors and PCM/BMS. The general FAQ lists 5–10 pieces depending on battery type. Request the minimum and the charge-protection schematic for this specific pack. [A&S Power custom packs](https://www.szaspower.com/custom-lithium-ion-battery-manufacturer/index.html) |
| Outputs Power | Its quote form accepts requests for sample runs below 10 pieces. Request dimensions, protection limits and applicable sample quantity in the quotation. [Outputs Power custom packs](https://outputspower.com/battery-packs/) |

Use the same four acceptance items to compare all replies.

1. Signed cell/pack identifiers and maximum finished **85 × 43 × 4.8 mm** drawing through the protection area, with life growth and the actual strain-relief exit.
2. Approved **4.16–4.23 V** charger regulation, **500 mA** continuous charge rating within the accepted window, termination tolerance and separately documented normal/full-charge and fault-voltage limits.
3. Independent hot/cold charge interruption, plus the separate 10 kΩ thermistor feedback curve, J2 pin-number drawing and actual finished lead lengths.
4. Minimum sample quantity, lead time, sample test/inspection report and transport documents for the exact offered variant.

## Electrical and temperature requirements

| Item | Required response/acceptance |
|---|---|
| Charge protocol | 1S lithium-ion, nominal 4.2 V CC/CV; supplier must approve the BQ24074 **4.16/4.20/4.23 V min/typ/max** regulation range, with the supplied cell's absolute voltage and protection limits |
| Continuous charge capability | At least **500 mA** in the accepted actual temperature window; this is a requested rating, not a verified supplier rating. Programmed charger maximum is 445.63 mA; the separate engineering ceiling is 450 mA |
| Termination | The Honcell reference protocol ends at 0.02C, or 32 mA for a 1600 mAh cell. R56 = 1.69 kΩ ±1% gives calculated E73 USB500 thresholds of **16.87 / 22.94 / 29.26 mA**. Ask the supplier to approve the lower threshold range and demonstrate taper to termination within the configured timer |
| Capacity | State cell/finished-pack capacity protocol and acceptance temperature, rate, cutoff and charger voltage. The 1600 mAh source label does not prove 1600 mAh delivered at the charger's 4.16 V corner; characterize this corner explicitly |
| Independent temperature protection | Factory pack must interrupt charging without the MCU or third-wire NTC circuitry. Including all sensor/IC errors and thermal lag, the actual allowed charging window must lie within **15–43 C**, with an **18–40 C** nominal target |
| Separate NTC feedback | Third-wire **10k 103AT-2 electrically compatible** thermistor, thermally coupled to the cell; provide R/T table, R25/B tolerances and attachment drawing. A thin compatible sensor may be needed to fit; do not add a protruding bead outside the envelope |
| Protection | Supply PCM/protection schematic, exact IC/MOSFET/sensor models, voltage/current/temperature thresholds, worst-case errors, delays, recovery conditions and leakage over voltage/temperature |
| Evidence | Signed pack limits, pack drawing, capacity/charging curves, temperature interruption/recovery records and production inspection criteria |

The independent protector and BQ24074 feedback need **separate sensing arrangements**. Do not connect a protector divider to the BQ thermistor node without a validated electrical design: its biasing can change the measured temperature. Voltage/current-only PCM and two-wire packs do not meet the temperature requirement. The charger IC's die thermal regulation is not cell thermal protection. [TI BQ24074 SLUS810N, electrical characteristics and sections 9.3.5/9.3.7](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Leads and assembly interface

Use one SHR-03V-S housing with three SSH-003T-P0.2-H contacts, AWG28 stranded copper, insulation OD <=0.65 mm. Pin 1 is red PACK+, pin 2 black PACK-, pin 3 yellow NTC to PACK-. Supply a drawing showing **pin numbers and the latch/viewing direction**; wire colors alone are insufficient. The pack leads/housing/contacts are included in the pack quantity, not additional loose purchases. [JST SH drawing](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf)

Pack local origin is its minimum X/Y/Z corner. Required strain-relief lead-exit datum is **[0,14,4.5] mm**, outward along -X, with pin endpoints offset by +2/0/-2 mm in Y. This is an engineering interface request requiring supplier confirmation. The body and strain relief must meet the complete-pack envelope; the external insulated pigtail is separately screened in the case at this exit datum. Show both envelopes on the drawing. Use the per-wire free lengths in [the M05 conductor table](../02-mechanical/service-case-m05/harness/wire-lengths-m05.csv); they are insulation lengths between exit planes, not crimp cut lengths. M05 nominal lengths are 113.512 mm for PACK+, 110.309 mm for PACK− and 107.229 mm for NTC. The ±0.5 mm dimension is a supplier target. Form the harness within the controlled route and check the actual fit. Length alone does not guarantee fit. Supplier must approve the chosen >=4 mm static bend radius and a >=5 mm pack lead transition zone without bending cell tabs or stressing welds.

## Qualification sequence

Inspect the signed drawing, polarity, NTC resistance and complete envelope before connection. Exercise the charger with a battery simulator first. On qualified packs, record full CC/CV/termination and timer behavior with board-on configured USB500 and separately with board-off USB100, across accepted source voltage, system load and temperature conditions. Verify independent hot/cold interruption/recovery and closed-case charger/cell temperatures. Record switch-off leakage, capacity and normal-firmware battery-side current with USB/debugger disconnected. First-article testing and acceptance remain open; calculation is not a substitute.

This root specification applies to E73 CORNER-07 and its SH3 battery interface. The separate Raytac variant retains its own supplier document and wiring datums. Final E73 cable retention and supplier acceptance remain open.
