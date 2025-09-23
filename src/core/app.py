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
from src.core.ifc.parameter_generator import extract_layer_polygons_with_fill

def dxf_script(path, e, layer_tick, layer_amount, feed_rate, feed_rate_g0):
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

def ifc_script(path, e, layer_tick, feed_rate, feed_rate_g0, offset=0.0, step=0.1, r_angle=0, v_angle=0, radius=0, t_min = 0, t_max = float("inf")):
    """
    Script principal optimizado para minimizar movimientos G0.
    """
    print("[Inicio] Procesando archivo IFC...")
    
    # 1. IFC Parser + Slicer
    start = time.time()
    try:
        sections = ifc_parser(path)
        meshes = slicer(sections, layer_tick)
    except Exception as ex:
        raise RuntimeError(f"Error al procesar el archivo IFC: {ex}") from ex
    print(f"[Tiempo] IFC Parser + Slicer: {time.time() - start:.2f} segundos")
    
    # 2. Extraer polígonos con relleno
    start = time.time()
    polygon_data = extract_layer_polygons_with_fill(
        meshes, step=step, offset=offset, angle=r_angle, v_angle=v_angle, radius=radius
    )
    print(f"[Tiempo] Extracción de polígonos y relleno: {time.time() - start:.2f} segundos")
    
    # 3. Generación optimizada de entidades
    start = time.time()
    gcode_generator = GcodeGenerator()
    initial_point = Vec3(0, 0, 0)
    
    # Nueva función que optimiza el recorrido y genera entidades
    entities = gcode_generator.generate_optimized_entities(polygon_data, initial_point)
    print(f"[Tiempo] Optimización y generación de entidades: {time.time() - start:.2f} segundos")
    
    # 4. Agrupar entidades por capa
    layer_entities = defaultdict(list)
    for entity in entities:
        z = round(entity['param']['start'].z, 5)
        layer_entities[z].append(entity)
    
    z_values = sorted(layer_entities.keys())
    layer_amount = len(z_values)
    
    print(f"[Info] Total de capas generadas: {layer_amount}")
    print(f"[Info] Total de entidades generadas: {len(entities)}")
    
    # 5. Generación de G-code
    start = time.time()
    machine = MachineHandler(f=feed_rate, fG0=feed_rate_g0, e=e, layer_thick=layer_tick)
    error_flag = False
    for i, z in enumerate(z_values):
        try: 
            machine.generate_gcode(layer_entities[z], i, (layer_amount - 1) * layer_tick,t_min,t_max)
        except Exception as e: 
            error_flag = True
            raise RuntimeError(f'Error al generar el código G, tiempo de capa superado, revisar parámetros o modelo: {e}')
        if (error_flag): 
            break
    
    print(f"[Tiempo] Generación de G-code: {time.time() - start:.2f} segundos")
    
    
    
    print("[Fin] Archivo G-code generado: test_outputs/g0opt.gcode")
    
    return machine.g_code

