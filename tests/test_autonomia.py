# -*- coding: utf-8 -*-
"""[RESTRIÇÃO: AUTONOMIA] Testes da restrição de autonomia."""
import random
import unittest

from algoritmo.rota import calculate_route_metrics, split_into_trips
from restricoes.autonomia import calculate_trip_distance, calculate_usable_autonomy, fits_autonomy, validate_reach
from restricoes.prioridade import REGULAR

DEPOT = (0, 0)
A, B, C = (30, 0), (60, 0), (30, 40)
# A e E ficam em direções diferentes: a viagem com os dois é 30 + 50 + 40 = 120
E = (0, 40)


class UsableAutonomyTest(unittest.TestCase):

    def test_desconta_a_reserva(self):
        self.assertAlmostEqual(calculate_usable_autonomy(1000, 0.1), 900)

    def test_sem_reserva_usa_tudo(self):
        self.assertEqual(calculate_usable_autonomy(1000, 0), 1000)


class ValidateReachTest(unittest.TestCase):

    def test_aceita_ida_e_volta_igual_a_autonomia(self):
        validate_reach(A, DEPOT, 60)

    def test_recusa_ida_e_volta_acima_da_autonomia(self):
        with self.assertRaises(ValueError):
            validate_reach(A, DEPOT, 59)


class FitsAutonomyTest(unittest.TestCase):

    def test_cabe_abaixo_do_limite(self):
        self.assertTrue(fits_autonomy(0, DEPOT, A, DEPOT, 100))

    def test_cabe_exatamente_no_limite(self):
        # Já rodou 30 até A, mais 30 até B, mais 60 de volta = 120
        self.assertTrue(fits_autonomy(30, A, B, DEPOT, 120))

    def test_nao_cabe_acima_do_limite(self):
        self.assertFalse(fits_autonomy(30, A, B, DEPOT, 119))

    def test_conta_a_volta_a_central(self):
        # Só a ida daria 60; com a volta são 120
        self.assertFalse(fits_autonomy(0, DEPOT, B, DEPOT, 100))

    def test_conta_o_que_ja_foi_rodado(self):
        self.assertTrue(fits_autonomy(0, A, B, DEPOT, 100))
        self.assertFalse(fits_autonomy(50, A, B, DEPOT, 100))


class TripDistanceTest(unittest.TestCase):

    def test_soma_ida_entregas_e_volta(self):
        # Triângulo: 30 até A, 40 de A até C, 50 de C até a central
        self.assertEqual(calculate_trip_distance([A, C], DEPOT), 120)

    def test_viagem_vazia_tem_distancia_zero(self):
        self.assertEqual(calculate_trip_distance([], DEPOT), 0)


class SplitByAutonomyTest(unittest.TestCase):

    def test_tudo_cabe_em_uma_viagem(self):
        self.assertEqual(split_into_trips([A, E], depot=DEPOT, autonomy=200, reserve=0), [[A, E]])

    def test_volta_antes_de_passar_da_autonomia(self):
        self.assertEqual(split_into_trips([A, E], depot=DEPOT, autonomy=119, reserve=0), [[A], [E]])

    def test_viagem_pode_usar_exatamente_a_autonomia(self):
        self.assertEqual(split_into_trips([A, E], depot=DEPOT, autonomy=120, reserve=0), [[A, E]])

    def test_reserva_reduz_a_distancia_permitida(self):
        self.assertEqual(split_into_trips([A, E], depot=DEPOT, autonomy=125, reserve=0), [[A, E]])
        self.assertEqual(split_into_trips([A, E], depot=DEPOT, autonomy=125, reserve=0.1), [[A], [E]])

    def test_distancia_zera_na_nova_viagem(self):
        far = [(60, 0), (0, 60), (-60, 0), (0, -60)]
        self.assertEqual(split_into_trips(far, depot=DEPOT, autonomy=120, reserve=0), [[city] for city in far])

    def test_nova_viagem_nao_herda_a_distancia_da_anterior(self):
        # A segunda viagem tem 30 + 10 + 40 = 80. Somando os 80 já rodados na primeira, não caberia
        near, near_too = (0, -30), (0, -40)
        trips = split_into_trips([A, E, near, near_too], depot=DEPOT, autonomy=120, reserve=0)
        self.assertEqual(trips, [[A, E], [near, near_too]])

    def test_erro_quando_a_entrega_esta_longe_demais(self):
        with self.assertRaises(ValueError):
            split_into_trips([A, B], depot=DEPOT, autonomy=100, reserve=0)

    def test_sem_central_nao_aplica_autonomia(self):
        self.assertEqual(split_into_trips([A, B], autonomy=1), [[A, B]])

    def test_autonomia_e_carga_valem_juntas(self):
        demands = {A: 60, B: 60, C: 10}
        # A carga separa A de B; a autonomia separa B de C
        trips = split_into_trips([A, B, C], demands, 100, DEPOT, 150, reserve=0)
        self.assertEqual(trips, [[A], [B], [C]])

    def test_rotas_aleatorias_respeitam_a_autonomia_e_a_ordem(self):
        cities = [(x, 100 - x) for x in range(1, 31)]
        for seed in range(30):
            random.seed(seed)
            route = random.sample(cities, len(cities))
            trips = split_into_trips(route, depot=DEPOT, autonomy=500, reserve=0.1)
            for trip in trips:
                self.assertLessEqual(calculate_trip_distance(trip, DEPOT), 450 + 1e-9)
            # Nenhuma entrega é perdida, repetida ou trocada de lugar
            self.assertEqual([city for trip in trips for city in trip], route)


class AutonomyInDistanceTest(unittest.TestCase):

    def test_volta_para_reabastecer_soma_na_distancia(self):
        priorities = {A: REGULAR, E: REGULAR}
        # O reabastecimento usa a reserva padrão: 200 x 0,9 = 180 e 125 x 0,9 = 112,5
        one_trip, _ = calculate_route_metrics([A, E], DEPOT, priorities, autonomy=200)
        two_trips, _ = calculate_route_metrics([A, E], DEPOT, priorities, autonomy=125)
        self.assertEqual(one_trip, 120)
        self.assertEqual(two_trips, 60 + 80)


if __name__ == "__main__":
    unittest.main()
