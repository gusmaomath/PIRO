# 🛰️ PIRO — Plataforma Integrada de Resposta Orbital

Monorepo do projeto **FIAP Global Solution 2026 · 1º Semestre** — Indústria Espacial: *O Código que Move o Universo*.

PIRO ingere dados orbitais de focos de incêndio quase em tempo real, prevê o risco de propagação
em 24h via machine learning com interpretabilidade SHAP, e dispara alertas direcionados a
brigadistas e órgãos ambientais. Conecta-se ao **ODS 13 — Ação Climática** (principal) e aos
ODS 9, 11 e 15 (complementares).

## 👥 Integrantes

| Nome | RM |
|------|----|
| Matheus Gusmão | RM550826 |
| Guilherme Morais | RM551981 |
| Julia Marques | RM98680 |

---

## 📑 Sumário

1. [Problema real](#-problema-real)
2. [Solução PIRO](#-solução-piro)
3. [Conexão com a Indústria Espacial e ODS](#-conexão-com-a-indústria-espacial-e-ods)
4. [Arquitetura integrada](#-arquitetura-integrada)
5. [Contrato de dados (Oracle)](#-contrato-de-dados-oracle)
6. [Módulos deste repositório](#-módulos-deste-repositório)
7. [Como rodar — passo a passo](#-como-rodar--passo-a-passo)
8. [Conclusões técnicas e análise dos dados](#-conclusões-técnicas-e-análise-dos-dados)
9. [Dicas para nota máxima em BDDI e GAIE](#-dicas-para-nota-máxima-em-bddi-e-gaie)
10. [Estado das entregas](#-estado-das-entregas)
11. [Segurança](#-segurança)

---

## 🎯 Problema real

O Brasil registra mais de 200 mil focos de incêndio por ano (INPE). Satélites detectam esses focos
em tempo quase-real, mas a resposta operacional é lenta porque os dados chegam **sem priorização
automática por risco de propagação**. Focos pequenos viram grandes incêndios antes que haja ação
coordenada. O PIRO resolve a fila de prioridades.

## 💡 Solução PIRO

Sistema único que:
- **Ingere dados orbitais reais** (NASA FIRMS) e os enriquece com clima (Open-Meteo).
- **Trata em Python** e carrega de forma idempotente no Oracle Database da FIAP.
- **Prevê o risco** de propagação em 24h via ML (Random Forest e XGBoost), com explicabilidade SHAP.
- **Apresenta** o resultado num **app Streamlit** com gauge, explicação local da previsão e dashboard
  do dataset.

## 🌱 Conexão com a Indústria Espacial e ODS

- **Dados orbitais reais** — sensores MODIS e VIIRS em satélites em órbita baixa da NASA.
- **ODS 13 (Ação Climática)** principal — resposta rápida a queimadas reduz emissões.
- **ODS 9** Inovação e infraestrutura · **ODS 11** Cidades sustentáveis · **ODS 15** Vida terrestre.

## 🏗️ Arquitetura integrada

```
 Fontes orbitais (Camada 1)              Pipeline & Inteligência (Camada 2)
 ┌─────────────────────┐                 ┌──────────────────────────────────┐
 │ NASA FIRMS          │── focos ───────►│ BDDI: Airflow                    │
 │ (MODIS/VIIRS)       │                 │   extract → transform → load     │── Oracle DB
 │                     │                 │                                  │   (focos +
 │ Open-Meteo          │── clima ───────►│ GAIE: ML (RF + XGBoost) + SHAP   │    clima +
 │ (grátis, sem chave) │                 │   prevê alto_risco_24h           │    imagens)
 └─────────────────────┘                 └────────────┬─────────────────────┘
                                                      │
                                          Deploy & Ação (Camadas 3 e 4)
                                          ┌──────────────────────────────┐
                                          │ App Streamlit (GAIE)          │
                                          │ Alertas RPA > 70% prob        │
                                          │ Azure App Service (SDTCC)     │
                                          │ Pitch BISD (YouTube)          │
                                          └──────────────────────────────┘
```

Fluxo dos dados:
```
NASA FIRMS ─┐
            ├─► BDDI (Airflow + Oracle) ─► GAIE (RF + XGBoost + SHAP) ─► App Streamlit
Open-Meteo ─┘                                                            └► RPA alerta (>70%)
```

## 📊 Contrato de dados (Oracle)

3 tabelas relacionadas alimentadas pelo BDDI e consumidas pelo GAIE.

### `focos_incendio` (preenchida pelo BDDI a partir da NASA FIRMS)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_foco` | NUMBER, PK | Identificador sequencial (`seq_focos`) |
| `latitude` | NUMBER(9,6) | Latitude do foco |
| `longitude` | NUMBER(9,6) | Longitude do foco |
| `data_hora` | TIMESTAMP | UTC, combinando `acq_date` + `acq_time` da FIRMS |
| `satelite` | VARCHAR2(20) | `MODIS_AQUA`, `VIIRS_SNPP`, etc. |
| `confianca` | NUMBER(3) | 0–100 (MODIS) ou mapeado 25/65/95 (VIIRS l/n/h) |
| `brilho` | NUMBER(7,2) | Temperatura de brilho em K |
| `frp` | NUMBER(9,2) | Fire Radiative Power em MW |
| `estado` | VARCHAR2(2) | UF derivada por bounding box |
| `bioma` | VARCHAR2(30) | Bioma derivado por bounding box |

### `clima_associado` (FK → focos_incendio)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_clima` | NUMBER, PK | Identificador (`seq_clima`) |
| `id_foco` | NUMBER, FK | Referência ao foco |
| `temperatura` | NUMBER(5,2) | °C, da Open-Meteo |
| `umidade` | NUMBER(5,2) | % de umidade relativa |
| `vento` | NUMBER(5,2) | m/s (convertido de km/h) |
| `precipitacao` | NUMBER(5,2) | mm |

### `imagens_satelite_metadata` (FK → focos_incendio, preenchida pela ACV)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_imagem` | NUMBER, PK | Identificador (`seq_imagens`) |
| `id_foco` | NUMBER, FK | Referência ao foco |
| `url_tile` | VARCHAR2(500) | URL do tile satelital |
| `resolucao` | VARCHAR2(20) | Ex.: `128x128` |
| `classe_cnn` | VARCHAR2(10) | `fire` / `nofire` |
| `confianca_cnn` | NUMBER(5,4) | Confiança da CNN |

Índices: `data_hora`, `estado`, `bioma` em `focos_incendio` + `id_foco` em `clima_associado`.

## 📦 Módulos deste repositório

| Módulo | Disciplina | O que faz |
|--------|------------|-----------|
| [`BDDI/`](BDDI/) | **BDDI** | Pipeline Airflow: NASA FIRMS + Open-Meteo → Python → Oracle, com 6 consultas analíticas e MERGE idempotente |
| [`GAIE/`](GAIE/) | **GAIE** | ML preditivo (RF + XGBoost + MLP) com SHAP (summary + waterfall + bar) e app Streamlit com treino ao vivo |
| [`.github/workflows/`](.github/workflows/) | SDTCC | Esqueleto de CI/CD para Azure |

> As demais disciplinas (ACV, SDTCC, RPA, PBML, BISD) ficam com outros integrantes/equipes.

---

## 🚀 Como rodar — passo a passo

Cada módulo é autocontido com seu próprio `requirements.txt` e venv. **Comece pelo BDDI**, porque
o GAIE consome os dados que ele carrega no Oracle.

### Pré-requisitos
- **Python 3.12** (TensorFlow não importa aqui; sklearn/xgboost rodam em 3.12 sem problema).
- **Docker** (opcional — só se for subir o Airflow para os prints da DAG).
- **Credenciais Oracle FIAP** (RM + senha) e **chave da NASA FIRMS** (gratuita).

### 1️⃣ BDDI — Pipeline de dados

```bash
cd BDDI
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -r deploy/requirements.txt

# Preencher .env (NUNCA commitar) — modelo em config/.env.example
cp config/.env.example config/.env
# editar config/.env com FIRMS_MAP_KEY, OPENWEATHER_KEY (opcional),
# ORACLE_USER (RM) e ORACLE_PASSWORD

# Com config/.env preenchido (oracle.fiap.com.br e acessivel pela internet publica):
python src/database.py setup      # cria 3 tabelas + FKs + indices no Oracle FIAP
python src/relatorio.py --refresh # sanity-check offline (sem precisar do Oracle)
python src/database.py query      # roda as 6 consultas analiticas
```

Para o **Airflow** (gera os 2 prints da DAG verde exigidos pelo edital):
```bash
cd BDDI/deploy
docker compose up -d              # sobe Airflow em http://localhost:8080
docker compose logs airflow | grep admin    # pega a senha do admin
# habilitar a DAG `piro_pipeline_queimadas` e disparar 2 trigger manuais
```

### 2️⃣ GAIE — 3 modelos + SHAP + App Streamlit com treino ao vivo

```bash
cd GAIE
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -r deploy/requirements.txt

python src/gerar_dados.py         # gera data/focos_incendio.csv (3000 linhas)
python src/treino.py              # treina RF + XGBoost + MLP, salva metricas + SHAP

streamlit run src/app.py          # abre o app em http://localhost:8501
```

### Subir o app Streamlit em URL pública (10 pts do GAIE)

**Opção A — Railway (zero-config, recomendado):**
1. Suba o repositório pro GitHub.
2. Em https://railway.app → New Project → Deploy from GitHub repo.
3. Configure **Root Directory = `GAIE`**. O `nixpacks.toml` na raiz dela já
   diz ao builder: `pip install -r deploy/requirements.txt` + `streamlit run src/app.py …`.
4. Settings → Networking → Generate Domain → cole a URL pública no
   [GAIE/README.md](GAIE/README.md) e no relatório.

**Opção B — Streamlit Community Cloud (grátis):**
- https://share.streamlit.io → New app → apontar para `GAIE/src/app.py`.

Passo a passo completo: [GAIE/docs/DEPLOY_RAILWAY.md](GAIE/docs/DEPLOY_RAILWAY.md).

---

## 📈 Conclusões técnicas e análise dos dados

### BDDI

**O que foi construído**
- Pipeline ETL completo (Airflow) que extrai focos da NASA FIRMS dia a dia e enriquece com clima da
  Open-Meteo em lote.
- Carga **idempotente** no Oracle via `MERGE`, evitando duplicação ao rodar a DAG várias vezes.
- 3 tabelas relacionadas + 4 índices.
- 5 consultas analíticas SQL (uma com JOIN, conforme exigido).

**Volume real carregado (snapshot atual)**

| Tabela | Linhas |
|--------|-------:|
| `focos_incendio` | **8.002** (7 dias FIRMS, Brasil) |
| `clima_associado` | **3.604** (enriquecidos via Open-Meteo) |
| `imagens_satelite_metadata` | 0 (preenchida pela ACV) |

**O que os dados reais revelam**
- **Mato Grosso lidera** com 1.502 focos no último mês, seguido de Pará (1.165) e Tocantins (921) —
  o clássico arco do desmatamento.
- **Cerrado** é o bioma mais atingido, alinhado com a estação seca em curso.
- A queda no número diário de focos entre 22 e 25/05 e o salto em 26/05 (1.599) sugerem padrão
  meteorológico (frente quente seguida de vento forte).
- ~21% dos focos têm UF `??` — coordenadas fora da bounding box dos retângulos de UF. Em produção,
  trocar a heurística por shapefile do IBGE (geopandas) zera esse percentual.

**Decisões técnicas relevantes**
- **Open-Meteo no lugar do OpenWeather:** Open-Meteo permite múltiplas coordenadas por requisição
  e não exige chave — muito mais eficiente para enriquecer milhares de focos.
- **Coleta dia a dia da FIRMS:** a API de área tem limite de volume por requisição (área × dias).
  N requisições de 1 dia evita HTTP 400 e dá robustez (dias indisponíveis viram skip).
- **Confiança normalizada:** VIIRS usa categórica (`l/n/h`) e MODIS usa numérica (0-100). O
  pipeline mapeia VIIRS para 25/65/95 antes do filtro `>= 30`, evitando descartar todo VIIRS.

### GAIE

**O que foi construído**
- Pipeline de ML do zero: leitura do Oracle → pré-processamento → engenharia de atributos →
  treino de 2 modelos → avaliação → SHAP → deploy via Streamlit.
- 2 técnicas distintas: **Random Forest** e **XGBoost**.
- App web em Streamlit com **gauge da probabilidade**, **SHAP local da previsão**, **dashboard do
  dataset** e ficha do modelo.

**Tabela comparativa de modelos**

| Modelo | Acurácia | Precisão | Recall | F1 | AUC |
|--------|:--------:|:--------:|:------:|:--:|:---:|
| Random Forest | 0.981 | 0.976 | 0.976 | 0.976 | 0.998 |
| **XGBoost** ⭐ | 0.989 | 0.983 | **0.990** | 0.986 | **0.9995** |

**Modelo escolhido e justificativa**
**XGBoost** foi escolhido pelo **maior recall (0.990)** e melhor AUC/F1. Em alerta de incêndio,
recall é o critério prioritário — deixar de sinalizar um foco perigoso (falso negativo) é mais
grave do que um alarme falso, que custa apenas uma checagem extra do brigadista.

**Ressalva metodológica (declarar no pitch!)**
As métricas altíssimas (AUC > 0.999) refletem a natureza **determinística do alvo**: o
`alto_risco_24h` é rotulado por regra de negócio (`secura + FRP + vento − precipitação`), pois
**não há rótulo observado** de propagação real disponível publicamente. Os modelos recuperam a
regra com precisão. Em produção, o alvo viria de **outcomes observados** (ex.: área queimada nas
24h seguintes via Sentinel-2). Esta limitação é **honesta de declarar** e mostra maturidade técnica.

**Interpretabilidade — o que o SHAP revelou**
- **`indice_secura`** (temperatura/umidade) é a variável mais influente — coerente com a física do
  fogo (combustível seco propaga rápido).
- **`frp`** (potência radiativa) está em 2º — focos intensos têm maior probabilidade de propagar.
- **`precipitacao`** tem efeito inverso (chuva reduz o risco).
- `flag_estacao_seca` e `flag_vento_forte` aparecem como sinais secundários consistentes.

**Decisões técnicas relevantes**
- **Recall como critério de escolha** em vez de acurácia: alinhado ao custo assimétrico de erro
  em alertas de emergência.
- **`ColumnTransformer` + `Pipeline`:** garante que o pré-processamento seja aplicado de forma
  idêntica em treino e inferência (no app), evitando *data leakage*.
- **Features derivadas com significado físico** (índice de secura, flag estação seca, vento forte)
  em vez de só features numéricas brutas — melhora generalização e explicabilidade.

### Impacto esperado

| Beneficiário | Como o PIRO ajuda |
|--------------|-------------------|
| Brigadistas / bombeiros | Alertas priorizados por risco — agem primeiro nos focos mais perigosos |
| IBAMA / ICMBio | Fiscalização baseada em dados consolidados |
| Produtores rurais em zona de risco | Notificação preventiva via RPA (regra > 70%) |
| Pesquisadores em clima | Acesso aos dados tratados via Oracle/SQL |

### Próximos passos sugeridos

- Substituir o alvo derivado por **outcomes observados** (área queimada em 24h via Sentinel-2).
- Trocar a heurística de UF/bioma por **shapefile do IBGE** (geopandas) — precisão total.
- **Calibrar threshold** do classificador para o custo operacional dos brigadistas (não usar 0.5 fixo).
- Treinar com **dados temporais** (mais dias) e validar com **time-based split**.
- Conectar o app à API de **previsão** do Open-Meteo (forecast em vez de current weather).

---

## 💡 Dicas para nota máxima em BDDI e GAIE

### BDDI (100 pts)

| Critério oficial | Peso | Status | Como garantir o máximo |
|------------------|:---:|:------:|------------------------|
| Pipeline automatizado no Apache Airflow | 20 | ✅ DAG escrita | Subir Airflow (`docker compose up`), **disparar a DAG ao menos 2× com sucesso** e tirar print do *Graph View* verde |
| Extração e integração dos dados | 15 | ✅ FIRMS + Open-Meteo | Mostrar no PDF as 2 fontes integradas + linhas de log com nº de focos coletados |
| Transformação e tratamento dos dados | 15 | ✅ implementado | Detalhar no PDF: normalização VIIRS (l/n/h→25/65/95), conversão UTC, dedup, UF/bioma |
| Estruturação e carga no Oracle | 15 | ✅ 3 tabelas + 4 índices, carga idempotente | Tirar print do SQL Developer com as 3 tabelas e dados |
| Consultas analíticas SQL | 20 | ✅ 5 consultas, uma com JOIN | Garantir que **todas as 5 aparecem no PDF com resultado real** |
| Arquitetura, documentação e clareza | 15 | ✅ PDF + ZIP + READMEs | Incluir o **diagrama visual** do fluxo (já tem em `fluxo_pipeline.png`) e conclusão técnica |

**Checklist final BDDI**
- [ ] Rodar `docker compose up -d` → DAG `piro_ingestion` verde **2 vezes** → print
- [ ] Print das tabelas populadas no SQL Developer/DBeaver (1 print por tabela com algumas linhas)
- [ ] Substituir os `[PLACEHOLDER]` no `RELATORIO_BDDI.pdf` pelos prints reais antes de entregar
- [ ] Confirmar nomes e RMs no PDF (já estão: Matheus, Guilherme, Julia)
- [ ] Postar o PDF + ZIP no portal FIAP

**Como capturar os prints**
1. `cd BDDI/deploy && docker compose up -d`
2. http://localhost:8080 — login `admin`/senha gerada em `standalone_admin_password.txt`
3. Ativar a DAG `piro_pipeline_queimadas`, clicar em *Trigger DAG* duas vezes
4. Graph View → print do fluxo todo verde
5. SQL Developer/DBeaver → `SELECT * FROM focos_incendio WHERE ROWNUM <= 20;` → print

### GAIE (100 pts)

| Critério oficial | Peso | Status | Como garantir o máximo |
|------------------|:---:|:------:|------------------------|
| Definição do problema e qualidade dos dados | 15 | ✅ dados reais 3.604 linhas | README e notebook já cobrem |
| Pré-processamento e engenharia de atributos | 20 | ✅ `ColumnTransformer` + features derivadas | Já detalhado |
| Aplicação e comparação de modelos | 20 | ✅ RF + XGBoost | Tabela comparativa no README e notebook |
| Validação e análise de métricas | 15 | ✅ acc/prec/recall/f1/AUC + matrizes | Notebook executado |
| Interpretabilidade com SHAP | 10 | ✅ summary + force + interpretação textual | Pronto |
| Deploy da aplicação | 10 | ✅ **Streamlit** | Subir em Streamlit Community Cloud ou Azure |
| Organização do código e README no GitHub | 10 | ✅ código achatado, README completo | Garantir `best_model.pkl` commitado |

**Checklist final GAIE**
- [ ] Criar repo GitHub público
- [ ] Subir o app **Streamlit** em URL pública (Streamlit Community Cloud é o caminho mais rápido)
- [ ] Preencher o link da aplicação no README do GAIE
- [ ] Confirmar que `models/best_model.pkl` e `reports/figures/shap_*` estão versionados
- [ ] Postar link do GitHub + link do app no portal FIAP

### Erros comuns que custam pontos

| Erro | Custo | Prevenção |
|------|:-----:|-----------|
| `.env` commitado no Git | Anula nota por segurança | `.env` no `.gitignore` (já está) |
| DAG sem execução com sucesso | -20 pts BDDI | Rodar e printar **2 execuções verdes** |
| Falta de JOIN nas queries | -5 pts BDDI | Q3 já tem JOIN focos × clima ✅ |
| App fora do ar no dia da entrega | -10 pts GAIE | Testar 1h antes; Streamlit Community Cloud é estável |
| Nomes/RMs errados nos documentos | -5 pts (vários) | Já corretos: Matheus, Guilherme, Julia |

### Pontos altos para destacar na defesa

**BDDI:**
- Pipeline **idempotente** (MERGE) — evita duplicação.
- Tratamento da **confiança categórica do VIIRS** (`l/n/h` → numérico) — mostra que estudou a fonte.
- Escolha do **Open-Meteo** em vez de OpenWeather (sem chave, lote eficiente).

**GAIE:**
- **Recall como critério** em vez de acurácia (custo assimétrico de erro).
- **`ColumnTransformer` no pipeline** — mesma transformação em treino e inferência.
- Declarar honestamente a **ressalva metodológica** do alvo derivado — mostra maturidade.
- SHAP confirmando física do problema (índice de secura + FRP) — modelo aprende padrões reais.

---

## ✅ Estado das entregas

| Disciplina | Critério oficial | Status |
|-----------|------------------|:------:|
| **BDDI** (100 pts) | DAG Airflow + extração + transformação + Oracle + 5 SQL + PDF/ZIP | ✅ código pronto, dados reais carregados, PDF gerado |
| **GAIE** (100 pts) | 2 modelos + SHAP + deploy web + README completo | ✅ XGBoost AUC 0.9995, SHAP, **app Streamlit** |

---

## 🔐 Segurança

- `.env` com credenciais **não vai pro Git** (está no `.gitignore`).
- Recomendo trocar a senha do Oracle após a entrega final, por garantia.
- Nenhuma senha aparece nos arquivos `.py` (todas via `os.environ` carregando do `.env`).
