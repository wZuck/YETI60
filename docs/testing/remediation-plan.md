English | [Chinese](remediation-plan.zh-CN.md)

# Remediation plan and acceptance gates

The goal is a design ready for an engineering first article, followed by measured hardware acceptance. Successful script execution is not final acceptance. Keep both module options in one branch, one nRF52840 per keyboard, C5 JSH, ordinary JLC four-layer through vias, the 60 sensing electrodes and 29 mounting holes. Preserve the original FELK60 exterior; an explicitly documented PCB wing and internal resin relief are permitted design candidates, not approved production geometry.

| ID / priority | Finding and repair | Required closing evidence | Current state |
|---|---|---|---|
| CAL-01 / critical | Optimistic min-released/max-pressed calibration can accept overlapping populations. Replace with labeled per-key captures, worst observed bounds and noise guard | Insufficient/overlap/noise/saturation negative tests; both normal/calibrator ARM builds; guide and command table match | Corrected and rebuilt for all four ARM targets; E73 47-stage and Raytac 44-stage full audits pass; physical calibration remains open |
| RF-01 / high | Raytac has a ~0.05mm GND fringe in its minimum antenna projection; E73 antenna end is inside substantial host copper | Native all-layer pad/track/zone intersections equal zero; actual rule-area checks reject injected copper | Existing boards fail/open; outboard placement candidate prepared |
| RF-02 / high | Metal plate projects near both antennas | Zero antenna/plate projected overlap plus declared lateral allowance, followed by assembled RF tests | Candidate BRep screen passes; not yet applied to PCB |
| MECH-01 / high | Outboard placement needs supported lands, board-edge clearance and internal relief | Native land-to-board checks; strict DRC; case/body/board/harness clearances over tolerances; unchanged exterior and original electrode/mount geometry | Candidate wing extends right edge from X356.812704 to X361.2 over Y114.5–132.0mm |
| SI-01 / high | USB checks previously summed branch tracks; this is not actual pair skew, impedance or return-path acceptance | Extract ordered J1-to-module paths through series links; count stubs/vias; route adjacent pair with reference plane; ordinary-stack model and complete cable/C5 limits; hardware eye/enumeration | Re-review and routing work required; no fabricated pass from aggregate length |
| POWER-01 / high | Long/indirect module decoupling and conservative primitive path sums need review | Measure pad/contact-aware paths and ground returns; place module bypass capacitors locally; verify widths/DC drop; transient and temperature bench results | Native power review required; existing calculations are not a stability proof |
| AFE-01 / high | 101x gain makes baseband disturbance significant; no extracted EC capacitance or sampled ADC network exists | Guarded distributions in all power/radio modes; rail/load/timing sweeps and physical waveforms | TI amplifier sensitivity tests exist; physical noise margin open |
| BAT-01 / high | Cell sheet current rows conflict; complete protected 1600mAh pack is not supplier approved | Corrected limits, signed complete envelope, independent 15–43°C interruption, NTC and charge/termination records | Supplier evidence unavailable; cannot be closed in CAD or software |
| FW-01 / high | Peripheral/radio/host behavior has only build and mocked-core evidence | Four matched ARM artifacts and source provenance; per-device flash/readback, USB/BLE and transport-cycle logs | All four updated ARM targets rebuilt and checked; hardware absent |
| MECH-02 / high | Dome preload, resin shrinkage/inserts, complete plug/harness serviceability remain conditional | Actual matched donor parts, dry fit, dimensions, pullout and closure records | Requires physical first article |
| TEST-01 / medium | Acceptance summary hardcodes a hold and named old findings | Derive design gates from fresh evidence; preserve independent physical gates; negative tests for false/stale closure | Repair required; never change a hold to a pass just to complete the plan |
| DFM-01 / medium | JLC ordinary-process output needs revalidation after every board change | No blind/buried/via-in-pad requirements, strict native DRC/parity, correct Gerbers/drills/BOM/placements and variant identity | Rerun after final routing; fabrication archives remain review packages |

## Antenna candidate already checked

The [controlled candidate dimensions](../../mechanical/rf-remediation.json) move E73 to origin (346,117), 0°, and Raytac to (356.25,125.25), 90°, on the component side. Antenna ends extend beyond the original plate edge. A common internal bottom-shell relief is X355.5–364.8, Y−133–−114, Z−5.7–0.2mm, radius 0.8mm. This does not change the exterior.

The [executed candidate study](../audit/rf-remediation-candidate.json) reports zero module/case collisions, E73 4.187mm and Raytac 3.387mm antenna-to-plate lateral separation, 0.5mm wing-to-case gap and at least 1.56mm sampled floor web after the imposed 0.15mm case tolerance. The E73 worst-depth module retains 0.296mm after that case tolerance. The floor check samples 595 locations and is not a full structural wall or resin strength analysis. The E73 3mm antenna band is still provisional because its vendor supplies no numeric host keepout. **These results establish candidate geometric feasibility, not routed PCB or RF acceptance.**

## Execution order

1. Correct calibration and its acceptance tests; rebuild all four firmware targets; regenerate the two bilingual guides. Commit and push a complete checkpoint with current evidence.
2. Prove supported lands and edge clearances, apply the RF wing/relief to both alternatives, move modules and local bypass components, and reroute connected nets with unchanged ordinary-process rules. Keep raw original geometry and a deterministic change specification for regression comparison.
3. Repair USB path geometry and review power/ground return paths. Reject any local repair that creates new DRC errors, disconnected signals, sensing changes or mechanical collisions.
4. Regenerate all affected manufacturing data, STEP geometry, cable drawings, step illustrations and render provenance. Rerun both full audits and all interference/acceptance negative tests. Publish the next checkpoint.
5. Manufacture only after design gates and ordering review pass. Obtain accepted pack and donor mechanism, then execute the [first-article procedure](README.md) and [interference matrix](interference.md#physical-interference-matrix). Keep failed measurements open and repeat affected tests after repairs. Hardware absence and supplier documents are evidence gaps, never automatic passes.

Reproduction: `python3 scripts/test_yeti60_calibration.py`; run `scripts/study_yeti60_rf_remediation.py` with the CAD environment. Current design and physical status are controlled by [acceptance evidence](../audit/acceptance.json), not by this proposed plan.
