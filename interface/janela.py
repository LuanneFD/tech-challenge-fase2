# -*- coding: utf-8 -*-
"""Janela do programa: eventos, desenho de cada geração, legenda e tela final."""
from typing import Dict, List, Tuple

import pygame

from algoritmo.rota import split_into_trips
from config import (AUTONOMY_RESERVE, BLACK, CRITICAL_TRIP_LIMIT, DEPOT_SIZE, FPS, GRAY, GREEN, HEIGHT, NODE_RADIUS,
                    ORDER_FONT_SIZE, PLOT_FIGSIZE, RED, TRIP_COLORS, WHITE, WIDTH)
from interface.desenho import draw_cities, draw_delivery_order, draw_depot, draw_paths, draw_plot, draw_text
from restricoes.autonomia import calculate_usable_autonomy
from restricoes.prioridade import CRITICAL, split_by_priority


def create_window() -> Tuple[pygame.Surface, pygame.time.Clock]:
    """Abre a janela."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TSP Solver using Pygame")
    return screen, pygame.time.Clock()


def handle_window_events() -> bool:
    """Retorna False se a janela foi fechada ou se apertaram "q"."""
    keep_open = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
            keep_open = False
    return keep_open


def update_window(clock: pygame.time.Clock) -> None:
    """Mostra o quadro desenhado e limita a velocidade."""
    pygame.display.flip()
    clock.tick(FPS)


def draw_generation(screen: pygame.Surface, problem, best_route: List, second_route: List, summary,
                    fitness_history: List[float]) -> None:
    """Desenha o gráfico, as rotas, os pontos e a legenda da geração."""
    screen.fill(WHITE)

    # Gráfico de convergência
    draw_plot(screen, list(range(len(fitness_history))), fitness_history, x_label="Geração",
              y_label="Custo = distância + atraso nos críticos + baixa ocupação", figsize=PLOT_FIGSIZE)

    # Segunda melhor rota em cinza e melhor rota com uma cor por viagem
    second_trips = split_into_trips(second_route, problem.demands, problem.capacity, problem.depot, problem.autonomy)
    for trip in second_trips:
        draw_paths(screen, [problem.depot] + trip, GRAY, width=1)
    for trip_index, trip in enumerate(summary.trips):
        draw_paths(screen, [problem.depot] + trip, TRIP_COLORS[trip_index % len(TRIP_COLORS)], width=3)

    # Pontos de entrega, central e ordem de entrega
    critical_cities, regular_cities = split_by_priority(problem.cities, problem.priorities)
    draw_cities(screen, critical_cities, RED, NODE_RADIUS)
    draw_cities(screen, regular_cities, GREEN, NODE_RADIUS)
    draw_depot(screen, problem.depot, BLACK, DEPOT_SIZE)
    draw_delivery_order(screen, best_route, WHITE, ORDER_FONT_SIZE)

    # Legenda
    usable_autonomy = calculate_usable_autonomy(problem.autonomy)
    draw_text(screen, f"Distância percorrida: {summary.distance:.0f}   Atraso nos críticos: {summary.penalty:.0f}   "
                      f"Baixa ocupação: {summary.occupancy_penalty:.0f}",
              BLACK, problem.cities, HEIGHT - 36)
    draw_text(screen, f"Viagens (saídas do depósito): {len(summary.trips)}", BLACK, problem.cities, HEIGHT - 18)
    draw_text(screen, f"Viagem mais longa: {max(summary.trip_distances):.0f} de {usable_autonomy:.0f} de autonomia "
                      f"({problem.autonomy} menos {AUTONOMY_RESERVE:.0%} de reserva)",
              BLACK, problem.cities, HEIGHT)


def format_generation_log(generation: int, best_fitness: float, best_route: List, summary, problem) -> str:
    """Texto do terminal para uma geração."""
    usable_autonomy = calculate_usable_autonomy(problem.autonomy)
    order = " > ".join("C" if problem.priorities[city] == CRITICAL else "R" for city in best_route)
    return (f"Generation {generation}: Custo = {round(best_fitness, 2)} "
            f"(distância percorrida = {round(summary.distance, 2)}, atraso nos críticos = {round(summary.penalty, 2)}, "
            f"baixa ocupação = {round(summary.occupancy_penalty, 2)}, "
            f"viagens = {len(summary.trips)}, cargas = {summary.trip_loads} kg, "
            f"distância de cada viagem = {[round(d) for d in summary.trip_distances]} de {usable_autonomy:.0f} de autonomia, "
            f"ordem: {order})")


def format_stop_message(found_at: int, report_status: str) -> str:
    """[MELHORIA: PARADA AUTOMÁTICA] Texto da tela final: geração da melhor rota e situação dos relatórios."""
    message = f"Melhor rota encontrada: geração {found_at}"
    return f"{message} | {report_status}" if report_status else message


def late_criticals_warning(late_criticals: int) -> str:
    """[RESTRIÇÃO: PRIORIDADE] Texto do aviso de críticas depois da viagem limite."""
    return (f"Atenção: {late_criticals} entrega(s) crítica(s) depois da viagem {CRITICAL_TRIP_LIMIT} "
            f"(não couberam nas primeiras viagens)")


def wait_until_closed(screen: pygame.Surface, clock: pygame.time.Clock, final_frame: pygame.Surface,
                      problem, found_at: int, report_status: Dict) -> None:
    """Mantém o resultado na tela, com a situação dos relatórios, até fecharem a janela."""
    while handle_window_events():
        screen.blit(final_frame, (0, 0))
        draw_text(screen, format_stop_message(found_at, report_status["text"]), BLACK, problem.cities, 2 * 15)
        update_window(clock)
