"""PIRO · BDDI — Relatorio sanity-check offline.

Le o ultimo arquivo tratado em data/staging/ (ou roda a coleta de novo) e
imprime metricas agregadas que aparecem no relatorio:
  - total de focos
  - focos por estado / bioma
  - media de FRP, temperatura, umidade
  - % em estacao seca

Uso:
    python src/relatorio.py
    python src/relatorio.py --refresh    # forca nova coleta
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante que src/ esta no sys.path independente da forma de invocacao.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd

from coleta_apis import extrair_clima, extrair_focos
from config import STAGING_DIR
from transformacao import transformar

TRATADO = STAGING_DIR / "focos_tratados.csv"


def gerar(refresh: bool = False) -> pd.DataFrame:
    if TRATADO.exists() and not refresh:
        print(f"[relatorio] usando {TRATADO}")
        return pd.read_csv(TRATADO)
    focos = extrair_focos(dias=1)
    clima = extrair_clima(focos)
    df = transformar(focos, clima)
    df.to_csv(TRATADO, index=False)
    return df


def imprimir(df: pd.DataFrame) -> None:
    print(f"\nTotal de focos: {len(df)}")
    if df.empty:
        return
    print("\nFocos por estado (top 5):")
    print(df.groupby("estado")["id_externo"].count().sort_values(ascending=False).head())
    print("\nFocos por bioma:")
    print(df.groupby("bioma")["id_externo"].count().sort_values(ascending=False))
    print("\nMedias:")
    for c in ("frp", "temperatura", "umidade", "vento", "precipitacao"):
        if c in df.columns:
            print(f"  {c}: {pd.to_numeric(df[c], errors='coerce').mean():.2f}")
    if "estacao_seca" in df.columns:
        print(f"\n% em estacao seca: {df['estacao_seca'].mean()*100:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    imprimir(gerar(refresh=args.refresh))
