# -*- coding: utf-8 -*-
"""Todos os parâmetros do projeto, em um só lugar."""

# --- Janela e desenho ---
# [MELHORIA: VISUALIZAÇÃO] Tamanho da janela e área do mapa (à direita do gráfico)
WIDTH, HEIGHT = 1200, 650
PLOT_X_OFFSET = 620
LEGEND_HEIGHT = 65
MAP_HEIGHT = HEIGHT - LEGEND_HEIGHT
PLOT_FIGSIZE = (6, 6.5)
NODE_RADIUS = 14
ORDER_FONT_SIZE = 15
DEPOT_SIZE = 18
FPS = 30

# Cores em RGB
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 160, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
# [RESTRIÇÃO: CARGA] Uma cor para cada viagem da melhor rota
TRIP_COLORS = [BLUE, (230, 130, 0), (150, 0, 200), (0, 170, 170)]

# --- Algoritmo genético ---
N_CITIES = 15
POPULATION_SIZE = 100
MUTATION_PROBABILITY = 0.5
# [MELHORIA: CONVERGÊNCIA] Gerações sem melhora até reiniciar a população
STAGNATION_LIMIT = 100
# [MELHORIA: PARADA AUTOMÁTICA] Gerações sem rota melhor até encerrar (não zera nos reinícios)
MAX_GENERATIONS_WITHOUT_IMPROVEMENT = 500

# --- Central de abastecimento (depósito) ---
DEPOT = ((PLOT_X_OFFSET + WIDTH) // 2, MAP_HEIGHT // 2)

# --- Restrição de prioridade ---
# [RESTRIÇÃO: PRIORIDADE] Proporção de entregas críticas
CRITICAL_RATIO = 0.3
# [RESTRIÇÃO: PRIORIDADE] Peso da distância acumulada até cada tipo de entrega
CRITICAL_WEIGHT = 0.5
REGULAR_WEIGHT = 0.0
# [RESTRIÇÃO: PRIORIDADE] Críticas devem ficar até esta viagem; cada uma depois dela soma a penalidade
CRITICAL_TRIP_LIMIT = 2
LATE_CRITICAL_PENALTY = 5000

# --- Restrição de carga ---
# [RESTRIÇÃO: CARGA] Capacidade do veículo e faixa de peso de cada entrega, em kg
VEHICLE_CAPACITY = 100
MIN_DEMAND = 5
MAX_DEMAND = 30
# [RESTRIÇÃO: CARGA] Ocupação mínima desejada por viagem; cada ponto percentual abaixo dela soma a penalidade
MIN_TRIP_OCCUPANCY = 0.6
LOW_OCCUPANCY_PENALTY = 40

# --- Restrição de autonomia ---
# [RESTRIÇÃO: AUTONOMIA] Distância máxima por tanque, nas unidades do mapa
VEHICLE_AUTONOMY = 1000
# [RESTRIÇÃO: AUTONOMIA] Fração da autonomia guardada como reserva de segurança
AUTONOMY_RESERVE = 0.1

# --- Relatórios ---
# [INTEGRAÇÃO: LLM] Gera os relatórios com a LLM quando a execução para sozinha
LLM_REPORTS_ENABLED = True
