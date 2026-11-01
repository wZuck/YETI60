English | [Chinese](raytac-review.zh-CN.md)

# Raytac review conclusions

**All 52 implemented software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.

| Area | Result |
|---|---|
| PCB | 0 errors / 0 opens; 267 signal pairs |
| DRC | 102 disclosed noncomponent courtyard warnings |
| ERC | 0 errors; 183 inherited off-grid warnings |
| JLC | 816 ordinary through vias; >=0.50/0.30 mm land/drill |
| USB / BLE | Normal/calibrator ARM builds and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested |
| RF | All four layers clear in vendor minimum antenna projection; physical RF open |
| BOM | 75 parts; 10 planned from stock, 65 net purchases |

## Repairs and image inspection

- USB mainboard D1 and long branches removed after actual C5 protected-channel/ground verification; C5 D1/U1/F1 retained
- Shared analog/discharge net labels unified without changing exported pin connectivity
- 75-part purchase, stock allocation, placement and illustrated guide contracts reconciled
- Complete explosion includes 75 electronic bodies, battery, seven wires, 60 domes/springs and hardware; tray camera/desk bounds checked
- Deskeys T1/42g kit and NicePBT BoW centered 6U caps selected; adapted plate preserves all 60 centers, 29 mounts and outer profile; actual mechanism Z/travel awaits a first article

## Supplier and physical work still open

- Final capacitor effective capacitance, fuse thermal derating, LED and exact-part qualification.
- Supplier-signed complete pack envelope, charge limits and independent thermal interruption.
- Actual housings/domes/springs/stabilizers, resin tolerances and harness/mechanical samples.
- Physical USB enumeration/eye, concurrent charge/input, BLE, per-key calibration, thermal/runtime and enclosed interference tests.
- Upstream C5 default DRC review items remain; protected-channel verification is not C5 manufacturing or ESD certification.

[Build entry](../../BUILD.md) · [complete explosion and part index](../engineering/exploded.md) · [first-article acceptance](../testing/README.md) · [machine evidence/hashes](raytac-review.json)
