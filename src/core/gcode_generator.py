from ezdxf.math import Vec3
from math import sin, cos, radians, atan
from src.utils.geometry import is_ccw, bulge_to_center
from src.utils.graph import traversal_order

class InvalidPointError(Exception):
    """Excepción lanzada cuando un punto tiene valores inválidos."""
    pass

class GcodeGenerator:
    def __init__ (self):
        self.entity_list = []

    def line_entity(self, start_point, end_point, layer, id):
        # Validar que los puntos no sean None
        if start_point is None or end_point is None:
            raise InvalidPointError(f"Invalid point detected: start_point={start_point}, end_point={end_point}")
        
        # Validar que las coordenadas no sean None
        if any(coord is None for coord in [start_point.x, start_point.y, start_point.z, end_point.x, end_point.y, end_point.z]):
            raise InvalidPointError(f"Invalid point detected: start_point={start_point}, end_point={end_point}")
        
        command_data = {
            'command': 'G1',
            'param': {
                'start': start_point,
                'end': end_point,
                'layer': layer,
                'id': id
            }
        }
        self.entity_list.append(command_data)
        
    def arc_entity(self, center, radius, start_angle, end_angle, layer, id):
        # Validar que el centro no sea None
        if center is None:
            raise InvalidPointError(f"Invalid center detected: center={center}")
        
        # Validar que las coordenadas no sean None
        if any(coord is None for coord in [center.x, center.y, center.z, radius, start_angle, end_angle]):
            raise InvalidPointError(f"Invalid center detected: center={center}")
        
        sx = radius * cos(radians(start_angle)) + center.x
        sy = radius * sin(radians(start_angle)) + center.y
        ex = radius * cos(radians(end_angle)) + center.x
        ey = radius * sin(radians(end_angle)) + center.y
        
        if any(coord is None for coord in [sx, sy, ex, ey]):
            raise InvalidPointError(f"Invalid calculated points: start=({sx}, {sy}), end=({ex}, {ey})")
        
        command_data = {
            'command': 'G2-3',
            'param': {
                'start': Vec3(sx, sy, 0),
                'end': Vec3(ex, ey, 0),
                'i': center.x - sx,
                'j': center.y - sy,
                'value': 3 if is_ccw(start_angle, end_angle) else 2,
                'layer': layer,
                'id': id
            }
        }
        self.entity_list.append(command_data)
    
    
    def adjust_to_reference(self): #Por ahora retorna la esquina inferior izquierda, pero se puede parametrizar para elegir un punto según la maquina
        reference = min(self.entity_list,key=lambda e: (e['param']['start'].x, e['param']['start'].y))['param']['start']
        for entity in self.entity_list:
            entity['param']['start'] = entity['param']['start'] - reference
            entity['param']['end'] = entity['param']['end'] - reference

           

    def order_entity_list(self,entity_list, initial_point): 
        entity_order = traversal_order(entity_list,initial_point)
    
        id_to_position = {entity_id: i for i, entity_id in enumerate(entity_order)}
        ordered_entity_list = sorted(entity_list,key=lambda entity: id_to_position.get(entity['param']['id'], float('inf')))
    
        return ordered_entity_list
    
    def get_entity_list(self):
        self.adjust_to_reference() 
        return self.entity_list
    
    
    #Esta función por el momento no tiene uso, queda por si las dudas ya que en principio funciona bien.
    def lwpolyline_entity(self, point_list): #Agregar manejo de layers
        #pensar en refactoring para mejorar legibilidad 
        prev_point = Vec3(0,0,0)
        if (point_list.close):
            initial_point = point_list[0]
        prev_point = point_list[0]
        bulge = point_list[0].bulge
        for actual_point in point_list[1:]:
            if (bulge == 0):
                command_data = {
                    'command': 'G1',
                    'param': {
                        'start': prev_point,
                        'end': actual_point
                    }
                }
                self.entity_list.append(command_data)
            else: 
                center = bulge_to_center(actual_point, prev_point, bulge)
                i = center.x - prev_point.x
                j = center.y - prev_point.y
                command = 3 if bulge > 0 else 2
                command_data = {
                    'command': 'G2-3',
                    'param': {
                        'start': prev_point,
                        'end': actual_point,
                        'i': i,
                        'j': j,
                        'value': command
                     }
                }
                self.entity_list.append(command_data)
            prev_point = actual_point
            bulge = actual_point.bulge        
        if (point_list.close):
            actual_point = initial_point
            if (bulge == 0):
                command_data = {
                    'command': 'G1',
                    'param': {
                        'start': prev_point,
                        'end': actual_point
                    }
                }
                self.entity_list.append(command_data)
            else: 
                center = bulge_to_center(actual_point, prev_point, bulge)
                i = center.x - prev_point.x
                j = center.y - prev_point.y
                command = 3 if bulge > 0 else 2
                command_data = {
                    'command': 'G2-3',
                    'param': {
                        'start': prev_point,
                        'end': actual_point,
                        'i': i,
                        'j': j,
                        'value': command
                     }
                }
                self.entity_list.append(command_data)