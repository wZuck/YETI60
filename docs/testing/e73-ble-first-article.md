English | [Chinese](e73-ble-first-article.zh-CN.md)

# E73 CORNER-07 Bluetooth range and interference

## Antenna surroundings in M05

The E73-2G4M08S1C drawing shows the ceramic antenna at the end opposite the 13 mm pad row. On CORNER-07 this end faces right. Ebyte advises keeping metal away from the antenna and provides no numeric installed clearance in this manual. The 3 × 13 mm band used here is a project screening region. [Ebyte manual, drawing and installation guidance](https://www.ebyte.com/downpdf/444.html)

| Check | Current design |
|---|---|
| Mainboard copper in the provisional keepout | Zero overlap across all four layers |
| 304 stainless-steel plate | Covers the entire 39 mm² band in projection. Closest gap to the bounded U1 body envelope is 1.10 mm |
| Right-hand side of the M05 enclosure | Nine horizontal CAD paths from the outer end of the antenna band cross 15.69–19.23 mm of shell material before the outer wall. The sampled paths pass beneath the plate. The planned shell material is unfilled engineering resin |
| Transmitter configuration | 0 dBm in the normal and calibrator builds. The evaluated configuration hashes match the firmware build record |

The case-path values describe material thickness along the chosen CAD lines. They do not supply the dielectric properties of the printed parts, antenna impedance, radiation pattern or attenuation. The steel remains close to the antenna, and nearby hands, screws, resin formulation, the desk and the host affect the link. [CAD probes and calculation inputs](../../hardware/e73-hhkb-corner/audit/radio-path.json)

## Reference at 2 m and 3 m

Free-space loss is `20 log10(4πdf/c)`, with distance in metres, frequency in hertz and `c = 299792458 m/s`. The example uses 0 dBm transmit power and 0 dBi antenna gains at both ends. It allows 15 dB for fading as a planning reserve. Nordic lists typical receiver sensitivity of −95 dBm at LE 1M for short packets and −92 dBm at LE 2M. The example host sensitivity is an assumed −85 dBm. Its power and sensitivity depend on the actual host. [ITU-R P.525-5](https://www.itu.int/rec/R-REC-P.525-5-202411-I/en) · [Bluetooth LE channels](https://www.bluetooth.com/wp-content/uploads/2023/03/bluetooth-le-regulatory-aspects-document.pdf) · [Nordic receiver table](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/radio.html)

| Distance | Free-space loss across 2402–2480 MHz | Additional loss available toward E73 at 1M / 2M | Additional loss available toward example host |
|---|---:|---:|---:|
| 2 m | 46.08–46.36 dB | 33.64 / 30.64 dB | 23.64 dB |
| 3 m | 49.60–49.88 dB | 30.12 / 27.12 dB | 20.12 dB |

The last two columns use the upper band edge and subtract the 15 dB reserve. Going from 2 m to 3 m adds 3.52 dB in free space. The link budget gives room for additional loss under these assumptions. Measuring the assembled keyboard is necessary to determine how much of that room remains.

## Verify the first article

1. With the case off, run the [bench power checks](e73-bench-power.md). Use the simulator to confirm BLE pairing and reconnect on battery power with USB disconnected. If the key stack is already fitted and calibrated, check typing at 2 m and 3 m on the intended host. Record this as the open-stack reference.
2. Fit the complete M05 enclosure, steel plate, intended protected battery and all fasteners. Repeat on the same host and desk, with the USB cable disconnected. Measure from the antenna end to the host. At each distance rotate the keyboard through 0°, 90°, 180° and 270° and type the same known sequence with a normal hand position. Include one trial with the right hand near the antenna end. Record at least 100 expected key-downs per distance across the orientations and check the releases as well. Look for unexpected events during a 60-second idle period. Check reconnect after a power cycle at 3 m.
3. Test USB typing while the host configures and charges the battery. Log charge current, missing or false keys, and any reconnects. USB takes priority while configured. Repeat BLE typing on battery after detach and compare with the open-stack log. Test on the intended desk with usual Wi-Fi and peripherals operating.
4. If the closed case fails and the open stack passes, repeat the same orientation and distance with the top removed to distinguish an enclosure effect. For radio-only comparisons without the steel plate, support the board safely and compare pairing, link continuity and RSSI if the host reports it. Keep the host, distance, geometry and radio settings fixed. Test typing with the calibrated key stack in place.

| Case / power | Host and orientation | Distance | Expected / observed keys | Link loss, reconnect and idle events | RSSI if available |
|---|---|---:|---|---|---|
| | | | | | |

Pass when the assembled keyboard repeats the expected input without loss, duplicates, false input or link drop across the recorded 2 m and 3 m conditions. Enter the results in the [first-article acceptance record](e73-first-article.md).
