from ezdxf.math import Vec3
from math import sin, cos, radians, atan
from src.utils.geometry import is_ccw, bulge_to_center, distance
from src.utils.path_optimizer import optimize_layer_traversal
import networkx as nx


class InvalidPointError(Exception):
    pass


class GcodeGenerator:
    def __init__(self):
        self.entity_list = []
        self.id_entity_counter = 0
        self.dxf_reference_point = Vec3(0, 0, 0)
    
    
    def find_optimal_outline_start(self, polygon_coords, entry_point):
        """
        Encuentra el índice óptimo para empezar el outline desde el punto más cercano.
        """
        min_dist = float('inf')
        best_idx = 0
        
        for i, coord in enumerate(polygon_coords[:-1]):  # Excluir último punto duplicado
            point = Vec3(coord[0], coord[1], entry_point.z)
            dist = point.distance(entry_point)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        
        return best_idx
    
    
    def generate_outline_from_point(self, polygon, entry_point, layer, outline_id):
        """
        Genera outline empezando desde el punto más cercano al entry_point.
        """
        coords = list(polygon.exterior.coords)
        if len(coords) < 2:
            return []
        
        # Encontrar mejor punto de inicio
        start_idx = self.find_optimal_outline_start(coords, entry_point)
        
        # Reordenar coordenadas para empezar desde start_idx
        ordered_coords = coords[start_idx:-1] + coords[:start_idx+1]
        
        entities = []
        for i in range(len(ordered_coords) - 1):
            p1 = Vec3(ordered_coords[i][0], ordered_coords[i][1], entry_point.z)
            p2 = Vec3(ordered_coords[i+1][0], ordered_coords[i+1][1], entry_point.z)
            
            if p1.distance(p2) > 1e-6:  # Evitar líneas de longitud cero
                entities.append({
                    'command': 'G1',
                    'param': {
                        'start': p1,
                        'end': p2,
                        'layer': layer,
                        'id': self.id_entity_counter,
                        'outline_id': outline_id
                    }
                })
                self.id_entity_counter += 1
        
        # Agregar outlines interiores (huecos)
        for interior in polygon.interiors:
            interior_coords = list(interior.coords)
            for i in range(len(interior_coords) - 1):
                p1 = Vec3(interior_coords[i][0], interior_coords[i][1], entry_point.z)
                p2 = Vec3(interior_coords[i+1][0], interior_coords[i+1][1], entry_point.z)
                
                if p1.distance(p2) > 1e-6:
                    entities.append({
                        'command': 'G1',
                        'param': {
                            'start': p1,
                            'end': p2,
                            'layer': layer,
                            'id': self.id_entity_counter,
                            'outline_id': outline_id
                        }
                    })
                    self.id_entity_counter += 1
        
        return entities
    
    
    def generate_fill_entities(self, fill_lines, layer, outline_id, z):
        """
        Genera entidades de relleno.
        """
        entities = []
        for line in fill_lines:
            coords = list(line.coords)
            for i in range(len(coords) - 1):
                p1 = Vec3(coords[i][0], coords[i][1], z)
                p2 = Vec3(coords[i+1][0], coords[i+1][1], z)
                
                if p1.distance(p2) > 1e-6:
                    entities.append({
                        'command': 'G1',
                        'param': {
                            'start': p1,
                            'end': p2,
                            'layer': 'fill',
                            'id': self.id_entity_counter,
                            'outline_id': outline_id
                        }
                    })
                    self.id_entity_counter += 1
        
        return entities
    
    
    def generate_optimized_entities(self, polygon_data, initial_point=Vec3(0, 0, 0)):
        """
        Genera entidades en orden optimizado para minimizar G0.
        """
        self.entity_list = []
        self.id_entity_counter = 0
        
        # Optimizar recorrido
        optimized_traversal = optimize_layer_traversal(polygon_data, initial_point)
        
        for z in sorted(optimized_traversal.keys()):
            sequence = optimized_traversal[z]
            
            for step in sequence:
                polygon_data_item = step['polygon_data']
                entry_point = step['entry_point']
                
                polygon = polygon_data_item['polygon']
                fill_lines = polygon_data_item.get('fill_lines', [])
                outline_id = step['polygon_index']
                
                # Generar outline optimizado
                outline_entities = self.generate_outline_from_point(
                    polygon, entry_point, 'outline', outline_id
                )
                self.entity_list.extend(outline_entities)
                
                # Generar fill inmediatamente después
                fill_entities = self.generate_fill_entities(
                    fill_lines, 'fill', outline_id, z
                )
                self.entity_list.extend(fill_entities)
        
        return self.entity_list
    
    
    # Mantener métodos existentes para compatibilidad
    def line_entity(self, start_point, end_point, layer, id, outline_id=-1):
        entity = {
            'command': 'G1',
            'param': {
                'start': start_point,
                'end': end_point,
                'layer': layer,
                'id': id,
                'outline_id': outline_id
            }
        }
        self.entity_list.append(entity)
    
    
    def arc_entity(self, center, radius, start_angle, end_angle, layer, id):
        start_x = center.x + radius * cos(radians(start_angle))
        start_y = center.y + radius * sin(radians(start_angle))
        end_x = center.x + radius * cos(radians(end_angle))
        end_y = center.y + radius * sin(radians(end_angle))
        
        start_point = Vec3(start_x, start_y, center.z)
        end_point = Vec3(end_x, end_y, center.z)
        
        i = center.x - start_x
        j = center.y - start_y
        
        if is_ccw(start_angle, end_angle):
            value = 3
        else:
            value = 2
        
        entity = {
            'command': 'G2-3',
            'param': {
                'start': start_point,
                'end': end_point,
                'i': i,
                'j': j,
                'value': value,
                'layer': layer,
                'id': id
            }
        }
        self.entity_list.append(entity)
    
    
    def adjust_to_reference(self):
        if self.entity_list:
            first_entity = self.entity_list[0]
            self.dxf_reference_point = first_entity['param']['start']
    
    
    def order_entity_list(self, entity_list, initial_point):
        """
        Método mantenido para compatibilidad - ahora simplificado.
        """
        return entity_list  # Ya están optimizados
    
    
    def get_entity_list(self):
        return self.entity_list