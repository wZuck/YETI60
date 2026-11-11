English | [Chinese](START-HERE.zh-CN.md)

# YETI60: start here

[Raytac USB repair candidate](variants/raytac/hardware/usb-short-route/README.md): revised native board and acceptance evidence; not yet an ordering release.

The active first-prototype track is **Raytac MDBT50Q-1MV2**. Open the [Raytac ordering and build handbook](variants/raytac/BUILD.md) for PCB files, order settings, inventory-adjusted materials, soldering, firmware and acceptance. E73 remains a separate alternative; do not use its mainboard files or firmware for this build.

**Raytac prototype ordering is on hold:** [new USB and battery findings](variants/raytac/docs/engineering/prototype-qualification.md) require repair/qualification beyond passing DRC. Start with the [open-bench procedure, including battery tests](variants/raytac/OPEN-BENCH.md); an enclosure is optional for those tests. The current `dfm-review` archive is not an ordering release.

[Selected mechanism, exact purchases and plate](variants/raytac/docs/build/key-mechanism.md): NiZ housings/sliders, separate steel-plate-mounted stabilizers, centered 6U caps and a new 1.6 mm plate.

**E73 alternative:** use the [E73 review and build entry](BUILD.md) for complete checks, matching firmware and materials. Confirmed USB protection-branch, plate and battery-plug service defects keep it on design hold; retain the existing C5 daughterboard.
