English | [Chinese](aperture-review.zh-CN.md)

# CORNER-06 drill, solder mask and stencil review

The fabrication ZIP in this delivery uses CORNER-06. Its Excellon via hits were matched to the native PCB and measured against all four actual mask and paste Gerbers. The screen covers 852 vias per layer. No nominal via-drill intersections were found. Four back-side vias have small margins once a conservative drill allowance is applied. [Fabrication ZIP measurements](cam-apertures.json)

| Location | Back mask gap | Back paste gap |
|---|---:|---:|
| U5.17, exposed charger pad | 0.100 mm | 0.150 mm |
| U6.11, exposed regulator pad | 0.100 mm | 0.168 mm |
| C42.2, output capacitor ground | 0.130 mm | 0.130 mm |
| D2.1, LED ground | 0.143 mm | 0.143 mm |
| SW1.1 reset via at (329.350, 124.675) mm | 0.175 mm | 0.175 mm |

The planning allowance is `sqrt(2) × 0.075 + 0.130/2 = 0.17107 mm`. It treats the published positional figure as a per-axis allowance and uses half the maximum positive diameter change as radial growth. The polygon calculation reserves another 0.0002 mm for curved edges. Confirm actual relative drill, mask and stencil registration with the fabricator. [JLCPCB drilling and mask capabilities](https://jlcpcb.com/capabilities/Capabilities)

## Isolated repair trial

The trial retains ordinary 0.30/0.40 mm drill sizes, through-vias and tenting. All original copper lands and their positions are preserved. C42 loses 0.10 mm at the inner edge of each solder opening. SW1 loses 0.06 mm at the outer edge of each opening in Y. This increases the reset-via gap without moving it into the nearby 3.3 V traces. The D2 ground via moves to (315.516, 122.070) mm and uses a 0.30 mm drill / 0.60 mm land. Its existing ground segment is shortened or extended to meet the via. U5 and U6 retain their original thermal vias and copper with larger mask islands and revised stencil windows.

| Result after replay | Value |
|---|---:|
| Minimum via gap to either front artwork layer | 0.328 mm |
| Minimum via gap to either back artwork layer | 0.230 mm |
| Smallest conservative drill-only residual including curve allowance | 0.059 mm |
| U5.17 paste coverage of copper land | 58.36% |
| U6.11 paste coverage of copper land | 53.97% |
| U5.17 and U6.11 minimum stencil web | 0.17 / 0.78 mm |
| U5.17 and U6.11 minimum area ratio at 0.125 mm stencil thickness | 1.15 / 1.56 |

KiCad reports zero DRC errors, zero unconnected items and zero schematic parity differences. The strict run retains 100 missing-courtyard warnings for existing non-purchased geometry. [Trial measurements and source hashes](aperture-trial.json)

TI's general QFN/SON guidance gives a typical 50–70% paste coverage range. The package examples in the individual TI data sheets use about 85% for U5 and 84% for U6. This board's split apertures require first-article stencil transfer, joint inspection and regulator/charger thermal testing. [TI assembly note, §4.4](https://www.ti.com/lit/an/slua271c/slua271c.pdf) · [BQ24074 package drawing](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [TPS63031 package drawing](https://www.ti.com/lit/ds/symlink/tps63031.pdf)

The repair is an isolated candidate with synchronized footprint copies and its own KiCad and CAM evidence. The consolidated Gerber ZIP still identifies CORNER-06. Before replacing it, integrate the repair into the native project and regenerate the board-bound firmware, fabrication files and acceptance reports. The ordinary-process fabrication and physical first-article checks remain open.
