#!/usr/bin/env python3
"""Reject stale or mixed nine-wire assembly drawings, renders and STEP files."""
import hashlib
import csv
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from render_usb_short_assembly import build_source
from usb_short_passive_contract import verify_passives
from study_usb_short_tolerances import verify_evidence as verify_tolerance_evidence

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def purchase_rows(path):
    with path.open(newline='') as stream:
        return list(csv.reader(stream))


def check_wire_table(text, closed, zh=False):
    labels={'usb':'USB','power':'电源' if zh else 'Power','battery':'电池' if zh else 'Battery'}
    for family,wires in closed['nominal']['wires'].items():
        for wire in wires:
            row=re.search(r'(?m)^\| '+labels[family]+' '+wire['pin']+r' \| ([\d.]+) \| ([\d.]+) \|',text)
            assert row,('Missing documented cable',family,wire['pin'])
            assert row.group(1)==f"{wire['free_length_mm']:.2f}",('Stale documented wire length',family,wire['pin'])
            assert row.group(2)==f"{wire['minimum_design_bend_radius_mm']:.2f}",('Stale documented bend radius',family,wire['pin'])


def hashes(table):
    for path,h in table.items():
        assert sha(ROOT/path)==h,('Stale candidate assembly input/output',path)


def verify():
    verify_passives()
    evidence={name:read(BASE/'audit'/name) for name in [
        'closed-assembly.json','guides.json','assembly.json','assembly-meshes.json',
        'assembly-surfaces.json','assembly-drawings.json','assembly-bom.json','feed-budget.json','vertical-motion.json','tolerance-diagnostic.json']}
    for record in evidence.values():
        hashes(record.get('source_sha256',{}));hashes(record.get('outputs',{}))
    closed=evidence['closed-assembly.json'];guide=evidence['guides.json'];assembly=evidence['assembly.json'];mesh=evidence['assembly-meshes.json']
    assert {family:len(wires) for family,wires in closed['nominal']['wires'].items()}=={'usb':4,'power':2,'battery':3}
    assert guide['part_count']==16 and guide['film_strips']==12
    assert len(guide['parts'])==16 and all(p['quantity']==1 for p in guide['parts'])
    assert len(assembly['mated_housings'])==5 and len(assembly['mated_housing_cross_checks'])==15
    assert all(c['minimum_expanded_gap_mm']>=.15-1e-6 for c in assembly['mated_housing_cross_checks'])
    assert assembly['case_files']['bottom']=='hardware/usb-short-route/mechanical/yeti60-bottom-short-usb.step'
    assert assembly['nominal_stack']==read(ROOT/'docs/audit/yeti60-assembly.json')['nominal_stack']
    contract={p.get('ref'):p.findtext('value') for p in ET.parse(BASE/'netlist.xml').findall('./components/comp')}
    for p in assembly['component_envelopes']:
        assert p['value']==contract[p['ref']],('Stale candidate component value',p['ref'])
    native_passives=read(ROOT/'.assembly-work/usb-short-audit/native-inputs.json')['revised_power_components']
    for c in native_passives:
        part=next(p for p in assembly['component_envelopes'] if p['ref']==c['ref'])
        x0,y0,x1,y1=c['bbox_pcb_mm'];z=assembly['nominal_stack']['pcb_bottom_z']
        assert part['position_pcb_mm']==c['position'][:2] and part['angle_deg']==c['position'][2]
        assert part['bounds_case_mm']==[x0,-y1,z-3,x1,-y0,z],('Stale power component bounds',c['ref'])
    assert len(assembly['mounting_hole_matches'])==28 and assembly['unused_pcb_mount_refs']==['H26']
    assert closed['case']['minimum_remaining_skin_after_tolerance_mm']>=2
    for zh in [False,True]:
        check_wire_table((BASE/('CLOSED-CASE'+('.zh-CN' if zh else '')+'.md')).read_text(),closed,zh)
    motion=evidence['vertical-motion.json']
    assert motion['status']=='nominal-disconnected-rigid-extraction-passed'
    assert motion['translation_mm']==[0,0,22]
    assert motion['complete_service_path_qualified'] is False
    expected_motion={p['ref'] for p in assembly['component_envelopes']}|{'PCB-exact-planar-footprint','plate-exact-planar-footprint','main-SH','J5-mating-plug'}
    expected_motion|={'stack-hardware-'+str(i+1) for i in range(len(assembly['mounting_hole_matches']))}
    expected_motion|={p['name'] for p in guide['render_parts'] if p['name'].startswith('PWR')}
    expected_motion|={'power-'+pin+'/segment-'+str(i+1) for pin,path in closed['nominal']['routes']['power'].items() for i in range(len(path))}
    assert {p['part'] for p in motion['moving_envelopes']}==expected_motion,'Incomplete rigid extraction coverage'
    assert all(p['intersection_mm3']<1e-6 for p in motion['moving_envelopes'])
    assert motion['baseline_regression']['unrelieved_PCB_sweep_intersection_mm3']>1
    assert len(motion['rear_clip_tolerance_screen'])==6
    assert min(row['remaining_gap_mm'] for row in motion['rear_clip_tolerance_screen'])>=.15-1e-6
    verify_tolerance_evidence(evidence['tolerance-diagnostic.json'],read(ROOT/'mechanical/assembly-spec.raytac.json'),read(ROOT/'mechanical/pcb-fabrication-spec.json'))
    feed=evidence['feed-budget.json']
    assert feed['selected_F1']['mpn']=='0466001.NRHF'
    for filename in ['mainboard-purchase.csv','mainboard-purchase.zh-CN.csv']:
        rows=purchase_rows(BASE/filename)
        fuse=next(row for row in rows[1:] if row[0]=='F1')
        assert fuse[1:4]==['1','0','1'],('Incorrect F1 quantity/stock allocation',filename)
        assert fuse[4]=='1A_FAST_0466001_NRHF',('Old F1 purchase type',filename)
        assert fuse[5]=='Fuse_Littelfuse_0466_1206__F1',('Old F1 purchase land pattern',filename)
        assert fuse[7]=='Littelfuse 0466001.NRHF',('Old F1 purchase MPN',filename)
    assert feed['status']=='conditional-feed-budget-calculated-not-qualified' and feed['engaged_power_contact_count']==8
    assert abs(feed['nominal_copper_length_m']-sum(w['free_length_mm'] for f,pin in feed['selected_wire_legs'] for w in closed['nominal']['wires'][f] if w['pin']==pin)/1000)<1e-9
    hashes(closed['case']['outputs']);hashes(mesh['published_wire_STEP_sha256'])
    assert len(mesh['published_wire_STEP_sha256'])==9
    assert mesh['assembly_report_sha256']==sha(BASE/'audit/assembly.json')
    assert mesh['guides_report_sha256']==sha(BASE/'audit/guides.json')
    assert mesh['export_recipe_sha256']==sha(ROOT/'scripts/export_usb_short_assembly.py')
    assert {p['ref'] for p in mesh['native_headers']}=={'J1','J4','J5'}
    assert 'J2' in mesh['unavailable_native_models']
    assert len(evidence['assembly-drawings.json']['outputs'])==28
    assert set(evidence['assembly-surfaces.json']['outputs'])=={
        'hardware/usb-short-route/assembly/pcb-surface-front.png','hardware/usb-short-route/assembly/pcb-surface-back.png'}
    manifest=read(BASE/'assembly/render-manifest.json')
    recipe_hash=hashlib.sha256(build_source().encode()).hexdigest()
    assert manifest['recipe_sha256']==recipe_hash,'Studio recipe changed; regenerate candidate renders'
    hashes(manifest['source_recipe_sha256']);hashes(manifest['geometry_sources'])
    assert manifest['surface_report_sha256']==sha(BASE/'audit/assembly-surfaces.json')
    assert manifest['guides_report_sha256']==sha(BASE/'audit/guides.json')
    assert manifest['mesh_receipt_sha256']==sha(BASE/'audit/assembly-meshes.json')
    assert manifest['assembly_report_sha256']==sha(BASE/'audit/assembly.json')
    assert manifest['fitted_BOM_sha256']==sha(BASE/'audit/assembly-bom.json')
    refs={ref.strip() for row in evidence['assembly-bom.json']['rows'] for ref in row['references'].split(',')}
    assert len(refs)==75 and refs==set(manifest['fitted_mainboard_references'])
    assert not refs.intersection({'R30','R31','JP1'}) and {'J4','J5'}.issubset(refs)
    assert manifest['exploded_visible_objects_by_group']['electronics']==75
    assert manifest['exploded_visible_objects_by_group']['interconnect']==42
    # Object counts distinguish physical quantities from their visual pieces:
    # 28 standoffs use 3 body segments each; 28 screws use head + shank.
    expected_objects={'bottom':1,'top':1,'plate':1,'pcb':1,'battery':1,'daughterboard':4,
        'caps':119,'switches':120,'domes':60,'springs':60,'stabilizers':15,
        'standoffs':84,'insulation':56,'pcb-fasteners':56,'shell-hardware':32,'feet':5}
    for group,count in expected_objects.items():
        assert manifest['exploded_visible_objects_by_group'][group]==count,('Incomplete explosion',group)
    assert all(v['in_frame'] and v['above_desk'] for v in manifest['exploded_frame_checks'].values())
    assert set(manifest['outputs'])=={'assembled.png','rear.png','exploded.png','battery-space.png'}
    for name,item in manifest['outputs'].items():
        assert sha(BASE/'assembly'/name)==item['sha256'],('Changed render',name)
        assert item['recipe_sha256']==recipe_hash,('Old view recipe',name)
        for field,actual in [('assembly_report_sha256',sha(BASE/'audit/assembly.json')),
                             ('mesh_receipt_sha256',sha(BASE/'audit/assembly-meshes.json')),
                             ('surface_report_sha256',sha(BASE/'audit/assembly-surfaces.json')),
                             ('guides_report_sha256',sha(BASE/'audit/guides.json')),
                             ('mesh_export_recipe_sha256',sha(ROOT/'scripts/export_usb_short_assembly.py'))]:
            assert item[field]==actual,('Old view inputs',name,field)
    return dict(status='candidate-assembly-package-consistent',physical_verification=False,manufacturing_released=False,
        conductor_count=9,mating_housings=5,printable_guides=16,retention_films=12,fitted_mainboard_parts=75,
        assembly_sheets_per_language=7,studio_views=4,physical_acceptance='open',
        evidence_sha256={name:sha(BASE/'audit'/name) for name in evidence},
        render_manifest_sha256=sha(BASE/'assembly/render-manifest.json'),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),BASE/'CLOSED-CASE.md',BASE/'CLOSED-CASE.zh-CN.md',BASE/'SERVICE-PATH.md',BASE/'SERVICE-PATH.zh-CN.md',BASE/'TOLERANCES.md',BASE/'TOLERANCES.zh-CN.md']},
        open_requirements=['Swept service/mating path and wire springback/retention',
                           'Plate-ear tolerance in both shells and SW100 floor reserve; see TOLERANCES.md',
                           'Supplier-qualified pack and final exact component approvals',
                           'Physical USB/BLE, simultaneous charging/input, 60-key calibration, temperature and enclosed RF'])


def main():
    result=verify()
    (BASE/'audit/assembly-package.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
