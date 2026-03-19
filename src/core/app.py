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


# Flag para habilitar debug log (cambiar a False en producción)
DEBUG_LOG_ENABLED = True


def write_debug_log(sections, meshes, polygon_data, log_filename="debug_log.txt"):
    """Escribe información de debug a un archivo de log."""
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
            
            # Meshes del slicer
            log_file.write("[2] Slicer - Meshes/Slices:\n")
            log_file.write("-"*40 + "\n")
            for i, mesh_slice in enumerate(meshes):
                log_file.write(f"Slice {i}: Z={mesh_slice.get('z')}, Type={mesh_slice.get('type')}\n")
                if 'sections' in mesh_slice:
                    log_file.write(f"  Secciones: {len(mesh_slice['sections'])}\n")
                    pprint.pprint(mesh_slice['sections'], stream=log_file)
            log_file.write("\n")
            
            # Polygon data
            log_file.write("[3] Parameter Generator - Polygon Data:\n")
            log_file.write("-"*40 + "\n")
            for z, polys in polygon_data.items():
                log_file.write(f"Z={z}: {len(polys)} elementos\n")
                for poly in polys:
                    log_file.write(f"  - Type: {poly.get('type')}, ID: {poly.get('id')}\n")
                    if poly.get('is_arc'):
                        log_file.write(f"    Arc Data:\n")
                        pprint.pprint(poly.get('arc_data'), stream=log_file)
                        log_file.write(f"    Fill lines count: {len(poly.get('fill_lines', []))}\n")
                        if poly.get('fill_lines'):
                            for i, fl in enumerate(poly['fill_lines']):
                                log_file.write(f"      Fill line {i}: {len(list(fl.coords))} points\n")
                    if poly.get('polygon'):
                        log_file.write(f"    Polygon bounds: {poly['polygon'].bounds}\n")
            
        print(f"[Debug] Log guardado en: {log_filename}")
    except Exception as e:
        print(f"[Debug] Error escribiendo log: {e}")


def write_openings_debug_log(
    openings_data,
    z_values,
    openings_ending,
    layer_height_m,
    eps,
    log_filename="ifc_openings_debug.txt",
):
    """Escribe diagnóstico de aberturas vs capas Z a un archivo para análisis offline."""
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

        print(f"[Debug] Diagnóstico aberturas guardado en: {log_filename}")
    except Exception as e:
        print(f"[Debug] Error escribiendo ifc_openings_debug: {e}")


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
               start_corner="bottom_left"):
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
        
    Returns:
        dict: Dictionary with 'gcode', 'start_point', and 'start_description'
        
    Raises:
        RuntimeError: If file processing, entity generation, or time limits fail
    """
    print("[Inicio] Procesando archivo IFC...")
    
    start = time.time()
    try:
        sections, openings_data = ifc_parser(path)
        meshes = slicer(sections, layer_tick)
    except Exception as ex:
        raise RuntimeError(f"Error al procesar el archivo IFC: {ex}") from ex
    print(f"[Tiempo] IFC Parser + Slicer: {time.time() - start:.2f} segundos")
    
    start = time.time()
    polygon_data = extract_layer_polygons_with_fill(
        meshes, step=step, offset=offset, angle=r_angle, v_angle=v_angle, radius=radius
    )
    print(f"[Tiempo] Extracción de polígonos y relleno: {time.time() - start:.2f} segundos")
    
    # Escribir debug log
    write_debug_log(sections, meshes, polygon_data)
    
    # Calcular bounding box del modelo para determinar punto de inicio
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for z, polygons in polygon_data.items():
        for poly_data in polygons:
            for bp in poly_data.get('boundary_points', []):
                min_x = min(min_x, bp.x)
                min_y = min(min_y, bp.y)
                max_x = max(max_x, bp.x)
                max_y = max(max_y, bp.y)
    
    # Si no hay datos, usar origen
    if min_x == float('inf'):
        min_x, min_y, max_x, max_y = 0, 0, 0, 0
    
    # Definir esquinas del modelo
    corners = {
        'bottom_left': (min_x, min_y, "Inferior izquierda"),
        'bottom_right': (max_x, min_y, "Inferior derecha"),
        'top_left': (min_x, max_y, "Superior izquierda"),
        'top_right': (max_x, max_y, "Superior derecha"),
    }
    
    # Determinar punto de inicio
    if start_corner == 'auto':
        # Encontrar la esquina más cercana al centroide del primer polígono
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
    
    print(f"[Info] Punto de inicio: X={corner_x:.2f}, Y={corner_y:.2f} ({corner_desc})")
    
    start = time.time()
    gcode_generator = GcodeGenerator()
    
    entities = gcode_generator.generate_optimized_entities(polygon_data, initial_point)
    print(f"[Tiempo] Optimización y generación de entidades: {time.time() - start:.2f} segundos")
    
    # Mostrar warnings de continuidad si los hay
    continuity_warnings = gcode_generator.get_continuity_warnings()
    if continuity_warnings:
        print(f"[Warning] Se detectaron {len(continuity_warnings)} problemas de continuidad:")
        for w in continuity_warnings[:10]:  # Mostrar máximo 10
            print(f"  {w}")
        if len(continuity_warnings) > 10:
            print(f"  ... y {len(continuity_warnings) - 10} más")
    
    layer_entities = defaultdict(list)
    for entity in entities:
        z = round(entity['param']['start'].z, 5)
        layer_entities[z].append(entity)
    
    z_values = sorted(layer_entities.keys())
    layer_amount = len(z_values)
    layer_height_m = layer_tick / 1000.0

    # Tolerancia numérica para comparación z_max con alturas de capa (metros)
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
    print(
        f"[Info] Aberturas: {len(openings_data)} detectada(s), "
        f"{layers_with_openings} capa(s) con comentario de finalización "
        f"(detalle en ifc_openings_debug.txt)"
    )

    print(f"[Info] Total de capas generadas: {layer_amount}")
    print(f"[Info] Total de entidades generadas: {len(entities)}")

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
    
    print(f"[Tiempo] Generación de G-code: {time.time() - start:.2f} segundos")
    print("[Fin] Archivo G-code generado")
    
    return {
        'gcode': machine.g_code,
        'start_point': {'x': corner_x, 'y': corner_y},
        'start_description': corner_desc
    }

