import math as m



def distance (x1,y1,x2,y2):
   return m.sqrt((x2-x1)**2+ (y2-y1)**2)

def bulge_to_radius (x1,y1,x2,y2,bulge):
   theta = 2*m.atan(bulge) #Se considera ya la division por dos que ocurre dentro del seno
   return (distance(x1,y1,x2,y2)) / (2*m.sin(theta))

def is_ccw (star_angle, end_angle):
   delta = (end_angle - star_angle) %360
   return delta > 0 and delta < 180