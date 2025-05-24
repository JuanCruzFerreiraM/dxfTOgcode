from ezdxf.math import Vec3
from math import sin, cos, radians, atan
from src.utils.geometry import is_ccw
class GcodeGenerator:
    def __init__ (self):
        self.entity_list = []
    
    def line_entity(self, start_point, end_point):
        command_data = {
            'command': 'G1',
            'param': {
                'start': start_point,
                'end': end_point
            }
        }
        self.entity_list.append(command_data)
        
    def arc_entity(self,center, radius, start_angle, end_angle):
        start_point = Vec3(0,0,0)
        end_point = Vec3(0,0,0)
        start_point.x = radius * cos(radians(start_angle)) + center.x
        start_point.y = radius * cos(radians(start_angle)) + center.y
        end_point.x = radius * sin(radians(end_angle)) + center.x
        end_point.y = radius * sin(radians(end_angle)) + center.y
        i = center.x - start_point.x
        j = center.y - start_point.y
        command = 'G3' if is_ccw(start_angle, end_angle) else 'G2'
        command_data = {
            'command': command,
            'param': {
                'start': start_point,
                'end': end_point,
                'i': i,
                'j': j
            }
        }
        self.entity_list.append(command_data)
    
    def lwpolyline_entity(self,): #is for lwpolyline. Conciderar si es necesario considerar el ancho.
        