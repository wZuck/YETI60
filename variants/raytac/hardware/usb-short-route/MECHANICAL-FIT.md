English | [Chinese](MECHANICAL-FIT.zh-CN.md)

# C04 plate, switch-floor relief and gasket installation

Use this mechanical revision with the current Raytac candidate. The original FELK60 exterior, upper shell, key centers, stabilizer openings and 28 installed mounting positions are retained. The plate's **outer perimeter is inset by 0.40 mm**; its interior cuts are unchanged. The minimum nominal metal web to an opening is 1.7498 mm before cutting tolerances; this dimension is not a strength qualification. An additional internal pocket clears SW100 in the lower shell.

The bounded **plate and switch** geometric checks pass at the dimensional limits below. Complete keyboard fit, foam behavior, connected plug service paths and physical electrical operation remain open. Limits are requirements to inspect on finished parts, not promises about an arbitrary resin print or supplier component.

## Files and materials

| Item | Quantity | Current file or specification |
|---|---:|---|
| C04 NiZ / plate-stabilizer steel plate | 1 | [Machining DXF](mechanical/yeti60-niz-pm1-c04.dxf), [installed STEP](mechanical/yeti60-niz-pm1-c04.step); 304 stainless, nominal 1.6 mm, finished 1.55–1.60 mm; **28 M2 × 0.4 tapped axes**; deburr without changing openings |
| Lower shell | 1 | [Repaired STEP](mechanical/yeti60-bottom-short-usb.step), [print STL](mechanical/yeti60-bottom-short-usb.stl); includes rear USB, RF-wing and new switch reliefs |
| Upper shell | 1 | [Original generated upper shell](../../mechanical/generated/yeti60-top.step); plate inset supplies clearance to both shells |
| Lower gasket strips | 4 | Each 33 × 3 mm, nominal 2.0 mm stock; nominal compressed gap 1.0162 mm |
| Upper gasket strips | 4 | Each 33 × 3 mm, nominal 1.2 mm stock; nominal compressed gap 0.5838 mm |
| Gasket stock allowance | 2 pieces | One ≥150 × 10 mm piece of each thickness is sufficient for four strips; existing larger sheets can be used |

This C04 DXF supersedes the original plate perimeter for the candidate; send the **whole DXF**, preserving all openings. It is a steel plate, not an additional PCB. Use the unchanged [current PCB fabrication package](FIRST-ARTICLE.md). Existing NiZ, stabilizer, keycap and fastener purchasing requirements still apply; H26 remains unused. Do not move a switch or drill new PCB stabilizer holes.

The 28 DXF circles are **Ø1.623 mm machining datums for M2 × 0.4 threads**, not final clearance-hole instructions. Order cutting **and tapping**, with the supplier choosing the proper pilot/finish process. The standoffs' 1.0 mm upper M2 studs engage these plate threads; there are no upper nuts. A laser-only plate with unfinished pilot holes cannot be assembled this way. Tap, clean and deburr before bringing electronics nearby; follow the [existing fastener/plate machining instructions](../../docs/build/key-mechanism.md).

## Dimensional acceptance limits

| Quantity | Limit |
|---|---|
| Plate outer-profile error | ≤0.10 mm radial in XY at every point |
| Installed plate XY position error | ≤0.10 mm radial at every point, including translation, rotation and deformation together |
| Installed plate surface Z error | ≤0.10 mm at both surfaces, including actual thickness, gasket setting and deformation together |
| Finished case coordinate error | ≤0.15 mm in each axis; the calculation conservatively uses a 0.259808 mm spatial bound |
| Finished mainboard thickness | 1.44–1.76 mm, unchanged ordinary JLC acceptance range |
| Installed PCB XY position error | ≤0.25 mm in each axis, including registration to the plate |
| SW100 installed height | ≤3.60 mm below the local PCB back surface, including solder and actuator |
| SW100 additional XY envelope error | ≤0.10 mm in each axis beyond the declared courtyard envelope |
| Additional mounted-PCB downward bow at SW100 | ≤0.15 mm, measured after fastening, separate from thickness and spacer/film variation |
| Gasket cut and installed XY error | ≤0.15 mm in each axis, combined |

The switch height limit is a project inspection envelope. Its nominal manufacturer drawing alone does not certify installed height. A PCB's free-state bow specification does not prove its mounted bow satisfies this limit.

## Calculation and evidence

The checker expands the actual C04 outer polygon by **0.10 + 0.10 = 0.20 mm** in XY and by **±0.10 mm in Z**. Its solid includes internal openings conservatively and covers every intermediate permitted point. The lower-shell extraction check extrudes that entire envelope through **22 mm**. The circular XY expansion is circumscribed to cover polygonal arc approximation.

For each measured envelope gap, `remaining gap = envelope-to-case distance − sqrt(3) × 0.15 − 0.002 mm`. The final term is a numerical/geometry guard; the required residual is **0.15 mm**. This is an arithmetic worst-case bound, not a statistical average. The plate check retains approximately **0.188 mm** after these allowances.

The switch envelope includes ordinary PCB downward growth `1.76 − 1.6062 = 0.1538 mm`, shoulder 0.03, film 0.02, installed plate Z 0.10, mounted bow 0.15 and installed-height increase `3.60 − 3.50 = 0.10 mm`. XY includes PCB registration and switch placement. The pocket spans X **104.975–119.025**, Y **−127.525–−114.725**, Z **−6.71–−5.40 mm**, with 0.5 mm corner radius. It preserves the external access hole and original exterior. Skin and screw/insert support checks include the new cut.

[Exact current fit results](audit/tolerance-fit.json) · [Plate cut parity and minimum metal web](audit/plate-build.json) · [Case and insert checks](audit/closed-assembly.json) · [Original failing baseline](TOLERANCES.md)

## Installing the eight gaskets

Use these case-coordinate centers for both layers; strips run along X:

| Position | X / mm | Y / mm |
|---|---:|---:|
| Front left | 102.5877 | −201.7000 |
| Front right | 326.5877 | −201.7000 |
| Rear left | 128.5877 | −100.2500 |
| Rear right | 300.0877 | −100.2500 |

The checker verifies all eight strips remain on case bearing faces and plate metal after the specified XY allowances. Fit the lower strips to the four lower ledges and the upper strips to the matching upper ledges. Keep adhesive within the footprint and include its thickness in stack measurement. No strip may bridge a key opening or screw hole.

Inspect actual case ledge heights, foam/adhesive thickness and the installed plate surfaces. With the stated case and plate Z limits, geometric gaps can range approximately **0.7662–1.2662 mm below** and **0.3338–0.8338 mm above**. The specified stock thicknesses are nominal starting materials; these intervals do **not** qualify an arbitrary foam's compression force, creep or adhesive. Verify suitable material/compression on a first article and adjust measured gasket thickness if necessary while maintaining the installed plate limits. Do not force the shells closed to achieve the nominal height.

Material research: the [Rogers product-availability brochure](https://www.rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/poron/english/product-availability/17-082-poron-polyurethanes-product-availability-brochure.pdf) lists different thicknesses and densities within PORON 4701-30. For example, supported `4701-30-25047-04 P` is 1.19 mm / 400 kg/m³, while `4701-30-20064-04 P` is 1.63 mm / 320 kg/m³. A generic “PORON 1.2 mm” listing does not establish the same material or force. The [manufacturer data sheet](https://rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/poron/english/data-sheets/17-006-poron-4701-30-very-soft.pdf) specifies compression-force measurements at 25% deflection; those values cannot be reused as force at 50–75% compression. These are reference candidates, not a frozen gasket MPN. Obtain the actual grade, total thickness including carrier/adhesive and full compression curve before foam acceptance.


The current [complete explosion](assembly/exploded.png) includes eight separate installed gasket strips. Follow the [candidate assembly sequence](ASSEMBLY.md), using this plate and these gaskets in place of the original perimeter/stock-tray illustration.

The installed-position bounds must also remain satisfied after key operation and handling. This geometric proof does not establish that gasket friction or adhesive retains that position; centering and retention acceptance remains open.
