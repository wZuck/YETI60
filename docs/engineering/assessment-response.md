English | [Chinese](assessment-response.zh-CN.md)

# Response to the P2 feasibility assessment

The [2026-10-28 assessment](../audit/2026-10-28-feasibility-assessment.md) is retained as a dated review. This document records subsequent decisions and acceptance work. The later user requirement **JLC ordinary manufacturing only** overrides its proposed HDI procurement route. C5 JSH, one nRF52840 and the custom 1600 mAh single cell remain the chosen architecture. RF/SI is deferred.

| Assessment finding | Response or adjustment | Acceptance evidence still required |
|---|---|---|
| Single-MCU architecture | Retain; USB/BLE and EC scan share the nRF52840 | Target enumeration, pairing, physical calibration and recovery tests |
| A1: narrow charge-current margin | Keep R40=2.21k/1%; distinguish the 450 mA programming ceiling from a new >=500 mA continuous pack charge-rating requirement | Supplier correction of contradictory current rows; signed rating and accepted temperature window |
| A1: narrow termination-current margin | R56 changed from 1.82k to 1.69k/1%; maximum falls from 31.51 to 29.26 mA, margin to provisional 32 mA increases from 0.49 to 2.74 mA | Full CC/CV cycle and timer tests; lower termination can extend CV time |
| A1: charger voltage and thermal protection | Pack specification now requires acceptance of the full 4.16–4.23 V charger range, independent thermal interruption and separate NTC feedback | Corrected cell limits, pack drawing and protection/charging measurements; an NTC lead alone does not close this |
| A2: special fabrication dependency | Replace the HDI route with ordinary through-via routing and an ordinary JLC four-layer stack; no blind/buried/laser or filled-and-capped process may be required | Current ordinary-process CAD guard, native DRC/connectivity and JLC file review; no old HDI archive may be ordered |
| A3: EC mechanism not frozen | Reject the assumption that an original HHKB donor supplies removable housings; require independently mountable matched parts and local normal/wide/6U samples | Actual supplier parts, full travel/return, dome preload, stabilizer/cap fit and thread life |
| A4: incomplete passive/F1/D2 selection | README lists every fitted reference, value, package and selection status; preserve open selection status | Exact MPNs, regulator capacitor effective capacitance, fuse derating and LED current/Vf; nominal capacitance is not sufficient |
| B: cable assembly unqualified | Add full mating envelopes, seven continuous swept wires, static bend-radius checks and removable routing guides; integrate into the audit and render provenance | Actual wire OD/length/exit height, springback, crimps, insertion/removal and insulation wear |
| B: narrow mounting/pack tolerances | Preserve mount centers; track actual ordinary-board thickness, washer/head dimensions and resin tolerances explicitly | Incoming dimensional inspection and local mechanical samples; no silent waiver of negative clearance |
| C: power/runtime assumptions | Retain idle scan/AFE gating/REG1 LDO; keep 90.77 h as a conservative continuous-AFE planning calculation, without invented savings | Battery-side current log, idle duty cycle, first-key latency, full-capacity/runtime tests |
| Charging/user behavior | Retain powered USB500 only after host configuration, board-off USB100 behavior and switch-off leakage documentation | Both full-charge cases and charging-only-adapter behavior on hardware |

## Engineering prototype gates

| Gate | Parts and setup | Recorded pass conditions |
|---|---|---|
| S0 power/firmware fixture | One ordinary-process mainboard; current-limited USB source and battery simulator before a qualified pack | Correct rails/polarity, no shorts, SWD programming, USB states, U8 gating, regulator transients and charge control; oscilloscope/current/temperature records |
| S1 local key mechanism | One sample containing a normal key, wide opening, 6U-spacebar mechanism and representative standoffs; actual matched housings/domes/springs/caps | Full travel, return, no interference, accepted preload, thread engagement and repeated assembly; physical EC press/release distributions |
| S2 complete engineering units | Three complete keyboards only after S0/S1 and supplier pack acceptance | Every populated key calibrated; no false presses from unused positions; USB/BLE recovery, controlled harness assembly, charge-to-termination and thermal/runtime tests |
| S3 pilot | 10–30 units only after recorded S2 pass and exact BOM/DFM acceptance | Yield, repeatability, mechanical life and supplier consistency; no automatic production release |

Open supplier and physical gates are intentional limits, not completed tests. The [current audit outcome](../audit/outcome.json) states which software/CAD checks actually passed. The [fabrication handoff](fabrication-review.md), [battery specification](battery-pack-specification.md) and [materials list](materials.md) make the remaining requests reviewable without contacting vendors or placing orders.
