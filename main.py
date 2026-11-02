import pygame

from algoritmo.genetico import (ProgressTracker, create_next_generation, evaluate_population,
                                generate_random_population, remove_duplicates, restart_population, sort_population)
from algoritmo.problema import create_problem
from algoritmo.rota import summarize_route
from config import (AUTONOMY_RESERVE, LLM_REPORTS_ENABLED, MAX_GENERATIONS_WITHOUT_IMPROVEMENT, MUTATION_PROBABILITY,
                    POPULATION_SIZE, STAGNATION_LIMIT)
from interface.janela import (create_window, draw_generation, format_generation_log, handle_window_events, late_criticals_warning, update_window, wait_until_closed)
from relatorios_llm import build_route_summary, start_reports
from restricoes.prioridade import count_late_criticals


def main() -> None:
    # Passo 1: monta o problema (pontos, central, prioridades e pesos)
    problem = create_problem()

    # Passo 2: abre a janela
    screen, clock = create_window()

    # Passo 3: cria a população inicial
    population = generate_random_population(problem.cities, POPULATION_SIZE)
    progress = ProgressTracker()
    fitness_history = []
    generation = 0
    stopped = False
    report_thread = None
    report_status = {"text": ""}

    while handle_window_events():
        generation += 1

        # Passo 4: troca rotas repetidas por rotas novas
        population = remove_duplicates(population, problem.cities)

        # Passo 5: calcula o custo de cada rota, aplicando as restrições
        fitness = evaluate_population(population, problem)

        # Passo 6: ordena da melhor rota para a pior
        population, fitness = sort_population(population, fitness)

        # Passo 7: registra a melhor rota da geração
        best_route, best_fitness = population[0], fitness[0]
        fitness_history.append(best_fitness)
        progress.update(best_fitness)

        # Passo 8: mostra o resultado na tela e no terminal
        summary = summarize_route(best_route, problem)
        draw_generation(screen, problem, best_route, population[1], summary, fitness_history)
        print(format_generation_log(generation, best_fitness, best_route, summary, problem))

        # Passo 9: para se ficou muitas gerações sem achar rota melhor
        if progress.should_stop(MAX_GENERATIONS_WITHOUT_IMPROVEMENT):
            found_at = generation - progress.since_best
            print(f"Generation {generation}: {MAX_GENERATIONS_WITHOUT_IMPROVEMENT} gerações sem encontrar uma rota "
                  f"melhor, execução encerrada. Melhor rota encontrada na geração {found_at}: custo = {round(best_fitness, 2)}")

            # Passo 10: avisa no terminal se alguma entrega crítica ficou fora do limite de viagens
            late_criticals = count_late_criticals(summary.trips, problem.priorities)
            if late_criticals:
                print(late_criticals_warning(late_criticals))

            # Passo 11: gera os relatórios com a LLM, sem travar a janela
            if LLM_REPORTS_ENABLED:
                route_data = build_route_summary(
                    best_route, problem.depot, problem.priorities, problem.demands, problem.capacity,
                    problem.autonomy, AUTONOMY_RESERVE, problem.cities,
                    algorithm_info={
                        "geracoes_executadas": generation,
                        "geracao_em_que_a_melhor_rota_foi_encontrada": found_at,
                        "reinicios_da_populacao": progress.restarts,
                        "tamanho_da_populacao": POPULATION_SIZE,
                        "probabilidade_de_mutacao": MUTATION_PROBABILITY,
                        "criterio_de_parada": f"{MAX_GENERATIONS_WITHOUT_IMPROVEMENT} gerações seguidas sem rota melhor",
                    })
                report_thread = start_reports(route_data, report_status)

            stopped = True
            break

        # Passo 12: reinicia a população se ela estagnou
        if progress.should_restart(STAGNATION_LIMIT):
            print(f"Generation {generation}: {STAGNATION_LIMIT} gerações sem melhora, reiniciando a população")
            population, fitness = restart_population(population, problem, POPULATION_SIZE)
            progress.register_restart()

        # Passo 13: cria a próxima geração (elitismo, seleção, cruzamento e mutação)
        population = create_next_generation(population, fitness, POPULATION_SIZE, MUTATION_PROBABILITY)

        # Passo 14: atualiza a tela
        update_window(clock)

    # Passo 15: mantém o resultado na tela até fecharem a janela
    if stopped:
        wait_until_closed(screen, clock, screen.copy(), problem, found_at, report_status)
    pygame.quit()

    # Passo 16: espera os relatórios terminarem antes de encerrar
    if report_thread is not None and report_thread.is_alive():
        print("Aguardando a LLM terminar os relatórios...")
        report_thread.join()


if __name__ == "__main__":
    main()
