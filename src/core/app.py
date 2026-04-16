from pathlib import Path
from src.core.dxf.dxf_parser import generate_entity_list, FileError, UnsupportedEntityError
from src.core.ifc.ifc_parser import ifc_parser
from src.core.ifc.slicer import slicer
from src.core.gcode_generator import GcodeGenerator
from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3
from collections import defaultdict
import hashlib
import json
import time
import numpy as np
import pprint
from src.core.ifc.parameter_generator import extract_layer_polygons_with_fill
from src.utils.wall_overlap import collect_all_shared_edges, collect_all_wall_overlaps
from src.core.debug_config import DEBUG_LOG_ENABLED


def write_debug_log(sections, meshes, polygon_data, log_filename="debug_log.txt"):
    """Write IFC pipeline debug dump to a text file (only when DEBUG_LOG_ENABLED)."""
    if not DEBUG_LOG_ENABLED:
        return
    
    try:
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.write("="*60 + "\n")
            log_file.write("DEBUG LOG - IFC Processing\n")
            log_file.write("="*60 + "\n\n")
            
            # Sections del parser
            log_file.write("[1] IFC Parser - Sections:\n")
            log_file.write("-"*40 + "\n")
            pprint.pprint(sections, stream=log_file)
            log_file.write("\n")
            
            log_file.write("[2] Slicer - Meshes/Slices:\n")
            log_file.write("-"*40 + "\n")
            for i, mesh_slice in enumerate(meshes):
                log_file.write(f"Slice {i}: Z={mesh_slice.get('z')}, Type={mesh_slice.get('type')}\n")
                if 'sections' in mesh_slice:
                    log_file.write(f"  Sections: {len(mesh_slice['sections'])}\n")
                    pprint.pprint(mesh_slice['sections'], stream=log_file)
            log_file.write("\n")
            
            log_file.write("[3] Parameter Generator - Polygon Data:\n")
            log_file.write("-"*40 + "\n")
            for z, polys in polygon_data.items():
                log_file.write(f"Z={z}: {len(polys)} elementos\n")
                for poly in polys:
                    log_file.write(f"  - Type: {poly.get('type')}, ID: {poly.get('id')}\n")
                    if poly.get('is_arc'):
                        log_file.write("    Arc Data:\n")
                        pprint.pprint(poly.get('arc_data'), stream=log_file)
                        log_file.write(f"    Fill lines count: {len(poly.get('fill_lines', []))}\n")
                        if poly.get('fill_lines'):
                            for i, fl in enumerate(poly['fill_lines']):
                                log_file.write(f"      Fill line {i}: {len(list(fl.coords))} points\n")
                    if poly.get('polygon'):
                        log_file.write(f"    Polygon bounds: {poly['polygon'].bounds}\n")
            
        if DEBUG_LOG_ENABLED:
            print(f"[Debug] Log written to: {log_filename}")
    except Exception as e:
        if DEBUG_LOG_ENABLED:
            print(f"[Debug] Error writing log: {e}")


def write_openings_debug_log(
    openings_data,
    z_values,
    openings_ending,
    layer_height_m,
    eps,
    log_filename="ifc_openings_debug.txt",
):
    """Write opening vs layer Z diagnostic to a file (offline analysis; debug only)."""
    if not DEBUG_LOG_ENABLED:
        return
    try:
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("DEBUG - Aberturas IFC vs capas G-code (openings_ending)\n")
            f.write("=" * 60 + "\n\n")

            f.write("[Parámetros]\n")
            f.write(f"  layer_height_m (espesor capa en m): {layer_height_m}\n")
            f.write(f"  eps (tolerancia numérica): {eps}\n")
            f.write(
                f"  Condición por capa z: (z - layer_height_m - eps) < z_max <= (z + eps)\n\n"
            )

            f.write("[Resumen]\n")
            f.write(f"  openings_data: {len(openings_data)} elemento(s)\n")
            if z_values:
                f.write(
                    f"  z_values (capas): min={min(z_values):.6f} m, "
                    f"max={max(z_values):.6f} m, total={len(z_values)}\n"
                )
            else:
                f.write("  z_values: (vacío)\n")
            capas_con = sum(1 for v in openings_ending.values() if v)
            f.write(f"  Capas con openings_ending no vacío: {capas_con}\n\n")

            f.write("[Aberturas detectadas (todas)]\n")
            f.write("-" * 40 + "\n")
            if not openings_data:
                f.write("  (ninguna)\n\n")
            else:
                for i, o in enumerate(openings_data):
                    f.write(
                        f"  [{i}] {o['type']}(id={o['id']}): "
                        f"z_min={o['z_min']:.6f} m, z_max={o['z_max']:.6f} m\n"
                    )
                f.write("\n")

            f.write("[Capas donde SÍ finaliza alguna abertura]\n")
            f.write("-" * 40 + "\n")
            zs_con = [z for z in z_values if openings_ending.get(z)]
            if not zs_con:
                f.write("  (ninguna)\n\n")
            else:
                for z in zs_con:
                    olist = openings_ending[z]
                    f.write(f"  Z={z:.6f} m:\n")
                    for o in olist:
                        f.write(
                            f"      {o['type']}(id={o['id']}) "
                            f"z_min={o['z_min']:.6f} z_max={o['z_max']:.6f}\n"
                        )
                f.write("\n")

            f.write("[Muestra de alturas de capa (z_values)]\n")
            f.write("-" * 40 + "\n")
            n = len(z_values)
            if n <= 40:
                for z in z_values:
                    tiene = "sí" if openings_ending.get(z) else "no"
                    f.write(f"  Z={z:.6f} m  finaliza_abertura={tiene}\n")
            else:
                f.write(f"  Total capas: {n} (muestra: primeras 15 y últimas 15)\n")
                for z in z_values[:15]:
                    tiene = "sí" if openings_ending.get(z) else "no"
                    f.write(f"  Z={z:.6f} m  finaliza_abertura={tiene}\n")
                f.write("  ...\n")
                for z in z_values[-15:]:
                    tiene = "sí" if openings_ending.get(z) else "no"
                    f.write(f"  Z={z:.6f} m  finaliza_abertura={tiene}\n")
                f.write("\n")

            f.write("\n[Notas]\n")
            f.write(
                "  Si openings_data es 0, revisar IFC (IfcRelFillsElement, "
                "IfcRelVoidsElement, IfcOpeningElement, IfcDoor/IfcWindow).\n"
            )
            f.write(
                "  Si hay aberturas pero capas con openings_ending=0, revisar "
                "alineación z_max de aberturas con alturas de capa del slicer.\n"
            )

        if DEBUG_LOG_ENABLED:
            print(f"[Debug] Openings diagnostic written to: {log_filename}")
    except Exception as e:
        if DEBUG_LOG_ENABLED:
            print(f"[Debug] Error writing ifc_openings_debug: {e}")


def write_wall_overlap_debug(
    polygon_data,
    step=0.1,
    log_filename="ifc_wall_overlap_debug.txt",
    min_edge_length_mm=0.1,
):
    """Detect wall overlap and shared edges per layer (debug dump file)."""
    if not DEBUG_LOG_ENABLED:
        return
    try:
        min_area = max(1e-3, float(step) ** 2 * 1e-6)
        overlaps = collect_all_wall_overlaps(
            polygon_data, min_area_mm2=min_area, step=step
        )
        shared_edges = collect_all_shared_edges(
            polygon_data,
            min_area_mm2=min_area,
            min_edge_length_mm=min_edge_length_mm,
            step=step,
        )
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("DEBUG - Solape entre muros (2D por capa, IfcWall polígonos)\n")
            f.write("=" * 60 + "\n\n")
            f.write("[Parámetros]\n")
            f.write(f"  min_area_mm2 (solape de superficie): {min_area}\n")
            f.write(
                f"  min_edge_length_mm (arista compartida, sin área): "
                f"{min_edge_length_mm}\n"
            )
            f.write("  Muros Arc_Wall (is_arc) no se comparan aquí.\n\n")

            f.write("[1] Solape de superficie (área > umbral)\n")
            f.write("-" * 40 + "\n")
            f.write(f"  Pares: {len(overlaps)}\n")
            if not overlaps:
                f.write(
                    "  (ninguno — dos huellas no comparten mancha con área positiva)\n\n"
                )
            else:
                for row in overlaps:
                    z = row["z"]
                    f.write(
                        f"  Z={z:.6f} m | {row['type_a']}(id={row['id_a']}) vs "
                        f"{row['type_b']}(id={row['id_b']})\n"
                    )
                    f.write(f"      área intersección: {row['area_mm2']:.6f} mm²\n")
                    if row.get("bounds"):
                        f.write(f"      bounds: {row['bounds']}\n")
                f.write("\n")

            f.write("[2] Aristas / bordes compartidos (área ~0, intersección tipo línea)\n")
            f.write("-" * 40 + "\n")
            f.write(
                "  Muros adyacentes comparten un segmento: posible doble trazo de "
                "contorno en esa arista (no relleno duplicado en mancha).\n"
            )
            f.write(f"  Pares con longitud de borde ≥ {min_edge_length_mm} mm: {len(shared_edges)}\n")
            if not shared_edges:
                f.write("  (ninguno bajo este umbral)\n\n")
            else:
                for row in shared_edges:
                    z = row["z"]
                    f.write(
                        f"  Z={z:.6f} m | {row['type_a']}(id={row['id_a']}) vs "
                        f"{row['type_b']}(id={row['id_b']})\n"
                    )
                    f.write(
                        f"      longitud borde común (aprox.): {row['edge_length_mm']:.3f} mm\n"
                    )
                    if row.get("bounds"):
                        f.write(f"      bounds: {row['bounds']}\n")
                f.write("\n")

            f.write("[Notas]\n")
            f.write(
                "  (1) Solape de área: riesgo claro de doble extrusión en esa zona.\n"
            )
            f.write(
                "  (2) Borde compartido: típico entre muros que se tocan; el riesgo es "
                "duplicar línea de contorno si ambos perímetros se imprimen.\n"
            )

        print(f"[Debug] Solape muros guardado en: {log_filename}")
        if overlaps:
            print(
                f"[Warning] {len(overlaps)} par(es) con solape de área — ver {log_filename}"
            )
        if shared_edges:
            print(
                f"[Info] {len(shared_edges)} par(es) con aristas compartidas "
                f"(detalle en {log_filename})"
            )
    except Exception as e:
        print(f"[Debug] Error escribiendo ifc_wall_overlap_debug: {e}")


def dxf_script(path, e, layer_tick, layer_amount, feed_rate, feed_rate_g0):
    """Process DXF file and generate G-code output.
    
    Args:
        path (str): Path to DXF file
        e (float): Extrusion amount per mm
        layer_tick (float): Layer thickness in mm
        layer_amount (int): Number of layers to generate
        feed_rate (int): Print feed rate in mm/min
        feed_rate_g0 (int): Travel feed rate in mm/min
        
    Returns:
        str: Generated G-code string
        
    Raises:
        RuntimeError: If file processing or entity generation fails
    """
    gcode_generator = GcodeGenerator()
    initial_point = Vec3(0, 0, 0)
    
    try:
        generate_entity_list(path, gcode_generator)
    except UnsupportedEntityError as ue:
        raise RuntimeError(f"Error: el archivo contiene una entidad no soportada ({ue.entity_type}).") from ue
    except FileError as fe:
        raise RuntimeError(f"No se pudo leer el archivo DXF:\n{str(fe)}") from fe
    
    main_list = gcode_generator.get_entity_list()
    entities = gcode_generator.order_entity_list(main_list, initial_point)
    machine = MachineHandler(f=feed_rate, fG0=feed_rate_g0, e=e, layer_thick=layer_tick)
    
    for i in range(layer_amount):
        machine.generate_gcode(entities, i, (layer_amount - 1) * layer_tick, 0, float("inf"))
    
    return machine.g_code


def hash_entity_list(entity_list):
    """Generate MD5 hash from entity list for caching purposes.
    
    Args:
        entity_list (list): List of G-code entities
        
    Returns:
        str: MD5 hash of entity list
    """
    raw = [
        (
            entity["command"],
            entity["param"]["id"],
            round(entity["param"]["start"].x, 5),
            round(entity["param"]["start"].y, 5),
            round(entity["param"]["end"].x, 5),
            round(entity["param"]["end"].y, 5),
            entity["param"]["layer"]
        )
        for entity in entity_list
    ]
    raw_str = json.dumps(raw, sort_keys=True)
    return hashlib.md5(raw_str.encode()).hexdigest()


def ifc_script(path, e=0, layer_tick=0.0, feed_rate=0.0, feed_rate_g0=0.0, offset=0.0, step=0.1, 
               r_angle=0, v_angle=0, radius=0, t_min=0, t_max=float("inf"), z_safe=20.0,
               start_corner="bottom_left", merge_walls_per_layer=False,
               dedupe_fill_overlap=True, unified_rect_wall_outlines=True,
               unified_rect_outline_eps=0.01,
               unified_rect_outline_snap_mm=0.05,
               dedupe_outline_segments=False,
               outline_dedupe_mm=0.02,
               route_options=None):
    """Process IFC file and generate optimized G-code with minimal travel movements.
    
    Args:
        path (str): Path to IFC file
        e (float): Extrusion amount per mm
        layer_tick (float): Layer thickness in mm
        feed_rate (int): Print feed rate in mm/min
        feed_rate_g0 (int): Travel feed rate in mm/min
        offset (float): Inward offset for fill pattern in mm
        step (float): Fill line spacing in mm
        r_angle (int): Rotation angle for fill pattern in degrees
        v_angle (int): Vertical angle for fill pattern in degrees
        radius (float): Radius parameter for fill patterns
        t_min (float): Minimum layer time in minutes
        t_max (float): Maximum layer time in minutes
        z_safe (float): Safe Z height for travel moves in mm
        start_corner (str): Starting corner - 'bottom_left', 'bottom_right', 
                           'top_left', 'top_right', or 'auto'
        merge_walls_per_layer (bool): Legacy mode: merge walls per layer and recompute fill.
        dedupe_fill_overlap (bool): Trim overlapping fill without full zigzag recompute.
        unified_rect_wall_outlines (bool): Outline from unary_union per layer (non-legacy).
        unified_rect_outline_eps (float): Ignored (compatibility); outline uses deduped edges.
        unified_rect_outline_snap_mm (float): Grid snap (mm) when merging shared edges (IFC).
        dedupe_outline_segments (bool): Experimental; True may drop valid outline segments
            when several outline_only elements share a layer.
        outline_dedupe_mm (float): Quantization (mm) when dedupe_outline_segments is True.
        route_options: Optional ``RouteOptimizeOptions`` (see ``src.utils.path_optimizer``);
            None uses defaults tuned for speed.

    Returns:
        dict: Dictionary with 'gcode', 'start_point', and 'start_description'
        
    Raises:
        RuntimeError: If file processing, entity generation, or time limits fail
    """
    start = time.time()
    try:
        sections, openings_data = ifc_parser(path)
        meshes = slicer(sections, layer_tick)
    except Exception as ex:
        raise RuntimeError(f"Error al procesar el archivo IFC: {ex}") from ex
    if DEBUG_LOG_ENABLED:
        print(f"[Timing] IFC parser + slicer: {time.time() - start:.2f}s")
    
    start = time.time()
    polygon_data = extract_layer_polygons_with_fill(
        meshes,
        step=step,
        offset=offset,
        angle=r_angle,
        v_angle=v_angle,
        radius=radius,
        merge_walls_per_layer=merge_walls_per_layer,
        dedupe_fill_overlap=dedupe_fill_overlap,
        unified_rect_wall_outlines=unified_rect_wall_outlines,
        unified_rect_outline_eps=unified_rect_outline_eps,
        unified_rect_outline_snap_mm=unified_rect_outline_snap_mm,
    )
    if DEBUG_LOG_ENABLED:
        print(f"[Timing] Polygon extraction + fill: {time.time() - start:.2f}s")
        if merge_walls_per_layer:
            print(
                "[Info] Walls merged per layer (unary_union) and fill recomputed (legacy)."
            )
        else:
            if dedupe_fill_overlap:
                print(
                    "[Info] Fill: per-wall zigzag; overlapping segments trimmed at end."
                )
            if unified_rect_wall_outlines:
                print(
                    "[Info] Rect wall outline: unique edges per layer (snap "
                    f"{unified_rect_outline_snap_mm} mm)."
                )
                if dedupe_outline_segments:
                    print(
                        "[Warning] dedupe_outline_segments=True may remove valid outline "
                        f"segments (quantize {outline_dedupe_mm} mm)."
                    )

    write_debug_log(sections, meshes, polygon_data)
    write_wall_overlap_debug(polygon_data, step=step)

    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for z, polygons in polygon_data.items():
        for poly_data in polygons:
            for bp in poly_data.get('boundary_points', []):
                min_x = min(min_x, bp.x)
                min_y = min(min_y, bp.y)
                max_x = max(max_x, bp.x)
                max_y = max(max_y, bp.y)
    
    if min_x == float('inf'):
        min_x, min_y, max_x, max_y = 0, 0, 0, 0
    
    corners = {
        'bottom_left': (min_x, min_y, "Inferior izquierda"),
        'bottom_right': (max_x, min_y, "Inferior derecha"),
        'top_left': (min_x, max_y, "Superior izquierda"),
        'top_right': (max_x, max_y, "Superior derecha"),
    }
    
    if start_corner == 'auto':
        first_centroid = None
        for z in sorted(polygon_data.keys()):
            if polygon_data[z]:
                first_centroid = polygon_data[z][0].get('centroid')
                break
        
        if first_centroid:
            best_corner = 'bottom_left'
            best_dist = float('inf')
            for corner_name, (cx, cy, _) in corners.items():
                dist = ((first_centroid.x - cx)**2 + (first_centroid.y - cy)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best_corner = corner_name
            start_corner = best_corner
        else:
            start_corner = 'bottom_left'
    
    corner_x, corner_y, corner_desc = corners[start_corner]
    initial_point = Vec3(corner_x, corner_y, 0)
    
    if DEBUG_LOG_ENABLED:
        print(f"[Info] Start point: X={corner_x:.2f}, Y={corner_y:.2f} ({corner_desc})")
    
    start = time.time()
    gcode_generator = GcodeGenerator()
    
    entities = gcode_generator.generate_optimized_entities(
        polygon_data,
        initial_point,
        dedupe_outline_segments=dedupe_outline_segments,
        outline_dedupe_mm=outline_dedupe_mm,
        route_options=route_options,
    )
    if DEBUG_LOG_ENABLED:
        print(f"[Timing] Entity optimization: {time.time() - start:.2f}s")
    
    continuity_warnings = gcode_generator.get_continuity_warnings()
    if continuity_warnings and DEBUG_LOG_ENABLED:
        print(f"[Warning] {len(continuity_warnings)} continuity issue(s):")
        for w in continuity_warnings[:10]:
            print(f"  {w}")
        if len(continuity_warnings) > 10:
            print(f"  ... and {len(continuity_warnings) - 10} more")
    
    layer_entities = defaultdict(list)
    for entity in entities:
        z = round(entity['param']['start'].z, 5)
        layer_entities[z].append(entity)
    
    z_values = sorted(layer_entities.keys())
    layer_amount = len(z_values)
    layer_height_m = layer_tick / 1000.0

    eps = 1e-6
    openings_ending = {
        z: [o for o in openings_data
            if (z - layer_height_m - eps < o["z_max"] <= z + eps)]
        for z in z_values
    }

    write_openings_debug_log(
        openings_data,
        z_values,
        openings_ending,
        layer_height_m,
        eps,
        log_filename="ifc_openings_debug.txt",
    )
    layers_with_openings = sum(1 for olist in openings_ending.values() if olist)
    if DEBUG_LOG_ENABLED:
        print(
            f"[Info] Openings: {len(openings_data)} detected, "
            f"{layers_with_openings} layer(s) with end-of-opening comments "
            f"(see ifc_openings_debug.txt when debug enabled)"
        )
        print(f"[Info] Layers: {layer_amount}, entities: {len(entities)}")

    start = time.time()
    machine = MachineHandler(
        f=feed_rate, fG0=feed_rate_g0, e=e, layer_thick=layer_tick, z_safe=z_safe,
        start_point=(corner_x, corner_y), start_description=corner_desc
    )
    error_flag = False

    for i, z in enumerate(z_values):
        try:
            machine.generate_gcode(
                layer_entities[z], i, (layer_amount - 1) * layer_tick, t_min, t_max,
                openings_ending=openings_ending.get(z, [])
            )
        except Exception as e: 
            error_flag = True
            raise RuntimeError(f'Error al generar el código G, tiempo de capa superado, revisar parámetros o modelo: {e}')
        if error_flag: 
            break
    
    if DEBUG_LOG_ENABLED:
        print(f"[Timing] G-code generation: {time.time() - start:.2f}s")
        print("[Done] G-code generated")
    
    return {
        'gcode': machine.g_code,
        'start_point': {'x': corner_x, 'y': corner_y},
        'start_description': corner_desc
    }

