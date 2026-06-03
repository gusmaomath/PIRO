"""
PIRO · GAIE — Gerador de dataset sintetico
-------------------------------------------
Gera dados de focos de incendio com variaveis climaticas e geograficas.
Alvo (target): 'alto_risco' = 1 se o foco tem alto risco de virar grande
incendio em 24h, 0 caso contrario.

Cumpre o requisito GAIE: >= 1.000 linhas e >= 10 colunas.
Aqui geramos 3.000 linhas e 12 colunas de entrada + 1 alvo.

Uso:
    python gerar_dados.py            # gera data/focos_incendio.csv (3000 linhas)
    python gerar_dados.py 5000       # numero de linhas customizado
"""
import sys
import numpy as np
import pandas as pd

from pipeline import DATASET_PATH

# Reprodutibilidade — mesma semente => mesmo dataset
RNG = np.random.default_rng(42)

BIOMAS = ["Amazonia", "Cerrado", "Pantanal", "Caatinga", "Mata Atlantica"]
# Quanto maior o fator, mais seco/inflamavel o bioma
SECURA_BIOMA = {"Amazonia": 0.6, "Cerrado": 1.0, "Pantanal": 0.9,
                "Caatinga": 1.1, "Mata Atlantica": 0.5}
ESTADOS = ["PA", "MT", "MS", "GO", "TO", "BA", "MA", "RO", "AM", "SP"]


def gerar(n: int = 3000) -> pd.DataFrame:
    temperatura = RNG.normal(31, 5, n).clip(15, 48)          # °C
    umidade = RNG.normal(45, 18, n).clip(8, 100)             # %
    velocidade_vento = RNG.gamma(2.0, 6, n).clip(0, 60)      # km/h
    precipitacao_mm = RNG.gamma(1.2, 3, n).clip(0, 80)       # mm/dia
    dias_sem_chuva = RNG.poisson(8, n).clip(0, 60)           # dias
    brilho = RNG.normal(320, 18, n).clip(280, 400)           # Kelvin (sensor)
    frp = RNG.gamma(2.0, 25, n).clip(1, 600)                 # MW (Fire Radiative Power)
    confianca = RNG.uniform(40, 100, n)                      # % confianca do satelite
    ndvi = RNG.uniform(0.1, 0.9, n)                           # indice de vegetacao
    declividade = RNG.gamma(1.5, 8, n).clip(0, 60)           # % inclinacao do terreno
    bioma = RNG.choice(BIOMAS, n)
    estado = RNG.choice(ESTADOS, n)

    df = pd.DataFrame({
        "temperatura": temperatura.round(1),
        "umidade": umidade.round(1),
        "velocidade_vento": velocidade_vento.round(1),
        "precipitacao_mm": precipitacao_mm.round(1),
        "dias_sem_chuva": dias_sem_chuva,
        "brilho": brilho.round(1),
        "frp": frp.round(1),
        "confianca": confianca.round(1),
        "ndvi": ndvi.round(3),
        "declividade": declividade.round(1),
        "bioma": bioma,
        "estado": estado,
    })

    # ---- Regra latente que define o risco (com ruido) ----
    fator_bioma = df["bioma"].map(SECURA_BIOMA).values
    score = (
        0.16 * (df["temperatura"] - 30)
        - 0.07 * (df["umidade"] - 45)
        + 0.13 * (df["velocidade_vento"] - 12)
        - 0.10 * df["precipitacao_mm"]
        + 0.14 * (df["dias_sem_chuva"] - 8)
        + 0.012 * (df["frp"] - 50)
        + 1.6 * (fator_bioma - 0.8)
        + 1.8 * (df["ndvi"] - 0.5)
        + RNG.normal(0, 0.9, n)            # ruido moderado => problema realista
    )
    prob = 1 / (1 + np.exp(-score))        # sigmoide
    df["alto_risco"] = (prob > 0.5).astype(int)

    # Injeta ~2% de valores nulos para exercitar o pre-processamento (GAIE)
    for col in ["umidade", "velocidade_vento", "ndvi"]:
        idx = RNG.choice(n, size=int(0.02 * n), replace=False)
        df.loc[idx, col] = np.nan

    return df


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    df = gerar(n)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH, index=False)
    print(f"OK  ->  {DATASET_PATH.relative_to(DATASET_PATH.parent.parent)}  "
          f"({len(df)} linhas, {df.shape[1]} colunas)")
    print(f"Distribuicao do alvo:\n{df['alto_risco'].value_counts(normalize=True).round(3)}")
