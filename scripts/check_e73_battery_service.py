#!/usr/bin/env python3
"""Native E73 SH3 landing, bounded body/plug fit and old-PH regression.

CAD runtime, after native checks and the USB local fit study. This qualifies
neither flexible battery leads/tools nor the battery/charger safety system.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from cad_geometry import bounds, intersection_volume, load
from check_yeti60_assembly import box, distance, move
from check_e73_usb_local_models import landing
from check_e73_usb_local_fit import expand, sweep_bounds
from kicad_sexpr import child, children, dumps, loads

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-usb-repair'
WORK=ROOT/'.assembly-work/e73-battery-service'
CLI=os.environ.get('KICAD_CLI','/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
SPEC=ROOT/'hardware/e73-battery-service-spec.json'


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(mapping):
    for p,digest in mapping.items():assert sha(ROOT/p)==digest,('Stale battery study input',p)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-python',default='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    args=parser.parse_args()
    report_path=BASE/'audit/battery-service.json';report_path.unlink(missing_ok=True)
    WORK.mkdir(parents=True,exist_ok=True)
    spec=read(SPEC)
    native_path=BASE/'audit/native-check.json';native=read(native_path);hashes(native['source_sha256'])
    assert native['status']=='e73-usb-native-candidate-checks-passed'
    assert native['preserved_geometry']['battery_service']['new_ordinary_through_vias']==2
    fit_path=BASE/'audit/local-fit.json';usb_fit=read(fit_path);hashes(usb_fit['source_sha256']);hashes(usb_fit['outputs'])
    assembly_path=ROOT/'docs/audit/yeti60-assembly.json';assembly=read(assembly_path)
    hashes(assembly['source_sha256']);hashes(assembly['verification_recipe_sha256'])
    assert sha(ROOT/'docs/audit/yeti60-pcb-mechanical-metadata.json')==assembly['mechanical_metadata_sha256']
    assert not native['manufacturing_released'] and not usb_fit['complete_assembly_qualified']
    board_path=BASE/'EC60-nRF52840.kicad_pcb';tree=loads(board_path.read_text())
    footprint=next(f for f in children(tree,'footprint') if any(p[1:3]==['Reference','J2'] for p in children(f,'property')))
    assert footprint[1]==spec['footprint_id']
    assert [float(v) for v in child(footprint,'at')[1:3]]==spec['position_PCB_mm']
    model=children(footprint,'model');assert len(model)==1 and not child(model[0],'hide')
    model=model[0]
    assert child(model,'offset')==['offset',['xyz','0','0','0']]
    assert child(model,'scale')==['scale',['xyz','1','1','1']]
    assert child(model,'rotate')==['rotate',['xyz','0','0','0']]
    assert model[1].startswith('${KICAD10_3DMODEL_DIR}/Connector_JST.3dshapes/JST_SH_SM03B-SRSS-TB_')
    model_root=Path(os.environ.get('KICAD10_3DMODEL_DIR','/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'))
    model_source=model_root/model[1].split('}/',1)[1];assert model_source.is_file()
    model[1]=str(model_source)
    resolved=WORK/'resolved.kicad_pcb';resolved.write_text(dumps(tree)+'\n')
    step=WORK/'J2.step'
    result=subprocess.run([CLI,'pcb','export','step','--no-board-body','--component-filter','J2','--user-origin','0x0mm','-f','-o',str(step),str(resolved)],text=True,capture_output=True)
    assert result.returncode==0,(result.stdout+result.stderr)[-3000:]
    header,data=step.read_text().split('DATA;',1)
    header=re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?','2000-01-01T00:00:00',header)
    step.write_text('\n'.join(line.rstrip() for line in (header+'DATA;'+data).splitlines())+'\n')
    exported=WORK/'native-inputs.json'
    subprocess.run([args.kicad_python,str(ROOT/'scripts/export_e73_usb_ground.py'),'--model-ref','J2','--output',str(exported)],check=True,capture_output=True)
    copper=read(exported);hashes(copper['source_sha256'])
    shape=load(step);bb=bounds(shape)
    assert bb[5]<0 and -bb[2]<=spec['maximum_installed_height_below_PCB_mm']
    contacts=landing(shape,copper['local_model_pads']['J2'],5)
    try:landing(move(shape,x=1),copper['local_model_pads']['J2'],5)
    except AssertionError:pass
    else:raise AssertionError('Displaced SH3 model was accepted')

    mechanical=read(ROOT/'mechanical/assembly-spec.json');fit=read(ROOT/'mechanical/e73-fit-spec.json')
    profile=read(ROOT/'mechanical/pcb-fabrication-spec.json');local=read(ROOT/'hardware/e73-usb-local-fit-spec.json')
    bottom_path=ROOT/local['bottom_output'];top_path=ROOT/mechanical['geometry']['top']
    assert str(bottom_path.relative_to(ROOT)) in usb_fit['outputs']
    bottom=load(bottom_path);top=load(top_path)
    z=assembly['nominal_stack']['pcb_bottom_z'];x,y=spec['position_PCB_mm'];height=spec['maximum_installed_height_below_PCB_mm']
    fab=copper['local_model_Fab_bounds_native_XY_mm']['J2']
    body=[min(bb[0],fab[0]),min(bb[1],fab[1]),z-height,max(bb[3],fab[2]),max(bb[4],fab[3]),z]
    exit_y=-y+spec['header_rear_local_y_mm']+spec['mated_depth_reference_mm'];width=spec['housing_nominal_width_mm']
    plug=[x-width/2,exit_y-spec['housing_nominal_depth_mm'],z-height,x+width/2,exit_y,z]
    swept,parked=sweep_bounds(plug,(1,1),spec['withdrawal_stroke_mm'])
    growth=local['maximum_body_growth_XY_each_axis_mm'];board_xy=local['maximum_installed_board_point_error_XY_each_axis_mm']
    detached=parked[1]-body[4]-2*growth
    assert detached>=spec['minimum_detached_gap_mm'],('SH3 remains engaged',detached)
    terms=dict(plate=fit['plate']['maximum_installed_surface_error_Z_mm'],shoulder=mechanical['pcb_fastener']['shoulder_length_tolerance'],
               film=mechanical['pcb_fastener']['top_insulator_thickness_tolerance'],bow=local['maximum_additional_mounted_PCB_bow_Z_mm'])
    dz=math.fsum(terms.values());xy=growth+board_xy
    case_error=math.sqrt(3)*fit['case_maximum_coordinate_error_each_axis_mm'];guard=fit['geometric_computation_guard_mm']
    retained=[]
    for p in assembly['component_envelopes']:
        if p['ref'] not in ['D1','R30','R31','J2','C32']:retained.append((p['ref'],p['bounds_case_mm']))
    for ref,b in usb_fit['required_body_bounds_case_mm'].items():retained.append((ref,b))
    for ref,datum in usb_fit['mating_housings'].items():retained.append((ref+'-mating-housing',datum['bounds_case_mm']))
    mounts=[]
    for p in assembly['mounting_hole_matches']:
        u,v=p['pcb_center_case_mm'];r=mechanical['pcb_fastener']['washer_od_max']/2+.15
        # Conservative inspected local hardware proxy; full fastener model and
        # tolerance qualification remains explicitly outside this study.
        mounts.append(('mount-'+p['pcb_ref'],[u-r,v-r,z-2.5,u+r,v+r,z]))
    retained+=mounts
    pack=box(assembly['battery_candidates'][0]['bounds_case_mm'])
    nominal=profile['CAD_finished_envelope_mm'];low,high=profile['ordinary_thickness_acceptance_range_mm']
    cases=[(t,nominal-t,nominal-t) for t in [nominal,low,high]]+ [([low,high],nominal-high,nominal-low)]
    rows=[]
    for thickness,down,up in cases:
        def placed(b):
            q=b[:];q[2]+=down;q[5]+=up;return q
        for name,b in [('header',body),('mated-housing',plug),('withdrawal-sweep',swept)]:
            env=expand(placed(b),xy,dz,dz);solid=box(env)
            case_gaps={k:distance(solid,s) for k,s in [('bottom',bottom),('top',top)]}
            reserve=min(case_gaps.values())-case_error-guard
            assert reserve>=spec['minimum_air_gap_mm'],(name,thickness,'Case obstruction',reserve)
            other=[(name,box(placed(b))) for name,b in retained]+[('pack',pack)]
            nearest=min((distance(solid,s),name) for name,s in other)
            assert nearest[0]>=spec['minimum_air_gap_mm'],(name,thickness,'Foreign obstruction',nearest)
            rows.append(dict(part=name,pcb_thickness_mm=thickness,bounds_case_mm=env,case_gaps_mm=case_gaps,
                             remaining_case_air_gap_mm=reserve,nearest_foreign_part=nearest[1],minimum_foreign_gap_mm=nearest[0],
                             foreign_envelopes_checked=len(other)))

    # Reproduce the held PH geometry from the actual pre-repair E73 Git board.
    baseline_path='hardware/e73-usb-repair/EC60-nRF52840.kicad_pcb'
    previous=subprocess.check_output(['git','show',spec['baseline_commit']+':'+baseline_path],cwd=ROOT)
    old_tree=loads(previous.decode());old=next(f for f in children(old_tree,'footprint') if any(p[1:3]==['Reference','J2'] for p in children(f,'property')))
    old_part=next(p for p in assembly['component_envelopes'] if p['ref']=='J2')
    assert old[1].startswith('YAECKB:JST_PH_') and [float(v) for v in child(old,'at')[1:3]]==old_part['position_pcb_mm']
    assert sorted(float(child(p,'at')[1]) for p in children(old,'pad') if p[1] in ['1','2','3'])==[-2,0,2]
    ph=read(ROOT/'mechanical/interconnect-spec.json')['sources']['PH'];px,py=old_part['position_pcb_mm']
    old_exit=-py+ph['header_back_local_y']+ph['mated_depth_reference']
    old_plug=[px-ph['housing_width']/2,old_exit-ph['housing_depth'],z-old_part['height_envelope_mm'],px+ph['housing_width']/2,old_exit,z]
    old_sweep,_=sweep_bounds(old_plug,(1,1),spec['withdrawal_stroke_mm'])
    old_solid=box(old_sweep);h8=box(next(b for name,b in mounts if name=='mount-H8'))
    regression=dict(E73_baseline_commit=spec['baseline_commit'],baseline_PCB_sha256=hashlib.sha256(previous).hexdigest(),
                    PH_header_proxy_bounds_case_mm=old_part['bounds_case_mm'],H8_proxy_bounds_case_mm=bounds(h8),
                    PH_plug_bounds_case_mm=old_plug,PH_sweep_bounds_case_mm=old_sweep,
                    PH_H8_envelope_overlap_mm3=intersection_volume(old_solid,h8),PH_bottom_envelope_overlap_mm3=intersection_volume(old_solid,bottom))
    assert min(regression['PH_H8_envelope_overlap_mm3'],regression['PH_bottom_envelope_overlap_mm3'])>1e-6,'Held PH obstructions did not reproduce'
    inputs=[Path(__file__),SPEC,board_path,native_path,fit_path,assembly_path,ROOT/spec['source_library'],bottom_path,top_path,
            ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/e73-fit-spec.json',ROOT/'mechanical/pcb-fabrication-spec.json',
            ROOT/'hardware/e73-usb-local-fit-spec.json',ROOT/'mechanical/interconnect-spec.json',ROOT/'scripts/e73_battery_service.py',
            ROOT/'scripts/check_e73_usb_local_fit.py',ROOT/'scripts/check_e73_usb_local_models.py',ROOT/'scripts/export_e73_usb_ground.py',
            ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_yeti60_interconnects.py',ROOT/'scripts/cad_geometry.py',ROOT/'scripts/kicad_sexpr.py',ROOT/'scripts/draw_e73_battery_service.py']
    report=dict(status='e73-sh3-native-landing-and-bounded-rigid-service-passed',manufacturing_released=False,physical_verification=False,
                complete_connected_service_qualified=False,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},
                native_model=dict(path=str(step.relative_to(ROOT)),sha256=sha(step),bounds_native_mm=bb,native_Fab_bounds_native_XY_mm=fab,landing=contacts,
                                  standard_source=str(model_source),standard_source_sha256=sha(model_source),shifted_model_fault_detected=True),
                header_required_body_bounds_case_mm=body,mated_housing_bounds_case_mm=plug,continuous_withdrawal_bounds_case_mm=swept,
                detached_housing_bounds_case_mm=parked,detached_to_header_after_body_growth_mm=detached,
                provisional_wire_exit_center_case_mm=[x,exit_y,z-1.6],wire_exit_datum_qualified=False,
                pin_wire_exit_X_case_mm={str(i):x+i-2 for i in [1,2,3]},
                vertical_error_terms_mm=terms,XY_body_and_board_point_allowance_mm=xy,case_coordinate_error_L2_mm=case_error,
                checks=rows,pre_repair_regression=regression,
                limits=['J2 nominal native model, numbered pin contract and rigid axial housing only; actual supplier dimensions/retention and incoming installed limits remain unqualified',
                        'Retained parts and 28 mounting sets use inherited proxies; complete component/fastener tolerance closure remains open',
                        'No connected flexible-wire deformation, loose-plug parking, tool/finger access, stack lift or installation-path acceptance',
                        'Wire-exit Z datum is provisional and must be confirmed for the finished harness before routing acceptance',
                        'SH catalog 1 A at AWG28 is not battery protection, fault interruption, contact heating or charging safety qualification',
                        'Candidate-specific firmware/calibration/CAM, left power/thermal layout and physical tests remain required'])
    from draw_e73_battery_service import draw
    report['outputs']=draw(report)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'checks; minimum case reserve',min(r['remaining_case_air_gap_mm'] for r in rows),flush=True)


if __name__=='__main__':main()
