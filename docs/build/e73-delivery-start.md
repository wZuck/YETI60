English | [Chinese](e73-delivery-start.zh-CN.md)

# YETI60 E73 — start here

This is the handoff entry for the **E73 lower-right HHKB candidate**. Keep this whole folder together. The English and Chinese manuals are separate documents; filenames and part numbers identify the same physical design.

**Current state: engineering review, not an order release.** Matching PCB, CAM, BOM and buildable firmware are bundled. The nine-wire route and 16 rigid retainers / 17 film pieces have passed bounded static checks. The delivery includes assembled, exploded, interior and PCB underside views. Retainer process, closed-case service and the final power/battery/manufacturing review remain open. The supplied bottom is the reviewed mechanical baseline, not a qualified complete harness assembly. The manifest records these limitations; a successful file-integrity check does not waive them.

| Task | Read / use |
|---|---|
| Open the current native KiCad project, identify the revision | [Project files and revision checks](e73-project-files.md) |
| Understand what to order and which options to select | [PCB and mechanical manufacturing instructions](e73-ordering-printing.md) |
| Check all nine leads, pin maps, free lengths and open gates | [Current harness study](../engineering/e73-corner-harness.md) |
| Print and locate the 16 retainers and cut 17 films | [Retainer files, placement plan and dry-fit guide](../engineering/e73-retention.md) |
| Check plug access and lifting the PCB before closing the case | [Case assembly and removal checks](../engineering/e73-corner-service.md) |
| Buy parts, credit existing inventory, identify every fitted reference | [Complete materials](../../README.md), [mainboard BOM / stock CSV](../../hardware/e73-hhkb-corner/mainboard-purchase.csv) |
| Ask the battery supplier to confirm pack parameters | [Complete pack specification](../engineering/battery-pack-specification.md) |
| Solder a blank PCB in stages and test each stage | [12-step PCB soldering and bench guide](../assembly/e73-corner/soldering.md), [illustrated web guide](../assembly/e73-corner/soldering.html) |
| View the closed keyboard, exploded parts and dry-fit stages | [Assembly views](e73-assembly-views.md) |
| Assemble the NiZ mechanism and plate stabilizers | [Parts, plate and mechanism guide](key-mechanism.md) |
| Connect SWD, install calibration firmware, calibrate all 60 keys and install normal firmware | [Firmware installation and calibration](../testing/e73-corner-firmware.md) |
| Review electrical, fit, antenna and release limitations | [Current E73 engineering review](../engineering/e73-hhkb-corner.md) |
| Review charging headroom, dissipation and ordinary PCB fabrication | [Current power and process review](../engineering/e73-corner-power-process.md) |
| Record CAM, soldering, charging, all keys, case closure and BLE | [First-article record](../testing/e73-first-article.md) |
| Browse offline | Open `index.html` in the delivery folder; no server or network is needed for bundled content |
| Verify file provenance | Read `manifest.json`; checksums bind the copied files to their source PCB and matching firmware |

## Follow this sequence

1. Read the engineering status and manufacturing instructions first. Use this corner candidate's files together. The original upper-right E73 and Raytac packages are separate revisions.
2. Count the planned stock before purchasing. The fitted mainboard needs 75 parts: 8 are planned from inventory and 67 require purchase; this is not the total mechanical, cable or tool count. Buy the passive values/packages and meet any effective-capacitance requirements in the BOM.
3. Retain the **already-made C5 JSH daughterboard**. One mainboard is installed per keyboard. J3 is a pogo/SWD contact pattern on that mainboard, not another PCB to print.
4. Follow the staged soldering guide: inspect the blank board; install and check the power section; add control/analog/reset parts and connectors; reflow the E73 module with its hidden lands; then carry out the stated unpowered and current-limited checks. The guide assigns all 75 fitted references exactly once.
5. Keep the battery disconnected for initial power and SWD work. Disconnect the bench supply physically before connecting host USB. Use the exact J3 pin map in the guide, not a generic connector pin map.
6. Assemble the NiZ/plate mechanism for meaningful key calibration. A shell is not needed to begin USB enumeration, firmware, raw sensing and BLE bench validation; domes/springs and the completed mechanism are needed to qualify all keys. Bare-board simulation is not physical EC acceptance.
7. Flash the supplied calibrator HEX, calibrate/save all 60 positions, then flash the matching normal HEX while preserving settings as documented. HEX is address-bearing; do not guess the address of the raw BIN. The USB connector is not a claim of an installed USB bootloader.
8. Validate USB data while charging from the same host connection, unplug-to-BLE behavior, battery-temperature faults and key sensing on the prototype. Insert the battery only after its complete-pack drawing, protection and NTC parameters are confirmed.
9. Build the shell and install the final cables only after the current harness, retention and closed-case drawings are released. Recheck all keys, cable trapping, charging temperatures and BLE in the assembled keyboard.

## Read the evidence correctly

Native DRC and source-bound firmware/host simulation can be checked before ordering. Vendor lead dimensions, crimp quality, incoming parts, resin shrinkage, actual NiZ retention/travel, USB signal integrity, BLE range/EC immunity and battery thermal behavior require supplied parts or a prototype. The steel plate still overlaps the provisional antenna region; the project does not claim verified 2–3 m operation.

The consolidated folder is an offline snapshot. External manufacturer/provenance links are references, while the indexed local files are the snapshot's deliverables. Recheck its manifest after any file is replaced.
