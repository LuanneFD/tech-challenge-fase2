# Relatório Diário

## 1. Resumo

Na data de 2026-11-02, foram entregues 257 kg de carga distribuídos em 15 entregas (sendo 4 críticas) ao longo de 4 viagens. Todas as restrições operacionais foram atendidas, com 0 entregas críticas fora do limite de 2 viagens e conclusão da última entrega crítica em 47 min. A otimização por algoritmo genético reduziu a distância total percorrida em 147,4 km (49,2%) em comparação com a rota sem otimização.

## 2. Eficiência da Rota

### Indicadores Gerais

| Indicador | Valor |
| --- | --- |
| Distância total | 152,1 km |
| Tempo total estimado | 114 min |
| Número de viagens | 4 |
| Uso médio da capacidade | 64% |
| Uso médio da autonomia útil | 84% |
| Entregas críticas fora do limite de viagens | 0 |

### Desempenho por Viagem

| Viagem | Carga | Uso da capacidade | Distância | Uso da autonomia útil |
| --- | --- | --- | --- | --- |
| Viagem 1 | 59 kg | 59% | 39,3 km | 87% |
| Viagem 2 | 64 kg | 64% | 43,6 km | 97% |
| Viagem 3 | 63 kg | 63% | 27,8 km | 62% |
| Viagem 4 | 71 kg | 71% | 41,5 km | 92% |

## 3. Economia de Tempo e Recursos

| Métrica | Sem Otimização | Com Otimização | Diferença |
| --- | --- | --- | --- |
| Distância total (km) | 299,5 km | 152,1 km | -147,4 km (-49,2%) |
| Tempo estimado (min) | 225 min | 114 min | -111 min |
| Número de viagens | 9 | 4 | -5 |
| Minutos até a última entrega crítica | 188 min | 47 min | -141 min |

Percentual de economia de distância: 49,2%.

## 4. Sugestões de Melhoria

### Sugestão 1: Elevação do uso mínimo da capacidade na primeira viagem
- **Padrão observado:** A viagem 1 registrou 59% de uso da capacidade (59 kg), ficando abaixo da ocupação mínima desejada de 60%, o que gerou uma penalidade de baixa ocupação de 40 no algoritmo.
- **Sugestão:** Ajustar os parâmetros de penalização do algoritmo genético para desestimular viagens com ocupação inferior a 60% ou rebalancear 1 kg a 2 kg adicionais para a viagem 1.
- **Impacto esperado e como medir:** Eliminação da penalidade de baixa ocupação de 40. Medir através do indicador de uso mínimo da capacidade nas execuções da rota.

### Sugestão 2: Balanceamento do uso de autonomia útil entre as viagens
- **Padrão observado:** A viagem 2 utilizou 97% da autonomia útil (43,6 km dos 45,0 km disponíveis), enquanto a viagem 3 utilizou apenas 62% (27,8 km).
- **Sugestão:** Reorganizar o sequenciamento das paradas entre as viagens no algoritmo para equalizar a distância percorrida por percurso, evitando proximidade excessiva do limite útil.
- **Impacto esperado e como medir:** Redução da amplitude do uso de autonomia útil por viagem (atualmente entre 62% e 97%). Medir comparando a diferença percentual de autonomia útil entre a viagem de maior e menor percurso.

### Sugestão 3: Calibração dos critérios de parada do algoritmo genético
- **Padrão observado:** A melhor rota foi encontrada na geração 112, mas o algoritmo continuou executando até a geração 612 devido ao critério de parada de 500 gerações sem melhora, realizando também 4 reinícios de população.
- **Sugestão:** Reduzir o limite do critério de parada para um intervalo menor de gerações sem melhora (por exemplo, 200 a 300 gerações) e reavaliar a probabilidade de mutação de 0,5.
- **Impacto esperado e como medir:** Redução do processamento computacional sem perda de qualidade da rota. Medir pelo número total de gerações executadas e o tempo de processamento do algoritmo.

### Sugestão 4: Ajuste do peso de penalidade de atraso nas entregas críticas
- **Padrão observado:** O sistema acumulou uma penalidade de atraso nas críticas de 1439, apesar de todas as 4 entregas críticas terem sido alocadas nas duas primeiras viagens e concluídas em 47 min.
- **Sugestão:** Revisar a função de aptidão do algoritmo genético para adequar o cálculo das penalidades de atraso ao tempo real de atendimento das entregas críticas.
- **Impacto esperado e como medir:** Redução ou eliminação da pontuação de penalidade no cálculo do algoritmo. Medir pelo valor do campo de penalidade de atraso nas críticas do resumo da rota.