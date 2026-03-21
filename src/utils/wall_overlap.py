# -*- coding: utf-8 -*-
"""Detección de solape 2D entre huellas de muros distintos en la misma capa."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _line_component_length(geom: Any) -> float:
    """Longitud total de tramos LineString/MultiLineString dentro de una geometría."""
    if geom is None or getattr(geom, "is_empty", True):
        return 0.0
    t = geom.geom_type
    if t == "LineString":
        return float(geom.length)
    if t == "MultiLineString":
        return float(geom.length)
    if t == "LinearRing":
        return float(geom.length)
    if t == "Point" or t == "MultiPoint":
        return 0.0
    if t == "Polygon":
        return 0.0
    if t == "GeometryCollection":
        return sum(_line_component_length(g) for g in geom.geoms)
    return 0.0


def find_overlapping_wall_pairs(
    layer_items: List[Dict[str, Any]],
    min_area_mm2: float = 1e-3,
) -> List[Dict[str, Any]]:
    """Encuentra pares de muros cuya huella 2D se solapa (área > umbral).

    Solo considera elementos con ``polygon`` válido y tipo que contenga ``wall``
    (p. ej. IfcWall). Omite muros de arco (``is_arc``) porque no usan un único
    polígono de planta comparable.

    Args:
        layer_items: Lista de dicts como los de ``polygon_data[z]`` (un elemento
            por muro/sección en esa capa).
        min_area_mm2: Área mínima de la intersección en mm² para contar como solape
            (evita ruido numérico; un borde compartido tiene área 0).

    Returns:
        Lista de dicts con: id_a, type_a, id_b, type_b, area_mm2, bounds (tuple o None).
    """
    walls: List[Dict[str, Any]] = []
    for item in layer_items:
        if item.get("outline_only"):
            continue
        t = item.get("type") or ""
        if "wall" not in str(t).lower():
            continue
        if item.get("is_arc"):
            continue
        poly = item.get("polygon")
        if poly is None or getattr(poly, "is_empty", True):
            continue
        try:
            if poly.area <= 0:
                continue
        except Exception:
            continue
        walls.append({"polygon": poly, "type": t, "id": item.get("id")})

    overlaps: List[Dict[str, Any]] = []
    n = len(walls)
    for i in range(n):
        for j in range(i + 1, n):
            p_i = walls[i]["polygon"]
            p_j = walls[j]["polygon"]
            try:
                if not p_i.intersects(p_j):
                    continue
                inter = p_i.intersection(p_j)
                area = float(inter.area)
            except Exception:
                continue
            if area <= min_area_mm2:
                continue
            bounds: Optional[tuple] = None
            try:
                bounds = tuple(inter.bounds)
            except Exception:
                bounds = None
            overlaps.append(
                {
                    "id_a": walls[i]["id"],
                    "type_a": walls[i]["type"],
                    "id_b": walls[j]["id"],
                    "type_b": walls[j]["type"],
                    "area_mm2": area,
                    "bounds": bounds,
                }
            )
    return overlaps


def find_shared_edge_wall_pairs(
    layer_items: List[Dict[str, Any]],
    min_area_mm2: float = 1e-3,
    min_edge_length_mm: float = 0.1,
) -> List[Dict[str, Any]]:
    """Pares de muros que comparten borde/arista (intersección con área ~0, línea > umbral).

    Dos polígonos adyacentes suelen tocarse en un segmento: la intersección es
    LineString(s) con longitud > 0 y área 0. Eso puede implicar **doble trazo** de
    contorno en la arista común (no relleno duplicado en mancha).

    No incluye pares ya cubiertos por solape de área (``area > min_area_mm2``).
    """
    walls: List[Dict[str, Any]] = []
    for item in layer_items:
        if item.get("outline_only"):
            continue
        t = item.get("type") or ""
        if "wall" not in str(t).lower():
            continue
        if item.get("is_arc"):
            continue
        poly = item.get("polygon")
        if poly is None or getattr(poly, "is_empty", True):
            continue
        try:
            if poly.area <= 0:
                continue
        except Exception:
            continue
        walls.append({"polygon": poly, "type": t, "id": item.get("id")})

    shared: List[Dict[str, Any]] = []
    n = len(walls)
    for i in range(n):
        for j in range(i + 1, n):
            p_i = walls[i]["polygon"]
            p_j = walls[j]["polygon"]
            try:
                if not p_i.intersects(p_j):
                    continue
                inter = p_i.intersection(p_j)
                area = float(inter.area)
                line_len = _line_component_length(inter)
            except Exception:
                continue
            if area > min_area_mm2:
                continue
            if line_len < min_edge_length_mm:
                continue
            bounds: Optional[tuple] = None
            try:
                bounds = tuple(inter.bounds)
            except Exception:
                bounds = None
            shared.append(
                {
                    "id_a": walls[i]["id"],
                    "type_a": walls[i]["type"],
                    "id_b": walls[j]["id"],
                    "type_b": walls[j]["type"],
                    "edge_length_mm": line_len,
                    "bounds": bounds,
                }
            )
    return shared


def collect_all_wall_overlaps(
    polygon_data: Dict[Any, List[Dict[str, Any]]],
    min_area_mm2: Optional[float] = None,
    step: float = 0.1,
) -> List[Dict[str, Any]]:
    """Recorre todas las capas Z y acumula solapes con coordenada z en cada registro.

    Args:
        polygon_data: Mapa Z -> lista de datos de polígono (salida de
            ``extract_layer_polygons_with_fill``).
        min_area_mm2: Si es None, usa ``max(1e-3, step**2 * 1e-6)``.
        step: Espaciado de relleno (mm), usado solo si ``min_area_mm2`` es None.

    Returns:
        Lista de dicts con campos de ``find_overlapping_wall_pairs`` más ``z``.
    """
    if min_area_mm2 is None:
        min_area_mm2 = max(1e-3, float(step) ** 2 * 1e-6)

    all_rows: List[Dict[str, Any]] = []
    for z in sorted(polygon_data.keys()):
        items = polygon_data[z] or []
        pairs = find_overlapping_wall_pairs(items, min_area_mm2=min_area_mm2)
        for p in pairs:
            row = dict(p)
            row["z"] = z
            all_rows.append(row)
    return all_rows


def collect_all_shared_edges(
    polygon_data: Dict[Any, List[Dict[str, Any]]],
    min_area_mm2: Optional[float] = None,
    min_edge_length_mm: float = 0.1,
    step: float = 0.1,
) -> List[Dict[str, Any]]:
    """Como ``collect_all_wall_overlaps`` pero para bordes compartidos (sin solape de área)."""
    if min_area_mm2 is None:
        min_area_mm2 = max(1e-3, float(step) ** 2 * 1e-6)

    all_rows: List[Dict[str, Any]] = []
    for z in sorted(polygon_data.keys()):
        items = polygon_data[z] or []
        pairs = find_shared_edge_wall_pairs(
            items,
            min_area_mm2=min_area_mm2,
            min_edge_length_mm=min_edge_length_mm,
        )
        for p in pairs:
            row = dict(p)
            row["z"] = z
            all_rows.append(row)
    return all_rows
