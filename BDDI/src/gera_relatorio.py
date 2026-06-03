"""PIRO - BDDI - Gerador do RELATORIO_BDDI.pdf.

Produz o PDF unico exigido pelo edital, cobrindo as 13 secoes:
  1. Equipe (nome + RM)
  2. Descricao da solucao proposta
  3. Objetivo do pipeline
  4. Fonte de dados utilizada
  5. Arquitetura do pipeline (visual)
  6. Etapas da DAG
  7. Transformacoes realizadas
  8. Modelagem das tabelas Oracle
  9. Prints das execucoes no Airflow
  10. Prints das tabelas populadas no Oracle
  11. >=5 consultas analiticas em SQL
  12. Resultados das consultas
  13. Conclusao tecnica

Uso:
    python src/gera_relatorio.py
Saida:
    reports/RELATORIO_BDDI.pdf
"""
from __future__ import annotations

import math
import sys
from datetime import datetime
from pathlib import Path

# Bootstrap sys.path
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from config import BDDI_DIR

REPORTS_DIR = BDDI_DIR / "reports"
PRINTS_DIR = REPORTS_DIR / "prints"
PDF_PATH = REPORTS_DIR / "RELATORIO_BDDI.pdf"
SQL_FILE = BDDI_DIR / "sql" / "02_consultas.sql"
SCHEMA_FILE = BDDI_DIR / "sql" / "01_modelagem.sql"
CONSULTAS_TXT = PRINTS_DIR / "consultas.txt"


def ler_consulta_de_txt(numero: int) -> str:
    """Le a saida da Consulta N do consultas.txt (gerado pelo `database.py query`)."""
    if not CONSULTAS_TXT.exists():
        return f"[consultas.txt nao encontrado em {CONSULTAS_TXT}]"
    texto = CONSULTAS_TXT.read_text(encoding="utf-8", errors="ignore")
    marcador = f"========== Consulta {numero}:"
    if marcador not in texto:
        return f"[Consulta {numero} nao encontrada em consultas.txt]"
    inicio = texto.index(marcador)
    # proxima '==========' apos o marcador
    proximo = texto.find("==========", inicio + len(marcador))
    if proximo == -1:
        return texto[inicio:].strip()
    return texto[inicio:proximo].strip()

# Cores PIRO
COR_TITULO = (15, 76, 117)       # azul petroleo
COR_SUBTITULO = (50, 130, 184)   # azul medio
COR_DESTAQUE = (200, 80, 40)     # laranja queimada
COR_TEXTO = (40, 40, 40)
COR_CINZA = (110, 110, 110)


# Mapeia caracteres Unicode comuns que aparecem em comentarios/textos para
# equivalentes latin-1 (suportados pela fonte core do fpdf2).
_UNICODE_MAP = {
    "—": "-",  "–": "-",  "−": "-",     # em-dash, en-dash, minus
    "‘": "'",  "’": "'",                       # curly quotes
    "“": '"',  "”": '"',
    "…": "...",                                     # ellipsis
    "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "▶": ">",  "•": "-",                       # play, bullet
    " ": " ",                                       # nbsp
}


def _sanitize(txt: str) -> str:
    """Converte texto unicode para latin-1 puro (sobrevive ao FPDF core)."""
    for k, v in _UNICODE_MAP.items():
        txt = txt.replace(k, v)
    return txt.encode("latin-1", errors="replace").decode("latin-1")


class RelatorioBDDI(FPDF):
    def normalize_text(self, text):  # noqa: D401
        """Override do fpdf2: sanitiza tudo que vai pra pagina."""
        if isinstance(text, str):
            return _sanitize(text)
        return text

    def header(self):  # noqa: D401
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "I", 9)
        self.set_text_color(*COR_CINZA)
        self.cell(0, 8, "PIRO - BDDI - Relatorio Tecnico - GS 2026",
                  align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COR_SUBTITULO)
        self.set_line_width(0.4)
        self.line(15, 22, 195, 22)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*COR_CINZA)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    # ---- helpers de layout ----
    def h1(self, txt: str):
        self.ln(2)
        self.set_font("helvetica", "B", 18)
        self.set_text_color(*COR_TITULO)
        self.cell(0, 12, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COR_TITULO)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 60, self.get_y())
        self.ln(4)

    def h2(self, txt: str):
        self.ln(2)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(*COR_SUBTITULO)
        self.cell(0, 8, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def h3(self, txt: str):
        self.set_font("helvetica", "B", 11)
        self.set_text_color(*COR_TEXTO)
        self.cell(0, 6, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def p(self, txt: str):
        self.set_font("helvetica", "", 10.5)
        self.set_text_color(*COR_TEXTO)
        self.multi_cell(0, 5.5, txt)
        self.ln(1)

    def code(self, txt: str, max_lines: int | None = None):
        """Bloco de codigo monoespacado com wrap automatico via multi_cell."""
        self.set_font("courier", "", 7.2)
        self.set_text_color(60, 60, 60)
        self.set_fill_color(245, 245, 245)
        page_w = self.w - 2 * self.l_margin
        linhas = txt.splitlines()
        if max_lines:
            linhas = linhas[:max_lines]
        for linha in linhas:
            linha = linha.rstrip()
            if not linha:
                self.ln(2)
                continue
            self.multi_cell(page_w, 3.4, linha, fill=True,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def tabela(self, cabecalho: list[str], linhas: list[list[str]],
               larguras: list[int] | None = None):
        if not larguras:
            larg = (self.w - 2 * self.l_margin) / len(cabecalho)
            larguras = [larg] * len(cabecalho)
        # cabecalho
        self.set_font("helvetica", "B", 9.5)
        self.set_fill_color(*COR_SUBTITULO)
        self.set_text_color(255, 255, 255)
        for col, w in zip(cabecalho, larguras):
            self.cell(w, 6.5, col, border=1, align="C", fill=True)
        self.ln()
        # corpo
        self.set_font("helvetica", "", 9)
        self.set_text_color(*COR_TEXTO)
        zebra = False
        for linha in linhas:
            if zebra:
                self.set_fill_color(240, 240, 240)
            else:
                self.set_fill_color(255, 255, 255)
            for valor, w in zip(linha, larguras):
                self.cell(w, 5.5, str(valor)[:30], border=1, align="L",
                          fill=True)
            self.ln()
            zebra = not zebra
        self.ln(2)

    def callout(self, titulo: str, texto: str):
        self.set_fill_color(255, 245, 235)
        self.set_draw_color(*COR_DESTAQUE)
        self.set_line_width(0.3)
        y_inicio = self.get_y()
        self.set_x(self.l_margin + 2)
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*COR_DESTAQUE)
        self.cell(0, 6, f"  >> {titulo}", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                  fill=True)
        self.set_font("helvetica", "", 9.5)
        self.set_text_color(*COR_TEXTO)
        self.set_x(self.l_margin + 2)
        self.multi_cell(self.w - 2 * self.l_margin - 4, 5, texto, fill=True)
        self.rect(self.l_margin, y_inicio, self.w - 2 * self.l_margin,
                  self.get_y() - y_inicio)
        self.ln(3)

    def imagem(self, caminho: Path, legenda: str = "", largura: int = 170):
        if not caminho.exists():
            self.set_font("helvetica", "I", 9)
            self.set_text_color(*COR_CINZA)
            self.cell(0, 5, f"[imagem ausente: {caminho.name}]",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            return
        x_centro = (self.w - largura) / 2
        self.image(str(caminho), x=x_centro, w=largura)
        if legenda:
            self.set_font("helvetica", "I", 9)
            self.set_text_color(*COR_CINZA)
            self.cell(0, 5, legenda, align="C",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)


def _box(pdf, x, y, w, h, titulo, sub="",
         fill=(50, 130, 184), txt_color=(255, 255, 255)):
    """Caixa retangular com titulo + subtitulo opcional, centralizados."""
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*fill)
    pdf.rect(x, y, w, h, style="F")
    pdf.set_text_color(*txt_color)
    if sub:
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(x, y + 1.5)
        pdf.cell(w, 4, titulo, align="C")
        pdf.set_font("helvetica", "", 6.5)
        pdf.set_xy(x, y + 6)
        pdf.cell(w, 4, sub, align="C")
    else:
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_xy(x, y + h / 2 - 2)
        pdf.cell(w, 4, titulo, align="C")


def _seta(pdf, x1, y1, x2, y2, color=(90, 90, 90)):
    """Linha com ponta triangular pequena em (x2, y2)."""
    pdf.set_draw_color(*color)
    pdf.set_line_width(0.45)
    pdf.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 1.8
    spread = math.pi / 7
    pdf.line(x2, y2,
             x2 - head * math.cos(angle - spread),
             y2 - head * math.sin(angle - spread))
    pdf.line(x2, y2,
             x2 - head * math.cos(angle + spread),
             y2 - head * math.sin(angle + spread))


def desenha_arquitetura(pdf: "RelatorioBDDI"):
    """Diagrama nativo: fontes -> 5 tarefas -> Oracle. Sem ASCII."""
    AZUL = (52, 152, 219)        # fontes externas
    LARANJA = (230, 126, 34)     # tarefas Airflow
    VERDE = (46, 139, 87)        # sink relacional
    CINZA = (100, 100, 100)      # setas

    bw, bh = 26, 12              # largura, altura das caixas
    gap = 5                      # gap entre caixas horizontais
    y_top = pdf.get_y() + 4

    # Coordenadas X de cada bloco (5 tarefas + 1 sink em linha)
    x_fontes = pdf.l_margin
    x_extrair = x_fontes + bw + 8
    x_stage = x_extrair + bw + gap
    x_transf = x_stage + bw + gap
    x_carga = x_transf + bw + gap
    x_oracle = x_carga + bw + gap

    # Y de fontes (2 caixas empilhadas) e ETL (centralizado entre as 2)
    y_firms = y_top
    y_open = y_top + bh + 4
    y_etl = y_top + (bh + 4) / 2

    # --- Caixas ---
    _box(pdf, x_fontes, y_firms, bw, bh, "NASA FIRMS", "VIIRS NRT", AZUL)
    _box(pdf, x_fontes, y_open, bw, bh, "Open-Meteo", "Lote (free)", AZUL)
    _box(pdf, x_extrair, y_etl, bw, bh, "1. extrair", "PythonOperator", LARANJA)
    _box(pdf, x_stage, y_etl, bw, bh, "2. armazenar_temp", "staging CSV", LARANJA)
    _box(pdf, x_transf, y_etl, bw, bh, "3. transformar", "limpa + bbox", LARANJA)
    _box(pdf, x_carga, y_etl, bw, bh, "4. carregar_oracle", "MERGE", LARANJA)
    _box(pdf, x_oracle, y_etl, bw, bh, "Oracle FIAP", "3 tabelas", VERDE)

    # --- Setas: fontes -> extrair (converging) ---
    _seta(pdf, x_fontes + bw, y_firms + bh / 2,
          x_extrair, y_etl + bh / 2 - 2, CINZA)
    _seta(pdf, x_fontes + bw, y_open + bh / 2,
          x_extrair, y_etl + bh / 2 + 2, CINZA)

    # --- Setas horizontais entre tasks ---
    for x_from, x_to in (
        (x_extrair, x_stage),
        (x_stage, x_transf),
        (x_transf, x_carga),
        (x_carga, x_oracle),
    ):
        _seta(pdf, x_from + bw, y_etl + bh / 2,
              x_to, y_etl + bh / 2, CINZA)

    # --- 5a tarefa (analisar) ramificacao abaixo de transformar ---
    y_analise = y_etl + bh + 10
    _box(pdf, x_transf, y_analise, bw, bh,
         "5. analisar", "log sanity", LARANJA)
    _seta(pdf, x_transf + bw / 2, y_etl + bh,
          x_transf + bw / 2, y_analise, CINZA)

    # --- Legenda colorida ---
    y_leg = y_analise + bh + 8
    pdf.set_xy(pdf.l_margin, y_leg)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    # quadradinhos
    def chip(x, y, color, label):
        pdf.set_fill_color(*color)
        pdf.rect(x, y, 4, 4, "F")
        pdf.set_xy(x + 5, y - 0.5)
        pdf.cell(38, 4.5, label)
    chip(pdf.l_margin, y_leg, AZUL, "Fontes externas")
    chip(pdf.l_margin + 50, y_leg, LARANJA, "Tarefas Airflow")
    chip(pdf.l_margin + 100, y_leg, VERDE, "Oracle (sink)")

    # Reseta cursor
    pdf.set_y(y_leg + 8)
    pdf.set_text_color(40, 40, 40)


def capa(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("helvetica", "B", 28)
    pdf.set_text_color(*COR_TITULO)
    pdf.cell(0, 14, "PIRO", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(*COR_SUBTITULO)
    pdf.cell(0, 9, "Plataforma Integrada de Resposta Orbital",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_draw_color(*COR_DESTAQUE)
    pdf.set_line_width(0.8)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(*COR_TITULO)
    pdf.cell(0, 10, "Camada de Engenharia de Dados Orbital",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(*COR_TEXTO)
    pdf.cell(0, 8, "Big Data Architecture & Data Integration (BDDI)",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(30)

    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(*COR_TEXTO)
    pdf.cell(0, 6, "FIAP - Global Solution 2026 - 1o Semestre",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, "Engenharia de Software - 4o Ano - ESPW - Presencial",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, "Tema: Industria Espacial - O Codigo que Move o Universo",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(40)
    pdf.set_font("helvetica", "I", 10)
    pdf.set_text_color(*COR_CINZA)
    pdf.cell(0, 5,
             f"Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def secao_1_equipe(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("1. Equipe")
    pdf.tabela(
        ["Nome completo", "RM"],
        [
            ["Julia Marques", "98680"],
            ["Matheus Gusmao", "550826"],
            ["Guilherme Morais", "551981"],
        ],
        larguras=[130, 50],
    )


def secao_2_solucao(pdf: RelatorioBDDI):
    pdf.h1("2. Descricao da solucao proposta")
    pdf.p(
        "O PIRO e uma plataforma integrada que consome dados orbitais de satelites "
        "(NASA FIRMS - VIIRS), enriquece-os com dados meteorologicos (Open-Meteo), "
        "carrega de forma idempotente em Oracle Database e expoe consultas analiticas "
        "para alimentar o resto do sistema (camadas ACV de visao computacional, GAIE "
        "de aprendizado de maquina preditivo e RPA de automacao de alerta)."
    )
    pdf.p(
        "Esta entrega corresponde a camada de Engenharia de Dados Orbital (BDDI): a "
        "fundacao que consolida em um unico banco relacional, com schema estavel, todas "
        "as variaveis necessarias para que as camadas downstream operem sobre dados "
        "consistentes e auditaveis. A pipeline executa diariamente via Apache Airflow, "
        "e idempotente por construcao (MERGE no Oracle) e expoe 6 consultas analiticas."
    )
    pdf.callout(
        "Diferenciais tecnicos da entrega",
        "1) MERGE idempotente comprovado - 2 execucoes da DAG mantiveram 7.502 "
        "linhas em focos_incendio e clima_associado. 2) APIs reais como fonte "
        "primaria (NASA FIRMS multi-dia + Open-Meteo em lote, sem chave). "
        "3) Derivacao geografica UF/bioma por bounding box, sem dependencia de "
        "shapefiles. 4) Pipeline resiliente a falhas parciais de API externa - "
        "fallback de mediana garante completude do dataset."
    )


def secao_3_objetivo(pdf: RelatorioBDDI):
    pdf.h1("3. Objetivo do pipeline")
    pdf.p(
        "Transformar a lista bruta de focos de incendio detectados pelo sensor VIIRS em "
        "uma base relacional enriquecida com clima e geografia derivada, pronta para "
        "consumo analitico (consultas SQL) e por modelos de Machine Learning (camada "
        "GAIE). Especificamente:"
    )
    pdf.p(
        "  - Extrair, diariamente, todos os focos do Brasil dos ultimos 7 dias.\n"
        "  - Enriquecer cada foco com temperatura, umidade, vento e precipitacao.\n"
        "  - Derivar UF e bioma a partir da latitude/longitude.\n"
        "  - Carregar no Oracle FIAP com chave natural id_externo (lat|lon|data|hora).\n"
        "  - Garantir idempotencia: rodar a DAG N vezes nao duplica linhas.\n"
        "  - Disponibilizar 6 consultas analiticas para visao operacional do oncall."
    )


def secao_4_fonte_dados(pdf: RelatorioBDDI):
    pdf.h1("4. Fonte de dados utilizada")
    pdf.h2("4.1 NASA FIRMS - VIIRS_SNPP_NRT")
    pdf.p(
        "Endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/VIIRS_SNPP_NRT/{BBOX}/1/{DATE}"
    )
    pdf.tabela(
        ["Parametro", "Valor"],
        [
            ["Sensor", "VIIRS_SNPP_NRT (Suomi-NPP)"],
            ["Resolucao", "375m (vs 1km do MODIS)"],
            ["Bounding box Brasil", "-74, -34, -34, 6"],
            ["Estrategia", "Loop dia-a-dia (limite area x dias)"],
            ["Janela utilizada", "7 dias"],
            ["Chave de API", "Gratuita - 5.000 transacoes / 10 min"],
            ["Volume real coletado", "7.762 focos brutos"],
        ],
        larguras=[70, 110],
    )

    pdf.h2("4.2 Open-Meteo - Forecast endpoint")
    pdf.p(
        "Endpoint: https://api.open-meteo.com/v1/forecast"
    )
    pdf.tabela(
        ["Parametro", "Valor"],
        [
            ["Chave de API", "Nao requer - 100% gratuito"],
            ["Tamanho do lote", "100 coordenadas por request"],
            ["Variaveis colhidas", "temperature_2m, relative_humidity_2m, wind_speed_10m, precipitation"],
            ["Retentativas", "3 com backoff linear (1.5s x tentativa)"],
            ["Hit rate observado", "1.400 / 7.502 focos (18.6%)"],
            ["Fallback", "Imputacao por mediana em transformar()"],
        ],
        larguras=[70, 110],
    )

    pdf.h2("4.3 Oracle Database FIAP - sink analitico")
    pdf.tabela(
        ["Parametro", "Valor"],
        [
            ["Host", "oracle.fiap.com.br"],
            ["Porta", "1521"],
            ["SID", "ORCL"],
            ["Acesso", "Internet publica (sem VPN)"],
            ["Driver Python", "python-oracledb 2.2 (modo thin)"],
        ],
        larguras=[70, 110],
    )


def secao_5_arquitetura(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("5. Arquitetura do pipeline")
    pdf.p(
        "Fluxo visual: fonte -> extracao -> staging -> transformacao -> carga no "
        "Oracle -> analise SQL. Cada tarefa da DAG e fina e chama uma funcao de um "
        "modulo em src/, permitindo teste isolado fora do Airflow."
    )
    desenha_arquitetura(pdf)
    pdf.p(
        "A DAG roda em @daily com 2 retries automaticos (retry_delay=2min) e usa "
        "XCom para passar os caminhos dos CSVs intermediarios entre tarefas. A "
        "tarefa 'analisar' executa em paralelo logico apos 'transformar', gerando "
        "logs de sanity-check (top 5 estados, media FRP) que servem para validacao "
        "rapida antes de consultar o Oracle. A tarefa 'armazenar_temp' cumpre o "
        "requisito explicito do edital de existencia de um passo de armazenamento "
        "intermediario entre extracao e transformacao."
    )


def secao_6_etapas_dag(pdf: RelatorioBDDI):
    pdf.h1("6. Explicacao das etapas da DAG")
    pdf.tabela(
        ["#", "Tarefa", "Funcao chamada", "Saida XCom"],
        [
            ["1", "extrair", "extrair_focos(dias=7) + extrair_clima(focos)",
             "Caminhos: focos_raw.csv + clima_raw.csv"],
            ["2", "armazenar_temp", "pd.merge dos 2 CSVs em focos_clima.csv",
             "Caminho stage_focos_clima.csv"],
            ["3", "transformar", "transformacao.transformar(focos, clima)",
             "Caminho focos_tratados.csv"],
            ["4", "carregar_oracle", "carga_oracle.carregar(df)",
             "Numero de registros confirmados"],
            ["5", "analisar", "Sanity-check Python (top 5 estados, media FRP)",
             "Print no log"],
        ],
        larguras=[10, 35, 75, 60],
    )
    pdf.p(
        "A tarefa 2 cumpre o requisito explicito do edital de existencia de um passo de "
        "armazenamento temporario (staging) entre extracao e transformacao."
    )


def secao_7_transformacoes(pdf: RelatorioBDDI):
    pdf.h1("7. Transformacoes realizadas")
    pdf.p(
        "Sequencia aplicada em src/transformacao.py, com justificativa tecnica de cada passo:"
    )
    pdf.tabela(
        ["#", "Passo", "Por que existe"],
        [
            ["1", "dropna(latitude, longitude)", "Sem coordenada nao se geocodifica"],
            ["2", "to_datetime(data)", "Permite filtros temporais nas consultas"],
            ["3", "_normaliza_confianca", "FIRMS mistura % (MODIS) e l/n/h (VIIRS)"],
            ["4", "confianca >= 30", "Descarta deteccoes de baixa confianca"],
            ["5", "drop_duplicates(id_externo)", "Loop multi-dia FIRMS pode duplicar"],
            ["6", "merge(clima, on=id_externo)", "Anexa colunas climaticas"],
            ["7", "fillna(median()) em clima", "Trata NaN do Open-Meteo (~80% nesta execucao)"],
            ["8", "_bbox_match em UF", "Deriva UF sem dependencia geoespacial"],
            ["9", "_bbox_match em bioma", "Deriva bioma sem dependencia geoespacial"],
            ["10", "estacao_seca = (u<30 & p<1)", "Feature binaria de risco climatico"],
        ],
        larguras=[10, 60, 110],
    )


def secao_8_modelagem(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("8. Modelagem das tabelas Oracle")
    pdf.p(
        "A modelagem segue o padrao estrela do data warehouse, com focos_incendio "
        "como tabela-fato (cada linha e um evento de deteccao de foco pelo satelite) "
        "e duas tabelas-dimensao que descrevem o evento: clima_associado (condicao "
        "atmosferica no momento do foco, relacao 1:1) e imagens_satelite_metadata "
        "(saida da CNN da camada ACV, relacao 1:N). Todas costuradas pela chave "
        "natural id_externo (latitude|longitude|data|hora), garantindo que MERGE e "
        "JOINs operem sobre a mesma chave de negocio em vez de IDs surrogados."
    )
    pdf.code(
        "focos_incendio (1) ---< (1) clima_associado           (descreve o foco)\n"
        "focos_incendio (1) ---< (N) imagens_satelite_metadata (populada pela ACV)\n"
    )

    pdf.h2("8.1 focos_incendio (fato)")
    pdf.tabela(
        ["Coluna", "Tipo", "Descricao"],
        [
            ["id_foco", "NUMBER IDENTITY", "PK auto-incremento"],
            ["id_externo", "VARCHAR2(60) UNIQUE", "Chave natural lat|lon|data|hora"],
            ["latitude", "NUMBER(9,4)", "Coordenada"],
            ["longitude", "NUMBER(9,4)", "Coordenada"],
            ["data_foco", "DATE", "Data da deteccao"],
            ["satelite", "VARCHAR2(20)", "N, 1, Aqua, Terra"],
            ["confianca", "NUMBER(5,1)", "% de confianca"],
            ["brilho", "NUMBER(7,1)", "Temperatura de brilho (K)"],
            ["frp", "NUMBER(8,1)", "Fire Radiative Power (MW)"],
            ["estado", "VARCHAR2(2)", "UF por bounding box"],
            ["bioma", "VARCHAR2(20)", "Bioma por bounding box"],
        ],
        larguras=[35, 45, 100],
    )

    pdf.h2("8.2 clima_associado (1:1 com focos)")
    pdf.tabela(
        ["Coluna", "Tipo", "Descricao"],
        [
            ["id_clima", "NUMBER IDENTITY", "PK"],
            ["id_externo", "VARCHAR2(60) UNIQUE FK", "Chave do MERGE"],
            ["temperatura", "NUMBER(5,1)", "Celsius (Open-Meteo)"],
            ["umidade", "NUMBER(5,1)", "% (Open-Meteo)"],
            ["vento", "NUMBER(5,1)", "km/h"],
            ["precipitacao", "NUMBER(6,1)", "mm"],
            ["estacao_seca", "NUMBER(1)", "0/1 derivado"],
        ],
        larguras=[35, 45, 100],
    )

    pdf.h2("8.3 imagens_satelite_metadata (1:N com focos)")
    pdf.tabela(
        ["Coluna", "Tipo", "Descricao"],
        [
            ["id_imagem", "NUMBER IDENTITY", "PK"],
            ["id_externo", "VARCHAR2(60) FK", "Foco relacionado"],
            ["url_tile", "VARCHAR2(400)", "URL do tile satelite"],
            ["resolucao", "VARCHAR2(20)", "375m, 10m, etc"],
            ["classificacao", "VARCHAR2(20)", "fogo / nao_fogo (CNN)"],
            ["confianca_cnn", "NUMBER(5,1)", "% da CNN"],
        ],
        larguras=[35, 45, 100],
    )

    pdf.h2("8.4 Indices criados")
    pdf.tabela(
        ["Indice", "Coluna", "Consultas beneficiadas"],
        [
            ["idx_focos_data", "focos_incendio.data_foco", "Consultas 1 e 2"],
            ["idx_focos_estado", "focos_incendio.estado", "Consultas 1 e 6"],
            ["idx_focos_bioma", "focos_incendio.bioma", "Consultas 3 e 6"],
            ["idx_clima_idext", "clima_associado.id_externo", "JOIN clima<->focos"],
        ],
        larguras=[45, 55, 80],
    )


def secao_9_prints_airflow(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("9. Prints das execucoes no Apache Airflow")

    pdf.h2("9.1 Graph view - 5 tarefas verde")
    pdf.imagem(PRINTS_DIR / "dag_graph_verde.png",
               "Fig 1. DAG piro_pipeline_queimadas com as 5 tarefas em status SUCCESS.",
               largura=180)

    pdf.h2("9.2 DAG Runs summary - 2 execucoes")
    pdf.imagem(PRINTS_DIR / "dag_runs_2x.png",
               "Fig 2. Summary com Total success: 2, evidencia das 2 execucoes exigidas pelo edital.",
               largura=180)


def secao_10_oracle(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("10. Tabelas populadas no Oracle Database")

    pdf.h2("10.1 Contagem das tabelas apos 2 execucoes")
    pdf.tabela(
        ["Tabela", "Linhas", "Esperado"],
        [
            ["focos_incendio", "7.502", "7.502 (= apos 1 run; MERGE nao duplicou)"],
            ["clima_associado", "7.502", "7.502 (1:1 com focos)"],
            ["imagens_satelite_metadata", "0", "Sera populada pela camada ACV"],
        ],
        larguras=[60, 30, 90],
    )
    pdf.callout(
        "Prova de idempotencia via MERGE",
        "Os 7.502 focos coletados na primeira execucao (apos dedup dos 7.762 brutos) "
        "foram inseridos no Oracle. Na segunda execucao, o MERGE INTO ... WHEN NOT "
        "MATCHED THEN INSERT detectou que todos os id_externo ja existiam e nao "
        "duplicou nenhuma linha. A contagem final continua em 7.502 - definicao "
        "formal de operacao idempotente."
    )

    pdf.h2("10.2 Trecho do log da tarefa extrair")
    log_extrair = PRINTS_DIR / "log_extrair_firms.txt"
    if log_extrair.exists():
        txt = log_extrair.read_text(encoding="utf-8", errors="ignore")
        # Pega so as linhas mais informativas
        linhas_uteis = [l for l in txt.splitlines() if any(
            tag in l for tag in ("[FIRMS]", "[Open-Meteo] clima REAL",
                                 "Marking task as SUCCESS"))]
        pdf.code("\n".join(linhas_uteis[:12]) or "[log nao encontrado]")
    else:
        pdf.code("[arquivo log_extrair_firms.txt nao encontrado em reports/prints/]")

    pdf.h2("10.3 Trecho do log da tarefa carregar_oracle")
    log_carga = PRINTS_DIR / "log_carga_oracle.txt"
    if log_carga.exists():
        txt = log_carga.read_text(encoding="utf-8", errors="ignore")
        linhas_uteis = [l for l in txt.splitlines() if any(
            tag in l for tag in ("[oracle]", "[load]",
                                 "Marking task as SUCCESS",
                                 "return code 0"))]
        pdf.code("\n".join(linhas_uteis[:10]) or "[log nao encontrado]")
    else:
        pdf.code("[arquivo log_carga_oracle.txt nao encontrado em reports/prints/]")


def secao_11_consultas_sql(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("11. Consultas analiticas em SQL")
    pdf.p(
        "Arquivo completo em sql/02_consultas.sql. As 6 consultas exercitam, no minimo, "
        "WHERE, GROUP BY, JOIN (inclusive de 3 tabelas), HAVING, agregacoes "
        "(COUNT/AVG/MIN/MAX/SUM), ORDER BY, FETCH FIRST e funcoes temporais."
    )
    if SQL_FILE.exists():
        pdf.code(SQL_FILE.read_text(encoding="utf-8", errors="ignore"))
    else:
        pdf.code("[02_consultas.sql nao encontrado]")


def secao_12_resultados(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("12. Resultados obtidos pelas consultas")

    pdf.h2("Consulta 1 - Ranking de estados (ultimo mes)")
    pdf.tabela(
        ["estado", "total_focos", "frp_medio"],
        [
            ["MT", "2.345", "6,8"],
            ["??", "1.349", "5,5"],
            ["TO", "909", "10,4"],
            ["PA", "753", "7,8"],
            ["MA", "362", "7,4"],
            ["BA", "357", "7,4"],
            ["MG", "351", "4,2"],
            ["AM", "287", "7,1"],
            ["MS", "206", "5,3"],
            ["RO", "206", "8,4"],
        ],
        larguras=[40, 70, 70],
    )
    pdf.p(
        "Leitura: Mato Grosso lidera com 31% do total. Os 1.349 focos com estado '??' "
        "sao pontos fora das 19 bounding boxes embutidas em transformacao.py (limitacao "
        "documentada). Top-5 estados validos: MT, TO, PA, MA, BA - eixo classico do "
        "Arco do Desmatamento."
    )

    pdf.h2("Consulta 2 - Evolucao diaria")
    pdf.tabela(
        ["dia", "focos_no_dia"],
        [
            ["2026-05-27", "1.525"],
            ["2026-05-28", "1.696"],
            ["2026-05-29", "1.306"],
            ["2026-05-30", "962"],
            ["2026-05-31", "1.015"],
            ["2026-06-02", "998"],
        ],
        larguras=[80, 100],
    )

    pdf.h2("Consulta 3 - Clima x focos por bioma (JOIN)")
    pdf.tabela(
        ["bioma", "qtd_focos", "temp_media", "umidade_media", "vento_medio", "focos_em_seca"],
        [
            ["Cerrado", "2.823", "25,3", "68,3", "7,7", "0"],
            ["Mata Atlantica", "1.569", "25,5", "66,7", "7,6", "0"],
            ["Desconhecido", "1.480", "24,9", "71,0", "7,3", "4"],
            ["Amazonia", "1.056", "25,9", "67,3", "7,6", "0"],
            ["Caatinga", "382", "25,3", "68,7", "8,1", "0"],
            ["Pampa", "102", "23,9", "70,8", "8,1", "0"],
            ["Pantanal", "90", "25,4", "68,9", "7,3", "0"],
        ],
        larguras=[40, 25, 30, 35, 25, 30],
    )

    pdf.add_page()
    pdf.h2("Consulta 4 - Top 10 areas criticas por FRP")
    pdf.tabela(
        ["UF", "Bioma", "FRP (MW)", "Brilho (K)", "Data"],
        [
            ["MT", "Cerrado", "214,0", "342,8", "2026-05-31"],
            ["TO", "Mata Atlantica", "195,0", "367,0", "2026-05-30"],
            ["GO", "Cerrado", "176,5", "354,4", "2026-05-28"],
            ["MT", "Cerrado", "172,6", "349,8", "2026-06-02"],
            ["BA", "Caatinga", "164,5", "367,0", "2026-05-29"],
            ["TO", "Cerrado", "150,1", "352,0", "2026-05-31"],
            ["MT", "Cerrado", "147,7", "357,5", "2026-06-02"],
            ["MT", "Cerrado", "130,5", "353,9", "2026-05-30"],
            ["MT", "Cerrado", "130,5", "367,0", "2026-05-30"],
            ["TO", "Mata Atlantica", "129,7", "352,4", "2026-06-02"],
        ],
        larguras=[20, 50, 35, 35, 40],
    )
    pdf.p(
        "7 dos 10 maiores focos estao em MT/Cerrado. Cinco deles concentrados em "
        "-14,0 lat x -58,8 lon - provavel incendio unico de grande extensao detectado "
        "como multiplos pontos pelo sensor VIIRS. Exatamente o tipo de evento que o "
        "modelo GAIE precisa marcar como alto_risco."
    )

    pdf.h2("Consulta 5 - Estatisticas por satelite (HAVING)")
    pdf.tabela(
        ["satelite", "qtd", "frp_min", "frp_medio", "frp_max", "confianca_media"],
        [
            ["N (VIIRS Suomi-NPP)", "7.502", "0,1", "7,1", "214,0", "66,3"],
        ],
        larguras=[55, 25, 25, 30, 25, 30],
    )

    pdf.h2("Consulta 6 - JOIN de 3 tabelas (focos x clima x imagens CNN)")
    pdf.p(
        "JOIN de 3 tabelas (focos_incendio + clima_associado + imagens_satelite_metadata) "
        "com filtro composto. A versao inicial usava f.frp > 100 AND c.umidade < 35, mas "
        "a interseccao retornava vazia porque a falha parcial do Open-Meteo deixou 78% "
        "dos focos com mediana imputada (umidade ~68%, incompativel com < 35). Limiar "
        "ajustado para f.frp > 50, preservando o JOIN de 3 tabelas e o conceito de 'foco "
        "intenso' enquanto entrega dados utilizaveis. O LEFT JOIN com "
        "imagens_satelite_metadata antecipa a integracao com a camada ACV."
    )
    pdf.code(ler_consulta_de_txt(6))

    pdf.callout(
        "Observacao tecnica - estacao_seca quase sempre zero",
        "A consulta 3 mostra focos_em_seca = 0 em quase todos os biomas. Isso nao e bug "
        "da regra de derivacao (umidade<30 AND precipitacao<1) e sim consequencia direta "
        "da falha parcial do Open-Meteo nesta execucao: 78% dos focos ficaram com "
        "umidade=mediana=68%, valor incompativel com o predicado de seca. A proxima "
        "iteracao usara batches menores (50 coords) e sleep maior (1,5s) para elevar o "
        "hit rate do Open-Meteo a >80%."
    )


def secao_13_conclusao(pdf: RelatorioBDDI):
    pdf.add_page()
    pdf.h1("13. Conclusao tecnica da equipe")
    pdf.p(
        "A camada BDDI do PIRO entrega uma pipeline completa, idempotente e auditavel, "
        "que ingere dados reais da NASA FIRMS e da Open-Meteo, processa em Python via "
        "DAG Airflow com 5 tarefas encadeadas, e carrega no Oracle Database FIAP via "
        "MERGE. Em homologacao, 7.502 focos do periodo 27/05 a 02/06/2026 foram "
        "processados, sobreviveram a duas execucoes consecutivas da DAG sem duplicacao "
        "e foram analisados por 6 consultas SQL cobrindo ranking por estado, evolucao "
        "temporal, correlacao clima/bioma, top FRP, estatisticas por satelite e join de "
        "tres tabelas."
    )
    pdf.h2("Pontos fortes da implementacao")
    pdf.p(
        "  - APIs reais como fonte primaria (nao demonstracao com mock).\n"
        "  - Separacao limpa entre DAG (orquestracao) e src/ (logica), com cada modulo testavel.\n"
        "  - MERGE idempotente comprovado experimentalmente (contagem estavel apos 2 runs).\n"
        "  - Resiliencia a falha parcial: pipeline conclui em verde mesmo com 78% dos\n"
        "    clima requests falhando, gracas ao fillna(median()) em transformacao.\n"
        "  - Modelagem em estrela com indices justificados pelas consultas-alvo."
    )
    pdf.h2("Limitacoes identificadas")
    pdf.p(
        "  - Hit rate baixo do Open-Meteo (18.6%) por rate-limit interno - sera mitigado\n"
        "    com batches menores e sleep maior na proxima iteracao.\n"
        "  - Derivacao UF/bioma por bounding box gera 1.349 focos com estado '??' \n"
        "    (estados de fronteira curva). PostGIS ou shapefiles do IBGE resolveriam.\n"
        "  - estacao_seca artificialmente baixo nas consultas devido a mediana imputada\n"
        "    de umidade - dependente da correcao do hit rate do Open-Meteo.\n"
        "  - Sem captura de evolucao temporal (mesmo foco re-detectado): atual MERGE\n"
        "    INSERT-only descarta updates. Requer WHEN MATCHED THEN UPDATE para v2."
    )
    pdf.ln(4)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(*COR_CINZA)
    pdf.cell(0, 5,
             "PIRO - Camada de Engenharia de Dados Orbital - "
             "Pipeline real com dados reais.",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf = RelatorioBDDI(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)

    capa(pdf)
    secao_1_equipe(pdf)
    secao_2_solucao(pdf)
    secao_3_objetivo(pdf)
    secao_4_fonte_dados(pdf)
    secao_5_arquitetura(pdf)
    secao_6_etapas_dag(pdf)
    secao_7_transformacoes(pdf)
    secao_8_modelagem(pdf)
    secao_9_prints_airflow(pdf)
    secao_10_oracle(pdf)
    secao_11_consultas_sql(pdf)
    secao_12_resultados(pdf)
    secao_13_conclusao(pdf)

    pdf.output(str(PDF_PATH))
    print(f"[OK] {PDF_PATH} ({PDF_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
