import trimesh
import numpy as np


def slicer(meshes_data, layer_height=20):
    """Slice 3D meshes into 2D cross-sections at regular height intervals.
    
    Args:
        meshes_data (list): List of mesh dictionaries from IFC parser
        layer_height (float): Height between slicing planes in mm
        
    Returns:
        list: List of slice dictionaries containing Z-level and 2D sections
    """
    layer_height /= 1000

    min_z = float('inf')
    max_z = float('-inf')

    for obj in meshes_data:
        if obj.get("mesh") is not None:
            min_z = min(min_z, obj["mesh"].bounds[0][2])
            max_z = max(max_z, obj["mesh"].bounds[1][2])
        elif obj.get("type") == 'ARC_WALL':
            base_z = 0
            if obj['segments']:
                first_seg = obj['segments'][0]
                if first_seg['type'] == 'ARC':
                    base_z = first_seg['center'][2]
                elif first_seg['type'] == 'LINE' and len(first_seg['points']) > 0:
                    base_z = first_seg['points'][0][2]
            
            min_z = min(min_z, base_z)
            max_z = max(max_z, base_z + obj['height'])

    if min_z == float('inf'):
        min_z, max_z = 0, 0

    slice_zs = np.arange(min_z, max_z + layer_height, layer_height)

    slices = []
    for z in slice_zs:
        z_rounded = round(z, 5)
        rect_sections = []

        for obj in meshes_data:
            
            if obj['type'] == 'ARC_WALL':
                # Recalcular base_z para verificar si el corte pasa por este muro
                base_z = 0
                if obj['segments']:
                    first_seg = obj['segments'][0]
                    if first_seg['type'] == 'ARC':
                        base_z = first_seg['center'][2]
                    elif first_seg['type'] == 'LINE' and len(first_seg['points']) > 0:
                        base_z = first_seg['points'][0][2]

                if base_z <= z_rounded <= (base_z + obj['height']):
                    slices.append({
                        "z": z_rounded,
                        "type": 'Arc_Wall',
                        'id': obj['id'],
                        "sections": obj['segments']
                    })
            else: 
                mesh = obj["mesh"]
                if mesh is None:
                    continue
                    
                zmin, zmax = mesh.bounds[:, 2]

                if not (zmin <= z <= zmax):
                    continue

                section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
                if section is not None:
                    path2d, tf = section.to_planar()
                    rect_sections.append({
                        "path": path2d,
                        "tf": tf,
                        "id": obj.get("id", None),
                        "type": obj.get("type", None),
                    })

        if rect_sections:
            slices.append({
                "z": z_rounded,
                "type": 'Rect_Wall',
                "sections": rect_sections
            })
    return slices