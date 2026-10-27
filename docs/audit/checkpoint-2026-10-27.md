English | [Chinese](checkpoint-2026-10-27.zh-CN.md)

# Historical checkpoint — 2026-10-27

This checkpoint established the single-nRF52840 direction, retaining FELK60 datums, EC60 sensing geometry and mounting holes. Rear USB uses a daughterboard connected to J1.

`hardware/ec60-nrf52840/` saved schematic, netlist, intermediate routing, generators/checkers, scanner reference and mechanical evidence.

At that checkpoint: 176 symbols and the single-MCU pin contract passed; PCB/netlist parity, 74 retained sensing-related footprints, outline, mounting holes and four-layer structure passed; ERC had 0 errors and 184 warnings; PCB DRC still had **12 errors and 35 opens**. Three STM32 reference host cases passed ASan/UBSan, which was not nRF target or hardware validation.

SI/RF work remained deferred until PCB completion. Routing, component/power layout review, daughterboard/battery assembly, target firmware and physical calibration still blocked production. Local EC60 editor settings, history and `.kicad_prl` were excluded from the checkpoint.
