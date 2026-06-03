"""PIRO · GAIE — Treino, validacao, comparacao e interpretabilidade.

Treina TRES tecnicas (criterio GAIE >= 2):
  1) Random Forest (bagging)
  2) XGBoost       (gradient boosting)
  3) Rede Neural MLP

Para cada modelo: split 80/20 estratificado, metricas (acc/precision/recall/F1/AUC),
matriz de confusao (PNG via ConfusionMatrixDisplay).

Para o melhor modelo (por F1): salva pipeline + gera SHAP:
  - summary plot (beeswarm — impacto + valor de cada feature)
  - force plot   (1 previsao individual — empurroes que decidiram)
  - bar plot     (top features para a mesma previsao)

Uso:
    python src/treino.py
"""
from __future__ import annotations

import json
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

from gerar_dados import gerar
from pipeline import (ALVO, CONFUSION_DIR, DATASET_PATH, FIGURES_DIR,
                      METRICAS_PATH, MODELO_PATH, RANDOM_STATE, SHAP_BAR_PATH,
                      SHAP_SUMMARY_PATH, SHAP_WATERFALL_PATH,
                      construir_modelos, separar_X_y)


# ==========================================================================
# Dados
# ==========================================================================
def carregar_dados() -> pd.DataFrame:
    if DATASET_PATH.exists():
        return pd.read_csv(DATASET_PATH)
    print(f"CSV nao encontrado em {DATASET_PATH}, gerando dataset sintetico...")
    df = gerar(3000)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH, index=False)
    return df


def _slug(nome: str) -> str:
    return (nome.lower().replace(" ", "_").replace("(", "").replace(")", "")
            .replace("/", "_"))


# ==========================================================================
# Avaliacao
# ==========================================================================
def avaliar(nome: str, modelo, X_test, y_test) -> dict:
    pred = modelo.predict(X_test)
    proba = modelo.predict_proba(X_test)[:, 1]
    return {
        "modelo": nome,
        "acuracia": round(accuracy_score(y_test, pred), 4),
        "precisao": round(precision_score(y_test, pred), 4),
        "recall": round(recall_score(y_test, pred), 4),
        "f1": round(f1_score(y_test, pred), 4),
        "auc": round(roc_auc_score(y_test, proba), 4),
        "matriz_confusao": confusion_matrix(y_test, pred).tolist(),
    }


def salvar_matriz_confusao(nome: str, modelo, X_test, y_test) -> None:
    """Matriz de confusao bonita via ConfusionMatrixDisplay."""
    ConfusionMatrixDisplay.from_estimator(
        modelo, X_test, y_test,
        display_labels=["baixo risco", "alto risco"],
        cmap="Oranges",
        colorbar=True,
    )
    plt.title(f"Matriz de confusao — {nome}")
    out = CONFUSION_DIR / f"confusion_matrix_{_slug(nome)}.png"
    plt.savefig(out, bbox_inches="tight", dpi=120)
    plt.close()
    print(f"[OK] {out}")


# ==========================================================================
# SHAP
# ==========================================================================
def _sv_classe_positiva(shap_values, base_value):
    """Normaliza saida SHAP para a classe positiva (binaria)."""
    if isinstance(shap_values, list):
        return shap_values[1], (base_value[1] if np.ndim(base_value) else base_value)
    if getattr(shap_values, "ndim", 2) == 3:
        return shap_values[..., 1], (base_value[1] if np.ndim(base_value) else base_value)
    return shap_values, base_value


def gerar_shap(pipe, X_train, X_test) -> None:
    """Salva summary (beeswarm), force plot (idx 0) e bar plot individual."""
    import shap
    prep = pipe.named_steps["prep"]
    clf = pipe.named_steps["clf"]
    feat_names = list(prep.get_feature_names_out())
    Xt_test = prep.transform(X_test)
    if hasattr(Xt_test, "toarray"):
        Xt_test = Xt_test.toarray()

    if hasattr(clf, "estimators_") or clf.__class__.__name__.startswith("XGB"):
        explainer = shap.TreeExplainer(clf)
        sv_raw = explainer.shap_values(Xt_test)
        base_raw = explainer.expected_value
    else:
        Xt_train = prep.transform(X_train)
        if hasattr(Xt_train, "toarray"):
            Xt_train = Xt_train.toarray()
        bg = shap.sample(Xt_train, 50, random_state=RANDOM_STATE)
        explainer = shap.KernelExplainer(lambda d: clf.predict_proba(d)[:, 1], bg)
        sv_raw = explainer.shap_values(Xt_test[:80], nsamples=100)
        base_raw = explainer.expected_value
        Xt_test = Xt_test[:80]

    sv, base = _sv_classe_positiva(sv_raw, base_raw)

    # 1) Summary plot (beeswarm — global)
    plt.figure()
    shap.summary_plot(sv, Xt_test, feature_names=feat_names, show=False, max_display=20)
    plt.tight_layout()
    plt.savefig(SHAP_SUMMARY_PATH, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"[OK] {SHAP_SUMMARY_PATH}")

    # 2) Waterfall plot (individual — moderno, legivel)
    try:
        exp = shap.Explanation(values=sv[0], base_values=base,
                               data=Xt_test[0], feature_names=feat_names)
        plt.figure()
        shap.plots.waterfall(exp, max_display=14, show=False)
        plt.tight_layout()
        plt.savefig(SHAP_WATERFALL_PATH, dpi=120, bbox_inches="tight")
        plt.close()
        print(f"[OK] {SHAP_WATERFALL_PATH}")
    except Exception as e:
        print(f"[aviso] waterfall falhou ({e}); pulando.")

    # 3) Bar plot individual (top features para a 1a amostra)
    plt.figure()
    shap.bar_plot(sv[0], feature_names=feat_names, max_display=12, show=False)
    plt.title("Top features — foco #0")
    plt.tight_layout()
    plt.savefig(SHAP_BAR_PATH, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"[OK] {SHAP_BAR_PATH}")


# ==========================================================================
# Main
# ==========================================================================
def main():
    warnings.filterwarnings("ignore")
    df = carregar_dados()
    X, y = separar_X_y(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE)

    resultados = []
    pipelines = {}
    for nome, pipe in construir_modelos().items():
        pipe.fit(X_train, y_train)
        pipelines[nome] = pipe
        r = avaliar(nome, pipe, X_test, y_test)
        resultados.append(r)
        print(f"[OK] {nome}: acc={r['acuracia']} f1={r['f1']} auc={r['auc']}")
        salvar_matriz_confusao(nome, pipe, X_test, y_test)
        joblib.dump(pipe, MODELO_PATH.parent / f"{_slug(nome)}.joblib")

    melhor = max(resultados, key=lambda r: r["f1"])
    print(f"\n>>> Melhor modelo (F1): {melhor['modelo']} (F1={melhor['f1']})")

    joblib.dump(pipelines[melhor["modelo"]], MODELO_PATH)
    METRICAS_PATH.write_text(json.dumps(
        {"resultados": resultados, "melhor": melhor["modelo"]}, indent=2))
    print(f"[OK] {MODELO_PATH}")
    print(f"[OK] {METRICAS_PATH}")

    try:
        gerar_shap(pipelines[melhor["modelo"]], X_train, X_test)
    except Exception as e:
        print(f"[aviso] SHAP falhou ({e}). Sera gerado dentro da app Streamlit.")


if __name__ == "__main__":
    main()
