class MachineHandler: 
    
    def __init__ (self,x=0,y=0,z=0,f=2500,e = None,layer_thick=1): #Analizar que otros parámetros de inicio y que valores default
        self.g_code = ''
        self.x = x
        self.y = y
        self.z = z
        self.f = f
        self.e = e
        self.layers_thick = layer_thick
        
 
    def _linear_move (self, start_p, end_p):
        """
        This function generates de G-code for a straight line
    
        #### Args:
        - start_p (Vec3): The initial point of the line.
        - end_p (Vec3): The end point of the line.
        
        #### Modifies: 
        - self.g_code (str): Adds the generated G-code instruction
        - self.x (float): Updates to the actual x position
        - self.y (float): Updates to the actual y position
        """
        if (self.e == None):
            extruder = ''
        else:
            extruder = f'E{self.e}'    
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z + 0.5} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G1 X{end_p.x} Y{end_p.y} Z{self.z} F{self.f} {extruder}\n'
        self.x, self.y = end_p.x, end_p.y
    
    def _arc_move (self, start_p, end_p, i, j,value): #podríamos agregar lógica para circulo completo con el comando P
        """
        This function generates de G-code for a arc movement
    
        #### Args:
        - start_p (Vec3): The initial point of the arc.
        - end_p (Vec3): The end point of the arc.
        - i (float): The X offset between the initial point and the center of the arc
        - j (float): The Y offset between the initial point and the center of the arc
        - value (int): Type of G-code instruction  (2 for CW, 3 for CCW)
        
        #### Modifies: 
        - self.g_code (str): Adds the generated G-code instruction
        - self.x (float): Updates to the actual x position
        - self.y (float): Updates to the actual y position
        """
        if (self.e == None):
            extruder = ''
        else:
            extruder = f'E{self.e}'    
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z + 0.5} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G{value} X{end_p.x} Y{end_p.y} Z{self.z} I{i} J{j} F{self.f} {extruder}\n'
        self.x, self.y = end_p.x, end_p.y
    
    def generate_gcode(self, entity_list, file_name, i, max_height):
        """
        Generates the G-code file based on a list of entities.

        #### Args:
        - entity_list (list): List of entities containing G-code commands.
        - file_name (str): Name of the file where the G-code will be written.
        - i (int): Current layer number.
        - max_height (float): Maximum printing height.

        #### Modifies:
        - self.g_code (str): Resets after writing each layer.
        - self.z (float): Updates the current Z position.

        #### Writes:
        - file_name: Writes the generated G-code to the specified file.
        """
        f = open(file_name, "a")
        if (i == 0):
            f.write('G21    ; Set units to mm\nG90  ; Set absolute positioning mode\nM107    ; Turn off the fan\n')
            f.write('G28    ; Home all axes\nG1 Z0.3   ; First layer printing height\n')
        f.write(f'; Layer {i}\n')
        self.z = self.layers_thick * i
        for command in entity_list:
            if (command['command'] == 'G1'):
                self._linear_move(command['param']['start'], command['param']['end'])
            elif (command['command'] == 'G2-3'):
                self._arc_move(command['param']['start'], command['param']['end'], command['param']['i'], command['param']['j'], command['param']['value'])
        f.write(self.g_code)
        self.g_code = ''
        if (self.z == max_height):
            f.write(';End of file')