"""PIRO · BDDI — Carga idempotente no Oracle FIAP.

  - MERGE em focos_incendio (chave: id_externo, que tem UNIQUE no schema).
  - MERGE em clima_associado (chave: id_externo).
  - Se o banco esta inacessivel (sem VPN/credencial), grava CSV de evidencia
    em data/staging/ para que a DAG nao trave a demo.

A modelagem fica em sql/01_modelagem.sql e e aplicada por database.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Garante que src/ esta no sys.path mesmo se este modulo for importado
# como `src.carga_oracle` (de fora do src/) ou rodado como `python src/...`.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd

from config import (ORACLE_HOST, ORACLE_PASSWORD, ORACLE_PORT, ORACLE_SID,
                    ORACLE_USER, STAGING_DIR)

try:
    import oracledb
except ImportError:  # pragma: no cover
    oracledb = None  # type: ignore

_MERGE_FOCO = """
MERGE INTO focos_incendio f
USING (SELECT :id_externo AS id_externo FROM dual) src
ON (f.id_externo = src.id_externo)
WHEN NOT MATCHED THEN
  INSERT (id_externo, latitude, longitude, data_foco, satelite,
          confianca, brilho, frp, estado, bioma)
  VALUES (:id_externo, :latitude, :longitude, TO_DATE(:data_foco,'YYYY-MM-DD'),
          :satelite, :confianca, :brilho, :frp, :estado, :bioma)
"""

_MERGE_CLIMA = """
MERGE INTO clima_associado c
USING (SELECT :id_externo AS id_externo FROM dual) src
ON (c.id_externo = src.id_externo)
WHEN NOT MATCHED THEN
  INSERT (id_externo, temperatura, umidade, vento, precipitacao, estacao_seca)
  VALUES (:id_externo, :temperatura, :umidade, :vento, :precipitacao, :estacao_seca)
"""


def conectar():
    if oracledb is None:
        raise RuntimeError("oracledb nao instalado")
    if not (ORACLE_USER and ORACLE_PASSWORD):
        raise RuntimeError("ORACLE_USER/ORACLE_PASSWORD ausentes (.env)")
    dsn = oracledb.makedsn(ORACLE_HOST, ORACLE_PORT, sid=ORACLE_SID)
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)


def _num(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _bind_foco(row: pd.Series) -> dict:
    return {
        "id_externo": str(row["id_externo"]),
        "latitude": _num(row.get("latitude")),
        "longitude": _num(row.get("longitude")),
        "data_foco": str(row.get("data") or row.get("data_dt", "")[:10]),
        "satelite": (row.get("satelite") or "")[:20],
        "confianca": _num(row.get("confianca")),
        "brilho": _num(row.get("brilho")),
        "frp": _num(row.get("frp")),
        "estado": (row.get("estado") or "??")[:2],
        "bioma": (row.get("bioma") or "Desconhecido")[:20],
    }


def _bind_clima(row: pd.Series) -> dict:
    return {
        "id_externo": str(row["id_externo"]),
        "temperatura": _num(row.get("temperatura")),
        "umidade": _num(row.get("umidade")),
        "vento": _num(row.get("vento")),
        "precipitacao": _num(row.get("precipitacao")),
        "estacao_seca": int(row.get("estacao_seca", 0) or 0),
    }


def carregar(df: pd.DataFrame) -> int:
    """Carrega focos + clima no Oracle. Retorna n de focos processados.

    Se a conexao falhar (sem VPN, sem credencial, oracledb ausente), salva
    `data/staging/carga_simulada.csv` e retorna 0 — assim a DAG nao trava.
    """
    if df.empty:
        print("[oracle] DataFrame vazio; nada a carregar.")
        return 0
    try:
        with conectar() as cx:
            cur = cx.cursor()
            cur.executemany(_MERGE_FOCO,
                            [_bind_foco(r) for _, r in df.iterrows()])
            cur.executemany(_MERGE_CLIMA,
                            [_bind_clima(r) for _, r in df.iterrows()])
            cx.commit()
        print(f"[oracle] {len(df)} focos+clima carregados (idempotente via MERGE).")
        return len(df)
    except Exception as e:
        fallback = STAGING_DIR / "carga_simulada.csv"
        df.to_csv(fallback, index=False)
        print(f"[oracle] indisponivel ({e}); evidencia salva em {fallback}.")
        return 0
