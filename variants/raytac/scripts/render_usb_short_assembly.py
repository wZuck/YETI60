#!/usr/bin/env python3
"""Render the isolated candidate with the existing studio recipe.

The legacy renderer and publications stay byte-for-byte unchanged. Exact,
asserted adaptations are recorded with both source recipes in the manifest.
Run with the Blender Python environment after export_usb_short_assembly.py.
"""
import hashlib
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/render_yeti60_assembly.py'
GENERATED = ROOT / '.assembly-work/usb-short-studio.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adapt(text, before, after, count=1):
    assert text.count(before) == count, ('Studio source changed; review adaptation', before)
    return text.replace(before, after)


def build_source():
    text = SOURCE.read_text()
    replacements = [
        ("OUT = ROOT/'renders/yeti60-assembly'; OUT.mkdir(exist_ok=True)",
         "OUT = ROOT/'hardware/usb-short-route/assembly'; OUT.mkdir(exist_ok=True)", 1),
        ("WORK = ROOT/'.assembly-work'", "WORK = ROOT/'.assembly-work/usb-short-assembly'", 1),
        ("REPORT = ROOT/'docs/audit/yeti60-assembly.json'", "REPORT = ROOT/'hardware/usb-short-route/audit/assembly.json'", 1),
        ("ROOT/'scripts/export_yeti60_render_meshes.py'", "ROOT/'scripts/export_usb_short_assembly.py'", 2),
        ("ROOT/'docs/audit/yeti60-interconnects.json'", "ROOT/'hardware/usb-short-route/audit/closed-assembly.json'", 1),
        ("ROOT/'docs/audit/yeti60-bom.json'", "ROOT/'hardware/usb-short-route/audit/assembly-bom.json'", 2),
        ("'electronics' if part['name']=='main-sh' else part['group']", "part['group']", 1),
        ("p['ref']=='J1'", "p['ref'] in ['J1','J4','J5']", 1),
        ("else:box(p['ref']+' / height envelope',p['bounds_case_mm'],mat,'electronics',.12)",
         "else:box(p['ref']+' / part body or clearance envelope',p.get('render_body_bounds_case_mm',p['bounds_case_mm']),mat,'electronics',.02 if p['ref']=='F1' else .12)", 1),
        ("'yellow':(.65,.4,.005)", "'yellow':(.65,.4,.005),'amber':(.53,.24,.025)", 1),
        ("Seven continuous round wires, complete conservative mating envelopes, conformal guides and native C5 CAD; supplier lead-exit datums pending",
         "Nine continuous round wires, five conservative mating envelopes, 16 removable guides, 12 retention films, three native SH headers, J2 body envelope and native C5 CAD; supplier lead-exit datums pending", 1),
        ("name+' / unmodified source CAD'", "name+' / controlled source CAD'", 1),
    ]
    for before, after, count in replacements:
        text = adapt(text, before, after, count)
    surface = ("import sys\nsys.path.insert(0,str(ROOT/'scripts'))\n"
               "mesh_receipt_path=ROOT/'hardware/usb-short-route/audit/assembly-meshes.json'\n"
               "mesh_receipt=json.loads(mesh_receipt_path.read_text());mesh_receipt_hash=sha(mesh_receipt_path)\n"
               "assert sha(MESH)==mesh_receipt['mesh_payload_sha256'],'Changed candidate mesh payload'\n"
               "from usb_short_render_surfaces import apply as apply_surfaces\n"
               "surface_hash=apply_surfaces(ROOT,bpy.data.objects['pcb / controlled source CAD'],CX,CY,data['nominal_stack'])\n\n")
    text = adapt(text, 'def box(name,bb,mat,group,bevel=0):', surface+'def box(name,bb,mat,group,bevel=0):')
    marker_outputs = '    # Preserve evidence for untouched views; never stamp them as freshly rendered.'
    text = adapt(text, marker_outputs,
        "        rendered_outputs[path.name]['mesh_receipt_sha256'] = mesh_receipt_hash\n"
        "        rendered_outputs[path.name]['surface_report_sha256'] = surface_hash\n"
        "        rendered_outputs[path.name]['guides_report_sha256'] = meshdata['guides_report_sha256']\n" + marker_outputs)
    marker = "    (OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2)+'\\n')"
    # Generated-script hash is already the per-output recipe. Preserve the two
    # maintained sources too, so an unchanged old image cannot be restamped.
    addition = ("    assert sha(mesh_receipt_path)==mesh_receipt_hash,'Mesh receipt changed during rendering'\n"
        "    manifest['mesh_receipt_sha256'] = mesh_receipt_hash\n"
        "    manifest['surface_report_sha256'] = surface_hash\n"
        "    manifest['unavailable_native_models'] = meshdata['unavailable_native_models']\n"
        "    manifest['source_recipe_sha256'] = " + repr({
        str(SOURCE.relative_to(ROOT)): sha(SOURCE),
        str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__)),
        'scripts/usb_short_render_surfaces.py': sha(ROOT/'scripts/usb_short_render_surfaces.py'),
    }) + "\n    manifest['guides_report_sha256'] = meshdata['guides_report_sha256']\n")
    text = adapt(text, marker, addition + marker)
    return text


def main():
    text = build_source()
    GENERATED.write_text(text)
    runpy.run_path(str(GENERATED), run_name='__main__')


if __name__ == '__main__':
    main()
