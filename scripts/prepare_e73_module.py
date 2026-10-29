#!/usr/bin/env python3
"""Import the vendor reference footprint and freeze the E73 pin proposal.

Run with KiCad Python. This prepares source data; it does not route a PCB.
"""
import hashlib
import json
from pathlib import Path
import sys
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
PIN_NAMES = {
    1:'P1.11',2:'P1.10',3:'P0.03',4:'P0.28',5:'GND',6:'P1.13',7:'P0.02',8:'P0.29',9:'P0.31',10:'P0.30',
    11:'P0.00',12:'P0.26',13:'P0.01',14:'P0.06',15:'P0.05',16:'P0.08',17:'P1.09',18:'P0.04',19:'VDD',
    20:'P0.12',21:'GND',22:'P0.07',23:'VDDH',24:'GND',25:'DCCH',26:'P0.18',27:'VBUS',28:'P0.15',
    29:'D-',30:'P0.17',31:'D+',32:'P0.20',33:'P0.13',34:'P0.22',35:'P0.24',36:'P1.00',37:'SWDIO',
    38:'P1.02',39:'SWDCLK',40:'P1.04',41:'P0.09',42:'P1.06',43:'P0.10',
}
OUTER = {1,2,3,4,5,6,7,8,9,10,11,13,15,17,19,21,23,25,26,27,29,31,33,35,37,39,41,43}
ROLES = {
    33:'ROW_DRV0',1:'ROW_DRV1',35:'ROW_DRV2',17:'ROW_DRV3',11:'ROW_DRV4',
    32:'AMUX_SEL_0',34:'AMUX_SEL_1',28:'AMUX_SEL_2',13:'APLEX_EN_PIN_0',41:'APLEX_EN_PIN_1',12:'APLEX_OUT_PIN_0',
    4:'ADC',15:'BAT_ADC',8:'BAT_MEAS_EN',9:'AFE_EN',3:'CHG_EN1',7:'CHG_EN2',6:'CHG_CE_N',
    2:'CHG_N',43:'PGOOD_N',10:'STATUS_LED',26:'RESET_N',37:'SWDIO',39:'SWDCLK',
    19:'+3.3V',23:'+3.3V',27:'USB_5V',29:'USB_DM',31:'USB_DP',5:'GND',21:'GND',24:'GND',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = Path(sys.argv[1])
    plugin = pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.ALTIUM_DESIGNER)
    names = plugin.footprintPyEnumerate(str(source), True)
    assert list(names) == ['E73(2G4M08S1C)']
    footprint = plugin.FootprintLoad(str(source), names[0])
    footprint.SetFPID(pcb.LIB_ID('Ebyte', 'E73-2G4M08S1C'))
    footprint.SetValue('E73-2G4M08S1C')
    library = ROOT/'hardware/module-options/Ebyte.pretty'
    library.mkdir(parents=True, exist_ok=True)
    pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(library), footprint)
    pads = {int(p.GetNumber()):p for p in footprint.Pads()}
    assert set(pads) == set(range(1,44))
    pins = []
    for number in range(1,44):
        pad = pads[number]
        pins.append({'number':number,'soc_function':PIN_NAMES[number],
                     'location':'outer' if number in OUTER else 'bottom',
                     'proposed_net':ROLES.get(number),
                     'vendor_land_center_mm':[pcb.ToMM(pad.GetPosition().x),pcb.ToMM(pad.GetPosition().y)],
                     'vendor_land_size_mm':[pcb.ToMM(pad.GetSize().x),pcb.ToMM(pad.GetSize().y)],
                     'vendor_land_angle_deg':pad.GetOrientationDegrees()})
    result = {
        'module':'Ebyte E73-2G4M08S1C','chip':'nRF52840','controller_count_per_board':1,
        'status':'pin-assignment-proposal-not-routed-not-built', 'production_approved':False,
        'body_nominal_mm':[18,13,3], 'body_dimension_tolerance_mm':.1,
        'vendor_origin_basis':'Unmodified Altium library origin; body X=0..18 and Y=-13..0, component view',
        'castellated_pitch_mm':1.27,'pins':pins,
        'power':{'VDD_pin':19,'VDDH_pin':23,'rail_V':3.3,'USB_VBUS_pin':27,
                 'DCCH_pin_25':'unconnected; REG0 DC/DC disabled',
                 'REG1_mode':'must confirm module inductor/provisioning before firmware release'},
        'firmware_requirements':['Use internal LF RC; pins P0.00/P0.01 are allocated to GPIO',
                                 'Configure both NFC pins as GPIO; verify linked UICR/NFCPINS setting',
                                 'Scan ADC is P0.28/AIN4; battery ADC remains P0.05/AIN3',
                                 'Preserve the corrected 60-key HHKB transform and active masks'],
        'sources':{'product':'https://www.ebyte.com/product/444.html',
                   'manual':'https://www.ebyte.com/downpdf/444.html',
                   'footprint_archive':'https://www.ebyte.com/pdf-down/2158.html'},
        'vendor_pcblib_sha256':sha(source),
        'footprint_output':'hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod',
        'footprint_sha256':sha(library/'E73-2G4M08S1C.kicad_mod'),
        'generator_sha256':sha(Path(__file__)),
        'remaining':['Native E73 schematic, board placement/routing and ordinary-process DRC',
                     'Module supply/DC-DC review; variant firmware builds, host and fault tests',
                     'Worst-case module height/case/harness checks and variant render/guide regeneration',
                     'Complete fabrication, BOM, provenance and cross-domain checks',
                     'Supplier and physical acceptance; RF/SI deferred by user'],
    }
    (ROOT/'hardware/module-options/e73.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Imported 43 vendor lands; 32 proposed connections, including five bottom lands; PCB/firmware pending')


if __name__=='__main__':
    main()
