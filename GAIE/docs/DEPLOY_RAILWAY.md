# Deploy do GAIE no Railway (passo a passo)

O Railway hospeda a app Streamlit a partir do seu repositório GitHub. O deploy é
automático a cada `git push`. Os arquivos de configuração já estão prontos nesta pasta:

- `requirements.txt` — dependências.
- `Procfile` — comando de início (`streamlit run ...`).
- `railway.json` — builder NIXPACKS + start command (redundância segura).
- `runtime.txt` — versão do Python.
- `.streamlit/config.toml` — modo headless, sem CORS/XSRF (necessário em nuvem).

> **Importante sobre a porta:** o Railway injeta a variável `$PORT`. O start command já usa
> `--server.port $PORT --server.address 0.0.0.0`. **Não fixe uma porta manualmente.**

---

## Pré-requisitos
- Conta no GitHub com o repositório do projeto.
- Conta no Railway (login com GitHub).
- A pasta `GAIE/` versionada no repo. Se ela **não** estiver na raiz do repositório,
  você definirá o *Root Directory* como `GAIE` no passo 3.

## Passo 1 — Suba o código para o GitHub
```bash
git add .
git commit -m "GAIE: app Streamlit pronta para deploy"
git push origin main
```

## Passo 2 — Crie o projeto no Railway
1. Acesse o painel do Railway e clique em **New Project**.
2. Escolha **Deploy from GitHub repo**.
3. Autorize o Railway e selecione o repositório do PIRO.

## Passo 3 — Configure o serviço
1. Abra o servico criado → aba **Settings**.
2. Em **Root Directory**, coloque `GAIE` (pule se a app estiver na raiz do repo).
3. Em **Deploy → Start Command**, confirme:
   ```
   streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
   ```
   (Ja vem do `railway.json`; so confira.)
4. O builder e **Nixpacks** com auto-deteccao. Como temos `requirements.txt` na
   raiz do GAIE (que faz `-r deploy/requirements.txt`) + `runtime.txt` na raiz
   (Python 3.12.7), o Nixpacks reconhece o projeto Python e configura
   automaticamente python + pip + venv + instalacao. Sem `nixpacks.toml`.

## Passo 4 — Gere o domínio público
1. Vá em **Settings → Networking → Public Networking**.
2. Clique em **Generate Domain**.
3. O Railway cria uma URL como `https://piro-gaie-production.up.railway.app`.

## Passo 5 — Valide
1. Acompanhe os logs na aba **Deployments** até aparecer
   `You can now view your Streamlit app`.
2. Abra a URL **em janela anônima** (garante que está pública).
3. Cole a URL no campo "Link da aplicação" do `README.md` e no relatório.

---

## Dicas
- **Cada `git push` redeploya** automaticamente — bom para mostrar 2 deploys no SDTCC.
- **Memória**: a app é leve (sklearn). Se o build estourar memória por causa do `shap`,
  ele só é importado quando você abre a aba SHAP — o deploy em si não o exige no boot.
- **Variáveis de ambiente** (se um dia ligar APIs reais): aba **Variables** do serviço.
  Nunca coloque chaves no código.

## Alternativa gratuita
Se preferir não usar Railway, o **Streamlit Community Cloud**
(`share.streamlit.io`) hospeda apps Streamlit a partir do GitHub sem custo: aponte para
`GAIE/app.py`, defina `requirements.txt` e pronto. As regras da disciplina aceitam qualquer
URL pública funcional.

> Planos e créditos gratuitos do Railway mudam com frequência — confira os valores atuais
> no painel antes de publicar, caso isso seja relevante para a entrega.
