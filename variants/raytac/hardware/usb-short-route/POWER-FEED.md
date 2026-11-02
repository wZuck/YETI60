English | [Chinese](POWER-FEED.zh-CN.md)

# Revised USB feed: voltage-drop acceptance

The extra J5 → J1 jumper adds two conductor legs and two mated connectors to the charging supply path. This must be qualified with the final wire and mainboard fuse; geometrically fitting AWG28 wires does not establish full-rate charging. The [reproducible calculation](../../scripts/calculate_usb_short_feed.py) and [data](audit/feed-budget.json) cover the new closed-case lengths.

The positive/return circuit is C5 SH → J4 → J5 → J1. The four wire legs in the deliberately pessimistic jumper-return model total approximately 1.0533 m, excluding internal crimp extensions. Four ±0.5 mm free-length tolerances give 1.0553 m for this model. This model uses eight engaged power contacts. The native PCB ground plane also connects J1/J4/J5 ground in parallel with the black power jumper; this calculation deliberately ignores that parallel path. It does not claim that all eight contacts carry identical actual current or solve the PCB current distribution. [JST SH, page 1](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf) specifies up to 20 mΩ initial contact resistance and 40 mΩ after its environmental tests.

```text
R_loop = sum(L_wire × R_wire_per_m) + 8 × R_contact
V_drop = I_input × R_loop
P_harness = I_input² × R_loop
```

For procurement sensitivity, impose wire targets ≤0.25 Ω/m at 20°C and ≤0.30 Ω/m at 60°C. **These are proposed acceptance limits, not verified wire-vendor data.** At the hot target and post-environment contact limit, the model gives approximately 0.637 Ω and 0.318 V drop at 500 mA. Additional crimp length/resistance, external USB/C5 losses and the mainboard fuse/copper are excluded; a finished-loop measurement must include them. Do not interpret the calculated number as a guaranteed maximum for an unspecified purchased harness.

[BQ24074 revision N, electrical table on page 12](https://www.ti.com/lit/ds/symlink/bq24074.pdf) gives USB input DPM threshold limits of 4.35/4.5/4.63 V minimum/typical/maximum. Use 4.63 V for a conservative **full-current headroom screen**, not as an absolute device operating cutoff. With 5.0 V measured at the C5 SH **board pads**, the hot/aged model leaves only about 52 mV for the mainboard fuse and copper before that screen is crossed. At 4.75 V it has no full-current margin even before those losses. Input DPM can reduce charging current; the configured charge current is therefore not a promised charging rate or charging-time guarantee.

Before prototype acceptance:

1. Select the mainboard F1 MPN and prove its hot hold/current derating and resistance. A generic “1206, 0.5 A hold” label is insufficient.
2. Obtain wire resistance versus temperature and finished crimp/loop resistance from the harness supplier. Keep the specified OD and bend geometry.
3. With a battery simulator and normal system load, measure C5 SH voltage, J1 input, U5 IN/OUT and MCU VBUS at USB100 and configured USB500. Include the external USB cable and C5 fuse in the complete test.
4. Verify stable USB typing during charging and current reduction, suspend, unplug/reconnect and battery-only BLE. Do not bypass either fuse or raise the USB current policy to hide a drop.

This calculation adds a qualification requirement; it does not approve the current unspecified fuse/wire or claim observed hardware operation. [Assembly guide](ASSEMBLY.md) · [Candidate entry](README.md)
