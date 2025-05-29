import networkx as nx
from src.utils.geometry import distance, center_of_shape
from ezdxf.math import Vec3

def generate_graph(list):
    graph = nx.DiGraph()
    for value in list:
        p1 = value['param']['start']
        p2 = value['param']['end']
        d = distance(p1,p2)
        graph.add_edge(p1,p2,weight = d)
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
                
            
def dfs(sg,start,center):
    stack = [start]
    visited = set()
    order = []
    
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            order.append(node)
        
        neighbors = list(sg.neighbors(node))
        neighbors.sort(key = lambda v: distance(v.x,v.y,center.x,center.y), reverse=True)
        
        for neighbor in neighbors:
            if neighbor  not in  visited:
                stack.append(neighbor)
    
    return order    

def traversal_order(list):
    sgs = generate_graph(list)
    sgs_in_order = order_sgs(sgs)
    final_order = []
    for sg in sgs_in_order:
        if Vec3(0,0,0) in sg.nodes:
            source = Vec3(0,0,0)
        else: 
            source = list(sg.nodes)[0]        
        final_order += dfs(sg,source,center_of_shape(list(sg.nodes)))
    return final_order