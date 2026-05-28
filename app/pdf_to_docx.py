"""Conversão PDF -> DOCX via LibreOffice headless (deliverable SECUNDÁRIO).

O DOCX é uma **cópia adaptada** com fidelidade parcial — algumas tabelas e
espaçamentos podem reorganizar. Sempre que possível use o PDF (deliverable
oficial).

Se LibreOffice **não** estiver instalado, a conversão é pulada com aviso
claro; o pipeline continua e entrega o PDF normalmente.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


class LibreOfficeNotFound(RuntimeError):
    """LibreOffice não está instalado no ambiente."""


@dataclass
class DocxResult:
    docx_path: Path | None
    skipped_reason: str | None = None
    libreoffice_used: Path | None = None

    @property
    def ok(self) -> bool:
        return self.docx_path is not None and self.docx_path.exists()


# --------------------------------------------------------------------------- #
def convert_pdf_to_docx(
    pdf_path: Path, out_docx: Path, config: Config
) -> DocxResult:
    """Converte ``pdf_path`` -> ``out_docx`` via ``soffice --headless``.

    Retorna :class:`DocxResult`. **Não lança** se o LibreOffice não estiver
    instalado: devolve ``DocxResult(docx_path=None, skipped_reason=...)`` para
    que o pipeline continue sem erro.
    """
    soffice = config.find_libreoffice()
    if soffice is None:
        msg = ("LibreOffice não encontrado — conversão para DOCX pulada. "
               "Instale: https://www.libreoffice.org/download/ (Windows) "
               "ou 'apt install libreoffice' (Linux). "
               "O PDF é o deliverable primário; o DOCX é opcional.")
        logger.warning(msg)
        return DocxResult(docx_path=None, skipped_reason=msg)

    out_docx = Path(out_docx).resolve()
    out_docx.parent.mkdir(parents=True, exist_ok=True)

    # LibreOffice escreve em --outdir com o mesmo nome (extensão trocada),
    # então usamos um tmpdir intermediário para controlar o nome final.
    with tempfile.TemporaryDirectory(prefix="diag_docx_") as tmpdir:
        cmd = [str(soffice), "--headless", "--norestore", "--nologo",
               "--convert-to", "docx", "--outdir", tmpdir, str(pdf_path)]
        logger.info("Convertendo PDF -> DOCX via LibreOffice: %s", soffice)
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", timeout=180)
        if proc.returncode != 0:
            msg = (f"LibreOffice falhou (exit={proc.returncode}): "
                   f"{(proc.stderr or proc.stdout or '')[-500:]}")
            logger.error(msg)
            return DocxResult(docx_path=None, skipped_reason=msg,
                              libreoffice_used=soffice)

        produced = Path(tmpdir) / (Path(pdf_path).stem + ".docx")
        if not produced.exists():
            return DocxResult(docx_path=None, skipped_reason=(
                "LibreOffice não produziu .docx. stdout: "
                f"{(proc.stdout or '')[-300:]}"
            ), libreoffice_used=soffice)
        shutil.copy2(produced, out_docx)

    logger.info("DOCX (best-effort) gerado: %s (%d bytes)",
                out_docx, out_docx.stat().st_size)
    return DocxResult(docx_path=out_docx, libreoffice_used=soffice)
