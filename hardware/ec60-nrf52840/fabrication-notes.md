English | [Chinese](fabrication-notes.zh-CN.md)

# YETI60 special PCB fabrication requirements

U1.39 (ROW_DRV2, 343.25 / 120.35 mm) and U1.51 (SWDIO, 348.85 / 120.35 mm) each use a through via with **0.50 mm copper diameter and 0.30 mm drill inside the module pad**. The module position is retained.

**Both require resin filling, planarization and copper capping to preserve a flat solderable pad. Ordinary open vias or soldermask tenting are not substitutes.** Confirm this process with the PCB and assembly vendors; geometric DRC does not verify fabrication execution.

U5 also has a ground/thermal-pad via. Solder-paste aperture and solder-wicking control require separate assembly review.

Current CAD checks do not replace board bring-up, charging thermal tests, regulator stability and effective capacitor-value validation, daughterboard or enclosure assembly. SI/RF analysis remains deferred.

## Back-side HDI power routing

Seven filled and planarized **0.40 mm diameter / 0.20 mm laser-drill microvias** connect B.Cu to In2.Cu at U6/C45/C46 and U5/C40/C41. Fabricate them as blind microvias, not through holes. Nominal stack: front mask 0.010, F.Cu 0.035, upper dielectric 0.200, In1.Cu 0.0175, core 1.115, In2.Cu 0.0175, lower laser dielectric 0.150, B.Cu 0.035, back mask 0.010 mm. Finished envelope is 1.590 mm. Preserve the upper sensing dielectric thickness. Use ENIG and a vendor-qualified lower laser dielectric; qualify laser aspect ratio, filling, planarization, dielectric tolerance and final warpage with the fabricator. Do not substitute the original symmetric stack or open microvias.
