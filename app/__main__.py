"""Entrypoint de linha de comando.

Uso:
    python -m app <planilha.xlsx> [saida.pdf] [opções]

Opções:
    --docx PATH        caminho do DOCX (default: ao lado do PDF)
    --skip-docx        não tenta gerar DOCX
    --keep-workdir     mantém o diretório de compilação para inspeção
    --first-wins       política de conflito first-wins (default: last-wins)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import Config
from app.latex_compiler import CompilationError
from app.pipeline import run, setup_logging


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Gera o relatório PDF (e opcionalmente DOCX) a partir da planilha .xlsx",
    )
    p.add_argument("xlsx", type=Path, help="Planilha de diagnóstico (.xlsx)")
    p.add_argument("pdf", type=Path, nargs="?", default=None, help="Saída .pdf (opcional)")
    p.add_argument("--docx", type=Path, default=None, help="Saída .docx (opcional)")
    p.add_argument("--skip-docx", action="store_true", help="Pula a conversão para DOCX")
    p.add_argument("--keep-workdir", action="store_true", help="Mantém diretório temporário")
    p.add_argument("--first-wins", action="store_true", help="Política first-wins de conflito")
    args = p.parse_args(argv)

    setup_logging()
    config = Config(conflict_policy="first-wins" if args.first_wins else "last-wins")

    try:
        result = run(
            args.xlsx, out_pdf=args.pdf, out_docx=args.docx,
            config=config, keep_workdir=args.keep_workdir,
            skip_docx=args.skip_docx,
        )
    except (FileNotFoundError, KeyError, CompilationError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(f"\nOK: PDF gerado em {result.pdf_path}")
    if result.docx_path:
        print(f"     DOCX (best-effort) em {result.docx_path}")
    elif result.docx_skipped_reason:
        print(f"     DOCX pulado: {result.docx_skipped_reason}")
    if result.warnings:
        print("\nAvisos:")
        for w in result.warnings:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
