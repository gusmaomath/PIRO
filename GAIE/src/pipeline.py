"""PIRO · GAIE — Pipeline compartilhado.

Cobre os criterios GAIE de pre-processamento:
  - Engenharia de atributos (indice_secura, estacao_seca, vento_forte).
  - Tratamento de outliers (IQR clipping).
  - Tratamento de nulos (mediana / moda).
  - Encoding categorico (One-Hot) + normalizacao (StandardScaler).
  - Flags binarias passam direto (passthrough).

Os caminhos (data/, models/, reports/) sao expostos como constantes para que
treino.py, gerar_dados.py e app.py compartilhem a mesma convencao.
"""
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ------ Layout de pastas ------
# Este arquivo vive em GAIE/src/ — sobe 1 nivel para alcancar data/, models/, reports/.
SRC_DIR = Path(__file__).resolve().parent
GAIE_DIR = SRC_DIR.parent
DATA_DIR = GAIE_DIR / "data"
MODELS_DIR = GAIE_DIR / "models"
REPORTS_DIR = GAIE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DATASET_PATH = DATA_DIR / "focos_incendio.csv"
MODELO_PATH = MODELS_DIR / "modelo.joblib"
METRICAS_PATH = REPORTS_DIR / "metricas.json"
SHAP_SUMMARY_PATH = FIGURES_DIR / "shap_summary.png"
SHAP_WATERFALL_PATH = FIGURES_DIR / "shap_waterfall.png"
SHAP_BAR_PATH = FIGURES_DIR / "shap_bar_individual.png"
CONFUSION_DIR = FIGURES_DIR
for _d in (DATA_DIR, MODELS_DIR, REPORTS_DIR, FIGURES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------ Features ------
ALVO = "alto_risco"

# Numericas continuas (recebem imputer mediana + scaler)
NUMERICAS_CONTINUAS = [
    "temperatura", "umidade", "velocidade_vento", "precipitacao_mm",
    "dias_sem_chuva", "brilho", "frp", "confianca", "ndvi", "declividade",
    "indice_secura",
]
# Flags binarias (passthrough — ja sao 0/1)
FLAGS_BINARIAS = ["estacao_seca", "vento_forte"]
# Categoricas (recebem imputer moda + onehot)
CATEGORICAS = ["bioma", "estado"]

NUMERICAS = NUMERICAS_CONTINUAS + FLAGS_BINARIAS   # compat com codigo antigo
RANDOM_STATE = 42


# ==========================================================================
# Engenharia + limpeza
# ==========================================================================
def engenharia_atributos(df: pd.DataFrame) -> pd.DataFrame:
    """Cria variaveis derivadas com significado fisico."""
    df = df.copy()
    df["indice_secura"] = df["temperatura"] / (df["umidade"].fillna(df["umidade"].median()) + 1)
    df["estacao_seca"] = (df["dias_sem_chuva"] >= 10).astype(int)
    df["vento_forte"] = (df["velocidade_vento"].fillna(0) >= 20).astype(int)
    return df


def clip_outliers_iqr(df: pd.DataFrame, fator: float = 1.5) -> pd.DataFrame:
    """Clipa cada numerica continua nos limites IQR (Q1 - k*IQR, Q3 + k*IQR)."""
    df = df.copy()
    for col in NUMERICAS_CONTINUAS:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        df[col] = df[col].clip(q1 - fator * iqr, q3 + fator * iqr)
    return df


# ==========================================================================
# Pre-processador + modelos
# ==========================================================================
def construir_preprocessador() -> ColumnTransformer:
    """Imputacao + escala (num continuas); imputacao + one-hot (categoricas);
    passthrough nas flags binarias."""
    num = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("num", num, NUMERICAS_CONTINUAS),
        ("cat", cat, CATEGORICAS),
        ("flags", "passthrough", FLAGS_BINARIAS),
    ])


def construir_modelos() -> dict:
    """3 modelos para a comparacao GAIE (criterio: >=2 tecnicas diferentes).

    - Random Forest: ensemble de arvores (bagging).
    - XGBoost: gradient boosting (state-of-the-art em dados tabulares).
    - MLP: rede neural densa — alimenta a aba de treino ao vivo.
    """
    from xgboost import XGBClassifier  # import local para nao quebrar app sem xgb
    pre = construir_preprocessador
    return {
        "Random Forest": Pipeline([
            ("prep", pre()),
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=12,
                random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
        "XGBoost": Pipeline([
            ("prep", pre()),
            ("clf", XGBClassifier(
                n_estimators=300, max_depth=5, learning_rate=0.1,
                eval_metric="logloss", random_state=RANDOM_STATE,
                n_jobs=-1, tree_method="hist")),
        ]),
        "Rede Neural (MLP)": Pipeline([
            ("prep", pre()),
            ("clf", MLPClassifier(
                hidden_layer_sizes=(64, 32), max_iter=400,
                random_state=RANDOM_STATE)),
        ]),
    }


def separar_X_y(df: pd.DataFrame):
    df = clip_outliers_iqr(engenharia_atributos(df))
    return df[NUMERICAS_CONTINUAS + CATEGORICAS + FLAGS_BINARIAS], df[ALVO]
