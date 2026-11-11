English | [Chinese](PACKAGE-MODELS.zh-CN.md)

# Current native models and thermal-pad construction

Use this candidate's complete project, local footprint library and `models/` directory with KiCad 10.0.7 and its standard 3D library. All 75 fitted parts have one model; electrodes and the unpopulated JP1 have none. The held long-USB reference is outside this repair. Standard models remain external library dependencies; their hashes and local-model attribution are in [model sources](models/model-sources.json).

U2/U4 now use the purchased TSSOP16 package instead of duplicate SSOP models. L1 uses the 3020 model with 2.0 mm height. [Nexperia's package drawing](https://assets.nexperia.com/documents/package-information/SOT403-1.pdf) and [Wurth's component drawing](https://www.we-online.com/components/products/datasheet/74438336015.pdf) support those choices. J2 now uses the standard SH3 model following the [low-profile battery-interface revision](BATTERY-SERVICE.md). Its three contacts and two retaining feet are checked against replacement native lands; the old PH/Celestial model belongs to the held Git checkpoint. U5 and SW100 have project-generated dimensional illustrations; molding details are approximations. Models do not certify supplier tolerances.

## Changes that affect fabrication and soldering

- U5's copper EP is **1.68 × 1.68 mm**, with **0.60 × 0.24 mm** lead lands on 0.50 mm pitch, following [TI RGT0016C](https://www.ti.com/lit/ds/symlink/bq24074.pdf), package outline/layout pages. Two small BAT_NTC/ICHG_SET toe connections were extended. The footprint's legacy `EP1.6x1.6` filename is retained as an identifier; it does not describe the revised copper.
- U5/U6 retain their short ground paths and ordinary **0.30/0.50 mm drill/land vias**. Both faces request solder-mask tenting. A **0.50 × 0.50 mm mask island** on the component face protects each thermal hole; four custom surrounding openings expose the remaining thermal copper. This uses ordinary mask artwork, without resin filling or copper capping.
- Four rounded paste windows per device avoid the mask island. Coverage is `sum(w*h - (4-pi)*r*r) / EP_area`: U5 **1.639816 / 2.8224 = 58.100%**; U6 **1.218910 / 2.4 = 50.788%**. Minimum internal stencil web is **0.16 mm**. These are geometric print ratios, not measured solder volume or void fraction. [TI SLUA271C §4.4](https://www.ti.com/lit/an/slua271c/slua271c.pdf) gives a typical 50–70% starting range and requires process development.

Order the current PCB and filtered bottom stencil together. Select conventional tented vias and **tell the fabricator to retain the U5/U6 mask islands and custom openings**. JLC explains [ordinary tenting versus plugging/filling](https://jlcpcb.com/help/article/pcb-via-covering) and [how intentional mask-defined features must be communicated](https://jlcpcb.com/help/article/how-to-order-boards-with-solder-mask-defined-pads). Tenting is not a guarantee that every manufactured hole is sealed. Fabricator DFM and incoming inspection must confirm the actual mask result; do not scrape away the islands or substitute the previous stencil.

Before applying paste, inspect both thermal-hole caps and the surrounding copper openings under magnification. Reject damaged/pinholed or altered caps for this assembly process. Controlled reflow and hidden-joint/thermal inspection remain first-article requirements; source geometry does not prove solder quality, charge safety or void fraction.

## Verification and firmware

The [native model record](audit/native-models.json) covers all 75 exported shapes and seven landing checks. SH/TSSOP flat feet must lie over native copper; the MAPI model has intentional heel overhang and records **91.66%** nominal planar overlap against the manufacturer's land pattern. Panasonic/C&K locating pegs intentionally enter NPTH holes; their complete dimensional tolerance acceptance remains open.

Collision envelopes include complete nominal models and terminals, with a 0.10 mm modeling allowance. SW100 instead uses the separate 3.60 mm installed-height acceptance envelope. This allowance is not a supplier tolerance. Matching firmware must be rebuilt because the PCB fingerprint changes. Use the current calibrator and normal bundle together; thresholds from an older fingerprint require recapture. Follow [the current assembly entry](ASSEMBLY.md) and [open-bench checks](../../OPEN-BENCH.md).
