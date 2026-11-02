# -*- coding: utf-8 -*-
"""Funções básicas de desenho no pygame."""
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pygame
from matplotlib.backends.backend_agg import FigureCanvasAgg


def draw_plot(screen: pygame.Surface, x: list, y: list, x_label: str = "Geração", y_label: str = "Custo",
              figsize: Tuple[float, float] = (4, 4)) -> None:
    """Desenha o gráfico de convergência."""
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    ax.plot(x, y)
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    size = canvas.get_width_height()
    surf = pygame.image.frombuffer(canvas.buffer_rgba(), size, "RGBA")
    screen.blit(surf, (0, 0))
    plt.close(fig)


def draw_cities(screen: pygame.Surface, cities: List[Tuple[int, int]], rgb_color: Tuple[int, int, int],
                node_radius: int) -> None:
    """Desenha os pontos de entrega."""
    for city in cities:
        pygame.draw.circle(screen, rgb_color, city, node_radius)


def draw_delivery_order(screen: pygame.Surface, route: List[Tuple[int, int]], rgb_color: Tuple[int, int, int],
                        font_size: int) -> None:
    """[MELHORIA: VISUALIZAÇÃO] Escreve em cada ponto o número da sua ordem de entrega."""
    pygame.font.init()
    font = pygame.font.SysFont("Arial", font_size, bold=True)

    for order, city in enumerate(route, start=1):
        text_surface = font.render(str(order), True, rgb_color)
        screen.blit(text_surface, text_surface.get_rect(center=city))


def draw_depot(screen: pygame.Surface, depot: Tuple[int, int], rgb_color: Tuple[int, int, int], size: int) -> None:
    """Desenha a central como um quadrado."""
    rect = pygame.Rect(0, 0, size, size)
    rect.center = depot
    pygame.draw.rect(screen, rgb_color, rect)


def draw_paths(screen: pygame.Surface, path: List[Tuple[int, int]], rgb_color: Tuple[int, int, int],
               width: int = 1) -> None:
    """Desenha um caminho fechado."""
    pygame.draw.lines(screen, rgb_color, True, path, width=width)


def draw_text(screen: pygame.Surface, text: str, color: Tuple[int, int, int], cities: List[Tuple[int, int]],
              height: int) -> None:
    """[MELHORIA: LEGENDA] Escreve um texto centralizado no mapa, sobre um fundo translúcido."""
    pygame.font.init()
    font_size = 15
    font = pygame.font.SysFont("Arial", font_size)
    text_surface = font.render(text, False, color)

    # Centraliza nos pontos sem deixar o texto sair da tela
    center_x = np.average(np.array(cities)[:, 0])
    text_x = min(max(center_x - text_surface.get_width() / 2, 0), screen.get_width() - text_surface.get_width())
    text_y = height - 1.5 * font_size

    background = pygame.Surface((text_surface.get_width() + 6, text_surface.get_height()), pygame.SRCALPHA)
    background.fill((255, 255, 255, 210))
    screen.blit(background, (text_x - 3, text_y))
    screen.blit(text_surface, (text_x, text_y))
