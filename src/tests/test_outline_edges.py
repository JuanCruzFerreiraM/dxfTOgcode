"""Tests for rect wall outline as unique edge multiset + linemerge."""

import math

from shapely.geometry import Polygon, box

from src.core.ifc.parameter_generator import (
    _collect_outline_linestrings,
    _inject_unified_rect_wall_outlines,
    _merged_wall_outline_geometry,
    _unique_outline_segments_from_polygons,
)
from src.core.gcode_generator import GcodeGenerator
from ezdxf.math import Vec3


def _outline_geom_length(geom):
    if geom is None:
        return 0.0
    if geom.geom_type == "MultiLineString":
        return sum(g.length for g in geom.geoms)
    return geom.length


def test_two_squares_fused_no_duplicate_shared_edge():
    """Dos cuadrados: arista compartida una sola vez; longitud total 7 (6 perímetro + 1 tabique)."""
    a = box(0, 0, 1, 1)
    b = box(1, 0, 2, 1)
    segs = _unique_outline_segments_from_polygons([a, b])
    assert len(segs) == 7
    g = _merged_wall_outline_geometry([a, b])
    assert g is not None and math.isclose(_outline_geom_length(g), 7.0)
    keys = {
        tuple(
            sorted(
                [
                    (round(x1, 4), round(y1, 4)),
                    (round(x2, 4), round(y2, 4)),
                ]
            )
        )
        for (x1, y1, x2, y2) in segs
    }
    assert len(keys) == len(segs)


def test_single_square_four_segments():
    a = box(0, 0, 1, 1)
    segs = _unique_outline_segments_from_polygons([a])
    assert len(segs) == 4


def test_linemerge_two_chains_or_one_for_two_adjacent_squares():
    a = box(0, 0, 1, 1)
    b = box(1, 0, 2, 1)
    merged = _merged_wall_outline_geometry([a, b])
    assert merged.geom_type in ("LineString", "MultiLineString")
    assert math.isclose(_outline_geom_length(merged), 7.0)


def test_inject_emits_outline_polyline_items():
    z = 0.0
    a = box(0, 0, 1, 1)
    b = box(1, 0, 2, 1)
    layer = {
        z: [
            {
                "polygon": a,
                "type": "IfcWall",
                "id": "w1",
                "fill_lines": [],
                "is_arc": False,
                "centroid": Vec3(0.5, 0.5, z),
                "boundary_points": [],
            },
            {
                "polygon": b,
                "type": "IfcWall",
                "id": "w2",
                "fill_lines": [],
                "is_arc": False,
                "centroid": Vec3(1.5, 0.5, z),
                "boundary_points": [],
            },
        ]
    }
    out = _inject_unified_rect_wall_outlines(layer, step=0.1)
    items = out[z]
    outlines = [i for i in items if i.get("outline_only")]
    assert len(outlines) >= 1
    assert all(o.get("outline_polyline") for o in outlines)
    assert all(o.get("outline_chain_coords") for o in outlines)
    walls = [i for i in items if "wall" in str(i.get("type") or "").lower() and not i.get("outline_only")]
    assert all(w.get("skip_outline") for w in walls)


def test_misaligned_verticals_shorter_fused_length_with_snap():
    """Borde común ~0,2 mm desfasado: con snap se elimina longitud duplicada frente al crudo."""
    a = box(0, 0, 1, 1)
    b = Polygon([(1.0002, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0002, 1.0)])
    raw = _collect_outline_linestrings([a, b], snap_mm=0)
    naive_len = sum(ls.length for ls in raw)
    fused0 = _merged_wall_outline_geometry([a, b], snap_mm=0)
    fused_snap = _merged_wall_outline_geometry([a, b], snap_mm=0.05)
    assert fused0 is not None and fused_snap is not None
    assert fused_snap.length < naive_len - 0.01
    assert fused_snap.length <= fused0.length + 1e-6


def test_t_junction_colinear_overlap_reduces_total_length():
    """T: base larga y tramo corto colineal; la fusión acorta respecto a sumar todas las aristas crudas."""
    horizontal = Polygon([(0, 0), (10, 0), (10, 1), (0, 1), (0, 0)])
    vertical = Polygon([(4, 0), (6, 0), (6, 5), (4, 5), (4, 0)])
    polys = [horizontal, vertical]
    raw = _collect_outline_linestrings(polys, snap_mm=0)
    naive_len = sum(ls.length for ls in raw)
    fused = _merged_wall_outline_geometry(polys, snap_mm=0)
    assert fused is not None
    assert fused.length < naive_len - 1.5


def test_l_shape_shared_partial_vertical_fused():
    """L: dos rectángulos comparten subtramo vertical; no se duplica longitud en ese tramo."""
    r1 = Polygon([(0, 0), (1, 0), (1, 3), (0, 3), (0, 0)])
    r2 = Polygon([(1, 0), (3, 0), (3, 1), (1, 1), (1, 0)])
    polys = [r1, r2]
    raw = _collect_outline_linestrings(polys, snap_mm=0)
    naive_len = sum(ls.length for ls in raw)
    fused = _merged_wall_outline_geometry(polys, snap_mm=0)
    assert fused is not None
    assert fused.length < naive_len - 0.5
    assert fused.length > 5.0


def test_generate_outline_from_polyline_closed_rectangle():
    g = GcodeGenerator()
    coords = [(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)]
    ent = g.generate_outline_from_polyline(coords, Vec3(0, 0, 0), 0, "outline", 0)
    g1 = [e for e in ent if e["command"] == "G1"]
    assert len(g1) == 4
