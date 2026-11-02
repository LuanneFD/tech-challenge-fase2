"""Cálculo de distância entre dois pontos do mapa."""
import math
from typing import Tuple


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """Distância em linha reta entre dois pontos."""
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
