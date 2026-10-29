#!/usr/bin/env python3
"""Run the nRF pin-bound control core on host with ASan/UBSan and GPIO invariants."""
import hashlib,json,subprocess,tempfile,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'scripts/generate_yeti60_pin_contract.py'),'--check'],check=True)
with tempfile.TemporaryDirectory(prefix='yeti60-sim-') as folder:
    binary=Path(folder)/'sim'
    subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-g','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-I',str(ROOT/'firmware/yeti60'),str(ROOT/'firmware/yeti60/core.c'),str(ROOT/'tests/yeti60/sim.c'),'-o',str(binary)],check=True)
    trace=ROOT/'docs/audit/yeti60-firmware-trace.csv'
    run=subprocess.run([str(binary)],capture_output=True,text=True,env={**os.environ,'YETI_SIM_TRACE':str(trace)})
files=[*sorted((ROOT/'firmware/yeti60').glob('*.[ch]')),ROOT/'tests/yeti60/sim.c',ROOT/'hardware/ec60-nrf52840/netlist.xml',ROOT/'hardware/ec60-nrf52840/pinmap.json',Path(__file__).resolve(),ROOT/'scripts/generate_yeti60_pin_contract.py']
report={'status':'passed' if run.returncode==0 else 'failed','exit_code':run.returncode,'output':run.stdout.splitlines(),'errors':run.stderr,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'trace_file':str(trace.relative_to(ROOT)),'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),'execution':'native host C core with address/undefined-behaviour sanitizers','nrf_gpio_contract':'generated from current module pin map and schematic XML; ADC AIN4 and battery AIN3','timing_model':'explicit illustrative waits; not analog settling validation','not_verified':['nRF52840 binary, peripheral register/HAL implementation or instruction-level emulation','actual USB enumeration and BLE pairing/radio/HID stack','analog waveforms, calibrated thresholds, RF coexistence and physical wake-up']}
(ROOT/'docs/audit/yeti60-firmware-simulation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(run.returncode)
