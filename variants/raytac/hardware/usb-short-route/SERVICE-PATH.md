English | [Chinese](SERVICE-PATH.zh-CN.md)

# Service-path finding: right PCB wing

**Enclosed assembly is on hold. Do not force a vertical insertion or removal.** Installed-position clearance and a complete exploded image do not establish an assembly path. The [reproducible diagnostic](../../scripts/probe_usb_short_service.py) and [pose results](audit/service-probe.json) check the nominal PCB and plate against the current candidate bottom.

The PCB is clear at its installed position. Raising it vertically by 1 mm produces about 25.10 mm³ of overlap; at 3 mm the overlap is about 99.26 mm³. At that pose the common-solid bounds are approximately X 357.663–361.200, Y −132.000–−114.500, Z 1.000–2.606 mm in case coordinates. The right RF wing is captured beneath an internal step. The plate itself is clear at the sampled poses. A clear 8 mm pose does not make the intervening movement possible.

These are discrete nominal rigid-body poses, not a continuous collision sweep. They do not qualify cables, mating connectors, tools, tolerances or a tilted trajectory. Current instructions and rendered explosions must be read as component identification and installed routing, not permission to perform an obstructed lift.

## Repair and acceptance work

1. Evaluate a right-wing-first tilted insertion and its reverse. Include the plate, fitted parts, every mating plug and PCB-mounted guides. A collision-free isolated board pose alone is insufficient.
2. Establish how the battery and USB guide retention is released before movement. Check wire length, minimum bend radius, slack and an actual tool corridor; do not assume the leads stretch or that the power-switch port provides cable access.
3. If a qualified motion cannot retain the existing internal step, design a limited internal relief. Preserve the FELK60 exterior and verify the actual plate-bearing surfaces, insert seats and remaining wall thickness before releasing revised case files.
4. Rebuild CAD reports, assembly instructions and renders for the chosen repair, then check the tolerance cases and a physical first article. The current manufacturing hold remains until the relevant design requirements are resolved.

The selected F1 and native electrical/firmware checks are independent of this newly measured mechanical obstruction. [Candidate entry](README.md) · [Assembly illustrations](ASSEMBLY.md)
