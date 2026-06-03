"""PIRO · BDDI — Transformacao / tratamento (T do ETL).

  - dropna em coordenadas/data,
  - parse de tipos (datas + numericos),
  - normalizacao de confianca (FIRMS mistura numero e l/n/h),
  - mediana para NaN de clima,
  - deduplicacao por id_externo,
  - derivacao de UF + bioma por bounding box (sem dependencia de shapefile),
  - feature de risco: estacao_seca.

Recebe focos + clima ja extraidos (DataFrames) e devolve um unico DataFrame
pronto pra carga.
"""
from __future__ import annotations

import pandas as pd

CONF_MIN = 30
_CONF_CATEGORICA = {"l": 25, "n": 65, "h": 95}

# (UF, lat_min, lat_max, lon_min, lon_max)
_UF_BBOXES = [
    ("AM", -9.8, 2.2, -73.8, -56.1), ("PA", -9.8, 2.6, -58.9, -46.0),
    ("MT", -18.0, -7.3, -61.6, -50.2), ("MS", -24.1, -17.2, -58.2, -50.9),
    ("GO", -19.5, -12.4, -53.3, -45.9), ("TO", -13.5, -5.2, -50.8, -45.7),
    ("BA", -18.4, -8.5, -46.6, -37.3), ("MG", -22.9, -14.2, -51.0, -39.9),
    ("SP", -25.3, -19.8, -53.1, -44.2), ("PR", -26.7, -22.5, -54.6, -48.0),
    ("RS", -33.8, -27.1, -57.6, -49.7), ("SC", -29.4, -25.9, -53.8, -48.3),
    ("MA", -10.3, -1.0, -48.8, -41.8), ("PI", -10.9, -2.7, -45.9, -40.4),
    ("CE", -7.9, -2.8, -41.4, -37.2), ("RO", -13.7, -7.9, -66.8, -59.8),
    ("AC", -11.2, -7.1, -73.9, -66.6), ("RR", -1.6, 5.3, -64.8, -58.9),
    ("AP", -1.2, 4.5, -54.9, -49.9),
]
_BIOMA_BBOXES = [
    ("Amazonia", -9.8, 5.3, -73.9, -46.0), ("Pantanal", -22.0, -16.0, -58.5, -55.0),
    ("Caatinga", -16.5, -2.8, -44.0, -37.0), ("Mata Atlantica", -30.0, -5.0, -48.5, -34.8),
    ("Pampa", -33.8, -28.0, -57.6, -49.7), ("Cerrado", -24.0, -2.0, -60.0, -41.0),
]


def _bbox_match(lat, lon, tabela, default):
    if pd.isna(lat) or pd.isna(lon):
        return default
    for nome, lat_min, lat_max, lon_min, lon_max in tabela:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return nome
    return default


def _normaliza_confianca(s: pd.Series) -> pd.Series:
    num = pd.to_numeric(s, errors="coerce")
    cat = s.astype(str).str.strip().str.lower().map(_CONF_CATEGORICA)
    return num.fillna(cat)


def transformar(focos: pd.DataFrame, clima: pd.DataFrame) -> pd.DataFrame:
    """Limpa, deduplica, junta com clima e deriva UF/bioma + estacao_seca."""
    if focos.empty:
        return focos
    antes = len(focos)
    df = focos.dropna(subset=["latitude", "longitude"]).copy()

    if "data" in df.columns:
        df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
        df = df.dropna(subset=["data_dt"])

    if "confianca" in df.columns:
        df["confianca"] = _normaliza_confianca(df["confianca"])
        df = df[df["confianca"].fillna(0) >= CONF_MIN]

    df = df.drop_duplicates(subset=["id_externo"])

    if not clima.empty:
        clima = clima.drop_duplicates(subset=["id_externo"])
        df = df.merge(clima, on="id_externo", how="left")
        for c in ("temperatura", "umidade", "vento", "precipitacao"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
                df[c] = df[c].fillna(df[c].median())

    df["estado"] = df.apply(
        lambda r: _bbox_match(r["latitude"], r["longitude"], _UF_BBOXES, "??"), axis=1)
    df["bioma"] = df.apply(
        lambda r: _bbox_match(r["latitude"], r["longitude"], _BIOMA_BBOXES, "Desconhecido"),
        axis=1)

    if {"umidade", "precipitacao"}.issubset(df.columns):
        df["estacao_seca"] = ((df["umidade"] < 30) & (df["precipitacao"] < 1)).astype(int)
    else:
        df["estacao_seca"] = 0

    print(f"[transform] {antes} -> {len(df)} apos limpeza + dedup + enriquecimento.")
    return df
