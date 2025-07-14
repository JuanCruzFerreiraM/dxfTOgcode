import ifcopenshell
import ifcopenshell.geom
import trimesh

class FileError(Exception):
    pass

def ifc_parser(file_path):
    try:
        ifc_file = ifcopenshell.open(file_path)
    except Exception as e:
        raise FileError(f'File Error. Please retry. {e}') from e

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    meshes_data = []
    allowed_types = {"IfcWall", "IfcWallStandardCase", "IfcSlab"}

    for element in ifc_file.by_type("IfcProduct"):
        if element.is_a() not in allowed_types:
            continue
        if not hasattr(element, "Representation") or element.Representation is None:
            continue
        if not element.ObjectPlacement:
            continue

        try:
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
    