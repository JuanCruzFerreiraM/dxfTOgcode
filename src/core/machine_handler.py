class MachineHandler: 
    
    def __init__ (self,x=0,y=0,z=0,f=2500,layers=1,layer_thick=1): #Analizar que otros parámetros de inicio y que valores default
        self.g_code = ''
        self.x = x
        self.y = y
        self.z = z
        self.f = f
        self.layers = layers
        self.layers_thick = layer_thick
        
    
    def _linear_move (self, start_p, end_p):
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G1 X{end_p.x} Y{end_p.y} Z{self.z} F{self.f}\n' #faltaría agregar lógica para extruder
        self.x, self.y = end_p.x, end_p.y
    
    def _arc_move (self, start_p, end_p, i, j,value): #podríamos agregar lógica para circulo completo con el comando P
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z} F{self.f}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G{value} X{end_p.x} Y{end_p.y} Z{self.z} I{i} J{j} F{self.f}\n' #faltaría lógica para E
        self.x, self.y = end_p.x, end_p.y
    
    def generate_gcode (self, entity_list,file_name):
        f = open(file_name, "w")
        f.write('G21    ; Establece las unidades en mm\nG90  ; Establece el modo de pos absoluto\nM107    ; Apaga el ventilador')
        f.write('G28    ; Home de todos los ejes\nG1 Z0.3   ; Altura de impresión de la primera capa')
        """
        De estos analizar si verdaderamente son los valores que quiero o tengo que adaptarlos al convertidor, sobre todo el home de los ejes y eso.
        Consultar cual es el home. Supongo que alguna esquina de la maquina, pero cual esquina, una opción es parametrizar y trabajar con la que sea mas
        cómoda para el caso que seleccione.
        """

        for i in range(0,self.layers):
            f.write(f'Layer {i}\n')
            self.z = self.layer_thick * i
            for command in entity_list: 
                if (command['command'] == 'G1'):
                    self._linear_move(self,command['param']['start'],command['param']['end'])
                elif (command['command'] == 'G2-3'):
                    self._arc_move(self,command['param']['start'],command['param']['end'],command['param']['i'],command['param']['j'],command['param']['value'])
            #Agregar algún lógica necesaria para el final de cada layer.
            f.write(self.g_code)        
        #Agregar lógica para final de archivo, apagar motores o cosas por el estilo.