import numpy as np
from math import sqrt
from .utils import CENTER, GSD

def area_and_distance(mask):
    area = mask.sum() * (GSD ** 2)
    ys, xs = np.where(mask == 1)
    cx, cy = xs.mean(), ys.mean()
    dx, dy = cx - CENTER[0], cy - CENTER[1]
    dist = sqrt(dx*dx + dy*dy) * GSD
    return round(area, 2), round(dist, 2)
