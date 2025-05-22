# last_mod = 22/05/2025
import ezdxf
from math import radians, sin, cos

#Analizar si es necesario usar G0 al principio de cada movimiento, todo depende de como leamos la lineas. 

#recibimos dos vectores, en este caso deberiamos ingorar z? osea nos mandan el plano de solo una casa ? 
def line_movement (x_s,y_s,z_s,x_f,y_f,z_f):
    """
    This function handles the conversion between dxf parameters for ARC entity to valid g-code 

    #### args
     
    - x_s: initial x coordinate.
    - y_s: initial y coordinate.
    - z_s: initial z coordinate.
    - x_f: final x coordinate.
    - y_f: final y coordinate.
    - z_f: final z coordinate.
    
    #### return
    
    A string with the g-code using G1.
    """
    not_extruder_mov = f'G0 X{x_s} Y{y_s} Z{z_s}\n'
    extruder_mov = f'G1 X{x_f} Y{y_f} Z{z_f}\n'
    return not_extruder_mov + extruder_mov #remplazar por el string directo, ahorro de memoria


def arc_movement (center_x, center_y, radius, theta_s, theta_f):
    """
    This function handles the conversion between dxf parameters for ARC entity to valid g-code 

    #### args
     
    - center_x: x coordinate of the center of the arc.
    - center_y: y coordinate of the center of the arc.
    - radius: radius of the arc
    - theta_s: angle between the center and the starter point of the arc 
    - theta_f: angle between the center and the final point of the arc 
    
    #### return
    
    A string with the g-code using G2 or G3 depending on wether the rotation is clockwise or counterclockwise. 
    """
    x_s = radius*cos(radians(theta_s)) + center_x
    y_s = radius*sin(radians(theta_s)) + center_y
    x_f = radius*cos(radians(theta_f)) + center_x
    y_f = radius*sin(radians(theta_f)) + center_y
    delta = (theta_f - theta_s)%360
    if 0 < delta < 180: #cw or ccw
        command = 'G3'
    else:
        command = 'G2'    
    return f'G0 X{x_s} Y{y_s}\n{command} X{x_f} Y{y_f} R{radius}\n'


# movimientos en circulo competo afrontar mas adelante, son relativamente complejos, en principio en la maquina no los necesitamos.

def polyline_movement (points_list):
    index = 0
    g_code = ''
    for point in points_list:
        index += 1
        x = point.x
        y = point.y
        curve_factor = point.bulge #en este caso tengo que usar un vector, el valor en i corresponde a [i] -> [i+1] entonces tengo que usar el bulge
                                   #de index -1. Revisar
        if (curve_factor == 0): 
            command = 'G0' if (index == 1) else 'G1'
            g_code = g_code + f'{command} X{x} Y{y}' #analizar integrar con la función line_movement
        else:
            # lógica para el curve factor es curve_factor = tan(theta/4) donde theta es el angulo central de la curva.
            #luego usamos comandos g3 o g4, nose que tan bueno esta usar arc_movement ya que tendríamos que hacer mucha adaptación matemática me parece
            #hay que ver como determino el con el angulo central tengo que determinar el radio o los offset, y el punto final ?