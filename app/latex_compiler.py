"""Compilação LaTeX -> PDF via Tectonic + verificação obrigatória.

Tectonic é um engine XeLaTeX portátil em um único binário, que baixa pacotes
do CTAN sob demanda. Foi escolhido porque:

* **Não precisa de admin**: o binário fica em ``bin/`` do projeto.
* **Auto-suficiente**: baixa abntex2 e todos os pacotes na primeira execução
  (cacheado pelo SO depois).
* **Estável**: equivalente a ``latexmk -xelatex``, mas sem precisar instalar
  uma distribuição TeX inteira (~5–8 GB).

Após compilar, **falha o build** se o PDF contiver qualquer ``<<`` ou ``>>``
(substituição incompleta) — critério obrigatório da DoD.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)

_LEFTOVER = re.compile(r"<<[^<>]+>>|<<|>>")


class CompilationError(RuntimeError):
    """Falha de compilação ou de verificação pós-compilação."""


@dataclass
class CompilationResult:
    pdf_path: Path
    page_count: int = 0
    placeholder_violations: list[str] = field(default_factory=list)
    tectonic_stdout: str = ""
    tectonic_stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.pdf_path.exists() and not self.placeholder_violations


# --------------------------------------------------------------------------- #
def compile_pdf(workdir: Path, out_pdf: Path, config: Config) -> Path:
    """Compila ``workdir/DIAG_PMS.tex`` para PDF e copia para ``out_pdf``."""
    if not config.tectonic_path.exists():
        raise CompilationError(
            f"Tectonic não encontrado em {config.tectonic_path}. "
            "Rode o setup ou baixe o binário em "
            "https://github.com/tectonic-typesetting/tectonic/releases."
        )
    main_tex = workdir / config.main_tex_name
    if not main_tex.exists():
        raise CompilationError(f"Arquivo principal não encontrado: {main_tex}")

    out_pdf = Path(out_pdf).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(config.tectonic_path), *config.tectonic_extra_args,
           "--outdir", str(workdir), str(main_tex)]
    logger.info("Compilando com Tectonic: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(workdir), encoding="utf-8",
    )
    logger.debug("Tectonic stdout (últimas linhas):\n%s",
                 "\n".join((proc.stdout or "").splitlines()[-15:]))
    if proc.stderr:
        logger.debug("Tectonic stderr (últimas linhas):\n%s",
                     "\n".join(proc.stderr.splitlines()[-15:]))

    pdf_in_workdir = workdir / Path(config.main_tex_name).with_suffix(".pdf").name
    if not pdf_in_workdir.exists() or pdf_in_workdir.stat().st_size == 0:
        raise CompilationError(
            f"Tectonic não gerou PDF (exit={proc.returncode}). "
            f"Últimas linhas do stderr:\n{(proc.stderr or '')[-1500:]}"
        )

    import shutil
    shutil.copy2(pdf_in_workdir, out_pdf)
    logger.info("PDF gerado: %s (%d bytes)", out_pdf, out_pdf.stat().st_size)
    return out_pdf


# --------------------------------------------------------------------------- #
def check_no_placeholders(pdf_path: Path) -> list[str]:
    """Extrai o texto do PDF e devolve a lista de ocorrências ``<<...>>``."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
    else:
        with fitz.open(str(pdf_path)) as doc:
            text = "".join(p.get_text() for p in doc)
    violations = sorted(set(_LEFTOVER.findall(text)))
    if violations:
        logger.error("Tokens '<<'/'>>' remanescentes no PDF: %s", violations)
    return violations


def count_pages(pdf_path: Path) -> int:
    try:
        import fitz
    except ImportError:
        import pypdf
        return len(pypdf.PdfReader(str(pdf_path)).pages)
    with fitz.open(str(pdf_path)) as doc:
        return doc.page_count


# --------------------------------------------------------------------------- #
def compile_and_verify(
    workdir: Path, out_pdf: Path, config: Config
) -> CompilationResult:
    """Compila e roda a verificação anti-``<<>>``; lança
    :class:`CompilationError` se a DoD não passar."""
    pdf = compile_pdf(workdir, out_pdf, config)
    violations = check_no_placeholders(pdf)
    pages = count_pages(pdf)
    result = CompilationResult(pdf_path=pdf, page_count=pages,
                               placeholder_violations=violations)
    if violations:
        raise CompilationError(
            f"PDF contém tokens não substituídos: {violations}. Build abortado."
        )
    logger.info("Verificação OK: %d páginas, sem '<<>>' remanescente.", pages)
    return result
