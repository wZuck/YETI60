English | [Chinese](board-markings.zh-CN.md)

# PCB marking cleanup

Only the central `YETI60 / EC60 by Cipulot` nonfunctional branding line was removed. The remaining revision and rear-USB marking is retained. All hole guides, references, pin numbers, polarity/assembly labels and fabrication annotations remain exactly as saved. Project attribution is retained in repository documentation.

The large circular and overlapping shapes are connected EC electrodes and ground shielding. They are functional copper and were retained. Removing them would change sensing performance and violate the instruction to keep the current functional design.

`python3 scripts/check_yeti60_board_markings.py` compares the full parsed KiCad tree against fixed commit `27894700dd021e40957199dce596f0e5130db60c`, permitting exactly that one text deletion. The [machine-readable result](../audit/yeti60-board-markings.json) records the current PCB hash. Strict DRC and connectivity regression were rerun. Old PCB/assembly render images remain historical until their source manifests are regenerated, as declared at the root checkpoint.
