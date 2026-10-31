English | [Chinese](USB-paths.zh-CN.md)

# USB path review

The current native boards need USB layout remediation. Their TVS branches are much longer than the imposed 5 mm project target. These are geometric findings, not measured USB failures or certification limits.

| Current formal board | D+ geometric path, mm | D− geometric path, mm | D+ TVS branch, mm | D− TVS branch, mm | Main-path vias, + / − |
|---|---:|---:|---:|---:|---:|
| E73 | 257.497 | 263.805 | 29.748 | 37.561 | 4 / 7 |
| Raytac | 244.103 | 246.361 | 29.748 | 37.561 | 4 / 6 |

The [contact-aware extractor](../../scripts/check_yeti60_signal_paths.py) constructs a graph from actual KiCad copper contacts. It splits tracks at intermediate branches, includes geometric pad-access and junction bridges, includes the center-to-center span of R30/R31, and derives via lengths from the declared four-layer stack. Arcs use chords with at most 0.002 mm deviation. A shortest path runs from J1 through its series link to the module USB land; a second shortest path runs from the TVS I/O land to any node on that main path. Detailed ordered paths and source hashes are in [the generated report](../audit/USB-signal-paths.json).

```text
Main geometric length = sum(trace centerlines + contact bridges
                            + via layer spans + series-package spans)
TVS branch length = shortest geometric path(TVS I/O, main-path node set)
```

This does not solve current distribution within pads, differential impedance, propagation delay, pair coupling or receiver eye opening. It excludes C5, the cable, connector internals and module-internal routing. A geometric length difference must not be described as measured electrical skew. Native continuity and descriptor current do not establish USB signal integrity.

[Nexperia's PRTR5V0U2X data sheet](https://assets.nexperia.com/documents/data-sheet/PRTR5V0U2X.pdf), section 10, recommends placement close to the input connector, short protected-line paths and short ground return paths. The imposed 5 mm branch target is our engineering screening choice; Nexperia does not specify that numeric limit. Repair must shorten both data branches, provide a local ground return, remove old stubs, and preserve the fused supply connection. A possible I/O-channel reassignment must be reflected in the schematic, native PCB and saved netlist together.

After repair, rerun native DRC, ordinary-process and connectivity checks, this extraction and the mechanical checks. Qualify the complete cable/C5/PCB path and USB enumeration/suspend behavior on hardware before final acceptance. The acceptance checker derives separate branch-layout and USB-SI gates; shortening a branch cannot close USB-SI qualification.

Reproduce with KiCad Python: `scripts/check_yeti60_signal_paths.py`, then `tests/audit/test_signal_paths.py`. The regression fixture includes an intermediate T junction; counting only primitive endpoints would report the wrong branch length.
