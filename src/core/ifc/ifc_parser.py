import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
import trimesh
import numpy as np
import math


def extract_trim_info(trim_element, transformation_matrix, local_center, radius):
    """
    Calculates the global coordinates of a trim point for an arc segment.

    It processes the trim information (which can be an angle in degrees or a Cartesian point)
    to determine the specific start or end point on the circle's circumference.
    The point is calculated locally and then transformed to the global coordinate system.

    Args:
        trim_element (set or list): A collection of trim items (IfcParameterValue or IfcCartesianPoint)
                                    defining the cut.
        transformation_matrix (numpy.ndarray): A 4x4 matrix to transform local coordinates to global.
        local_center (list or tuple): The center coordinates of the circle in local space.
        radius (float): The radius of the circle.

    Returns:
        numpy.ndarray: The global coordinates of the trim point [x, y, z].
    """   
    angle = 0    
    for item in trim_element:    
        print(item, item.is_a())
        if isinstance(item, (float, int)) or item.is_a('IfcParameterValue'):
            if item.is_a('IfcParameterValue'):
                item = item.wrappedValue
            angle = math.radians(float(item))
            break
        
        elif item.is_a('IfcCartesianPoint'):
            coords = item.Coordinates

            dx = coords[0] - local_center[0]
            dy = coords[1] - local_center[1]
            angle = math.atan2(dy,dx)
    
    local_pt = np.array([
        local_center[0] + radius * math.cos(angle),
        local_center[1] + radius * math.sin(angle),
        0,1
    ])
    
    global_pt_array = transformation_matrix @ local_pt
    
    global_pt = global_pt_array[:3]
    return  global_pt

def extract_arc_info(element, transformation_matrix): 
    """
    Parses an IFC element to extract geometry defined by an IfcCompositeCurve, specifically looking for arcs and lines.

    It inspects the 'Body' representation for an IfcExtrudedAreaSolid. If the profile is an
    IfcArbitraryClosedProfileDef based on an IfcCompositeCurve, it iterates through segments
    to extract arcs (from IfcTrimmedCurve/IfcCircle) and lines (from IfcPolyLine).

    Args:
        element: The IfcWall or IfcWallStandardCase entity to process.
        transformation_matrix (numpy.ndarray): A 4x4 matrix to transform local coordinates to global.

    Returns:
        dict or None: A dictionary with keys 'type' ('ARC_WALL'), 'id', 'height', and 'segments' 
        (containing radius, center, points, etc.) if successful. Returns None if the element 
        does not match the specific arc/composite curve criteria.
    """
    body_rep = None
    for rep in element.Representation.Representations: 
        if rep.RepresentationIdentifier == 'Body':
            body_rep = rep
            break
    
    if not body_rep: return None
    
    extrusion = None
    for item in body_rep.Items:
        if item.is_a('IfcExtrudedAreaSolid'):
            extrusion = item
            break
        
    if not extrusion: return None
    
    height = extrusion.Depth #Altura total en Z
    
    profile = extrusion.SweptArea
    if not profile.is_a("IfcArbitraryClosedProfileDef"): return None
    
    curve = profile.OuterCurve
    if not curve.is_a('IfcCompositeCurve'): return None
    
    segments_data = []
    for segment in curve.Segments:
        parent = segment.ParentCurve
        
        if parent.is_a('IfcTrimmedCurve'):
            basis = parent.BasisCurve 
            is_ccw = True
            if hasattr(parent, 'SenseAgreement'):
                if not parent.SenseAgreement:
                    is_ccw = not is_ccw
            if hasattr(segment, 'SameSense'):
                if not segment.SameSense:
                    is_ccw = not is_ccw
            trim1 = parent.Trim1
            trim2 = parent.Trim2
            if basis.is_a('IfcCircle'):
                
                radius = basis.Radius
                center_local_pt = basis.Position.Location.Coordinates
                center_local_array = [center_local_pt[0], center_local_pt[1], 0, 1]
                
                center_global_array = transformation_matrix @ center_local_array
                center_global_pt = center_global_array[:3]
                
                pt_1 = extract_trim_info(trim1,transformation_matrix,center_local_pt,radius)
                pt_2 = extract_trim_info(trim2,transformation_matrix,center_local_pt,radius)
                
                segments_data.append({
                    'type': 'ARC',
                    'radius': radius,
                    'center': center_global_pt,
                    'is_ccw': is_ccw,
                    'point_trim1': pt_1,
                    'point_trim2': pt_2,
                })
            else:
                return None
        
        elif parent.is_a('IfcPolyLine'):
            points = [p.Coordinates for p in parent.Points]
            segments_data.append({
                'type': 'LINE', 
                'points': points
            })
        else:
            return None
    
    return {
        'type': 'ARC_WALL', 
        'id': element.id(),
        'height': height,
        'segments': segments_data
    }            
                

class FileError(Exception):
    """Exception raised for IFC file processing errors."""
    pass


def ifc_parser(file_path):
    """Parse IFC file and extract 3D mesh data from building elements.
    
    Args:
        file_path (str): Path to IFC file to process
        
    Returns:
        list: List of dictionaries containing mesh data, element ID, and type
        
    Raises:
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
            
            matrix4x4 = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
            
            transform_matrix = np.array(matrix4x4)
            
            curve_wall = extract_arc_info(element, transform_matrix)
            
            if curve_wall is not None: 
                meshes_data.append(curve_wall)
                
            else:
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
                }

                meshes_data.append(mesh_info)

        except Exception as e:
            print(f"[IFC PARSER] Error procesando {element.GlobalId}: {e}")

    return meshes_data