"""Encadenado greedy de segmentos de relleno para reducir viajes G0 entre tramos."""

from __future__ import annotations

from typing import List, Tuple

from ezdxf.math import Vec3
from shapely.geometry import LineString


def _segment_endpoints(
    fill_lines,
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Descompone LineStrings en segmentos atómicos (2D)."""
    segs: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for line in fill_lines or []:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            a = (float(coords[i][0]), float(coords[i][1]))
            b = (float(coords[i + 1][0]), float(coords[i + 1][1]))
            if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 > 1e-12:
                segs.append((a, b))
    return segs


def chain_fill_linestrings(fill_lines, start: Vec3) -> List[LineString]:
    """
    Ordena segmentos de relleno con vecino más cercano desde ``start``,
    pudiendo invertir cada segmento. Reduce saltos entre líneas del zigzag.

    Cada segmento se emite como LineString de dos puntos, en orden de impresión;
    el extremo final de un segmento coincide con el inicial del siguiente.
    """
    segs = _segment_endpoints(fill_lines)
    if not segs:
        return []

    unused = set(range(len(segs)))
    current = start
    out: List[LineString] = []

    while unused:
        best_i = None
        best_dist = float("inf")
        best_flip = False
        for i in unused:
            a, b = segs[i]
            va = Vec3(a[0], a[1], start.z)
            vb = Vec3(b[0], b[1], start.z)
            da = current.distance(va)
            db = current.distance(vb)
            if da <= db:
                if da < best_dist:
                    best_dist = da
                    best_i = i
                    best_flip = False
            else:
                if db < best_dist:
                    best_dist = db
                    best_i = i
                    best_flip = True
        assert best_i is not None
        unused.remove(best_i)
        a, b = segs[best_i]
        if best_flip:
            out.append(LineString([b, a]))
            current = Vec3(a[0], a[1], start.z)
        else:
            out.append(LineString([a, b]))
            current = Vec3(b[0], b[1], start.z)

    return out
