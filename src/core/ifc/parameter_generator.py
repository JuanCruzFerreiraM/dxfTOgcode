# -*- coding: utf-8 -*-
from shapely.affinity import affine_transform, rotate, translate
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from ezdxf.math import Vec3
import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from src.utils.debug_mpl import plot_polygon_layer_debug

# -----------------------
# Utilidades geométricas
# -----------------------

def simplify_union_polygon(polygon: Polygon, tolerance=0.01) -> Polygon:
    """
    Simplifica un polígono unión para eliminar complejidad innecesaria.
    """
    try:
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        if simplified.is_valid and simplified.area > polygon.area * 0.9:
            return simplified
        return polygon.convex_hull
    except:
        return polygon

def calculate_dominant_angle(polygon: Polygon) -> float:
    """
    Calcula el ángulo (en grados, 0° a 180°) del borde más largo del polígono,
    medido respecto al eje X positivo.
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
    """
    Determina si el zigzag debe ir en 'x' o 'y' según el borde más largo del polígono.
    """
    angle_deg = calculate_dominant_angle(polygon)
    if 45 <= abs(angle_deg) <= 135:
        return 'y'
    return 'x'

def normalize_polygon_bounds(polygon: Polygon, tolerance=1e-10) -> Polygon:
    """
    Normaliza un polígono eliminando errores numéricos muy pequeños.
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
        x = round(x, 6)
        y = round(y, 6)
        normalized_coords.append((x, y))
    
    try:
        normalized_polygon = Polygon(normalized_coords)
        if not normalized_polygon.is_valid:
            normalized_polygon = normalized_polygon.buffer(0)
        return normalized_polygon
    except:
        return polygon

def _clip_polygon_by_offset(polygon: Polygon, offset: float) -> Polygon:
    if offset and offset > 0:
        clipped = polygon.buffer(-offset)
        if clipped.is_empty:
            return polygon
        return clipped
    return polygon

# -----------------------
# Generador zigzag single-pass
# -----------------------
def generate_vzigzag_singlepass(polygon: Polygon, step=0.1, offset=0.0, global_shift=0.0, fill_rot_anlgle=0, v_angle=0):
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

    if direction == 'x':
        calc_step = (maxy - miny) * np.tan(v_angle_rad) if v_angle_rad != 0 else step
        start = minx + global_shift - calc_step
        while start <= maxx + calc_step:
            y = maxy if toggle else miny
            points.append((start, y))
            toggle = not toggle
            start += calc_step
    else:
        calc_step = (maxx - minx) * np.tan(v_angle_rad) if v_angle_rad != 0 else step
        start = miny + global_shift - calc_step
        while start <= maxy + calc_step:
            x = maxx if toggle else minx
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

# -----------------------
# Optimización global shift
# -----------------------
def optimize_global_shift_for_layer(sections, step=0.1, offset=0.0, n_shifts=20, v_angle=0):
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

# -----------------------
# Extraer polígonos y aplicar relleno con superposición Z
# -----------------------
def extract_layer_polygons_with_fill(slices, step=0.1, offset=0.0, n_shifts=20, angle=0, v_angle=0, radius=0):
    layer_polygons = {}
    
    # Recopilar todos los polígonos por element_type e element_id a través de todas las capas
    all_polygons_by_element = {}
    for layer in slices:
        z = layer["z"]
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
                
                key = f"{element_type}_{element_id}"
                if key not in all_polygons_by_element:
                    all_polygons_by_element[key] = []
                all_polygons_by_element[key].append(transformed_polygon)

    # Crear polígonos unión para cada elemento
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
    
    # Calcular best_shifts usando los polígonos unión
    global_best_shifts = optimize_global_shift_for_layer(
        union_polygons_for_optimization, step=step, offset=offset, n_shifts=n_shifts, v_angle=v_angle
    )
    
    # Generar patrones base
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
        
        # Generar patrón base
        base_pattern = generate_vzigzag_singlepass(
            poly, step=step, offset=offset, global_shift=shift_real, 
            fill_rot_anlgle=angle, v_angle=v_angle
        )
        base_patterns[key] = base_pattern

    # Aplicar los patrones base a todas las capas
    for layer in slices:
        z = layer["z"]
        raw_sections = []
        
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
                
                raw_sections.append({"polygon": transformed_polygon, "type": element_type, "id": element_id})

        sections_data = []
        for sec in raw_sections:
            poly = sec['polygon']
            element_type = sec['type']
            element_id = sec['id']
            data = {"polygon": poly, "type": element_type, "id": element_id, "fill_lines": []}

            if "wall" in element_type.lower() and poly.area > (step**2) * 1e-3:
                key = f"{element_type}_{element_id}"
                
                if key in base_patterns:
                    base_pattern = base_patterns[key]
                    fill_lines = []
                    
                    for line in base_pattern:
                        intersection = poly.intersection(line)
                        if not intersection.is_empty:
                            if isinstance(intersection, LineString):
                                fill_lines.append(intersection)
                            elif isinstance(intersection, MultiLineString):
                                fill_lines.extend(list(intersection.geoms))
                    
                    data["fill_lines"] = fill_lines
            
            sections_data.append(data)
        layer_polygons[z] = sections_data
    
    return layer_polygons

# -----------------------
# Generar G-code
# -----------------------
def generate_gcode_from_meshes(generator, sliced_layers, step=0.1, offset=0.0, start_id=0, debug_plot_every=0, rotation_angle=0, v_angle=0, radius=0):
    def to_vec3_mm_rounded(coord, z):
        x_mm = round(coord[0] * 1000, 1)
        y_mm = round(coord[1] * 1000, 1)
        z_mm = round(z * 1000, 1)
        return Vec3(x_mm, y_mm, z_mm)

    polygon_data = extract_layer_polygons_with_fill(
        sliced_layers, step=step, offset=offset, angle=rotation_angle, v_angle=v_angle, radius=radius
    )

    if debug_plot_every and debug_plot_every > 0:
        plot_polygon_layer_debug(polygon_data, step=debug_plot_every)

    entity_id_counter = start_id
    id_outline = 0

    for z, sections in sorted(polygon_data.items()):
        for section in sections:
            polygon = section["polygon"]

            # OUTLINE exterior
            coords = list(polygon.exterior.coords)
            n = len(coords) - 1
            for i in range(n):
                p1 = to_vec3_mm_rounded(coords[i], z)
                p2 = to_vec3_mm_rounded(coords[i+1], z)
                if p1.x == p2.x and p1.y == p2.y and p1.z == p2.z:
                    continue
                generator.line_entity(p1, p2, layer="outline", id=entity_id_counter)
                entity_id_counter += 1

            # OUTLINE interior
            for interior in polygon.interiors:
                coords = list(interior.coords)
                for i in range(len(coords)-1):
                    p1 = to_vec3_mm_rounded(coords[i], z)
                    p2 = to_vec3_mm_rounded(coords[i+1], z)
                    if p1.x == p2.x and p1.y == p2.y and p1.z == p2.z:
                        continue
                    generator.line_entity(p1, p2, layer="outline", id=entity_id_counter, outline_id=id_outline)
                    entity_id_counter += 1

            # Filling
            fill_lines = section.get("fill_lines", [])
            for line in fill_lines:
                coords = list(line.coords)
                for i in range(len(coords)-1):
                    p1 = to_vec3_mm_rounded(coords[i], z)
                    p2 = to_vec3_mm_rounded(coords[i+1], z)
                    if p1.x == p2.x and p1.y == p2.y and p1.z == p2.z:
                        continue
                    generator.line_entity(p1, p2, layer="fill", id=entity_id_counter, outline_id=id_outline)
                    entity_id_counter += 1

            id_outline += 1

    return entity_id_counter
