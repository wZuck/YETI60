#!/usr/bin/env python3
"""Compare flashed Gerber X2 copper lands to native KiCad pad sites."""

from collections import Counter
import re

import pcbnew as pcb


PAD_FUNCTIONS = {"ComponentPad", "HeatsinkPad", "SMDPad"}
FLASH = re.compile(r"X(-?\d+)Y(-?\d+)D03\*")
APERTURE_DEFINITION = re.compile(r"%ADD(\d+).+\*%")
APERTURE_SELECTION = re.compile(r"D(\d+)\*")
ESCAPE = re.compile(r"\\u([\da-fA-F]{4})")


def attribute_value(value):
    return ESCAPE.sub(lambda match: chr(int(match[1], 16)), value)


def read_land_flashes(artwork, *, inner):
    """Read sites from full-coordinate D03 flashes and their X2 attributes."""
    apertures = {}
    objects = {}
    function = None
    selected = None
    lands = Counter()

    for line in artwork.splitlines():
        if line.startswith("%TA.AperFunction,"):
            function = line[17:-2].split(",")[0]
        elif match := APERTURE_DEFINITION.fullmatch(line):
            apertures[match[1]] = function
        elif match := APERTURE_SELECTION.fullmatch(line):
            selected = match[1]
        elif line.startswith("%TO."):
            key, *values = line[4:-2].split(",")
            objects[key] = [attribute_value(value) for value in values]
        elif line == "%TD*%":
            objects.clear()
            function = None
        elif line.startswith("%TD."):
            objects.pop(line[4:-2], None)
        elif line.endswith("D03*") and apertures.get(selected) in PAD_FUNCTIONS:
            flash = FLASH.fullmatch(line)
            assert flash, ("Unexpected coordinate format for copper pad flash", line)
            if inner:
                assert apertures[selected] == "ComponentPad" and "P" not in objects
                # KiCad exports plated component lands on inner layers with
                # the component reference only. Position distinguishes its lands.
                ref, = objects.get("C", [""])
                pin = ""
            else:
                ref, pin = objects.get("P", ["", ""])[:2]
            net, = objects.get("N", [""])
            if net == "N/C":
                net = ""
            lands[ref, pin, net, int(flash[1]), int(flash[2])] += 1
    return lands


def native_land_sites(board, layer, *, inner):
    return Counter(
        (
            footprint.GetReference(),
            "" if inner else pad.GetNumber(),
            pad.GetNetname(),
            pad.GetPosition().x,
            -pad.GetPosition().y,
        )
        for footprint in board.GetFootprints()
        for pad in footprint.Pads()
        if pad.IsOnLayer(layer) and pad.GetAttribute() != pcb.PAD_ATTRIB_NPTH
    )


def check_copper_lands(board, artwork_by_layer):
    """Check sites by side, reference, pad number where exported, net and XY.

    Artwork maps the four KiCad copper layer IDs to original Gerber text.
    Polygon-macro flashes are checked at their origins, like standard flashes.
    Copper overlap, aperture contours and standalone regions are separate checks.
    """
    required = {pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu}
    assert set(artwork_by_layer) == required
    counts = {}
    for layer, artwork in artwork_by_layer.items():
        layer_name = board.GetLayerName(layer)
        inner = layer in {pcb.In1_Cu, pcb.In2_Cu}
        expected = native_land_sites(board, layer, inner=inner)
        actual = read_land_flashes(artwork, inner=inner)
        assert actual == expected, (
            "Copper land flash mismatch",
            layer_name,
            "missing", list((expected - actual).items())[:5],
            "unexpected", list((actual - expected).items())[:5],
        )
        counts[layer_name] = sum(actual.values())
    return {
        "comparison": "X2 flashed lands matched by copper layer, reference, pin where exported, net and origin",
        "land_flashes_checked_by_layer": counts,
        "land_flashes_checked": sum(counts.values()),
    }
