# -*- coding: utf-8 -*-
"""Teste de ponta a ponta — critérios de aceite (DoD) do pipeline PDF-primário."""
import re

import pytest

from app import latex_compiler
from app.config import Config
from app.pipeline import run

#: Número no padrão pt-BR (milhar '.', decimal ','), ex.: "1.976,93".
_PTBR_NUMBER = re.compile(r"\d{1,3}(\.\d{3})*,\d{2}")


def _tectonic_available() -> bool:
    return Config().tectonic_path.exists()


@pytest.mark.skipif(not _tectonic_available(),
                    reason="Tectonic binary não encontrado em bin/")
def test_end_to_end_dod(tmp_path, fixture_xlsx):
    out_pdf = tmp_path / "relatorio.pdf"
    result = run(fixture_xlsx, out_pdf=out_pdf, config=Config())

    # 1) PDF gerado e baixável
    assert out_pdf.exists() and out_pdf.stat().st_size > 0
    assert result.pdf_path == out_pdf

    # 2) Sem '<<' ou '>>' no PDF
    assert latex_compiler.check_no_placeholders(out_pdf) == []

    # 3) PDF tem múltiplas páginas (template abnTeX2 completo)
    assert result.summary["pages"] > 10

    # 4) Valores formatados presentes
    try:
        import fitz
        with fitz.open(out_pdf) as doc:
            text = "".join(p.get_text() for p in doc)
    except ImportError:
        import pypdf
        text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out_pdf)).pages)
    assert "27/01/2026" in text                 # data formatada (dd/mm/aaaa)
    assert _PTBR_NUMBER.search(text)            # há número no padrão pt-BR
    # Regressão do bug nº→nz: o glifo quebrado do ordinal (ž) não deve aparecer.
    assert "ž" not in text


@pytest.mark.skipif(not _tectonic_available(),
                    reason="Tectonic binary não encontrado em bin/")
def test_end_to_end_model_compiles(tmp_path, model_xlsx):
    """Compila o template novo com o modelo (RD_MODELO) de ponta a ponta."""
    out_pdf = tmp_path / "modelo.pdf"
    result = run(model_xlsx, out_pdf=out_pdf, config=Config())
    assert out_pdf.exists() and out_pdf.stat().st_size > 0
    assert latex_compiler.check_no_placeholders(out_pdf) == []
    assert result.summary["pages"] > 10
    # Bug do ordinal (nº) e dos sobrescritos: glifo quebrado não deve aparecer.
    try:
        import fitz
        with fitz.open(out_pdf) as doc:
            text = "".join(p.get_text() for p in doc)
    except ImportError:
        import pypdf
        text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out_pdf)).pages)
    assert "ž" not in text


@pytest.mark.skipif(not _tectonic_available(), reason="Tectonic não encontrado")
def test_original_template_not_mutated(model_xlsx, tmp_path):
    config = Config()
    main_tex = config.template_dir / "DIAG_PMS.tex"  # contém <<nomeUc>>, <<data>>
    before = main_tex.read_text(encoding="utf-8")
    run(model_xlsx, out_pdf=tmp_path / "r.pdf", config=config)
    after = main_tex.read_text(encoding="utf-8")
    assert before == after
    assert "<<" in after  # template-fonte mantém as chaves
