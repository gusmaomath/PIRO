"""
PIRO · GAIE — Aplicacao Streamlit
==================================
App que demonstra TODO o pipeline de ML do PIRO e permite ver o
treinamento acontecendo EM TEMPO REAL (epoca a epoca / arvore a arvore).

Abas:
  1. Sobre o problema   -> contexto + dataset
  2. Treinar ao vivo    -> treina os 3 modelos com graficos atualizando ao vivo
  3. Comparar modelos   -> tabela de metricas + matrizes de confusao
  4. Interpretar (SHAP) -> summary beeswarm + force plot + bar individual
  5. Testar previsao    -> sliders -> probabilidade de alto risco

Rodar local:  streamlit run app.py
"""
import time
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score,
                             confusion_matrix)

from pipeline import (DATASET_PATH, CATEGORICAS, RANDOM_STATE,
                      construir_preprocessador, separar_X_y)
from gerar_dados import gerar, BIOMAS, ESTADOS

st.set_page_config(page_title="PIRO · GAIE", page_icon="🛰️", layout="wide")

# --------------------------------------------------------------------------
# Dados (cacheados): gerados na hora se nao houver CSV
# --------------------------------------------------------------------------
@st.cache_data
def carregar_dados():
    # Preferencia: snapshot real do Oracle FIAP (exportado pelo BDDI)
    reais = DATASET_PATH.parent / "focos_reais.csv"
    if reais.exists():
        return pd.read_csv(reais)
    # Fallback 1: CSV sintetico ja gerado por gerar_dados.py
    if DATASET_PATH.exists():
        return pd.read_csv(DATASET_PATH)
    # Fallback 2: gera em memoria (ultimo recurso para deploy sem CSV)
    return gerar(10000)


def fonte_dos_dados() -> str:
    reais = DATASET_PATH.parent / "focos_reais.csv"
    if reais.exists():
        return "Oracle FIAP (BDDI)"
    if DATASET_PATH.exists():
        return "CSV sintetico (gerar_dados.py)"
    return "Gerador sintetico em memoria"


@st.cache_resource
def preparar_dados():
    """Fit do pre-processador 1x e split. Retorna arrays prontos p/ treino incremental."""
    df = carregar_dados()
    X, y = separar_X_y(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42)
    prep = construir_preprocessador().fit(X_tr)
    return {
        "df": df,
        "prep": prep,
        "feat_names": list(prep.get_feature_names_out()),
        "Xtr": prep.transform(X_tr), "Xte": prep.transform(X_te),
        "ytr": y_tr.values, "yte": y_te.values,
        "X_tr_raw": X_tr,
    }


D = preparar_dados()
if "modelos" not in st.session_state:
    st.session_state.modelos = {}    # nome -> {pipe-like, history, metrics}

st.title("🛰️ PIRO · GAIE — Previsao de risco de propagacao de queimadas")
st.caption("Generative AI For Engineering · Global Solution 2026 · "
           "Pipeline de ML com treino ao vivo, comparacao, SHAP e teste.")

abas = st.tabs(["📊 Sobre o problema", "🏋️ Treinar ao vivo",
                "📈 Comparar modelos", "🔍 Interpretar (SHAP)", "🎯 Testar previsao"])

# ==========================================================================
# ABA 1 — SOBRE
# ==========================================================================
with abas[0]:
    st.subheader("O problema")
    st.markdown(
        "Satelites (NASA FIRMS, Sentinel, INPE) detectam milhares de focos de calor por dia. "
        "Nem todo foco vira um grande incendio. **O modelo preve se um foco tem ALTO RISCO "
        "de se propagar nas proximas 24h**, para priorizar a resposta de brigadistas. "
        "Classificacao binaria: `alto_risco` = 0 ou 1.")
    c1, c2, c3, c4 = st.columns(4)
    df = D["df"]
    fonte = fonte_dos_dados()
    c1.metric("Linhas no dataset", f"{len(df):,}")
    c2.metric("Colunas (features)", df.shape[1] - 1)
    c3.metric("% alto risco", f"{df['alto_risco'].mean()*100:.1f}%")
    c4.metric("Fonte", fonte.split(" ")[0])
    if "Oracle" in fonte:
        st.success(
            "**Fonte dos dados:** snapshot do **Oracle FIAP** populado pela camada "
            "BDDI deste projeto (NASA FIRMS + Open-Meteo, MERGE idempotente). "
            "O alvo `alto_risco` e derivado da mesma regra fisica latente usada "
            "no gerador sintetico para garantir comparabilidade entre as duas fontes."
        )
    else:
        st.info(
            "**Fonte dos dados:** dataset sintetico gerado por regra fisica latente "
            "(`gerar_dados.py`) com seed=42. Em producao, e alimentado pelo "
            "snapshot do Oracle FIAP exportado pela camada BDDI "
            "(`BDDI/src/exportar_para_gaie.py`)."
        )
    st.dataframe(df.head(20), use_container_width=True)
    st.markdown("**Engenharia de atributos** cria: `indice_secura` (temp/umidade), "
                "`estacao_seca` (dias sem chuva >= 10), `vento_forte` (vento >= 20 km/h).")

# ==========================================================================
# ABA 2 — TREINO AO VIVO
# ==========================================================================
with abas[1]:
    st.subheader("Treine e assista a evolucao em tempo real")
    st.markdown("Cada modelo e treinado **incrementalmente**: o grafico se atualiza "
                "a cada passo, mostrando o aprendizado acontecendo. **3 tecnicas** "
                "para a comparacao GAIE.")
    st.warning("⚠️ Treine **um modelo de cada vez**. Aguarde a barra de progresso "
               "chegar ao fim (mensagem `OK · acc=... · auc=...`) antes de clicar no "
               "botao do proximo modelo. Treinos simultaneos podem corromper o estado "
               "da sessao Streamlit.")

    colA, colB, colC = st.columns(3)

    # ---------- Modelo 1: Random Forest (arvore a arvore) ----------
    with colA:
        st.markdown("### 🌳 Random Forest")
        n_arvores = st.slider("Arvores", 10, 300, 150, 10, key="rf_n")
        if st.button("Treinar RF", key="btn_rf"):
            graf = st.empty(); barra = st.progress(0); status = st.empty()
            rf = RandomForestClassifier(n_estimators=1, warm_start=True,
                                        max_depth=12, random_state=RANDOM_STATE, n_jobs=-1)
            hist = {"arvores": [], "acuracia": [], "f1": [], "auc": []}
            passos = list(range(5, n_arvores + 1, 5))
            for k, n in enumerate(passos):
                rf.n_estimators = n
                rf.fit(D["Xtr"], D["ytr"])
                pred = rf.predict(D["Xte"]); proba = rf.predict_proba(D["Xte"])[:, 1]
                hist["arvores"].append(n)
                hist["acuracia"].append(accuracy_score(D["yte"], pred))
                hist["f1"].append(f1_score(D["yte"], pred))
                hist["auc"].append(roc_auc_score(D["yte"], proba))
                graf.line_chart(pd.DataFrame(
                    {"acuracia": hist["acuracia"], "f1": hist["f1"], "auc": hist["auc"]},
                    index=hist["arvores"]))
                status.write(f"Arvores: **{n}** · acc=`{hist['acuracia'][-1]:.3f}` "
                             f"· auc=`{hist['auc'][-1]:.3f}`")
                barra.progress((k + 1) / len(passos))
                time.sleep(0.04)
            st.session_state.modelos["Random Forest"] = {
                "model": rf, "kind": "rf",
                "metrics": {"acuracia": hist["acuracia"][-1], "f1": hist["f1"][-1],
                            "auc": hist["auc"][-1],
                            "cm": confusion_matrix(D["yte"], rf.predict(D["Xte"])).tolist()},
                "history": hist}
            st.success(f"OK · acc={hist['acuracia'][-1]:.3f} · auc={hist['auc'][-1]:.3f}")

    # ---------- Modelo 2: XGBoost (round a round) ----------
    with colB:
        st.markdown("### ⚡ XGBoost")
        n_rounds = st.slider("Boosting rounds", 20, 400, 200, 20, key="xgb_n")
        if st.button("Treinar XGB", key="btn_xgb"):
            try:
                from xgboost import XGBClassifier
                graf = st.empty(); barra = st.progress(0); status = st.empty()
                hist = {"rounds": [], "acuracia": [], "f1": [], "auc": []}
                incremento = 20   # rounds adicionados por passo (treino incremental)
                acumulado = list(range(incremento, n_rounds + 1, incremento))
                xgb_final = None
                booster_so_far = None
                status.write("Treinando XGBoost incrementalmente...")
                for k, n in enumerate(acumulado):
                    xgb = XGBClassifier(n_estimators=incremento, max_depth=5,
                                        learning_rate=0.1, eval_metric="logloss",
                                        random_state=RANDOM_STATE, n_jobs=-1,
                                        tree_method="hist")
                    # xgb_model permite continuar de onde parou: O(n) em vez de O(n^2)
                    if booster_so_far is None:
                        xgb.fit(D["Xtr"], D["ytr"])
                    else:
                        xgb.fit(D["Xtr"], D["ytr"], xgb_model=booster_so_far)
                    booster_so_far = xgb.get_booster()
                    xgb_final = xgb
                    pred = xgb.predict(D["Xte"]); proba = xgb.predict_proba(D["Xte"])[:, 1]
                    hist["rounds"].append(n)
                    hist["acuracia"].append(accuracy_score(D["yte"], pred))
                    hist["f1"].append(f1_score(D["yte"], pred))
                    hist["auc"].append(roc_auc_score(D["yte"], proba))
                    if len(hist["rounds"]) >= 2:
                        graf.line_chart(pd.DataFrame(
                            {"acuracia": hist["acuracia"], "f1": hist["f1"],
                             "auc": hist["auc"]},
                            index=hist["rounds"]))
                    status.write(f"Rounds: **{n}** · acc=`{hist['acuracia'][-1]:.3f}` "
                                 f"· auc=`{hist['auc'][-1]:.3f}`")
                    barra.progress((k + 1) / len(acumulado))
                st.session_state.modelos["XGBoost"] = {
                    "model": xgb_final, "kind": "xgb",
                    "metrics": {"acuracia": hist["acuracia"][-1], "f1": hist["f1"][-1],
                                "auc": hist["auc"][-1],
                                "cm": confusion_matrix(D["yte"], xgb_final.predict(D["Xte"])).tolist()},
                    "history": hist}
                st.success(f"OK · acc={hist['acuracia'][-1]:.3f} · auc={hist['auc'][-1]:.3f}")
            except ImportError:
                st.warning("Instale xgboost: `pip install xgboost==2.1.0`.")

    # ---------- Modelo 3: Rede Neural MLP (epoca a epoca) ----------
    with colC:
        st.markdown("### 🧠 Rede Neural (MLP)")
        n_epocas = st.slider("Numero de epocas", 10, 200, 80, 10, key="mlp_n")
        if st.button("Treinar Rede Neural", key="btn_mlp"):
            graf_loss = st.empty()
            graf_acc = st.empty()
            barra = st.progress(0)
            status = st.empty()
            mlp = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1,
                                warm_start=True, random_state=42)
            hist = {"epoca": [], "loss": [], "acc_treino": [], "acc_val": []}
            import warnings
            warnings.filterwarnings("ignore")
            for ep in range(1, n_epocas + 1):
                mlp.fit(D["Xtr"], D["ytr"])           # 1 epoca por chamada (warm_start)
                hist["epoca"].append(ep)
                hist["loss"].append(mlp.loss_)
                hist["acc_treino"].append(mlp.score(D["Xtr"], D["ytr"]))
                hist["acc_val"].append(mlp.score(D["Xte"], D["yte"]))
                graf_loss.line_chart(pd.DataFrame({"loss (treino)": hist["loss"]},
                                                  index=hist["epoca"]))
                graf_acc.line_chart(pd.DataFrame(
                    {"acc treino": hist["acc_treino"], "acc validacao": hist["acc_val"]},
                    index=hist["epoca"]))
                status.write(f"Epoca: **{ep}** · loss=`{mlp.loss_:.3f}` "
                             f"· acc_val=`{hist['acc_val'][-1]:.3f}`")
                barra.progress(ep / n_epocas)
                time.sleep(0.03)
            proba = mlp.predict_proba(D["Xte"])[:, 1]
            st.session_state.modelos["Rede Neural (MLP)"] = {
                "model": mlp, "kind": "mlp",
                "metrics": {"acuracia": hist["acc_val"][-1],
                            "f1": f1_score(D["yte"], mlp.predict(D["Xte"])),
                            "auc": roc_auc_score(D["yte"], proba),
                            "cm": confusion_matrix(D["yte"], mlp.predict(D["Xte"])).tolist()},
                "history": hist}
            st.success(f"Treinado! acc={hist['acc_val'][-1]:.3f} "
                       f"· auc={st.session_state.modelos['Rede Neural (MLP)']['metrics']['auc']:.3f}")

# ==========================================================================
# ABA 3 — COMPARAR
# ==========================================================================
with abas[2]:
    st.subheader("Comparacao de desempenho")
    if not st.session_state.modelos:
        st.info("Treine pelo menos um modelo na aba **Treinar ao vivo**.")
    else:
        from sklearn.metrics import ConfusionMatrixDisplay
        linhas = [{"Modelo": nome, "Acuracia": round(m["metrics"]["acuracia"], 4),
                   "F1": round(m["metrics"]["f1"], 4), "AUC": round(m["metrics"]["auc"], 4)}
                  for nome, m in st.session_state.modelos.items()]
        tab = pd.DataFrame(linhas).sort_values("F1", ascending=False)
        st.dataframe(tab, use_container_width=True, hide_index=True)
        melhor = tab.iloc[0]["Modelo"]
        st.success(f"🏆 Melhor modelo (por F1): **{melhor}**")
        st.markdown("### Matrizes de confusao")
        cols = st.columns(len(st.session_state.modelos))
        for col, (nome, m) in zip(cols, st.session_state.modelos.items()):
            with col:
                st.markdown(f"**{nome}**")
                cm = np.array(m["metrics"]["cm"])
                # Cria figura nova e fecha explicitamente apos render:
                # `clear_figure=True` no st.pyplot causa bug visual quando
                # multiplos plt.subplots() coexistem no mesmo run do script.
                fig, ax = plt.subplots(figsize=(3.2, 2.8))
                disp = ConfusionMatrixDisplay(
                    confusion_matrix=cm,
                    display_labels=["baixo", "alto"])
                disp.plot(ax=ax, cmap="Oranges", colorbar=False, values_format="d")
                ax.set_title("")
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

# ==========================================================================
# ABA 4 — SHAP
# ==========================================================================
with abas[3]:
    st.subheader("Interpretabilidade com SHAP")
    st.markdown("SHAP mostra **quanto cada variavel empurrou** a previsao "
                "para 'alto risco'. Requisito GAIE: **>=1 grafico global + >=1 individual**. "
                "Aqui ha 3: summary (beeswarm), force plot e bar plot.")

    candidatos = {n: m for n, m in st.session_state.modelos.items()
                  if m["kind"] in ("rf", "xgb")}
    if not candidatos:
        st.info("Treine **Random Forest** ou **XGBoost** na aba 'Treinar ao vivo' "
                "(SHAP roda rapido em arvores via TreeExplainer).")
    else:
        try:
            import shap
            nome = st.selectbox("Explicar qual modelo?", list(candidatos.keys()))
            clf = candidatos[nome]["model"]
            feat = D["feat_names"]
            Xte = D["Xte"]
            if hasattr(Xte, "toarray"):
                Xte = Xte.toarray()

            with st.spinner("Calculando valores SHAP..."):
                explainer = shap.TreeExplainer(clf)
                sv = explainer.shap_values(Xte)
                base = explainer.expected_value
                if isinstance(sv, list):
                    sv = sv[1]
                    base = base[1] if np.ndim(base) else base
                elif getattr(sv, "ndim", 2) == 3:
                    sv = sv[..., 1]
                    base = base[1] if np.ndim(base) else base

            st.markdown("#### 1. Importancia global (beeswarm)")
            st.caption("Cada ponto e um foco. Azul = valor baixo, vermelho = valor alto. "
                       "Direita do zero empurra para ALTO RISCO; esquerda empurra para BAIXO.")
            fig1 = plt.figure()
            shap.summary_plot(sv, Xte, feature_names=feat, show=False, max_display=20)
            plt.tight_layout()
            st.pyplot(fig1, clear_figure=True, use_container_width=True)

            st.markdown("#### 2. Explicacao individual (1 foco)")
            i = int(st.number_input("Indice do foco no teste", 0, len(Xte) - 1, 0))

            tab_waterfall, tab_bar = st.tabs(["Waterfall", "Bar plot"])
            with tab_waterfall:
                st.caption("Empilha o impacto de cada feature partindo da media do dataset "
                           "ate o resultado deste foco. Vermelho = empurra para ALTO RISCO, "
                           "azul = empurra para BAIXO. `E[f(X)]` e a media, `f(x)` o resultado.")
                try:
                    exp = shap.Explanation(values=sv[i], base_values=base,
                                           data=Xte[i], feature_names=feat)
                    fig2 = plt.figure()
                    shap.plots.waterfall(exp, max_display=14, show=False)
                    plt.tight_layout()
                    st.pyplot(fig2, clear_figure=True, use_container_width=True)
                except Exception as e:
                    st.warning(f"Waterfall falhou ({e}). Use Bar plot.")
            with tab_bar:
                st.caption("Top 12 features que mais influenciaram a previsao deste foco.")
                fig3 = plt.figure()
                shap.bar_plot(sv[i], feature_names=feat, max_display=12, show=False)
                plt.tight_layout()
                st.pyplot(fig3, clear_figure=True, use_container_width=True)
        except ModuleNotFoundError:
            st.warning("Biblioteca `shap` nao instalada. Rode: `pip install shap`.")

# ==========================================================================
# ABA 5 — TESTAR
# ==========================================================================
with abas[4]:
    st.subheader("Teste uma previsao")
    if not st.session_state.modelos:
        st.info("Treine um modelo na aba **Treinar ao vivo** para testar.")
    else:
        nome = st.selectbox("Modelo", list(st.session_state.modelos.keys()))
        c1, c2, c3 = st.columns(3)
        entrada = {}
        defaults = {"temperatura": 34.0, "umidade": 30.0, "velocidade_vento": 25.0,
                    "precipitacao_mm": 0.0, "dias_sem_chuva": 15, "brilho": 340.0,
                    "frp": 120.0, "confianca": 85.0, "ndvi": 0.7, "declividade": 10.0}
        campos = list(defaults.items())
        for idx, (k, v) in enumerate(campos):
            col = [c1, c2, c3][idx % 3]
            entrada[k] = col.number_input(k, value=float(v))
        entrada["bioma"] = c1.selectbox("bioma", BIOMAS, index=1)
        entrada["estado"] = c2.selectbox("estado", ESTADOS)

        if st.button("Prever risco"):
            from pipeline import engenharia_atributos
            linha = pd.DataFrame([entrada])
            linha = engenharia_atributos(linha)
            Xt = D["prep"].transform(linha)
            prob = st.session_state.modelos[nome]["model"].predict_proba(Xt)[0, 1]
            st.metric("Probabilidade de ALTO RISCO", f"{prob*100:.1f}%")
            if prob >= 0.7:
                st.error("🚨 ALTO RISCO — disparar alerta (gatilho do bot RPA).")
            elif prob >= 0.4:
                st.warning("⚠️ Risco moderado — monitorar.")
            else:
                st.success("✅ Risco baixo — apenas registrar.")
