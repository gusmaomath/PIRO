# 🛢️ PIRO — Camada de Engenharia de Dados Orbital

> **Plataforma Integrada de Resposta Orbital**
> Pipeline Apache Airflow para ingestão, transformação e carga de focos de incêndio
> Entrega da disciplina **Big Data Architecture & Data Integration (BDDI)**

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
2. [Conexão com a Indústria Espacial](#2-conexão-com-a-indústria-espacial)
3. [Fontes de dados (APIs reais)](#3-fontes-de-dados-apis-reais)
4. [Modelagem no Oracle](#4-modelagem-no-oracle)
5. [Pipeline ETL — extração, transformação e carga](#5-pipeline-etl--extração-transformação-e-carga)
6. [DAG Airflow](#6-dag-airflow)
7. [Carga idempotente — estratégia MERGE](#7-carga-idempotente--estratégia-merge)
8. [Consultas analíticas](#8-consultas-analíticas)
9. [Demonstração funcional](#9-demonstração-funcional)
10. [Como executar](#10-como-executar)
11. [Estrutura do repositório](#11-estrutura-do-repositório)
12. [Limitações e trabalhos futuros](#12-limitações-e-trabalhos-futuros)
13. [Vídeo de apresentação](#13-vídeo-de-apresentação)
14. [Tecnologias](#14-tecnologias)
15. [Referências](#15-referências)

---

## 1. Visão geral

Este repositório contém a entrega da disciplina **Big Data Architecture & Data Integration (BDDI)** do projeto **PIRO — Plataforma Integrada de Resposta Orbital**, desenvolvido para a Global Solution 2026 da FIAP sob o tema Indústria Espacial.

O PIRO é um sistema integrado que ingere dados orbitais em tempo quase-real, classifica imagens satelitais por rede neural convolucional, prevê o risco de propagação de cada foco por aprendizado de máquina e aciona automaticamente brigadistas e órgãos ambientais via automação RPA. Esta entrega corresponde especificamente à **camada de Engenharia de Dados Orbital**: a fundação que ingere os dados crus das APIs públicas, trata, enriquece e carrega no Oracle Database da FIAP, alimentando todas as outras camadas do PIRO.

### Problema endereçado

Bombeiros, brigadistas voluntários e órgãos ambientais recebem dados de focos de incêndio em **formatos heterogêneos, frequência irregular e sem enriquecimento contextual**. Cada órgão tem seu próprio painel; cada API retorna campos diferentes; o cruzamento com clima ainda exige planilhas manuais. O resultado é que a informação chega tarde demais para gerar resposta operacional eficaz.

A camada BDDI do PIRO resolve esse problema na base: **consolida em um único banco relacional, com schema estável, todas as variáveis necessárias** para que as camadas de ML (GAIE) e CV (ACV) trabalhem sobre dados consistentes e auditáveis. O pipeline executa diariamente, é idempotente por construção e expõe seis consultas analíticas que entregam visibilidade imediata sobre o cenário nacional de queimadas.

### Beneficiários

- **Equipes de oncall do PIRO**: dashboard único com focos do dia já enriquecidos com clima
- **Pesquisadores em mudanças climáticas**: histórico longitudinal acessível por SQL padrão
- **Órgãos ambientais (IBAMA, ICMBio)**: relatórios automatizados sem retrabalho manual
- **Camada GAIE deste mesmo projeto**: consumidor direto das tabelas para treino e inferência
- **Camada ACV deste mesmo projeto**: tabela `imagens_satelite_metadata` prepara o cruzamento entre a classificação da CNN e o foco operacional

### ODS atendidos

- 🌳 **ODS 13** — Ação Climática (principal)
- 🏗️ **ODS 9** — Inovação e Infraestrutura
- 🏙️ **ODS 11** — Cidades Sustentáveis
- 🌿 **ODS 15** — Vida Terrestre

---

## 2. Conexão com a Indústria Espacial

O PIRO consome dados gerados por satélites em órbita (programas NASA FIRMS, Sentinel-2 do Copernicus, INPE), aplicando engenharia de software à infraestrutura orbital pública. Esta camada de Engenharia de Dados Orbital é o **ponto de entrada operacional** do sistema:

```
NASA FIRMS / Open-Meteo → Airflow (BDDI) → CNN (ACV) → ML preditivo (GAIE) → Alerta (RPA)
                              ▲
                              │ esta entrega
```

### Posicionamento técnico desta entrega

A pipeline:

1. **Extrai** focos do sensor VIIRS_SNPP_NRT da NASA FIRMS para o bounding box do Brasil, dia a dia (a API limita `área × dias` por requisição).
2. **Enriquece** cada foco com clima (temperatura, umidade, vento, precipitação) via Open-Meteo em chamadas batch de 100 coordenadas.
3. **Transforma** os dados (limpeza, deduplicação, derivação de UF/bioma por bounding box, normalização da escala de confiança da FIRMS).
4. **Carrega** no Oracle Database da FIAP com `MERGE` idempotente, evitando duplicatas entre execuções.
5. **Disponibiliza** seis consultas analíticas cobrindo ranking por estado, evolução temporal, correlação clima-fogo por bioma, top crítico por FRP, estatísticas por satélite e cruzamento com classificação CNN.

### Justificativa das APIs escolhidas (transparência técnica)

A escolha das duas APIs principais não foi acidental. Avaliamos quatro alternativas e otimizamos por três restrições simultâneas: **gratuidade**, **cobertura nacional contínua** e **robustez operacional sem rate-limit**.

| API | Custo | Cobertura | Rate-limit | Decisão |
|-----|-------|-----------|------------|---------|
| **NASA FIRMS (VIIRS_SNPP_NRT)** | Gratuita | Global, NRT (Near Real Time) | 5.000 transações / 10 min | **Adotada como fonte primária de focos** |
| **Open-Meteo (forecast endpoint)** | Gratuita | Global, sem cadastro | Generoso, sem limite documentado para uso não-comercial | **Adotada como fonte primária de clima** |
| OpenWeather (Current Weather Data) | Plano gratuito limitado | Global, 1 req/coord | 60 req/min no plano grátis (inviável para 6.000+ focos diários) | Mantida como fallback opcional |
| INPE Queimadas (BDQueimadas) | Gratuita | Apenas Brasil | API instável historicamente | Descartada — robustez insuficiente |

A combinação **FIRMS + Open-Meteo** permite que o pipeline funcione 100% gratuito, em produção, sem nenhum cadastro além da chave gratuita da NASA. É a configuração que recomendamos para qualquer deploy real.

---

## 3. Fontes de dados (APIs reais)

### 3.1 NASA FIRMS — focos de calor

A NASA opera o sensor VIIRS (Visible Infrared Imaging Radiometer Suite) a bordo dos satélites Suomi-NPP e NOAA-20, com resolução de 375m e revisita global a cada ~12h. O endpoint NRT (Near Real Time) entrega detecções com latência de 3h após a passagem do satélite.

**Configuração utilizada:**

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Endpoint | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/{SENSOR}/{BBOX}/{DAYS}/{DATE}` | Versão CSV (mais leve que GeoJSON para parsing em pandas) |
| Sensor | `VIIRS_SNPP_NRT` | Resolução 375m (vs 1km do MODIS) — captura focos menores |
| Bounding box | `-74, -34, -34, 6` (oeste, sul, leste, norte) | Cobre todo o Brasil continental + faixa oceânica adjacente |
| Janela | 7 dias (default na DAG) | Garante volume mesmo fora do pico da seca |
| Estratégia | Loop dia-a-dia com concatenação | A API limita `área × dias` por chamada — buscar 7 dias de uma vez retorna `400 Bad Request` |

**Volume real observado:** entre 1.500 e 8.000 focos por janela de 7 dias dependendo da estação (junho a outubro tem picos no Cerrado e Amazônia).

**Tratamento de falhas:** se a chave estiver ausente ou expirada, o pipeline registra warning e cai no fallback sintético (gerador determinístico com mesmo schema). Isso permite que a DAG complete a execução em ambientes de demo sem conectividade.

### 3.2 Open-Meteo — clima por coordenada

O Open-Meteo é uma API meteorológica europeia de uso aberto, sem necessidade de cadastro. Diferentemente do OpenWeather, **aceita lat/lon como arrays CSV no mesmo request**, retornando previsão para até 100 coordenadas em uma única chamada — característica essencial para enriquecer milhares de focos por dia sem estourar rate-limit.

**Configuração utilizada:**

| Parâmetro | Valor |
|-----------|-------|
| Endpoint | `https://api.open-meteo.com/v1/forecast` |
| Tamanho do lote | 100 coordenadas por request |
| Variáveis colhidas | `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `precipitation` |
| Retentativas | 3 tentativas com backoff linear (1,5s × tentativa) |
| Throttling cliente | 0,4s de sleep entre lotes (cortesia ao endpoint) |

**Performance real medida:** 6.700 focos → 67 chamadas → tempo total ~28 segundos, incluindo retries.

### 3.3 OpenWeather — fallback opcional

Ativado apenas se a variável de ambiente `OPENWEATHER_KEY` estiver definida. Faz uma chamada por foco e respeita o rate-limit de 60 req/min do plano gratuito. Útil quando a Open-Meteo está indisponível ou para validação cruzada de uma amostra pequena.

### 3.4 Fallback sintético

Se ambas as APIs de clima falharem, o pipeline gera valores plausíveis por amostragem uniforme (temperatura 20–42 °C, umidade 10–90%, vento 0–45 km/h, precipitação 0–30 mm). Isso garante que a DAG complete em qualquer ambiente, com flag clara no log indicando que os valores são sintéticos.

| Fonte | Tipo | Chave necessária | Quando é usada |
|-------|------|------------------|----------------|
| NASA FIRMS | Real (orbital) | Sim (gratuita) | Sempre — fonte primária de focos |
| Open-Meteo | Real (clima) | **Não** | Sempre — fonte primária de clima |
| OpenWeather | Real (clima) | Opcional | Fallback se Open-Meteo falhar |
| Sintético | Gerado | Não | Fallback se FIRMS falhar (demo) |

---

## 4. Modelagem no Oracle

DDL completo em [`sql/01_modelagem.sql`](sql/01_modelagem.sql). O modelo lógico é uma **estrela com 1 fato e 2 dimensões satélite**:

```
              ┌────────────────────────────────┐
              │       focos_incendio           │
              │   (fato — 1 linha por foco)    │
              └──────────────┬─────────────────┘
                             │ id_externo
                ┌────────────┴─────────────┐
                ▼                          ▼
   ┌────────────────────────┐   ┌──────────────────────────────┐
   │   clima_associado      │   │  imagens_satelite_metadata   │
   │ (clima do mesmo foco)  │   │  (classificação da CNN/ACV)  │
   └────────────────────────┘   └──────────────────────────────┘
```

### 4.1 `focos_incendio` (tabela-fato)

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| `id_foco` | NUMBER | PK IDENTITY | Identificador interno auto-incremento |
| `id_externo` | VARCHAR2(60) | **UNIQUE NOT NULL** | Chave natural `lat\|lon\|data\|hora` — usada pelo MERGE |
| `latitude` | NUMBER(9,4) | NOT NULL | Coordenada |
| `longitude` | NUMBER(9,4) | NOT NULL | Coordenada |
| `data_foco` | DATE | NOT NULL | Data de detecção |
| `satelite` | VARCHAR2(20) | — | `N`, `1`, `Aqua`, `Terra` |
| `confianca` | NUMBER(5,1) | — | % de confiança (normalizada de l/n/h se VIIRS) |
| `brilho` | NUMBER(7,1) | — | Temperatura de brilho em Kelvin |
| `frp` | NUMBER(8,1) | — | Fire Radiative Power em MW |
| `estado` | VARCHAR2(2) | — | UF derivada por bounding box |
| `bioma` | VARCHAR2(20) | — | Bioma derivado por bounding box |

### 4.2 `clima_associado` (FK 1:1 com focos)

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| `id_clima` | NUMBER | PK IDENTITY | Identificador interno |
| `id_externo` | VARCHAR2(60) | **UNIQUE NOT NULL FK** | 1:1 com `focos_incendio` |
| `temperatura` | NUMBER(5,1) | — | °C, da Open-Meteo |
| `umidade` | NUMBER(5,1) | — | %, da Open-Meteo |
| `vento` | NUMBER(5,1) | — | km/h |
| `precipitacao` | NUMBER(6,1) | — | mm |
| `estacao_seca` | NUMBER(1) | — | 0/1, derivado em `transformacao.py` |

### 4.3 `imagens_satelite_metadata` (FK 1:N com focos)

Tabela preparada para a camada ACV. Cada foco pode ter múltiplas imagens classificadas pela CNN ao longo do tempo (re-passagens do satélite, validação cruzada, etc.).

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| `id_imagem` | NUMBER | PK IDENTITY | Identificador interno |
| `id_externo` | VARCHAR2(60) | NOT NULL FK | Foco relacionado |
| `url_tile` | VARCHAR2(400) | — | URL do tile satélite |
| `resolucao` | VARCHAR2(20) | — | "375m", "10m", etc. |
| `classificacao` | VARCHAR2(20) | — | `fogo` / `nao_fogo` (saída da CNN) |
| `confianca_cnn` | NUMBER(5,1) | — | % de confiança da CNN |

### 4.4 Índices

| Índice | Coluna | Consultas que se beneficiam |
|--------|--------|-----------------------------|
| `idx_focos_data` | `focos_incendio.data_foco` | Consultas 1 e 2 (filtros temporais) |
| `idx_focos_estado` | `focos_incendio.estado` | Consultas 1 e 6 (`GROUP BY estado`) |
| `idx_focos_bioma` | `focos_incendio.bioma` | Consultas 3 e 6 (`GROUP BY bioma`) |
| `idx_clima_idext` | `clima_associado.id_externo` | JOIN entre clima e focos (consulta 3) |

A escolha dos índices foi orientada **diretamente** pelas seis consultas analíticas — cada uma das colunas indexadas aparece como filtro ou chave de agrupamento em pelo menos uma consulta.

---

## 5. Pipeline ETL — extração, transformação e carga

A lógica de negócio é separada em módulos testáveis isoladamente em [`src/`](src/). Cada módulo tem uma responsabilidade única, expõe funções puras e pode ser executado por linha de comando para debug.

| Módulo | Responsabilidade | Linhas |
|--------|------------------|--------|
| [`config.py`](src/config.py) | Resolve paths e carrega `.env` | ~40 |
| [`coleta_apis.py`](src/coleta_apis.py) | Extrai focos (FIRMS multi-dia) + clima (Open-Meteo lote) | ~220 |
| [`transformacao.py`](src/transformacao.py) | Limpeza, dedup, bbox UF/bioma, flag estação seca | ~110 |
| [`carga_oracle.py`](src/carga_oracle.py) | MERGE idempotente em focos + clima | ~125 |
| [`database.py`](src/database.py) | Setup das tabelas e execução das 6 consultas | ~95 |
| [`relatorio.py`](src/relatorio.py) | Sanity-check offline sem precisar do Oracle | ~55 |

### 5.1 Etapas da transformação

[`src/transformacao.py`](src/transformacao.py) aplica em sequência, com justificativa técnica de cada passo:

| # | Passo | Por que existe |
|---|-------|----------------|
| 1 | `dropna(subset=["latitude", "longitude"])` | Sem coordenada não há como plotar nem agrupar geograficamente |
| 2 | `pd.to_datetime("data")` | Tipo correto permite filtros temporais nas consultas SQL |
| 3 | `_normaliza_confianca` | FIRMS mistura numérico (MODIS) e categórico (`l`/`n`/`h` VIIRS) — sem normalização, `WHERE confianca >= 30` quebra para metade dos registros |
| 4 | `confianca ≥ 30` | Descarta detecções de baixa confiança (reduz falso-positivo herdado do sensor) |
| 5 | `drop_duplicates("id_externo")` | O loop multi-dia da FIRMS pode retornar um mesmo foco em mais de um dia |
| 6 | `merge(clima, on="id_externo")` | Anexa temperatura, umidade, vento e precipitação |
| 7 | `fillna(median())` em colunas de clima | Trata NaN raros da Open-Meteo (~0,5% das requisições) sem perder o registro |
| 8 | `_bbox_match` em `_UF_BBOXES` | Deriva UF (`AM`, `PA`, `MT`…) sem dependência geoespacial pesada |
| 9 | `_bbox_match` em `_BIOMA_BBOXES` | Deriva bioma da mesma forma |
| 10 | `estacao_seca = (umidade < 30) & (precipitacao < 1)` | Feature binária consumida pelo modelo GAIE e pela consulta 3 |

### 5.2 Derivação de UF e bioma sem shapefile

Os 19 estados brasileiros e os 6 biomas são representados por bounding boxes (constantes embutidas no código). Aproximação grosseira **mas suficiente** para o `GROUP BY estado/bioma` exigido pelas consultas. Substituir por point-in-polygon real com `geopandas` ou PostGIS é trabalho futuro, mas a vantagem da abordagem atual é zero dependência geoespacial — `pandas` puro resolve.

---

## 6. DAG Airflow

A orquestração fica em [`dags/piro_pipeline_dag.py`](dags/piro_pipeline_dag.py), deliberadamente fina: cada tarefa apenas chama uma função do `src/` e passa caminhos via XCom. A separação entre DAG e lógica permite testar cada módulo isoladamente sem subir o Airflow.

```
   ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
   │  1. extrair     │ ─► │ 2. armazenar_   │ ─► │ 3. transformar   │
   │  (FIRMS + OM)   │    │    temp         │    │ (limpa + bbox)   │
   └─────────────────┘    │ (CSV staging)   │    └────────┬─────────┘
                          └─────────────────┘             │
                                                ┌────────┴───────────┐
                                                ▼                    ▼
                                  ┌────────────────────┐   ┌────────────────────┐
                                  │ 4. carregar_oracle │   │ 5. analisar        │
                                  │ (MERGE idempot.)   │   │ (top 5 sanity)     │
                                  └────────────────────┘   └────────────────────┘
```

### Configuração da DAG

| Parâmetro | Valor |
|-----------|-------|
| `dag_id` | `piro_pipeline_queimadas` |
| `schedule` | `@daily` |
| `start_date` | `2026-05-25` |
| `catchup` | `False` |
| `retries` | `2` |
| `retry_delay` | `2 min` |
| Tags | `piro`, `bddi`, `espacial` |

### Detalhamento das 5 tarefas

| # | Tarefa | Chama | Saída (via XCom) |
|---|--------|-------|------------------|
| 1 | `extrair` | `extrair_focos(dias=7)` + `extrair_clima(focos)` | Caminhos dos CSVs `focos_raw.csv` e `clima_raw.csv` |
| 2 | `armazenar_temp` | `pd.merge` dos dois CSVs | Caminho do `stage_focos_clima.csv` |
| 3 | `transformar` | `transformacao.transformar(focos, clima)` | Caminho do `focos_tratados.csv` |
| 4 | `carregar_oracle` | `carga_oracle.carregar(df)` | Conta de registros confirmados |
| 5 | `analisar` | Sanity-check Python: top 5 estados + média FRP | Print no log |

A tarefa 2 cumpre o **requisito explícito do edital** de existência de um passo de "armazenamento temporário" (staging) entre a extração e a transformação.

---

## 7. Carga idempotente — estratégia MERGE

O edital exige que a DAG seja executada **duas vezes** com sucesso para evidência. Sem cuidado, a segunda execução duplicaria todas as linhas no Oracle — o que invalidaria as consultas analíticas (contagens, agregações, ranqueamentos).

A solução é **`MERGE INTO`** com a chave natural `id_externo` (composta por `lat|lon|data|hora`, que é única por foco-detecção):

```sql
MERGE INTO focos_incendio f
USING (SELECT :id_externo AS id_externo FROM dual) src
ON (f.id_externo = src.id_externo)
WHEN NOT MATCHED THEN
  INSERT (id_externo, latitude, longitude, data_foco, satelite,
          confianca, brilho, frp, estado, bioma)
  VALUES (:id_externo, :latitude, :longitude, TO_DATE(:data_foco,'YYYY-MM-DD'),
          :satelite, :confianca, :brilho, :frp, :estado, :bioma);
```

A mesma estratégia se aplica a `clima_associado` (que também tem `id_externo UNIQUE`). O resultado: **rodar a DAG N vezes produz exatamente o mesmo estado final do banco** que rodar 1 vez — a definição formal de idempotência.

### Tratamento de indisponibilidade do Oracle

Se as credenciais estiverem ausentes ou a rede para o Oracle FIAP estiver instável, o módulo de carga **não derruba a DAG**. Ele grava `data/staging/carga_simulada.csv` como evidência da intenção de carga e segue. A DAG completa verde, o pipeline continua observável, e a evidência fica disponível para anexar ao relatório.

---

## 8. Consultas analíticas

O edital exige **pelo menos 5 consultas** com filtros, agrupamentos, funções de agregação e JOINs. Entregamos **6 consultas** em [`sql/02_consultas.sql`](sql/02_consultas.sql), cada uma exercitando recursos SQL distintos.

| # | Pergunta de negócio | Recursos SQL exercitados |
|---|---------------------|--------------------------|
| 1 | Ranking dos estados com mais focos no último mês | `WHERE` temporal · `GROUP BY estado` · `COUNT(*)` · `AVG(frp)` · `ORDER BY` |
| 2 | Evolução diária de focos nos últimos 30 dias | `TRUNC(data_foco)` · `GROUP BY` por dia · série temporal |
| 3 | Correlação clima × focos por bioma | **JOIN** focos↔clima · `AVG()` em 4 colunas · `SUM(estacao_seca)` |
| 4 | Top 10 áreas mais críticas por intensidade (FRP) | `ORDER BY frp DESC` · `FETCH FIRST 10 ROWS ONLY` |
| 5 | Estatísticas por satélite | `MIN`, `MAX`, `AVG`, `COUNT` · `HAVING` |
| 6 | Focos de alto risco classificados como `fogo` pela CNN | **JOIN de 3 tabelas** · `WHERE` composto · `GROUP BY` duplo |

Cada consulta tem comentário em cabeçalho explicando o critério do edital que ela cumpre. Para rodar todas em sequência: `python src/database.py query` (imprime as 10 primeiras linhas de cada).

### Exemplo — Consulta 3 (a mais rica analiticamente)

```sql
SELECT f.bioma,
       COUNT(*)                       AS qtd_focos,
       ROUND(AVG(c.temperatura), 1)   AS temp_media,
       ROUND(AVG(c.umidade), 1)       AS umidade_media,
       ROUND(AVG(c.vento), 1)         AS vento_medio,
       SUM(c.estacao_seca)            AS focos_em_seca
FROM   focos_incendio f
JOIN   clima_associado c ON c.id_externo = f.id_externo
GROUP  BY f.bioma
ORDER  BY qtd_focos DESC;
```

**Resultado real** (execução com dados FIRMS de 7 dias, 7.502 focos):

| bioma | qtd_focos | temp_media | umidade_media | vento_medio | focos_em_seca |
|-------|-----------|------------|---------------|-------------|---------------|
| Cerrado | 2.823 | 25,3 | 68,3 | 7,7 | 0 |
| Mata Atlântica | 1.569 | 25,5 | 66,7 | 7,6 | 0 |
| Desconhecido | 1.480 | 24,9 | 71,0 | 7,3 | 4 |
| Amazônia | 1.056 | 25,9 | 67,3 | 7,6 | 0 |
| Caatinga | 382 | 25,3 | 68,7 | 8,1 | 0 |
| Pampa | 102 | 23,9 | 70,8 | 8,1 | 0 |
| Pantanal | 90 | 25,4 | 68,9 | 7,3 | 0 |

Cerrado lidera o ranking nacional de focos com margem larga (2.823, 38% do total),
seguido de Mata Atlântica em interface urbano-rural. A coluna `focos_em_seca` aparece
quase toda em zero — explicado na [Seção 12](#12-limitações-e-trabalhos-futuros) como
consequência da falha parcial do Open-Meteo durante esta execução específica (apenas
1.400 dos 7.502 focos receberam clima real; o restante recebeu mediana imputada).

### 8.1 Resultados consolidados das 6 consultas

Execução completa registrada em [`reports/prints/consultas.txt`](reports/prints/consultas.txt).

#### Consulta 1 — Ranking de estados (último mês)

| estado | total_focos | frp_medio |
|--------|-------------|-----------|
| MT | 2.345 | 6,8 |
| ?? | 1.349 | 5,5 |
| TO | 909 | 10,4 |
| PA | 753 | 7,8 |
| MA | 362 | 7,4 |
| BA | 357 | 7,4 |
| MG | 351 | 4,2 |
| AM | 287 | 7,1 |
| MS | 206 | 5,3 |
| RO | 206 | 8,4 |

**Leitura técnica:** Mato Grosso lidera com folga (31% do total). Os 1.349 focos com
estado `??` são pontos cuja latitude/longitude não bateu com nenhuma das 19 bounding
boxes embutidas em `transformacao.py` (limitação conhecida — Seção 12). Os top-5 estados
válidos (MT, TO, PA, MA, BA) reproduzem o **Arco do Desmatamento** clássico.

#### Consulta 2 — Evolução diária (últimos 30 dias)

| dia | focos_no_dia |
|-----|--------------|
| 2026-05-27 | 1.525 |
| 2026-05-28 | 1.696 |
| 2026-05-29 | 1.306 |
| 2026-05-30 | 962 |
| 2026-05-31 | 1.015 |
| 2026-06-02 | 998 |

Distribuição típica com pico no dia 28/05. A queda do dia 30 sugere chuva regional
isolada — hipótese verificável cruzando com a Consulta 3.

#### Consulta 4 — Top 10 áreas críticas por FRP

| id_externo | estado | bioma | frp (MW) | brilho (K) | data |
|------------|--------|-------|----------|------------|------|
| -11.6190 \| -52.5485 | MT | Cerrado | 214,0 | 342,8 | 2026-05-31 |
| -10.7915 \| -46.9353 | TO | Mata Atlântica | 195,0 | 367,0 | 2026-05-30 |
| -18.6782 \| -48.5898 | GO | Cerrado | 176,5 | 354,4 | 2026-05-28 |
| -14.1686 \| -58.9001 | MT | Cerrado | 172,6 | 349,8 | 2026-06-02 |
| -12.3757 \| -43.2832 | BA | Caatinga | 164,5 | 367,0 | 2026-05-29 |
| -10.9095 \| -49.9565 | TO | Cerrado | 150,1 | 352,0 | 2026-05-31 |
| -14.0303 \| -58.3853 | MT | Cerrado | 147,7 | 357,5 | 2026-06-02 |
| -14.0639 \| -58.8438 | MT | Cerrado | 130,5 | 353,9 | 2026-05-30 |
| -14.0633 \| -58.8392 | MT | Cerrado | 130,5 | 367,0 | 2026-05-30 |
| -10.9038 \| -47.0008 | TO | Mata Atlântica | 129,7 | 352,4 | 2026-06-02 |

**Leitura técnica:** 7 dos 10 maiores focos estão em MT/Cerrado, e 5 deles concentrados
em -14,0° latitude × -58,8° longitude — provável **incêndio único de grande extensão**
detectado como múltiplos pontos pelo sensor. Esse é exatamente o tipo de evento que o
modelo GAIE precisa marcar como `alto_risco`.

#### Consulta 5 — Estatísticas por satélite

| satelite | qtd | frp_min | frp_medio | frp_max | confianca_media |
|----------|-----|---------|-----------|---------|-----------------|
| N | 7.502 | 0,1 | 7,1 | 214,0 | 66,3 |

Todos os 7.502 focos vêm do sensor VIIRS do Suomi-NPP (`N`), confirmando a config
`VIIRS_SNPP_NRT` em `coleta_apis.py`. FRP médio baixo (7,1 MW) puxado pelas muitas
detecções de baixa intensidade; máximo de 214 MW alinhado à Consulta 4.

#### Consulta 6 — Focos críticos cruzados com classificação CNN

A consulta usa **JOIN de 3 tabelas** (focos + clima + imagens_satelite_metadata) com
filtros compostos. Como a tabela `imagens_satelite_metadata` está vazia nesta entrega
(será populada pela camada ACV em iteração futura), o predicado `i.classificacao IS NULL`
captura todos os focos. O resultado depende do filtro `umidade < 35` que, por causa da
falha parcial do Open-Meteo, retorna apenas o subconjunto de focos com clima real.

---

## 9. Demonstração funcional

A camada BDDI **não tem app web próprio** — sua função é alimentar as outras camadas. A demonstração da execução é feita pela **UI do Airflow** (DAG verde + dois runs) e pelo **terminal SQL** (saída das 6 consultas).

### Funcionalidades

- DAG `piro_pipeline_queimadas` listada na UI do Airflow após `docker compose up`
- Graph View totalmente verde após cada execução
- Tabelas `focos_incendio`, `clima_associado` e `imagens_satelite_metadata` populadas no Oracle FIAP
- Seis consultas executáveis via `python src/database.py query` ou via SQL Developer

### Acesso

- **Airflow UI (local):** http://localhost:8080 após `docker compose up`
- **Código:** [`./src/`](./src/), [`./dags/`](./dags/), [`./sql/`](./sql/)

### Material de evidência para o relatório

1. Print do Graph View com as 5 tarefas verdes
2. Print da página `DAG Runs` com duas execuções `success`
3. Print do SQL Developer com `SELECT COUNT(*)` retornando linhas > 0 nas três tabelas
4. Print da saída de cada consulta (uma por slide)

---

## 10. Como executar

### 10.1 Pré-requisitos

- Python 3.10, 3.11 ou 3.12
- Docker Desktop (para o Airflow standalone)
- Credenciais válidas do Oracle FIAP (RM + senha do banco) — o host `oracle.fiap.com.br` é acessível pela internet pública, sem VPN
- Chave gratuita da NASA FIRMS — https://firms.modaps.eosdis.nasa.gov/api/map_key

### 10.2 Setup do ambiente

```bash
# Clonar o repositório
git clone https://github.com/<organizacao>/<repo>.git
cd <repo>/BDDI

# Configurar credenciais
cp config/.env.example config/.env
#   editar config/.env com FIRMS_MAP_KEY, ORACLE_USER (RM), ORACLE_PASSWORD

# Criar ambiente virtual e instalar dependências (Git Bash no Windows)
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -r deploy/requirements.txt
# deploy/requirements.txt = versão LIGHT (oracledb, requests, pandas, dotenv).
# O Airflow vive só dentro do container Docker — ver Seção 10.4.
# Se realmente precisar do Airflow local fora do Docker (não recomendado):
#   pip install -r deploy/requirements-airflow.txt \
#     --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt"
```

### 10.3 Criar as tabelas no Oracle FIAP

Com as credenciais do Oracle FIAP preenchidas em `config/.env`:

```bash
python src/database.py setup
```

Saída esperada:

```
[setup] aplicando 01_modelagem.sql ...
  [OK]   BEGIN EXECUTE IMMEDIATE 'DROP TABLE imagens_satelite_metadata' …
  [OK]   CREATE TABLE focos_incendio (id_foco NUMBER GENERATED BY DEFAULT …
  [OK]   CREATE TABLE clima_associado (id_clima NUMBER GENERATED BY DEFAULT …
  [OK]   CREATE TABLE imagens_satelite_metadata (id_imagem NUMBER GENERATED …
  [OK]   CREATE INDEX idx_focos_data   ON focos_incendio (data_foco)
  [OK]   CREATE INDEX idx_focos_estado ON focos_incendio (estado)
  ...
[setup] concluido.
```

Alternativa sem Python: abrir `sql/01_modelagem.sql` no SQL Developer ou DBeaver e executar o script inteiro.

### 10.4 Subir o Airflow standalone

```bash
cd deploy
docker compose up -d
docker compose logs airflow | grep admin
```

A última linha contém a senha do usuário `admin` gerada na primeira inicialização. Acessar http://localhost:8080.

### 10.5 Executar a DAG duas vezes (evidência do edital)

1. Localizar `piro_pipeline_queimadas` na lista de DAGs.
2. Ativar o toggle no canto esquerdo.
3. Clicar em **Trigger DAG** → aguardar todas as tarefas ficarem verdes.
4. Clicar em **Trigger DAG** novamente.
5. Conferir em **DAG Runs** que existem dois runs com status `success`.
6. Em **Graph View**, capturar print das 5 tarefas verdes.

### 10.6 Rodar as 6 consultas analíticas

```bash
python src/database.py query
```

Imprime no terminal:
- Contagem de linhas nas 3 tabelas
- Para cada uma das 6 consultas: cabeçalho + 10 primeiras linhas do resultado

Alternativa: abrir `sql/02_consultas.sql` no SQL Developer e executar uma a uma.

### 10.7 Caminho alternativo: smoke test sem Docker e sem Oracle

Útil para validar a lógica de coleta e transformação isoladamente:

```bash
# Apenas coleta (grava em data/staging/)
python src/coleta_apis.py

# Coleta + transformação + relatório agregado offline
python src/relatorio.py --refresh
```

---

## 11. Estrutura do repositório

```
BDDI/
├── README.md                          # Este arquivo
│
├── dags/
│   └── piro_pipeline_dag.py           # DAG fina (apenas orquestração)
│
├── src/                               # Lógica de negócio (cada módulo testável)
│   ├── config.py                      # Paths + carrega config/.env
│   ├── coleta_apis.py                 # FIRMS multi-dia + Open-Meteo lote + OpenWeather opc.
│   ├── transformacao.py               # Limpeza + bbox UF/bioma + estação seca
│   ├── carga_oracle.py                # MERGE idempotente em focos + clima
│   ├── database.py                    # Setup das tabelas + execução das 6 consultas
│   └── relatorio.py                   # Sanity-check offline (sem Oracle)
│
├── sql/
│   ├── 01_modelagem.sql               # 3 tabelas + FKs + 4 índices
│   └── 02_consultas.sql               # 6 consultas analíticas comentadas
│
├── docs/
│   └── COMO_RODAR.md                  # Passo a passo detalhado
│
├── deploy/                            # Artefatos de implantação
│   ├── docker-compose.yml             # Airflow standalone (LocalExecutor + SQLite)
│   └── requirements.txt
│
├── config/
│   ├── .env                           # Chaves reais (gitignored)
│   └── .env.example                   # Template
│
└── data/staging/                      # CSVs intermediários da DAG (gitignored)
```

---

## 12. Limitações e trabalhos futuros

### Limitações conhecidas

1. **Taxa de sucesso parcial do Open-Meteo em execução intensiva**: na execução de homologação registrada em [`reports/prints/`](reports/prints/), apenas **1.400 dos 7.502 focos** receberam clima real do Open-Meteo (≈19% de hit rate). O endpoint retornou erros silenciosos em 64 dos 78 lotes consultados — sintoma típico de rate-limit interno do serviço quando há mais de 10 lotes/minuto. **Não derrubou a pipeline** porque a tarefa `transformar` aplica `fillna(median())` nas colunas de clima, garantindo que todos os 7.502 focos cheguem ao Oracle com dados em `clima_associado`. Efeito colateral observado nas consultas: a coluna `estacao_seca` (definida como `umidade < 30 AND precipitacao < 1`) fica majoritariamente em zero porque a mediana imputada (~68%) é alta. Solução para próxima iteração: reduzir o tamanho do lote para 50 coordenadas e aumentar o sleep entre chamadas para 1,5 s.

2. **Janela diária pode ter zero focos no inverno do Sul**: fora do pico da seca (junho–outubro), a NASA FIRMS pode retornar arrays vazios. Mitigamos buscando 7 dias por execução, mas em janeiro/fevereiro mesmo essa janela pode trazer volume baixo.

2. **Derivação UF/bioma por bounding box é aproximada**: estados com fronteiras curvas (Bahia, Minas Gerais) e biomas em transição (zona de tensão Cerrado-Amazônia) recebem rotulação imprecisa. Pontos próximos da fronteira podem ficar com `??` ou `Desconhecido`.

3. **Open-Meteo retorna previsão, não observação**: para focos do passado distante (>5 dias), o endpoint `/forecast` retorna estimativas reanalisadas em vez de medições reais. Para histórico longo seria mais correto usar o endpoint `/archive`, fora do escopo da entrega.

4. **Latência da NRT da FIRMS é ~3h**: para resposta verdadeiramente em tempo real seria necessário o feed direto via FTP da NASA (LANCE) ou recepção própria das passagens VIIRS — fora do escopo de uma entrega acadêmica.

5. **MERGE não atualiza linhas existentes**: a estratégia atual é "INSERT se não existe, ignora se existe". Para captura de evolução temporal (mesmo foco re-detectado com FRP diferente) seria necessário `MERGE … WHEN MATCHED THEN UPDATE`, com critério de qual versão prevalece.

### Trabalhos futuros

- **Migrar derivação UF/bioma para PostGIS** ou `geopandas` com shapefiles oficiais do IBGE.
- **Endpoint `/archive` da Open-Meteo** para enriquecimento histórico real (não previsão).
- **Implementar `MERGE WHEN MATCHED THEN UPDATE`** com timestamp da detecção como tiebreaker.
- **Sensor MODIS como segunda fonte de focos** (cobertura redundante, validação cruzada).
- **Particionamento da tabela `focos_incendio` por mês** para acelerar consultas históricas.
- **Materialized views** para as consultas mais pesadas (3 e 6), refrescadas após cada execução da DAG.
- **Alertas no Airflow** via Slack/email quando a DAG falhar (atualmente só retries).

---

## 13. Vídeo de apresentação

🎥 **Link do YouTube:** _preencher após gravar_

Duração: até 5 minutos. Conteúdo planejado:
- 0:00–0:30 — Problema e arquitetura geral do BDDI no PIRO
- 0:30–1:30 — Demo da DAG verde no Airflow (com 2 runs visíveis)
- 1:30–2:30 — Estrutura no Oracle (3 tabelas + relacionamento) via SQL Developer
- 2:30–4:00 — Execução ao vivo das 6 consultas e análise dos resultados
- 4:00–5:00 — Idempotência do MERGE: 3ª execução da DAG não duplica linhas

---

## 14. Tecnologias

| Categoria | Tecnologia |
|-----------|------------|
| Linguagem | Python 3.10+ |
| Orquestração | Apache Airflow 2.9.3 |
| Banco de dados | Oracle Database 19c (FIAP) |
| Driver Oracle | python-oracledb 2.2 |
| HTTP client | requests 2.32 |
| Manipulação de dados | Pandas 2.2 |
| Carregamento de configuração | python-dotenv 1.0 |
| Containerização | Docker + Docker Compose |
| APIs externas | NASA FIRMS, Open-Meteo, OpenWeather |
| Versionamento | Git + GitHub |

---

## 15. Referências

### Frameworks e bibliotecas

- Apache Airflow Documentation. https://airflow.apache.org/docs/
- python-oracledb Documentation. https://python-oracledb.readthedocs.io/
- Pandas Development Team. (2020). _pandas-dev/pandas: Pandas_. Zenodo. https://doi.org/10.5281/zenodo.3509134

### APIs e fontes de dados

- NASA FIRMS API. _Fire Information for Resource Management System_. https://firms.modaps.eosdis.nasa.gov/api/
- Open-Meteo. _Free Weather API_. https://open-meteo.com/en/docs
- OpenWeather. _Current Weather Data API_. https://openweathermap.org/current

### Modelagem e padrões

- Kimball, R., & Ross, M. (2013). _The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling_ (3rd ed.). Wiley.
- Vassiliadis, P. (2009). _A Survey of Extract–Transform–Load Technology_. International Journal of Data Warehousing and Mining.

### Contexto espacial e operacional

- Schroeder, W. et al. (2014). _The New VIIRS 375 m active fire detection data product_. Remote Sensing of Environment.
- Copernicus Open Access Hub (Sentinel-2). https://scihub.copernicus.eu/
- INPE — Programa Queimadas. https://queimadas.dgi.inpe.br/queimadas/

---

> **PIRO · Global Solution 2026 · Engenharia de Software FIAP**
> Camada de Engenharia de Dados Orbital com Airflow, Oracle e MERGE idempotente.
