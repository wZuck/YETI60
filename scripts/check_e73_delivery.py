#!/usr/bin/env python3
"""Verify an offline E73 bundle, or verify the bundle and source checkout together."""
import argparse,csv,hashlib,json,math,re,struct,zipfile
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
RETAINER_DIR = '02-mechanical/retention/'
RETAINER_ARCHIVE = RETAINER_DIR + 'M05-retainer-STLs-REVIEW.zip'
RETAINER_SCREEN = '06-validation/m05-retainer-process.json'
LEGACY_RETAINER_FILES = frozenset(
    ['print/ALL-16-GUIDES-ONE-EACH' + ext for ext in ('.step', '.stl')] +
    [f'print/BAT-R{number}.stl' for number in (1, 2)] +
    [f'assembly-reference/BAT-R{number}{suffix}.step'
     for number in (1, 2) for suffix in ('', '-film')]
)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def retainer_mesh(data, weld_digits=6):
    """Read a single closed binary STL component in its supplied millimetre pose."""
    triangles, = struct.unpack_from('<I', data, 80)
    assert triangles > 0 and len(data) == 84 + 50 * triangles
    edges = defaultdict(list)
    vertices = set()
    for index, face in enumerate(struct.iter_unpack('<12fH', data[84:])):
        points = [tuple(round(coord, weld_digits) for coord in face[offset:offset + 3])
                  for offset in (3, 6, 9)]
        assert len(set(points)) == 3 and all(math.isfinite(coord) for point in points for coord in point)
        for start, end in zip(points, points[1:] + points[:1]):
            edges[tuple(sorted((start, end)))].append(index)
        vertices.update(points)
    assert all(len(faces) == 2 for faces in edges.values()), 'Open or non-manifold retainer mesh'
    neighbors = defaultdict(list)
    for first, second in edges.values():
        neighbors[first].append(second)
        neighbors[second].append(first)
    visited = {0}
    remaining = [0]
    while remaining:
        for face in neighbors[remaining.pop()]:
            if face not in visited:
                visited.add(face)
                remaining.append(face)
    assert len(visited) == triangles, 'Multiple disconnected components in retainer STL'
    dimensions = [round(max(axis) - min(axis), 6) for axis in zip(*vertices)]
    assert min(dimensions) > 0
    return triangles, dimensions


def retainer_process_screen(bundle, retainers):
    """Screen the archived geometry against ordinary SLA's published size floor."""
    minimums = [[5, 5, 5], [10, 2, 2]]
    specification = json.loads((bundle/'02-mechanical/retention-spec.json').read_text())
    limits = specification['tolerance_contract']
    rows = {}
    for name, path in sorted(retainers.items()):
        data = (bundle/path).read_bytes()
        triangles, dimensions = retainer_mesh(data)
        ordered = sorted(dimensions, reverse=True)
        rows[name] = {
            'STL': path, 'sha256': hashlib.sha256(data).hexdigest(),
            'dimensions_xyz_mm': dimensions, 'triangles': triangles, 'connected_closed_shells': 1,
            'meets_published_standard_SLA_minimum_size': any(
                all(actual >= minimum for actual, minimum in zip(ordered, model))
                for model in minimums
            ),
        }
    return {
        'revision': 'M05', 'physical_verification': False, 'factory_process_qualified': False,
        'published_ordinary_SLA': {
            'minimum_model_sizes_mm': minimums,
            'general_size_tolerance_through_100_mm': 0.20,
            'source': 'https://jlc3dp.com/help/article/3d-printing-design-guideline',
        },
        'project_surface_point_error_L2_max_mm': limits['guide_maximum_surface_point_error_L2_mm'],
        'project_minimum_finished_web_mm': limits['minimum_finished_web_mm'],
        'parts': rows,
    }


def strip_jp1_paste(artwork):
    """Remove the two flashes without changing the modal aperture selection."""
    block = rb'(?m)^%TO\.C,JP1\*%\n(?:X-?\d+Y-?\d+D03\*\n){2}%TD\*%\n'
    filtered, count = re.subn(block, b'', artwork)
    assert count == 1 and b'%TO.C,JP1*%' not in filtered, 'Unexpected JP1 paste artwork'
    return filtered


def first_article_keys(bundle):
    """Join the physical position sheet to the compiled normal/calibrator maps."""
    firmware = bundle / '05-firmware'
    manifest = json.loads((firmware / 'manifest.json').read_text())
    pipeline_path = firmware / 'key-pipeline.json'
    pipeline = json.loads(pipeline_path.read_text())
    build_path = firmware / 'yeti60-target-build.json'
    assert manifest['evidence']['hardware/e73-hhkb-corner/firmware/key-pipeline.json'] == sha(pipeline_path)
    assert pipeline['target_build_manifest_sha256'] == sha(build_path)
    assert pipeline['status'] == 'passed' and pipeline['physical_verification'] is False
    matrix = pipeline['compiled_maps']['normal']
    base_layer, fn_layer = pipeline['compiled_bindings']['normal']
    assert pipeline['compiled_maps']['calibrator'] == matrix
    assert pipeline['compiled_bindings']['calibrator'] == [base_layer, fn_layer]
    positions_path = bundle / '04-assembly/calibration-keys.csv'
    labels_path = firmware / 'calibration-bindings.csv'
    mechanism_path = bundle / '02-mechanical/key-mechanism.json'
    assert manifest['source_sha256']['firmware/target/calibration-keys.csv'] == sha(labels_path)
    assert manifest['source_sha256']['mechanical/yeti60-key-mechanism.e73.json'] == sha(mechanism_path)
    with positions_path.open(newline='') as stream:
        positions = list(csv.DictReader(stream))
    with labels_path.open(newline='') as stream:
        labels = list(csv.DictReader(stream))
    assert len(positions) == len(labels) == len(base_layer) == len(fn_layer) == len(set(matrix)) == 60
    assert len({key['Electrode'] for key in positions}) == 60
    mechanism = json.loads(mechanism_path.read_text())
    stabilized = {key['active_index'] for key in mechanism['stabilized_keys']}
    assert len(stabilized) == 3
    fn_positions = [i for i, binding in enumerate(base_layer)
                    if binding == ['zmk,behavior-momentary-layer', 1]]
    assert len(fn_positions) == 1

    rows = []
    for index, key in enumerate(positions):
        label = labels[index]
        row, column = divmod(matrix[index], 256)
        assert int(key['Index']) == int(label['index']) == index
        assert (int(key['Row']), int(key['Column'])) == (row, column)
        assert (int(label['row']), int(label['column'])) == (row, column)
        is_fn = index in fn_positions
        expected = 'none' if is_fn else keyboard_usage(base_layer[index])
        physical_key = 'Fn' if is_fn else label['key_binding'].removeprefix('&kp ')
        assert label['key_binding'] == ('&mo 1' if is_fn else '&kp ' + physical_key)
        common = dict(position_index=index, row=row, column=column,
                      electrode=key['Electrode'], physical_key=physical_key)
        pending = dict(usb_while_charging='not-run', ble_on_battery='not-run', notes='')
        rows.append(dict(**common, action='center', expected_usage=expected, **pending))
        if index in stabilized:
            for action in ('left_edge', 'right_edge'):
                rows.append(dict(**common, action=action, expected_usage=expected, **pending))
        if fn_layer[index][0] == 'zmk,behavior-key-press':
            fn_usage = keyboard_usage(fn_layer[index])
            rows.append(dict(**common, action='with_fn', expected_usage=fn_usage, **pending))
            if fn_usage == '0x07/0x3A':  # F1, with Fn released before the key.
                rows.append(dict(**common, action='release_fn_first', expected_usage=fn_usage, **pending))
    assert sum(row['action'] == 'release_fn_first' for row in rows) == 1
    return rows


def keyboard_usage(binding):
    behavior, value = binding
    assert behavior == 'zmk,behavior-key-press' and value >> 16 == 7
    return f'0x07/0x{value & 0xFFFF:02X}'


class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  self.links.extend(v for k,v in attrs if k in ['href','src'])


def ordinary_sla_trial(prototype):
    case_dir = '02-mechanical/service-case-m05/'
    trial_dir = case_dir + 'relieved-trial/'
    coupon_dir = '02-mechanical/front-retainer-coupon/'
    return {
        'status': 'engineering-trial',
        'units': 'mm',
        'scale_percent': 100,
        'quantity_per_STL': 1,
        'shell_STL': [
            trial_dir+'bottom-m05-relieved-REVIEW.stl' if path == case_dir+'bottom-m05-REVIEW.stl' else path
            for path in prototype['shell_STL']
        ],
        'guide_carriers_STL': {
            coupon_dir+'M05-front-guides-SLA-COUPON.stl': 4,
            '02-mechanical/retained-guide-blanks/M05-case-guides-SLA-BLANKS.stl': 5,
            '02-mechanical/retained-guide-blanks/M05-power-guides-SLA-BLANKS.stl': 7,
        },
        'separate_floor_coupon_STL': coupon_dir+'M05-front-floor-SLA-COUPON.stl',
        'harness_lengths': [trial_dir+'wire-lengths-relieved'+suffix+'.csv' for suffix in ('','.zh-CN')],
    }


def check_sla_order_links(guide, selection, harness):
    # Limit this check to the actual upload section. Other sections may
    # describe the stock M05 option or separate test fixtures.
    guide = guide.resolve()
    heading = '<h2 id="m05-relieved-trial-stl-upload-list">'
    chinese_heading = '<h2 id="m05-让位版-stl-上传清单">'
    body = guide.read_text()
    headings = (heading, chinese_heading)
    assert sum(body.count(title) for title in headings) == 1, (
        'Missing unique SLA upload section', guide.name)
    title = next(title for title in headings if title in body)
    section = body.split(title, 1)[1].split('<h2', 1)[0]
    parsed = Links()
    parsed.feed(section)
    paths = [
        (guide.parent/unquote(link.split('#',1)[0])).resolve()
        for link in parsed.links if not re.match(r'^[a-z]+:|^#',link)
    ]
    bundle = guide.parent.parent
    expected = [*selection['shell_STL'], *selection['guide_carriers_STL'], selection['separate_floor_coupon_STL']]
    assert sorted(p for p in paths if p.suffix == '.stl') == sorted(bundle/p for p in expected), (
        'Wrong or duplicate M05 trial STL links', guide.name)
    assert [path for path in paths if path.suffix == '.csv'] == [bundle/harness], (
        'Wrong or duplicate harness length table', guide.name)


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--bundle',type=Path,help='Path to an unpacked delivery directory')
 parser.add_argument('--require-release',action='store_true')
 args=parser.parse_args()
 if not __debug__:
  parser.error('Run Python without optimization so the verification checks are enabled')
 sibling=Path(__file__).resolve().parent
 in_checkout=args.bundle is None and not (sibling/'manifest.json').is_file()
 base=(ROOT/'delivery/YETI60-E73' if in_checkout else args.bundle or sibling).resolve()
 m=json.loads((base/'manifest.json').read_text())
 if in_checkout:
  for name,digest in m['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale source',name)
  assert m['revision']==json.loads((ROOT/'hardware/e73-corner-spec.json').read_text())['revision']
 files={str(p.relative_to(base))for p in base.rglob('*')if p.is_file()and p!=base/'manifest.json'and p.name!='.DS_Store'}
 assert files==set(m['files_sha256']),'Unlisted or missing delivery file'
 for name,digest in m['files_sha256'].items():assert sha(base/name)==digest,('Changed delivery file',name)
 prototype=m['mechanical_first_article']
 assert prototype['revision']=='M05' and prototype['use']=='first-article-dry-fit'
 assert not prototype['physical_verification']
 assert len(set(prototype['shell_STL']))==4 and len(set(prototype['retainer_STL'].values()))==16
 assert len(prototype['harness_lengths'])==len(prototype['assembly_views'])==2
 assert prototype['retainer_STL_archive'] == RETAINER_ARCHIVE
 retainers = prototype['retainer_STL']
 assert not {RETAINER_DIR + name for name in LEGACY_RETAINER_FILES} & files
 with zipfile.ZipFile(base/RETAINER_ARCHIVE) as archive:
  names = {Path(path).name:path for path in retainers.values()}
  assert len(names) == len(archive.namelist()) == 16 and set(names) == set(archive.namelist())
  assert all(archive.read(name) == (base/path).read_bytes() for name, path in names.items())
 assert json.loads((base/RETAINER_SCREEN).read_text()) == retainer_process_screen(base, retainers)
 films = json.loads((base/'06-validation/retention-prints.json').read_text())['film_blanks']
 for lang in ('','.zh-CN'):
  table = base/(RETAINER_DIR+'parts'+lang+'.csv')
  with table.open(newline='') as stream:
   header, *rows = list(csv.reader(stream))
  assert len(header) == 4 and len(rows) == 33 and all(len(row) == 4 and row[1] == '1' for row in rows)
  assert set(row[0] for row in rows) == set(retainers) | {film['name'] for film in films}
  assert all((table.parent/row[3]).resolve() == (base/retainers[row[0]]).resolve()
             for row in rows if row[0] in retainers)
 required=set(prototype['shell_STL']+list(prototype['retainer_STL'].values())+
              prototype['harness_lengths']+prototype['assembly_views'])
 assert required<=files
 case_dir='02-mechanical/service-case-m05/'
 for name in ('BAT-R1','BAT-R2'):assert prototype['retainer_STL'][name]==case_dir+'harness/'+name+'-M05.stl'
 for name in ('bottom-m05','cover-J2','cover-J4'):assert case_dir+name+'-REVIEW.stl' in prototype['shell_STL']
 blank_dir = '02-mechanical/retained-guide-blanks/'
 blank = json.loads((base/'06-validation/m05-retained-guide-blanks.json').read_text())
 assert blank['status'] == 'm05-retained-guide-connected-blank-meshes-and-trim-checked'
 assert all(blank[key] is False for key in (
     'manufacturing_released','physical_verification','selected_for_assembly','factory_process_qualified'))
 case_carrier,power_carrier = [blank_dir+name for name in ('M05-case-guides-SLA-BLANKS.stl','M05-power-guides-SLA-BLANKS.stl')]
 blank_tables = [blank_dir+name for name in ('finishing.csv','finishing.zh-CN.csv')]
 assert set(blank['files_sha256']) == {case_carrier,power_carrier,blank_dir+'cut-map.svg',*blank_tables}
 assert set(blank['files_sha256']) <= files and not set(blank['files_sha256']) & required
 assert all(sha(base/name) == digest for name,digest in blank['files_sha256'].items())
 assert blank['finished_guide_count'] == 12 and blank['maximum_printed_parts_per_connected_file'] == 10
 assert blank['branch_cross_section_mm'] == [2.,2.] and blank['published_connection_web_mm_must_exceed'] == 1.5
 assert blank['backing_stock_mm'] == 2.40 and blank['stock_on_each_transverse_side_mm'] == .60
 assert blank['maximum_finished_surface_point_error_L2_mm'] == .05 and blank['minimum_finished_web_mm'] == .30
 assert set(blank['carriers']) == {case_carrier,power_carrier}
 assert set(blank['carriers'][case_carrier]['parts']) == {'USB-R1','USB-R2','USB-R3','BAT-R1','BAT-R2'}
 assert set(blank['carriers'][power_carrier]['parts']) == {*(f'PWR-R{i}' for i in range(1,6)),'PWR-F-upper','PWR-F-lower'}
 assert {name for model in blank['carriers'].values() for name in model['parts']} == {
     name for name in retainers if not name.startswith('USB-F')}
 trim_table = []
 for model_path,model in blank['carriers'].items():
  triangles,dimensions = retainer_mesh((base/model_path).read_bytes())
  assert triangles == model['triangles'] and dimensions == model['dimensions_xyz_mm']
  assert model['connected_closed_shells'] == 1 and dimensions[1] >= 10 and min(dimensions) >= 2
  assert [row['order'] for row in model['parts'].values()] == list(range(1,len(model['parts'])+1))
  for name,row in model['parts'].items():
   expected = case_dir+f'harness/{name}-M05.step' if name.startswith('BAT-') else RETAINER_DIR+f'assembly-reference/{name}.step'
   assert row['finished_reference'] == expected and row['finished_reference_sha256'] == sha(base/expected)
   assert max(row['trim_removed_from_finished_mm3'],row['trim_stock_remaining_mm3']) < 1e-6
   planes = row['underside_planes']
   x,y,_ = row['finished_dimensions_mm']
   assert planes[0]['region_xy_mm'][1] == 0 and planes[-1]['region_xy_mm'][3] == y
   assert all(a['region_xy_mm'][3] == b['region_xy_mm'][1] for a,b in zip(planes,planes[1:]))
   for plane in planes:
    X,start,extent,end = plane['region_xy_mm']
    assert X == 0 and extent == x and end > start
    trim_table.append([Path(model_path).name,str(row['order']),name,*map(str,row['finished_dimensions_mm']),
                       str(start),str(end),str(plane['height_above_finished_base_mm']),expected])
 for name in blank_tables:
  with (base/name).open(newline='') as stream:
   header,*rows = list(csv.reader(stream))
  assert len(header) == 10 and rows == trim_table
 recess = json.loads((base/'06-validation/m05-usb-retainer-recess.json').read_text())
 assert recess['status'] == 'USB-front-recess-service-poses-and-parked-lift-checked'
 assert recess['selected_for_assembly'] is False and recess['physical_verification'] is False
 case_source = 'hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.step'
 assert recess['source_sha256'][case_source] == sha(base/(case_dir+'bottom-m05-REVIEW.step'))
 assert [row['station'] for row in recess['stations']] == ['USB-F1','USB-F2']
 assert all(row['larger_section_fixed_axis_floor_deficit_mm'] > 0 for row in recess['stations'])
 assert all(row['larger_section_fixed_axis_PCB_gap_after_allowances_mm'] < 0 for row in recess['stations'])
 route = recess['seated_USB_nominal_trial']
 assert all(route['wire_collision_volume_after_station_recesses_mm3'][pin] > 0 for pin in ('2','3'))
 assert route['worst_wire_to_bottom_gap_after_allowances_mm'] >= route['minimum_wire_to_bottom_gap_required_mm']
 assert route['minimum_wall_to_selected_exterior_after_allowances_mm'] >= recess['minimum_screened_exterior_wall_mm']
 endpoints = route['PCB_thickness_endpoint_gaps_after_allowances']
 assert [row['PCB_thickness_mm'] for row in endpoints] == recess['PCB_finished_thickness_range_mm']
 assert all(min(row['wire_to_bottom_gaps_mm'].values()) >= route['minimum_wire_to_bottom_gap_required_mm']
            for row in endpoints)
 motion = recess['USB_service_motion_trial']
 poses = ['seated', 'J2-halfway', 'J2-axial-end', 'J2-parked', 'J4-halfway', 'J4-axial-end', 'both-parked']
 assert [row['PCB_thickness_mm'] for row in motion['variants']] == [
     endpoints[0]['PCB_thickness_mm'], route['nominal_PCB_thickness_mm'], endpoints[1]['PCB_thickness_mm']]
 required_gap = motion['minimum_wire_to_obstacle_gap_required_mm']
 assert required_gap == route['minimum_wire_to_bottom_gap_required_mm'] == .15
 witnesses = motion['seated_only_relief_failure_witnesses']
 assert [(row['state'], row['USB_wire_pin']) for row in witnesses] == [
     ('J4-halfway', '4'), ('J4-axial-end', '2')]
 assert all(row['residual_gap_mm'] < required_gap for row in witnesses)
 assert motion['motion_floor_relief_bounds_case_mm'][1] < route['continuous_floor_relief_bounds_case_mm'][1]
 assert motion['minimum_wall_to_selected_exterior_after_allowances_mm'] >= recess['minimum_screened_exterior_wall_mm']
 assert motion['existing_main_and_daughterboard_insert_guards_checked'] == 8
 assert motion['bottom_covers_untouched_by_cut'] == ['J2', 'J4']
 assert motion['vertical_lift_travel_mm'] == 25
 enlarged = motion['larger_USB_guide_envelopes_case_mm']
 assert set(enlarged) == {'USB-F1-envelope', 'USB-F2-envelope'}
 assert all(len(box) == 6 and all(box[i] < box[i+3] for i in range(3))
            for box in enlarged.values())
 for row in motion['variants']:
  assert [state['state'] for state in row['states']] == poses
  assert all(required_gap <= min(state['minimum_residual_air_gap_mm'], state['minimum_USB_to_other_harness_gap_mm'],
                                  state['minimum_USB_to_fitted_body_gap_mm'])
             and state['minimum_static_bend_radius_mm'] >= 4
             and state['largest_free_length_change_from_seated_mm'] < .06
             and state['USB_pair_geometric_skew_mm'] < .005 for state in row['states'])
  lift = row['parked_lift']
  assert lift['moving_rigid_envelopes'] == 122
  assert lift['stationary_rigid_envelopes'] == 22 and lift['stationary_wire_envelopes'] == 7
  assert all(lift[proof]['clearance_mm'] >= required_gap for proof in (
      'rigid_deck_to_stationary_objects', 'rigid_deck_to_stationary_wires'))
  assert set(lift['parked_housings']) == {'J2', 'J4'}
  assert all(plug['deck_clearance_mm'] > .5 and plug['fixed_objects']['clearance_mm'] >= required_gap
             for plug in lift['parked_housings'].values())
  pairs = {(proof['moving_wire'], proof['stationary_part']) for proof in lift['moving_wire_checks']}
  assert len(pairs) == len(lift['moving_wire_checks']) == 58
  assert {wire for wire, _ in pairs} == {'power.1', 'power.2'}
  assert all(len({part for wire, part in pairs if wire == name}) == 29 for name in ('power.1', 'power.2'))
  assert all((wire, part) in pairs for wire in ('power.1', 'power.2')
             for part in {*enlarged, 'bottom', 'pack', 'J2-plug', 'J4-plug'})
  assert all(proof['certified_residual_gap_mm'] >= required_gap and proof['distance_evaluations'] >= 0
             for proof in lift['moving_wire_checks'])
 coupon_dir = '02-mechanical/front-retainer-coupon/'
 coupon = json.loads((base/'06-validation/m05-usb-retainer-coupon.json').read_text())
 assert coupon['status'] == 'm05-front-retainer-sla-coupons-exported-and-cad-checked'
 assert all(coupon[key] is False for key in (
     'selected_for_assembly', 'manufacturing_released', 'physical_verification', 'factory_process_qualified'))
 assert coupon['recess_report_sha256'] == sha(base/'06-validation/m05-usb-retainer-recess.json')
 required_coupon_files = {coupon_dir+name for name in (
     'M05-front-guides-SLA-COUPON.stl', 'M05-front-floor-SLA-COUPON.stl',
     'fit-reference-DO-NOT-UPLOAD.step', 'cut-map.svg')}
 assert set(coupon['files_sha256']) == required_coupon_files and required_coupon_files <= files
 assert all(sha(base/name) == digest for name, digest in coupon['files_sha256'].items())
 assert set(coupon['print_meshes']) == {name for name in required_coupon_files if name.endswith('.stl')}
 assert not required_coupon_files & required
 for name, mesh in coupon['print_meshes'].items():
  triangles, dimensions = retainer_mesh((base/name).read_bytes())
  assert mesh == {'triangles':triangles, 'dimensions_xyz_mm':dimensions, 'closed_connected_shells':1}
  a,b,c = sorted(dimensions,reverse=True)
  assert (a>=5 and b>=5 and c>=5) or (a>=10 and b>=2 and c>=2)
 stations = [row['station'] for row in recess['stations']]
 printed = coupon['guide_print_parts']
 assert set(printed) == {station+suffix for station in stations for suffix in ('-base','-lid')}
 assert len(printed) <= coupon['published_connected_part_count_max'] == 10
 assert coupon['connection_square_mm'] - 2*coupon['hypothetical_surface_point_error_L2_mm'] > 1.5
 assert coupon['nominal_print_web_mm'] >= 1.0 and coupon['nominal_finished_web_mm'] == recess['minimum_nominal_web_mm']
 assert all(row['trim_recovery_volume_error_mm3'] < 1.e-6 for row in printed.values())
 assert [row['station'] for row in coupon['measurements']] == stations
 assert all(row['lateral_gap_after_allowances_mm'] >= recess['minimum_target_seat_lateral_gap_mm']
            and row['base_bondline_mm'] == .10 and min(row['tape_contact_areas_mm2']) >= .30
            for row in coupon['measurements'])
 capture_rows = coupon['wire_capture_checks']
 assert len(capture_rows) == 42 and {
     (row['PCB_thickness_mm'],row['state'],row['station']) for row in capture_rows
 } == {(variant['PCB_thickness_mm'],pose,station)
       for variant in motion['variants'] for pose in poses for station in stations}
 assert all(row['pins_captured_after_groove_shrink'] == ['1','2','3','4']
            and row['maximum_wire_overlap_with_finished_guide_mm3'] < 1.e-6 for row in capture_rows)
 relieved_dir = case_dir+'relieved-trial/'
 relieved = json.loads((base/'06-validation/m05-relieved-bottom.json').read_text())
 assert relieved['status'] == 'm05-relieved-trial-bottom-exported-and-verified'
 assert all(relieved[key] is False for key in ('selected_for_assembly','manufacturing_released','physical_verification'))
 assert relieved['source_reports_sha256'] == {name:sha(base/name) for name in (
     '06-validation/m05-usb-retainer-recess.json','06-validation/m05-usb-retainer-coupon.json')}
 relieved_files = {relieved_dir+name for name in (
     'bottom-m05-relieved-REVIEW.step','bottom-m05-relieved-REVIEW.stl',
     'wire-lengths-relieved.csv','wire-lengths-relieved.zh-CN.csv')}
 assert set(relieved['files_sha256']) == relieved_files and relieved_files <= files and not relieved_files & required
 order = m['ordinary_SLA_relieved_trial']
 assert order == ordinary_sla_trial(prototype)
 assert len(set(order['shell_STL'])) == 4 and case_dir+'bottom-m05-REVIEW.stl' not in order['shell_STL']
 assert set(order['shell_STL']) - set(prototype['shell_STL']) == {relieved_dir+'bottom-m05-relieved-REVIEW.stl'}
 assert set(order['guide_carriers_STL']) | {order['separate_floor_coupon_STL']} == (
     set(blank['carriers']) | set(coupon['print_meshes']))
 assert {(path, count) for path, count in order['guide_carriers_STL'].items()
         if path in blank['carriers']} == {(path,len(item['parts'])) for path,item in blank['carriers'].items()}
 assert sum(order['guide_carriers_STL'].values()) == len(retainers)
 assert set(order['harness_lengths']) == {name for name in relieved_files if name.endswith('.csv')}
 for suffix, table in zip(('', '.zh-CN'), order['harness_lengths']):
  check_sla_order_links(base/f'01-pcb/ordering-and-printing{suffix}.html', order, table)
 assert all(sha(base/name) == digest for name,digest in relieved['files_sha256'].items())
 mesh = relieved['mesh']
 assert mesh['connected_closed_shells'] == 1 and mesh['weld_decimal_places'] == 5
 assert retainer_mesh((base/(relieved_dir+'bottom-m05-relieved-REVIEW.stl')).read_bytes(),weld_digits=5) == (
     mesh['triangles'],mesh['dimensions_xyz_mm'])
 geometry = relieved['geometry']
 assert geometry['identical_to_crop_in_coupon_reference'] and geometry['cover_interfaces_clear'] == ['J2','J4']
 assert len(geometry['m05_holes_read_back']) == 12
 assert {row['interface'] for row in geometry['m05_holes_read_back']} == {
     'M3 lower passage','C5 insert','J2 cover insert','J4 cover insert'}
 assert math.isclose(geometry['minimum_leftover_skin_after_allowances_mm'],
                     motion['minimum_wall_to_selected_exterior_after_allowances_mm'],abs_tol=1e-5)
 assert [row['PCB_thickness_mm'] for row in relieved['variants']] == [row['PCB_thickness_mm'] for row in motion['variants']]
 for variant in relieved['variants']:
  checks = variant['guide_checks']
  assert [row['state'] for row in checks] == poses
  assert all(row['channels_checked'] == 30 and min(row['foreign_route_gap_mm_at_least'],
                 row['front_guide_to_foreign_wire_gap_mm']) >= required_gap for row in checks)
 lengths = relieved['variants'][1]['seated_free_lengths_mm']
 port_families = {'J4':'usb','J5':'power','J2':'battery'}
 for language in ('.csv','.zh-CN.csv'):
  with (base/(case_dir+'harness/wire-lengths-m05'+language)).open(newline='') as stream:
   before_header,*before = list(csv.reader(stream))
  with (base/(relieved_dir+'wire-lengths-relieved'+language)).open(newline='') as stream:
   after_header,*after = list(csv.reader(stream))
  assert before_header == after_header and len(before) == len(after) == len(lengths) == 9
  for old,new in zip(before,after):
   key = port_families[new[1]]+'.'+new[2]
   value = (lengths['usb.2']+lengths['usb.3'])/2 if key in ('usb.2','usb.3') else lengths[key]
   assert old[:6] == new[:6] and old[7] == new[7] and new[6] == f'{value:.3f}'
   delta = round(float(new[6])-float(old[6]),3)
   assert delta == relieved['seated_free_length_target_delta_from_m05_mm'][key]
   assert key.startswith('usb.') or delta == 0
 assert all(path.startswith(case_dir+'harness/wire-lengths-m05') for path in prototype['harness_lengths'])
 pack_review=json.loads((base/'06-validation/pack-source-review.json').read_text())
 assert not pack_review['physical_verification'] and not pack_review['supplier_pack_accepted']
 assert not pack_review['published_standard_pack']['yeti60_direct_replacement']
 pack_target=pack_review['yeti60_e73_m05']
 assembly=json.loads((base/'02-mechanical/assembly-spec.json').read_text())
 assert pack_target['maximum_finished_pack_envelope_mm']==assembly['battery']['full_envelope_including_growth']
 gauge = json.loads((base/'06-validation/m05-pack-gauge.json').read_text())
 assert gauge['status'] == 'cad-only-m05-inert-pack-gauge' and gauge['physical_verification'] is False
 battery = assembly['battery']
 assert gauge['pack_envelope_mm'] == battery['full_envelope_including_growth']
 expected_origin = [*battery['bounds_xy'][:2], round(battery['top_z'] - gauge['pack_envelope_mm'][2], 6)]
 assert gauge['case_origin_of_gauge_mm'] == expected_origin
 assert all(clearance > 0 for clearance in gauge['body_clearance_to_nominal_case_parts_mm'].values())
 for name in ('bottom-m05-REVIEW.step','cover-J2-REVIEW.step','cover-J4-REVIEW.step'):
  source = 'hardware/e73-hhkb-corner/mechanical/service-case-m05/' + name
  assert gauge['source_sha256'][source] == sha(base/(case_dir+name))
 assert set(gauge['files_sha256']) == {case_dir+'pack-gauge/M05-inert-pack-gauge'+ext for ext in ('.step','.stl')}
 assert all(m['files_sha256'][name] == digest for name,digest in gauge['files_sha256'].items())
 harness_spec = json.loads((base/'02-mechanical/interconnect-spec.json').read_text())
 exit_x, exit_y, exit_z = harness_spec['battery']['pack_exit_local']
 assert [lead['exit_local_mm'] for lead in gauge['lead_exits']] == [
  [exit_x, exit_y+offset, exit_z] for offset in harness_spec['battery']['lateral_offsets']]
 assert [lead['J2_pin'] for lead in gauge['lead_exits']] == ['1','2','3']
 with (base/(case_dir+'harness/wire-lengths-m05.csv')).open() as stream:
  leads=[float(row['FreeLength_mm']) for row in csv.DictReader(stream) if row['Harness']=='battery']
 assert leads==pack_target['required_free_lead_lengths_mm']
 cell_size=pack_review['reference_cell']['maximum_body_cycled_mm']
 assert [round(limit-size,3) for limit,size in zip(pack_target['maximum_finished_pack_envelope_mm'],cell_size)]==pack_target['difference_to_maximum_cycled_body_mm']
 coupon=json.loads((base/'06-validation/plate-fit-coupon.json').read_text())
 assert coupon['status']=='m01-opening-profiles-translated-and-read-back' and not coupon['physical_fit_verified']
 assert coupon['source_plate_sha256']==sha(base/'02-mechanical/steel-plate.dxf')
 assert set(coupon['files_sha256'])=={'02-mechanical/plate-fit-coupon.dxf','02-mechanical/plate-fit-coupon.svg'}
 assert all(m['files_sha256'][name]==digest for name,digest in coupon['files_sha256'].items())
 antenna_trial=json.loads((base/'06-validation/antenna-window-trial.json').read_text())
 assert not antenna_trial['physical_verification'] and not antenna_trial['selected_as_default_plate']
 assert antenna_trial['default_plate_sha256']==coupon['source_plate_sha256']
 assert antenna_trial['preserved_openings_and_mounts']==[60,28]
 assert antenna_trial['steel_over_antenna_before_after_mm2']==[39,0]
 assert set(antenna_trial['trial_sha256'])=={
  '02-mechanical/antenna-trial/M01-antenna-window-TRIAL.dxf',
  '02-mechanical/antenna-trial/M01-antenna-window-TRIAL.svg',
 }
 assert all(m['files_sha256'][name]==digest for name,digest in antenna_trial['trial_sha256'].items())
 print_fit=json.loads((base/'06-validation/m05-print-fit.json').read_text())
 assert print_fit['status']=='m05-step-readback-and-ordinary-sla-fit-screen' and not print_fit['physical_verification']
 assert set(print_fit['STEP_sha256'])=={'02-mechanical/top.step',case_dir+'bottom-m05-REVIEW.step',
                                      case_dir+'cover-J2-REVIEW.step',case_dir+'cover-J4-REVIEW.step'}
 assert all(m['files_sha256'][name]==digest for name,digest in print_fit['STEP_sha256'].items())
 closure_finish=print_fit['lower_m3_finish']
 assert len(closure_finish['locations'])==4
 assert closure_finish['worst_case_cut_model_is_one_valid_solid_with_original_bounds']
 assert min(closure_finish[key] for key in
            ('minimum_shank_gap_mm','minimum_head_gap_mm','minimum_shim_gap_mm'))>0
 assert all(site['outside_sleeve_material_fraction']==site['seat_material_fraction']==1
            for site in closure_finish['locations'])
 render=json.loads((base/'06-validation/assembly-render.json').read_text())
 harness=json.loads((base/'06-validation/m05-harness.json').read_text())
 thickness=json.loads((base/'02-mechanical/assembly-spec.json').read_text())['stack']['pcb_thickness']
 lengths=next(trial['seated_free_lengths_mm'] for trial in relieved['variants']
              if trial['PCB_thickness_mm']==thickness)
 assert render['case_revision']==prototype['revision']+'-relieved-trial'
 assert lengths.keys()==render['wire_free_lengths_mm'].keys() and len(lengths)==9
 assert all(abs(value-render['wire_free_lengths_mm'][key])<.000001 for key,value in lengths.items())
 for model in (relieved_dir+'bottom-m05-relieved-REVIEW.step',
               '02-mechanical/front-retainer-coupon/fit-reference-DO-NOT-UPLOAD.step'):
  assert render['source_sha256']['delivery/YETI60-E73/'+model]==m['files_sha256'][model]
 assert render['views']['case-underside']['objects_by_group']['covers']==2
 bench=json.loads((base/'06-validation/bench-power-plan.json').read_text())
 assert bench['pcb_sha256']==m['source_PCB_sha256'] and not bench['physical_verification']
 assert bench['charge_headroom_M05']['model_R_60C_ohm']==harness['charging_path_sensitivity']['model_R_at_temperature_ohm']
 for p in base.rglob('*'):
  if p.suffix=='.html':
   parser=Links();parser.feed(p.read_text());links=parser.links
  elif p.suffix=='.md':links=re.findall(r'\]\(([^)]+)\)',p.read_text())
  else:continue
  for link in links:
   if re.match(r'^[a-z]+:|^#',link):continue
   target=(p.parent/link.split('#')[0]).resolve()
   assert base in target.parents and target.is_file(),('Broken local delivery link',str(p.relative_to(base)),link)
 archive=base/'01-pcb/YETI60-E73-gerbers-REVIEW.zip'
 with zipfile.ZipFile(archive)as z:
  expected={p.name for p in (base/'01-pcb/gerbers').iterdir()
            if p.is_file() and p.name!='.DS_Store'}
  assert len(z.namelist())==len(expected) and set(z.namelist())==expected,'Incomplete or duplicate Gerber archive entries'
  for name in z.namelist():assert z.read(name)==(base/'01-pcb/gerbers'/name).read_bytes(),('Gerber archive mismatch',name)
 cam=json.loads((base/'06-validation/cam-ordinary.json').read_text())
 assert cam['status']=='cam-geometry-matches-native-pcb' and cam['archive_sha256']==sha(archive)
 assert cam['source_sha256']['hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb']==m['source_PCB_sha256']
 copper = cam['copper_routing']
 lands = cam['copper_lands']['land_flashes_checked_by_layer']
 assert set(copper) == set(lands) == {'F.Cu','In1.Cu','In2.Cu','B.Cu'}
 assert all(row['via_lands'] == cam['through_via_count'] for row in copper.values())
 assert all(0 <= row['maximum_arc_endpoint_delta_mm'] <= .0001 for row in copper.values())
 assert sum(lands.values()) == cam['copper_lands']['land_flashes_checked'] == 584
 assert sum(row['straight_traces'] + row['arc_traces'] for row in copper.values()) == 4722
 ipc = cam['electrical_test_netlist']
 assert ipc['format'] == 'IPC-D-356A' and ipc['physical_verification'] is False
 assert ipc['file'] == 'EC60-nRF52840.d356' and ipc['through_vias_checked'] == cam['through_via_count']
 netlist = base/'01-pcb/gerbers'/ipc['file']
 assert sha(netlist) == ipc['sha256']
 records = netlist.read_text(encoding='ascii').splitlines()
 assert all(len(line) == 80 for line in records) and records[-1].strip() == '999'
 assert sum(line.startswith(('317','327','367')) for line in records) == ipc['records_checked']
 assert 0 <= ipc['maximum_coordinate_axis_error_mm'] <= ipc['coordinate_unit_mm'] / 2
 apertures=json.loads((base/'06-validation/cam-apertures.json').read_text())
 assert apertures['archive_sha256']==cam['archive_sha256'] and apertures['source_PCB_sha256']==m['source_PCB_sha256']
 assert apertures['vias']==cam['through_via_count'] and len(apertures['layers'])==4
 assert all(not layer['nominal_intersections'] and not layer['holes_below_conservative_reserve']
            and layer['min_nominal_gap_mm']>=.229 for layer in apertures['layers'].values())
 stencil = apertures['order_stencil']
 stencil_path = base/'01-pcb/YETI60-E73-stencils-REVIEW.zip'
 assert stencil['archive_sha256'] == sha(stencil_path)
 assert stencil['omitted_reference'] == 'JP1' and len(stencil['omitted_cut_centers_PCB_mm']) == 2
 names = {f'EC60-nRF52840-{layer}' for layer in ('F_Paste.gtp', 'B_Paste.gbp', 'Edge_Cuts.gm1')}
 with zipfile.ZipFile(stencil_path) as order:
  assert len(order.namelist()) == len(names) and set(order.namelist()) == names
  assert stencil['files_sha256'] == {name: hashlib.sha256(order.read(name)).hexdigest() for name in names}
  for name in names:
   original = (base/'01-pcb/gerbers'/name).read_bytes()
   if name.endswith('B_Paste.gbp'):
    original = strip_jp1_paste(original)
   assert order.read(name) == original, ('Stencil artwork changed outside JP1', name)
 assert [stencil['sides'][side]['cuts'] for side in ('F.Paste','B.Paste')] == [43, 234]
 assert all(side['standard_thicknesses']['0.12']['cuts_below_screen'] == 0
            for side in stencil['sides'].values())
 assert sha(base/'01-pcb/source/EC60-nRF52840.kicad_pcb')==m['source_PCB_sha256']
 firmware=base/'05-firmware'
 fm=json.loads((firmware/'manifest.json').read_text())
 assert fm['source_PCB_sha256']==m['source_PCB_sha256']
 expected_images={f'releases/{variant}/yeti60-e73.{extension}'
                  for variant in ('normal','calibrator') for extension in ('hex','bin')}
 firmware_prefix='hardware/e73-hhkb-corner/firmware/'
 assert fm['published_outputs'].keys()=={firmware_prefix+image for image in expected_images}
 for image in expected_images:
  assert sha(firmware/image)==fm['published_outputs'][firmware_prefix+image],('Firmware image mismatch',image)
 with (base/'06-validation/key-acceptance.csv').open(newline='') as stream:
  key_rows = list(csv.DictReader(stream))
 expected_rows = first_article_keys(base)
 assert key_rows == [{key: str(value) for key, value in row.items()} for row in expected_rows], 'Stale key acceptance template'
 message='Delivery hashes, M05 files, local links, Gerber archive and firmware/PCB identity passed'
 print(message+(' against the source checkout' if in_checkout else ' in the offline bundle'))
 if args.require_release and (m['pending']or not m['production_approved']):
  print('Delivery remains a review draft:',', '.join(m['pending']));return 2
 return 0
if __name__=='__main__':raise SystemExit(main())
