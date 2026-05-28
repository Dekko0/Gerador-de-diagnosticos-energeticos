# -*- coding: utf-8 -*-
"""Testes do compilador Tectonic. Requer ``bin/tectonic.exe``; pulados se ausente."""
from pathlib import Path

import pytest

from app import latex_compiler
from app.config import Config


def _has_tectonic() -> bool:
    return Config().tectonic_path.exists()


@pytest.mark.skipif(not _has_tectonic(),
                    reason="Tectonic binary não encontrado em bin/")
def test_compile_minimal_doc(tmp_path):
    cfg = Config(template_dir=tmp_path / "tpl")
    (cfg.template_dir).mkdir()
    main = cfg.template_dir / "DIAG_PMS.tex"
    main.write_text(r"\documentclass{article}\begin{document}Olá mundo.\end{document}",
                    encoding="utf-8")
    pdf = latex_compiler.compile_pdf(cfg.template_dir, tmp_path / "out.pdf", cfg)
    assert pdf.exists() and pdf.stat().st_size > 0


def test_check_no_placeholders_regex():
    """xelatex renderiza '<<' '>>' como guillemets; o check é defesa em
    profundidade. A verificação **autoritativa** é em ``latex_filler.unsubstituted_tokens``.
    """
    assert latex_compiler._LEFTOVER.findall("ok") == []
    assert latex_compiler._LEFTOVER.findall("foo <<bar>> baz") == ["<<bar>>"]
    # token completo casa primeiro (greedy alternation)
    assert latex_compiler._LEFTOVER.findall("<< stray >>") == ["<< stray >>"]
    # stray '<<' isolado
    assert latex_compiler._LEFTOVER.findall("only << here") == ["<<"]
