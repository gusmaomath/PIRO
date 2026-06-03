"""PIRO · BDDI — Extracao de focos + clima.

Estrategia (do mais robusto p/ menos):

  FOCOS:
    1. NASA FIRMS (VIIRS_SNPP_NRT)  — exige FIRMS_MAP_KEY (gratuita).
       Buscamos dia a dia (a API limita area x dias por requisicao).
    2. Fallback sintetico se nao houver chave / falhar.

  CLIMA:
    1. Open-Meteo (api.open-meteo.com)  — gratuita, SEM chave, em lote.
       Aceita lat/lon como CSV no mesmo request: 100 focos por chamada.
    2. OpenWeather (se OPENWEATHER_KEY presente) — 1 chamada por foco.
    3. Fallback sintetico coerente.

Quando rodada como script (`python scripts/coleta_apis.py`), grava os CSVs
extraidos em data/staging/ para inspecao manual.
"""
from __future__ import annotations

import io
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Garante que src/ esta no sys.path independente da forma de invocacao.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

from config import (BRAZIL_BBOX, FIRMS_BASE, FIRMS_MAP_KEY, OPENMETEO_URL,
                    OPENWEATHER_KEY, OPENWEATHER_URL, STAGING_DIR)

BIOMAS = ["Amazonia", "Cerrado", "Pantanal", "Caatinga", "Mata Atlantica"]
ESTADOS = ["PA", "MT", "MS", "GO", "TO", "BA", "MA", "RO", "AM", "SP"]


# ==========================================================================
# FOCOS
# ==========================================================================
def extrair_focos(dias: int = 3, sensor: str = "VIIRS_SNPP_NRT") -> pd.DataFrame:
    """Baixa focos do Brasil (FIRMS) dia a dia. Cai pro sintetico se falhar."""
    if FIRMS_MAP_KEY and requests is not None:
        frames = []
        hoje = date.today()
        for d in range(dias):
            dia = (hoje - timedelta(days=d)).isoformat()
            url = f"{FIRMS_BASE}/{FIRMS_MAP_KEY}/{sensor}/{BRAZIL_BBOX}/1/{dia}"
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                df = pd.read_csv(io.StringIO(resp.text))
                if not df.empty:
                    frames.append(df)
            except requests.RequestException as e:
                print(f"[FIRMS] dia {dia} falhou ({e}).")
        if frames:
            df = _padroniza_firms(pd.concat(frames, ignore_index=True))
            print(f"[FIRMS] {len(df)} focos REAIS coletados em {dias} dia(s).")
            return df
        print("[FIRMS] nenhuma resposta util; caindo pro fallback sintetico.")
    else:
        motivo = "sem FIRMS_MAP_KEY" if not FIRMS_MAP_KEY else "requests indisponivel"
        print(f"[FIRMS] {motivo}; gerando focos sinteticos.")
    return _focos_sinteticos(500)


def _padroniza_firms(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas da FIRMS para o nosso schema canonico."""
    ren = {"acq_date": "data", "acq_time": "hora", "satellite": "satelite",
           "confidence": "confianca", "bright_ti4": "brilho", "brightness": "brilho",
           "frp": "frp"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    # id_externo estavel = lat|lon|data|hora
    if {"data", "hora"}.issubset(df.columns):
        df["id_externo"] = (
            df["latitude"].round(4).astype(str) + "|"
            + df["longitude"].round(4).astype(str) + "|"
            + df["data"].astype(str) + "|" + df["hora"].astype(str).str.zfill(4))
    else:
        df["id_externo"] = df.index.astype(str)
    return df


def _focos_sinteticos(n: int) -> pd.DataFrame:
    hoje = date.today()
    linhas = []
    for i in range(n):
        d = hoje - timedelta(days=random.randint(0, 29))
        linhas.append({
            "id_externo": f"SYN{i:06d}",
            "latitude": round(random.uniform(-33, 5), 4),
            "longitude": round(random.uniform(-73, -34), 4),
            "data": d.isoformat(),
            "hora": f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
            "satelite": random.choice(["N", "1", "Aqua", "Terra"]),
            "confianca": round(random.uniform(40, 100), 1),
            "brilho": round(random.uniform(300, 380), 1),
            "frp": round(random.uniform(1, 500), 1),
        })
    df = pd.DataFrame(linhas)
    print(f"[FIRMS] {len(df)} focos sinteticos gerados.")
    return df


# ==========================================================================
# CLIMA
# ==========================================================================
def extrair_clima(focos: pd.DataFrame, chunk: int = 100) -> pd.DataFrame:
    """Tenta Open-Meteo (lote, sem chave) -> OpenWeather (por foco) -> sintetico."""
    if focos.empty:
        return pd.DataFrame(columns=["id_externo", "temperatura", "umidade", "vento",
                                     "precipitacao"])
    if requests is not None:
        df = _clima_openmeteo(focos, chunk)
        if df is not None and not df.empty:
            return df
        if OPENWEATHER_KEY:
            df = _clima_openweather(focos)
            if df is not None and not df.empty:
                return df
    return _clima_sintetico(focos)


def _clima_openmeteo(focos: pd.DataFrame, chunk: int):
    """Open-Meteo aceita ate ~100 coords por request (CSV em lat/lon)."""
    saidas = []
    for i in range(0, len(focos), chunk):
        lote = focos.iloc[i:i + chunk]
        lats = ",".join(str(v) for v in lote["latitude"])
        lons = ",".join(str(v) for v in lote["longitude"])
        results = None
        for tentativa in range(3):
            try:
                resp = requests.get(OPENMETEO_URL, timeout=60, params={
                    "latitude": lats, "longitude": lons,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"})
                resp.raise_for_status()
                data = resp.json()
                results = data if isinstance(data, list) else [data]
                break
            except requests.RequestException:
                time.sleep(1.5 * (tentativa + 1))
        if results is None:
            print(f"[Open-Meteo] lote {i//chunk + 1} falhou; pulando.")
            continue
        for (_, foco), res in zip(lote.iterrows(), results):
            cur = res.get("current") if isinstance(res, dict) else None
            if not cur:
                continue
            saidas.append({
                "id_externo": foco["id_externo"],
                "temperatura": cur.get("temperature_2m"),
                "umidade": cur.get("relative_humidity_2m"),
                # Open-Meteo: wind_speed_10m em km/h por padrao
                "vento": cur.get("wind_speed_10m"),
                "precipitacao": cur.get("precipitation", 0.0) or 0.0,
            })
        time.sleep(0.4)
    if not saidas:
        return None
    df = pd.DataFrame(saidas)
    print(f"[Open-Meteo] clima REAL para {len(df)} focos.")
    return df


def _clima_openweather(focos: pd.DataFrame):
    saidas = []
    for _, f in focos.iterrows():
        try:
            r = requests.get(OPENWEATHER_URL, timeout=15, params={
                "lat": f["latitude"], "lon": f["longitude"],
                "appid": OPENWEATHER_KEY, "units": "metric"})
            r.raise_for_status()
            w = r.json()
            saidas.append({
                "id_externo": f["id_externo"],
                "temperatura": w["main"]["temp"],
                "umidade": w["main"]["humidity"],
                "vento": w.get("wind", {}).get("speed", 0) * 3.6,  # m/s -> km/h
                "precipitacao": w.get("rain", {}).get("1h", 0.0)})
        except Exception:
            continue
    if not saidas:
        return None
    df = pd.DataFrame(saidas)
    print(f"[OpenWeather] clima REAL para {len(df)} focos.")
    return df


def _clima_sintetico(focos: pd.DataFrame) -> pd.DataFrame:
    linhas = [{
        "id_externo": f["id_externo"],
        "temperatura": round(random.uniform(20, 42), 1),
        "umidade": round(random.uniform(10, 90), 1),
        "vento": round(random.uniform(0, 45), 1),
        "precipitacao": round(random.uniform(0, 30), 1),
    } for _, f in focos.iterrows()]
    df = pd.DataFrame(linhas)
    print(f"[clima] {len(df)} registros sinteticos.")
    return df


# ==========================================================================
# Execucao standalone (debug)
# ==========================================================================
if __name__ == "__main__":
    focos = extrair_focos(dias=1)
    clima = extrair_clima(focos)
    focos.to_csv(STAGING_DIR / "focos_raw.csv", index=False)
    clima.to_csv(STAGING_DIR / "clima_raw.csv", index=False)
    print(f"focos.head:\n{focos.head()}")
    print(f"clima.head:\n{clima.head()}")
    print(f"Arquivos em {STAGING_DIR}")
