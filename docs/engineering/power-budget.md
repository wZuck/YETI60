English | [Chinese](power-budget.zh-CN.md)

# Power and runtime calculation

This is a reproducible **sensitivity calculation**, not measured runtime. No physical board exists. Manufacturer values below establish component behavior; MCU average, efficiency and usable capacity remain explicit scenario assumptions. A reliable whole-board average cannot be obtained from a BLE peak-current specification alone.

## Source data and firmware state

| Item | Published data / actual design state | Use and limitation |
|---|---|---|
| OPA350 | 5.2 mA typical, 7.5 mA maximum at 25°C; 8.5 mA maximum over −40…85°C | [TI SBOS099D, p7](https://www.ti.com/lit/ds/symlink/opa350.pdf); continuous AFE load, independent of typing |
| nRF52840 | CPU CoreMark from flash: 6.3 mA LDO typical, 3.3 mA DC/DC typical | [Nordic PS v1.10, §5.2.1.3](https://docs-be.nordicsemi.com/bundle/nRF52840_PS_v1.10/raw/resource/enus/nRF52840_PS_v1.10.pdf?save_local=true); benchmark values do not determine firmware duty cycle |
| Radio | TX 0 dBm: 10.6 mA LDO or 4.8 mA DC/DC typical; RX 1M: 9.9 / 4.6 mA typical | [Nordic RADIO electrical table](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/radio.html); radio-only peaks, not average board current |
| TPS22919 | 8 µA ON typical; 2 nA OFF typical at 25°C | [TI SLVSEN5B, p5](https://www.ti.com/lit/ds/symlink/tps22919.pdf); U8 on, U7 off in current normal target |
| 74HC4051 | 8 µA maximum per IC at 25°C, VCC=6 V, static rail inputs | [Nexperia Rev12, p9](https://assets.nexperia.com/documents/data-sheet/74HC_HCT4051.pdf); 16 µA pair used as a DC budget, not dynamic-current characterization at 3.3 V |
| BQ24074 | BAT sleep current 4.3 µA typical / 6.5 µA maximum, no input/no OUT load, TJ=85°C | [TI SLUS810N, p12](https://www.ti.com/lit/ds/symlink/bq24074.pdf); baseline bias approximation, actual loaded PowerPath needs measurement |
| TPS63031 | VIN/VINA quiescent 25 / 35 µA typical/max; output quiescent 4 / 6 µA, specified test conditions | [TI SLVS696D, p5](https://www.ti.com/lit/ds/symlink/tps63031.pdf); efficiency depends on operating point; not simply “96%” |

The current target has `CONFIG_ZMK_SLEEP=n`, keeps the AFE on between frames, disables battery reporting and does not drive the status LED. The custom board does not enable REG1 DC/DC: generated device tree uses regulator mode 0 (LDO). [Raytac Version L](https://www.raytac.com/download/index.php?index_id=43) states that the REG1 inductor is inside the module, so enabling DC/DC is a possible later firmware optimization, not current behavior. No-typing time still includes continuous EC scanning; advertising and reconnection may consume more than an established link.

There are 75 sampled matrix positions per frame. Explicit waits are `15×3 + 75×(10+5) = 1170 µs`; acquisition is `75×40 = 3000 µs`; allocating 2 µs per conversion gives 150 µs; the loop then sleeps 4000 µs. The sum is **8320 µs before GPIO, driver and scheduler overhead**. ADC blocking may let the CPU sleep, so 4320/8320 is not a measured CPU duty ratio. Instrument the scan thread and battery current to establish it.

## Equations and assumptions

Units below are mA, V, mAh and hours. `I_MCU` includes CPU, ADC, clocks, BLE and software overhead together, avoiding a second addition of the same radio/ADC current.

```text
I_3V3 = I_OPA + I_MCU + 2×3.3/100000×1000 + 0.008 + 0.016 + 0.100
       = I_OPA + I_MCU + 0.190
I_battery = 3.3×I_3V3/(V_battery×η) + V_battery/100000×1000 + I_BQ + I_PCM
t = capacity×f_usable/I_battery
```

Two 100k pull-downs (R44, R50) draw 66 µA when `/CE` and AFE_EN are high. R48 draws separately from VSYS, approximated by battery voltage. The 0.100 mA allowance covers remaining passive/output and dynamic logic loads; it is **assumed**. PCM current is also unknown (10 µA planning / 20 µA stress assumed). End-to-end regulator efficiency includes regulator quiescent losses, so its quiescent current is not added again. No status LED load is assumed; an enabled LED adds approximately `(3.3−Vf)/2200` A at full duty.

| Scenario | OPA mA | Assumed MCU average mA | Assumed η | Assumed battery V | 3.3 V rail mA | Battery mA | 200 mAh hours | 1000 mAh hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Lower demand | 5.2 | 3 | 90% | 3.7 | 8.390 | 8.366 | 19.13 | 95.63 |
| Planning | 5.2 | 6 | 85% | 3.7 | 11.390 | 12.003 | 13.33 | 66.65 |
| Stress | 7.5 | 10 | 80% | 3.3 | 17.690 | 22.172 | 7.22 | 36.08 |

All runtime columns assume **f_usable=0.80**, an engineering reserve for aging, voltage cutoff and environment, not a manufacturer guarantee. The 200 mAh value is the baseline custom-pack target; 1000 mAh references the Honcell bare-cell minimum and requires a qualified finished pack. These are scenarios, not a guaranteed 7–19 h or 36–96 h product range. At the planning point: `3.3×11.39=37.587 mW`, battery power is `44.40981 mW`, and `3.7×0.2×0.8 / 0.04440981 = 13.33 h`. Capacity increase alone scales this scenario by five.

Reproduce with `python3 scripts/calculate_yeti60_power.py`. [CSV](../../hardware/bom/power-scenarios.csv) and [JSON](../audit/yeti60-power-budget.json) contain unrounded intermediate values and source hashes. [Source registry](sources.json) identifies versions, locators, retrieval dates and available download hashes.

## Charging and larger-pack compatibility

Current R40=8.87k gives `890/8870=100.34 mA` nominal programmed current, but USB100 caps total input at 100 mA. System power and charger overhead reduce the actual battery charge current. Even the impossible zero-system-load ideal needs `1000/100 = 10 h` before CV taper for a 1000 mAh pack; a hypothetical 85 mA average needs 11.76 h. These are arithmetic examples, not predicted full-charge times.

U5 TMR (pin14) is explicitly unconnected. Its default fast-charge timer is **4/5/6 h minimum/typical/maximum**, and precharge is 24/30/36 min. TI §9.3.5.6 describes proportional timer slowing under DPPM, input-voltage or thermal regulation; it does not approve arbitrary charge duration. The approximately 100 mA ISET reference and finite timer make a full 1000 mAh recharge incompatible with an unqualified drop-in claim. A resistor alone within the documented TMR range (18–72k) reaches at most 7.2 h at the minimum timer factor, still needing evaluation against charge current and CV time. Do not disable or repeatedly reset safety timers as a substitute for a proper charge design.

**Decision:** the recessed case can be evaluated geometrically for a larger pack, but the current PCB/firmware remains the 200 mAh/USB100 electrical configuration. A larger-pack electrical variant must separately qualify ISET, input budget after USB enumeration, TMR, termination, pack temperature window and maximum charge current. Keep its firmware/configuration distinct from the 200 mAh pack. The current BQ24074/103AT-2 typical temperature range extends beyond a 0…45°C cell specification; the custom pack must provide the independent thermal interruption already required by the assembly specification.

The power switch disables the 3.3 V converter, not the complete charger/battery path. BQ bias, converter shutdown, PCM leakage and cell self-discharge remain. No storage-life or weeks-long idle-runtime claim is justified. Before release, use a calibrated battery-side power analyzer with the normal firmware, debugger/USB disconnected, logging off, testing typing, connected idle, advertising, reconnect, switch-off, and charge-to-termination over the accepted temperature/voltage range.
