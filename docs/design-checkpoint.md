English | [Chinese](design-checkpoint.zh-CN.md)

# Design checkpoint

This is an intermediate engineering commit, not a manufacturing release. There is no physical board yet; the authorized next milestone is completed design and buildable firmware.

- Normal and USB-CDC calibrator ARM binaries build from the fully frozen ZMK/Zephyr manifest. Output hashes, complete Intel HEX checks and settings partition protection are recorded in the target audit reports. USB/BLE HID, bonding and profile switching are supplied by ZMK. Physical enumeration, pairing and EC calibration remain untested.
- Local power routes are shortened without moving electrodes, components, outline or mounting centers. Seven 0.40/0.20 mm back-side microvias connect B.Cu to In2.Cu. Strict DRC has zero errors and opens. The upper sensing dielectric remains 0.20 mm; the lower laser dielectric is 0.15 mm and the core is 1.115 mm, retaining the 1.59 mm finished thickness. This requires a qualified HDI process, filled and planarized microvias, ENIG, and the separately specified capped U1 through vias.
- Generated resin-case solids add bonded insert seats and underside switch access. Every exterior bounding coordinate remains unchanged. The 4.6 mm stack uses a specified M2/M1.6 adapter standoff and insulation; actual Topre parts require first-article acceptance.
- A custom 200 mAh pack specification reserves 50×20×2.9 mm including protection, NTC, wrapping and growth. It requires independent charging temperature protection and a supplier-signed drawing. It is not an approved retail battery.
- The rear daughterboard is pinned to Unified Daughterboard C5 JSH. Native PCB checks verify the signal order, input fuse and two separate 5.1 kOhm CC terminations.

Remaining work: final cable/plug and fastener CAD collision/tolerance checks, manufacturing drawings, full evidence integration, synchronized documentation and regenerated PCB/assembly images. Existing render manifests and the old full integration/outcome reports do not certify this checkpoint. SI/RF analysis remains deferred by the user.
