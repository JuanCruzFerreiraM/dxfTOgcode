from src.utils.geometry import distance
import math


class LayerTimeError(Exception):
    """Exception raised when layer time exceeds maximum limit."""
    
    def __init__(self, layer_time, t_max, layer_number):
        """Initialize LayerTimeError exception.
        
        Args:
            layer_time (float): Actual layer time in minutes
            t_max (float): Maximum allowed layer time in minutes
            layer_number (int): Layer number that exceeded the limit
        """
        self.layer_time = layer_time
        self.t_max = t_max
        self.layer_number = layer_number
        super().__init__(f"Layer {layer_number}: tiempo de capa ({layer_time:.2f} min) excede el límite máximo ({t_max:.2f} min)")


class MachineHandler:
    """Handles G-code generation for 3D printer movements and operations."""
    
    def __init__(self, x=0, y=0, z=0, f=2500, fG0=2500, e=0, layer_thick=1):
        """Initialize MachineHandler with printer parameters.
        
        Args:
            x (float): Initial X coordinate position
            y (float): Initial Y coordinate position  
            z (float): Initial Z coordinate position
            f (int): Print feed rate in mm/min
            fG0 (int): Travel feed rate in mm/min
            e (float): Extrusion amount per mm
            layer_thick (float): Layer thickness in mm
        """
        self.g_code = ''
        self.x = x
        self.y = y
        self.z = z
        self.f = f
        self.e = e
        self.fG0 = fG0
        self.layers_thick = layer_thick
        self.disg0 = 0
        self.disg1 = 0
        
 
    def _linear_move(self, start_p, end_p):
        """Generate G-code for linear movement between two points.
        
        Args:
            start_p (Vec3): Starting point coordinates
            end_p (Vec3): Ending point coordinates
            
        Modifies:
            self.g_code (str): Appends generated G-code instructions
            self.x (float): Updates current X position
            self.y (float): Updates current Y position
        """
        extruder = f'E{self.e}' if self.e != 0 else ''
        
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 Z{self.z + 0.5:.3f} F{self.fG0}\n'
            self.g_code += f'G0 X{start_p.x:.3f} Y{start_p.y:.3f}\n'
            self.g_code += f'G0 Z{self.z:.3f} F{self.fG0}\n'
        
        self.g_code += f'G1 X{end_p.x:.3f} Y{end_p.y:.3f} Z{self.z:.3f} F{self.f} {extruder}\n'
        self.x, self.y = end_p.x, end_p.y
    
    def _arc_move(self, start_p, end_p, i, j, value):
        """Generate G-code for arc movement between two points.
        
        Args:
            start_p (Vec3): Starting point coordinates
            end_p (Vec3): Ending point coordinates
            i (float): X offset from start point to arc center
            j (float): Y offset from start point to arc center
            value (int): Arc direction (2 for clockwise, 3 for counter-clockwise)
            
        Modifies:
            self.g_code (str): Appends generated G-code instructions
            self.x (float): Updates current X position
            self.y (float): Updates current Y position
        """
        extruder = f'E{self.e}' if self.e != 0 else ''
        
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x:.3f} Y{start_p.y:.3f} Z{self.z + 0.5:.3f} F{self.fG0}\n'
        
        self.g_code += f'G{value} X{end_p.x:.3f} Y{end_p.y:.3f} Z{self.z:.3f} I{i:.3f} J{j:.3f} F{self.f} {extruder}\n'
        self.x, self.y = end_p.x, end_p.y
    
    def generate_gcode(self, entity_list, i, max_height, t_min, t_max):
        """Generate G-code for a layer from entity commands.
        
        Args:
            entity_list (list): List of movement commands with parameters
            i (int): Current layer number
            max_height (float): Maximum print height
            t_min (float): Minimum layer time in minutes
            t_max (float): Maximum layer time in minutes
            
        Raises:
            LayerTimeError: When layer time exceeds t_max
            
        Modifies:
            self.g_code (str): Appends generated G-code instructions
            self.z (float): Updates current Z position
        """
        if i == 0:
            self.g_code += 'G21    ; Set units to mm\nG90  ; Set absolute positioning mode\nM107    ; Turn off the fan\n'
            self.g_code += f'G28    ; Home all axes\nG1 Z{self.layers_thick}   ; First layer printing height\n'
        
        self.g_code += f'; Layer {i}\n'
        self.z = self.layers_thick * i
        dfG0 = 0
        dfG1 = 0
        
        for command in entity_list:
            d1 = distance(self.x, self.y, command['param']['start'].x, command['param']['start'].y)
            dfG0 += d1
            self.disg0 += d1
            d2 = distance(command['param']['start'].x, command['param']['start'].y, command['param']['end'].x, command['param']['end'].y)
            dfG1 += d2
            self.disg1 += d2
            
            if command['command'] == 'G1':
                self._linear_move(command['param']['start'], command['param']['end'])
            elif command['command'] == 'G2-3':
                self._arc_move(command['param']['start'], command['param']['end'], command['param']['i'], command['param']['j'], command['param']['value'])

        layer_time = (dfG0 / self.fG0) + (dfG1 / self.f)

        if layer_time > t_max:
            raise LayerTimeError(layer_time, t_max, i)
        elif layer_time < t_min and self.z != max_height:
            dif = (t_min - layer_time) * 60
            self.g_code += f'G4 S{round(dif)} ;Wait till settle time\n'
            print(f"Layer {i}: tiempo ajustado de {layer_time:.2f}min a {t_min:.2f}min")
        
        if self.z == max_height:
            self.g_code += ';End of file\n'
            total_time = (self.disg0 / self.fG0) + (self.disg1 / self.f)
            print(f'distancia g0 = {self.disg0} distancia g1 = {self.disg1}')
            print(f'TIME G0 = {self.disg0 / self.fG0:.2f} TIME G1 = {self.disg1 / self.f:.2f}')
            print(f'TOTAL TIME = {total_time:.2f} minutes')
