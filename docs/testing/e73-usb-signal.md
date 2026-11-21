English | [Chinese](e73-usb-signal.zh-CN.md)

# E73 CORNER-07 USB full-speed path

The path is the host cable, the existing C5 JSH daughterboard, the M05 twisted pair, J4, and the CORNER-07 mainboard to U1. The nRF52840 uses USB full speed at 12 Mb/s. J4.2 carries D− and J4.3 carries D+. [Nordic USBD specification](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/usbd.html) · [M05 print and wiring guide](../build/e73-m05-prototype.md)

## Model results

The longer PCB centreline is 101.29 mm excluding the vertical via. Most of it is a 0.30 mm trace on B.Cu, with a nominal 0.20 mm copper gap and In2.Cu reference copper. The M05 pair reaches 285.29 mm across the geometric cases, from connector exit to connector exit. [Native route check](../../hardware/e73-hhkb-corner/audit/USB-reference.json) · [Bound calculations and model sweeps](../../hardware/e73-hhkb-corner/audit/usb-signal.json)

The straight PCB section uses 0.2104 mm between copper and the reference plane, 35 µm copper, a 7628 dielectric constant of 4.4, and JLC's representative solder mask parameters. A two-dimensional electrostatic solve drives the traces at ±0.5 V, finds capacitance per unit length with the dielectric and with vacuum, and computes `Zdiff = 1 / (c × sqrt(C × C0))`. The fine-grid estimate is **88.26 Ω**, within 0.17 Ω of the coarser mesh. Varying assumed etched width from 0.27 to 0.33 mm, changing the gap oppositely, and varying dielectric height from 0.18 to 0.24 mm and Dk from 4.2 to 4.6 gives illustrative extrema of **76.19 and 100.91 Ω**. These corners are a sensitivity test. The ordinary fabrication quote determines actual tolerances. [JLC stack and material data](https://jlcpcb.com/impedance)

At the nominal calculation, the modeled PCB delay is 0.59 ns. A harness propagation speed of 0.65c gives 1.46 ns for the longest M05 data conductor. The two estimated delays total about **2.05 ns**. The ngspice sweep uses the full routed PCB length as one uniform section. A 3 m, 90 Ω external cable with 15 ns of delay, a 90 Ω differential source, a 15 pF load with a 15 kΩ differential DC path, and a 4 ns source edge (10–90%) define the reference experiment. C5 has two TPD4E05U06 protection channels per conductor. The model uses a 0.5 pF differential equivalent for the two 1.0 pF per-line shunts. [TI protection diode data](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf) · [USB-IF full-speed electrical test notes](https://compliance.usb.org/index.asp?Format=Standard&UpdateFile=Electrical)

| Assumed M05 pair impedance, nominal PCB | Largest modeled reverse excursion after the rising-edge zero crossing, host → U1 | U1 → host |
|---|---:|---:|
| 75 Ω | <0.01 V | 0.38 V |
| 90 Ω | <0.01 V | 0.04 V |
| 120 Ω | 0.43 V | 0.48 V |
| 150 Ω | 0.91 V | 0.88 V |

The sweep measures how much the differential voltage drops from an earlier peak during the 60 ns after the crossing. With the harness held at 90 Ω, the two PCB geometry corners gave up to 0.15 V of reverse excursion. The result puts the harness impedance high on the list of first-article measurements. The ideal lines exclude connector and via transitions, return discontinuities at the launches, conductor and dielectric loss, and common-mode conversion. Actual transmitter and receiver models and the finished cable impedance are open. USB compliance requires the finished device, its cable, and the USB-IF measurement procedure. [USB-IF signal quality procedure](https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf)

## First-article test

1. Before power, confirm C5 JSH pin 2 to J4.2 and pin 3 to J4.3, verify ground continuity on pin 4, and check for shorts. Use a known data cable. Keep the M05 pair together and verify the insulation envelope before installing guides.
2. With the case off and a battery simulator fitted for charging tests, run both HEX images. Observe full-speed enumeration, reports or calibration traffic, reset, suspend/resume, and detach/reconnect. Repeat both plug orientations and use the intended external USB cable. Verify USB HID during charging using the [bench procedure](e73-bench-power.md).
3. Repeat when the M05 guides and case are fitted. Record the cable, host port, negotiated speed, charge state, any link resets or protocol errors, and the expected versus received key sequence.
4. If the bare board and assembled case behave differently, compare the assembled M05 harness with a known short USB pair on the same C5 and mainboard. Preserve the ground connection and pin order. For an electrical sign-off, measure the finished pair or an equivalent terminated sample by differential TDR and check the finished full-speed device with the USB-IF test setup. Use **90 Ω differential** as the matching target when selecting the pair, with insulation and contacts that fit the released M05 geometry.

Record the results with the [first-article checks](e73-first-article.md). A passing functional test on one cable documents that operating combination.
