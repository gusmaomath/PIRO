"""PIRO · BDDI — Utilitario: criar tabelas e rodar as 6 consultas.

Uso:
    python scripts/database.py setup   # aplica sql/01_modelagem.sql
    python scripts/database.py query   # imprime contagem + 6 consultas analiticas
    python scripts/database.py both    # setup + query

Importa apenas oracledb (sem Airflow) — roda na sua maquina com a VPN da FIAP.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante que src/ esta no sys.path independente da forma de invocacao.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from carga_oracle import conectar
from config import SQL_DIR

try:
    import oracledb
except ImportError:  # pragma: no cover
    oracledb = None  # type: ignore

SCHEMA_SQL = SQL_DIR / "01_modelagem.sql"
CONSULTAS_SQL = SQL_DIR / "02_consultas.sql"
ERROS_OK = ("ORA-00955", "ORA-01408", "ORA-02260", "ORA-02275")


def _statements(texto: str):
    """Divide um arquivo SQL em statements (separador ; / em linha propria).

    Remove comentarios de linha (-- ...) ANTES de dividir por ';', porque
    um ';' dentro de comentario quebrava o parser ingenuo (ex.: a Consulta 6
    tem '; filtros compostos' no cabecalho).
    """
    # 1) Tira comentarios linha a linha
    sem_coment = "\n".join(
        l for l in texto.replace("\r\n", "\n").splitlines()
        if not l.strip().startswith("--")
    )
    # 2) Separa em statements por '\n/\n' (PL/SQL) e depois ';'
    saidas = []
    for bloco in sem_coment.split("\n/\n"):
        for raw in bloco.split(";"):
            stmt = raw.strip()
            if stmt:
                saidas.append(stmt)
    return saidas


def setup():
    print(f"[setup] aplicando {SCHEMA_SQL.name} ...")
    with conectar() as cx, cx.cursor() as cur:
        for stmt in _statements(SCHEMA_SQL.read_text(encoding="utf-8")):
            head = stmt.splitlines()[0][:60]
            try:
                cur.execute(stmt)
                print(f"  [OK]   {head}")
            except oracledb.DatabaseError as e:  # type: ignore
                err, = e.args
                if any(c in err.message for c in ERROS_OK):
                    print(f"  [skip] {head}  (objeto ja existe)")
                else:
                    print(f"  [ERRO] {head}: {err.message}")
        cx.commit()
    print("[setup] concluido.")


def consultas():
    """Imprime contagens + cada uma das 6 consultas analiticas."""
    print("[query] contagens:")
    with conectar() as cx, cx.cursor() as cur:
        for t in ("focos_incendio", "clima_associado", "imagens_satelite_metadata"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                print(f"  {t}: {cur.fetchone()[0]} linhas")
            except Exception as e:
                print(f"  {t}: erro ({e})")
        for i, stmt in enumerate(_statements(CONSULTAS_SQL.read_text(encoding="utf-8")), 1):
            head = stmt.splitlines()[0][:70]
            print(f"\n========== Consulta {i}: {head} ==========")
            try:
                cur.execute(stmt)
                cols = [c[0] for c in cur.description]
                print(" | ".join(cols))
                for row in cur.fetchmany(10):
                    print(" | ".join(str(v) for v in row))
            except Exception as e:
                print(f"[ERRO] {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["setup", "query", "both"])
    args = ap.parse_args()
    if args.acao in ("setup", "both"):
        setup()
    if args.acao in ("query", "both"):
        consultas()
