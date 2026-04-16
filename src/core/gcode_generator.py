from ezdxf.math import Vec3
from math import atan, cos, hypot, radians, sin
from src.utils.geometry import is_ccw, bulge_to_center, distance
from src.utils.path_optimizer import DEFAULT_ROUTE_OPTIONS, optimize_layer_traversal
from src.utils.fill_chain import chain_fill_linestrings
import networkx as nx
import warnings


class InvalidPointError(Exception):
    """Exception raised for invalid point coordinates."""
    pass


class PathContinuityWarning(UserWarning):
    """Warning raised when path continuity issues are detected."""
    pass


# Tolerancia para considerar dos puntos como conectados (en mm)
CONTINUITY_TOLERANCE = 0.5


def _outline_g1_segment_key(start, end, quant_mm):
    """Clave de segmento no orientado para detectar aristas duplicadas en contornos G1."""
    if quant_mm is None or quant_mm <= 0:
        quant_mm = 0.02
    scale = 1.0 / quant_mm

    def snap_xy(v):
        return (int(round(v.x * scale)), int(round(v.y * scale)))

    a, b = snap_xy(start), snap_xy(end)
    return tuple(sorted([a, b]))


class GcodeGenerator:
    """Generates G-code entities from geometric data with path optimization."""
    
    def __init__(self):
        """Initialize GcodeGenerator with empty entity list and counters."""
        self.entity_list = []
        self.id_entity_counter = 0
        self.dxf_reference_point = Vec3(0, 0, 0)
        self.continuity_warnings = []  # Lista para acumular warnings
    
    
    def find_optimal_outline_start(self, polygon_coords, entry_point):
        """Find optimal starting index for outline from closest point to entry.
        
        Args:
            polygon_coords (list): List of polygon coordinate tuples
            entry_point (Vec3): Reference point to find closest start
            
        Returns:
            int: Index of optimal starting point in polygon_coords
        """
        min_dist = float('inf')
        best_idx = 0
        
        for i, coord in enumerate(polygon_coords[:-1]):
            point = Vec3(coord[0], coord[1], entry_point.z)
            dist = point.distance(entry_point)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        
        return best_idx
    
    
    def generate_outline_from_point(self, polygon, entry_point, layer, outline_id):
        """Generate outline entities starting from closest point to entry_point.
        
        Args:
            polygon (Polygon): Shapely polygon with exterior and interior rings
            entry_point (Vec3): Reference point to determine optimal start
            layer (str): Layer type identifier
            outline_id (int): Unique identifier for this outline group
            
        Returns:
            list: List of G-code entity dictionaries for outline
        """
        coords = list(polygon.exterior.coords)
        if len(coords) < 2:
            return []
        
        start_idx = self.find_optimal_outline_start(coords, entry_point)
        ordered_coords = coords[start_idx:-1] + coords[:start_idx+1]
        
        entities = []
        for i in range(len(ordered_coords) - 1):
            p1 = Vec3(ordered_coords[i][0], ordered_coords[i][1], entry_point.z)
            p2 = Vec3(ordered_coords[i+1][0], ordered_coords[i+1][1], entry_point.z)
            
            if p1.distance(p2) > 1e-6:
                entities.append({
                    'command': 'G1',
                    'param': {
                        'start': p1,
                        'end': p2,
                        'layer': layer,
                        'id': self.id_entity_counter,
                        'outline_id': outline_id
                    }
                })
                self.id_entity_counter += 1
        
        for interior in polygon.interiors:
            interior_coords = list(interior.coords)
            for i in range(len(interior_coords) - 1):
                p1 = Vec3(interior_coords[i][0], interior_coords[i][1], entry_point.z)
                p2 = Vec3(interior_coords[i+1][0], interior_coords[i+1][1], entry_point.z)
                
                if p1.distance(p2) > 1e-6:
                    entities.append({
                        'command': 'G1',
                        'param': {
                            'start': p1,
                            'end': p2,
                            'layer': layer,
                            'id': self.id_entity_counter,
                            'outline_id': outline_id
                        }
                    })
                    self.id_entity_counter += 1
        
        return entities

    def generate_outline_from_polyline(self, coords, entry_point, z, layer, outline_id):
        """Emite G1 a lo largo de una polilínea (cadena tras linemerge de aristas de muro)."""
        if not coords or len(coords) < 2:
            return []
        pts = [(float(c[0]), float(c[1])) for c in coords]
        first_last = hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
        closed = first_last < 1e-5

        if closed:
            if len(pts) < 3:
                return []
            ring = pts[:-1]
            if len(ring) < 2:
                return []
            best_i = min(
                range(len(ring)),
                key=lambda i: Vec3(ring[i][0], ring[i][1], z).distance(entry_point),
            )
            ordered = ring[best_i:] + ring[:best_i]
            ordered.append(ordered[0])
        else:
            fwd, rev = pts, list(reversed(pts))
            d_fwd = Vec3(fwd[0][0], fwd[0][1], z).distance(entry_point)
            d_rev = Vec3(rev[0][0], rev[0][1], z).distance(entry_point)
            ordered = fwd if d_fwd <= d_rev else rev

        entities = []
        for i in range(len(ordered) - 1):
            p1 = Vec3(ordered[i][0], ordered[i][1], z)
            p2 = Vec3(ordered[i + 1][0], ordered[i + 1][1], z)
            if p1.distance(p2) > 1e-6:
                entities.append(
                    {
                        "command": "G1",
                        "param": {
                            "start": p1,
                            "end": p2,
                            "layer": layer,
                            "id": self.id_entity_counter,
                            "outline_id": outline_id,
                        },
                    }
                )
                self.id_entity_counter += 1
        return entities

    def generate_arc_outline(self, arc_data_list, entry_point, z, layer, outline_id):
        """Generate arc outline entities, ignoring LINE segments (trim lines).
        
        Las líneas de trim se ignoran porque en esquinas curvas conectadas a muros rectos,
        esas líneas ya están cubiertas por los muros adyacentes. Esto evita sobreextrusión.
        
        Ambos arcos (interior y exterior) usan el mismo rango angular y la misma dirección,
        definidos por el arco EXTERIOR (mayor radio).
        """
        import math
        
        entities = []
        if not arc_data_list:
            return []

        # Filtrar solo los arcos, ignorar las líneas de trim
        arc_segments = [seg for seg in arc_data_list if seg['type'] == 'ARC']
        
        if not arc_segments:
            return []

        # Identificar arco exterior (mayor radio) para usar como referencia
        arcs_sorted = sorted(arc_segments, key=lambda a: a['radius'], reverse=True)
        outer_arc = arcs_sorted[0]
        
        # Obtener el centro (común a ambos arcos)
        center = Vec3(outer_arc['center'][0], outer_arc['center'][1], z)
        
        # Calcular el rango angular desde los trim points del arco EXTERIOR
        t1_outer = outer_arc['point_trim1']
        t2_outer = outer_arc['point_trim2']
        
        dx1 = t1_outer[0] - outer_arc['center'][0]
        dy1 = t1_outer[1] - outer_arc['center'][1]
        dx2 = t2_outer[0] - outer_arc['center'][0]
        dy2 = t2_outer[1] - outer_arc['center'][1]
        
        angle_trim1 = math.atan2(dy1, dx1)
        angle_trim2 = math.atan2(dy2, dx2)
        
        # Usar la dirección del arco EXTERIOR para todos los arcos
        outer_ccw = outer_arc.get('is_ccw', True)
        
        # Determinar dirección de entrada basada en proximidad
        # Calculamos los puntos del arco exterior para decidir
        outer_t1 = Vec3(t1_outer[0], t1_outer[1], z)
        outer_t2 = Vec3(t2_outer[0], t2_outer[1], z)
        is_reversed = entry_point.distance(outer_t2) < entry_point.distance(outer_t1)
        
        # Procesar arcos en orden (exterior primero, luego interior)
        for segment in arcs_sorted:
            radius = segment['radius']
            
            # Calcular los puntos de inicio y fin usando los MISMOS ángulos del exterior
            p1_x = center.x + radius * math.cos(angle_trim1)
            p1_y = center.y + radius * math.sin(angle_trim1)
            p2_x = center.x + radius * math.cos(angle_trim2)
            p2_y = center.y + radius * math.sin(angle_trim2)
            
            t1 = Vec3(p1_x, p1_y, z)
            t2 = Vec3(p2_x, p2_y, z)
            
            # Definir Inicio y Fin físico según dirección
            actual_start, target = (t2, t1) if is_reversed else (t1, t2)

            # Calculamos I, J
            i = center.x - actual_start.x
            j = center.y - actual_start.y
            
            # TODOS los arcos usan la misma dirección (del exterior), ajustada por is_reversed
            effective_ccw = outer_ccw != is_reversed  # XOR
            
            command = 'G3' if effective_ccw else 'G2'
            
            entities.append({
                'command': command,
                'param': {
                    'start': actual_start, 'end': target, 'i': i, 'j': j,
                    'layer': layer, 'id': self.id_entity_counter, 'outline_id': outline_id
                }
            })
            self.id_entity_counter += 1
                
        return entities
    
    
    def generate_fill_entities(self, fill_lines, layer, outline_id, z):
        """Generate fill pattern entities from line segments.
        
        Args:
            fill_lines (list): List of LineString objects representing fill pattern
            layer (str): Layer type identifier
            outline_id (int): Associated outline group identifier
            z (float): Z coordinate for all fill entities
            
        Returns:
            list: List of G-code entity dictionaries for fill pattern
        """
        entities = []
        for line in fill_lines:
            coords = list(line.coords)
            for i in range(len(coords) - 1):
                p1 = Vec3(coords[i][0], coords[i][1], z)
                p2 = Vec3(coords[i+1][0], coords[i+1][1], z)
                
                if p1.distance(p2) > 1e-6:
                    entities.append({
                        'command': 'G1',
                        'param': {
                            'start': p1,
                            'end': p2,
                            'layer': 'fill',
                            'id': self.id_entity_counter,
                            'outline_id': outline_id
                        }
                    })
                    self.id_entity_counter += 1
        
        return entities

    def build_item_entity_list(
        self,
        polygon_data_item,
        entry_point,
        z,
        outline_id,
        pos_before_island,
        dedupe_outline_segments=False,
        outline_dedupe_mm=0.02,
        seen_outline_segments=None,
    ):
        """
        Construye entidades de contorno + relleno para un ítem (sin modificar ``entity_list``).

        ``pos_before_island`` es la posición del cabezal antes de este ítem: para
        ``skip_outline`` encadena el relleno desde ahí; si hay contorno, el relleno
        se encadena desde el último punto del contorno.
        """
        saved_list = self.entity_list
        saved_id = self.id_entity_counter
        self.entity_list = []
        try:
            fill_raw = polygon_data_item.get("fill_lines") or []

            if polygon_data_item.get("is_arc", False):
                outline_entities = self.generate_arc_outline(
                    polygon_data_item["arc_data"],
                    entry_point,
                    z,
                    "outline",
                    outline_id,
                )
            elif polygon_data_item.get("skip_outline"):
                outline_entities = []
            elif polygon_data_item.get("outline_polyline"):
                chain = polygon_data_item.get("outline_chain_coords") or []
                outline_entities = self.generate_outline_from_polyline(
                    chain, entry_point, z, "outline", outline_id
                )
            else:
                polygon = polygon_data_item.get("polygon")
                if polygon is None:
                    outline_entities = []
                else:
                    outline_entities = self.generate_outline_from_point(
                        polygon, entry_point, "outline", outline_id
                    )

            if dedupe_outline_segments and seen_outline_segments is not None:
                filtered = []
                for ent in outline_entities:
                    if (
                        ent.get("command") == "G1"
                        and ent.get("param", {}).get("layer") == "outline"
                    ):
                        p = ent["param"]
                        sk = _outline_g1_segment_key(
                            p["start"], p["end"], outline_dedupe_mm
                        )
                        if sk in seen_outline_segments:
                            continue
                        seen_outline_segments.add(sk)
                    filtered.append(ent)
                outline_entities = filtered

            if polygon_data_item.get("outline_only"):
                fill_ordered = []
            elif polygon_data_item.get("skip_outline"):
                fill_ordered = chain_fill_linestrings(fill_raw, pos_before_island)
            else:
                if outline_entities:
                    last = outline_entities[-1]["param"]["end"]
                    chain_start = last
                else:
                    chain_start = entry_point
                fill_ordered = chain_fill_linestrings(fill_raw, chain_start)

            if polygon_data_item.get("outline_only"):
                fill_entities = []
            else:
                fill_entities = self.generate_fill_entities(
                    fill_ordered, "fill", outline_id, z
                )

            return outline_entities + fill_entities
        finally:
            self.entity_list = saved_list
            self.id_entity_counter = saved_id

    def first_print_start(self, entities):
        """Primer punto de contacto G1/G2/G3 de una lista de entidades."""
        if not entities:
            return None
        return entities[0]["param"]["start"]

    def last_print_end(self, entities):
        if not entities:
            return None
        return entities[-1]["param"]["end"]

    
    def generate_optimized_entities(
        self,
        polygon_data,
        initial_point=Vec3(0, 0, 0),
        dedupe_outline_segments=False,
        outline_dedupe_mm=0.02,
        route_options=None,
    ):
        """Generate path-optimized entities to minimize travel movements.
        
        Args:
            polygon_data (dict): Dictionary mapping Z-levels to polygon data
            initial_point (Vec3): Starting position for path optimization
            dedupe_outline_segments (bool): Por defecto False. Si True, filtra G1 de contorno
                duplicados por capa (puede romper anillos cerrados con varios outline_only).
            outline_dedupe_mm (float): Cuantización en mm si dedupe_outline_segments es True.
            route_options: ``RouteOptimizeOptions`` o None para valores por defecto (rápido en modelos grandes).

        Returns:
            list: Optimized list of G-code entity dictionaries
        """
        self.entity_list = []
        self.id_entity_counter = 0
        
        ro = route_options if route_options is not None else DEFAULT_ROUTE_OPTIONS
        optimized_traversal = optimize_layer_traversal(
            polygon_data, initial_point, route_options=ro
        )
        outline_g1_seen_by_z = {} if dedupe_outline_segments else None
        cursor = initial_point

        for z in sorted(optimized_traversal.keys()):
            cursor = Vec3(cursor.x, cursor.y, z)
            sequence = optimized_traversal[z]
            z_key = round(float(z), 5)
            if dedupe_outline_segments:
                if z_key not in outline_g1_seen_by_z:
                    outline_g1_seen_by_z[z_key] = set()
                seen_outline_segments = outline_g1_seen_by_z[z_key]
            else:
                seen_outline_segments = None

            for step in sequence:
                polygon_data_item = step['polygon_data']
                entry_point = step['entry_point']
                outline_id = step['polygon_index']

                ents = self.build_item_entity_list(
                    polygon_data_item,
                    entry_point,
                    z,
                    outline_id,
                    cursor,
                    dedupe_outline_segments=dedupe_outline_segments,
                    outline_dedupe_mm=outline_dedupe_mm,
                    seen_outline_segments=seen_outline_segments,
                )
                self.entity_list.extend(ents)
                if ents:
                    cursor = ents[-1]["param"]["end"]
        
        # Verificar continuidad del path y emitir warnings
        self._check_path_continuity()
        
        return self.entity_list

    def _check_path_continuity(self):
        """Verifica la continuidad del path y emite warnings si hay discontinuidades.
        
        Agrupa entidades por capa Z y verifica que dentro de cada grupo de outline,
        el punto final de cada entidad coincida con el inicio de la siguiente.
        """
        if len(self.entity_list) < 2:
            return
        
        # Agrupar por Z
        entities_by_z = {}
        for entity in self.entity_list:
            z = round(entity['param']['start'].z, 3)
            if z not in entities_by_z:
                entities_by_z[z] = []
            entities_by_z[z].append(entity)
        
        for z, entities in entities_by_z.items():
            # Agrupar por outline_id
            entities_by_outline = {}
            for entity in entities:
                oid = entity['param'].get('outline_id', -1)
                if oid not in entities_by_outline:
                    entities_by_outline[oid] = []
                entities_by_outline[oid].append(entity)
            
            # Verificar continuidad dentro de cada outline
            for oid, outline_entities in entities_by_outline.items():
                if len(outline_entities) < 2:
                    continue
                
                for i in range(len(outline_entities) - 1):
                    current_end = outline_entities[i]['param']['end']
                    next_start = outline_entities[i + 1]['param']['start']
                    
                    gap = current_end.distance(next_start)
                    if gap > CONTINUITY_TOLERANCE:
                        warning_msg = (
                            f"[CONTINUIDAD] Z={z}mm, outline={oid}: "
                            f"Gap de {gap:.2f}mm entre entidades {i} y {i+1}"
                        )
                        self.continuity_warnings.append(warning_msg)
                        warnings.warn(warning_msg, PathContinuityWarning)
    
    def get_continuity_warnings(self):
        """Retorna la lista de warnings de continuidad detectados."""
        return self.continuity_warnings

    
    
    def line_entity(self, start_point, end_point, layer, id, outline_id=-1):
        """Create linear movement entity between two points.
        
        Args:
            start_point (Vec3): Starting position
            end_point (Vec3): Ending position
            layer (str): Layer type identifier
            id (int): Unique entity identifier
            outline_id (int): Associated outline group identifier
        """
        entity = {
            'command': 'G1',
            'param': {
                'start': start_point,
                'end': end_point,
                'layer': layer,
                'id': id,
                'outline_id': outline_id
            }
        }
        self.entity_list.append(entity)
    
    
    def arc_entity(self, center, radius, start_angle, end_angle, layer, id):
        """Create arc movement entity from center and angle parameters.
        
        Args:
            center (Vec3): Arc center point
            radius (float): Arc radius
            start_angle (float): Starting angle in degrees
            end_angle (float): Ending angle in degrees
            layer (str): Layer type identifier
            id (int): Unique entity identifier
        """
        start_x = center.x + radius * cos(radians(start_angle))
        start_y = center.y + radius * sin(radians(start_angle))
        end_x = center.x + radius * cos(radians(end_angle))
        end_y = center.y + radius * sin(radians(end_angle))
        
        start_point = Vec3(start_x, start_y, center.z)
        end_point = Vec3(end_x, end_y, center.z)
        
        i = center.x - start_x
        j = center.y - start_y
        
        value = 3 if is_ccw(start_angle, end_angle) else 2
        
        entity = {
            'command': 'G2-3',
            'param': {
                'start': start_point,
                'end': end_point,
                'i': i,
                'j': j,
                'value': value,
                'layer': layer,
                'id': id
            }
        }
        self.entity_list.append(entity)
    
    
    def adjust_to_reference(self):
        """Set DXF reference point to first entity's starting position."""
        if self.entity_list:
            first_entity = self.entity_list[0]
            self.dxf_reference_point = first_entity['param']['start']

    def order_entity_list(self, entity_list, initial_point):
        """Orden de entidades ya optimizado en ``optimize_layer_traversal`` / encadenado de relleno.

        Reordenar aquí duplicaría lógica con ``path_optimizer`` y ``chain_fill_linestrings``;
        se mantiene identidad salvo extensiones futuras (p. ej. 2-opt global sobre entidades).
        """
        return entity_list

    def get_entity_list(self):
        """Return current list of generated entities.
        
        Returns:
            list: Current entity list
        """
        return self.entity_list