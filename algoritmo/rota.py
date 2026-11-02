"""Divide a rota em viagens e calcula o custo, aplicando as restrições."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from algoritmo.distancia import calculate_distance
from config import AUTONOMY_RESERVE
from restricoes.autonomia import calculate_trip_distance, calculate_usable_autonomy, fits_autonomy, validate_reach
from restricoes.carga import calculate_occupancy_penalty, calculate_trip_load, fits_load, validate_demand
from restricoes.prioridade import calculate_priority_penalty


def split_into_trips(path: List[Tuple[float, float]], demands: Optional[Dict] = None,
                     capacity: Optional[int] = None, depot: Optional[Tuple[float, float]] = None,
                     autonomy: Optional[float] = None,
                     reserve: float = AUTONOMY_RESERVE) -> List[List[Tuple[float, float]]]:
    """Fecha a viagem e volta à central quando a próxima entrega não cabe na carga ou na autonomia."""
    # [RESTRIÇÃO: AUTONOMIA] Só vale com a central informada, para saber a distância de volta
    use_autonomy = depot is not None and autonomy is not None
    usable_autonomy = calculate_usable_autonomy(autonomy, reserve) if use_autonomy else None

    trips = []
    current_trip = []
    current_load = 0
    trip_distance = 0
    location = depot

    for city in path:
        demand = demands[city] if demands is not None else 0

        # Confere se a entrega é possível
        validate_demand(city, demand, capacity)
        if use_autonomy:
            validate_reach(city, depot, usable_autonomy)

        # Confere se a entrega cabe na viagem atual
        fits = fits_load(current_load, demand, capacity)
        if use_autonomy:
            fits = fits and fits_autonomy(trip_distance, location, city, depot, usable_autonomy)

        # Não cabe: volta à central e começa outra viagem
        if current_trip and not fits:
            trips.append(current_trip)
            current_trip = []
            current_load = 0
            trip_distance = 0
            location = depot

        # Faz a entrega
        if use_autonomy:
            trip_distance += calculate_distance(location, city)
        location = city
        current_trip.append(city)
        current_load += demand

    if current_trip:
        trips.append(current_trip)
    return trips


def calculate_route_distance(trips: List[List[Tuple[float, float]]], depot: Tuple[float, float]) -> float:
    """Distância total das viagens, somando as voltas à central."""
    total = 0
    for trip in trips:
        location = depot
        for city in trip:
            total += calculate_distance(location, city)
            location = city
        total += calculate_distance(location, depot)
    return total


def build_trips(path: List[Tuple[float, float]], depot: Tuple[float, float], demands: Optional[Dict] = None,
                capacity: Optional[int] = None, autonomy: Optional[float] = None) -> List[List[Tuple[float, float]]]:
    """Monta as viagens da rota. Sem carga nem autonomia, a rota é uma viagem só."""
    if (demands is None or capacity is None) and autonomy is None:
        return [list(path)]
    return split_into_trips(path, demands, capacity, depot, autonomy)


def calculate_route_metrics(path: List[Tuple[float, float]], depot: Tuple[float, float], priorities: Dict,
                            demands: Optional[Dict] = None, capacity: Optional[int] = None,
                            autonomy: Optional[float] = None) -> Tuple[float, float]:
    """Retorna (distância total, penalidade de prioridade) da rota."""
    trips = build_trips(path, depot, demands, capacity, autonomy)
    return calculate_route_distance(trips, depot), calculate_priority_penalty(trips, depot, priorities)


def calculate_priority_fitness(path: List[Tuple[float, float]], depot: Tuple[float, float], priorities: Dict,
                               demands: Optional[Dict] = None, capacity: Optional[int] = None,
                               autonomy: Optional[float] = None) -> float:
    """Custo da rota: distância + penalidade de prioridade + penalidade de ocupação. Quanto menor, melhor."""
    trips = build_trips(path, depot, demands, capacity, autonomy)
    return (calculate_route_distance(trips, depot) + calculate_priority_penalty(trips, depot, priorities)
            + calculate_occupancy_penalty(trips, demands, capacity))


@dataclass
class RouteSummary:
    """Dados da rota usados na tela e no terminal."""
    distance: float
    penalty: float
    occupancy_penalty: float
    trips: List[List[Tuple[float, float]]]
    trip_distances: List[float]
    trip_loads: List[int]


def summarize_route(route: List[Tuple[float, float]], problem) -> RouteSummary:
    """Reúne distância, penalidades, viagens, distância e carga de cada viagem."""
    distance, penalty = calculate_route_metrics(route, problem.depot, problem.priorities, problem.demands,
                                                problem.capacity, problem.autonomy)
    trips = split_into_trips(route, problem.demands, problem.capacity, problem.depot, problem.autonomy)
    occupancy_penalty = calculate_occupancy_penalty(trips, problem.demands, problem.capacity)
    return RouteSummary(distance, penalty, occupancy_penalty, trips,
                        [calculate_trip_distance(trip, problem.depot) for trip in trips],
                        [calculate_trip_load(trip, problem.demands) for trip in trips])
