from pathlib import Path
from src.core.dxf_parser import generate_entity_list, FileError,UnsupportedEntityError
from src.core.gcode_generator import GcodeGenerator
from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3;

def dxf_script(path,e,layer_tick, layer_amount, feed_rate, feed_rate_g0):
    gcode_generator = GcodeGenerator()
    initial_point = Vec3(0,0,0)
    try:
        generate_entity_list(path, gcode_generator)
    except UnsupportedEntityError as ue:
        raise RuntimeError(f"Error: el archivo contiene una entidad no soportada ({ue.entity_type}).") from ue
    except FileError as fe:
        raise RuntimeError(f"No se pudo leer el archivo DXF:\n{str(fe)}") from fe
    main_list = gcode_generator.get_entity_list()
    entitys = gcode_generator.order_entity_list(main_list,initial_point)
    machine = MachineHandler(f = feed_rate, fG0= feed_rate_g0, e=e, layer_thick=layer_tick)
    for i in range(0,layer_amount):
        machine.generate_gcode(entitys,i, (layer_amount - 1) * layer_tick)
    return machine.g_code
