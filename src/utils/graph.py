import networkx as nx
from src.utils.geometry import distance
from ezdxf.math import Vec3


def generate_graph(entity_list, tipo='outline'):
    """Create directed graph from entities of specified type.
    
    Args:
        entity_list (list): List of entity dictionaries
        tipo (str): Entity layer type to filter ('outline', 'fill', etc.)
        
    Returns:
        list: List of subgraphs for each connected component
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
    """Find minimum distance from reference point to any node in subgraph.
    
    Args:
        sg (networkx.DiGraph): Subgraph to search
        reference_point (Vec3): Reference point for distance calculation
        
    Returns:
        float: Minimum distance found
    """
    return min(distance(p.x, p.y, reference_point.x, reference_point.y) for p in sg.nodes)


def dfs(sg, node, order, visited, reverse=False):
    """Perform depth-first search traversal on subgraph.
    
    Args:
        sg (networkx.DiGraph): Subgraph to traverse
        node (Vec3): Starting node for traversal
        order (list): List to accumulate entity IDs in traversal order
        visited (list): List of already visited nodes
        reverse (bool): Whether to reverse neighbor order
        
    Returns:
        Vec3: Last node visited in traversal
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
    """Group entities by outline_id to process outline+fill together.
    
    Args:
        entity_list (list): List of entity dictionaries
        
    Returns:
        dict: Dictionary mapping outline_id to grouped entities with centroid
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
    """Generate optimized traversal order by processing outline+fill groups.
    
    Args:
        entity_list (list): List of entity dictionaries
        initial_point (Vec3): Starting reference point
        
    Returns:
        list: Ordered list of entity IDs for optimal traversal
    """
    final_order = []
    
    groups = group_entities_by_outline(entity_list)
    remaining_groups = dict(groups)
    current_point = initial_point
    
    while remaining_groups:
        closest_outline_id = min(remaining_groups.keys(),
                               key=lambda oid: remaining_groups[oid]['centroid'].distance(current_point))
        
        group = remaining_groups.pop(closest_outline_id)
        
        if group['outline']:
            outline_graphs = generate_graph(group['outline'], tipo='outline')
            
            for sg in outline_graphs:
                source = min(list(sg.nodes), key=lambda p: p.distance(current_point))
                
                order_normal = []
                last_node_normal = dfs(sg, source, order_normal, [], reverse=False)
                
                final_order.extend(order_normal)
                current_point = last_node_normal if order_normal else current_point
        
        fill_ids = [entity['param']['id'] for entity in group['fill']]
        final_order.extend(fill_ids)
        
        current_point = group['centroid']
    
    return final_order
