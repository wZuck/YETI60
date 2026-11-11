English | [Chinese](WIRE-QUALIFICATION.zh-CN.md)

# Wire qualification: exact part still open

The 4 mm bend requirement on this page concerns enclosed harnesses. A case-free first article may use loose loops and the [first-article entry](FIRST-ARTICLE.md) specification of at least 10 mm design radius with supplier-supported wire limits. This does not qualify the enclosed wire or the complete USB link.

The closed routes require AWG28 stranded copper, a common SH insulation OD of 0.5–0.8 mm and a permitted static bend radius of 4 mm or less. These are design requirements, not a purchased wire's certified properties. See [route geometry](CLOSED-CASE.md) and the [feed calculation](POWER-FEED.md).

## Investigated part

The [Alpha Wire 2842/19 manufacturer specification](https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=2842/19), pages 2 and 5, lists AWG28, 19/40 silver-plated copper, PTFE OD 0.027 ±0.002 inch, nominal DCR 58 Ω/1000 ft at 20°C, and bend radius ten times diameter.

```text
maximum OD = 0.029 × 25.4 = 0.7366 mm
nominal DCR = 58 / 304.8 = 0.19029 Ω/m
required bend radius at maximum OD = 10 × 0.7366 = 7.366 mm
```

**Reject this part for the current 4 mm closed-case route.** Its diameter fits, but its published bending requirement does not. Nominal resistance also cannot prove a maximum-resistance procurement limit or hot performance. This is single-conductor wire; it does not establish the impedance of an assembled USB pair.

## Evidence required before selection

Obtain the exact wire construction, maximum OD, static bending allowance at the specified temperature, resistance versus temperature, and compatibility with the selected JST contact and crimp tooling. Qualify a finished sample for crimp retention, formed-route springback, insulation damage and measured loop resistance. Qualify the complete USB link separately. If no supplier-supported wire meets the 4 mm route, revise the guides and routes for the selected wire and repeat clearance, free-length, voltage-drop and service-path checks.

No wire purchase is approved by this note. Loose open-bench lengths do not qualify enclosure assembly. [Candidate entry](README.md) · [Assembly guide](ASSEMBLY.md)
