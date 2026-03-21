# -*- coding: utf-8 -*-
"""Parameter generator for IFC polygon processing and fill pattern generation.

This module provides functions for converting IFC slice data into optimized
polygon representations with fill patterns, coordinate transformations,
and geometric optimizations for 3D printing applications.
"""

from shapely.affinity import affine_transform, rotate, translate, scale
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from ezdxf.math import Vec3
import numpy as np
import math
from src.utils.geometry import calculate_centroid_from_trims

def generate_arc_fill(transform_section,offset,v_angle, debug_info=None):
    """Generate polar zigzag fill pattern for arc-shaped wall segments.

    Calculates a continuous zigzag path between inner and outer radius of an arc,
    adjusting the angular step based on wall thickness and the desired V-angle
    to maintain consistent pattern density.

    Args:
        transform_section (list): List of dictionaries containing arc geometry data
                                  (center, radius, trims) in millimeters.
        offset (float): Offset distance from the wall boundaries in mm.
        v_angle (float): Angle of the zigzag pattern relative to the radius in degrees.
        debug_info (dict, optional): Dictionary to store debug information.

    Returns:
        tuple: A tuple containing:
            - list: List of LineString objects representing the fill path.
            - list/tuple: Coordinates of the first trim point.
            - list/tuple: Coordinates of the second trim point.
    """
    # Recolectar todos los arcos
    arcs = [s for s in transform_section if s['type'] == 'ARC']
    
    if len(arcs) < 2:
        return [], (0,0), (0,0)
    
    # Identificar arco exterior (mayor radio) e interior (menor radio)
    arcs_sorted = sorted(arcs, key=lambda a: a['radius'], reverse=True)
    outer_arc = arcs_sorted[0]  # Mayor radio
    inner_arc = arcs_sorted[1]  # Menor radio
    
    # Usar el centro (deberían ser iguales, pero por seguridad tomamos el del exterior)
    center = outer_arc['center']
    
    # Radios con offset aplicado
    r_outer = outer_arc['radius'] - offset  # Radio exterior reducido
    r_inner = inner_arc['radius'] + offset  # Radio interior aumentado
    
    # Usar los trim points del arco EXTERIOR para definir el rango angular
    trim_1 = outer_arc['point_trim1']
    trim_2 = outer_arc['point_trim2']
    is_ccw = outer_arc['is_ccw']
    
    dx_1 = trim_1[0] - center[0]
    dy_1 = trim_1[1] - center[1]    
    dx_2 = trim_2[0] - center[0]
    dy_2 = trim_2[1] - center[1]
    
    raw_angle1 = math.atan2(dy_1, dx_1)
    raw_angle2 = math.atan2(dy_2, dx_2)
    
    # Normalizar ángulos a [0, 2π]
    norm_angle1 = raw_angle1 if raw_angle1 >= 0 else raw_angle1 + 2 * math.pi
    norm_angle2 = raw_angle2 if raw_angle2 >= 0 else raw_angle2 + 2 * math.pi
    
    # Determinar el rango angular correcto según la dirección del arco
    # El arco va de trim1 a trim2
    if is_ccw:
        # Sentido antihorario: el ángulo aumenta
        alpha1 = norm_angle1
        alpha2 = norm_angle2
        if alpha2 <= alpha1:
            alpha2 += 2 * math.pi
    else:
        # Sentido horario: el ángulo disminuye, pero para el fill vamos en orden creciente
        alpha1 = norm_angle2
        alpha2 = norm_angle1
        if alpha2 <= alpha1:
            alpha2 += 2 * math.pi
    
    # Guardar debug info si se proporciona
    if debug_info is not None:
        debug_info['center'] = (center[0], center[1])
        debug_info['r_outer'] = r_outer
        debug_info['r_inner'] = r_inner
        debug_info['trim1'] = (trim_1[0], trim_1[1])
        debug_info['trim2'] = (trim_2[0], trim_2[1])
        debug_info['is_ccw'] = is_ccw
        debug_info['raw_angle1_deg'] = math.degrees(raw_angle1)
        debug_info['raw_angle2_deg'] = math.degrees(raw_angle2)
        debug_info['norm_angle1_deg'] = math.degrees(norm_angle1)
        debug_info['norm_angle2_deg'] = math.degrees(norm_angle2)
        debug_info['alpha1_deg'] = math.degrees(alpha1)
        debug_info['alpha2_deg'] = math.degrees(alpha2)
    
    avg_radius = (r_inner + r_outer) / 2
    e = r_outer - r_inner
    
    if e <= 0:
        # Si el offset es mayor que el espesor del muro, no hay espacio para relleno
        return [], trim_1, trim_2
    
    # Calcular offset angular para que el relleno no toque las líneas de trim
    angular_offset = offset / avg_radius if avg_radius > 0 else 0
    
    # Reducir el rango angular por el offset en ambos extremos
    alpha1_fill = alpha1 + angular_offset
    alpha2_fill = alpha2 - angular_offset
    
    if debug_info is not None:
        debug_info['angular_offset_deg'] = math.degrees(angular_offset)
        debug_info['alpha1_fill_deg'] = math.degrees(alpha1_fill)
        debug_info['alpha2_fill_deg'] = math.degrees(alpha2_fill)
        debug_info['arc_span_deg'] = math.degrees(alpha2_fill - alpha1_fill)
    
    if alpha2_fill <= alpha1_fill:
        return [], trim_1, trim_2
    
    # Calcular step angular basado en el espesor y v_angle
    if v_angle != 0:
        angular_step = (e * math.tan(math.radians(v_angle))) / avg_radius
    else:
        # Sin v_angle, usar un step que dé aproximadamente 10 líneas
        angular_step = (alpha2_fill - alpha1_fill) / 10
    
    if angular_step < 0.01: 
        angular_step = 0.01
    
    if debug_info is not None:
        debug_info['angular_step_deg'] = math.degrees(angular_step)
        debug_info['e'] = e
    
    points = []
    phi = alpha1_fill
    going_out = True  # True = de interior a exterior

    while phi < alpha2_fill:
        if going_out:
            # Punto en radio interior
            p1 = (r_inner * math.cos(phi) + center[0], r_inner * math.sin(phi) + center[1])
            points.append(p1)
            # Avanzar al siguiente ángulo
            next_phi = phi + angular_step
            if next_phi > alpha2_fill:
                next_phi = alpha2_fill
            # Punto en radio exterior en el nuevo ángulo
            p2 = (r_outer * math.cos(next_phi) + center[0], r_outer * math.sin(next_phi) + center[1])
            points.append(p2)
            phi = next_phi
        else:
            # Punto en radio exterior
            p1 = (r_outer * math.cos(phi) + center[0], r_outer * math.sin(phi) + center[1])
            points.append(p1)
            # Avanzar al siguiente ángulo
            next_phi = phi + angular_step
            if next_phi > alpha2_fill:
                next_phi = alpha2_fill
            # Punto en radio interior en el nuevo ángulo
            p2 = (r_inner * math.cos(next_phi) + center[0], r_inner * math.sin(next_phi) + center[1])
            points.append(p2)
            phi = next_phi
        
        going_out = not going_out
        
        # Evitar loop infinito si phi no avanza
        if phi >= alpha2_fill:
            break
    
    if debug_info is not None:
        debug_info['num_points'] = len(points)
        if len(points) >= 2:
            debug_info['first_point'] = points[0]
            debug_info['last_point'] = points[-1]
    
    if len(points) < 2:
        return [], trim_1, trim_2
    
    return [LineString(points)], trim_1, trim_2

def convert_arc_to_mm(arc_data: dict) -> dict:
    transform_arc_data = []
    for value in arc_data: 
        if value['type'] == 'ARC':
            transform_value = {
                'center': value['center'] * 1000,
                'is_ccw': value['is_ccw'],
                'point_trim1': value['point_trim1'] * 1000,
                'point_trim2': value['point_trim2'] * 1000,
                'radius': value['radius'] * 1000,
                'type': 'ARC'
            }
            transform_arc_data.append(transform_value)
        elif value['type'] == 'LINE':
            
            scaled_points = [
                (p[0] * 1000, p[1] * 1000, p[2] * 1000 if len(p) > 2 else 0) for p in value['points']
            ]
            
            transform_value = {
                'points': scaled_points,
                'type': 'LINE'
            }
            transform_arc_data.append(transform_value)
    return transform_arc_data

def convert_polygon_to_mm(polygon: Polygon) -> Polygon:
    """Convert polygon coordinates from meters to millimeters.
    
    Args:
        polygon (Polygon): Shapely polygon with coordinates in meters
        
    Returns:
        Polygon: Scaled polygon with coordinates in millimeters
    """
    return scale(polygon, xfact=1000.0, yfact=1000.0, origin=(0, 0))

def simplify_union_polygon(polygon: Polygon, tolerance=0.01) -> Polygon:
    """Simplify union polygon to remove unnecessary complexity.
    
    Args:
        polygon (Polygon): Complex polygon to simplify
        tolerance (float): Simplification tolerance in coordinate units
        
    Returns:
        Polygon: Simplified polygon or convex hull if simplification fails
    """
    try:
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        if simplified.is_valid and simplified.area > polygon.area * 0.9:
            return simplified
        return polygon.convex_hull
    except:
        return polygon

def calculate_dominant_angle(polygon: Polygon) -> float:
    """Calculate angle of longest polygon edge relative to positive X-axis.
    
    Args:
        polygon (Polygon): Input polygon to analyze
        
    Returns:
        float: Angle in degrees (0° to 180°) of dominant edge
    """
    longest = 0.0
    best_angle = 0.0
    coords = list(polygon.exterior.coords)
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length > longest:
            longest = length
            best_angle = math.atan2(dy, dx)
    angle_deg = math.degrees(best_angle) % 180
    return angle_deg

def dominant_edge_direction(polygon: Polygon) -> str:
    """Determine optimal zigzag direction based on polygon's longest edge.
    
    Args:
        polygon (Polygon): Input polygon to analyze
        
    Returns:
        str: 'x' for horizontal or 'y' for vertical zigzag direction
    """
    angle_deg = calculate_dominant_angle(polygon)
    if 45 <= abs(angle_deg) <= 135:
        return 'y'
    return 'x'

def normalize_polygon_bounds(polygon: Polygon, tolerance=1e-7) -> Polygon:
    """Normalize polygon coordinates to eliminate numerical errors.
    
    Args:
        polygon (Polygon): Input polygon with potential numerical issues
        tolerance (float): Threshold for considering values as zero
        
    Returns:
        Polygon: Normalized polygon with rounded coordinates
    """
    if polygon.is_empty:
        return polygon
    
    coords = list(polygon.exterior.coords)
    normalized_coords = []
    
    for x, y in coords:
        if abs(x) < tolerance:
            x = 0.0
        if abs(y) < tolerance:
            y = 0.0
        x = round(x, 3)
        y = round(y, 3)
        normalized_coords.append((x, y))
    
    try:
        normalized_polygon = Polygon(normalized_coords)
        if not normalized_polygon.is_valid:
            normalized_polygon = normalized_polygon.buffer(0)
        return normalized_polygon
    except:
        return polygon

def _clip_polygon_by_offset(polygon: Polygon, offset: float) -> Polygon:
    """Apply inward offset to polygon for fill boundary adjustment.
    
    Args:
        polygon (Polygon): Input polygon to offset
        offset (float): Inward offset distance (positive values shrink polygon)
        
    Returns:
        Polygon: Offset polygon or original if offset results in empty geometry
    """
    if offset and offset > 0:
        clipped = polygon.buffer(-offset)
        if clipped.is_empty:
            return polygon
        return clipped
    return polygon

def generate_vzigzag_singlepass(polygon: Polygon, step=0.1, offset=0.0, global_shift=0.0, fill_rot_anlgle=0, v_angle=0):
    """Generate vertical zigzag fill pattern for polygon with single-pass optimization.
    
    Args:
        polygon (Polygon): Target polygon for fill generation
        step (float): Base spacing between fill lines in mm
        offset (float): Inward offset from polygon boundary in mm
        global_shift (float): Global shift for pattern alignment
        fill_rot_anlgle (int): Fill pattern rotation angle in degrees
        v_angle (int): Vertical angle for angled fill patterns in degrees
        
    Returns:
        list: List of LineString objects representing fill pattern
    """
    v_angle_rad = np.radians(v_angle)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty:
        return []
    
    dominant_angle = calculate_dominant_angle(polygon)
    centroid = polygon.centroid
    translated_polygon = translate(polygon, xoff=-centroid.x, yoff=-centroid.y)
    rotated_polygon = rotate(translated_polygon, (fill_rot_anlgle - dominant_angle), origin=(0,0))
    direction = dominant_edge_direction(rotated_polygon)
    poly = _clip_polygon_by_offset(rotated_polygon, offset)
    
    if poly.is_empty: 
        return []

    minx, miny, maxx, maxy = poly.bounds
    points = []
    toggle = True
    
    # Margen adicional para que el zigzag no toque las "tapas" del polígono
    # en la dirección de barrido (start/end)
    end_margin = offset * 0.5  # Medio offset de margen en los extremos
    
    # También aplicar margen en la dirección perpendicular (donde el zigzag hace sus picos)
    perp_margin = offset * 0.3  # Margen para los picos del zigzag

    if direction == 'x':
        calc_step = (maxy - miny) * np.tan(v_angle_rad) if v_angle_rad != 0 else step
        # Empezar después del margen y terminar antes
        start = minx + end_margin + global_shift
        end_limit = maxx - end_margin
        # Aplicar margen perpendicular a los límites Y
        y_low = miny + perp_margin
        y_high = maxy - perp_margin
        while start <= end_limit:
            y = y_high if toggle else y_low
            points.append((start, y))
            toggle = not toggle
            start += calc_step
    else:
        calc_step = (maxx - minx) * np.tan(v_angle_rad) if v_angle_rad != 0 else step
        # Empezar después del margen y terminar antes
        start = miny + end_margin + global_shift
        end_limit = maxy - end_margin
        # Aplicar margen perpendicular a los límites X
        x_low = minx + perp_margin
        x_high = maxx - perp_margin
        while start <= end_limit:
            x = x_high if toggle else x_low
            points.append((x, start))
            toggle = not toggle
            start += calc_step

    if len(points) < 2:
        return []

    zigzag_line = LineString(points)
    intersection_rotated = poly.intersection(zigzag_line)
    intersection_translated = rotate(intersection_rotated, (dominant_angle - fill_rot_anlgle), origin=(0,0))
    intersection = translate(intersection_translated, xoff=centroid.x, yoff=centroid.y)

    results = []
    if intersection.is_empty:
        cx, cy = poly.representative_point().x, poly.representative_point().y
        if direction == 'x':
            center_line = LineString([(cx, miny), (cx, maxy)])
        else:
            center_line = LineString([(minx, cy), (maxx, cy)])
        inter_center = poly.intersection(center_line)
        if not inter_center.is_empty:
            if isinstance(inter_center, LineString):
                results.append(inter_center)
            elif isinstance(inter_center, MultiLineString):
                results.extend(list(inter_center.geoms))
        return results

    if isinstance(intersection, LineString):
        results.append(intersection)
    elif isinstance(intersection, MultiLineString):
        results.extend(list(intersection.geoms))
    return results


def optimize_global_shift_for_layer(sections, step=0.1, offset=0.0, n_shifts=20, v_angle=0):
    """Optimize global pattern shift to maximize fill line coverage across layer.
    
    Args:
        sections (list): List of polygon section dictionaries
        step (float): Base fill line spacing in mm
        offset (float): Inward offset from boundaries in mm
        n_shifts (int): Number of shift values to test
        v_angle (int): Vertical angle for fill patterns in degrees
        
    Returns:
        dict: Optimal shift fractions for 'x' and 'y' directions
    """
    shifts_frac = np.linspace(0.0, 1.0, n_shifts, endpoint=False)
    best = {'x': 0.0, 'y': 0.0}
    polys_by_dir = {'x': [], 'y': []}
    
    for sec in sections:
        if sec.get('type', '').lower().find('wall') >= 0:
            poly = sec['polygon']
            d = dominant_edge_direction(poly)
            polys_by_dir[d].append(poly)

    for d in ('x', 'y'):
        if not polys_by_dir[d]:
            best[d] = 0.0
            continue
        
        best_frac = 0.0
        best_length = -1.0
        
        for s in shifts_frac:
            total_len = 0.0
            for poly in polys_by_dir[d]:
                minx, miny, maxx, maxy = _clip_polygon_by_offset(poly, offset).bounds
                if v_angle != 0:
                    v_angle_rads = np.radians(v_angle)
                    calc_step = (maxy - miny) * np.tan(v_angle_rads) if d == "x" else (maxx - minx) * np.tan(v_angle_rads)
                else:
                    calc_step = step
                
                shift_actual = s * calc_step
                lines = generate_vzigzag_singlepass(poly, step=step, offset=offset, global_shift=shift_actual, v_angle=v_angle)
                for ln in lines:
                    total_len += ln.length
            
            if total_len > best_length:
                best_length = total_len
                best_frac = s
        
        best[d] = best_frac
    return best


def _polygons_from_union_geometry(geom):
    """Lista de Polygon a partir del resultado de unary_union sobre muros."""
    if geom is None or getattr(geom, "is_empty", True):
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [geom]
    if gt == "MultiPolygon":
        return list(geom.geoms)
    if gt == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_polygons_from_union_geometry(g))
        return out
    return []


def _append_fill_from_intersection(new_fill, inter):
    """Añade LineString(s) desde el resultado de line.intersection(polígono)."""
    if inter is None or getattr(inter, "is_empty", True):
        return
    gt = inter.geom_type
    if gt == "LineString":
        new_fill.append(inter)
    elif gt == "MultiLineString":
        new_fill.extend(list(inter.geoms))
    elif gt == "GeometryCollection":
        for g in inter.geoms:
            _append_fill_from_intersection(new_fill, g)


def _dedupe_wall_fill_overlap(layer_polygons):
    """Recorta ``fill_lines`` donde varios muros se solapan en planta, sin recalcular el zigzag.

    El relleno se genera igual que siempre por muro; después se eliminan tramos que caen
    en zona ya cubierta por polígonos de muros procesados antes (orden estable por tipo+id).

    No modifica ``polygon`` ni contornos; solo las líneas de relleno. ``Arc_Wall`` no se toca.
    """
    out = {}
    for z, items in layer_polygons.items():
        arc_items = [i for i in items if i.get("is_arc")]
        wall_items = [
            i
            for i in items
            if not i.get("is_arc")
            and "wall" in str(i.get("type") or "").lower()
            and i.get("polygon") is not None
        ]
        other = [i for i in items if i not in arc_items and i not in wall_items]

        if len(wall_items) <= 1:
            out[z] = items
            continue

        indexed = list(enumerate(wall_items))
        indexed.sort(
            key=lambda iw: (str(iw[1].get("type")), str(iw[1].get("id")))
        )

        U = None
        fills_by_index = {}
        for orig_idx, w in indexed:
            poly = w["polygon"]
            try:
                if U is None:
                    exclusive = poly
                else:
                    exclusive = poly.difference(U)
                    if not exclusive.is_valid:
                        exclusive = exclusive.buffer(0)
            except Exception:
                exclusive = poly

            new_fill = []
            for line in w.get("fill_lines") or []:
                if line is None or getattr(line, "is_empty", True):
                    continue
                try:
                    inter = line.intersection(exclusive)
                    _append_fill_from_intersection(new_fill, inter)
                except Exception:
                    continue

            fills_by_index[orig_idx] = new_fill

            try:
                U = poly if U is None else unary_union([U, poly])
                if not U.is_valid:
                    U = U.buffer(0)
            except Exception:
                U = poly if U is None else U

        new_walls = []
        for i, w in enumerate(wall_items):
            nw = dict(w)
            nw["fill_lines"] = fills_by_index.get(i, w.get("fill_lines", []))
            new_walls.append(nw)

        out[z] = new_walls + arc_items + other

    return out


def _inject_unified_rect_wall_outlines(layer_polygons, step=0.1):
    """Añade contornos desde ``unary_union`` de muros rectos y omite perímetro por muro.

    El relleno por muro no se recalcula. Cada ``IfcWall`` recto pasa a ``skip_outline``;
    los perímetros compartidos entre muros dejan de duplicarse en el G-code de contorno.
    """
    out = {}
    for z, items in layer_polygons.items():
        arc_items = [i for i in items if i.get("is_arc")]
        wall_items = [
            i
            for i in items
            if not i.get("is_arc")
            and "wall" in str(i.get("type") or "").lower()
            and i.get("polygon") is not None
        ]
        other = [i for i in items if i not in arc_items and i not in wall_items]

        if len(wall_items) <= 1:
            out[z] = items
            continue

        polys = []
        for w in wall_items:
            try:
                p = w["polygon"]
                if p is not None and not p.is_empty and float(p.area) > 0:
                    polys.append(p)
            except Exception:
                continue

        if len(polys) <= 1:
            out[z] = items
            continue

        try:
            U = unary_union(polys)
            if not U.is_valid:
                U = U.buffer(0)
        except Exception:
            out[z] = items
            continue

        if U.is_empty:
            out[z] = items
            continue

        components = _polygons_from_union_geometry(U)
        if not components:
            out[z] = items
            continue

        outline_items = []
        for idx, poly in enumerate(components):
            if poly.area <= (step**2) * 1e-3:
                continue
            try:
                poly = normalize_polygon_bounds(poly)
            except Exception:
                pass
            centroid = poly.centroid
            boundary_points = list(poly.exterior.coords)
            outline_items.append(
                {
                    "polygon": poly,
                    "type": "IfcWallOutlineUnion",
                    "id": f"outline_union_{idx}",
                    "fill_lines": [],
                    "is_arc": False,
                    "outline_only": True,
                    "skip_outline": False,
                    "centroid": Vec3(centroid.x, centroid.y, z),
                    "boundary_points": [
                        Vec3(p[0], p[1], z) for p in boundary_points
                    ],
                }
            )

        if not outline_items:
            out[z] = items
            continue

        new_walls = []
        for w in wall_items:
            nw = dict(w)
            nw["skip_outline"] = True
            if "outline_only" in nw:
                del nw["outline_only"]
            new_walls.append(nw)

        out[z] = outline_items + new_walls + arc_items + other

    return out


def _merge_wall_footprints_per_layer(
    layer_polygons, step, offset, n_shifts, angle, v_angle, radius
):
    """Fusiona todas las huellas rectas de IfcWall en cada capa (``unary_union``).

    Las aristas compartidas entre muros dejan de ser doble contorno: la unión
    produce un único polígono (o varios si hay masas desconectadas). El relleno
    se recalcula sobre cada polígono fusionado.

    Los ``Arc_Wall`` no se modifican.
    """
    out = {}
    for z, items in layer_polygons.items():
        arc_items = [i for i in items if i.get("is_arc")]
        wall_items = [
            i
            for i in items
            if not i.get("is_arc")
            and "wall" in str(i.get("type") or "").lower()
            and i.get("polygon") is not None
        ]
        other = [i for i in items if i not in arc_items and i not in wall_items]

        if len(wall_items) <= 1:
            out[z] = items
            continue

        polys = []
        for w in wall_items:
            try:
                p = w["polygon"]
                if p is not None and not p.is_empty and float(p.area) > 0:
                    polys.append(p)
            except Exception:
                continue

        if len(polys) <= 1:
            out[z] = items
            continue

        try:
            u = unary_union(polys)
            if not u.is_valid:
                u = u.buffer(0)
        except Exception:
            out[z] = items
            continue

        if u.is_empty:
            out[z] = items
            continue

        geom_list = _polygons_from_union_geometry(u)
        if not geom_list:
            out[z] = items
            continue

        merged_list = []
        for idx, poly in enumerate(geom_list):
            try:
                poly = normalize_polygon_bounds(poly)
            except Exception:
                pass
            if poly.area <= (step**2) * 1e-3:
                continue

            synthetic_id = f"merged_{idx}"
            union_list = [
                {"polygon": poly, "type": "IfcWall", "id": synthetic_id}
            ]
            global_best_shifts = optimize_global_shift_for_layer(
                union_list, step=step, offset=offset, n_shifts=n_shifts, v_angle=v_angle
            )
            direction = dominant_edge_direction(poly)
            frac = global_best_shifts.get(direction, 0.0)
            clipped = _clip_polygon_by_offset(poly, offset)

            if clipped.is_empty:
                calc_step = step
                max_dim = step
            else:
                minx, miny, maxx, maxy = clipped.bounds
                if v_angle != 0:
                    v_angle_rad = np.radians(v_angle)
                    calc_step = (
                        (maxy - miny) * np.tan(v_angle_rad)
                        if direction == "x"
                        else (maxx - minx) * np.tan(v_angle_rad)
                    )
                else:
                    calc_step = step
                max_dim = max(maxx - minx, maxy - miny)

            calc_step = float(np.clip(calc_step, step * 0.01, max_dim))
            shift_real = float(frac) * calc_step
            base_pattern = generate_vzigzag_singlepass(
                poly,
                step=step,
                offset=offset,
                global_shift=shift_real,
                fill_rot_anlgle=angle,
                v_angle=v_angle,
            )
            fill_lines = []
            poly_offset = _clip_polygon_by_offset(poly, offset)
            if not poly_offset.is_empty:
                for line in base_pattern:
                    intersection = poly_offset.intersection(line)
                    if not intersection.is_empty:
                        if isinstance(intersection, LineString):
                            fill_lines.append(intersection)
                        elif isinstance(intersection, MultiLineString):
                            fill_lines.extend(list(intersection.geoms))

            centroid = poly.centroid
            boundary_points = list(poly.exterior.coords)
            data = {
                "polygon": poly,
                "type": "IfcWall",
                "id": synthetic_id,
                "fill_lines": fill_lines,
                "is_arc": False,
                "centroid": Vec3(centroid.x, centroid.y, z),
                "boundary_points": [Vec3(p[0], p[1], z) for p in boundary_points],
            }
            merged_list.append(data)

        if not merged_list:
            out[z] = items
        else:
            out[z] = merged_list + arc_items + other

    return out


def extract_layer_polygons_with_fill(
    slices,
    step=0.1,
    offset=0.0,
    n_shifts=20,
    angle=0,
    v_angle=0,
    radius=0,
    merge_walls_per_layer=False,
    dedupe_fill_overlap=True,
    unified_rect_wall_outlines=True,
):
    """Extract polygons with fill information for layer processing optimization.
    
    Processes IFC slice data to generate optimized polygon representations with
    fill patterns. Converts coordinates from meters to millimeters and applies
    global shift optimization for consistent layer coverage.
    
    Args:
        slices (list): List of layer slice dictionaries with polygon data
        step (float): Base fill line spacing in mm
        offset (float): Inward offset from polygon boundaries in mm
        n_shifts (int): Number of shift values to test for optimization
        angle (int): Fill pattern rotation angle in degrees
        v_angle (int): Vertical angle for angled fill patterns in degrees
        radius (float): Radius parameter for arc operations (unused in current implementation)
        merge_walls_per_layer (bool): Si True, reemplaza muros por ``unary_union`` y
            **recalcula** relleno (legacy; no combinar con dedupe).
        dedupe_fill_overlap (bool): Si True (y merge False), mantiene el zigzag original
            y recorta ``fill_lines`` para no depositar dos veces en solapes entre muros.
        unified_rect_wall_outlines (bool): Si True (y merge False), inyecta contorno desde
            ``unary_union`` de muros rectos y marca ``skip_outline`` en cada muro (solo relleno).
        
    Returns:
        dict: Dictionary mapping Z-heights to lists of section data with polygons,
              fill patterns, centroids, and boundary points in millimeter coordinates
    """
    layer_polygons = {}
    
    # Collect all polygons by element_type and element_id across all layers
    all_polygons_by_element = {}
    for layer in slices:
        z = layer["z"]
        
        
        if (layer['type'] != 'Arc_Wall'):
            for section in layer["sections"]:

                path = section["path"]
                transform = section["tf"]
                element_type = section.get("type", "Unknown")
                element_id = section.get("id", None)
                affine_matrix = transform[:2, :2].flatten().tolist() + transform[:2, 3].tolist()

                for polygon in path.polygons_full:
                    if np.allclose(affine_matrix, [1,0,0,1,0,0]):
                        transformed_polygon = polygon
                    else:
                        transformed_polygon = affine_transform(polygon, affine_matrix)

                    if not transformed_polygon.is_valid:
                        transformed_polygon = transformed_polygon.buffer(0)

                    # Convert from meters to millimeters
                    transformed_polygon = convert_polygon_to_mm(transformed_polygon)

                    key = f"{element_type}_{element_id}"
                    if key not in all_polygons_by_element:
                        all_polygons_by_element[key] = []
                    all_polygons_by_element[key].append(transformed_polygon)

    # Create union polygons for each element
    base_patterns = {}
    union_polygons_for_optimization = []
    
    for key, polygons in all_polygons_by_element.items():
        element_type, element_id = key.split('_', 1)
        if "wall" in element_type.lower():
            try:
                union_polygon = unary_union(polygons)
                union_polygon = normalize_polygon_bounds(union_polygon)
                union_polygon = simplify_union_polygon(union_polygon)
                
                if isinstance(union_polygon, MultiPolygon):
                    union_polygon = max(union_polygon.geoms, key=lambda p: p.area)
                    union_polygon = normalize_polygon_bounds(union_polygon)
                
                # Minimum area adjusted for mm (step already in mm)
                if union_polygon.area > (step**2) * 1e-3:
                    union_polygons_for_optimization.append({
                        "polygon": union_polygon, 
                        "type": element_type, 
                        "id": element_id
                    })
                        
            except Exception as e:
                largest_poly = max(polygons, key=lambda p: p.area)
                if largest_poly.area > (step**2) * 1e-3:
                    union_polygons_for_optimization.append({
                        "polygon": largest_poly, 
                        "type": element_type, 
                        "id": element_id
                    })
    
    # Calculate best_shifts
    global_best_shifts = optimize_global_shift_for_layer(
        union_polygons_for_optimization, step=step, offset=offset, n_shifts=n_shifts, v_angle=v_angle
    )
    
    # Generate base patterns
    for sec in union_polygons_for_optimization:
        poly = sec['polygon']
        element_type = sec['type']
        element_id = sec['id']
        key = f"{element_type}_{element_id}"
        
        direction = dominant_edge_direction(poly)
        frac = global_best_shifts.get(direction, 0.0)
        clipped = _clip_polygon_by_offset(poly, offset)
        
        if clipped.is_empty:
            calc_step = step
        else:
            minx, miny, maxx, maxy = clipped.bounds
            if v_angle != 0:
                v_angle_rad = np.radians(v_angle)
                calc_step = (maxy - miny) * np.tan(v_angle_rad) if direction == 'x' else (maxx - minx) * np.tan(v_angle_rad)
            else:
                calc_step = step
        
        max_dim = max(maxx - minx, maxy - miny) if not clipped.is_empty else step
        calc_step = float(np.clip(calc_step, step * 0.01, max_dim))
        shift_real = float(frac) * calc_step
        
        base_pattern = generate_vzigzag_singlepass(
            poly, step=step, offset=offset, global_shift=shift_real, 
            fill_rot_anlgle=angle, v_angle=v_angle
        )
        base_patterns[key] = base_pattern

    # Apply patterns and return structured data
    for layer in slices:
        z = layer["z"]  # z already in mm from slicer
        raw_sections = []
        
        # Obtener o crear lista para esta altura Z
        if z not in layer_polygons:
            layer_polygons[z] = []
        sections_data = layer_polygons[z]
        
        if (layer['type'] == 'Arc_Wall'):
            transform_section = convert_arc_to_mm(layer['sections'])
            
            # Debug info para arc fill
            arc_debug_info = {}
            fill_arc_lines, trim1, trim2 = generate_arc_fill(transform_section,offset,v_angle, debug_info=arc_debug_info)
            
            # Log debug info si está habilitado
            import sys
            print(f"\n=== ARC FILL DEBUG (ID: {layer['id']}, Z={z}) ===", file=sys.stderr)
            for key, value in arc_debug_info.items():
                print(f"  {key}: {value}", file=sys.stderr)
            print(f"==========================================\n", file=sys.stderr)
            
            trim1_vec = Vec3(trim1[0], trim1[1], z)
            trim2_vec = Vec3(trim2[0], trim2[1], z)
            arc_data = {
                "polygon": None, 
                "type": layer['type'], 
                "id": layer['id'], 
                "fill_lines": fill_arc_lines,
                "is_arc": True,
                "arc_data": transform_section,
                "centroid": calculate_centroid_from_trims(trim1,trim2,z),  # z already in mm
                "boundary_points": [trim1_vec,trim2_vec]
            }
            sections_data.append(arc_data)
        else: 
        
            for section in layer["sections"]:
                path = section["path"]
                transform = section["tf"]
                element_type = section.get("type", "Unknown")
                element_id = section.get("id", None)
                affine_matrix = transform[:2, :2].flatten().tolist() + transform[:2, 3].tolist()

                for polygon in path.polygons_full:
                    if np.allclose(affine_matrix, [1,0,0,1,0,0]):
                        transformed_polygon = polygon
                    else:
                        transformed_polygon = affine_transform(polygon, affine_matrix)

                    if not transformed_polygon.is_valid:
                        transformed_polygon = transformed_polygon.buffer(0)

                    # Convert from meters to millimeters
                    transformed_polygon = convert_polygon_to_mm(transformed_polygon)

                    raw_sections.append({"polygon": transformed_polygon, "type": element_type, "id": element_id})


            for sec in raw_sections:
                poly = sec['polygon']
                element_type = sec['type']
                element_id = sec['id']

                # Calculate centroid and boundary points (already in mm)
                centroid = poly.centroid
                boundary_points = list(poly.exterior.coords)

                data = {
                    "polygon": poly, 
                    "type": element_type, 
                    "id": element_id, 
                    "fill_lines": [],
                    "is_arc": False,
                    "centroid": Vec3(centroid.x, centroid.y, z),  # z already in mm
                    "boundary_points": [Vec3(p[0], p[1], z) for p in boundary_points]  # coordinates in mm
                }

                if "wall" in element_type.lower() and poly.area > (step**2) * 1e-3:
                    key = f"{element_type}_{element_id}"

                    if key in base_patterns:
                        base_pattern = base_patterns[key]
                        fill_lines = []
                        poly_offset = _clip_polygon_by_offset(poly, offset)

                        if not poly_offset.is_empty:
                            for line in base_pattern:
                                intersection = poly_offset.intersection(line)
                                if not intersection.is_empty:
                                    if isinstance(intersection, LineString):
                                        fill_lines.append(intersection)
                                    elif isinstance(intersection, MultiLineString):
                                        fill_lines.extend(list(intersection.geoms))

                        data["fill_lines"] = fill_lines
            
                sections_data.append(data)
        
        # sections_data ya está referenciado a layer_polygons[z], no es necesario reasignar

    if merge_walls_per_layer:
        layer_polygons = _merge_wall_footprints_per_layer(
            layer_polygons,
            step=step,
            offset=offset,
            n_shifts=n_shifts,
            angle=angle,
            v_angle=v_angle,
            radius=radius,
        )
    elif dedupe_fill_overlap:
        layer_polygons = _dedupe_wall_fill_overlap(layer_polygons)

    if unified_rect_wall_outlines and not merge_walls_per_layer:
        layer_polygons = _inject_unified_rect_wall_outlines(layer_polygons, step=step)

    return layer_polygons
