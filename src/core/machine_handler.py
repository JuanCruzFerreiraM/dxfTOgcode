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
        if (self.e == None):
            extruder = ''
        else:
            extruder = f'E{self.e}'    
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z + 0.5} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G1 X{end_p.x} Y{end_p.y} Z{self.z} F{self.f} {extruder}\n'
        self.x, self.y = end_p.x, end_p.y
    
    def _arc_move (self, start_p, end_p, i, j,value): #podríamos agregar lógica para circulo completo con el comando P
        if (self.e == None):
            extruder = ''
        else:
            extruder = f'E{self.e}'    
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z + 0.5} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G{value} X{end_p.x} Y{end_p.y} Z{self.z} I{i} J{j} F{self.f} {extruder}\n' #faltaría lógica para E
        self.x, self.y = end_p.x, end_p.y
    
    def generate_gcode (self, entity_list,file_name, i, max_height): #Lo adaptamos a manejar solo una capa. 
        f = open(file_name, "a")
        if (i == 0):
            f.write('G21    ; Establece las unidades en mm\nG90  ; Establece el modo de pos absoluto\nM107    ; Apaga el ventilador\n')
            f.write('G28    ; Home de todos los ejes\nG1 Z0.3   ; Altura de impresión de la primera capa\n')
        f.write(f'; Layer {i}\n')
        self.z = self.layers_thick * i
        for command in entity_list: 
            if (command['command'] == 'G1'):
                self._linear_move(command['param']['start'],command['param']['end'])
            elif (command['command'] == 'G2-3'):
                self._arc_move(command['param']['start'],command['param']['end'],command['param']['i'],command['param']['j'],command['param']['value'])
            #Agregar algún lógica necesaria para el final de cada layer.
        f.write(self.g_code)
        self.g_code = ''
        if (self.z == max_height):
            f.write(';Final del archivo')