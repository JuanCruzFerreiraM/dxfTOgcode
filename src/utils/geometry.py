import math as m
from ezdxf.math import Vec3


def distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two 2D points.

    Args:
        x1 (float): X-coordinate of first point
        y1 (float): Y-coordinate of first point
        x2 (float): X-coordinate of second point
        y2 (float): Y-coordinate of second point

    Returns:
        float: Euclidean distance between the points
    """
    return m.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def distance_vec3_xy(a, b):
    """Distancia euclídea en plano XY entre dos Vec3 (ignora Z)."""
    return m.hypot(a.x - b.x, a.y - b.y)


def bulge_to_radius(x1, y1, x2, y2, bulge):
    """Calculate arc radius from bulge factor and chord endpoints.
    
    Args:
        x1 (float): X-coordinate of arc start point
        y1 (float): Y-coordinate of arc start point
        x2 (float): X-coordinate of arc end point
        y2 (float): Y-coordinate of arc end point
        bulge (float): Bulge factor defining arc curvature
        
    Returns:
        float: Arc radius
    """
    theta = 2 * m.atan(bulge)
    return distance(x1, y1, x2, y2) / (2 * m.sin(theta))


def is_ccw(start_angle, end_angle):
    """Determine if arc direction is counter-clockwise.
    
    Args:
        start_angle (float): Starting angle in degrees
        end_angle (float): Ending angle in degrees
        
    Returns:
        bool: True if counter-clockwise, False if clockwise
    """
    delta = (end_angle - start_angle) % 360
    return delta > 0 and delta < 180


def bulge_to_center(end_p, start_p, bulge):
    """Calculate arc center point from endpoints and bulge factor.
    
    Args:
        end_p (Vec3): Arc end point
        start_p (Vec3): Arc start point
        bulge (float): Bulge factor defining arc curvature
        
    Returns:
        Vec3: Arc center point coordinates
    """
    xs, ys = start_p.x, start_p.y
    xe, ye = end_p.x, end_p.y
    
    dx = xe - xs
    dy = ye - ys
    l = distance(xs, ys, xe, ye)
    h = (l / 2) * bulge
    
    mx = (xe + xs) / 2
    my = (ye + ys) / 2
    
    perp_x = -dy / l
    perp_y = dx / l
    
    cx = mx + h * perp_x
    cy = my + h * perp_y
    
    return Vec3(cx, cy, 0)


def center_of_shape(points_list):
    """Calculate geometric center (centroid) of a list of points.
    
    Args:
        points_list (list): List of Vec3 points
        
    Returns:
        Vec3: Center point coordinates
    """
    n = len(points_list)
    x = sum(p.x for p in points_list) / n 
    y = sum(p.y for p in points_list) / n
    return Vec3(x, y, 0)

def calculate_centroid_from_trims(trim1,trim2,z):
    cx = (trim1[0] + trim2[0]) /2
    cy = (trim1[1] + trim2[1]) /2
    
    return Vec3(cx,cy,z)