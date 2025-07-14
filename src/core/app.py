from pathlib import Path
from src.core.dxf.dxf_parser import generate_entity_list, FileError, UnsupportedEntityError
from src.core.ifc.ifc_parser import ifc_parser
from src.core.ifc.parameter_generator import generate_gcode_from_meshes
from src.core.ifc.slicer import slicer
from src.core.gcode_generator import GcodeGenerator
from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3
from collections import defaultdict
import hashlib
import json
import time

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
        machine.generate_gcode(entities, i, (layer_amount - 1) * layer_tick)
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

def ifc_script(path, e, layer_tick, feed_rate, feed_rate_g0, offset=0.0, step=0.1):
    gcode_generator = GcodeGenerator()
    initial_point = Vec3(0, 0, 0)

    start = time.time()
    try:
        sections = ifc_parser(path)
        meshes = slicer(sections, layer_tick)
    except Exception as ex:
        raise RuntimeError(f"Error al procesar el archivo IFC: {ex}") from ex
    print(f"[Tiempo] IFC Parser + Slicer: {time.time() - start:.2f} segundos")

    start = time.time()
    generate_gcode_from_meshes(gcode_generator, meshes, step=step, offset=offset, start_id=0)
    print(f"[Tiempo] Generate G-code from meshes: {time.time() - start:.2f} segundos")

    start = time.time()
    main_list = gcode_generator.get_entity_list()
    entities = gcode_generator.order_entity_list(main_list, initial_point)
    print(f"[Tiempo] Ordenamiento DFS: {time.time() - start:.2f} segundos")

    layer_entities = defaultdict(list)
    for entity in entities:
        z = round(entity['param']['start'].z, 5)
        layer_entities[z].append(entity)

    z_values = sorted(layer_entities.keys())
    layer_amount = len(z_values)

    start = time.time()
    machine = MachineHandler(f=feed_rate, fG0=feed_rate_g0, e=e, layer_thick=layer_tick)

    for i, z in enumerate(z_values):
        print(f"Capa {i} (z = {z})")
        machine.generate_gcode(layer_entities[z], i, (layer_amount - 1) * layer_tick)
    print(f"[Tiempo] Generación final de G-code: {time.time() - start:.2f} segundos")

    return machine.g_code

if __name__ == "__main__":
    ifc_path = "src/core/ifc/AC20-FZK-Haus.ifc"
    e_param = 0.05
    layer_thickness = 20
    feed_rate = 1500
    feed_rate_g0 = 3000
    offset_fill = 0.01
    step_fill = 0.1

    gcode_output = ifc_script(
        path=ifc_path,
        e=e_param,
        layer_tick=layer_thickness,
        feed_rate=feed_rate,
        feed_rate_g0=feed_rate_g0,
        offset=offset_fill,
        step=step_fill
    )
    print("----- G-code generado -----\n")
    # Guardar el G-code en un archivo .gcode
    output_path = "/home/juan-ferreira/PPS/dxfTOgcode/outputs/text/generated_code.gcode"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(gcode_output)

    print(f"\nArchivo G-code guardado en: {output_path}")
