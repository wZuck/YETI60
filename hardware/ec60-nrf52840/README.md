# YETI60 single-nRF52840 PCB

English | [简体中文](README.zh-CN.md)

YETI60 uses one Raytac MDBT50Q-1MV2 for EC scanning and native USB/BLE support. The EC60 electrodes, board outline and mounting holes are retained. The rear Type-C daughterboard connects to J1; J2 requires a protected 1S 4.2 V pack and 10k NTC.

The current review changes R30/R31 to **0 Ω** because the nRF52840 PHY includes series termination. Local power layout, assembly fit and new assembled renders remain under review. The public project name is YETI60; existing `EC60-nRF52840.*` filenames and `YAECKB` library identifiers are compatibility identifiers and are not additional MCUs or public branding.

See the [review checkpoint](../../docs/audit/yeti60-review-checkpoint.md), [firmware simulation](../../firmware/yeti60/README.md), [electrical evidence](../../docs/audit/yeti60-electrical.json), and [CAD audit data](audit-current.json). The current CAD result must be read from that hashed report rather than inferred from an older render.

Power uses BQ24074 and TPS63031. Firmware must keep GPIOs high-Z while the switched analog rail is off, wait for analog settling, and serialize ADC use. USB current-limit controls must follow enumeration and suspend state. The internal low-frequency RC clock is used. J3 is a custom six-contact SWD layout.

U1.39/U1.51 require filled, planarized and copper-capped vias-in-pad. No physical assembly, final battery, switch/keycap tolerance stack, regulator stability, USB eye diagram, SI or RF approval is claimed. Full English/Chinese documentation synchronization is part of the ongoing review.
