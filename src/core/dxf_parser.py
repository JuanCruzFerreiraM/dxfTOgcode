import ezdxf
from ezdxf.math import OCS, Matrix44
from src.core.gcode_generator import GcodeGenerator
class FileError(Exception):
    """Excepción personalizada para errores de archivo."""
    pass

def generate_entity_list(filename,gcode_generator): #Estudiar bien el modelo coordenado de dxf para poder entender los cambios necesarios. Sobre todo para diferentes layers
    #Etapa 2
    try: 
        doc = ezdxf.readfile(filename)
    except Exception as e:
        raise FileError(f'File Error. Please retry. {e}') from e
    
    model_space = doc.modelspace()
    
    for entity in  model_space:
        if (entity.dxftype() == 'LINE'):
            gcode_generator.line_entity(entity.dxf.start, entity.dxf.end, entity.dxf.layer)
        elif (entity.dxftype() == 'ARC'):
            gcode_generator.arc_entity(entity.dxf.center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle, entity.dxf.layer)
        elif (entity.dxftype() == 'LWPOLYLINE'):
            gcode_generator.lwpolyline_entity(entity)
        else: 
            print(f'No support for entity {entity.deftype()}')