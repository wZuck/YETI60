"""Independent verifier for the source/effective-config calibration identifier."""
import hashlib

INPUTS = (
    'firmware/yeti60/board_pins.h', 'firmware/yeti60/core.c',
    'firmware/yeti60/core.h', 'firmware/yeti60/calibration.c',
    'firmware/yeti60/calibration.h', 'firmware/target/src/scanner.c',
    'firmware/target/src/gpio_modes.h',
    'firmware/target/src/scanner_control.c', 'firmware/target/src/scanner_control.h',
    'firmware/target/boards/yeti/yeti60/yeti60.dts',
    'firmware/target/boards/yeti/yeti60/yeti60_defconfig',
    'firmware/target/config/yeti60.conf', 'firmware/target/config/west.yml',
    'firmware/target/Kconfig', 'firmware/target/CMakeLists.txt',
    'firmware/target/calibration-contract.cmake',
    'mechanical/assembly-spec.json', 'mechanical/felk60_plate_hhkb.plate-mount.dxf',
    'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb',
)
OPTIONS = ('CONFIG_YETI60_ACTIVE_SCAN_MS', 'CONFIG_YETI60_IDLE_SCAN_MS',
           'CONFIG_YETI60_IDLE_AFTER_MS', 'CONFIG_YETI60_AFE_IDLE_GATING')


def configuration(text):
    values = dict(line.split('=', 1) for line in text.splitlines()
                  if line.startswith('CONFIG_') and '=' in line)
    values.setdefault('CONFIG_YETI60_AFE_IDLE_GATING', 'n')
    return {option: values[option] for option in OPTIONS}


def version(root, options, pcb=None):
    fields = ['yeti60-calibration-v4']
    for rel in INPUTS:
        path=pcb if pcb is not None and rel==INPUTS[-1] else root/rel
        fields.append(rel+'='+hashlib.sha256(path.read_bytes()).hexdigest())
    fields.extend(option+'='+options[option] for option in OPTIONS)
    return '0x'+hashlib.sha256('\n'.join(fields).encode()).hexdigest()[:8]
