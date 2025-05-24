class MachineHandler: 
    
    def __init__ (self,x,y,z,f): #lo hago a lo ultimo, hay que considerar los paremtros de inicializacion.
        self.x = x
        self.y = y
        self.z = z
        
    
    def _linear_move (self, start_p, end_p):
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z} Y{self.y}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G1 X{end_p.x} Y{end_p.y} Z{self.z} F{self.f}\n' #faltaria agregar logica para extruder
        self.x, self.y = end_p.x, end_p.y
    
    def _arc_move (self, start_p, end_p, i, j,value): #podriamos agregar logica para circulo completo con el comando P
        if not ((self.x == start_p.x) and (self.y == start_p.y)):
            self.g_code += f'G0 X{start_p.x} Y{start_p.y} Z{self.z} Y{self.y}\n' #We don't have any line between the last point and the actual point
        self.g_code += f'G{value} X{end_p.x} Y{end_p.y} Z{self.z} I{i} J{j} F{self.f} \n' #faltaria logica para E
        self.x, self.y = end_p.x, end_p.y
    
    def _generate_gcode (self, entity_list):
        for i in range(0,self.layers):
            self.z = self.layer_thick * i
            for command in entity_list: 
                if (command['command'] == 'G1'):
                    self._linear_move(self,command['param']['start'],command['param']['end'])
                elif (command['command'] == 'G2-3'):
                    self._arc_move(self,command['param']['start'],command['param']['end'],command['param']['i'],command['param']['j'],command['param']['value'])
                    