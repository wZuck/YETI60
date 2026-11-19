English | [Chinese](BUILD.zh-CN.md)

# YETI60 E73: current build and review entry

The selected design is **E73 CORNER-06**, with the module on the front in the unused lower-right HHKB corner. Open the [current KiCad project](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pro) and [PCB](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb). [Revision and project-file checks](docs/build/e73-project-files.md) explain how to distinguish the historical candidates.

**Engineering review; order release remains open.** Native routing/reference checks and matching firmware builds passed. The nine-conductor route, 16 rigid retainers and 17 film pieces passed bounded static checks. Retainer manufacturing/service, closed-case installation and withdrawal, supplier pack, factory CAM and first-article charging review and physical acceptance remain open. A clean DRC or a verified file manifest does not close those gates.

The already-made **UDB-C-JSH C5 daughterboard stays unchanged**. No replacement daughterboard PCB is needed.

| Task | Current controlled entry |
|---|---|
| All delivery assets in one folder | [Start here](delivery/YETI60-E73/START-HERE.md), [offline web index](delivery/YETI60-E73/index.html) |
| PCB options, files and printing requirements | [PCB and mechanical manufacturing](docs/build/e73-ordering-printing.md) |
| Current electrical and mechanical evidence | [Corner review and reproduction commands](docs/engineering/e73-hhkb-corner.md) |
| Full materials, packages, counts and inventory | [Preparation list](README.md#complete-materials-for-one-keyboard), [75-part mainboard purchase CSV](hardware/e73-hhkb-corner/mainboard-purchase.csv) |
| Start from a blank PCB | [12-step soldering and bench guide](docs/assembly/e73-corner/soldering.md), [illustrated web guide](docs/assembly/e73-corner/soldering.html) |
| Cables, exact pin connections and free lengths | [Nine-conductor harness](docs/engineering/e73-corner-harness.md) |
| Retainer files, placement and film templates | [16 rigid parts and 17 film pieces](docs/engineering/e73-retention.md) |
| Assembled, exploded, case interior and PCB underside views | [Assembly views and dry-fit stages](docs/build/e73-assembly-views.md) |
| NiZ housings/sliders and steel-plate stabilizers | [Mechanism and assembly](docs/build/key-mechanism.md); 60 keys, three stabilizer pairs, 28 mounting sets, H26 unused |
| Battery supplier confirmation | [Protected 1S pack specification](docs/engineering/battery-pack-specification.md) |
| Build, flash and calibrate matching firmware | [Current corner firmware](docs/testing/e73-corner-firmware.md) |
| File-integrity and source consistency | `python3 scripts/check_e73_delivery.py`; `--require-release` must still fail while the listed gates remain open |

The mainboard uses ordinary 4-layer FR-4, nominal 1.6 mm, mechanical through vias and both-side tenting. No HDI, filled/capped vias or daughterboard redesign is required. The current review CAM archive is indexed in the delivery folder. It is not a released factory order.

E73 has five connected bottom lands: soldering only the module edges is insufficient. Both paste sides, staged inspection and a suitable reflow process are required. A shell is not required to begin current-limited power, USB enumeration, SWD, raw sensing or BLE bench tests; the completed NiZ/plate mechanism is needed for meaningful 60-key calibration. Actual charging temperatures, USB data, BLE range, EC interference and resin/adhesive fit remain prototype tests.

The old `hardware/ec60-nrf52840`, intermediate `hardware/e73-usb-repair`, old complete renders and legacy `scripts/run_e73_review.py` / `scripts/run_audit.py` target other revisions. They are provenance references, not acceptance for this corner board. Raytac assets are under [their separate entry](variants/raytac/BUILD.md).
