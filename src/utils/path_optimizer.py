from ezdxf.math import Vec3
from src.utils.geometry import distance


def get_polygon_entry_points(polygon_data):
    """
    Obtiene todos los puntos de entrada posibles para un polígono.
    """
    return polygon_data["boundary_points"]


def calculate_polygon_exit_point(polygon_data, entry_point):
    """
    Estima dónde terminará el recorrido de este polígono.
    Para simplificar, usa el punto más lejano del punto de entrada.
    """
    all_points = polygon_data["boundary_points"]
    
    if polygon_data["fill_lines"]:
        # Agregar puntos de fill
        for line in polygon_data["fill_lines"]:
            coords = list(line.coords)
            for coord in coords:
                all_points.append(Vec3(coord[0], coord[1], polygon_data["centroid"].z))
    
    if not all_points:
        return entry_point
    
    # Punto más lejano del entry_point (aproximación del exit)
    exit_point = max(all_points, key=lambda p: p.distance(entry_point))
    return exit_point


def find_optimal_polygon_sequence(layer_polygons, initial_point):
    """
    Encuentra la secuencia óptima de polígonos para minimizar G0.
    """
    sequence = []
    remaining_polygons = list(enumerate(layer_polygons))
    current_point = initial_point
    
    while remaining_polygons:
        best_idx = None
        best_entry_point = None
        best_distance = float('inf')
        
        # Evaluar todos los polígonos restantes
        for i, (orig_idx, polygon_data) in enumerate(remaining_polygons):
            entry_points = get_polygon_entry_points(polygon_data)
            
            # Encontrar el mejor punto de entrada para este polígono
            closest_entry = min(entry_points, key=lambda p: p.distance(current_point))
            dist = closest_entry.distance(current_point)
            
            if dist < best_distance:
                best_distance = dist
                best_idx = i
                best_entry_point = closest_entry
        
        # Seleccionar el mejor polígono
        orig_idx, polygon_data = remaining_polygons.pop(best_idx)
        
        # Calcular punto de salida
        exit_point = calculate_polygon_exit_point(polygon_data, best_entry_point)
        
        sequence.append({
            'polygon_index': orig_idx,
            'polygon_data': polygon_data,
            'entry_point': best_entry_point,
            'exit_point': exit_point
        })
        
        current_point = exit_point
    
    return sequence


def optimize_layer_traversal(polygon_data, initial_point):
    """
    Optimiza el recorrido completo de una capa.
    """
    optimized_layers = {}
    
    for z, polygons in polygon_data.items():
        if not polygons:
            continue
            
        sequence = find_optimal_polygon_sequence(polygons, initial_point)
        optimized_layers[z] = sequence
        
        # Actualizar punto inicial para la siguiente capa
        if sequence:
            initial_point = sequence[-1]['exit_point']
    
    return optimized_layers