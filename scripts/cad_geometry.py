#!/usr/bin/env python3
"""Shared STEP loading, exact bounds and solid-intersection helpers."""
from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader

def load(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise ValueError(f"Cannot load STEP: {path}")
    shape = reader.OneShape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError(f"Invalid STEP shape: {path}")
    return shape


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    lower, upper = box.CornerMin(), box.CornerMax()
    return [lower.X(), lower.Y(), lower.Z(), upper.X(), upper.Y(), upper.Z()]


def intersection_volume(first, second):
    operation = BRepAlgoAPI_Common(first, second)
    operation.Build()
    if not operation.IsDone():
        raise ValueError("Case intersection operation did not complete")
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(operation.Shape(), properties)
    return abs(properties.Mass())
