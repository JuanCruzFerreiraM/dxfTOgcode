"""Orden de islas por capa: NN + 2-opt con límites de coste para modelos grandes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ezdxf.math import Vec3

from src.utils.geometry import distance_vec3_xy


@dataclass
class RouteOptimizeOptions:
    """Parámetros de rendimiento vs calidad del orden de rutas."""

    max_entry_candidates: int = 16
    two_opt_max_islands: int = 20
    two_opt_max_passes: int = 2
    cache_quant_mm: float = 0.25


DEFAULT_ROUTE_OPTIONS = RouteOptimizeOptions()


def _quantize_xy(v: Vec3, quant_mm: float) -> Tuple[int, int]:
    if quant_mm is None or quant_mm <= 0:
        return (int(round(v.x * 1e6)), int(round(v.y * 1e6)))
    s = 1.0 / quant_mm
    return (int(round(v.x * s)), int(round(v.y * s)))


class _RouteOptimizeContext:
    """Caché de first/last por isla dentro de una planificación de capa."""

    __slots__ = ("options", "_cache")

    def __init__(self, options: RouteOptimizeOptions):
        self.options = options
        self._cache: Dict[Tuple[Any, ...], Tuple[Vec3, Vec3]] = {}

    def _cache_key(
        self,
        orig_idx: int,
        entry: Optional[Vec3],
        current_point: Vec3,
        z: float,
        skip_outline: bool,
    ) -> Tuple[Any, ...]:
        q = self.options.cache_quant_mm
        ez = _quantize_xy(entry, q) if entry is not None else None
        cz = _quantize_xy(current_point, q)
        return (orig_idx, ez, cz, round(float(z), 5), skip_outline)

    def get_cached_endpoints(
        self,
        orig_idx: int,
        entry: Optional[Vec3],
        current_point: Vec3,
        z: float,
        skip_outline: bool,
    ) -> Optional[Tuple[Vec3, Vec3]]:
        k = self._cache_key(orig_idx, entry, current_point, z, skip_outline)
        return self._cache.get(k)

    def set_cached_endpoints(
        self,
        orig_idx: int,
        entry: Optional[Vec3],
        current_point: Vec3,
        z: float,
        skip_outline: bool,
        first: Vec3,
        last: Vec3,
    ) -> None:
        k = self._cache_key(orig_idx, entry, current_point, z, skip_outline)
        self._cache[k] = (first, last)


def get_polygon_entry_points(polygon_data, z):
    """Candidatos de entrada en contorno (o centroid / relleno si no hay borde)."""
    pts = list(polygon_data.get("boundary_points") or [])
    if not pts:
        for line in polygon_data.get("fill_lines") or []:
            for coord in line.coords:
                pts.append(Vec3(float(coord[0]), float(coord[1]), z))
    if not pts:
        c = polygon_data.get("centroid")
        if c is not None:
            pts = [c]
    return pts


def _limit_entry_candidates(
    entries: List[Vec3], current_point: Vec3, z: float, max_k: int
) -> List[Vec3]:
    """Solo los K vértices del borde más cercanos en XY (o todos si hay pocos)."""
    if max_k <= 0 or len(entries) <= max_k:
        return entries
    with_z = [Vec3(p.x, p.y, z) for p in entries]
    with_z.sort(key=lambda p: distance_vec3_xy(current_point, p))
    return with_z[:max_k]


def _endpoints_from_build(
    gen, polygon_data, entry, z, orig_idx, pos_before, ctx: _RouteOptimizeContext
) -> Tuple[Vec3, Vec3]:
    skip = bool(polygon_data.get("skip_outline"))
    hit = ctx.get_cached_endpoints(orig_idx, entry, pos_before, z, skip)
    if hit is not None:
        return hit
    ents = gen.build_item_entity_list(
        polygon_data,
        entry if entry is not None else pos_before,
        z,
        orig_idx,
        pos_before,
    )
    if not ents:
        e = entry if entry is not None else pos_before
        ctx.set_cached_endpoints(orig_idx, entry, pos_before, z, skip, e, e)
        return e, e
    first = gen.first_print_start(ents)
    last = gen.last_print_end(ents)
    ctx.set_cached_endpoints(orig_idx, entry, pos_before, z, skip, first, last)
    return first, last


def _simulate_island(
    gen,
    polygon_data,
    current_point,
    z,
    orig_idx,
    ctx: _RouteOptimizeContext,
):
    """
    Calcula (mejor_entry, end_point, travel_mm) para llegar e imprimir el ítem
    desde current_point.
    """
    if polygon_data.get("skip_outline"):
        first, last = _endpoints_from_build(
            gen, polygon_data, current_point, z, orig_idx, current_point, ctx
        )
        travel = distance_vec3_xy(current_point, first)
        return current_point, last, travel

    entries = get_polygon_entry_points(polygon_data, z)
    if not entries:
        first, last = _endpoints_from_build(
            gen, polygon_data, current_point, z, orig_idx, current_point, ctx
        )
        return current_point, last, distance_vec3_xy(current_point, first)

    limited = _limit_entry_candidates(
        entries, current_point, z, ctx.options.max_entry_candidates
    )

    best_travel = float("inf")
    best_entry = limited[0]
    best_end = current_point

    for e in limited:
        first, last = _endpoints_from_build(
            gen, polygon_data, e, z, orig_idx, current_point, ctx
        )
        tr = distance_vec3_xy(current_point, first)
        if tr < best_travel:
            best_travel = tr
            best_entry = e
            best_end = last

    return best_entry, best_end, best_travel


def _sequence_travel_mm(
    gen,
    initial_point,
    ordered_indices_data,
    z,
    ctx: _RouteOptimizeContext,
):
    """Coste total de viaje en plano para una permutación de ítems."""
    pos = initial_point
    total = 0.0
    for orig_idx, polygon_data in ordered_indices_data:
        _, end_p, tr = _simulate_island(gen, polygon_data, pos, z, orig_idx, ctx)
        total += tr
        pos = end_p
    return total


def _two_opt_improve_order(
    layer_polygons,
    initial_order_indices,
    initial_point,
    z,
    gen,
    ctx: _RouteOptimizeContext,
):
    """2-opt sobre la secuencia de islas; omitido si hay demasiadas islas."""
    n = len(initial_order_indices)
    opt = ctx.options
    if n < 3 or n > opt.two_opt_max_islands:
        return initial_order_indices

    def as_pairs(order):
        return [(i, layer_polygons[i]) for i in order]

    order = list(initial_order_indices)
    best_cost = _sequence_travel_mm(gen, initial_point, as_pairs(order), z, ctx)
    improved = True
    passes = 0

    while improved and passes < opt.two_opt_max_passes:
        improved = False
        passes += 1
        for i in range(n):
            for k in range(i + 2, n):
                new_order = order[: i + 1] + order[i + 1 : k + 1][::-1] + order[k + 1 :]
                c = _sequence_travel_mm(gen, initial_point, as_pairs(new_order), z, ctx)
                if c + 1e-9 < best_cost:
                    order = new_order
                    best_cost = c
                    improved = True
                    break
            if improved:
                break

    return order


def _build_sequence_from_order(
    gen, layer_polygons, order, initial_point, z, ctx: _RouteOptimizeContext
):
    """Anota entry/exit reales recorriendo la capa en ``order``."""
    sequence = []
    pos = initial_point
    for orig_idx in order:
        polygon_data = layer_polygons[orig_idx]
        entry, end_p, _ = _simulate_island(gen, polygon_data, pos, z, orig_idx, ctx)
        sequence.append(
            {
                "polygon_index": orig_idx,
                "polygon_data": polygon_data,
                "entry_point": entry,
                "exit_point": end_p,
            }
        )
        pos = end_p
    return sequence


def find_optimal_polygon_sequence(
    layer_polygons,
    initial_point,
    z,
    route_options: Optional[RouteOptimizeOptions] = None,
):
    """Secuencia de polígonos: vecino más cercano con simulación real + 2-opt acotado."""
    from src.core.gcode_generator import GcodeGenerator

    opt = route_options or DEFAULT_ROUTE_OPTIONS
    ctx = _RouteOptimizeContext(opt)
    gen = GcodeGenerator()
    remaining = list(enumerate(layer_polygons))
    current_point = initial_point
    nn_order = []

    while remaining:
        best_i = None
        best_travel = float("inf")
        best_end = current_point

        for i, (orig_idx, polygon_data) in enumerate(remaining):
            _, end_p, travel = _simulate_island(
                gen, polygon_data, current_point, z, orig_idx, ctx
            )
            if travel < best_travel:
                best_travel = travel
                best_i = i
                best_end = end_p

        orig_idx, _ = remaining.pop(best_i)
        nn_order.append(orig_idx)
        current_point = best_end

    improved_order = _two_opt_improve_order(
        layer_polygons, nn_order, initial_point, z, gen, ctx
    )
    return _build_sequence_from_order(
        gen, layer_polygons, improved_order, initial_point, z, ctx
    )


def optimize_layer_traversal(
    polygon_data,
    initial_point,
    route_options: Optional[RouteOptimizeOptions] = None,
):
    """
    Optimiza el recorrido completo por capa. Propaga el punto final simulado
    entre capas consecutivas.
    """
    optimized_layers = {}

    for z, polygons in polygon_data.items():
        if not polygons:
            continue

        layer_start = Vec3(initial_point.x, initial_point.y, z)
        sequence = find_optimal_polygon_sequence(
            polygons, layer_start, z, route_options=route_options
        )
        optimized_layers[z] = sequence

        if sequence:
            initial_point = sequence[-1]["exit_point"]

    return optimized_layers
