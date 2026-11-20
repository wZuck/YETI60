English | [Chinese](e73-aperture-review.zh-CN.md)

# CORNER-07 drill, solder mask and stencil review

The CORNER-07 fabrication ZIP was checked against the native PCB. The screen matches 852 Excellon via hits per layer and measures them against the four mask and paste Gerbers. Zero holes intersect nominal openings or fall below the conservative drill allowance. [CORNER-07 fabrication ZIP measurements](../../delivery/YETI60-E73/06-validation/cam-apertures.json)

The original back-side gaps below are from the [archived CORNER-06 fabrication ZIP measurements](https://github.com/wZuck/YETI60/blob/e94fe4ee2e16914f796e27543dccfbd14cb4bbc7/delivery/YETI60-E73/06-validation/cam-apertures.json).

| Location | Back mask gap | Back paste gap |
|---|---:|---:|
| U5.17, exposed charger pad | 0.100 mm | 0.150 mm |
| U6.11, exposed regulator pad | 0.100 mm | 0.168 mm |
| C42.2, output capacitor ground | 0.130 mm | 0.130 mm |
| D2.1, LED ground | 0.143 mm | 0.143 mm |
| SW1.1 reset via at (329.350, 124.675) mm | 0.175 mm | 0.175 mm |

The planning allowance is `sqrt(2) × 0.075 + 0.130/2 = 0.17107 mm`. It treats the published positional figure as a per-axis allowance and uses half the maximum positive diameter change as radial growth. The polygon calculation reserves another 0.0002 mm for curved edges. Confirm actual relative drill, mask and stencil registration with the fabricator. [JLCPCB drilling and mask capabilities](https://jlcpcb.com/capabilities/Capabilities)

## Integrated aperture repair

The repair retains ordinary 0.30/0.40 mm drill sizes, through-vias and tenting. All original copper lands and their positions are preserved. C42 loses 0.10 mm at the inner edge of each solder opening. SW1 loses 0.06 mm at the outer edge of each opening in Y. This increases the reset-via gap without moving it into the nearby 3.3 V traces. The D2 ground via moves to (315.516, 122.070) mm and uses a 0.30 mm drill / 0.60 mm land. The existing B.Cu ground segment extends to the new via center. U5 and U6 retain their original thermal vias and copper with larger mask islands and revised stencil windows.

| Result from the CORNER-07 fabrication ZIP | Value |
|---|---:|
| Minimum via gap to either front artwork layer | 0.328 mm |
| Minimum via gap to either back artwork layer | 0.230 mm |
| Smallest conservative drill-only residual including curve allowance | 0.059 mm |
| U5.17 paste coverage of copper land | 58.36% |
| U6.11 paste coverage of copper land | 53.97% |
| U5.17 and U6.11 minimum stencil web | 0.17 / 0.78 mm |
| U5.17 and U6.11 minimum area ratio at 0.125 mm stencil thickness | 1.15 / 1.56 |

KiCad reports zero DRC errors, zero unconnected items and zero schematic parity differences. The strict run retains 100 missing-courtyard warnings for existing non-purchased geometry. [Archived isolated repair proof](https://github.com/wZuck/YETI60/blob/e94fe4ee2e16914f796e27543dccfbd14cb4bbc7/hardware/e73-hhkb-corner/audit/aperture-trial.json) · [Current native DRC](../../hardware/e73-hhkb-corner/audit/DRC-routing-open.json)

TI's general QFN/SON guidance gives a typical 50–70% paste coverage range. The package examples in the individual TI data sheets use about 85% for U5 and 84% for U6. This board's split apertures require first-article stencil transfer, joint inspection and regulator/charger thermal testing. [TI assembly note, §4.4](https://www.ti.com/lit/an/slua271c/slua271c.pdf) · [BQ24074 package drawing](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [TPS63031 package drawing](https://www.ti.com/lit/ds/symlink/tps63031.pdf)

The CORNER-07 native PCB, local footprints, Gerber ZIP and firmware share the same board source. Factory registration and physical first-article acceptance remain open.
