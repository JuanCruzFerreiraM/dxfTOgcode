import ezdxf
from ezdxf.math import OCS, Matrix44
from src.core.gcode_generator import GcodeGenerator


class FileError(Exception):
    """Exception raised for DXF file processing errors."""
    pass


class UnsupportedEntityError(Exception):
    """Exception raised for unsupported DXF entity types."""
    
    def __init__(self, entity_type):
        """Initialize with specific entity type that caused the error.
        
        Args:
            entity_type (str): DXF entity type that is not supported
        """
        super().__init__(f"Entidad DXF no soportada: {entity_type}")
        self.entity_type = entity_type


def generate_entity_list(filename, gcode_generator):
    """Read DXF file and generate entities for G-code generation.

    Args:
        filename (str): Path to the DXF file to process
        gcode_generator (GcodeGenerator): Generator instance to store entities

    Raises:
        FileError: If DXF file cannot be read or processed
        UnsupportedEntityError: If file contains unsupported entity types
        
    Modifies:
        gcode_generator.entity_list: Adds generated entities from DXF file
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
