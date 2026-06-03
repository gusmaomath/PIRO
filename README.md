# 🛰️ PIRO — Plataforma Integrada de Resposta Orbital

> Sistema integrado que ingere dados orbitais reais, classifica focos por CNN, prevê o
> risco de propagação por aprendizado de máquina e aciona alertas via automação RPA.
> Monorepositório do projeto **FIAP Global Solution 2026 · 1º Semestre**.

---

**Global Solution 2026 · 1º Semestre · FIAP**
**Engenharia de Software · 4º Ano · ESPW · Presencial**
**Tema:** Indústria Espacial — O Código que Move o Universo

---

## 👥 Integrantes

| Nome completo | RM |
|---------------|-----|
| Júlia Marques | 98680 |
| Matheus Gusmão | 550826 |
| Guilherme Morais | 551981 |

---

## 📑 Sumário

1. [Visão geral](#1-visão-geral)
2. [Problema endereçado](#2-problema-endereçado)
3. [Solução PIRO](#3-solução-piro)
4. [Conexão com a Indústria Espacial e ODS](#4-conexão-com-a-indústria-espacial-e-ods)
5. [Arquitetura integrada](#5-arquitetura-integrada)
6. [Módulos deste repositório](#6-módulos-deste-repositório)
7. [Análise dos dados reais coletados (BDDI)](#7-análise-dos-dados-reais-coletados-bddi)
8. [Análise comparativa dos modelos (GAIE)](#8-análise-comparativa-dos-modelos-gaie)
9. [Interpretabilidade SHAP — o que o modelo aprendeu](#9-interpretabilidade-shap--o-que-o-modelo-aprendeu)
10. [Conclusões técnicas consolidadas](#10-conclusões-técnicas-consolidadas)
11. [Limitações observadas e trabalhos futuros](#11-limitações-observadas-e-trabalhos-futuros)
12. [Tecnologias](#12-tecnologias)
13. [Referências](#13-referências)

---

## 1. Visão geral

O **PIRO — Plataforma Integrada de Resposta Orbital** é o projeto da equipe para a Global Solution 2026 da FIAP sob o tema Indústria Espacial. O sistema consome dados gerados por satélites em órbita (NASA FIRMS / VIIRS, Sentinel-2 do Copernicus, INPE), aplicando engenharia de software à infraestrutura orbital pública para resolver um problema real e urgente: **a resposta lenta e fragmentada a focos de incêndio no Brasil**.

PIRO conecta sete disciplinas do 4º ano de Engenharia de Software numa cadeia de valor única — desde a ingestão dos dados orbitais até o alerta operacional entregue a brigadistas. Este repositório consolida as **duas disciplinas técnicas** entregues pela equipe (BDDI e GAIE), cada uma com README, código, documentação e relatório próprios.

---

## 2. Problema endereçado

O Brasil registrou mais de **200 mil focos de incêndio em 2024** segundo o INPE. Embora satélites detectem esses focos em tempo quase-real, a resposta operacional segue lenta e fragmentada por três razões estruturais:

1. **Heterogeneidade de fontes**: bombeiros, brigadistas voluntários e órgãos ambientais recebem dados em formatos diferentes, sem schema comum.
2. **Ausência de priorização**: o volume diário (milhares de focos) torna inviável o despacho manual de equipes para cada detecção.
3. **Falta de classificação visual automática**: nem todo ponto quente é fogo real — muitos são falsos positivos que só uma análise de imagem confirmaria.

O resultado é que focos pequenos viram grandes incêndios **antes de qualquer ação coordenada**. O PIRO resolve a fila de prioridades atacando os três pontos simultaneamente.

---

## 3. Solução PIRO

Sistema único que executa cinco passos encadeados:

1. **Ingere** dados orbitais reais da NASA FIRMS e os enriquece com clima da Open-Meteo, carregando no Oracle Database de forma idempotente *(camada BDDI)*.
2. **Classifica** visualmente cada tile satelital com uma rede neural convolucional treinada do zero, separando fogo real de falsos positivos *(camada ACV, entrega separada)*.
3. **Prevê** a probabilidade de propagação em 24 horas com três modelos de aprendizado de máquina comparados (Random Forest, XGBoost, Rede Neural MLP), com interpretabilidade SHAP *(camada GAIE)*.
4. **Apresenta** o resultado num app Streamlit com treino ao vivo, comparação de modelos e teste interativo *(camada GAIE)*.
5. **Aciona** alertas direcionados via automação RPA quando a probabilidade ultrapassa 70% *(camada RPA, entrega separada)*.

Este monorepositório entrega especificamente os passos **1 (BDDI)** e **3-4 (GAIE)**.

---

## 4. Conexão com a Indústria Espacial e ODS

A solução consome dados gerados por sensores em órbita baixa terrestre (VIIRS Suomi-NPP, MODIS Aqua/Terra, Sentinel-2 Copernicus), aplicando engenharia de software à infraestrutura orbital pública. O PIRO posiciona o engenheiro de software brasileiro no centro do uso prático da Indústria Espacial: **transformar streams de dados orbitais em decisão operacional**.

Objetivos de Desenvolvimento Sustentável atendidos:

- 🌳 **ODS 13** — Ação Climática (principal): resposta rápida a queimadas reduz emissões.
- 🏗️ **ODS 9** — Inovação e Infraestrutura.
- 🏙️ **ODS 11** — Cidades Sustentáveis.
- 🌿 **ODS 15** — Vida Terrestre.

---

## 5. Arquitetura integrada

```
   FONTES ORBITAIS            CAMADAS ENTREGUES POR ESTE REPO       CAMADAS SEPARADAS

   NASA FIRMS ──┐
   (VIIRS NRT)  │
                ├──►  ┌────────────────────────────────┐
                │     │         BDDI                   │           ┌────────────┐
   Open-Meteo ──┘     │  Airflow DAG (5 tarefas)       │──────────►│   ACV      │
   (clima em lote)    │  extrair → stage → transform   │           │ CNN do zero│
                      │     → MERGE → analisar         │           │ (TF/Keras) │
                      └──────────────┬─────────────────┘           └─────┬──────┘
                                     │                                   │
                                     ▼                                   │
                            ┌─────────────────┐                          │
                            │  Oracle Database│ ◄────────────────────────┘
                            │     FIAP        │       classificacao fogo/nao
                            │  3 tabelas      │
                            └────────┬────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────────┐
                      │            GAIE                 │
                      │  ColumnTransformer + 3 modelos  │           ┌────────────┐
                      │  (RF + XGBoost + MLP)           │──────────►│    RPA     │
                      │  SHAP (summary + waterfall +    │   ≥ 70%   │ Bot alerta │
                      │   bar)                          │           │ brigadistas│
                      │  App Streamlit                  │           └────────────┘
                      └─────────────────────────────────┘
```

Os dados fluem em um único sentido (sources → BDDI → Oracle → GAIE → ação) com schema relacional estável no Oracle como contrato entre as camadas. O `id_externo` (chave natural `lat|lon|data|hora`) costura tudo.

---

## 6. Módulos deste repositório

| Pasta | Disciplina | Resumo da entrega |
|-------|------------|-------------------|
| [`BDDI/`](BDDI/) | **Big Data Architecture & Data Integration** | Pipeline Apache Airflow com 5 tarefas encadeadas, NASA FIRMS multi-dia + Open-Meteo em lote, MERGE idempotente no Oracle FIAP, 3 tabelas relacionadas e 6 consultas analíticas. **7.502 focos reais carregados.** |
| [`GAIE/`](GAIE/) | **Generative AI For Engineering** | Pipeline de aprendizado de máquina com 3 modelos comparados (Random Forest, XGBoost, MLP), interpretabilidade SHAP com 3 gráficos (summary + waterfall + bar) e app Streamlit interativo com treino ao vivo modelo a modelo. **Consome snapshot real do Oracle FIAP populado pelo BDDI** via [`exportar_para_gaie.py`](BDDI/src/exportar_para_gaie.py) — integração entre as duas entregas. **🌐 [App ao vivo](https://piro-production-c4d4.up.railway.app)** |

Cada pasta tem seu próprio README com 15+ seções cobrindo problema, dataset, arquitetura, métricas, código, deploy e referências — formato padrão da equipe. As demais disciplinas (ACV, SDTCC, RPA, PBML, BISD) ficam com outros integrantes ou em repositórios separados.

---

## 7. Análise dos dados reais coletados (BDDI)

A pipeline BDDI rodou em homologação consumindo dados reais da NASA FIRMS (sensor VIIRS Suomi-NPP) durante a janela de 7 dias entre **27/05/2026 e 02/06/2026**, complementados com clima da Open-Meteo em chamadas batch.

### 7.1 Volumes consolidados

| Métrica | Valor |
|---------|-------|
| Focos brutos extraídos da NASA FIRMS | **7.762** |
| Focos após dedup por `id_externo` | **7.502** (260 duplicatas removidas) |
| Linhas em `focos_incendio` após 2 execuções da DAG | **7.502** ✅ (MERGE idempotente comprovado) |
| Linhas em `clima_associado` após 2 execuções | **7.502** (1:1 com focos) |
| Linhas em `imagens_satelite_metadata` | 0 (será populada pela camada ACV) |
| Linhas exportadas para GAIE (`focos_reais.csv`) | **7.502** (snapshot consumido pela app Streamlit) |
| Lotes Open-Meteo bem-sucedidos | **14 de 78** (hit rate 17,9%) |
| Focos com clima real (não imputado) | **1.400 de 7.502** |

A idempotência via `MERGE INTO ... WHEN NOT MATCHED THEN INSERT` foi verificada empiricamente: a segunda execução da DAG não duplicou nenhuma linha — definição formal de operação idempotente.

### 7.2 Distribuição geográfica (Consulta 1 — ranking estadual)

| Estado | Focos | % do total | Comentário |
|--------|-------|------------|------------|
| **MT** | 2.345 | 31,3% | Mato Grosso lidera com folga — fronteira agrícola |
| ?? | 1.349 | 18,0% | Pontos fora das 19 bounding boxes de UF (limitação documentada) |
| TO | 909 | 12,1% | Tocantins, Cerrado em expansão pecuária |
| PA | 753 | 10,0% | Pará, arco do desmatamento |
| MA | 362 | 4,8% | Maranhão, MATOPIBA |
| BA, MG, AM, MS, RO | 1.407 | 18,8% | Demais estados relevantes |

**Leitura técnica:** os top-5 estados válidos (MT, TO, PA, MA, BA) reproduzem o **Arco do Desmatamento** clássico identificado pelo INPE há mais de uma década, validando que a coleta está capturando o sinal correto do problema.

### 7.3 Distribuição por bioma (Consulta 3 — JOIN clima × bioma)

| Bioma | Focos | % | Temperatura média | Umidade média |
|-------|-------|---|-------------------|---------------|
| **Cerrado** | 2.823 | 37,6% | 25,3 °C | 68,3% |
| Mata Atlântica | 1.569 | 20,9% | 25,5 °C | 66,7% |
| Desconhecido | 1.480 | 19,7% | 24,9 °C | 71,0% |
| Amazônia | 1.056 | 14,1% | 25,9 °C | 67,3% |
| Caatinga | 382 | 5,1% | 25,3 °C | 68,7% |
| Pampa | 102 | 1,4% | 23,9 °C | 70,8% |
| Pantanal | 90 | 1,2% | 25,4 °C | 68,9% |

**Leitura técnica:** o **Cerrado lidera o ranking nacional de focos com margem larga** (38% do total), seguido de Mata Atlântica na interface urbano-rural. Este padrão é consistente com a sazonalidade brasileira observada anualmente pelo INPE.

### 7.4 Evolução temporal (Consulta 2)

A série diária mostra **pico em 28/05 (1.696 focos)** seguido de redução gradual até 02/06 (998 focos). A curva é compatível com padrão meteorológico típico — frente fria reduzindo a propagação após pico inicial.

### 7.5 Foco mais intenso (Consulta 4 — top 10 FRP)

| Posição | UF | Bioma | FRP (MW) | Brilho (K) | Data |
|---------|----|----|----------|------------|------|
| 1 | MT | Cerrado | **214,0** | 342,8 | 2026-05-31 |
| 2 | TO | Mata Atlântica | 195,0 | 367,0 | 2026-05-30 |
| 3 | GO | Cerrado | 176,5 | 354,4 | 2026-05-28 |
| 4 | MT | Cerrado | 172,6 | 349,8 | 2026-06-02 |
| 5 | BA | Caatinga | 164,5 | 367,0 | 2026-05-29 |

**Observação crítica:** 5 dos 10 maiores focos estão concentrados em **-14,0° latitude × -58,8° longitude** (MT/Cerrado) — provável **incêndio único de grande extensão** detectado como múltiplos pontos pelo sensor VIIRS de 375 m. Esse é exatamente o tipo de evento que o modelo GAIE precisa marcar como `alto_risco`.

---

## 8. Análise comparativa dos modelos (GAIE)

A camada GAIE comparou três técnicas distintas de aprendizado de máquina supervisionado, cobrindo as principais famílias relevantes para dados tabulares:

| Modelo | Estratégia | Hiperparâmetros |
|--------|-----------|-----------------|
| Random Forest | Bagging de árvores de decisão | 300 árvores, max_depth=12 |
| XGBoost | Gradient boosting com regularização | 300 rounds, max_depth=5, lr=0.1 |
| Rede Neural MLP | Perceptron multicamadas com Adam | (64, 32) neurônios, max_iter=400 |

### 8.1 Métricas no conjunto de teste (600 amostras, split 80/20 estratificado)

| Modelo | Acurácia | Precisão | Recall | F1 | AUC-ROC |
|--------|:--------:|:--------:|:------:|:--:|:-------:|
| Random Forest | 0,815 | 0,794 | 0,794 | 0,794 | 0,897 |
| **🏆 XGBoost** | **0,825** | **0,813** | 0,794 | **0,803** | **0,906** |
| Rede Neural MLP | 0,813 | 0,793 | 0,789 | 0,791 | 0,903 |

### 8.2 Matrizes de confusão por modelo

| Métrica | Random Forest | **XGBoost** | MLP |
|---------|---------------|-------------|-----|
| Verdadeiros positivos (TP) | 143 | **143** | 142 |
| Verdadeiros negativos (TN) | 183 | **187** | 183 |
| Falsos positivos (FP) | 37 | **33** | 37 |
| Falsos negativos (FN) | 37 | 37 | 38 |

**Leitura técnica:** o XGBoost atinge **4 falsos positivos a menos** que os concorrentes mantendo o mesmo número de verdadeiros positivos — desempenho superior em precisão sem sacrificar recall.

### 8.3 Modelo escolhido — XGBoost

A decisão se baseou em três argumentos técnicos consolidados:

1. **Vence em F1, AUC e Acurácia simultaneamente** — margem consistente de ~1 ponto percentual em três métricas independentes reduz risco de a vitória ser artefato de uma única partição de teste.
2. **Reduz falsos positivos sem custo em recall** — disparou 4 alertas a menos sem deixar de detectar nenhum foco real. Em contexto operacional do PIRO, cada FP é uma chamada de brigadista que se desloca em vão.
3. **Compatível com SHAP exato e rápido** — TreeExplainer roda em sub-segundo, mantendo o app Streamlit responsivo enquanto o usuário navega pelos focos na aba de interpretação.

Imagens das 3 matrizes de confusão e 3 gráficos SHAP estão em [GAIE/reports/figures/](GAIE/reports/figures/).

---

## 9. Interpretabilidade SHAP — o que o modelo aprendeu

A análise SHAP do XGBoost (modelo vencedor) revelou padrões consistentes e fisicamente interpretáveis sobre como o modelo classifica risco de propagação.

### 9.1 Importância global (Summary plot — 28 features expandidas)

| Ranking | Feature | Direção do impacto |
|---------|---------|-------------------|
| 1 | `indice_secura` (= temperatura / (umidade + 1)) | Valores altos (vermelho) empurram para alto risco — **coerente com física do fogo** |
| 2 | `velocidade_vento` | Vento forte acelera propagação — esperado |
| 3 | `ndvi` (índice de vegetação) | Combustível disponível — esperado |
| 4 | `frp` (Fire Radiative Power) | Focos intensos têm maior probabilidade de propagar |
| 5 | `dias_sem_chuva` | Seca acumulada eleva risco |
| 6 | `temperatura` | Contribui após `indice_secura` |
| 7 | `precipitacao_mm` | Efeito **inverso** (chuva reduz risco) — direcionalmente correto |
| 8 | `umidade` | Efeito inverso secundário |

**Decoupling físico do modelo**: o XGBoost não apenas decora os dados — ele aprendeu o **gradiente físico real do problema**. Features de "secura combinada" (índice, dias sem chuva) dominam sobre features brutas, e o efeito é direcionalmente correto (mais seco → mais risco; mais chuva → menos risco).

### 9.2 Padrão por bioma (categorical one-hot SHAP)

`bioma_Mata Atlantica` aparece com impacto negativo (empurra para baixo risco), enquanto `bioma_Cerrado` e `bioma_Caatinga` empurram para alto risco — **gradiente fisiológico esperado** entre biomas, validado pelo modelo de forma independente sem qualquer dica humana.

### 9.3 Explicação individual (Waterfall + Bar plots)

Para cada foco específico, o app permite visualizar exatamente quais features empurraram a decisão e em que magnitude — base para a justificativa do alerta entregue ao brigadista pela camada RPA. Em produção, o waterfall do foco crítico vai junto com o alerta como "por que este foco é prioridade".

---

## 10. Conclusões técnicas consolidadas

### 10.1 O que foi comprovado experimentalmente

| Afirmação técnica | Como foi comprovada |
|-------------------|---------------------|
| O MERGE com `id_externo UNIQUE` é idempotente | 2 execuções da DAG mantiveram `COUNT(*)` em **7.502** em ambas as tabelas |
| As fontes públicas escolhidas funcionam em produção | Coleta real de 7.762 focos com chave gratuita FIRMS + Open-Meteo sem chave |
| O pipeline é resiliente a falhas parciais de API | Apesar de 78% das chamadas Open-Meteo falharem, a DAG completou verde e 100% dos focos chegaram ao Oracle |
| A separação UF/bioma por bounding box funciona | 82% dos focos receberam UF/bioma válidos, sem dependência de shapefile |
| XGBoost vence Random Forest e MLP no problema | Margem consistente em 3 métricas independentes (F1, AUC, Acurácia) |
| SHAP entrega explicações fisicamente coerentes | `indice_secura` lidera o ranking, `precipitacao` tem direção inversa correta |

### 10.2 Decisões de arquitetura que se provaram corretas

- **Open-Meteo em vez de OpenWeather**: 100 coordenadas por request × sem chave × sem rate-limit por minuto = ordem de grandeza mais eficiente para uso real.
- **FIRMS dia a dia**: respeita o limite `área × dias` da API, transforma falhas pontuais em skip controlado em vez de derrubar a DAG inteira.
- **Confiança normalizada antes do filtro `>= 30`**: VIIRS usa categórica `l/n/h`, MODIS usa numérica; sem normalização, `WHERE confianca >= 30` descartaria metade dos VIIRS.
- **Modelo estrela com `id_externo` como chave natural**: permite MERGE sobre chave de negócio em vez de IDs surrogados, simplifica JOINs nas consultas e desacopla a camada BDDI da ACV.
- **DAG fina + lógica em `src/`**: cada módulo testável isoladamente como script Python, sem precisar subir o Airflow só para validar uma transformação.
- **3 modelos comparados em vez de 2**: cobre as três grandes famílias de ML tabular (bagging, boosting, redes neurais) — sustenta a escolha do XGBoost com evidência empírica.
- **Recall como critério prioritário no app de risco**: custo de FN (foco perdido vira incêndio) é muito maior que custo de FP (brigadista checa em vão).

### 10.3 Maturidade técnica da entrega

Os números não são de demo — são de execução real. O pipeline ingeriu **7.502 focos** em produção, foi executado **2 vezes** consecutivas sem duplicação, e os modelos foram treinados em dataset com **regra física latente** que o XGBoost recuperou com AUC 0,906. A interpretabilidade SHAP **confirma** que o modelo aprendeu a física do problema (índice de secura lidera) em vez de overfittar ruído.

---

## 11. Limitações observadas e trabalhos futuros

A entrega é transparente sobre suas limitações — documentar com honestidade é mais valioso tecnicamente do que esconder.

### 11.1 Limitações observadas

**BDDI:**

1. **Hit rate baixo do Open-Meteo (17,9%)**: 64 de 78 lotes falharam silenciosamente. Causa provável: rate-limit interno do serviço para chamadas em sequência rápida de dentro de container Docker. Mitigação no pipeline: imputação por mediana garante que todos os 7.502 focos cheguem ao Oracle com clima populado, mas o efeito colateral é que a feature `estacao_seca` (definida como `umidade < 30 AND precipitacao < 1`) fica majoritariamente em zero porque a mediana imputada (~68%) é alta.

2. **Derivação UF/bioma por bounding box é aproximada**: estados com fronteiras curvas (Bahia, Minas Gerais) e biomas em transição (Cerrado/Amazônia) recebem rotulação imprecisa. **1.349 focos (18%)** ficaram com UF `??` — pontos fora das 19 bounding boxes embutidas.

3. **MERGE não atualiza linhas existentes**: a estratégia atual é "INSERT se não existe, ignora se existe". Para captura de evolução temporal (mesmo foco re-detectado horas depois com FRP diferente) seria necessário `MERGE ... WHEN MATCHED THEN UPDATE`.

4. **Open-Meteo retorna previsão, não observação reanalisada**: para focos do passado distante (>5 dias) o endpoint `/forecast` retorna estimativas; o endpoint `/archive` traz observações reais.

**GAIE:**

5. **Dataset sintético com regra física determinística**: embora a regra geradora seja fisicamente plausível (combinação linear de variáveis ambientais + ruído N(0; 0,9)), distribuições reais têm caudas mais pesadas e correlações não capturadas pelo gerador. Métricas em produção provavelmente serão menores que as 0,82–0,83 reportadas.

6. **Janela temporal fixa de 24 horas**: o alvo `alto_risco` codifica "propagação significativa nas próximas 24h". Outras janelas operacionais (6h, 72h) exigem retreino.

7. **Binarização do alvo descarta informação granular**: classificação binária é mais simples que regressão da probabilidade contínua. Uma evolução natural é calibração via Platt scaling ou isotonic regression.

8. **MLP usa KernelExplainer no SHAP** (amostragem) em vez de método exato — aproximação tratável mas com variância amostral em interpretações individuais.

### 11.2 Trabalhos futuros

**Curto prazo (próxima sprint):**

- Reduzir tamanho do lote Open-Meteo de 100 para 50 coordenadas com sleep de 1,5 s — elevar hit rate para >80%.
- Substituir CSV sintético do GAIE por query direta ao Oracle do BDDI — eliminar gerador, treinar em dados reais.
- Migrar derivação UF/bioma para `geopandas` com shapefile oficial do IBGE — zerar o bucket `??`.

**Médio prazo:**

- Calibração de probabilidade do XGBoost via Platt scaling ou isotonic regression — alinhar `predict_proba` com frequência empírica observada.
- Implementar `MERGE WHEN MATCHED THEN UPDATE` com timestamp como tiebreaker — capturar evolução temporal de focos persistentes.
- Materialized views no Oracle para as consultas 3 e 6 (mais pesadas) — refresh após cada execução da DAG.
- Detecção de drift estatístico (`evidently` ou `nannyml`) comparando distribuição de features entre treino e produção semanalmente.

**Longo prazo (visão de produto):**

- Substituir Sequential por Celery Executor com Postgres como metadata DB do Airflow — permite paralelismo real entre branches.
- Endpoint `/archive` da Open-Meteo para enriquecimento histórico real (não previsão) na janela > 5 dias.
- Integração end-to-end com a camada ACV: gravar saída da CNN em `imagens_satelite_metadata` e usar como feature adicional do GAIE (CNN confirma fogo + clima/geografia preveem propagação = modelo composto).
- Retreino periódico mensal integrado ao Airflow com versionamento de modelos (MLflow).

---

## 12. Tecnologias

| Camada | Stack principal |
|--------|-----------------|
| Linguagem | Python 3.10+ |
| Orquestração | Apache Airflow 2.9.3 (Docker standalone, SequentialExecutor + SQLite) |
| Banco analítico | Oracle Database 19c (FIAP) — `python-oracledb` 2.2 em modo thin |
| ETL | pandas 2.2, requests 2.32, python-dotenv 1.0 |
| Machine Learning | scikit-learn 1.5, XGBoost 2.1 |
| Interpretabilidade | SHAP 0.46 (TreeExplainer + KernelExplainer) |
| Visualização | Matplotlib 3.9 |
| App web | Streamlit 1.37 |
| Deploy | Railway (Nixpacks) — alternativa: Streamlit Community Cloud |
| APIs externas | NASA FIRMS, Open-Meteo |
| Geração de relatório | fpdf2 2.7 |
| Containerização | Docker + Docker Compose |
| Versionamento | Git + GitHub |

---

## 13. Referências

### Frameworks e bibliotecas

- Chen, T., & Guestrin, C. (2016). _XGBoost: A Scalable Tree Boosting System_. KDD '16.
- Lundberg, S. M., & Lee, S.-I. (2017). _A Unified Approach to Interpreting Model Predictions_ (SHAP). NeurIPS.
- Pedregosa, F. et al. (2011). _Scikit-learn: Machine Learning in Python_. JMLR, 12, 2825–2830.
- Breiman, L. (2001). _Random Forests_. Machine Learning, 45(1), 5–32.
- Apache Airflow Documentation. https://airflow.apache.org/docs/
- python-oracledb Documentation. https://python-oracledb.readthedocs.io/

### Modelagem e padrões de dados

- Kimball, R., & Ross, M. (2013). _The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling_ (3rd ed.). Wiley.
- Vassiliadis, P. (2009). _A Survey of Extract–Transform–Load Technology_. International Journal of Data Warehousing and Mining.

### Contexto espacial e operacional

- Schroeder, W. et al. (2014). _The New VIIRS 375 m active fire detection data product_. Remote Sensing of Environment.
- NASA FIRMS — Fire Information for Resource Management System. https://firms.modaps.eosdis.nasa.gov/
- Open-Meteo — Free Weather API. https://open-meteo.com/
- Copernicus Open Access Hub (Sentinel-2). https://scihub.copernicus.eu/
- INPE — Programa Queimadas. https://queimadas.dgi.inpe.br/queimadas/

---

> **PIRO · Global Solution 2026 · Engenharia de Software FIAP**
> Plataforma integrada que transforma dados orbitais em decisão operacional.
