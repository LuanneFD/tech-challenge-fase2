"""Operadores do algoritmo genético: população, avaliação, seleção, cruzamento e mutação."""
import random
from dataclasses import dataclass
from typing import List, Tuple

from algoritmo.rota import calculate_priority_fitness


def generate_random_population(cities: List[Tuple[float, float]], population_size: int) -> List[List[Tuple[float, float]]]:
    """Cria rotas aleatórias."""
    return [random.sample(cities, len(cities)) for _ in range(population_size)]


def evaluate_population(population: List[List[Tuple[float, float]]], problem) -> List[float]:
    """Calcula o custo de cada rota, com todas as restrições."""
    return [calculate_priority_fitness(individual, problem.depot, problem.priorities, problem.demands,
                                       problem.capacity, problem.autonomy)
            for individual in population]


def sort_population(population: List[List[Tuple[float, float]]], fitness: List[float]) -> Tuple[List, List]:
    """Ordena da melhor rota (menor custo) para a pior."""
    combined = sorted(zip(population, fitness), key=lambda item: item[1])
    sorted_population, sorted_fitness = zip(*combined)
    return sorted_population, sorted_fitness


def tournament_selection(population: List[List[Tuple[float, float]]], fitness: List[float],
                         tournament_size: int = 3) -> List[Tuple[float, float]]:
    """Sorteia alguns indivíduos e devolve o melhor deles."""
    contenders = random.sample(range(len(population)), min(tournament_size, len(population)))
    return population[min(contenders, key=lambda index: fitness[index])]


def order_crossover(parent1: List[Tuple[float, float]], parent2: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Cruzamento OX: copia um trecho do pai 1 e completa na ordem do pai 2."""
    length = len(parent1)
    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    child = parent1[start_index:end_index]
    remaining_positions = [i for i in range(length) if i < start_index or i >= end_index]
    remaining_genes = [gene for gene in parent2 if gene not in child]

    for position, gene in zip(remaining_positions, remaining_genes):
        child.insert(position, gene)
    return child


def mutate_mixed(solution: List[Tuple[float, float]], mutation_probability: float) -> List[Tuple[float, float]]:
    """[MELHORIA: CONVERGÊNCIA] Sorteia entre inverter um trecho, trocar duas entregas ou mover uma."""
    mutated_solution = list(solution)

    if len(solution) < 2 or random.random() >= mutation_probability:
        return mutated_solution

    i, j = sorted(random.sample(range(len(solution)), 2))
    operation = random.random()

    if operation < 1 / 3:
        mutated_solution[i:j + 1] = reversed(mutated_solution[i:j + 1])
    elif operation < 2 / 3:
        mutated_solution[i], mutated_solution[j] = mutated_solution[j], mutated_solution[i]
    else:
        # A entrega pode ir para frente ou para trás
        if random.random() < 0.5:
            i, j = j, i
        mutated_solution.insert(j, mutated_solution.pop(i))
    return mutated_solution


def remove_duplicates(population: List[List[Tuple[float, float]]],
                      cities: List[Tuple[float, float]]) -> List[List[Tuple[float, float]]]:
    """[MELHORIA: CONVERGÊNCIA] Troca rotas repetidas por rotas aleatórias, mantendo a primeira de cada."""
    seen_routes = set()
    unique_population = []

    for individual in population:
        route_key = tuple(individual)
        if route_key in seen_routes:
            unique_population.append(random.sample(cities, len(cities)))
        else:
            seen_routes.add(route_key)
            unique_population.append(individual)
    return unique_population


def restart_population(population: List[List[Tuple[float, float]]], problem, population_size: int) -> Tuple[List, List]:
    """[MELHORIA: CONVERGÊNCIA] Mantém só a melhor rota e troca o resto por rotas aleatórias."""
    new_population = [population[0]] + generate_random_population(problem.cities, population_size - 1)
    return sort_population(new_population, evaluate_population(new_population, problem))


def create_next_generation(population: List[List[Tuple[float, float]]], fitness: List[float], population_size: int,
                           mutation_probability: float) -> List[List[Tuple[float, float]]]:
    """Mantém a melhor rota (elitismo) e cria as outras por seleção, cruzamento e mutação."""
    new_population = [population[0]]

    while len(new_population) < population_size:
        parent1 = tournament_selection(population, fitness)
        parent2 = tournament_selection(population, fitness)
        child = order_crossover(parent1, parent2)
        new_population.append(mutate_mixed(child, mutation_probability))
    return new_population


@dataclass
class ProgressTracker:
    """Conta as gerações sem melhora, para decidir quando reiniciar e quando parar."""
    best_fitness: float = float("inf")
    since_restart: int = 0   # [MELHORIA: CONVERGÊNCIA] zera na melhora e no reinício
    since_best: int = 0      # [MELHORIA: PARADA AUTOMÁTICA] zera só na melhora
    restarts: int = 0

    def update(self, fitness: float) -> None:
        """Atualiza os contadores com o melhor custo da geração."""
        if fitness < self.best_fitness - 1e-9:
            self.best_fitness = fitness
            self.since_restart = 0
            self.since_best = 0
        else:
            self.since_restart += 1
            self.since_best += 1

    def should_stop(self, limit: int) -> bool:
        return self.since_best >= limit

    def should_restart(self, limit: int) -> bool:
        return self.since_restart >= limit

    def register_restart(self) -> None:
        self.since_restart = 0
        self.restarts += 1
