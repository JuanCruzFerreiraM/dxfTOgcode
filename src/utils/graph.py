import networkx as nx
from src.utils.geometry import distance, center_of_shape
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


def order_sgs(sgs, initial_point=Vec3(0, 0, 0)):
    """
    Ordena subgrafos de contorno para minimizar saltos G0.
    """
    ordered = []
    remaining = sgs.copy()

    start_sg = next((sg for sg in remaining if initial_point in sg.nodes), None)
    if start_sg is None:
        start_sg = min(remaining, key=lambda sg: min_dis_sg(sg, initial_point))

    ordered.append(start_sg)
    remaining.remove(start_sg)
    current_point = initial_point

    while remaining:
        closest_sg = min(remaining, key=lambda sg: min_dis_sg(sg, current_point))
        ordered.append(closest_sg)
        current_point = min(closest_sg.nodes, key=lambda p: p.distance(current_point))
        remaining.remove(closest_sg)

    return ordered


def dfs(sg, node, order, visited, reverse=False):
    """
    Recorrido DFS con opción de reversa.
    """
    if node in visited:
        return
    visited.append(node)

    neighbors = list(sg.neighbors(node))
    neighbors.sort(key=lambda v: sg[node][v].get('tipo', '') == 'fill')
    if reverse:
        neighbors.reverse()

    for neighbor in neighbors:
        edge_data = sg[node][neighbor]
        entity_id = edge_data.get('id_entity')
        if entity_id is not None:
            order.append(entity_id)
        dfs(sg, neighbor, order, visited, reverse)


def traversal_order(entity_list, initial_point):
    """
    Devuelve el orden de entidades optimizado para G0, separando outline y fill.
    """
    final_order = []

    # --- OUTLINE: grafo + DFS optimizado ---
    outline_graphs = generate_graph(entity_list, tipo='outline')
    outline_ordered_sgs = order_sgs(outline_graphs, initial_point)
    current_point = initial_point

    for sg in outline_ordered_sgs:
        visited = []
        source = min(list(sg.nodes), key=lambda p: p.distance(current_point))

        # DFS normal
        order_normal = []
        dfs(sg, source, order_normal, visited.copy(), reverse=False)
        end_point_normal = source
        for node in sg.nodes:
            if sg.has_edge(source, node):
                end_point_normal = node
        dist_normal = end_point_normal.distance(current_point) if order_normal else float('inf')

        # DFS reverso
        order_reverse = []
        dfs(sg, source, order_reverse, visited.copy(), reverse=True)
        end_point_reverse = source
        for node in sg.nodes:
            if sg.has_edge(source, node):
                end_point_reverse = node
        dist_reverse = end_point_reverse.distance(current_point) if order_reverse else float('inf')

        # Selección final
        if dist_normal <= dist_reverse:
            final_order.extend(order_normal)
            current_point = end_point_normal
        else:
            final_order.extend(order_reverse)
            current_point = end_point_reverse

    # --- FILL: directo, sin grafo ni DFS ---
    fill_ids = [
        value['param']['id']
        for value in entity_list
        if value['param']['layer'] == 'fill'
    ]
    final_order.extend(fill_ids)

    return final_order
