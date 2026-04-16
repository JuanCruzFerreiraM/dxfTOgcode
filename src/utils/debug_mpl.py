import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

def plot_polygon_layer_debug(layer_polygons, step=10):
    for i, (z, sections) in enumerate(sorted(layer_polygons.items())):
        if i % step != 0:
            continue

        fig, ax = plt.subplots()
        ax.set_title(f'Capa Z = {z:.2f}')
        patches = []

        for section in sections:
            polygon = section["polygon"]
            fill_lines = section.get("fill_lines", [])
            element_type = section.get("type", "Unknown")

            if polygon.is_empty or not polygon.is_valid:
                print(f"[WARNING] Polígono vacío o inválido en Z={z}, tipo={element_type}, ID={section.get('id')}")
                continue

            # Color diferenciado si el área es casi cero
            color = 'lightgray' if polygon.area > 1e-5 else 'red'

            # Exterior
            patch = MplPolygon(polygon.exterior.coords, closed=True, edgecolor='black',
                               facecolor=color, alpha=0.3)
            patches.append(patch)

            # Interiores (agujeros)
            for interior in polygon.interiors:
                hole_patch = MplPolygon(interior.coords, closed=True, edgecolor='black',
                                        facecolor='white', alpha=1.0)
                patches.append(hole_patch)

            # Relleno zigzag
            for line in fill_lines:
                x, y = line.xy
                ax.plot(x, y, color='blue', linewidth=0.5)

        p_collection = PatchCollection(patches, match_original=True)
        ax.add_collection(p_collection)
        ax.set_aspect('equal')
        ax.autoscale_view()
        plt.grid(True)
        plt.show()

