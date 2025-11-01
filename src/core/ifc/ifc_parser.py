"""
To do list: 

Terminar de implementar el pasaje a coordenadas globales de los trim, y determinar angulos 
Terminar de implementar en el codigo la logica para arcos
Implementar dichas cosas en el propio flujo ifc. 
"""


import ifcopenshell
import ifcopenshell.geom
import trimesh
import numpy as np
from ifcopenshell.util import placement


def calculate_trim_angle(trim,global_center,transf_matrix, representation):
    for trim_value in trim:
        if trim_value.is_a('IfcCartesianPoint') and representation != 'PARAMETER':
            local_point = np.array(list(trim_value.Coordinates) + [1.0])
            global_point = tuple(np.dot(transf_matrix, local_point)[:3])
            angle = np.atan2(global_point[1] - global_center[1], global_point[0] - global_center[0])
            return angle
        elif isinstance(trim_value, float):
            alpha = (np.atan2(transf_matrix[1][0], transf_matrix[0][0]))
            angle = trim_value + alpha
            return angle 
        else: 
            continue     #En este caso se debería ignorar el angulo ? 

 

def get_arc_parameters(item, transf_matrix):
    """
    Extract arc information from a IfcTrimmedCurve (mostly) or a IfcCircle.
    
    #### Args:
        item (ifcopenshell.entity_instance): A item with the arc information.
    
    #### Returns: 
        data: dictionary containing the parameters of the arc or circle. 
    """
    data = None
    if item.is_a('IfcTrimmedCurve'): #Podriamos agregar una fase de deteccion y conversion y siempre devolver el angulo que es lo que nos interesa para G2/3
        radius = item.BasisCurve.Radius 
        center_point = np.array(list(item.BasisCurve.Position.Location.Coordinates) + [1.0])
        global_center = tuple(np.dot(transf_matrix, center_point)[:3])
        initial_point = item.Trim1
        end_point = item.Trim2
        representation = item.MasterRepresentation
        sense_agreement = item.SenseAgreement #El nombre no es tan explicativo pero sirve para determinar el sentido de giro
        data = {
            'radius': radius,
            'center_point': global_center,
            'initial_angle': calculate_trim_angle(initial_point, global_center, transf_matrix,representation),
            'end_angle': calculate_trim_angle(end_point, global_center, transf_matrix,representation),
            'sense': sense_agreement
        }
    else: 
        radius = item.Radius
        center_point = np.array(list(item.Position.Location.Coordinates) + [1.0])
        global_center = tuple(np.dot(transf_matrix, center_point)[:3])
        initial_angle = 0.0
        end_angle = 2 * np.pi
        sense_agreement = True
        data = {
            'radius': radius,
            'center_point': global_center,
            'initial_angle': initial_angle,
            'end_angle': end_angle,
            'sense': sense_agreement
        }    
        return data

class FileError(Exception):
    """Exception raised for IFC file processing errors."""
    pass


def ifc_parser(file_path):
    """Parse IFC file and extract 3D mesh data from building elements.
    
    #### Args:
        file_path (str): Path to IFC file to process
        
    #### Returns:
        list: List of dictionaries containing mesh data, element ID, and type
        
    #### Raises:
        FileError: If IFC file cannot be opened or processed
    """
    try:
        ifc_file = ifcopenshell.open(file_path)
    except Exception as e:
        raise FileError(f'File Error. Please retry. {e}') from e

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    meshes_data = []
    allowed_types = {"IfcWall", "IfcWallStandardCase"}

    for element in ifc_file.by_type("IfcProduct"):
        if element.is_a() not in allowed_types:
            continue
        if not hasattr(element, "Representation") or element.Representation is None:
            continue
        if not element.ObjectPlacement:
            continue

        try:
            transformation_matrix = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
            curve_data = None
            
            if hasattr(element, "Representation") and element.Representation is not None:
                for shape_representation in element.Representation.Representations: 
                    if shape_representation.RepresentationIdentifier == "FootPrint" or shape_representation.RepresentationIdentifier == "Contour":
                        for item in shape_representation.Items: 
                            if item.is_a('IfcTrimmedCurve') or item.is_a('IfcCircle'):
                                curve_data = get_arc_parameters(item, transformation_matrix)
                                break
                    if curve_data is not None:
                        break    
                                
            
            shape = ifcopenshell.geom.create_shape(settings, element)

            if not shape.geometry.verts or not shape.geometry.faces:
                continue

            verts = shape.geometry.verts
            faces = shape.geometry.faces

            vertices = [(verts[i], verts[i+1], verts[i+2]) for i in range(0, len(verts), 3)]
            faces = [(faces[i], faces[i+1], faces[i+2]) for i in range(0, len(faces), 3)]

            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

            mesh_info = {
                "mesh": mesh,
                "id": element.id(),
                "type": element.is_a(),
                "curve_data": curve_data,
            }

            meshes_data.append(mesh_info)

        except Exception as e:
            print(f"[IFC PARSER] Error procesando {element.GlobalId}: {e}")

    return meshes_data
    
    
    
