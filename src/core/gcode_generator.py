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
        """
        Generates a G-code command for a straight line entity.

        #### Args:
        - start_point (Vec3): The initial point of the line.
        - end_point (Vec3): The end point of the line.
        - layer (str): The layer where the entity is located.
        - id (int): Unique identifier for the entity.

        #### Modifies:
        - self.entity_list (list): Adds the generated G-code command to the list.
        """
        if start_point is None or end_point is None:
            raise InvalidPointError(f"Invalid point detected: start_point={start_point}, end_point={end_point}")
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
        """
        Generates a G-code command for an arc entity.

        #### Args:
        - center (Vec3): The center point of the arc.
        - radius (float): The radius of the arc.
        - start_angle (float): The starting angle of the arc (in degrees).
        - end_angle (float): The ending angle of the arc (in degrees).
        - layer (str): The layer where the entity is located.
        - id (int): Unique identifier for the entity.

        #### Modifies:
        - self.entity_list (list): Adds the generated G-code command to the list.

        #### Raises:
        - InvalidPointError: If the center or calculated points are invalid.
        """
        if center is None:
            raise InvalidPointError(f"Invalid center detected: center={center}")
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
    
    
    def adjust_to_reference(self):
        """
        Adjusts all entities to a reference point (bottom-left corner).

        #### Modifies:
        - self.entity_list (list): Updates the start and end points of all entities to be relative to the reference point.
        """
        reference = min(self.entity_list, key=lambda e: (e['param']['start'].x, e['param']['start'].y))['param']['start']
        for entity in self.entity_list:
            entity['param']['start'] = entity['param']['start'] - reference
            entity['param']['end'] = entity['param']['end'] - reference

           

    def order_entity_list(self, entity_list, initial_point):
        """
        Orders the list of entities based on a graph algorithm.

        #### Args:
        - entity_list (list): List of entities to be ordered.
        - initial_point (Vec3): The starting point for ordering.

        #### Modifies:
        - self.entity_list (list): Updates the internal entity list to follow the order.

        #### Returns:
        - list: Ordered list of entities.
        """
        ordered_ids = traversal_order(entity_list, initial_point)
        id_to_entity = {entity['param']['id']: entity for entity in entity_list}
        ordered_list = [id_to_entity[i] for i in ordered_ids if i in id_to_entity]
        self.entity_list = ordered_list
        return ordered_list
    
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