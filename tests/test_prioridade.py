# -*- coding: utf-8 -*-
"""[RESTRIÇÃO: PRIORIDADE] Testes da restrição de prioridade."""
import random
import unittest

from algoritmo.distancia import calculate_distance
from algoritmo.rota import calculate_priority_fitness, split_into_trips
from restricoes.prioridade import (CRITICAL, PRIORITY_WEIGHTS, REGULAR, calculate_delivery_penalty,
                                   calculate_priority_penalty, choose_spread_criticals, count_late_criticals,
                                   generate_priorities, split_by_priority, split_into_distance_bands)

DEPOT = (0, 0)
# Pontos em linha, para as contas darem valores exatos
A, B, C, D = (10, 0), (20, 0), (30, 0), (40, 0)
CITIES = [(x, 0) for x in range(10, 110, 10)]


class GeneratePrioritiesTest(unittest.TestCase):

    def test_quantidade_de_criticas_segue_a_proporcao(self):
        priorities = generate_priorities(CITIES, 0.3)
        self.assertEqual(list(priorities.values()).count(CRITICAL), 3)

    def test_todos_os_pontos_recebem_prioridade(self):
        priorities = generate_priorities(CITIES, 0.3, DEPOT)
        self.assertEqual(set(priorities), set(CITIES))
        self.assertEqual(set(priorities.values()), {CRITICAL, REGULAR})

    def test_proporcao_zero_nao_gera_critica(self):
        priorities = generate_priorities(CITIES, 0, DEPOT)
        self.assertNotIn(CRITICAL, priorities.values())

    def test_proporcao_um_torna_todas_criticas(self):
        priorities = generate_priorities(CITIES, 1, DEPOT)
        self.assertEqual(set(priorities.values()), {CRITICAL})

    def test_com_central_cada_faixa_de_distancia_tem_uma_critica(self):
        for seed in range(20):
            random.seed(seed)
            priorities = generate_priorities(CITIES, 0.3, DEPOT)
            for band in split_into_distance_bands(CITIES, DEPOT, 3):
                self.assertEqual(sum(priorities[city] == CRITICAL for city in band), 1)


class SplitIntoDistanceBandsTest(unittest.TestCase):

    def test_divide_do_mais_perto_ao_mais_longe(self):
        bands = split_into_distance_bands([D, A, C, B], DEPOT, 2)
        self.assertEqual(bands, [[A, B], [C, D]])

    def test_sobra_fica_nas_primeiras_faixas(self):
        bands = split_into_distance_bands(CITIES, DEPOT, 3)
        self.assertEqual([len(band) for band in bands], [4, 3, 3])

    def test_nao_perde_nem_repete_pontos(self):
        bands = split_into_distance_bands(CITIES, DEPOT, 3)
        self.assertEqual(sorted(city for band in bands for city in band), sorted(CITIES))


class ChooseSpreadCriticalsTest(unittest.TestCase):

    def test_escolhe_o_ponto_mais_afastado_na_faixa_seguinte(self):
        # Faixas: [A, B] e [C, D]. D é o mais longe de qualquer ponto da primeira faixa
        for seed in range(20):
            random.seed(seed)
            chosen = choose_spread_criticals([A, B, C, D], DEPOT, 2)
            self.assertIn(chosen[0], (A, B))
            self.assertEqual(chosen[1], D)

    def test_quantidade_escolhida(self):
        self.assertEqual(len(set(choose_spread_criticals(CITIES, DEPOT, 4))), 4)


class SplitByPriorityTest(unittest.TestCase):

    def test_separa_criticas_e_comuns(self):
        priorities = {A: CRITICAL, B: REGULAR, C: CRITICAL}
        self.assertEqual(split_by_priority([A, B, C], priorities), ([A, C], [B]))


class DeliveryPenaltyTest(unittest.TestCase):

    def test_comum_nao_tem_penalidade(self):
        self.assertEqual(calculate_delivery_penalty(REGULAR, 100, 0), 0)

    def test_comum_nao_sofre_limite_de_viagens(self):
        self.assertEqual(calculate_delivery_penalty(REGULAR, 100, 9, trip_limit=2, late_penalty=5000), 0)

    def test_critica_paga_pelo_peso_vezes_distancia(self):
        expected = PRIORITY_WEIGHTS[CRITICAL] * 100
        self.assertEqual(calculate_delivery_penalty(CRITICAL, 100, 0, trip_limit=2, late_penalty=5000), expected)

    def test_critica_na_ultima_viagem_permitida_nao_paga_atraso(self):
        expected = PRIORITY_WEIGHTS[CRITICAL] * 100
        self.assertEqual(calculate_delivery_penalty(CRITICAL, 100, 1, trip_limit=2, late_penalty=5000), expected)

    def test_critica_depois_do_limite_paga_atraso(self):
        expected = PRIORITY_WEIGHTS[CRITICAL] * 100 + 5000
        self.assertEqual(calculate_delivery_penalty(CRITICAL, 100, 2, trip_limit=2, late_penalty=5000), expected)


class PriorityPenaltyTest(unittest.TestCase):

    def test_soma_a_distancia_acumulada_de_cada_critica(self):
        priorities = {A: CRITICAL, B: REGULAR, C: CRITICAL}
        # Distância acumulada: A = 10 e C = 30
        expected = PRIORITY_WEIGHTS[CRITICAL] * (10 + 30)
        self.assertEqual(calculate_priority_penalty([[A, B, C]], DEPOT, priorities), expected)

    def test_distancia_nao_zera_entre_viagens(self):
        priorities = {A: REGULAR, B: CRITICAL}
        # Viagem 1: 10 de ida e 10 de volta. Viagem 2: 20 até B. Acumulado = 40
        expected = PRIORITY_WEIGHTS[CRITICAL] * 40
        self.assertEqual(calculate_priority_penalty([[A], [B]], DEPOT, priorities), expected)

    def test_sem_criticas_nao_ha_penalidade(self):
        priorities = {A: REGULAR, B: REGULAR}
        self.assertEqual(calculate_priority_penalty([[A, B]], DEPOT, priorities), 0)

    def test_soma_o_atraso_das_criticas_depois_do_limite(self):
        priorities = {A: REGULAR, B: REGULAR, C: CRITICAL}
        trips = [[A], [B], [C]]
        # Acumulado até C: (10 + 10) + (20 + 20) + 30 = 90
        expected = PRIORITY_WEIGHTS[CRITICAL] * 90 + 5000
        self.assertEqual(calculate_priority_penalty(trips, DEPOT, priorities, trip_limit=2, late_penalty=5000), expected)


class CountLateCriticalsTest(unittest.TestCase):

    def test_nao_conta_criticas_dentro_do_limite(self):
        priorities = {A: CRITICAL, B: CRITICAL, C: REGULAR}
        self.assertEqual(count_late_criticals([[A], [B], [C]], priorities, trip_limit=2), 0)

    def test_conta_criticas_depois_do_limite(self):
        priorities = {A: REGULAR, B: REGULAR, C: CRITICAL, D: CRITICAL}
        self.assertEqual(count_late_criticals([[A], [B], [C], [D]], priorities, trip_limit=2), 2)

    def test_comuns_depois_do_limite_nao_contam(self):
        priorities = {A: CRITICAL, B: CRITICAL, C: REGULAR}
        self.assertEqual(count_late_criticals([[A, B], [], [C]], priorities, trip_limit=2), 0)


class PriorityInFitnessTest(unittest.TestCase):

    def test_rota_com_critica_antes_tem_custo_menor(self):
        # Pontos em lados opostos da central: as duas rotas têm a mesma distância,
        # e só a prioridade muda o custo
        other_side = (-40, 0)
        priorities = {A: REGULAR, other_side: CRITICAL}
        first = calculate_priority_fitness([other_side, A], DEPOT, priorities)
        last = calculate_priority_fitness([A, other_side], DEPOT, priorities)
        self.assertLess(first, last)

    def test_custo_e_distancia_mais_penalidade(self):
        priorities = {A: CRITICAL}
        expected = 2 * calculate_distance(DEPOT, A) + PRIORITY_WEIGHTS[CRITICAL] * 10
        self.assertEqual(calculate_priority_fitness([A], DEPOT, priorities), expected)

    def test_custo_prefere_critica_dentro_do_limite_de_viagens(self):
        # Cada entrega pesa 60 kg, então cada viagem leva só uma
        demands = {A: 60, B: 60, C: 60}
        priorities = {A: REGULAR, B: REGULAR, C: CRITICAL}
        self.assertEqual(len(split_into_trips([A, B, C], demands, 100)), 3)
        inside = calculate_priority_fitness([C, A, B], DEPOT, priorities, demands, 100)
        outside = calculate_priority_fitness([A, B, C], DEPOT, priorities, demands, 100)
        self.assertLess(inside + 4000, outside)


if __name__ == "__main__":
    unittest.main()
