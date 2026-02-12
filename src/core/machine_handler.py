import math
from src.utils.geometry import distance

class LayerTimeError(Exception):
    """Exception raised when layer time exceeds maximum limit."""
    
    def __init__(self, layer_time, t_max, layer_number):
        self.layer_time = layer_time
        self.t_max = t_max
        self.layer_number = layer_number
        super().__init__(f"Layer {layer_number}: tiempo de capa ({layer_time:.2f} min) excede el límite máximo ({t_max:.2f} min)")


class MachineHandler:
    """Handles G-code generation for 3D printer movements and operations."""
    
    def __init__(self, x=0, y=0, z=0, f=2500, fG0=2500, e=0, layer_thick=1, z_safe=20.0,
                 start_point=None, start_description="No especificado"):
        """Initialize MachineHandler.
        
        Args:
            x, y, z: Initial position
            f: Print feed rate (mm/min)
            fG0: Travel feed rate (mm/min)
            e: Extrusion factor
            layer_thick: Layer thickness (mm)
            z_safe: Safe Z height for travel moves (mm). Must be higher than tallest printed feature.
            start_point: Tuple (x, y) with the starting point coordinates
            start_description: Human-readable description of the starting corner
        """
        # Construir header con información del punto de inicio
        start_info = ""
        if start_point:
            start_info = (
                "; ================================================\n"
                f"; PUNTO DE INICIO REQUERIDO:\n"
                f";   X = {start_point[0]:.2f} mm\n"
                f";   Y = {start_point[1]:.2f} mm\n"
                f";   Esquina: {start_description}\n"
                "; \n"
                "; Posicione la boquilla en estas coordenadas\n"
                "; antes de ejecutar este archivo.\n"
                "; ================================================\n"
            )
        
        self.g_code = (
            "G21    ; Set units to mm\n"
            "G90    ; Set absolute positioning mode\n"
            f"{start_info}"
            "M107   ; Turn off the fan\n"
            "G28    ; Home all axes\n"
            "G1 Z20.0 ; First layer printing height\n"
        )
        self.x = x
        self.y = y
        self.z = z
        self.f = f
        self.fG0 = fG0
        self.e = e
        self.layer_thick = layer_thick
        self.z_safe = z_safe  # Altura de seguridad para movimientos de viaje
        # Inicializar contadores totales
        self.total_g0 = 0.0
        self.total_g1 = 0.0

    def _linear_move(self, start_p, end_p):
        """Generate G1 linear movement command."""
        # CORRECCIÓN: Pasar coordenadas separadas (x1, y1, x2, y2)
        dist = distance(start_p.x, start_p.y, end_p.x, end_p.y)
        
        e_val = dist * self.e * self.layer_thick
        
        self.g_code += f"G1 X{end_p.x:.5f} Y{end_p.y:.5f} F{self.f} E{e_val:.5f}\n"
        
        self.x = end_p.x
        self.y = end_p.y
        return dist

    def _arc_move(self, start_p, end_p, i, j, command):
        """Generate G2/G3 arc movement command."""
        arc_len = self._calculate_arc_length(start_p, end_p, i, j, command)
        
        e_val = arc_len * self.e * self.layer_thick
        
        self.g_code += f"{command} X{end_p.x:.5f} Y{end_p.y:.5f} I{i:.5f} J{j:.5f} F{self.f} E{e_val:.5f}\n"
        
        self.x = end_p.x
        self.y = end_p.y
        return arc_len

    def _calculate_arc_length(self, start_p, end_p, i, j, command):
        radius = math.sqrt(i**2 + j**2)
        if radius < 1e-5:
            return 0.0

        center_x = start_p.x + i
        center_y = start_p.y + j

        start_angle = math.atan2(start_p.y - center_y, start_p.x - center_x)
        end_angle = math.atan2(end_p.y - center_y, end_p.x - center_x)

        diff = end_angle - start_angle

        if command == 'G3':  # CCW
            if diff <= 0:
                diff += 2 * math.pi
        else:  # G2 - CW
            if diff >= 0:
                diff -= 2 * math.pi
            diff = abs(diff)

        return radius * diff
    
    def generate_gcode(self, entity_list, i, max_height, t_min, t_max):
        dfG0 = 0.0
        dfG1 = 0.0
        
        if i == 0:
            self.g_code += f"G0 Z{self.layer_thick:.3f} F{self.fG0}\n"
            self.z = self.layer_thick
        else:
            new_z = self.z + self.layer_thick
            self.g_code += f"G0 Z{new_z:.3f} F{self.fG0}\n"
            self.z = new_z

        for entity in entity_list:
            command = entity['command']
            param = entity['param']
            start = param['start']
            end = param['end']

            # CORRECCIÓN: Pasar coordenadas separadas a distance
            if distance(self.x, self.y, start.x, start.y) > 0.001:
                dist_travel = distance(self.x, self.y, start.x, start.y)
                self.g_code += f"; Aca debe ir el comando para cerrar la boquilla\n"
                self.g_code += f"G0 Z{(self.z + self.z_safe):.5f} F{self.fG0}\n" 
                self.g_code += f"G0 X{start.x:.5f} Y{start.y:.5f} F{self.fG0}\n"
                self.g_code += f"G0 Z{self.z:.5f} F{self.fG0}\n"
                self.g_code += f"; Aca debe ir el comando para abrir la boquilla\n"
                self.x = start.x
                self.y = start.y
                dfG0 += dist_travel

            if command == 'G1':
                dist = self._linear_move(start, end)
                dfG1 += dist
            elif command in ['G2', 'G3']:
                dist = self._arc_move(start, end, param['i'], param['j'], command)
                dfG1 += dist

        # Actualizar totales
        self.total_g0 += dfG0
        self.total_g1 += dfG1

        layer_time = (dfG1 / self.f) + (dfG0 / self.fG0)

        if layer_time > t_max:
            raise LayerTimeError(layer_time, t_max, i)
        elif layer_time < t_min and self.z != max_height:
            dif = (t_min - layer_time) * 60
            self.g_code += f'G4 S{round(dif)} ;Wait till settle time\n'
            print(f"Layer {i}: tiempo ajustado de {layer_time:.2f}min a {t_min:.2f}min")
       
        if self.z == max_height:
            self.g_code += ';End of file\n'
            total_time = (self.total_g0 / self.fG0) + (self.total_g1 / self.f)
            print(f'distancia g0 = {self.total_g0} distancia g1 = {self.total_g1}')
            print(f'TIME G0 = {self.total_g0 / self.fG0:.2f} TIME G1 = {self.total_g1 / self.f:.2f}')
            print(f'TOTAL TIME = {total_time:.2f} minutes')
