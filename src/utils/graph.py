import networkx as nx
from src.utils.geometry import distance
from ezdxf.math import Vec3


def generate_graph(entity_list, tipo='outline'):
    """
    Crea subgrafos separados por componentes conexas, solo para entidades del tipo indicado.
    """
    graph = nx.DiGraph()
    for value in entity_list:
        layer = value['param']['layer']
        if layer != tipo:
            continue
        p1 = value['param']['start']
        p2 = value['param']['end']
        graph.add_edge(p1, p2, tipo=layer, id_entity=value['param']['id'])

    list_components = list(nx.weakly_connected_components(graph))
    return [graph.subgraph(c).copy() for c in list_components]


def min_dis_sg(sg, reference_point):
    return min(distance(p.x, p.y, reference_point.x, reference_point.y) for p in sg.nodes)


def dfs(sg, node, order, visited, reverse=False):
    """
    Recorrido DFS con opción de reversa.
    Devuelve también el último nodo visitado.
    """
    if node in visited:
        return node
    visited.append(node)

    neighbors = list(sg.neighbors(node))
    neighbors.sort(key=lambda v: sg[node][v].get('tipo', '') == 'fill')
    if reverse:
        neighbors.reverse()

    last_node = node
    for neighbor in neighbors:
        edge_data = sg[node][neighbor]
        entity_id = edge_data.get('id_entity')
        if entity_id is not None:
            order.append(entity_id)
        last_node = dfs(sg, neighbor, order, visited, reverse)

    return last_node


def group_entities_by_outline(entity_list):
    """
    Agrupa entidades por outline_id para procesar outline+fill juntos.
    """
    groups = {}
    for entity in entity_list:
        outline_id = entity['param'].get('outline_id', -1)
        if outline_id not in groups:
            groups[outline_id] = {'outline': [], 'fill': [], 'centroid': None}
        
        layer = entity['param']['layer']
        if layer == 'outline':
            groups[outline_id]['outline'].append(entity)
        elif layer == 'fill':
            groups[outline_id]['fill'].append(entity)
    
    # Calcular centroide de cada grupo UNA SOLA VEZ
    for outline_id, group in groups.items():
        all_points = []
        for entity in group['outline'] + group['fill']:
            all_points.extend([entity['param']['start'], entity['param']['end']])
        
        if all_points:
            avg_x = sum(p.x for p in all_points) / len(all_points)
            avg_y = sum(p.y for p in all_points) / len(all_points) 
            avg_z = sum(p.z for p in all_points) / len(all_points)
            group['centroid'] = Vec3(avg_x, avg_y, avg_z)
        else:
            group['centroid'] = Vec3(0, 0, 0)
    
    return groups


def traversal_order(entity_list, initial_point):
    """
    Algoritmo más simple: 
    Después de completar cada polígono (outline+fill), buscar el centroide más cercano.
    """
    final_order = []
    
    # Agrupar entidades por outline_id
    groups = group_entities_by_outline(entity_list)
    remaining_groups = dict(groups)  # Copia para ir eliminando
    current_point = initial_point
    
    while remaining_groups:
        # Buscar el grupo más cercano por centroide
        closest_outline_id = min(remaining_groups.keys(),
                               key=lambda oid: remaining_groups[oid]['centroid'].distance(current_point))
        
        # Procesar el grupo seleccionado
        group = remaining_groups.pop(closest_outline_id)
        
        # 1. Procesar OUTLINE
        if group['outline']:
            outline_graphs = generate_graph(group['outline'], tipo='outline')
            
            for sg in outline_graphs:
                # Empezar desde el nodo más cercano al punto actual
                source = min(list(sg.nodes), key=lambda p: p.distance(current_point))
                
                # DFS para outline
                order_normal = []
                last_node_normal = dfs(sg, source, order_normal, [], reverse=False)
                
                final_order.extend(order_normal)
                current_point = last_node_normal if order_normal else current_point
        
        # 2. Procesar FILL inmediatamente después
        fill_ids = [entity['param']['id'] for entity in group['fill']]
        final_order.extend(fill_ids)
        
        # 3. Actualizar punto actual al centroide del grupo completado
        # (aproximación simple pero consistente)
        current_point = group['centroid']
    
    return final_order
