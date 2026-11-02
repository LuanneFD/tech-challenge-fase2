"""Monta o problema: pontos de entrega, central, prioridades e pesos."""
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from config import (CRITICAL_RATIO, DEPOT, MAP_HEIGHT, N_CITIES, NODE_RADIUS, PLOT_X_OFFSET, VEHICLE_AUTONOMY,
                    VEHICLE_CAPACITY, WIDTH)
from restricoes.carga import generate_demands
from restricoes.prioridade import generate_priorities


@dataclass
class Problem:
    """Dados de uma execução."""
    cities: List[Tuple[int, int]]
    depot: Tuple[int, int]
    priorities: Dict
    demands: Dict
    capacity: int
    autonomy: float


def create_random_cities(n_cities: int = N_CITIES) -> List[Tuple[int, int]]:
    """Sorteia os pontos de entrega dentro da área do mapa."""
    return [(random.randint(NODE_RADIUS + PLOT_X_OFFSET, WIDTH - NODE_RADIUS),
             random.randint(NODE_RADIUS, MAP_HEIGHT - NODE_RADIUS))
            for _ in range(n_cities)]


def create_problem() -> Problem:
    """Sorteia os pontos e define a prioridade e o peso de cada entrega."""
    cities = create_random_cities()
    priorities = generate_priorities(cities, CRITICAL_RATIO, DEPOT)
    demands = generate_demands(cities)
    return Problem(cities, DEPOT, priorities, demands, VEHICLE_CAPACITY, VEHICLE_AUTONOMY)
