English | [简体中文](README.zh-CN.md)

# YETI60 assembled renders

These are **conditional assembly studies**, not production approval. The original FELK60 shells, current PCB finished-thickness envelope and audited 1.2 mm HHKB plate use the same coordinates as the [assembly check](../../docs/audit/yeti60-assembly.json). The 4.6 mm PCB-to-plate gap is provisional. Switches, stems, keycaps, component body envelopes, material colors and battery volume are illustrative.

![Assembled](assembled.png)

![Exploded](exploded.png)

![Battery-space budget](battery-space.png)

The green volume is an unselected maximum pack-space envelope, not a battery model or procurement recommendation. Its thickness depends on the eventual switch/dome stack.

`render-manifest.json` records source geometry hashes, the assembly-report hash, render recipe and output hashes. The original 7° wedge is rotated as one scene to present the keyboard on a level desk; assembly measurements remain in source coordinates.

Rebuild using the pinned CAD runtime after refreshing mechanical metadata:

```sh
python scripts/check_yeti60_assembly.py
python scripts/render_yeti60_assembly.py
```

Requires `requirements-audit.txt`, Pillow, KiCad and the metadata produced by KiCad Python `scripts/export_yeti60_mechanical_metadata.py`. Surface copper artwork is omitted from this geometry study; detailed copper appearance is shown in the separate native KiCad PCB renders. Temporary geometry and frames stay in ignored `.assembly-work/`. See the [full review](../../docs/audit/yeti60-comprehensive-review.md) before interpreting fit.
