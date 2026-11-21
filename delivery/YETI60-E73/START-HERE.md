English | [Chinese](START-HERE.zh-CN.md)

# YETI60 E73 — start here

This is the handoff entry for the **E73 lower-right HHKB candidate**. Keep this whole folder together. The English and Chinese manuals are separate documents; filenames and part numbers identify the same physical design.

**Engineering review.** The first article uses the CORNER-07 PCB and firmware together with the M05 bottom, two access covers, nine matched conductors, 16 rigid retainers and 17 film pieces. The assembly views and wire lengths use M05. Factory registration, pack confirmation and physical acceptance remain open.

| Task | Read / use |
|---|---|
| Open the current native KiCad project, identify the revision | [Project files and revision checks](01-pcb/project-files.md) |
| Understand what to order and which options to select | [PCB and mechanical manufacturing instructions](01-pcb/ordering-and-printing.md) |
| Download the M05 case, access covers, retainers and matching wire lengths | [M05 first-article printing, wiring and service](02-mechanical/service-case-m05/print-guide.md) |
| Buy parts, credit existing inventory, identify every fitted reference | [Complete materials](03-bom/materials.md), [mainboard BOM / stock CSV](03-bom/mainboard-purchase.csv) |
| Ask the battery supplier to confirm pack parameters | [Complete pack specification](03-bom/battery-requirements.md) |
| Solder a blank PCB in stages and test each stage | [12-step PCB soldering and bench guide](04-assembly/soldering.md), [illustrated web guide](04-assembly/soldering.html) |
| View the closed keyboard, exploded parts and dry-fit stages | [Assembly views](04-assembly/assembly-views.md) |
| Assemble the NiZ mechanism and plate stabilizers | [Parts, plate and mechanism guide](04-assembly/key-mechanism.md) |
| Connect SWD, install calibration firmware, calibrate all 60 keys and install normal firmware | [Firmware installation and calibration](05-firmware/installation.md) |
| Verify open-bench power, charging and USB/BLE switching with a simulator | [Bench connections, probe map and record](06-validation/bench-power.md) |
| Review electrical, fit, antenna and release limitations | [Current E73 engineering review](06-validation/corner-review.md) |
| Check Bluetooth at 2 m and 3 m and isolate enclosure effects | [M05 antenna geometry and Bluetooth test](06-validation/ble-first-article.md) |
| Check the USB pair and test with the final cable | [USB full-speed path and signal checks](06-validation/usb-signal.md) |
| Review charging headroom, dissipation and ordinary PCB fabrication | [Current power and process review](06-validation/power-process.md) |
| Check via clearances and stencil coverage in the fabrication ZIP | [Drill, mask and stencil review](06-validation/aperture-review.md) |
| Record CAM, soldering, charging, all keys, case closure and BLE | [First-article record](06-validation/first-article.md) |
| Browse offline | Open `index.html` in the delivery folder; no server or network is needed for bundled content |
| Verify an unpacked copy | Run `python3 verify.py` in the delivery directory. The [manifest](https://github.com/wZuck/YETI60/blob/master/delivery/YETI60-E73/manifest.json) lists file checksums and the matching PCB and firmware |

## Follow this sequence

1. Read the engineering status and manufacturing instructions first. Use this corner candidate's files together. The original upper-right E73 and Raytac packages are separate revisions.
2. Count the planned stock before purchasing. The fitted mainboard needs 75 parts: 8 are planned from inventory and 67 require purchase; this is not the total mechanical, cable or tool count. Buy the passive values/packages and meet any effective-capacitance requirements in the BOM.
3. Retain the **already-made C5 JSH daughterboard**. One mainboard is installed per keyboard. J3 is a pogo/SWD contact pattern on that mainboard, not another PCB to print.
4. Follow the staged soldering guide: inspect the blank board; install and check the power section; add control/analog/reset parts and connectors; reflow the E73 module with its hidden lands; then carry out the stated unpowered and current-limited checks. The guide assigns all 75 fitted references exactly once.
5. Keep the battery disconnected for initial power and SWD work. Disconnect the bench supply physically before connecting host USB. Use the exact J3 pin map in the guide, not a generic connector pin map.
6. Assemble the NiZ/plate mechanism for meaningful key calibration. A shell is not needed to begin USB enumeration, firmware, raw sensing and BLE bench validation; domes/springs and the completed mechanism are needed to qualify all keys. Bare-board simulation is not physical EC acceptance.
7. Flash the supplied calibrator HEX, calibrate/save all 60 positions, then flash the matching normal HEX while preserving settings as documented. HEX is address-bearing; do not guess the address of the raw BIN. The USB connector is not a claim of an installed USB bootloader.
8. Validate USB data while charging from the same host connection, unplug-to-BLE behavior, battery-temperature faults and key sensing on the prototype. Insert the battery only after its complete-pack drawing, protection and NTC parameters are confirmed.
9. Follow the [M05 first-article guide](02-mechanical/service-case-m05/print-guide.md). Temporarily position the retainers and trial the service sequence with an inert pack gauge. Record closed-case harness, charging temperature and BLE tests on the physical article.

## Read the evidence correctly

Native DRC and source-bound firmware/host simulation can be checked before ordering. Vendor lead dimensions, crimp quality, incoming parts, resin shrinkage, actual NiZ retention/travel, USB signal integrity, BLE range/EC immunity and battery thermal behavior require supplied parts or a prototype. The steel plate still overlaps the provisional antenna region; the project does not claim verified 2–3 m operation.

The consolidated folder is an offline snapshot. To verify a download, run `python3 verify.py` from an untouched copy before opening the KiCad project. Python 3 is the only requirement for this check.
