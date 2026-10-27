from pathlib import Path
root=Path('.')
p=root/'README.md';old=p.read_text().replace('# YAECKB','# YETI60',1);old='[English](README.md) | 简体中文\n\n'+old;old=old.replace('![当前 PCB 器件面渲染]','![上一阶段 PCB 器件面渲染]').replace('[查看 360° 动画]','[查看上一阶段 360° 动画]');old+='\n## 当前全面复查\n\n项目公开名称改为 YETI60，文档正在统一为英文默认、中文并行。见[阶段记录](docs/audit/yeti60-review-checkpoint.zh-CN.md)。当前 nRF52840 控制核心已完成主机模拟；装配匹配、供电局部布线复查及新装配渲染仍在进行。旧渲染对应上一阶段 PCB，不代表当前装配结果。\n';(root/'README.zh-CN.md').write_text(old)
p.write_text('''# YETI60

English | [简体中文](README.zh-CN.md)

An EC60-derived electrocapacitive keyboard for the FELK60 case, redesigned around a **single nRF52840** (Raytac MDBT50Q-1MV2). The PCB retains the EC60 electrode geometry, outline and mounting holes. A rear USB daughterboard connects to J1; the original STM32 and onboard USB connector are removed.

## Review in progress

The current review covers functional circuit correctness, nRF52840 control-core simulation, case/PCB/plate fit, available battery space and assembled renders. See the [checkpoint](docs/audit/yeti60-review-checkpoint.md). This is not a production approval.

- USB D+/D− links are now **0 Ω**, replacing the inherited STM32 27 Ω values: the nRF52840 PHY already contains series termination.
- The new [portable control core](firmware/yeti60/README.md) runs against the actual schematic pin contract under host ASan/UBSan. GPIO, ADC and HID transports are mocked; no target binary or radio-stack validation is claimed.
- Local power-route review, assembly Z registration and assembled renders are still in progress. No battery has been selected; available space will be evaluated before specifying a pack.
- Project-owned documentation is being migrated to English by default with parallel Chinese versions. Upstream attribution and legacy technical library/file identifiers are retained.

## Design and evidence

- [Current single-controller design](hardware/ec60-nrf52840/README.md)
- [KiCad project](hardware/ec60-nrf52840/EC60-nRF52840.kicad_pro)
- [Electrical review data](docs/audit/yeti60-electrical.json)
- [Firmware simulation results](docs/audit/yeti60-firmware-simulation.json)
- [Previous PCB audit](docs/audit/pcb-review-2026-10-27.zh-CN.md)
- [Previous PCB-only renders](renders/ec60-nrf52840/README.zh-CN.md) — generated before the current review; assembled YETI60 renders are pending.

The case material remains provisionally resin. Resin inserts, real switch/keycap tolerances, a protected battery with NTC, the rear Type-C daughterboard, hardware calibration and SI/RF validation are not approved by the current CAD or host tests.

Based on [Cipulot/EC60](https://github.com/Cipulot/EC60) and [fredlb/felk60](https://github.com/fredlb/felk60). Their names, licenses and original contributions remain attributed.
''')
(root/'firmware/yeti60/README.md').write_text('''# YETI60 nRF52840 control-core simulation

English | [简体中文](README.zh-CN.md)

`core.c` is a new portable control core bound to the current MDBT50Q-1MV2 pin assignment. `board_pins.h` is generated from the schematic XML and module pin contract. Scan ADC is P0.04/AIN2; battery ADC is P0.05/AIN3.

Run from the repository root:

```sh
python3 scripts/generate_yeti60_pin_contract.py --check
python3 scripts/simulate_yeti60_firmware.py
```

The host executable runs the actual core C source under AddressSanitizer and UndefinedBehaviorSanitizer. Coverage includes all 75 scan positions, mux bank/address and open-drain sequencing, one driven row at a time, explicit settling/discharge/acquisition waits, hysteresis and two-frame debounce, ADC failure with atomic frame abort, released keys on fault, AFE high-Z shutdown, USB100/USB500/suspend controls, held-key USB/BLE report handover, boot-protocol rollover, send retries, reentrancy exclusion and a 50 ms battery-divider settling delay. A deterministic 2,000-frame noise scenario checks logic behavior within the hysteresis band.

## Limits

This is native host simulation with mocked GPIO, ADC and HID transports, **not** an nRF52840 binary, peripheral-register/instruction emulator, USB enumeration test or BLE pairing/radio test. `usage[][]` is supplied by the caller; the test mapping is not a finished HHKB keymap. The application/HAL and actual USB/BLE stacks still need target integration.

The test timing and thresholds are illustrative configuration values, not physical calibration. The battery conversion assumes a 12-bit SAADC using a 0.6 V reference, gain 1/6 and the board's 1M:1M divider. Hardware must serialize access to the shared SAADC and configure that reference/gain. USB current limits must reflect host enumeration; the charger NTC protection remains a hardware function.

Results and source hashes: [yeti60-firmware-simulation.json](../../docs/audit/yeti60-firmware-simulation.json). The older GPL EC60 reference scanner is preserved separately in `firmware/ec60/`; its tests do not establish nRF support.
''')
(root/'firmware/yeti60/README.zh-CN.md').write_text('''# YETI60 nRF52840 控制核心模拟

[English](README.md) | 简体中文

`core.c` 是按当前 MDBT50Q-1MV2 引脚设计的新可移植控制核心。`board_pins.h` 从原理图 XML 和模块引脚契约生成；扫描使用 P0.04/AIN2，电池测量使用 P0.05/AIN3。

在项目根目录运行：

```sh
python3 scripts/generate_yeti60_pin_contract.py --check
python3 scripts/simulate_yeti60_firmware.py
```

测试将实际核心 C 源码编入主机程序，并启用 ASan/UBSan。覆盖全部 75 个扫描位置、多路选择器地址及分组、开漏充放电顺序、单行驱动、等待时序、滞回与两帧去抖、ADC 故障中止整帧及释放按键、模拟前端断电高阻、USB100/USB500/挂起控制、按住按键时 USB/BLE 报告切换、启动协议溢出、发送失败重试、重入排除和电池分压开启后 50 ms 等待。固定种子的 2000 帧噪声场景检查滞回带内的逻辑行为。

## 限制

这是模拟 GPIO、ADC、HID 传输接口的主机执行，**不是** nRF52840 目标固件、寄存器／指令模拟、USB 枚举或蓝牙配对／无线测试。`usage[][]` 由调用者传入，测试键码不是完整 HHKB 键位。应用层、硬件 HAL 和真正 USB/BLE 栈仍需接入。

阈值和等待时间均为示例配置，不能作为实物校准结果。电池换算假定 12 位 SAADC、0.6 V 参考、1/6 增益及 1M:1M 分压；硬件必须正确配置并串行使用共享 ADC。USB 电流限制须遵循枚举授权，NTC 保护由充电芯片硬件承担。

结果与源码哈希见 [模拟报告](../../docs/audit/yeti60-firmware-simulation.json)。原 GPL EC60 扫描参考保留在 `firmware/ec60/`，其测试不能证明 nRF 支持。
''')
(root/'hardware/ec60-nrf52840/README.md').write_text('''# YETI60 single-nRF52840 PCB

English | [简体中文](README.zh-CN.md)

YETI60 uses one Raytac MDBT50Q-1MV2 for EC scanning and native USB/BLE support. The EC60 electrodes, board outline and mounting holes are retained. The rear Type-C daughterboard connects to J1; J2 requires a protected 1S 4.2 V pack and 10k NTC.

The current review changes R30/R31 to **0 Ω** because the nRF52840 PHY includes series termination. Local power layout, assembly fit and new assembled renders remain under review. The public project name is YETI60; existing `EC60-nRF52840.*` filenames and `YAECKB` library identifiers are compatibility identifiers and are not additional MCUs or public branding.

See the [review checkpoint](../../docs/audit/yeti60-review-checkpoint.md), [firmware simulation](../../firmware/yeti60/README.md), [electrical evidence](../../docs/audit/yeti60-electrical.json), and [CAD audit data](audit-current.json). The current CAD result must be read from that hashed report rather than inferred from an older render.

Power uses BQ24074 and TPS63031. Firmware must keep GPIOs high-Z while the switched analog rail is off, wait for analog settling, and serialize ADC use. USB current-limit controls must follow enumeration and suspend state. The internal low-frequency RC clock is used. J3 is a custom six-contact SWD layout.

U1.39/U1.51 require filled, planarized and copper-capped vias-in-pad. No physical assembly, final battery, switch/keycap tolerance stack, regulator stability, USB eye diagram, SI or RF approval is claimed. Full English/Chinese documentation synchronization is part of the ongoing review.
''')
