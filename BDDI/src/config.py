"""PIRO · BDDI — Configuracao compartilhada.

Resolve caminhos (data/, sql/, scripts/) e carrega as variaveis de ambiente.
Importado por coleta_apis.py, transformacao.py, carga_oracle.py e database.py.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None

# Este arquivo vive em BDDI/src/ — sobe 1 nivel para alcancar BDDI/.
SRC_DIR = Path(__file__).resolve().parent
BDDI_DIR = SRC_DIR.parent
SQL_DIR = BDDI_DIR / "sql"
DATA_DIR = BDDI_DIR / "data"
STAGING_DIR = DATA_DIR / "staging"
CONFIG_DIR = BDDI_DIR / "config"
for _d in (DATA_DIR, STAGING_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# .env vive em config/. Dentro do container Airflow, montamos em /opt/airflow/.env.
if load_dotenv is not None:
    for _env in (CONFIG_DIR / ".env", Path("/opt/airflow/.env")):
        if _env.exists():
            load_dotenv(_env)
            break

# ---- APIs ----
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_KEY", "")
BRAZIL_BBOX = "-74,-34,-34,6"            # oeste, sul, leste, norte
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# ---- Oracle FIAP ----
ORACLE_HOST = os.environ.get("ORACLE_HOST", "oracle.fiap.com.br")
ORACLE_PORT = int(os.environ.get("ORACLE_PORT", "1521"))
ORACLE_SID = os.environ.get("ORACLE_SID", "ORCL")
ORACLE_USER = os.environ.get("ORACLE_USER", "")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "")
