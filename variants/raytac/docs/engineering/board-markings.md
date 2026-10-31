English | [Chinese](board-markings.zh-CN.md)

# PCB marking cleanup

Only the central `YETI60 / EC60 by Cipulot` nonfunctional branding line was removed. The remaining revision and rear-USB marking is retained. All hole guides, references, pin numbers, polarity/assembly labels and fabrication annotations remain exactly as saved. Project attribution is retained in repository documentation.

The large circular and overlapping shapes are connected EC electrodes and ground shielding. They are functional copper and were retained. Removing them would change sensing performance and violate the instruction to keep the current functional design.

`python3 scripts/check_yeti60_board_markings.py` verifies that historical cleanup commit `03c2be3` differs from `2789470` by that single deletion. Current P2 also has intentional charger changes, so it does not claim all copper is unchanged. The check retains all standalone guidance and existing reference identifiers; `check_single_nrf_pcb.py` separately verifies electrode/outline/mounting geometry. The [machine report](../audit/yeti60-board-markings.json) records the current board hash.
