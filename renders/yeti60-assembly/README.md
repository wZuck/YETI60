# YETI60 physical studio renders

English | [Chinese](README.zh-CN.md)

These images use Blender Cycles path tracing, softbox lighting, fine resin/PBT surface roughness, rounded sculpted keycaps and contact shadows. Images contain no overlaid prose. The case is generated directly from the current FELK60-derived P2 STEP solids, with **no case scaling, bevel modifiers, silhouette editing or relative movement of the two shells**.

![Assembled front view](assembled.png)

![Assembled rear view](rear.png)

![Exploded assembly study](exploded.png)

![Default pack envelope](battery-space.png)

## Dimensions and scope

The combined case envelope in the original CAD coordinate frame is **325.700 × 125.200 × 31.190 mm**. This is a bounding box in that frame, not a claim about desk-projected depth or overall height including keycaps. The entire assembly receives one rigid 7° rotation to place the existing wedge on the table. Meshes use a 0.015 mm linear deflection; mesh bounding coordinates are checked against the source BRep within 0.02 mm. Millimetres are converted uniformly to metres for the renderer.

[Geometry verification](../../docs/audit/yeti60-render-geometry.json) and [render manifest](render-manifest.json) record original source hashes, case dimensions, render recipe, tessellation and image hashes. The 1.2 mm plate and current PCB use the same coordinates as the [assembly check](../../docs/audit/yeti60-assembly.json).

**Appearance realism does not qualify unspecified parts.** Resin colour and finish, sculpted keycaps, legends, switch housings/stems and component envelopes are illustrative. The provisional 4.6 mm PCB-to-plate gap still requires an actual dome/fastener stack. The green block is the selected custom 1600 mAh full-pack envelope (85×43×4.8 mm); supplier drawings and thermal protection remain unqualified. The rear opening remains the original source geometry; a final USB daughterboard, mating plug and cable are not represented as validated parts.

## Rebuild

Refresh metadata with KiCad Python `scripts/export_yeti60_mechanical_metadata.py`. Use the pinned CAD runtime for the first two commands, then the separate Blender runtime:

```sh
python scripts/check_yeti60_assembly.py
python scripts/export_yeti60_render_meshes.py
uv run --python 3.11 --with-requirements requirements-render.txt python scripts/render_yeti60_assembly.py
```

`--preview --view assembled` produces a low-resolution study in ignored `.assembly-work/`. Final images are 2600 × 1734 pixels with 256 maximum Cycles samples and denoising. Studio setup follows the [Cycles renderer](https://www.blender.org/features/rendering/) and [Blender material API](https://docs.blender.org/api/5.0/bpy.types.Material.html). See the [full review](../../docs/audit/yeti60-comprehensive-review.md) for unresolved hardware requirements.
