import trimesh
import numpy as np


def slicer(meshes_data, layer_height=20):
    layer_height /= 1000  # mm a metros

    min_z = min(obj["mesh"].bounds[0][2] for obj in meshes_data)
    max_z = max(obj["mesh"].bounds[1][2] for obj in meshes_data)

    slice_zs = np.arange(min_z, max_z + layer_height, layer_height)

    slices = []
    for z in slice_zs:
        z_rounded = round(z, 5)
        sections = []

        for obj in meshes_data:
            mesh = obj["mesh"]
            zmin, zmax = mesh.bounds[:, 2]  # bounds[:,2] -> solo componente Z

            # Optimización: descartar si el plano Z no toca el objeto
            if not (zmin <= z <= zmax):
                continue

            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is not None:
                path2d, tf = section.to_planar()
                sections.append({
                    "path": path2d,
                    "tf": tf,
                    "id": obj.get("id", None),
                    "type": obj.get("type", None),
                })

        slices.append({
            "z": z_rounded,
            "sections": sections
        })

    return slices
