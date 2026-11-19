English | [Chinese](e73-first-article.zh-CN.md)

# CORNER-06 first article

Start with the bare board and the already-made C5 daughterboard. The bench stages do not require a case. Use a battery simulator for the first charging tests. The later stages require the NiZ mechanism, the specified pack and the closed case.

Copy this page for each unit. Record the PCB and firmware digests from the delivery manifest, the actual PCB thickness, the C5 revision, the pack identifier, ambient temperature, host, cable and instruments. Record measurements beside each result. A checked design report cannot populate a physical result.

| Stage | Test and evidence | Pass condition |
|---|---|---|
| Factory CAM | Compare board preview and stack offer with the [order instructions](../build/e73-ordering-printing.md). Inspect NPTH, slots, two stencil layers, C42/C48 drill relocation and SW1, U5 and U6 registration | Ordinary four-layer process and the reviewed geometry accepted by the factory. Record any proposed CAM changes before accepting them |
| Bare board | Check joints and polarity, then use the staged limited-power test. Confirm the 3.3 V rail and the J3 contact map | No short, abnormal current or heating. Correct rail and SWD identification. [Soldering steps](../assembly/e73-corner/soldering.md) |
| Flash and open bench | Program the calibrator using SWD. Start with the pack disconnected. Check the C5 cable orientation and USB enumeration | Programmer verifies the image. Correct USB device enumerates and stays connected. [Firmware and J3 pin map](e73-corner-firmware.md) |
| Pack simulator | Observe charger IN, OUT, BAT, current and VBUS at the E73 during USB preconfiguration, configuration, weak input, suspend, resume and board-off USB100. Check new and worn cable conditions as applicable | Charging follows the documented policy. Keyboard stays on USB HID during current foldback. VBUS at U1 stays within its operating range while active. No reset or loss of the typed sequence. [Power-path limits and test points](../engineering/e73-corner-power-process.md) |
| All keys | Assemble the plate, domes and springs outside the case. Save 60 calibration positions and program the matching normal image with settings retained. Test each press and release, plus both stabilized ends of the three large keys | All 60 physical positions produce their expected key or layer behavior. Both edges of each stabilized key return without sticking. [Mechanism guide](../build/key-mechanism.md) |
| Physical battery | Review the pack supplier drawing, ratings, polarity, thermistor and separately implemented temperature interruption. Measure charge current, termination, temperature and off-state draw after the simulator test | Meets the complete supplier-confirmed [pack specification](../engineering/battery-pack-specification.md), including independent temperature interruption and full charge timing |
| Dry-fit and reopening | Fit the printed case and the retained leads without permanent adhesive. Record the release tool, parked plug positions and sequence for inserting and withdrawing the stack. Inspect the USB/power crossover as the PCB moves | Demonstrated insertion and withdrawal with actual parts. No forced motion, cable pinch, contact damage, plug lash or compression on the pouch. [Assembly views](../build/e73-assembly-views.md) · [Case service checks](../engineering/e73-corner-service.md) |
| Closed case | Repeat USB and BLE typing while idle, charging and after detach. Try orientations and normal hand positions at 2 and 3 m. Measure charger and pack temperature. Look for missed, false or repeated keys while the radio and charger operate | Meets the target use range and pack/board temperature limits. No unexpected HID events, link loss or unsafe heating over the recorded duration and conditions |

Record a failed stage before continuing. Do not qualify the finished build until the relevant failures are corrected and retested.
