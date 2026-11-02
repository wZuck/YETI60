English | [Chinese](ordering.zh-CN.md)

# PCB ordering worksheet

Return to the [build handbook](../../BUILD.md). These are design-required selections, not a completed quote. **Ordering is not yet released**; close the handbook's outstanding work and use synchronized files.

## Which PCBs

One [Raytac mainboard archive](../../hardware/fabrication/yeti60-raytac-p2-dfm-review.zip) per keyboard; compare its [native PCB](../../hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb) and [file manifest](../audit/yeti60-fabrication.json). The archive excludes C5. Buy one populated C5 JSH, or separately fabricate one [pinned upstream C5](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip) and obtain its [seven parts](../../hardware/bom/daughterboard.csv). No SWD PCB is needed: J3 is on the mainboard. The plate is a mechanical part. Prefer populated C5 for the first prototype; do not substitute S, PH or an unprotected connector breakout.

| Order field | Mainboard selection |
|---|---|
| Product/material | Ordinary rigid FR-4; no HDI, aluminium, flex or Rogers |
| Layers | 4: F.Cu, In1.Cu, In2.Cu, B.Cu |
| Thickness | **1.6 mm**, not the 1.6062 mm CAD envelope |
| Stack | Ordinary **JLC04161H-7628**; outer-to-inner dielectric target 0.2104 mm; no unreviewed substitution |
| Copper | 1 oz outer; stock approximately 0.5 oz inner; no extra copper |
| Bounds | Approximately **289.39x94.60 mm**, including rounded RF wing; never crop to a 285 mm rectangle |
| Quantity | One net per keyboard; prepare two assembled prototypes if practical; order platform minimums and retain spares |
| Panelization | Single design/single board; assembler must approve any process rails without occupying electrodes/antenna |
| Mask/silkscreen | Green/white; preserve orientation, holes and functional reference marks |
| Finish | Standard ENIG; no hard gold/gold fingers |
| Vias | Ordinary mechanically drilled through vias, minimum hole/land 0.30/0.50 mm; normal tenting subject to process review |
| Special vias | No blind/buried/laser, resin filling/capping or special via-in-pad; review U5 open thermal-via solder loss |
| Castellations/edge plating/fingers | None; module castellations do not require castellated mainboard fabrication |
| Impedance | No claim of verified 90 ohm differential routing; selecting a quote checkbox cannot qualify USB. Retain stock stack, review paths and measure prototypes |
| Electrical test | Bare-board netlist test against IPC-D-356/native connectivity |
| Factory mark | Supplier-approved position outside sensing electrodes, antenna and mounting contact areas |
| Stencil | **B.Paste**, bottom; 0.10 mm stainless is a process-review starting point; omit JP1, approve U5/U6 exposed-pad apertures and open-via wicking |
| SMT | Disable for self-assembly. Otherwise supply this BOM, 75-part placement, PCB and stencil requirements; ordinary PCB availability does not guarantee module PCBA stocking |

Inspect the upload preview for four copper layers, correct dimensions/orientation, 29 mounts, RF wing and both plated/nonplated drill sets. Stop before payment if interpretation differs. No silent electrode/net/stack/outline changes are permitted.

C5 self-assembly uses **18.0x16.5 mm, four layers, 1.6 mm**, mounting rectangle 14x12.5 mm, ordinary FR-4/through vias, stock 1 oz outer copper, green/white and ENIG. Its stencil is **F.Paste**. Submit upstream geometry for supplier review: native defaults disclose courtyard/library and 0.25 mm edge findings. All seven parts, including U1 data protection and D1 VBUS protection, are mandatory.

Supplier note: engineering prototype, ordinary four-layer JLC04161H-7628/1.6 mm/ENIG/mechanical through vias; preserve electrodes, 29 mount centres and rounded RF wing. No stack substitution or HDI/fill/capping. Test against native nets and return marked coordinates for any trace, space, edge, drill or mask concession before modifying files.

See [fabrication requirements](../../hardware/ec60-nrf52840/fabrication-notes.md), [DFM checklist](../engineering/fabrication-review.md), [JLC capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/) and [stack information](https://jlcpcb.com/impedance). No quote or supplier acceptance has been obtained.

Order the new 1.60 mm stainless plate separately using the [NiZ / plate-mount plan and machining requirements](key-mechanism.md). It is neither the original undersized plate nor another PCB. No stabilizer mounting holes are added to the mainboard.
