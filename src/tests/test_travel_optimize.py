"""Tests: métricas G0, encadenado de relleno y optimización de secuencia de islas."""

import time

from ezdxf.math import Vec3
from shapely.geometry import LineString, Point, Polygon

from src.core.gcode_generator import GcodeGenerator
from src.utils.fill_chain import chain_fill_linestrings
from src.utils.path_optimizer import (
    RouteOptimizeOptions,
    find_optimal_polygon_sequence,
    optimize_layer_traversal,
)
from src.utils.travel_metrics import planar_travel_stats


def test_planar_travel_stats_counts_jumps():
    """Tres segmentos desconectados implican dos saltos desde el origen."""
    entities = [
        {
            "command": "G1",
            "param": {
                "start": Vec3(0, 0, 0),
                "end": Vec3(1, 0, 0),
            },
        },
        {
            "command": "G1",
            "param": {
                "start": Vec3(10, 0, 0),
                "end": Vec3(11, 0, 0),
            },
        },
        {
            "command": "G1",
            "param": {
                "start": Vec3(20, 0, 0),
                "end": Vec3(21, 0, 0),
            },
        },
    ]
    st = planar_travel_stats(entities, initial_xy=(0.0, 0.0))
    assert st["jump_count"] == 2
    assert st["travel_mm"] >= 18.0


def test_chain_fill_reduces_travel_vs_reverse_order():
    """Segmentos desordenados: encadenar desde un extremo reduce viaje total."""
    z = 0.0
    # Tres horizontales separados; orden "malo" en una sola polilínea por línea
    raw = [
        LineString([(0, 0), (10, 0)]),
        LineString([(0, 5), (10, 5)]),
        LineString([(0, 10), (10, 10)]),
    ]
    start = Vec3(0, 0, z)
    chained = chain_fill_linestrings(raw, start)
    g = GcodeGenerator()
    naive = g.generate_fill_entities(raw, "fill", 0, z)
    g2 = GcodeGenerator()
    ordered = g2.generate_fill_entities(chained, "fill", 0, z)
    sn = planar_travel_stats(naive, initial_xy=(0.0, 0.0))
    so = planar_travel_stats(ordered, initial_xy=(0.0, 0.0))
    assert so["travel_mm"] < sn["travel_mm"]


def test_find_optimal_sequence_two_squares_less_travel_than_reverse():
    """Dos cuadrados: la secuencia NN+2opt no empeora vs orden inverso fijo."""
    z = 1.0
    sq = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])

    def wall(poly, idx, ox, oy):
        p = Polygon(
            [(ox + x, oy + y) for x, y in poly.exterior.coords[:-1]]
            + [(ox, oy)]
        )
        bp = [Vec3(ox + c[0], oy + c[1], z) for c in p.exterior.coords[:-1]]
        return {
            "polygon": p,
            "fill_lines": [],
            "boundary_points": bp,
            "centroid": Vec3(ox + 50, oy + 50, z),
            "is_arc": False,
            "skip_outline": False,
            "outline_only": False,
        }

    a = wall(sq, 0, 0, 0)
    b = wall(sq, 1, 150, 0)
    seq_ab = find_optimal_polygon_sequence([a, b], Vec3(0, 0, z), z)
    seq_ba = find_optimal_polygon_sequence([b, a], Vec3(0, 0, z), z)
    # Desde (0,0,z) el primer polígono debe ser el de la esquina inferior izquierda
    assert seq_ab[0]["polygon_index"] == 0
    assert seq_ba[0]["polygon_index"] == 1


def test_benchmark_many_islands_completes_quickly():
    """Muchas islas en una capa: debe terminar en unos segundos (NN sin 2-opt pesado)."""
    z = 0.0

    def wall(i):
        ox, oy = (i % 10) * 25.0, (i // 10) * 25.0
        p = Polygon([(ox, oy), (ox + 10, oy), (ox + 10, oy + 10), (ox, oy + 10)])
        bp = [
            Vec3(ox, oy, z),
            Vec3(ox + 10, oy, z),
            Vec3(ox + 10, oy + 10, z),
            Vec3(ox, oy + 10, z),
        ]
        return {
            "polygon": p,
            "fill_lines": [],
            "boundary_points": bp,
            "centroid": Vec3(ox + 5, oy + 5, z),
            "is_arc": False,
            "skip_outline": False,
            "outline_only": False,
        }

    items = [wall(i) for i in range(30)]
    t0 = time.perf_counter()
    find_optimal_polygon_sequence(items, Vec3(0, 0, z), z)
    elapsed = time.perf_counter() - t0
    assert elapsed < 12.0, f"optimización demasiado lenta: {elapsed:.2f}s"


def test_benchmark_dense_boundary_limited_entries():
    """Polígono con muchos vértices: solo se evalúan K candidatos de entrada."""
    z = 0.0
    circle = Point(200.0, 200.0).buffer(25.0, quad_segs=48)
    p = Polygon(list(circle.exterior.coords))
    bp = [Vec3(float(x), float(y), z) for x, y in p.exterior.coords[:-1]]
    assert len(bp) > 40
    dense = {
        "polygon": p,
        "fill_lines": [],
        "boundary_points": bp,
        "centroid": Vec3(200, 200, z),
        "is_arc": False,
        "skip_outline": False,
        "outline_only": False,
    }
    small = Polygon([(0, 0), (15, 0), (15, 15), (0, 15), (0, 0)])
    sbp = [Vec3(c[0], c[1], z) for c in small.exterior.coords[:-1]]
    other = {
        "polygon": small,
        "fill_lines": [],
        "boundary_points": sbp,
        "centroid": Vec3(7.5, 7.5, z),
        "is_arc": False,
        "skip_outline": False,
        "outline_only": False,
    }
    t0 = time.perf_counter()
    seq = find_optimal_polygon_sequence([dense, other], Vec3(0, 0, z), z)
    elapsed = time.perf_counter() - t0
    assert elapsed < 8.0, f"took {elapsed:.2f}s"
    assert len(seq) == 2


def test_optimize_many_layers_stays_under_time_budget():
    """Varias capas Z con la misma planta: cada capa usa el optimizador acotado."""
    z0 = 0.0
    p = Polygon([(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)])
    bp0 = [Vec3(c[0], c[1], z0) for c in p.exterior.coords[:-1]]
    out = {}
    for i in range(80):
        zz = z0 + i * 0.01
        out[zz] = [
            {
                "polygon": p,
                "fill_lines": [],
                "boundary_points": [Vec3(v.x, v.y, zz) for v in bp0],
                "centroid": Vec3(10, 10, zz),
                "is_arc": False,
                "skip_outline": False,
                "outline_only": False,
            }
            for _ in range(2)
        ]
    t0 = time.perf_counter()
    optimize_layer_traversal(out, Vec3(0, 0, z0))
    elapsed = time.perf_counter() - t0
    assert elapsed < 15.0, f"{elapsed:.2f}s para 80 capas × 2 islas"


def test_route_options_disables_two_opt_for_small_max_islands():
    """Con two_opt_max_islands=0 nunca aplica 2-opt (solo NN)."""
    z = 0.0
    sq = Polygon([(0, 0), (50, 0), (50, 50), (0, 50), (0, 0)])

    def wall(ox, oy):
        p = Polygon(
            [(ox + x, oy + y) for x, y in sq.exterior.coords[:-1]] + [(ox, oy)]
        )
        bpv = [Vec3(ox + c[0], oy + c[1], z) for c in p.exterior.coords[:-1]]
        return {
            "polygon": p,
            "fill_lines": [],
            "boundary_points": bpv,
            "centroid": Vec3(ox + 25, oy + 25, z),
            "is_arc": False,
            "skip_outline": False,
            "outline_only": False,
        }

    items = [wall(0, 0), wall(80, 0), wall(40, 60)]
    opt = RouteOptimizeOptions(two_opt_max_islands=0, two_opt_max_passes=2)
    seq = find_optimal_polygon_sequence(items, Vec3(0, 0, z), z, route_options=opt)
    assert len(seq) == 3
