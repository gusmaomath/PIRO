# Como rodar o GAIE localmente

## Pre-requisitos
- Python 3.10+ (testado em 3.12)
- pip

## Passo a passo

```bash
# 1. Entre na pasta GAIE
cd GAIE

# 2. (recomendado) crie um ambiente virtual (Git Bash no Windows)
py -3.12 -m venv .venv
source .venv/Scripts/activate
# Linux/Mac: source .venv/bin/activate

# 3. Instale as dependencias
pip install -r deploy/requirements.txt

# 4. (opcional) gere o dataset — a app gera sozinha se faltar
python src/gerar_dados.py

# 5. Abra a aplicacao
streamlit run src/app.py
```

A app abre em `http://localhost:8501`. Para usar a configuracao de produção
(headless / sem CORS / sem XSRF), aponte o Streamlit para o config.toml em
config/:

```bash
export STREAMLIT_CONFIG_DIR=config/.streamlit
streamlit run src/app.py
```

## O que fazer na app (roteiro para o video do pitch)

1. **Aba "Sobre o problema"** — contexto e dataset (previa das linhas).
2. **Aba "Treinar ao vivo"** — clique em **Treinar Random Forest** e depois
   **Treinar Rede Neural**. Os graficos atualizam em tempo real:
   - Random Forest: acuracia/F1/AUC sobem conforme as arvores sao adicionadas.
   - Rede Neural: a *loss* cai e a acuracia sobe **epoca a epoca**.
3. **Aba "Comparar modelos"** — metricas + matrizes de confusao lado a lado.
4. **Aba "Interpretar (SHAP)"** — importancia global + explicacao de 1 foco.
5. **Aba "Testar previsao"** — sliders -> probabilidade de alto risco.
   Acima de 70% a app sinaliza o gatilho do bot RPA (PIRO).

## Treino por script

```bash
python src/treino.py
```

Gera (caminhos resolvidos por `src/pipeline.py`):
- `models/modelo.joblib`
- `reports/metricas.json`
- `reports/shap_global.png`

## Problemas comuns

- **`shap` lento na 1a vez**: normal; o `TreeExplainer` no Random Forest e rapido.
  Treine o Random Forest antes de abrir a aba SHAP.
- **Avisos de convergencia do MLP**: esperados (treino e incremental, 1 epoca por
  passo). Ja sao silenciados na app.
- **Porta ocupada**: `streamlit run src/app.py --server.port 8502`.
- **ImportError "pipeline"**: rode a partir da raiz do GAIE; o Streamlit adiciona
  a pasta do script (`src/`) ao `sys.path`, mas se rodar de fora pode falhar.
