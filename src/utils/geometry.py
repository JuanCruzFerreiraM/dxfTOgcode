import math as m
from ezdxf.math import Vec3



def distance(x1, y1, x2, y2):
    """
    Calculates the Euclidean distance between two points.

    #### Args:
    - x1 (float): X-coordinate of the first point.
    - y1 (float): Y-coordinate of the first point.
    - x2 (float): X-coordinate of the second point.
    - y2 (float): Y-coordinate of the second point.

    #### Returns:
    - float: The Euclidean distance between the two points.
    """
    return m.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def bulge_to_radius (x1,y1,x2,y2,bulge):
   theta = 2*m.atan(bulge) #Se considera ya la division por dos que ocurre dentro del seno
   return (distance(x1,y1,x2,y2)) / (2*m.sin(theta))

def is_ccw (star_angle, end_angle):
   delta = (end_angle - star_angle) %360
   return delta > 0 and delta < 180



def bulge_to_center(end_p, start_p, bulge): 
  xs,ys = start_p.x,start_p.y
  xe,ye = end_p.x, end_p.y
  
  dx = xe - xs
  dy = ye - ys
  l = distance(xs,ys,xe,ye)
  h = (l/2) * bulge
  
  mx = (xe + xs) / 2
  my = (ye + ys) / 2
   
  perp_x = -dy/l
  perp_y = dx/l
  
  cx = mx + h * perp_x
  cy = my + h* perp_y
  
  return Vec3(cx,cy,0) 

def center_of_shape(points_list):
   n = len(points_list)
   x = sum(p.x for p in points_list) / n 
   y = sum(p.y for p in points_list) / n
   return Vec3(x,y,0)