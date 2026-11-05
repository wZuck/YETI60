#!/usr/bin/env python3
"""Compile actual target GPIO/init bodies and test electrical pin invariants."""
import hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from yeti60_host_atomics import prepare
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=Path.home()/'.cache/yeti60-zmk-workspace'
ZEPHYR_REV='10ba6d0cb38bc3d258775d27982f707599320085'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(source,name):
    start=source.index('static '+('void' if name=='gpio' else 'int')+' '+name+'(')
    brace=source.index('{',start);depth=1;end=brace+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]+'\n'
def main():
    assert subprocess.check_output(['git','-C',str(WORKSPACE/'zephyr'),'rev-parse','HEAD'],text=True).strip()==ZEPHYR_REV
    upstream={rel:subprocess.check_output(['git','-C',str(WORKSPACE/'zephyr'),'show',ZEPHYR_REV+':'+rel],text=True) for rel in ['include/zephyr/drivers/gpio.h','include/zephyr/dt-bindings/gpio/gpio.h','drivers/gpio/gpio_nrfx.c']}
    names=['GPIO_INPUT','GPIO_OUTPUT','GPIO_DISCONNECTED','GPIO_OUTPUT_INIT_LOW','GPIO_OUTPUT_INIT_HIGH','GPIO_OUTPUT_LOW','GPIO_OUTPUT_HIGH','GPIO_PULL_UP','GPIO_PULL_DOWN']
    constants=''
    for name in names:
        line=next(line for source in upstream.values() for line in source.splitlines() if re.match(r'^#define '+name+r'\s',line))
        constants+=line.replace('GPIO_','PINNED_GPIO_')+'\n'
    constants+='\n'.join('_Static_assert('+n+' == PINNED_'+n+', "Host GPIO flags differ from pinned Zephyr");' for n in names)+'\n'
    scanner=ROOT/'firmware/target/src/scanner.c';source=scanner.read_text();header=ROOT/'firmware/target/src/gpio_modes.h';original=header.read_text()
    cases=['normal','device-missing','USB-init-failure','GPIO-init-failure','ADC-read-failure'];results=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='yeti-gpio-modes-') as folder:
        temp=Path(folder);atomic_hashes=prepare(WORKSPACE,temp);(temp/'zephyr_gpio_constants.h').write_text(constants)
        (temp/'scanner_gpio.inc').write_text(function(source,'gpio'));init=function(source,'init');(temp/'scanner_init.inc').write_text(init)
        def build(name,text,initialization=init):
            (temp/'gpio_modes.h').write_text(text);(temp/'scanner_init.inc').write_text(initialization)
            binary=temp/name
            command=[shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(temp),'-I',str(ROOT/'firmware/target/src'),'-I',str(ROOT/'tests/yeti60/stubs'),'-I',str(ROOT/'firmware/yeti60'),str(ROOT/'firmware/yeti60/core.c'),str(ROOT/'firmware/target/src/scanner_control.c'),str(ROOT/'tests/yeti60/gpio_modes.c'),'-o',str(binary)]
            subprocess.run(command,check=True);return binary
        good=build('good',original)
        for name in cases:
            run=subprocess.run([str(good),name],text=True,capture_output=True,check=True);results.append(dict(case=name,output=run.stdout.strip()))
        changes=[('digital-input-buffer',original.replace('return GPIO_DISCONNECTED;','return GPIO_INPUT;'),init,'normal'),
                 ('pull-up-on-float',original.replace('return GPIO_DISCONNECTED;','return GPIO_DISCONNECTED | GPIO_PULL_UP;'),init,'normal'),
                 ('actively-drive-release',original.replace('case Y_OD_RELEASE:\n    return GPIO_DISCONNECTED;','case Y_OD_RELEASE:\n    return GPIO_OUTPUT_HIGH;'),init,'normal'),
                 ('skip-startup-shutdown',original,init.replace('(void)yeti_power(&core, false);','(void)0;'),'GPIO-init-failure')]
        for name,text,body,case in changes:
            assert text!=original or body!=init,name
            binary=build(name,text,body);run=subprocess.run([str(binary),case],text=True,capture_output=True)
            assert run.returncode!=0 and 'Assertion' in run.stderr,(name,run.stderr)
            negative.append(dict(case=name,exit_code=run.returncode,output=run.stderr.strip()[-600:]))
    files=[Path(__file__),scanner,header,ROOT/'scripts/yeti60_host_atomics.py',ROOT/'firmware/target/src/scanner_control.c',ROOT/'firmware/target/src/scanner_control.h',ROOT/'tests/yeti60/gpio_modes.c',ROOT/'tests/yeti60/stubs/zephyr/drivers/gpio.h',ROOT/'firmware/yeti60/core.c',ROOT/'firmware/yeti60/core.h',ROOT/'firmware/yeti60/board_pins.h']
    report=dict(status='passed',physical_verification=False,execution='Verbatim production target GPIO/init functions, actual mode helper and portable core under ASan/UBSan; host pin/ADC/device models, not a hardware or nrfx-driver execution',nominal_scan_samples=150,positive_cases=results,rejected_mutants=negative,
                upstream_revision=ZEPHYR_REV,GPIO_constants_checked_against_pinned_headers=True,upstream_sha256={**atomic_hashes,**{rel:hashlib.sha256(text.encode()).hexdigest() for rel,text in upstream.items()}},
                not_verified=['Physical pin leakage, analog noise, injected current or actual rail discharge','Physical GPIO/load-switch failure or stuck pins','Real RTOS/SAADC/USB/BLE and electrical initialization transients'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files})
    (ROOT/'docs/audit/gpio-mode-policy.json').write_text(json.dumps(report,indent=2)+'\n')
    for result in results:print(result['output'])
    print('Electrical GPIO/initialization mutants rejected:',len(negative))
if __name__=='__main__':main()
