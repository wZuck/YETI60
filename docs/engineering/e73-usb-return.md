English | [Chinese](e73-usb-return.zh-CN.md)

# E73 USB reference and local model checkpoint

**The candidate remains unreleased.** This closes specific host-board geometry and nominal model checks for the [isolated USB repair](e73-usb-repair.md). It does not accept the complete keyboard, cable, battery, RF behavior or USB compliance. The selected canonical PCB, firmware and fabrication package are unchanged; retain the existing C5 daughterboard.

## Current checks

| Scope | Result | Evidence |
|---|---|---|
| Actual USB paths | Approximately 9.969 mm each; zero data vias; computed difference below 0.001 mm against the 0.05 mm project limit | [Native candidate check](../../hardware/e73-usb-repair/audit/native-check.json) |
| Data routing | 0.3 mm B.Cu tracks; 0.6 mm pitch on the coupled straight section; pad fanout and length compensation measured separately | [Controlled routing specification](../../hardware/e73-usb-repair-spec.json) |
| Adjacent reference | In2 GND covers both path centerlines and the complete native copper areas of all 18 data-track primitives and all four data lands | [Return geometry](../../hardware/e73-usb-repair/audit/return-check.json) |
| Independent ground connectivity | One connected ground network, with layers joined only through actual plated GND vias/PTH pads | [Return geometry](../../hardware/e73-usb-repair/audit/return-check.json) |
| Reference faults | Pre-repair COL14 crossing, a removed ground stripe under USB, and missing plated ground bridges are detected | [Three regression/fault cases](../../hardware/e73-usb-repair/audit/return-faults.json) |
| Local native models | Actual E73-positioned J4/J5/C32 STEP geometry has 6/4/2 matched solder lands; a shifted header fails the landing check | [Local model check](../../hardware/e73-usb-repair/audit/local-models.json) |

The length differences describe CAD arithmetic, not physical etching accuracy or electrical delay. The partner-distance statistic in the return report is a geometric proximity probe; it is not an impedance measurement or a USB standard limit.

## What changed

COL14 previously cut the reference directly beneath the USB interface. Its local In2 route now detours outside the protected data region and rejoins the original lower column trunk. Its sensor lands, existing sensor vias, net nodes and MCU assignments remain unchanged; this analog reroute adds no via. Analog margin and noise still require separate qualification.

The USB pair now converges onto a closer main route. The compensation segment remains outside the main coupled section. The check uses every actual data-track and data-land polygon, including copper inside lands bypassed by the shortest contact-aware graph path.

That broader check also found a reference void under J4.2 caused by USB_FEED. The power route now leaves the local area on In1 and changes to In2 farther left. It uses three ordinary 0.5 / 0.3 mm through vias, with no new land-overlapping via or special via process. Its current/drop/thermal budget remains open.

The pre-repair regression is read from immutable commit `aaa3292547c9831fd3fddfc1c02d843156aec34a`. The script exports that actual PCB and the current PCB with the same native reader. Connectivity and reference coverage use the same normalized positive-area ground polygons; numerical normalization and the 1 nm join allowance are recorded explicitly. A connected overall GND network alone does not prove local reference coverage.

## Model scope

J4, J5 and C32 are exported individually from this candidate using KiCad's native STEP exporter. Their actual planar seating faces are compared with this PCB's inscribed copper polygons. The checks do not reuse a Raytac assembly acceptance result.

The generated STEP files are local cache artifacts under `.assembly-work/e73-usb-local-models/`; the report records their hashes, source standard-model hashes, bounds and land matches. Reproduce them with the matching KiCad 10 model library. These nominal models do not qualify supplier dimensions, physical coplanarity, solder joints, maximum installed envelopes, or case/plug withdrawal. The remaining 72 fitted parts and complete assembly have not received this model-closure check.

## Reproduce

After building and checking the candidate with KiCad Python, use the pinned CAD runtime:

```sh
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/study_e73_usb_return.py
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/check_e73_usb_local_models.py
```

Both commands accept `--kicad-python /path/to/kicad/python`. Use a Git checkout containing the baseline commit for the regression; a source ZIP without Git history cannot reproduce that case. Rebuilding the candidate invalidates the derived reports, so run the native checker and these studies again afterward.

Remaining work includes complete component models, case/fastener/plug tolerances and service motion, the nine-wire harness and guides, the PH battery connector obstruction, left power/package/thermal closure, candidate-bound firmware/calibration and CAM, supplier battery acceptance, and physical USB/BLE/ADC/RF/charging tests. None is waived by this checkpoint.
