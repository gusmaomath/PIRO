# Como rodar o BDDI localmente

## Pre-requisitos
- Docker Desktop (Airflow standalone em 1 comando) **ou**
  Python 3.10+ se for rodar o Airflow direto na maquina (mais trabalho).
- SQL Developer ou DBeaver (para `sql/01_modelagem.sql` e `sql/02_consultas.sql`).
- Credenciais válidas do Oracle FIAP (RM + senha) — o host `oracle.fiap.com.br` é público, sem VPN.

## Passo a passo (Docker)

```bash
# 1. Entre na pasta BDDI
cd BDDI

# 2. Configure suas chaves
cp config/.env.example config/.env
#   edite config/.env com FIRMS_MAP_KEY, OPENWEATHER_KEY (opcional),
#   ORACLE_USER (seu RM) e ORACLE_PASSWORD

# 3. Crie as tabelas no Oracle FIAP
#   abra sql/01_modelagem.sql no SQL Developer/DBeaver -> execute o script inteiro
#   OU, com Python local: python src/database.py setup

# 4. Suba o Airflow
cd deploy
docker compose up -d

# 5. Pegue o login admin (gerado na primeira vez)
docker compose logs airflow | grep admin

# 6. Abra http://localhost:8080 -> login -> habilite a DAG piro_pipeline_queimadas
# 7. Trigger MANUAL 2x (o edital pede 2 execucoes verdes).
# 8. Confirme dados no Oracle:
#    SELECT COUNT(*) FROM focos_incendio;
#    SELECT COUNT(*) FROM clima_associado;
```

## Rodar as 6 consultas

```bash
cd BDDI
python src/database.py query        # imprime as 6 consultas + topo de 10 linhas
```

Ou abra `sql/02_consultas.sql` no SQL Developer e execute uma a uma. Salve os
prints com resultados visiveis (vao para o relatorio BDDI).

## Rodar sem Docker (testar isoladamente)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r deploy/requirements.txt

# So coleta (FIRMS + Open-Meteo)
python src/coleta_apis.py           # grava data/staging/focos_raw.csv + clima_raw.csv

# Coleta + transformacao + relatorio (sem Oracle)
python src/relatorio.py --refresh

# Criar tabelas + rodar as 6 consultas
python src/database.py both
```

## Por dentro do pipeline (o que cada modulo faz)

| Arquivo                       | Responsabilidade                                |
|---|---|
| `src/config.py`               | Le `config/.env` e expoe constantes (paths + chaves) |
| `src/coleta_apis.py`          | FIRMS multi-dia -> Open-Meteo lote -> fallback  |
| `src/transformacao.py`        | Limpeza, dedup, bbox UF/bioma, estacao_seca     |
| `src/carga_oracle.py`         | `MERGE` idempotente em focos + clima            |
| `src/database.py`             | Cria tabelas (`01_modelagem.sql`) + roda 6 consultas |
| `src/relatorio.py`            | Sanity-check offline (sem precisar de banco)    |
| `dags/piro_pipeline_dag.py`   | DAG fina: orquestra os scripts via XCom         |

## Problemas comuns

- **Erro "ORA-12541" / "ORA-12170" / timeout**: rede instavel para `oracle.fiap.com.br:1521` ou credenciais incorretas. Confira `config/.env` (RM e senha) e teste o host com `ping oracle.fiap.com.br`.
- **FIRMS retorna 401**: `FIRMS_MAP_KEY` errada ou expirada (renove em
  https://firms.modaps.eosdis.nasa.gov/api/map_key). A DAG cai no fallback sintetico.
- **FIRMS retorna 0 focos**: normal fora do pico da seca; ajuste `dias=` na chamada
  de `extrair_focos()` (a DAG usa `dias=7`).
- **Tarefa `carregar_oracle` "indisponivel"**: o `oracledb` nao conseguiu conectar.
  A evidencia fica em `data/staging/carga_simulada.csv` dentro do container —
  copie com `docker cp` se precisar mostrar.
- **`coleta_apis` nao encontrado pelo Airflow**: a DAG procura em `/opt/airflow/scripts`
  (montado pelo `deploy/docker-compose.yml` apontando para `src/`). Se mudar a
  estrutura, ajuste os `volumes:` e os caminhos em `dags/piro_pipeline_dag.py`.
