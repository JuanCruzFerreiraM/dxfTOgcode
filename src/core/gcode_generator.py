from ezdxf.math import Vec3
from math import sin, cos, radians, atan
from src.utils.geometry import is_ccw, bulge_to_center
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
        command = 3 if is_ccw(start_angle, end_angle) else 2
        command_data = {
            'command': 'G2-3',
            'param': {
                'start': start_point,
                'end': end_point,
                'i': i,
                'j': j,
                'value': command
            }
        }
        self.entity_list.append(command_data)
    
    def lwpolyline_entity(self, point_list): #is for lwpolyline. Conciderar si es necesario considerar el ancho.
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