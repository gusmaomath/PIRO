"""PIRO · BDDI — DAG Airflow (orquestracao fina).

Fluxo: extrair -> armazenar_temp -> transformar -> carregar_oracle -> analisar

Cada tarefa chama uma funcao em scripts/ (coleta_apis.py, transformacao.py,
carga_oracle.py). A DAG nao tem logica de negocio — so passa caminhos via XCom.

Estrutura esperada no Airflow:
  /opt/airflow/dags/piro_pipeline_dag.py
  /opt/airflow/scripts/{config,coleta_apis,transformacao,carga_oracle}.py
(docker-compose.yml monta cada pasta no path correto)

Variaveis de ambiente (.env / Airflow Admin -> Variables):
  FIRMS_MAP_KEY, OPENWEATHER_KEY (opcional),
  ORACLE_HOST, ORACLE_PORT, ORACLE_SID, ORACLE_USER, ORACLE_PASSWORD
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

# Em producao (container Airflow), os modulos sao montados em /opt/airflow/scripts
# (ver deploy/docker-compose.yml). Localmente eles vivem em BDDI/src/.
_CANDIDATOS = [
    Path("/opt/airflow/scripts"),
    Path(__file__).resolve().parent.parent / "src",
]
for _p in _CANDIDATOS:
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from coleta_apis import extrair_clima, extrair_focos  # noqa: E402
from carga_oracle import carregar  # noqa: E402
from config import STAGING_DIR  # noqa: E402
from transformacao import transformar  # noqa: E402

DEFAULT_ARGS = {
    "owner": "equipe_piro",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

FOCOS_RAW = STAGING_DIR / "focos_raw.csv"
CLIMA_RAW = STAGING_DIR / "clima_raw.csv"
STAGE = STAGING_DIR / "stage_focos_clima.csv"
TRATADO = STAGING_DIR / "focos_tratados.csv"


def _extrair(**_):
    # 7 dias: garante volume mesmo em dias fora do pico da seca.
    # Open-Meteo enriquece em lote (~67 chamadas para 6700 focos).
    focos = extrair_focos(dias=7)
    clima = extrair_clima(focos)
    focos.to_csv(FOCOS_RAW, index=False)
    clima.to_csv(CLIMA_RAW, index=False)
    return {"focos": str(FOCOS_RAW), "clima": str(CLIMA_RAW)}


def _armazenar_temp(**ctx):
    paths = ctx["ti"].xcom_pull(task_ids="extrair")
    focos = pd.read_csv(paths["focos"])
    clima = pd.read_csv(paths["clima"]) if Path(paths["clima"]).exists() else pd.DataFrame()
    merged = focos.merge(clima, on="id_externo", how="left") if not clima.empty else focos
    merged.to_csv(STAGE, index=False)
    print(f"[staging] {len(merged)} linhas em {STAGE}")
    return str(STAGE)


def _transformar(**ctx):
    stage = pd.read_csv(ctx["ti"].xcom_pull(task_ids="armazenar_temp"))
    cols_clima = ["id_externo", "temperatura", "umidade", "vento", "precipitacao"]
    clima = stage[[c for c in cols_clima if c in stage.columns]].drop_duplicates()
    focos = stage.drop(columns=[c for c in cols_clima if c != "id_externo" and c in stage.columns],
                       errors="ignore")
    df = transformar(focos, clima)
    df.to_csv(TRATADO, index=False)
    return str(TRATADO)


def _carregar(**ctx):
    df = pd.read_csv(ctx["ti"].xcom_pull(task_ids="transformar"))
    n = carregar(df)
    print(f"[load] {n} registros confirmados no Oracle.")


def _analisar(**ctx):
    df = pd.read_csv(ctx["ti"].xcom_pull(task_ids="transformar"))
    print(f"[analise] total: {len(df)} | media FRP: {df['frp'].mean():.1f}")
    if "estado" in df.columns:
        print("[analise] top 5 estados:")
        print(df.groupby("estado")["id_externo"].count().sort_values(ascending=False).head())


with DAG(
    dag_id="piro_pipeline_queimadas",
    description="PIRO BDDI: NASA FIRMS + Open-Meteo -> Oracle FIAP -> consultas",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=datetime(2026, 5, 25),
    catchup=False,
    tags=["piro", "bddi", "espacial"],
) as dag:
    extrair = PythonOperator(task_id="extrair", python_callable=_extrair)
    armazenar_temp = PythonOperator(task_id="armazenar_temp", python_callable=_armazenar_temp)
    transformar_task = PythonOperator(task_id="transformar", python_callable=_transformar)
    carregar_oracle = PythonOperator(task_id="carregar_oracle", python_callable=_carregar)
    analisar = PythonOperator(task_id="analisar", python_callable=_analisar)

    extrair >> armazenar_temp >> transformar_task >> carregar_oracle >> analisar
