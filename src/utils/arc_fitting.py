import numpy as np
import scipy as sc

def calculate_centroid(point_list):
    x_sum = 0
    y_prom = 0
    n = len(point_list)
    for point in  point_list:
        x_sum += point[0]
        y_sum += point[1]
    return np.array([x_sum / n, y_sum / n])
        

def preprocess_for_hyperfit(centroid, point_list):
    translated_points = []
    for point in point_list:
        x_translated = point[0] - centroid[0]
        y_translated = point[1] - centroid[1]
        z_translated = (x_translated ** 2) + (y_translated ** 2)
        translated_point = np.array([x_translated,y_translated,z_translated])
        translated_points.append(translated_point)
    return translated_points

def calculate_M (point_list):
    