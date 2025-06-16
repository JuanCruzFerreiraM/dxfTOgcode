import ezdxf
from ezdxf.math import OCS, Matrix44
from src.core.gcode_generator import GcodeGenerator
class FileError(Exception):
    """Excepción personalizada para errores de archivo."""
    pass

def generate_entity_list(filename, gcode_generator):
    """
    Reads a DXF file and generates a list of entities for G-code generation.

    #### Args:
    - filename (str): Path to the DXF file to be processed.
    - gcode_generator (GcodeGenerator): Instance of GcodeGenerator to store the generated entities.

    #### Modifies:
    - gcode_generator.entity_list (list): Adds the generated entities from the DXF file.

    #### Raises:
    - FileError: If the DXF file cannot be read or processed.
    """
    try:
        doc = ezdxf.readfile(filename)
    except Exception as e:
        raise FileError(f'File Error. Please retry. {e}') from e

    model_space = doc.modelspace()
    id_entity = 0

    for entity in model_space:
        if entity.dxftype() == 'LINE':
            gcode_generator.line_entity(entity.dxf.start, entity.dxf.end, entity.dxf.layer, id_entity)
        elif entity.dxftype() == 'ARC':
            gcode_generator.arc_entity(entity.dxf.center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle, entity.dxf.layer, id_entity)
        # elif entity.dxftype() == 'LWPOLYLINE':  # Not implemented yet
        #     gcode_generator.lwpolyline_entity(entity)
        else:
            print(f'No support for entity {entity.dxftype()}')