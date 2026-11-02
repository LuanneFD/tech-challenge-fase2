"""
[RESTRIÇÃO: AUTONOMIA]
O veículo tem distância máxima por viagem: ele volta à central antes de usar a reserva.
"""
from typing import List, Tuple

from algoritmo.distancia import calculate_distance
from config import AUTONOMY_RESERVE


def calculate_usable_autonomy(autonomy: float, reserve: float = AUTONOMY_RESERVE) -> float:
    """Autonomia que pode ser usada por viagem, sem a reserva de segurança."""
    return autonomy * (1 - reserve)


def validate_reach(city: Tuple[float, float], depot: Tuple[float, float], usable_autonomy: float) -> None:
    """Dá erro se o veículo não conseguir ir até a entrega e voltar nem em uma viagem só para ela."""
    if 2 * calculate_distance(depot, city) > usable_autonomy:
        raise ValueError(f"A entrega em {city} está longe demais da central para a "
                         f"autonomia útil de {usable_autonomy:.0f}")


def fits_autonomy(trip_distance: float, location: Tuple[float, float], city: Tuple[float, float],
                  depot: Tuple[float, float], usable_autonomy: float) -> bool:
    """Diz se, depois de ir até a entrega, ainda dá para voltar à central."""
    distance_after_delivery = trip_distance + calculate_distance(location, city)
    return distance_after_delivery + calculate_distance(city, depot) <= usable_autonomy


def calculate_trip_distance(trip: List[Tuple[float, float]], depot: Tuple[float, float]) -> float:
    """Distância de uma viagem: sai da central, faz as entregas e volta."""
    stops = [depot] + list(trip) + [depot]
    return sum(calculate_distance(stops[i], stops[i + 1]) for i in range(len(stops) - 1))
