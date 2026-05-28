# -*- coding: utf-8 -*-
"""Teste de ponta a ponta — critérios de aceite (DoD) do pipeline PDF-primário."""
import pytest

from app import latex_compiler
from app.config import Config
from app.pipeline import run


def _tectonic_available() -> bool:
    return Config().tectonic_path.exists()


@pytest.mark.skipif(not _tectonic_available(),
                    reason="Tectonic binary não encontrado em bin/")
def test_end_to_end_dod(tmp_path, fixture_xlsx):
    out_pdf = tmp_path / "relatorio.pdf"
    result = run(fixture_xlsx, out_pdf=out_pdf,
                 out_docx=tmp_path / "relatorio.docx",
                 config=Config(), skip_docx=True)  # DOCX opcional, pulado aqui

    # 1) PDF gerado e baixável
    assert out_pdf.exists() and out_pdf.stat().st_size > 0
    assert result.pdf_path == out_pdf

    # 2) Sem '<<' ou '>>' no PDF
    assert latex_compiler.check_no_placeholders(out_pdf) == []

    # 3) PDF tem múltiplas páginas (template abnTeX2 completo)
    assert result.summary["pages"] > 10

    # 4) Conflito reportado nos avisos
    assert any("consumoTotal" in w for w in result.warnings)

    # 5) Valores formatados presentes
    try:
        import fitz
        with fitz.open(out_pdf) as doc:
            text = "".join(p.get_text() for p in doc)
    except ImportError:
        import pypdf
        text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out_pdf)).pages)
    assert "05/03/2026" in text
    assert "4.707,45" in text or "1.976,93" in text  # números pt-BR


@pytest.mark.skipif(not _tectonic_available(), reason="Tectonic não encontrado")
def test_original_template_not_mutated(fixture_xlsx, tmp_path):
    config = Config()
    cap8 = config.template_dir / "capitulo8.tex"
    before = cap8.read_text(encoding="utf-8")
    run(fixture_xlsx, out_pdf=tmp_path / "r.pdf", config=config, skip_docx=True)
    after = cap8.read_text(encoding="utf-8")
    assert before == after
    assert "<<" in after  # template-fonte mantém as chaves
