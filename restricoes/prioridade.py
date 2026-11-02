"""
[RESTRIÇÃO: PRIORIDADE]
Entregas críticas (medicamentos) devem ser atendidas antes das comuns (insumos).
"""
import random
from typing import Dict, List, Tuple

from algoritmo.distancia import calculate_distance
from config import CRITICAL_TRIP_LIMIT, CRITICAL_WEIGHT, LATE_CRITICAL_PENALTY, REGULAR_WEIGHT

CRITICAL = "critical"
REGULAR = "regular"
PRIORITY_WEIGHTS = {CRITICAL: CRITICAL_WEIGHT, REGULAR: REGULAR_WEIGHT}


def split_into_distance_bands(cities: List[Tuple[float, float]], depot: Tuple[float, float],
                              n_bands: int) -> List[List[Tuple[float, float]]]:
    """Ordena os pontos pela distância à central e os divide em faixas de tamanho parecido."""
    by_distance = sorted(cities, key=lambda city: calculate_distance(depot, city))
    band_size, extra = divmod(len(by_distance), n_bands)

    bands = []
    start = 0
    for band_index in range(n_bands):
        end = start + band_size + (1 if band_index < extra else 0)
        bands.append(by_distance[start:end])
        start = end
    return bands


def choose_spread_criticals(cities: List[Tuple[float, float]], depot: Tuple[float, float],
                            n_critical: int) -> List[Tuple[float, float]]:
    """Escolhe uma crítica por faixa, a mais afastada das críticas já escolhidas."""
    bands = split_into_distance_bands(cities, depot, n_critical)

    chosen = [random.choice(bands[0])]
    for band in bands[1:]:
        chosen.append(max(band, key=lambda city: min(calculate_distance(city, other) for other in chosen)))
    return chosen


def generate_priorities(cities: List[Tuple[float, float]], critical_ratio: float = 0.3,
                        depot: Tuple[float, float] = None) -> Dict[Tuple[float, float], str]:
    """Define a prioridade de cada entrega. Com a central informada, as críticas ficam espalhadas."""
    n_critical = round(len(cities) * critical_ratio)

    if depot is None or n_critical == 0:
        critical_cities = set(random.sample(cities, n_critical))
    else:
        critical_cities = set(choose_spread_criticals(cities, depot, n_critical))

    return {city: CRITICAL if city in critical_cities else REGULAR for city in cities}


def split_by_priority(cities: List[Tuple[float, float]],
                      priorities: Dict[Tuple[float, float], str]) -> Tuple[List, List]:
    """Separa os pontos em (críticos, comuns)."""
    critical = [city for city in cities if priorities[city] == CRITICAL]
    regular = [city for city in cities if priorities[city] != CRITICAL]
    return critical, regular


def calculate_delivery_penalty(priority: str, accumulated_distance: float, trip_index: int,
                               trip_limit: int = CRITICAL_TRIP_LIMIT,
                               late_penalty: float = LATE_CRITICAL_PENALTY) -> float:
    """Penalidade de uma entrega. `trip_index` começa em 0 (0 = primeira viagem)."""
    penalty = PRIORITY_WEIGHTS[priority] * accumulated_distance
    if priority == CRITICAL and trip_index >= trip_limit:
        penalty += late_penalty
    return penalty


def calculate_priority_penalty(trips: List[List[Tuple[float, float]]], depot: Tuple[float, float],
                               priorities: Dict[Tuple[float, float], str],
                               trip_limit: int = CRITICAL_TRIP_LIMIT,
                               late_penalty: float = LATE_CRITICAL_PENALTY) -> float:
    """Soma a penalidade da rota. A distância acumulada não zera entre as viagens."""
    accumulated_distance = 0
    penalty = 0

    for trip_index, trip in enumerate(trips):
        location = depot
        for city in trip:
            accumulated_distance += calculate_distance(location, city)
            penalty += calculate_delivery_penalty(priorities[city], accumulated_distance, trip_index,
                                                  trip_limit, late_penalty)
            location = city
        # Volta à central: soma na distância, mas não é uma entrega
        accumulated_distance += calculate_distance(location, depot)

    return penalty


def count_late_criticals(trips: List[List[Tuple[float, float]]], priorities: Dict[Tuple[float, float], str],
                         trip_limit: int = CRITICAL_TRIP_LIMIT) -> int:
    """Conta as críticas que ficaram depois da viagem limite."""
    return sum(priorities[city] == CRITICAL for trip in trips[trip_limit:] for city in trip)
