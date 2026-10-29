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

The current target has `CONFIG_ZMK_SLEEP=n`, slows the scan interval from 4 ms to 30 ms after 30 seconds without a pressed or changed key, and gates the AFE with U8 between idle scans. Any key or state change returns it to 4 ms. Battery reporting is disabled and the adapter does not drive the status LED. The E73 devicetree explicitly selects REG1 LDO, with REG0 DC/DC disabled and DCCH unconnected. The planning table below still assumes the AFE is on continuously, so it is conservative and does not credit idle gating; measured improvement is not a guaranteed runtime. Advertising and reconnection may consume more than an established link.

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

| Scenario | OPA mA | Assumed MCU average mA | Assumed η | Assumed battery V | 3.3 V rail mA | Battery mA | Default 1600 mAh hours |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lower demand | 5.2 | 6.3 | 90% | 3.7 | 11.690 | 11.636 | 110.00 |
| Planning | 5.2 | 8 | 85% | 3.7 | 13.390 | 14.101 | 90.77 |
| Stress | 7.5 | 15 | 80% | 3.3 | 22.690 | 28.422 | 45.04 |

This E73 variant uses REG1 LDO with REG0 DC/DC disabled. Both supply inputs use regulated 3.3 V, without relying on undocumented internal DC/DC inductors. MCU averages of 6.3/8/15 mA are assumed: 6.3 mA references the Nordic LDO flash CoreMark typical benchmark; the other values are engineering scenarios allowing peripheral/radio activity. None is a measured average or guaranteed bound.

All scenarios assume an 80% usable-capacity factor for aging, cutoff and environment; it is not a manufacturer guarantee. The default 1600 mAh is the HCP404074 bare-cell minimum, subject to finished-pack acceptance. Do not advertise 45.04–110.00 h as a guaranteed range. At the planning point, `3.3×13.39=44.187 mW`, battery power is `52.17452 mW`, and `3.7×1.6×0.8 / 0.05217452 = 90.77 h`. No hardware measurement supports a runtime claim yet.

Idle gating is not credited in the table: with a 30 ms idle frame and roughly 5 ms AFE settling plus the scan window, the average AFE current is substantially below 5.2 mA. Actual duty cycle, first-key latency, mux/ADC settling and RF interaction still require first-article measurement. The table intentionally keeps the conservative “AFE continuously on” basis for direct comparison with earlier calculations.

Reproduce with `python3 scripts/calculate_yeti60_power.py`. [CSV](../../hardware/bom/power-scenarios.csv) and [JSON](../audit/yeti60-power-budget.json) contain unrounded intermediate values and source hashes. [Source registry](sources.json) identifies versions, locators, retrieval dates and available download hashes.

## Default P2 charging design

Retain [BQ24074, SLUS810N pp12–13 and 27–28](https://www.ti.com/lit/ds/symlink/bq24074.pdf). R40 changes from 8.87k to 2.21k/1%; add R55=69.8k/1% from TMR to ground and R56=1.69k/1% from ITERM to ground. The old small-pack configuration is not interchangeable.

```text
I_CHG = K_ISET / R40; K_ISET = 797 / 890 / 975 AΩ
minimum = 797/(2210×1.01) = 357.06 mA
typical = 890/2210 = 402.71 mA
maximum = 975/(2210×0.99) = 445.63 mA

t_fast = 10 × R55(kΩ) × K_TMR / 3600 hours
K_TMR = 36 / 48 / 60 seconds/kΩ
minimum / typical / maximum = 6.9102 / 9.3067 / 11.7497 hours

I_TERM = K_ITERM × R56 / R40
K_ITERM(USB500) = 0.0225 / 0.0300 / 0.0375
minimum / typical / maximum = 16.87 / 22.94 / 29.26 mA
cell 0.02C endpoint = 1600×0.02 = 32 mA
```

R56 was reduced from 1.82k to 1.69k in response to the feasibility assessment: maximum termination falls from 31.51 to 29.26 mA, increasing margin to the provisional 32 mA endpoint from 0.49 to 2.74 mA. Lower termination extends CV taper; full-charge/timer acceptance remains required.

The 450 mA value is the **programmed-charge engineering ceiling**, not a certified battery rating. Procurement now requires at least **500 mA continuous pack charging capability** within the accepted temperature window; calculated maximum 445.63 mA then has 54.37 mA rating margin. Supplier confirmation of the inconsistent cell sheet remains mandatory. BQ24074 specifies **4.16/4.20/4.23 V minimum/typical/maximum** regulation over its stated junction-temperature range; the cell supplier must accept the full 4.16–4.23 V range, including the effect of the low voltage corner on delivered capacity. A nominal 4.2 V label is insufficient.

R55's full tolerance range, 69.102…70.498k, stays inside the documented 18…72k range. Precharge timing is one tenth of fast-charge timing. USB100 termination factors are 0.008/0.010/0.012: their limits are not exactly one third of the USB500 limits. JSON records unrounded calculations including resistor tolerances.

The pinned legacy Zephyr `CONFIG_USB_MAX_POWER=250` means 500 mA, verified in both linked ELF descriptors. Only an accepted host configuration enables USB500 and charging; before enumeration, input remains USB100 and charging is disabled. Suspend disables charging and makes the input high impedance; resume retains the accepted configuration. BQ USB500 input-limit min/typ/max is 450/475/500 mA, **not constant 500 mA into the cell**. With an assumed 40 mA system input reserve, `450−40=410 mA` remains above the minimum 357.06 mA setting. The high-current tolerance corner can enter PowerPath current limiting. The 40 mA reserve requires measurement; thermal regulation, cable loss and CV taper also reduce charge current.

The control policy above applies while 3.3 V is on and target firmware runs. **With SW100 off**, hardware pull-downs R42/R43/R44 set EN1=0, EN2=0 and /CE=0, permitting autonomous USB100 slow charging. The board cannot enumerate or select 500 mA in that state, and complete charge time is unverified. A charge-only adapter cannot configure USB while the board is on, so firmware disables charging; switching the board off restores hardware USB100 slow charging. Qualify full-speed charging with the board on and a host accepting 500 mA, and separately test off-state slow charging/timer behavior. Independent pack thermal protection must work without the MCU.

The ideal CC arithmetic at the minimum programmed current is `1600/357.06=4.48 h`, leaving approximately 2.43 h before the minimum fast timer for CV taper. This does not prove full-charge time and excludes deep-discharge precharge, cold operation, thermal limiting and abnormal host power. TI's dynamic timer slows in specified limiting conditions; do not disable or repeatedly reset it to evade acceptance. Supplier curves and first articles must demonstrate termination within the permitted timing/current/temperature conditions; revise the design if they cannot.

The HCP404074 sheet has inconsistent rate/current labels; see [battery selection](battery-study.md). Maximum 445.63 mA exceeds the explicitly stated 270 mA standard current but stays below the 1350 mA maximum stated for 15…45°C. The factory pack must therefore independently guarantee charging only within an actual cell window inside 15…43°C, target 18…40°C including all tolerances. BQ24074 with 103AT-2 alone does not enforce that window; third-wire NTC feedback or a voltage/current-only PCM is insufficient. Written supplier confirmation is required before procurement release.

The switch disables the 3.3 V converter; charger bias, PCM leakage and self-discharge remain. Before release, use a calibrated battery-side analyzer for typing, connected idle, advertising, reconnect, switch-off and full-charge tests across accepted temperature/voltage conditions. Measure runtime using normal firmware, USB/debugger disconnected and logging off. RF/SI remains deferred by the user.
