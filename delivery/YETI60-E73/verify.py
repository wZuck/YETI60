#!/usr/bin/env python3
"""Verify an offline E73 bundle, or verify the bundle and source checkout together."""
import argparse,csv,hashlib,json,re,zipfile
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


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
 required=set(prototype['shell_STL']+list(prototype['retainer_STL'].values())+
              prototype['harness_lengths']+prototype['assembly_views'])
 assert required<=files
 case_dir='02-mechanical/service-case-m05/'
 for name in ('BAT-R1','BAT-R2'):assert prototype['retainer_STL'][name]==case_dir+'harness/'+name+'-M05.stl'
 for name in ('bottom-m05','cover-J2','cover-J4'):assert case_dir+name+'-REVIEW.stl' in prototype['shell_STL']
 assert all(path.startswith(case_dir+'harness/wire-lengths-m05') for path in prototype['harness_lengths'])
 pack_review=json.loads((base/'06-validation/pack-source-review.json').read_text())
 assert not pack_review['physical_verification'] and not pack_review['supplier_pack_accepted']
 assert not pack_review['published_standard_pack']['yeti60_direct_replacement']
 pack_target=pack_review['yeti60_e73_m05']
 assembly=json.loads((base/'02-mechanical/assembly-spec.json').read_text())
 assert pack_target['maximum_finished_pack_envelope_mm']==assembly['battery']['full_envelope_including_growth']
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
 lengths=harness['trial_variants'][0]['seated_free_lengths_mm']
 assert render['case_revision']==prototype['revision'] and len(lengths)==9
 assert all(abs(value-render['wire_free_lengths_mm'][key])<.000001 for key,value in lengths.items())
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
