# -*- coding: utf-8 -*-
from pathlib import Path

from app import latex_filler
from app.config import Config


def _write_tex(workdir: Path, name: str, content: str) -> Path:
    p = workdir / name
    p.write_text(content, encoding="utf-8")
    return p


def test_exact_token_no_prefix_collision(tmp_path):
    """<<consumoTotal>> não deve casar dentro de <<ConsumoTotalUm>>."""
    _write_tex(tmp_path, "capitulo1.tex",
               r"Total=<<consumoTotal>> Mes1=<<ConsumoTotalUm>>")
    resolved = {"<<consumoTotal>>": 18.74, "<<ConsumoTotalUm>>": 996.6}
    latex_filler.substitute(tmp_path, resolved, Config())
    out = (tmp_path / "capitulo1.tex").read_text(encoding="utf-8")
    assert "Total=18,74 " in out
    assert "Mes1=996,6" in out
    assert "<<" not in out and ">>" not in out


def test_missing_in_planilha_uses_placeholder(tmp_path):
    _write_tex(tmp_path, "capitulo1.tex", r"Valor=<<naoExiste>>")
    report = latex_filler.substitute(tmp_path, {}, Config(missing_placeholder="—"))
    out = (tmp_path / "capitulo1.tex").read_text(encoding="utf-8")
    assert "Valor=—" in out
    assert "<<naoExiste>>" in report.missing_in_planilha


def test_planilha_only_detected(tmp_path):
    _write_tex(tmp_path, "capitulo1.tex", r"X=<<usada>>")
    report = latex_filler.substitute(tmp_path, {"<<usada>>": 1, "<<extra>>": 2}, Config())
    assert "<<extra>>" in report.planilha_only


def test_normalize_unicode_replaces_dashes(tmp_path):
    _write_tex(tmp_path, "capitulo1.tex", "linha — fim; outra – aqui; ponto …")
    latex_filler.normalize_unicode_for_latex(tmp_path, Config())
    out = (tmp_path / "capitulo1.tex").read_text(encoding="utf-8")
    assert "—" not in out and "–" not in out and "…" not in out
    assert "---" in out and "--" in out and r"\ldots{}" in out


def test_normalize_unicode_superscripts_and_symbols(tmp_path):
    """Sobrescritos/símbolos (m², CO₂, µ, °, nº, ½, ×) viram comandos LaTeX."""
    _write_tex(tmp_path, "capitulo1.tex",
               "Area de 50 m² e CO₂; µg a 25°C; nº 920; "
               "½ kWh; 3 × 4; 1ª etapa")
    latex_filler.normalize_unicode_for_latex(tmp_path, Config())
    out = (tmp_path / "capitulo1.tex").read_text(encoding="utf-8")
    # nenhum caractere problemático sobra
    for ch in ("²", "₂", "µ", "°", "º", "½", "×", "ª"):
        assert ch not in out
    assert r"m\textsuperscript{2}" in out
    assert r"\textsubscript{2}" in out
    assert r"\textmu{}" in out
    assert r"\textdegree{}" in out
    assert r"n\textordmasculine{}" in out
    assert r"\textonehalf{}" in out
    assert r"\texttimes{}" in out


def test_normalize_also_covers_bib(tmp_path):
    """A normalização cobre .bib (bibliografia), não só .tex."""
    (tmp_path / "ref.bib").write_text(
        "@misc{x, title={Resolucao nº 920 e 10 m²}}", encoding="utf-8")
    latex_filler.normalize_unicode_for_latex(tmp_path, Config())
    out = (tmp_path / "ref.bib").read_text(encoding="utf-8")
    assert "º" not in out and "²" not in out
    assert r"\textordmasculine{}" in out and r"\textsuperscript{2}" in out


def test_ensure_referenced_images_creates_placeholders(tmp_path):
    _write_tex(tmp_path, "capitulo1.tex",
               r"\includegraphics{Figuras/Foto}\includegraphics{Figuras/ssa3.png}")
    (tmp_path / "Figuras").mkdir()
    # ssa3.png existe; Foto não
    (tmp_path / "Figuras" / "ssa3.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    created = latex_filler.ensure_referenced_images(tmp_path, Config())
    assert any("Foto.png" in c for c in created)
    assert (tmp_path / "Figuras" / "Foto.png").exists()
    # imagem existente não é regerada
    assert all("ssa3" not in c for c in created)


def test_count_braces_ignores_escaped_and_comments():
    assert latex_filler.count_braces(r"{a}{b}") == (2, 2)
    assert latex_filler.count_braces(r"\{ \} {x}") == (1, 1)
    assert latex_filler.count_braces("{a} % {comment}") == (1, 1)


def test_unsubstituted_tokens_detects_leftover(tmp_path):
    _write_tex(tmp_path, "capitulo1.tex", r"Texto sem chaves.")
    _write_tex(tmp_path, "capitulo2.tex", r"Tem uma <<chaveOrfa>> aqui.")
    leftover = latex_filler.unsubstituted_tokens(tmp_path)
    assert leftover == ["<<chaveOrfa>>"]


def test_full_fill_no_leftover_no_brace_warnings(model_load_result):
    """Após o fill com o modelo novo, nenhum <<...>> sobra nos .tex e os
    capítulos têm chaves balanceadas (chaves ausentes viram placeholder, não
    deixam token)."""
    config = Config()
    workdir = latex_filler.prepare_workdir(config)
    try:
        report = latex_filler.fill_template(model_load_result.resolved, config, workdir=workdir)
        assert latex_filler.unsubstituted_tokens(workdir) == []
        assert report.brace_warnings == []
    finally:
        import shutil
        shutil.rmtree(workdir.parent, ignore_errors=True)
