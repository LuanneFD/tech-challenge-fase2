# -*- coding: utf-8 -*-
"""
[RESTRIÇÃO: CARGA]
O veículo tem peso máximo: quando a próxima entrega não cabe, ele volta à central.
"""
import random
from typing import Dict, List, Optional, Tuple

from config import LOW_OCCUPANCY_PENALTY, MAX_DEMAND, MIN_DEMAND, MIN_TRIP_OCCUPANCY


def generate_demands(cities: List[Tuple[float, float]], min_demand: int = MIN_DEMAND,
                     max_demand: int = MAX_DEMAND) -> Dict[Tuple[float, float], int]:
    """Sorteia o peso, em kg, de cada entrega."""
    return {city: random.randint(min_demand, max_demand) for city in cities}


def validate_demand(city: Tuple[float, float], demand: int, capacity: Optional[int]) -> None:
    """Dá erro se a entrega não couber no veículo nem sozinha."""
    if capacity is not None and demand > capacity:
        raise ValueError(f"A entrega em {city} pesa {demand} kg, mais que a capacidade de {capacity} kg")


def fits_load(current_load: int, demand: int, capacity: Optional[int]) -> bool:
    """Diz se a entrega cabe na carga da viagem. Sem capacidade, sempre cabe."""
    return capacity is None or current_load + demand <= capacity


def calculate_trip_load(trip: List[Tuple[float, float]], demands: Dict[Tuple[float, float], int]) -> int:
    """Soma o peso das entregas de uma viagem."""
    return sum(demands[city] for city in trip)


def calculate_trip_occupancy_penalty(load: int, capacity: int, min_occupancy: float = MIN_TRIP_OCCUPANCY,
                                     penalty_per_point: float = LOW_OCCUPANCY_PENALTY) -> float:
    """Penalidade de uma viagem: soma um valor por ponto percentual abaixo da ocupação mínima."""
    missing_points = max(0, min_occupancy - load / capacity) * 100
    return missing_points * penalty_per_point


def calculate_occupancy_penalty(trips: List[List[Tuple[float, float]]], demands: Optional[Dict],
                                capacity: Optional[int], min_occupancy: float = MIN_TRIP_OCCUPANCY,
                                penalty_per_point: float = LOW_OCCUPANCY_PENALTY) -> float:
    """Soma a penalidade das viagens com pouca carga. Sem pesos ou capacidade, não há penalidade."""
    if demands is None or capacity is None:
        return 0
    return sum(calculate_trip_occupancy_penalty(calculate_trip_load(trip, demands), capacity, min_occupancy,
                                                penalty_per_point)
               for trip in trips)
