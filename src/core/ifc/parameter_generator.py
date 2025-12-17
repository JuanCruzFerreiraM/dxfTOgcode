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

def generate_arc_fill(transform_section,offset,v_angle):
    """Generate polar zigzag fill pattern for arc-shaped wall segments.

    Calculates a continuous zigzag path between inner and outer radius of an arc,
    adjusting the angular step based on wall thickness and the desired V-angle
    to maintain consistent pattern density.

    Args:
        transform_section (list): List of dictionaries containing arc geometry data
                                  (center, radius, trims) in millimeters.
        offset (float): Offset distance from the wall boundaries in mm.
        v_angle (float): Angle of the zigzag pattern relative to the radius in degrees.

    Returns:
        tuple: A tuple containing:
            - list: List of LineString objects representing the fill path.
            - list/tuple: Coordinates of the first trim point.
            - list/tuple: Coordinates of the second trim point.
    """
    radius_1, radius_2 = 0
    trim_1,trim_2 = 0
    center = 0
    for section in transform_section:
        if (section['type'] == 'ARC'):
            if (radius_1 == 0): 
                radius_1 = section['radius']
            else:
                radius_2 = section['radius']
            center = section['center']
            trim_1 = section['point_trim1']
            trim_2 = section['point_trim2']
            is_ccw = section['is_ccw']

    if (radius_1 > radius_2):
        r2 = radius_1 - offset
        r1 = radius_2 + offset
    else: 
        r1 = radius_1 + offset
        r2 = radius_2 - offset
    
        dx_1 = trim_1[0] - center[0]
    dy_1 = trim_1[1] - center[1]    
    dx_2 = trim_2[0] - center[0]
    dy_2 = trim_2[1] - center[1]
    

    raw_angle1 = math.atan2(dy_1, dx_1)
    raw_angle2 = math.atan2(dy_2, dx_2)
    
    if raw_angle1 < 0: raw_angle1 += 2 * math.pi
    if raw_angle2 < 0: raw_angle2 += 2 * math.pi
    
    
    alpha1 = raw_angle1
    alpha2 = raw_angle2
    

    if is_ccw:
        if alpha2 <= alpha1:
            alpha2 += 2 * math.pi
    else:

        alpha1, alpha2 = alpha2, alpha1
        if alpha2 <= alpha1:
            alpha2 += 2 * math.pi
    
    avg_radius = (r1 + r2) / 2
    e = r2 - r1
    
    angular_step = (e * math.tan(math.radians(v_angle))) / avg_radius
    if angular_step < 0.01: angular_step = 0.01
    
    phi1 = alpha1
    phi2 = alpha1 + angular_step
    points = []

    
    while (phi1 < alpha2 and phi2 < alpha2):
        p1 = (r1 * math.cos(phi1) + center[0], r1 * math.sin(phi1) + center[1])
        p2 = (r2 * math.cos(phi2) + center[0], r2 * math.sin(phi2) + center[1])
        points.append(p1)
        points.append(p2)
        phi1 = (phi1 + 2 * angular_step) if (phi1 + 2 * angular_step) < alpha2 else alpha2
        phi2 = (phi2 + 2 * angular_step) if (phi2 + 2 * angular_step) < alpha2 else alpha2
    
    
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
            transform_value = {
                'points': value['points'] * 1000,
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


def extract_layer_polygons_with_fill(slices, step=0.1, offset=0.0, n_shifts=20, angle=0, v_angle=0, radius=0):
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
        sections_data = []
        
        if (layer['type'] == 'Arc_Wall'):
            transform_section = convert_arc_to_mm(layer['sections'])
            
            fill_arc_lines, trim1, trim2 = generate_arc_fill(transform_section,offset,v_angle);
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
            continue
        
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
