import networkx as nx
from src.utils.geometry import distance, center_of_shape
from ezdxf.math import Vec3

def generate_graph(entity_list):
    graph = nx.DiGraph()
    for value in entity_list:
        p1 = value['param']['start']
        p2 = value['param']['end']
        d = distance(p1.x,p1.y,p2.x,p2.y)
        graph.add_edge(p1,p2, tipo = value['param']['layer'], id_entity = value['param']['id'])
    list_components = list(nx.weakly_connected_components(graph))
    return [graph.subgraph(c).copy() for c in list_components]

def min_dis_sg(sg, initial_point):
    return min(distance(p.x,p.y,initial_point.x,initial_point.y) for p in sg.nodes)

def order_sgs(sgs):
    other_graphs = []
    initial_point = Vec3(0,0,0)
    for sg in sgs:
        if initial_point in sg.nodes:
            main_graph = sg
        else: 
            other_graphs.append(sg)
    other_sg_order = sorted(other_graphs,key = lambda sg: min_dis_sg(sg,initial_point)) 
    return [main_graph] + other_sg_order
            
            
def dfs(sg, node, order, visited):
    """
    Performs a Depth-First Search (DFS) on a subgraph to determine the order of entities.

    #### Args:
    - sg (networkx.DiGraph): The subgraph to traverse.
    - node (Vec3): The starting node for the traversal.
    - order (list): List to store the ordered entity IDs.
    - visited (list): List to track visited nodes.

    #### Modifies:
    - order (list): Appends the entity IDs in the traversal order.
    - visited (list): Updates the list of visited nodes.
    """
    if node in visited:
        return
    
    visited.append(node)
    
    neighbors = list(sg.neighbors(node))
    neighbors.sort(key=lambda v: sg[node][v].get('tipo', '') == 'fill')
    
    for neighbor in neighbors:
        edge_data = sg[node][neighbor]
        entity_id = edge_data.get('id_entity')
        if entity_id is not None:
            order.append(entity_id)
        dfs(sg, neighbor, order, visited)


def traversal_order(entity_list, initial_point):
    """
    Generates the traversal order of entities based on proximity to an initial point.

    #### Args:
    - entity_list (list): List of entities to be processed.
    - initial_point (Vec3): The starting point for the traversal.

    #### Returns:
    - list: Ordered list of entity IDs based on the traversal.
    """
    sgs = generate_graph(entity_list)
    sgs_in_order = order_sgs(sgs)
    final_order = []
    for sg in sgs_in_order:
        visited = []
        if initial_point in sg.nodes:
            source = initial_point
        else: 
            source = min(list(sg.nodes), key=lambda e: (e.x, e.y))    
        dfs(sg, source, final_order, visited)
    return final_order
