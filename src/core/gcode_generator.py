from ezdxf.math import Vec3
from math import sin, cos, radians, atan
from src.utils.geometry import is_ccw, bulge_to_center, distance
from src.utils.path_optimizer import optimize_layer_traversal
import networkx as nx


class InvalidPointError(Exception):
    """Exception raised for invalid point coordinates."""
    pass


class GcodeGenerator:
    """Generates G-code entities from geometric data with path optimization."""
    
    def __init__(self):
        """Initialize GcodeGenerator with empty entity list and counters."""
        self.entity_list = []
        self.id_entity_counter = 0
        self.dxf_reference_point = Vec3(0, 0, 0)
    
    
    def find_optimal_outline_start(self, polygon_coords, entry_point):
        """Find optimal starting index for outline from closest point to entry.
        
        Args:
            polygon_coords (list): List of polygon coordinate tuples
            entry_point (Vec3): Reference point to find closest start
            
        Returns:
            int: Index of optimal starting point in polygon_coords
        """
        min_dist = float('inf')
        best_idx = 0
        
        for i, coord in enumerate(polygon_coords[:-1]):
            point = Vec3(coord[0], coord[1], entry_point.z)
            dist = point.distance(entry_point)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        
        return best_idx
    
    
    def generate_outline_from_point(self, polygon, entry_point, layer, outline_id):
        """Generate outline entities starting from closest point to entry_point.
        
        Args:
            polygon (Polygon): Shapely polygon with exterior and interior rings
            entry_point (Vec3): Reference point to determine optimal start
            layer (str): Layer type identifier
            outline_id (int): Unique identifier for this outline group
            
        Returns:
            list: List of G-code entity dictionaries for outline
        """
        coords = list(polygon.exterior.coords)
        if len(coords) < 2:
            return []
        
        start_idx = self.find_optimal_outline_start(coords, entry_point)
        ordered_coords = coords[start_idx:-1] + coords[:start_idx+1]
        
        entities = []
        for i in range(len(ordered_coords) - 1):
            p1 = Vec3(ordered_coords[i][0], ordered_coords[i][1], entry_point.z)
            p2 = Vec3(ordered_coords[i+1][0], ordered_coords[i+1][1], entry_point.z)
            
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
        """Generate fill pattern entities from line segments.
        
        Args:
            fill_lines (list): List of LineString objects representing fill pattern
            layer (str): Layer type identifier
            outline_id (int): Associated outline group identifier
            z (float): Z coordinate for all fill entities
            
        Returns:
            list: List of G-code entity dictionaries for fill pattern
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
        """Generate path-optimized entities to minimize travel movements.
        
        Args:
            polygon_data (dict): Dictionary mapping Z-levels to polygon data
            initial_point (Vec3): Starting position for path optimization
            
        Returns:
            list: Optimized list of G-code entity dictionaries
        """
        self.entity_list = []
        self.id_entity_counter = 0
        
        optimized_traversal = optimize_layer_traversal(polygon_data, initial_point)
        
        for z in sorted(optimized_traversal.keys()):
            sequence = optimized_traversal[z]
            
            for step in sequence:
                polygon_data_item = step['polygon_data']
                entry_point = step['entry_point']
                
                polygon = polygon_data_item['polygon']
                fill_lines = polygon_data_item.get('fill_lines', [])
                outline_id = step['polygon_index']
                
                outline_entities = self.generate_outline_from_point(
                    polygon, entry_point, 'outline', outline_id
                )
                self.entity_list.extend(outline_entities)
                
                fill_entities = self.generate_fill_entities(
                    fill_lines, 'fill', outline_id, z
                )
                self.entity_list.extend(fill_entities)
        
        return self.entity_list
    
    
    def line_entity(self, start_point, end_point, layer, id, outline_id=-1):
        """Create linear movement entity between two points.
        
        Args:
            start_point (Vec3): Starting position
            end_point (Vec3): Ending position
            layer (str): Layer type identifier
            id (int): Unique entity identifier
            outline_id (int): Associated outline group identifier
        """
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
        """Create arc movement entity from center and angle parameters.
        
        Args:
            center (Vec3): Arc center point
            radius (float): Arc radius
            start_angle (float): Starting angle in degrees
            end_angle (float): Ending angle in degrees
            layer (str): Layer type identifier
            id (int): Unique entity identifier
        """
        start_x = center.x + radius * cos(radians(start_angle))
        start_y = center.y + radius * sin(radians(start_angle))
        end_x = center.x + radius * cos(radians(end_angle))
        end_y = center.y + radius * sin(radians(end_angle))
        
        start_point = Vec3(start_x, start_y, center.z)
        end_point = Vec3(end_x, end_y, center.z)
        
        i = center.x - start_x
        j = center.y - start_y
        
        value = 3 if is_ccw(start_angle, end_angle) else 2
        
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
        """Set DXF reference point to first entity's starting position."""
        if self.entity_list:
            first_entity = self.entity_list[0]
            self.dxf_reference_point = first_entity['param']['start']

    def order_entity_list(self, entity_list, initial_point):
        """Order entity list for optimal traversal.
        
        Args:
            entity_list (list): List of entities to order
            initial_point (Vec3): Starting reference point
            
        Returns:
            list: Ordered entity list (now simplified as entities are pre-optimized)
        """
        return entity_list

    def get_entity_list(self):
        """Return current list of generated entities.
        
        Returns:
            list: Current entity list
        """
        return self.entity_list