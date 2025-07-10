import ezdxf
from ezdxf.math import OCS, Matrix44
from src.core.gcode_generator import GcodeGenerator
class FileError(Exception):
    """Excepción personalizada para errores de archivo."""
    pass

class UnsupportedEntityError(Exception):
    """Excepción para entidades DXF no soportadas."""
    def __init__(self, entity_type):
        super().__init__(f"Entidad DXF no soportada: {entity_type}")
        self.entity_type = entity_type

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
            id_entity += 1
        elif entity.dxftype() == 'ARC':
            gcode_generator.arc_entity(entity.dxf.center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle, entity.dxf.layer, id_entity)
            id_entity += 1
        else:
            raise UnsupportedEntityError(entity.dxftype())
