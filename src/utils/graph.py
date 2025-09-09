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


def traversal_order(entity_list, initial_point):
    """
    Devuelve el orden de entidades optimizado para G0, separando outline y fill.
    """
    final_order = []

    # --- OUTLINE: grafo + DFS optimizado paso a paso ---
    outline_graphs = generate_graph(entity_list, tipo='outline')
    remaining_sgs = outline_graphs.copy()
    current_point = initial_point

    while remaining_sgs:
        # Elegir el subgrafo más cercano al punto actual
        idx_min = min(range(len(remaining_sgs)),
                      key=lambda i: min_dis_sg(remaining_sgs[i], current_point))
        sg = remaining_sgs.pop(idx_min)

        # Nodo inicial más cercano al punto actual
        source = min(list(sg.nodes), key=lambda p: p.distance(current_point))

        # DFS normal
        order_normal = []
        last_node_normal = dfs(sg, source, order_normal, [], reverse=False)
        dist_normal = last_node_normal.distance(current_point) if order_normal else float('inf')

        # DFS reverso
        order_reverse = []
        last_node_reverse = dfs(sg, source, order_reverse, [], reverse=True)
        dist_reverse = last_node_reverse.distance(current_point) if order_reverse else float('inf')

        # Selección final
        if dist_normal <= dist_reverse:
            final_order.extend(order_normal)
            current_point = last_node_normal
        else:
            final_order.extend(order_reverse)
            current_point = last_node_reverse

    # --- FILL: directo, sin grafo ni DFS ---
    fill_ids = [
        value['param']['id']
        for value in entity_list
        if value['param']['layer'] == 'fill'
    ]
    final_order.extend(fill_ids)

    return final_order
