English | [Chinese](fabrication-notes.zh-CN.md)

# YETI60 special PCB fabrication requirements

U1.39 (ROW_DRV2, 343.25 / 120.35 mm) and U1.51 (SWDIO, 348.85 / 120.35 mm) each use a through via with **0.50 mm copper diameter and 0.30 mm drill inside the module pad**. The module position is retained.

**Both require resin filling, planarization and copper capping to preserve a flat solderable pad. Ordinary open vias or soldermask tenting are not substitutes.** Confirm this process with the PCB and assembly vendors; geometric DRC does not verify fabrication execution.

U5 also has a ground/thermal-pad via. Solder-paste aperture and solder-wicking control require separate assembly review.

Current CAD checks do not replace board bring-up, charging thermal tests, regulator stability and effective capacitor-value validation, daughterboard or enclosure assembly. SI/RF analysis remains deferred.
