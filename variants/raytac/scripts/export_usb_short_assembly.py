#!/usr/bin/env python3
"""Join candidate wires, five mating plugs, guides and native header CAD.

No native board, old case or old assembly publication is modified. Housing
boxes are conservative fit envelopes, not supplier-exact injection moulds.
"""
import copy
import csv
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from cad_geometry import bounds, load
from check_usb_short_closed_assembly import BASE, ROOT, hashes, input_data, obstacles
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import near, write_step
from export_yeti60_render_meshes import tessellate
from kicad_sexpr import child, children, dumps, loads
from usb_short_guides import build
from usb_short_harness import envelope_wire, paired_data, paths
from usb_short_battery_service import POSITION, HOUSING_DEPTH, HOUSING_WIDTH

WORK = ROOT / '.assembly-work/usb-short-assembly'
AUD = BASE / 'audit'
KICAD = Path('/Applications/KiCad/KiCad.app/Contents')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def expand(bb, amount):
    return [v + (-amount if i < 3 else amount) for i, v in enumerate(bb)]


def plugs(local, legacy, nominal):
    result = []
    for entry in legacy['mated_housings']:
        name = entry['name']
        owner = {'main-SH': 'J1', 'main-PH': 'J2', 'C5-SH': 'C5'}[name]
        result.append(dict(name=name, bounds_case_mm=entry['bounds_case_mm'],
                           family={'J1': 'power', 'J2': 'battery', 'C5': 'usb'}[owner], owner=owner))
        if owner=='J2':
            result[-1]['name']='J2-SH3-mating-plug'
            exit_y=-POSITION[1]+4.575
            result[-1]['bounds_case_mm']=[POSITION[0]-HOUSING_WIDTH/2,exit_y-HOUSING_DEPTH,-5.1,POSITION[0]+HOUSING_WIDTH/2,exit_y,-2.1]
    for entry in local['local_connector_and_mating_housing_checks']:
        if entry['envelope'].endswith('-mating-plug') and abs(entry['pcb_thickness_mm'] - nominal) < 1e-7:
            owner = entry['envelope'].split('-')[0]
            result.append(dict(name=entry['envelope'], bounds_case_mm=entry['bounds_case_mm'],
                               family='usb' if owner == 'J4' else 'power', owner=owner))
    assert len(result) == 5
    return result


def check_plugs(spec, assembly, native, exits, closed, guide_report):
    profile = read(ROOT / 'mechanical/pcb-fabrication-spec.json')
    nominal = profile['CAD_finished_envelope_mm']
    housing = plugs(read(AUD / 'geometry-check.json'), read(ROOT / 'docs/audit/yeti60-interconnects.json'), nominal)
    case = load(BASE / 'mechanical/yeti60-bottom-short-usb.step')
    top = load(ROOT / 'mechanical/generated/yeti60-top.step')
    pack = box(assembly['battery_candidates'][0]['bounds_case_mm'])
    guides, films = build(spec, case, closed['nominal']['routes'], exits)
    gap = spec['wire']['minimum_air_gap_after_allowance']
    allowance = spec['wire']['case_and_route_position_allowance']
    checks = []
    for thickness in [nominal, *profile['ordinary_thickness_acceptance_range_mm']]:
        delta = nominal - thickness
        routes, centre = paths(spec, exits, delta)
        routes['usb'].update(paired_data(centre, spec)[0])
        wires = {f: [envelope_wire(p, spec['wire']['insulation_od_max'] + 2 * allowance)
                     for p in conductors.values()] for f, conductors in routes.items()}
        pcb = move(load(ROOT / '.assembly-work/pcb-placed.step'), z=delta)
        obs = obstacles(assembly, native, delta)
        for plug in housing:
            dz = 0 if plug['owner'] == 'C5' else delta
            bb = [v + (dz if i in [2, 5] else 0) for i, v in enumerate(plug['bounds_case_mm'])]
            shape, enlarged = box(bb), box(expand(bb, allowance))
            # The allowance is not applied through the intentional PCB-side
            # mating datum; the nominal housing must not overlap the PCB.
            from cad_geometry import intersection_volume
            assert intersection_volume(shape, pcb) < 1e-6, (plug['name'], 'PCB overlap')
            clear = {name: distance(enlarged, obj) for name, obj in [('bottom', case), ('top', top), ('pack', pack)]}
            for name, obj in obs:
                if name == plug['owner'] or not near(bounds(enlarged), bounds(obj), 1):
                    continue
                clear[name] = distance(enlarged, obj)
            for family, objects in wires.items():
                # Its own conductors intentionally emerge through the plug.
                if family != plug['family']:
                    clear[family + '-wires'] = min(distance(enlarged, obj) for obj in objects)
            for part in guides + films:
                dz_part = delta if part['name'].startswith('PWR') else 0
                obj = move(part['shape'], z=dz_part)
                if near(bounds(enlarged), bounds(obj), 1):
                    clear[part['name']] = distance(enlarged, obj)
            for other in housing:
                if other['name'] == plug['name']:
                    continue
                dz_other = 0 if other['owner'] == 'C5' else delta
                other_bb = [v + (dz_other if i in [2, 5] else 0) for i, v in enumerate(other['bounds_case_mm'])]
                # Both housings have independent position allowance.
                clear[other['name']] = distance(enlarged, box(expand(other_bb, allowance)))
            nearest = min(clear, key=clear.get)
            assert clear[nearest] >= gap - 1e-6, (plug['name'], thickness, nearest, clear[nearest])
            checks.append(dict(name=plug['name'], pcb_thickness_mm=thickness,
                               minimum_expanded_gap_mm=clear[nearest], nearest=nearest,
                               foreign_gaps_mm=clear))
    return housing, checks


def headers():
    tree = loads((BASE / 'EC60-nRF52840.kicad_pcb').read_text())
    byref = {str(next(p[2] for p in children(f, 'property') if p[1] == 'Reference')): f
             for f in children(tree, 'footprint')}
    result = []
    from usb_short_model_contract import resolve
    for ref in ['J1', 'J2', 'J4', 'J5']:
        model=child(byref[ref], 'model')
        source=resolve(model[1]);assert source.is_file(),source
        model[1]=str(source)
        result.append(dict(ref=ref, model_source=source.name, model_source_sha256=sha(source)))
    temporary = WORK / 'headers.kicad_pcb'
    temporary.write_text(dumps(tree) + '\n')
    for part in result:
        target = WORK / (part['ref'] + '.step')
        subprocess.run([str(KICAD / 'MacOS/kicad-cli'), 'pcb', 'export', 'step', '--no-board-body',
                        '--component-filter', part['ref'], '--user-origin', '0x0mm', '-f', '-o', str(target), str(temporary)],
                       check=True, capture_output=True)
        text = re.sub(r"(FILE_NAME\('[^']*',')[^']*", r'\g<1>2000-01-01T00:00:00', target.read_text())
        target.write_text('\n'.join(line.rstrip() for line in text.splitlines()) + '\n')
        part.update(path=str(target.relative_to(ROOT)), sha256=sha(target))
    return result


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    closed, guides = read(AUD / 'closed-assembly.json'), read(AUD / 'guides.json')
    hashes(closed['source_sha256']); hashes(guides['source_sha256']); hashes(guides['outputs'])
    hashes(closed['case']['outputs']); hashes(closed['nominal']['generated_step_sha256'])
    plate_build=read(AUD/'plate-build.json');hashes(plate_build['source_sha256']);hashes(plate_build['outputs'])
    spec = read(BASE / 'interconnect-spec.json')
    assembly, native, exits = input_data(spec)
    housing, checks = check_plugs(spec, assembly, native, exits, closed, guides)
    print('Five mating plugs versus foreign wires, guides, case, pack and retained parts passed at all three thicknesses', flush=True)
    data = copy.deepcopy(assembly)
    data['status'] = 'candidate-closed-assembly-geometry-passed-not-physical'
    data['case_files']['bottom'] = str((BASE / 'mechanical/yeti60-bottom-short-usb.step').relative_to(ROOT))
    data['plate_geometry']=plate_build['candidate_STEP']
    data['plate_DXF']=plate_build['candidate_plate']
    data['component_envelopes'] = [p for p in data['component_envelopes'] if p['ref'] not in ['R30', 'R31']]
    native_values = {p.get('ref'):p.findtext('value') for p in ET.parse(BASE / 'netlist.xml').findall('./components/comp')}
    qualification = read(BASE / 'parts-qualification.json')['F1']
    nominal_model = load(BASE / qualification['native_model']['path'])
    assert max(abs(a-b) for a,b in zip(bounds(nominal_model),qualification['native_model']['bounds_local_mm']))<1e-6
    for component in data['component_envelopes']:
        # The previous Raytac assembly map is a geometry baseline. In
        # particular its J1 data-input name and old F1 value are not current.
        component['value'] = native_values[component['ref']]
        if component['ref'] == 'F1':
            component['mpn'] = qualification['mpn']
            component['clearance_basis'] = 'Retain the larger legacy clearance envelope; selected 466 body and solder allowance fit inside it'
            x,y = component['position_pcb_mm']; length,width,height = qualification['body_nominal_LWH_mm']
            assert component['angle_deg']==90 and component['back']
            z = data['nominal_stack']['pcb_bottom_z']
            component['render_body_bounds_case_mm'] = [x-width/2,-y-length/2,z-height,x+width/2,-y+length/2,z]
            length,width,height = qualification['body_max_LWH_mm']
            body = [x-width/2-.25,-y-length/2-.25,z-height-.1,x+width/2+.25,-y+length/2+.25,z]
            outer = component['bounds_case_mm']
            assert all(outer[i]<=body[i] for i in range(3)) and all(outer[i]>=body[i] for i in range(3,6))
            component['qualified_max_body_with_allowance_case_mm'] = body
    with (BASE / 'mainboard-purchase.csv').open() as stream:
        rows = [dict(references=r['References'], quantity=int(r['Required']), package=r['Package']) for r in csv.DictReader(stream)]
    assert sum(r['quantity'] for r in rows) == 75
    (AUD / 'assembly-bom.json').write_text(json.dumps(dict(rows=rows, source_sha256={'hardware/usb-short-route/mainboard-purchase.csv': sha(BASE / 'mainboard-purchase.csv')}), indent=2) + '\n')
    dependencies = [AUD / 'closed-assembly.json', AUD / 'guides.json', AUD / 'native-check.json', AUD / 'geometry-check.json',
                    ROOT / 'docs/audit/yeti60-assembly.json', ROOT / 'docs/audit/yeti60-daughterboard.json',
                    ROOT / 'docs/audit/yeti60-interconnects.json', ROOT / 'scripts/export_yeti60_render_meshes.py',
                    ROOT / 'scripts/usb_short_guides.py', ROOT / 'scripts/usb_short_harness.py',
                    ROOT / 'scripts/cad_geometry.py', ROOT / 'scripts/kicad_sexpr.py', Path(__file__), AUD / 'assembly-bom.json', BASE / 'parts-qualification.json', BASE / 'netlist.xml']
    dependencies += [AUD/'plate-build.json',BASE/'mechanical-fit-spec.json',ROOT/plate_build['candidate_STEP'],ROOT/plate_build['candidate_plate']]
    data['source_sha256'] = dict(closed['source_sha256']) | {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    data['mated_housings'] = housing
    data['mated_housing_cross_checks'] = checks
    data['physical_verification'] = False
    data['manufacturing_released'] = False
    data['not_verified'] += ['Mating/unmating swept service path, adhesive retention forces and real cable springback',
                             'USB impedance/eye, enclosed RF and thermal performance with the final pack']
    report = AUD / 'assembly.json'
    report.write_text(json.dumps(data, indent=2) + '\n')
    meshes = {name: tessellate(path) for name, path in [('bottom', ROOT / data['case_files']['bottom']),
              ('top', ROOT / data['case_files']['top']), ('plate', ROOT / data['plate_geometry']),
              ('pcb', ROOT / '.assembly-work/pcb-placed.step')]}
    extras = []
    fit=read(BASE/'mechanical-fit-spec.json');g=fit['gaskets'];sx,sy=g['finished_size_XY_mm']
    data['gaskets']=[]
    for layer,z0,z1 in [('lower',3.19,data['nominal_stack']['plate_bottom_z']),('upper',data['nominal_stack']['plate_bottom_z']+data['nominal_stack']['plate_thickness_mm'],6.39)]:
        for i,(x,y) in enumerate(g['centers_case_XY_mm'],1):
            name='gasket-'+layer+'-'+str(i);bb=[x-sx/2,y-sy/2,z0,x+sx/2,y+sy/2,z1]
            target=WORK/(name+'.step');write_step(box(bb),target);meshes[name]=tessellate(target)
            extras.append(dict(name=name,mesh=name,category='gasket',color='black',group='gasket-'+layer))
            data['gaskets'].append(dict(name=name,bounds_case_mm=bb,stock_thickness_mm=g[layer+'_stock_thickness_mm']))
    report.write_text(json.dumps(data,indent=2)+'\n')
    public_wires = BASE / 'mechanical/harness'
    public_wires.mkdir(exist_ok=True)
    published = {}
    for part in closed['nominal']['render_parts']:
        source = ROOT / part['path']
        target = public_wires / (part['name'] + '.step')
        shutil.copyfile(source, target)
        assert sha(target) == part['sha256']
        published[str(target.relative_to(ROOT))] = sha(target)
        name = 'wire-' + part['name']; meshes[name] = tessellate(target)
        extras.append(part | dict(mesh=name))
    for part in guides['render_parts']:
        assert sha(ROOT / part['path']) == part['sha256']
        name = 'guide-' + part['name']; meshes[name] = tessellate(ROOT / part['path'])
        extras.append(part | dict(mesh=name, group='interconnect', color=part.get('color', 'gray')))
    for plug in housing:
        target = WORK / (plug['name'] + '.step'); write_step(box(plug['bounds_case_mm']), target)
        meshes[plug['name']] = tessellate(target)
        extras.append(dict(name=plug['name'], mesh=plug['name'], category='mating-housing', color='cream', group='interconnect'))
    header_parts = headers()
    daughter = read(ROOT / 'docs/audit/yeti60-daughterboard.json')
    ds = read(ROOT / 'mechanical/assembly-spec.raytac.json')['daughterboard']
    models = [(p['ref'], p, [0, 0, data['nominal_stack']['pcb_bottom_z']], 'header', 'cream', 'electronics') for p in header_parts]
    models += [('C5-' + name, part, [ds['source_to_case_x_offset'], ds['source_to_case_y_offset'], ds['pcb_bottom_z']],
                'daughterboard', {'pcb': 'pcb', 'usb': 'metal', 'sh': 'cream', 'components': 'black'}[name], 'daughterboard')
               for name, part in daughter['render_parts'].items()]
    for name, part, offset, category, color, group in models:
        assert sha(ROOT / part['path']) == part['sha256']
        m = tessellate(ROOT / part['path'])
        m['vertices_mm'] = [[v[i] + offset[i] for i in range(3)] for v in m['vertices_mm']]
        for field in ['brep_bounds_mm', 'mesh_bounds_mm']:
            m[field] = [v + offset[i % 3] for i, v in enumerate(m[field])]
        meshes[name] = m
        extras.append(dict(name=name, mesh=name, category=category, color=color, group=group))
    geometry = dict(assembly_report_sha256=sha(report), export_recipe_sha256=sha(Path(__file__)),
                    geometry_helper_sha256=sha(ROOT / 'scripts/cad_geometry.py'), geometry_sources=data['source_sha256'],
                    interconnect_report_sha256=sha(AUD / 'closed-assembly.json'),
                    daughterboard_report_sha256=sha(ROOT / 'docs/audit/yeti60-daughterboard.json'),
                    guides_report_sha256=sha(AUD / 'guides.json'), extra_parts=extras, meshes=meshes,
                    tessellation_linear_deflection_mm=.015, tessellation_angular_deflection_rad=.08,
                    case_scale=[1, 1, 1], native_headers=header_parts, published_wire_STEP_sha256=published,
                    unavailable_native_models={})
    (WORK / 'render-meshes.json').write_text(json.dumps(geometry, separators=(',', ':')))
    receipt = {k: v for k, v in geometry.items() if k != 'meshes'}
    receipt['mesh_payload_sha256'] = sha(WORK / 'render-meshes.json')
    (AUD / 'assembly-meshes.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Candidate assembly meshes: nine wires, five mating plugs, 16 guides, 12 films, four native headers including SH3 J2 and complete C5', flush=True)


if __name__ == '__main__':
    main()
