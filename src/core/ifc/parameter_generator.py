from shapely.affinity import affine_transform
from shapely.geometry import LineString, MultiLineString
from ezdxf.math import Vec3
import numpy as np


def generate_vzigzag_fill(polygon, step=0.1, offset=0.0, direction='x'):
    """
    Genera un relleno zigzag tipo VVVVV dentro del polígono, adaptable a dirección X o Y.
    """
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    if offset > 0:
        polygon = polygon.buffer(-offset)
        if polygon.is_empty:
            return []

    minx, miny, maxx, maxy = polygon.bounds
    points = []
    toggle = True

    if direction == 'x':
        x = minx
        while x <= maxx:
            y = maxy if toggle else miny
            points.append((x, y))
            toggle = not toggle
            x += step
    elif direction == 'y':
        y = miny
        while y <= maxy:
            x = maxx if toggle else minx
            points.append((x, y))
            toggle = not toggle
            y += step

    zigzag_line = LineString(points)
    intersection = polygon.intersection(zigzag_line)

    if intersection.is_empty:
        return []

    if isinstance(intersection, LineString):
        return [intersection]
    elif isinstance(intersection, MultiLineString):
        return list(intersection.geoms)
    else:
        return []


def extract_layer_polygons_with_fill(slices, step=0.1, offset=0.0):
    """
    Extrae polígonos 2D de las capas y aplica relleno zigzag adaptativo.
    """
    layer_polygons = {}

    for layer in slices:
        z = layer["z"]
        sections_data = []

        for section in layer["sections"]:
            path = section["path"]
            transform = section["tf"]
            element_type = section.get("type", "Unknown")
            element_id = section.get("id", None)
            affine_matrix = transform[:2, :2].flatten().tolist() + transform[:2, 3].tolist()

            for polygon in path.polygons_full:
                if np.allclose(affine_matrix, [1, 0, 0, 1, 0, 0]):
                    transformed_polygon = polygon
                else:
                    transformed_polygon = affine_transform(polygon, affine_matrix)

                # Validar y corregir geometría si es necesario
                if not transformed_polygon.is_valid:
                    transformed_polygon = transformed_polygon.buffer(0)

                # Determinar dirección del relleno
                minx, miny, maxx, maxy = transformed_polygon.bounds
                width = maxx - minx
                height = maxy - miny
                direction = 'x' if width >= height else 'y'

                data = {
                    "polygon": transformed_polygon,
                    "type": element_type,
                    "id": element_id,
                }

                if "wall" in element_type.lower():
                    if transformed_polygon.area > step**2:  # evitar geometrías pequeñas
                        data["fill_lines"] = generate_vzigzag_fill(
                            transformed_polygon, step=step, offset=offset, direction=direction
                        )
                    else:
                        data["fill_lines"] = []
                else:
                    data["fill_lines"] = []

                sections_data.append(data)

        layer_polygons[z] = sections_data

    return layer_polygons


def generate_gcode_from_meshes(generator, sliced_layers, step=0.1, offset=0.0, start_id=0):
    """
    Convierte las capas procesadas en comandos G-code con contornos y relleno.
    """
    polygon_data = extract_layer_polygons_with_fill(sliced_layers, step=step, offset=offset)
    entity_id_counter = start_id

    for z, sections in sorted(polygon_data.items()):
        for section in sections:
            polygon = section["polygon"]

            # OUTLINE exterior
            coords = list(polygon.exterior.coords)
            for i in range(len(coords) - 1):
                p1 = Vec3(coords[i][0], coords[i][1], z)
                p2 = Vec3(coords[i + 1][0], coords[i + 1][1], z)
                generator.line_entity(p1, p2, layer="outline", id=entity_id_counter)
                entity_id_counter += 1

            # OUTLINE interiores (huecos)
            for interior in polygon.interiors:
                coords = list(interior.coords)
                for i in range(len(coords) - 1):
                    p1 = Vec3(coords[i][0], coords[i][1], z)
                    p2 = Vec3(coords[i + 1][0], coords[i + 1][1], z)
                    generator.line_entity(p1, p2, layer="outline", id=entity_id_counter)
                    entity_id_counter += 1

            # RELLENO zigzag
            fill_lines = section.get("fill_lines", [])
            for line in fill_lines:
                coords = list(line.coords)
                if len(coords) >= 2:
                    for i in range(len(coords) - 1):
                        p1 = Vec3(coords[i][0], coords[i][1], z)
                        p2 = Vec3(coords[i + 1][0], coords[i + 1][1], z)
                        generator.line_entity(p1, p2, layer="fill", id=entity_id_counter)
                        entity_id_counter += 1

    return entity_id_counter
