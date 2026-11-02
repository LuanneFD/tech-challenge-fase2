# -*- coding: utf-8 -*-
"""[RESTRIÇÃO: CARGA] Testes da restrição de carga."""
import random
import unittest

from algoritmo.rota import calculate_priority_fitness, calculate_route_distance, calculate_route_metrics, split_into_trips
from config import LATE_CRITICAL_PENALTY, LOW_OCCUPANCY_PENALTY, MIN_TRIP_OCCUPANCY
from restricoes.carga import (calculate_occupancy_penalty, calculate_trip_load, calculate_trip_occupancy_penalty,
                              fits_load, generate_demands, validate_demand)
from restricoes.prioridade import REGULAR

DEPOT = (0, 0)
A, B, C, D = (10, 0), (20, 0), (30, 0), (40, 0)


class GenerateDemandsTest(unittest.TestCase):

    def test_todos_os_pontos_recebem_peso(self):
        self.assertEqual(set(generate_demands([A, B, C])), {A, B, C})

    def test_peso_fica_dentro_da_faixa(self):
        cities = [(x, 0) for x in range(500)]
        demands = generate_demands(cities, min_demand=5, max_demand=30)
        self.assertGreaterEqual(min(demands.values()), 5)
        self.assertLessEqual(max(demands.values()), 30)


class ValidateDemandTest(unittest.TestCase):

    def test_aceita_entrega_igual_a_capacidade(self):
        validate_demand(A, 100, 100)

    def test_recusa_entrega_maior_que_a_capacidade(self):
        with self.assertRaises(ValueError):
            validate_demand(A, 101, 100)

    def test_sem_capacidade_aceita_qualquer_peso(self):
        validate_demand(A, 10 ** 6, None)


class FitsLoadTest(unittest.TestCase):

    def test_cabe_abaixo_da_capacidade(self):
        self.assertTrue(fits_load(40, 50, 100))

    def test_cabe_exatamente_na_capacidade(self):
        self.assertTrue(fits_load(50, 50, 100))

    def test_nao_cabe_acima_da_capacidade(self):
        self.assertFalse(fits_load(50, 51, 100))

    def test_sem_capacidade_sempre_cabe(self):
        self.assertTrue(fits_load(10 ** 6, 10 ** 6, None))


class TripLoadTest(unittest.TestCase):

    def test_soma_o_peso_da_viagem(self):
        self.assertEqual(calculate_trip_load([A, C], {A: 10, B: 99, C: 25}), 35)

    def test_viagem_vazia_nao_tem_peso(self):
        self.assertEqual(calculate_trip_load([], {A: 10}), 0)


class TripOccupancyPenaltyTest(unittest.TestCase):

    def test_sem_penalidade_acima_do_minimo(self):
        self.assertEqual(calculate_trip_occupancy_penalty(80, 100, 0.6, 40), 0)

    def test_sem_penalidade_exatamente_no_minimo(self):
        self.assertEqual(calculate_trip_occupancy_penalty(60, 100, 0.6, 40), 0)

    def test_cobra_por_ponto_percentual_abaixo_do_minimo(self):
        # 45% de ocupação são 15 pontos abaixo de 60%
        self.assertAlmostEqual(calculate_trip_occupancy_penalty(45, 100, 0.6, 40), 600)

    def test_usa_a_porcentagem_e_nao_os_kg(self):
        # 100 kg em um veículo de 200 kg são 50%, 10 pontos abaixo de 60%
        self.assertAlmostEqual(calculate_trip_occupancy_penalty(100, 200, 0.6, 40), 400)

    def test_quanto_menos_carga_maior_a_penalidade(self):
        self.assertGreater(calculate_trip_occupancy_penalty(20, 100), calculate_trip_occupancy_penalty(40, 100))


class OccupancyPenaltyTest(unittest.TestCase):

    def test_soma_a_penalidade_de_cada_viagem(self):
        # Viagens com 50% e 40%: 10 e 20 pontos abaixo de 60%. A de 90% não paga
        demands = {A: 50, B: 40, C: 90}
        self.assertAlmostEqual(calculate_occupancy_penalty([[A], [B], [C]], demands, 100, 0.6, 40), 400 + 800)

    def test_soma_a_carga_da_viagem_inteira(self):
        demands = {A: 30, B: 30}
        self.assertEqual(calculate_occupancy_penalty([[A, B]], demands, 100, 0.6, 40), 0)

    def test_sem_pesos_nao_ha_penalidade(self):
        self.assertEqual(calculate_occupancy_penalty([[A]], None, 100), 0)

    def test_sem_capacidade_nao_ha_penalidade(self):
        self.assertEqual(calculate_occupancy_penalty([[A]], {A: 10}, None), 0)

    def test_valores_do_projeto_nao_superam_uma_critica_fora_do_limite(self):
        # Mesmo a viagem mais vazia custa menos que atrasar uma crítica
        self.assertLess(MIN_TRIP_OCCUPANCY * 100 * LOW_OCCUPANCY_PENALTY, LATE_CRITICAL_PENALTY)


class OccupancyInFitnessTest(unittest.TestCase):

    def test_custo_soma_a_penalidade_de_ocupacao(self):
        priorities = {A: REGULAR}
        demands = {A: 10}
        fitness = calculate_priority_fitness([A], DEPOT, priorities, demands, 100)
        expected = calculate_route_distance([[A]], DEPOT) + calculate_occupancy_penalty([[A]], demands, 100)
        self.assertAlmostEqual(fitness, expected)
        self.assertGreater(fitness, calculate_route_distance([[A]], DEPOT))

    def test_rota_mais_cheia_custa_menos_que_viagem_quase_vazia(self):
        # Mesmas entregas: juntar a viagem leve com outra evita a penalidade dela
        priorities = {A: REGULAR, B: REGULAR, C: REGULAR}
        demands = {A: 50, B: 45, C: 55}
        cheia = calculate_priority_fitness([A, B, C], DEPOT, priorities, demands, 100)
        vazia = calculate_priority_fitness([A, C, B], DEPOT, priorities, demands, 100)
        self.assertLess(cheia, vazia)


class SplitByLoadTest(unittest.TestCase):

    def test_tudo_cabe_em_uma_viagem(self):
        demands = {A: 30, B: 30, C: 40}
        self.assertEqual(split_into_trips([A, B, C], demands, 100), [[A, B, C]])

    def test_abre_viagem_quando_a_proxima_nao_cabe(self):
        demands = {A: 60, B: 60, C: 30}
        self.assertEqual(split_into_trips([A, B, C], demands, 100), [[A], [B, C]])

    def test_carga_zera_na_nova_viagem(self):
        demands = {A: 100, B: 100, C: 100}
        self.assertEqual(split_into_trips([A, B, C], demands, 100), [[A], [B], [C]])

    def test_erro_quando_a_entrega_nao_cabe_no_veiculo(self):
        with self.assertRaises(ValueError):
            split_into_trips([A, B], {A: 10, B: 101}, 100)

    def test_rota_vazia_nao_tem_viagens(self):
        self.assertEqual(split_into_trips([], {}, 100), [])

    def test_rotas_aleatorias_respeitam_a_capacidade_e_a_ordem(self):
        cities = [(x, x) for x in range(1, 31)]
        for seed in range(30):
            random.seed(seed)
            route = random.sample(cities, len(cities))
            demands = generate_demands(cities)
            trips = split_into_trips(route, demands, 100)
            for trip in trips:
                self.assertLessEqual(calculate_trip_load(trip, demands), 100)
            # Nenhuma entrega é perdida, repetida ou trocada de lugar
            self.assertEqual([city for trip in trips for city in trip], route)


class LoadInDistanceTest(unittest.TestCase):

    def test_volta_para_recarregar_soma_na_distancia(self):
        priorities = {A: REGULAR, B: REGULAR}
        one_trip, _ = calculate_route_metrics([A, B], DEPOT, priorities, {A: 40, B: 40}, 100)
        two_trips, _ = calculate_route_metrics([A, B], DEPOT, priorities, {A: 60, B: 60}, 100)
        self.assertEqual(one_trip, 40)
        self.assertEqual(two_trips, 60)


if __name__ == "__main__":
    unittest.main()
