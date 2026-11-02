"""
[INTEGRAÇÃO: LLM]
Geração de instruções e relatórios com uma LLM pré-treinada (Gemini, do
Google, no plano gratuito da API) a partir da melhor rota encontrada pelo
algoritmo genético.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from algoritmo.distancia import calculate_distance
from algoritmo.rota import calculate_route_metrics, split_into_trips
from config import CRITICAL_TRIP_LIMIT, MIN_TRIP_OCCUPANCY
from restricoes.carga import calculate_occupancy_penalty
from restricoes.prioridade import CRITICAL


# [INTEGRAÇÃO: LLM] 
# O primeiro é o principal; os outros são reservas, usados só quando o anterior falha.
LLM_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
API_KEY_VARIABLE = "GEMINI_API_KEY"
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
LLM_MAX_TOKENS = 16000

# [INTEGRAÇÃO: LLM] Tempo máximo de espera por resposta de cada modelo, em segundos
LLM_TIMEOUT_SECONDS = 120

# [INTEGRAÇÃO: LLM] Se o limite estourar (erro 429) ou o serviço estiver sobrecarregado (503), espera e tenta de
# novo no mesmo modelo. A espera cresce a cada tentativa: 45 s e depois 90 s
LLM_RETRY_ATTEMPTS = 3
LLM_RETRY_WAIT_SECONDS = 45

# [INTEGRAÇÃO: LLM] Premissas para converter o mapa em valores do mundo real. O mapa
# do sistema está em pixels; com 0,05 km por unidade, a área de entregas tem uns
# 29 km de largura (escala de uma cidade). O tempo é só uma estimativa de direção,
# sem contar paradas, e não entra no custo da rota
KM_PER_MAP_UNIT = 0.05
AVERAGE_SPEED_KMH = 80      # velocidade média

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")

# [INTEGRAÇÃO: LLM] Arquivo, na pasta de cada execução, com os problemas da geração.
# Só é criado se algo falhar, e guarda o motivo depois que o terminal é fechado
ERRORS_FILE = "erros.txt"


def to_km(map_units: float) -> float:
    """
    [INTEGRAÇÃO: LLM]
    Converte uma distância do mapa (pixels) para km, usando KM_PER_MAP_UNIT.
    """
    return map_units * KM_PER_MAP_UNIT


def drive_minutes(km: float) -> float:
    """
    [INTEGRAÇÃO: LLM]
    Tempo estimado de direção, em minutos, para percorrer `km` na velocidade média.
    """
    return km / AVERAGE_SPEED_KMH * 60


def simulate_route(route: List[Tuple[float, float]], depot: Tuple[float, float],
                   priorities: Dict, demands: Dict, capacity: int, autonomy: float,
                   reserve: float) -> Dict:
    """
    [INTEGRAÇÃO: LLM]
    Percorre a rota viagem por viagem (com as mesmas regras de carga e autonomia
    do algoritmo genético) e calcula, para cada parada, a distância do trecho,
    a prioridade e a carga entregue. O tempo é só o de direção, em minutos.

    Parâmetros:
    - route: Ordem de visita das entregas.
    - depot: Coordenada da central de abastecimento (depósito).
    - priorities, demands: Prioridade e peso (kg) de cada entrega.
    - capacity, autonomy, reserve: Capacidade (kg), autonomia e reserva do veículo.

    Retorna:
    Dict: Totais da rota e a lista de viagens com as paradas detalhadas.
    """
    trips = split_into_trips(route, demands, capacity, depot, autonomy, reserve)
    usable_autonomy = autonomy * (1 - reserve)

    elapsed_min = 0.0
    total_map_units = 0.0
    critical_arrivals = []
    delivery_order = 0
    trips_data = []

    for trip_index, trip in enumerate(trips):
        location = depot
        trip_map_units = 0.0
        stops = []
        for city in trip:
            delivery_order += 1
            leg = calculate_distance(location, city)
            trip_map_units += leg
            elapsed_min += drive_minutes(to_km(leg))
            is_critical = priorities[city] == CRITICAL
            if is_critical:
                critical_arrivals.append(elapsed_min)

            stops.append({
                "ordem": delivery_order,
                "prioridade": "crítica" if is_critical else "comum",
                "carga_kg": demands[city],
                "distancia_do_trecho_km": round(to_km(leg), 1),
            })
            location = city

        # Volta da última parada da viagem para a central
        back = calculate_distance(location, depot)
        trip_map_units += back
        elapsed_min += drive_minutes(to_km(back))
        total_map_units += trip_map_units

        load = sum(demands[city] for city in trip)
        trips_data.append({
            "viagem": trip_index + 1,
            "carga_total_kg": load,
            "uso_da_capacidade_pct": round(load / capacity * 100),
            "distancia_km": round(to_km(trip_map_units), 1),
            "uso_da_autonomia_util_pct": round(trip_map_units / usable_autonomy * 100),
            "paradas": stops,
            "retorno": {
                "distancia_km": round(to_km(back), 1),
            },
        })

    # Motivo de cada volta à central: a próxima entrega não cabia na carga
    # restante, ou não dava para ir até ela e voltar dentro da autonomia útil
    for trip_index, trip_data in enumerate(trips_data):
        if trip_index == len(trips) - 1:
            trip_data["retorno"]["motivo"] = "fim da rota"
            continue
        next_city = trips[trip_index + 1][0]
        if trip_data["carga_total_kg"] + demands[next_city] > capacity:
            trip_data["retorno"]["motivo"] = "recarregar: a próxima entrega não cabe na carga restante"
        else:
            trip_data["retorno"]["motivo"] = "reabastecer: a autonomia útil está perto do fim"

    total_km = to_km(total_map_units)
    return {
        "distancia_total_km": round(total_km, 1),
        "tempo_total_estimado_min": round(elapsed_min),
        "numero_de_viagens": len(trips),
        "minutos_ate_a_ultima_entrega_critica": round(max(critical_arrivals)) if critical_arrivals else None,
        "viagens": trips_data,
    }


def build_route_summary(best_route: List[Tuple[float, float]], depot: Tuple[float, float],
                        priorities: Dict, demands: Dict, capacity: int, autonomy: float,
                        reserve: float, cities_locations: List[Tuple[float, float]],
                        algorithm_info: Dict) -> Dict:
    """
    [INTEGRAÇÃO: LLM]
    Monta todos os dados que a LLM recebe: premissas, veículo, informações do
    algoritmo genético, a rota otimizada detalhada e a comparação com uma rota
    sem otimização (entregas feitas na ordem de cadastro dos pedidos).

    Parâmetros:
    - best_route: Melhor rota encontrada pelo algoritmo genético.
    - depot, priorities, demands, capacity, autonomy, reserve: Dados do problema.
    - cities_locations: Pontos de entrega na ordem de cadastro.
    - algorithm_info: Dados da execução do algoritmo (gerações, reinícios etc.).

    Retorna:
    Dict: Dados da rota, prontos para virar JSON e ir para a LLM.
    """
    args = (depot, priorities, demands, capacity, autonomy, reserve)
    optimized = simulate_route(best_route, *args)
    # A rota "sem otimização" segue a ordem em que os pedidos foram cadastrados,
    # com as mesmas regras de carga e autonomia
    baseline = simulate_route(list(cities_locations), *args)
    _, priority_penalty = calculate_route_metrics(best_route, depot, priorities, demands, capacity, autonomy)

    def saving(field: str) -> Optional[float]:
        if baseline[field] is None or optimized[field] is None:
            return None
        return round(baseline[field] - optimized[field], 2)

    n_critical = sum(1 for city in best_route if priorities[city] == CRITICAL)
    total_load = sum(demands.values())
    trips = optimized["viagens"]

    return {
        "data_execucao": datetime.now().strftime("%Y-%m-%d"),
        "premissas": {
            "km_por_unidade_do_mapa": KM_PER_MAP_UNIT,
            "velocidade_media_kmh": AVERAGE_SPEED_KMH,
        },
        "veiculo": {
            "capacidade_kg": capacity,
            "autonomia_km": round(to_km(autonomy), 1),
            "reserva_de_seguranca_pct": round(reserve * 100),
            "autonomia_util_por_viagem_km": round(to_km(autonomy * (1 - reserve)), 1),
        },
        "algoritmo_genetico": algorithm_info,
        "resumo": {
            "entregas": len(best_route),
            "entregas_criticas": n_critical,
            # [RESTRIÇÃO: PRIORIDADE] Limite de viagens para as críticas e quantas ficaram fora dele
            "limite_de_viagens_para_entregas_criticas": CRITICAL_TRIP_LIMIT,
            "entregas_criticas_fora_do_limite": sum(
                1 for trip in trips[CRITICAL_TRIP_LIMIT:] for stop in trip["paradas"] if stop["prioridade"] == "crítica"),
            "carga_total_kg": total_load,
            "uso_medio_da_capacidade_pct": round(sum(t["uso_da_capacidade_pct"] for t in trips) / len(trips)),
            # [RESTRIÇÃO: CARGA] Ocupação mínima desejada, a menor ocupação da rota e a penalidade aplicada
            "ocupacao_minima_desejada_pct": round(MIN_TRIP_OCCUPANCY * 100),
            "uso_minimo_da_capacidade_pct": min(t["uso_da_capacidade_pct"] for t in trips),
            "penalidade_de_baixa_ocupacao": round(calculate_occupancy_penalty(
                split_into_trips(best_route, demands, capacity, depot, autonomy, reserve), demands, capacity)),
            "uso_medio_da_autonomia_util_pct": round(sum(t["uso_da_autonomia_util_pct"] for t in trips) / len(trips)),
            "penalidade_de_atraso_nas_criticas": round(priority_penalty),
            **{key: value for key, value in optimized.items() if key != "viagens"},
        },
        "rota_otimizada": trips,
        "comparacao_com_rota_sem_otimizacao": {
            "descricao": "rota sem otimização = entregas feitas na ordem de cadastro dos pedidos",
            "sem_otimizacao": {key: value for key, value in baseline.items() if key != "viagens"},
            "economia_km": saving("distancia_total_km"),
            "economia_pct_da_distancia": round(saving("distancia_total_km") / baseline["distancia_total_km"] * 100, 1),
            "economia_tempo_min": saving("tempo_total_estimado_min"),
            "antecipacao_da_ultima_entrega_critica_min": saving("minutos_ate_a_ultima_entrega_critica"),
        },
    }


def build_driver_data(summary: Dict) -> Dict:
    """
    [INTEGRAÇÃO: LLM]
    Separa só o que vai para as instruções do motorista: dados do veículo e das
    entregas de cada viagem. Sem tempos, comparações nem dados do algoritmo, a
    LLM não tem como colocar essas informações no texto do motorista.

    Parâmetros:
    - summary: Dados da rota criados por `build_route_summary`.

    Retorna:
    Dict: Dados do veículo e das viagens, prontos para virar JSON.
    """
    return {
        "veiculo": summary["veiculo"],
        "viagens": [{
            "viagem": trip["viagem"],
            "carga_total_kg": trip["carga_total_kg"],
            "paradas": trip["paradas"],
            "retorno_a_central_km": trip["retorno"]["distancia_km"],
        } for trip in summary["rota_otimizada"]],
    }


# [INTEGRAÇÃO: LLM] Prompt de sistema: papel da LLM e regras que valem para todos os
# textos. Fica fixo (sem data nem números), para ser igual em todas as chamadas
SYSTEM_PROMPT = """Você é o assistente de logística da Central de Abastecimento de uma rede hospitalar. Um algoritmo genético calcula a rota de um veículo que sai da Central, faz as entregas e volta. Você recebe os dados dessa rota em JSON e os transforma em textos para o motorista e para a gestão. O objetivo do sistema é encontrar a melhor rota dentro das restrições de prioridade, carga e autonomia. O tempo é só uma estimativa de direção, sem paradas.

Regras:
- Use somente os dados fornecidos. Se um dado necessário não existir, diga que não está disponível em vez de supor.
- O único local com nome é a Central. Identifique cada ponto apenas como "Entrega N", onde N é o campo "ordem", o mesmo número que aparece no mapa do sistema. Não invente nomes de locais, endereços, ruas ou pessoas.
- Não cite horários do dia nem direções ou regiões (norte, leste etc.). Tempo aparece apenas como duração em minutos, quando estiver nos dados.
- Não fale de valores em dinheiro: os dados não têm essa informação. Também não diga o tipo de veículo nem de energia (bateria, combustível): fale apenas em autonomia.
- Não escreva notas, observações sobre os dados nem frases de introdução ou conclusão. Comece direto pelo título do texto.
- Ao citar um número, use o valor dos dados, com a unidade (km, min, kg). Se fizer uma conta (soma, diferença, percentual), ela deve sair dos dados.
- Escreva em português do Brasil, em Markdown, de forma direta. Prefira listas e tabelas curtas a parágrafos longos."""

# [INTEGRAÇÃO: LLM] Prompt de cada texto: público, objetivo e estrutura da resposta.
# Uma estrutura fixa deixa os relatórios comparáveis de um dia para o outro
DRIVER_INSTRUCTIONS_PROMPT = """Tarefa: escreva as instruções de entrega para o motorista, apenas com os dados das entregas. Não inclua orientações, cuidados, instruções de carregamento nem comentários.

Estrutura:
1. Título "Instruções de Entrega".
2. Veículo: capacidade em kg e autonomia em km (informe também a autonomia útil por viagem e a reserva).
3. Uma seção por viagem ("Viagem N"), com:
   - Carga total da viagem em kg.
   - Entregas críticas: tabela com as colunas Entrega e Peso (kg), só com as entregas de prioridade "crítica". Se não houver nenhuma, escreva "Nenhuma".
   - Entregas comuns: tabela com as colunas Entrega e Peso (kg), só com as entregas de prioridade "comum". Se não houver nenhuma, escreva "Nenhuma".
   - Roteiro passo a passo: lista numerada na ordem das entregas, com uma linha por trecho, neste formato:
     "Siga X km da Central até a Entrega N (CRÍTICA, Y kg)" no primeiro trecho;
     "Siga X km até a Entrega N (COMUM, Y kg)" nos demais trechos;
     "Siga X km de volta à Central" no último trecho."""

DAILY_REPORT_PROMPT = """Tarefa: escreva o relatório diário para a gestão da Central de Abastecimento, com base em <dados_da_rota>. A rota sem otimização é a que faz as entregas na ordem de cadastro dos pedidos.

Estrutura (título do texto: "Relatório Diário"):
1. Resumo (até 4 frases): o que foi entregue, se as restrições foram cumpridas e quanto a otimização reduziu de distância.
2. Eficiência da rota: tabela com distância total, tempo total estimado, número de viagens, uso médio da capacidade, uso médio da autonomia útil e entregas críticas fora do limite de viagens. Em seguida, uma tabela por viagem com carga, uso da capacidade, distância e uso da autonomia útil.
3. Economia de tempo e recursos: tabela com os valores sem otimização, com otimização e a diferença em distância (km), tempo estimado (min), número de viagens e minutos até a última entrega crítica. Inclua o percentual de economia de distância.
4. Sugestões de melhoria: de 3 a 5, da mais para a menos importante, baseadas nos padrões dos dados. Para cada uma:
   - Padrão observado: o dado que motivou a sugestão, com os números.
   - Sugestão: o que mudar (operação, veículo, parâmetros do algoritmo etc.).
   - Impacto esperado e como medir.
   Inclua apenas sugestões apoiadas pelos dados, voltadas à rota e às restrições, e não repita a mesma ideia em duas sugestões."""


class LLMUnavailableError(Exception):
    """[INTEGRAÇÃO: LLM] Sem chave, chave inválida ou sem internet: nenhum pedido vai funcionar."""


class LLMRequestError(Exception):
    """[INTEGRAÇÃO: LLM] Falha só neste pedido (sobrecarga, limite de uso, bloqueio, modelo retirado)."""


def load_api_key() -> Optional[str]:
    """
    [INTEGRAÇÃO: LLM]
    Lê a chave da API do Gemini: primeiro da variável de ambiente GEMINI_API_KEY
    e, se ela não existir, da linha "GEMINI_API_KEY=..." do arquivo .env na
    pasta do projeto. Ler o .env sem biblioteca extra evita instalar pacotes.

    Retorna:
    Optional[str]: A chave, ou None se não foi configurada.
    """
    if os.environ.get(API_KEY_VARIABLE):
        return os.environ[API_KEY_VARIABLE].strip()
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as file:
            for line in file:
                name, _, value = line.partition("=")
                if name.strip() == API_KEY_VARIABLE and value.strip():
                    return value.strip().strip('"').strip("'")
    return None


def request_model(api_key: str, model: str, request_body: Dict) -> str:
    """
    [INTEGRAÇÃO: LLM]
    Envia o pedido a um modelo do Gemini e devolve o texto da resposta. Em caso
    de sobrecarga ou limite de uso, espera e tenta de novo no mesmo modelo.

    Parâmetros:
    - api_key: Chave da API do Gemini.
    - model: Nome do modelo.
    - request_body: Corpo do pedido, montado por `ask_llm`.

    Retorna:
    str: Texto em Markdown gerado pela LLM.
    """
    # A chave vai no cabeçalho, e não na URL, para não aparecer em logs de erro
    request = urllib.request.Request(
        GEMINI_URL.format(model=model), data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")

    for attempt in range(1, LLM_RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
                reply = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            try:
                message = json.loads(error.read().decode("utf-8"))["error"]["message"]
            except (ValueError, KeyError):
                message = error.reason
            # 429: limite do plano gratuito; 500/503: serviço sobrecarregado. Espera e tenta de novo
            # Exceção: com o limite diário esgotado, esperar segundos não adianta
            daily_limit_reached = error.code == 429 and "per day" in message.lower()
            if error.code in (429, 500, 503) and not daily_limit_reached and attempt < LLM_RETRY_ATTEMPTS:
                time.sleep(LLM_RETRY_WAIT_SECONDS * attempt)
                continue
            # 400/401/403: chave inválida ou sem permissão. Nesses casos nenhum pedido
            # vai funcionar. Os demais erros (como 404, modelo retirado) são só deste modelo
            if error.code in (400, 401, 403):
                raise LLMUnavailableError(f"erro {error.code} da API do Gemini: {message}")
            raise LLMRequestError(f"erro {error.code} da API do Gemini: {message}")
        except urllib.error.URLError:
            raise LLMUnavailableError("sem conexão com a API do Gemini. Confira a internet")
        except TimeoutError:
            # Modelo lento: em vez de esperar de novo por ele, passa para o próximo
            raise LLMRequestError(f"a API do Gemini não respondeu em {LLM_TIMEOUT_SECONDS} s")
        except OSError as error:
            raise LLMRequestError(f"a conexão com a API do Gemini caiu: {error}")

    # Pedido bloqueado pelos filtros de segurança do Gemini: não vem resposta
    if not reply.get("candidates"):
        block_reason = reply.get("promptFeedback", {}).get("blockReason", "motivo não informado")
        raise LLMRequestError(f"o Gemini bloqueou o pedido ({block_reason})")

    candidate = reply["candidates"][0]
    # Partes marcadas como "thought" são o raciocínio do modelo, não o texto final
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
    # Sem texto final (ex.: o raciocínio gastou todo o limite de tokens): não há o que salvar
    if not text.strip():
        raise LLMRequestError(f"resposta vazia (motivo: {candidate.get('finishReason', 'não informado')})")
    if candidate.get("finishReason") == "MAX_TOKENS":
        text += "\n\n> Aviso: a resposta atingiu o limite de tamanho e pode estar incompleta."
    return text


def ask_llm(api_key: str, route_data: Dict, task_prompt: str,
            on_problem: Callable[[str], None] = print) -> str:
    """
    [INTEGRAÇÃO: LLM]
    Pede um texto à LLM, tentando os modelos de LLM_MODELS em ordem até um responder.

    Os dados da rota vêm antes da tarefa, entre tags, para o modelo separar
    bem o que é dado do que é instrução. Não é enviada temperatura: os modelos
    Gemini 3.6 em diante ignoram esse parâmetro.

    Parâmetros:
    - api_key: Chave da API do Gemini.
    - route_data: Dados da rota que esta tarefa pode usar.
    - task_prompt: Instruções da tarefa.
    - on_problem: Função chamada quando um modelo falha.

    Retorna:
    str: Texto em Markdown gerado pela LLM.
    """
    route_data_json = json.dumps(route_data, ensure_ascii=False, indent=1)
    request_body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{
            "role": "user",
            "parts": [{"text": f"<dados_da_rota>\n{route_data_json}\n</dados_da_rota>\n\n{task_prompt}"}],
        }],
        "generationConfig": {"maxOutputTokens": LLM_MAX_TOKENS},
    }

    for model in LLM_MODELS:
        try:
            return request_model(api_key, model, request_body)
        except LLMRequestError as error:
            on_problem(f"LLM: o modelo {model} falhou: {error}")
    raise LLMRequestError("nenhum modelo respondeu")


def run_report_pipeline(summary: Dict, on_progress: Callable[[str], None] = print) -> bool:
    """
    [INTEGRAÇÃO: LLM]
    Salva os dados da rota e gera os dois textos com a LLM. O motorista recebe
    só os dados das entregas; o relatório diário usa os dados completos.
    Erros da API não derrubam o programa: são informados por `on_progress`,
    gravados em ERRORS_FILE, e os dados da rota continuam salvos.

    Parâmetros:
    - summary: Dados da rota criados por `build_route_summary`.
    - on_progress: Função chamada com mensagens de andamento (ex.: para o terminal).

    Retorna:
    bool: True se todos os textos foram gerados.
    """
    output_dir = os.path.join(REPORTS_DIR, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "dados_rota.json"), "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    # Textos gerados: (arquivo de saída, prompt da tarefa, dados que a tarefa recebe)
    report_tasks = [
        ("instrucoes_motorista.md", DRIVER_INSTRUCTIONS_PROMPT, build_driver_data(summary)),
        ("relatorio_diario.md", DAILY_REPORT_PROMPT, summary),
    ]

    def report_problem(message: str) -> None:
        # Mostra o problema na tela e também o grava, para consultar depois
        on_progress(message)
        with open(os.path.join(output_dir, ERRORS_FILE), "a", encoding="utf-8") as file:
            file.write(f"{datetime.now().strftime('%H:%M:%S')} {message}\n")

    api_key = load_api_key()
    if api_key is None:
        report_problem(f"LLM: chave do Gemini não configurada. Crie o arquivo .env com {API_KEY_VARIABLE}=sua-chave")
        return False

    generated = 0
    for index, (file_name, task_prompt, route_data) in enumerate(report_tasks, start=1):
        on_progress(f"LLM: gerando {file_name} ({index}/{len(report_tasks)})...")
        try:
            text = ask_llm(api_key, route_data, task_prompt, report_problem)
        except LLMUnavailableError as error:
            # Sem chave válida ou internet, nenhum dos textos vai funcionar: para aqui
            report_problem(f"LLM: {error}")
            return False
        except LLMRequestError as error:
            # Erro só neste texto: informa e segue para o próximo
            report_problem(f"LLM: não foi possível gerar {file_name}: {error}")
            continue

        with open(os.path.join(output_dir, file_name), "w", encoding="utf-8") as file:
            file.write(text)
        generated += 1

    on_progress(f"LLM: {generated} de {len(report_tasks)} textos salvos em {output_dir}")
    return generated == len(report_tasks)


def start_reports(summary: Dict, status: Dict) -> threading.Thread:
    """
    [INTEGRAÇÃO: LLM]
    Gera os relatórios em outra thread, para a janela não travar esperando a API.
    A situação fica em status["text"], para a janela; os detalhes vão para o terminal.
    """
    def generate_reports() -> None:
        try:
            success = run_report_pipeline(summary)
        except Exception as error:
            print(f"LLM: erro inesperado: {error}")
            success = False
        status["text"] = "Relatórios gerados" if success else "Erro ao gerar relatórios"

    status["text"] = "Gerando relatórios"
    thread = threading.Thread(target=generate_reports)
    thread.start()
    return thread
