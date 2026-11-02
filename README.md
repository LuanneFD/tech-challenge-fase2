# Roteirização de entregas hospitalares com Algoritmo Genético

Tech Challenge FIAP (fase 2). Um algoritmo genético calcula a rota de um veículo que sai da central de abastecimento, entrega medicamentos e insumos e volta, respeitando as restrições de prioridade, carga e autonomia. Baseado em [FIAP/genetic_algorithm_tsp](https://github.com/FIAP/genetic_algorithm_tsp).

## Restrições

| Restrição | Regra | Como é tratada |
|---|---|---|
| Prioridade | Entregas críticas primeiro, até a 2ª viagem | Penalidade no custo |
| Carga | 100 kg por viagem; ocupação mínima desejada de 60% | Volta à central quando não cabe; penalidade para pouca carga |
| Autonomia | 1000 unidades do mapa por viagem, com 10% de reserva | Volta à central antes de usar a reserva |

Os pontos e os pesos são sorteados a cada execução, e por isso cada mapa é diferente. O projeto usa um veículo, que pode fazer várias viagens.

## Estrutura

```
main.py              Passo a passo do algoritmo
config.py            Parâmetros do algoritmo, das restrições e da tela
relatorios_llm.py    Relatórios gerados com a LLM (Gemini) e seus parâmetros
algoritmo/
  distancia.py       Distância entre dois pontos
  problema.py        Pontos de entrega, central, prioridades e pesos
  genetico.py        População, seleção, cruzamento e mutação
  rota.py            Divide a rota em viagens e calcula o custo
restricoes/
  prioridade.py      Entregas críticas primeiro
  carga.py           Peso máximo do veículo e ocupação mínima
  autonomia.py       Distância máxima por viagem
interface/
  desenho.py         Funções básicas de desenho
  janela.py          Janela, legenda e tela final
tests/               Testes unitários das restrições
relatorios/          Relatórios gerados em cada execução
```

## Como executar

É preciso ter o Python 3 instalado. Na pasta do projeto, prepare o ambiente uma vez:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pygame-ce numpy matplotlib
```

Depois, execute:

```powershell
.venv\Scripts\python.exe main.py
```

A janela mostra o gráfico de convergência, o mapa com uma cor por viagem e a legenda. A execução para sozinha depois de 500 gerações sem achar uma rota melhor, e o resultado fica na tela até a janela ser fechada. A tecla `q` também fecha a janela.

## Relatórios com LLM

Os relatórios usam o plano gratuito da API do Gemini e precisam de internet. Crie uma chave em https://aistudio.google.com/apikey e um arquivo `.env` na pasta do projeto:

```
GEMINI_API_KEY=sua-chave-aqui
```

O arquivo `.env` não vai para o GitHub. Sem a chave, o algoritmo roda normalmente e salva só os dados da rota.

Cada execução cria uma pasta em `relatorios/` com:

- `instrucoes_motorista.md`: dados das entregas de cada viagem
- `relatorio_diario.md`: eficiência, economia de tempo e recursos e sugestões
- `dados_rota.json`: dados enviados à LLM
- `erros.txt`: motivo das falhas, criado só se algo der errado

## Testes

```powershell
.venv\Scripts\python.exe -m unittest discover -v
```
