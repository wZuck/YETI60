English | [Chinese](battery-vendor-checklist.zh-CN.md)

# Battery parameters to send to your supplier

Use the specified **SHR-03V-S without protrusions, 4.0 mm wide**. The catalogued **SHR-03V-S-B with protrusions is 6.0 mm wide** and is not covered by the present housing envelope; do not substitute it without a separate fit check. [JST housing table](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

The user will verify the battery with the supplier. No finished pack is approved merely by matching its model code. Request **one sample pack** and a written response to every line below. The default remains one 1600 mAh pack per keyboard.

| Parameter | Requirement to confirm |
|---|---|
| Chemistry / cells | One lithium-ion polymer cell, **1S**, nominal **3.7 V**, nominal **4.2 V CC/CV charging**. Not 2S, LiFePO4 or a 4.35 V HV pack |
| Capacity | **Minimum 1600 mAh**, with the actual test current, temperature, charge voltage and discharge cutoff. Report minimum separately from typical; clarify any inconsistent C-rate/current entries |
| Complete size | **Length <=85 mm, width <=43 mm, thickness <=4.8 mm**, including PCM, thermal protection, sensors, folded tabs, wrapping, insulation, strain relief and specified growth. Provide maximum dimensions and a section drawing. External bench samples may be thicker, but this does not establish final case fit |
| Charger compatibility | Accept the BQ24074 output range **4.16–4.23 V** and state the maximum permitted charge voltage. Describe delivered capacity at the 4.16 V corner rather than assuming it remains 1600 mAh |
| Continuous charging | **At least 500 mA allowed** inside the accepted temperature window. The keyboard programming has a calculated maximum **445.63 mA**; 500 mA is the requested pack rating, not guaranteed cell current |
| End of charge | Accept termination-current range **16.87–29.26 mA**, typical **22.94 mA**, under the stated CC/CV protocol; provide charging/termination curves |
| Discharge capability | Prefer a confirmed continuous rating **>=0.5 A** in the intended operating window; this is procurement margin, not measured keyboard consumption. Supply actual continuous/pulse ratings and allowed temperatures |
| Normal discharge cutoff | Cell operating cutoff **3.0 V**. Explain operating cutoff, emergency PCM cutoff, all tolerances/delays and recovery; a bare statement of 2.4 V emergency protection is insufficient. Current target firmware has no autonomous low-voltage shutdown |
| Independent temperature interruption | Hardware must inhibit charging without the keyboard MCU or external charger-feedback circuit. Including error and thermal lag, allowed charging must stay **inside 15–43°C**, target nominal **18–40°C**. State cold/hot trip, recovery, hysteresis, sensor open/short behavior and tolerances |
| Third-wire temperature feedback | Cell-coupled NTC electrically compatible with **SEMITEC 103AT-2: 10 kOhm at25°C, B25/85=3435 K**, R25/B tolerances **<=1%**, or provide a full equivalent R/T table for review. This feedback must not be electrically loaded by the independent protector |
| Sensor packaging | Show the sensor on the section drawing. A 2.4 mm bead stacked on a 4.3 mm cell does not fit a 4.8 mm pack; use a qualified thin sensor or end-bay coupling arrangement |
| Other protection | State exact PCM IC/MOSFET models and overvoltage, undervoltage, charge/discharge overcurrent, short-circuit and temperature thresholds, delays, recovery and leakage. “Protected” or “three-wire” alone is not an answer |
| Connector / polarity | **JST SHR-03V-S, 1.0 mm pitch, three pins**; pin1 PACK+ red, pin2 PACK− black, pin3 NTC yellow referenced to PACK−. Supply a numbered mating-face/latch drawing. Do not rely on generic battery polarity or colors |
| Leads | AWG28 stranded copper, insulation OD<=0.8 mm; free lengths between the controlled pack-exit and plug-exit planes: pin1 **114.92 mm**, pin2 **111.61 mm**, pin3 **108.63 mm**, tolerance +/-0.5 mm, preformed as drawn. These are not crimp cut lengths. Confirm strain relief and >=4 mm static bend radius |
| Documents | Corrected cell datasheet, exact finished-pack model, dimensioned complete drawing, protector schematic/specification, capacity and full-charge curves, protection test record, and applicable sample/batch inspection records |

Ask the supplier to return its **actual model, values, tolerances and drawings**, identifying every mismatch. Do not approve an alternative voltage, polarity, PCM or temperature window based only on a seller's “compatible” description. The [full pack specification](../engineering/battery-pack-specification.md) controls the geometry and lead-exit datums.

Battery verification is user-owned; PCB/USB repair can continue in parallel. First unpowered/power/USB tests do not need a battery connected, while complete open-bench acceptance **does require** battery discharge and charging tests. [Open-bench guide](../../OPEN-BENCH.md) · [build handbook](../../BUILD.md).
