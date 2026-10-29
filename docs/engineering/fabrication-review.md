English | [Chinese](fabrication-review.zh-CN.md)

# P2 fabrication and assembly review handoff

The [review archive](../../hardware/fabrication/yeti60-p2-dfm-review.zip) is for fabricator/assembler DFM review. It does not authorize an order. Rebuild it with `python3 scripts/export_yeti60_fabrication.py`; the [manifest](../audit/yeti60-fabrication.json) binds the archive to the PCB, BOM and instructions.

## Supplied outputs

Four copper Gerbers, both masks/paste/silkscreens/fabrication layers, board outline, separate plated/nonplated through drill files, IPC-D-356 connectivity, a 76-part placement CSV, English/Chinese purchase requirements and ordinary-process notes. JP1 is DNP. Electrode/fixture geometry is excluded from purchasing/placement, but preserved in the PCB/Gerbers. These are mainboard outputs; purchase the complete C5 JSH daughterboard separately.

The exporter verifies absence of layer-pair blind-drill files, all 76 fitted placements and unchanged PCB source. Placement uses the absolute KiCad origin in mm, without negating bottom-side X; the assembler must confirm rotation/side conventions against the native PCB and a first article. The archive's manifest records file hashes. Its two language versions carry the same technical instructions.

## Written DFM response required

| Item | Required supplier response |
|---|---|
| Stack | Select ordinary JLC04161H-7628, nominal 1.6 mm, finished range 1.44–1.76 mm; the 1.6062 mm CAD envelope includes modeled mask and is not a custom order thickness. See [ordinary notes](../../hardware/ec60-nrf52840/fabrication-notes.md) |
| Through vias | All ordinary mechanical through holes, minimum land/drill 0.50/0.30 mm; no blind/buried or special filling process |
| Module escape | Confirm no U1 vias-in-pad; two signals escape through off-pad vias without capping |
| Surface and assembly | ENIG; review U1 module and U5 exposed-pad soldering, U5 thermal via/paste wicking, stencil apertures, cleaning and inspection |
| Geometry | Identify every required trace, spacing, drill, slot, mask or courtyard concession using coordinates and a marked drawing; do not silently alter electrode copper, nets or the specified ordinary stack |
| Acceptance | Native-netlist electrical test, ordinary dimension/thickness inspection and solder-process acceptance |

The existing DRC/ERC warnings remain review inputs; a zero-error report is not a zero-warning report. Do not delete warnings simply to claim readiness. Changing dielectric or via construction requires engineering review because the EC sensing electrodes depend on the stack.

## Assembly release conditions

The BOM contains unselected passive MPNs, F1 and D2. Before assembly release, record exact orderable parts, resistor ratings/tolerance, fuse hold/trip/temperature behavior, LED polarity/Vf/current, and capacitor effective capacitance at operating bias, tolerance and temperature. Nominal 20 uF at C45/C46 is not proof of the regulator's required effective output capacitance. Request manufacturer bias data or measurements for the final selected capacitors and compare with the TPS63031 requirements.

For the first lot, use the [assessment response and prototype gates](assessment-response.md). Battery procurement additionally requires the [pack specification](battery-pack-specification.md). Vendor DFM acceptance, quotations, physical waveforms and assembly yield remain open; no supplier was contacted by this workflow. SI/RF remains deferred.
