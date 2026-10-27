English | [Chinese](README.zh-CN.md)

# Upstream EC60 manufacturing-reference correction

`POS-EC60.corrected.csv` applies to the **unmodified upstream EC60 PCB**, not the new Bluetooth PCB or interface prototype.

The original placement file labels the OPA350 as U1, duplicating U1 and omitting U3. The corrected copy identifies the unique matching position, orientation, footprint, value and board side and restores U3, then checks all original BOM references.

This is not a production approval. Upstream DRC, complete copper/mask/paste Gerber parity, exact purchasing specifications and the new PCB remain separate verification scopes. Do not mix this placement file with a different revision's BOM or Gerbers.

Rebuild with `python3 scripts/check_manufacturing_reference.py` after refreshing upstream PCB metadata using KiCad Python `scripts/extract_pcb_metadata.py`. Evidence: `docs/audit/manufacturing-reference.json`.
