import ifcopenshell
import ifcopenshell.geom
import trimesh

class FileError(Exception):
    """Excepción personalizada para errores de archivo."""
    pass

def ifc_parser (file_path):
    try:
        ifc_file = ifcopenshell.open(file_path)
    except Exception as e:
        raise FileError(f'File Error. Please retry. {e}') from e
        
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    meshes_data = []

    allowed_types = {"IfcWall", "IfcWallStandardCase", "IfcSlab"}  # sin ventanas ni puertas

    for element in ifc_file.by_type("IfcProduct"):
        if element.is_a() not in allowed_types:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            verts = shape.geometry.verts
            faces = shape.geometry.faces

            vertices = [(verts[i], verts[i+1], verts[i+2]) for i in range(0, len(verts), 3)]
            faces = [(faces[i], faces[i+1], faces[i+2]) for i in range(0, len(faces), 3)]

            mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            mesh_info = {
                "mesh": mesh,
                "id": element.id(),
                "type": element.is_a(),
                #"name": element.attribute_name() este nose, en principio podemos ver que dos contornos pertenecen a un mismo muro si el id es el mismo.
            }
            meshes_data.append(mesh)

        except Exception as e:
            print(f"Error procesando {element.GlobalId}: {e}")
            
    return meshes_data
