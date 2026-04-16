"""Métricas de viaje en plano (G0 XY) sobre listas de entidades G-code."""

from __future__ import annotations

from typing import List, Tuple

from src.utils.geometry import distance


def planar_travel_stats(
    entity_list,
    initial_xy: Tuple[float, float] = (0.0, 0.0),
    tol_mm: float = 0.001,
) -> dict:
    """
    Simula el acumulado de desplazamiento XY entre entidades como en MachineHandler:
    si el inicio de la siguiente entidad no coincide con la posición actual, cuenta
    un viaje (salto) y suma la distancia en plano hasta ese inicio.

    Returns:
        dict con ``jump_count``, ``travel_mm``, ``initial_xy``, ``tol_mm``.
    """
    x, y = float(initial_xy[0]), float(initial_xy[1])
    jumps = 0
    travel_mm = 0.0

    for entity in entity_list:
        param = entity.get("param") or {}
        start = param.get("start")
        if start is None:
            continue
        if distance(x, y, start.x, start.y) > tol_mm:
            d = distance(x, y, start.x, start.y)
            travel_mm += d
            jumps += 1
            x, y = start.x, start.y
        end = param.get("end")
        if end is not None:
            x, y = end.x, end.y

    return {
        "jump_count": jumps,
        "travel_mm": travel_mm,
        "initial_xy": initial_xy,
        "tol_mm": tol_mm,
    }
