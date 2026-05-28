"""Orquestração do pipeline: planilha ``.xlsx`` -> template -> **PDF**.

PDF é o deliverable final (100% fiel ao template LaTeX/abnTeX2), compilado por
Tectonic.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import charts, excel_loader, latex_compiler, latex_filler
from .config import Config

#: Callback opcional ``(stage_label, fraction_0_to_1)`` chamado em cada fase
#: do pipeline. Permite à UI exibir um progresso por etapa (UX).
ProgressCallback = Callable[[str, float], None]

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    pdf_path: Path
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
    root.setLevel(level)


def run(
    xlsx_path: str | Path,
    out_pdf: str | Path | None = None,
    config: Config | None = None,
    keep_workdir: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    """Executa o pipeline completo.

    * ``out_pdf`` — caminho do PDF final. Default: ``output/<stem>.pdf``.
    * ``progress_callback`` — opcional. Recebe ``(label, fraction)`` em cada
      etapa. ``fraction`` está em ``[0, 1]``.
    """
    config = config or Config()
    xlsx_path = Path(xlsx_path)
    stem = xlsx_path.stem
    out_pdf = Path(out_pdf) if out_pdf else Path("output") / f"{stem}.pdf"

    def _progress(label: str, fraction: float) -> None:
        if progress_callback is not None:
            try:
                progress_callback(label, fraction)
            except Exception:  # noqa: BLE001
                logger.exception("progress_callback falhou (ignorado)")

    warnings: list[str] = []
    info: list[str] = []

    # 1) Ler a planilha -----------------------------------------------------
    _progress("Lendo planilha", 0.05)
    load = excel_loader.load(xlsx_path, config)
    info.append(f"{len(load.resolved)} chaves lidas da planilha.")
    for c in load.conflicts:
        warnings.append(f"Conflito de chave duplicada — {c.describe()}")
    warnings.extend(load.marker_warnings)
    if load.pie.dropped_zero:
        info.append(f"Gráfico 1: fatias zero omitidas: {load.pie.dropped_zero}")
    if load.bar.dropped:
        info.append(f"Gráfico 2: {len(load.bar.dropped)} mês(es) descartado(s).")

    # 2) Preparar cópia de trabalho do template ----------------------------
    _progress("Preparando template", 0.15)
    workdir = latex_filler.prepare_workdir(config)
    base_tmp = workdir.parent
    try:
        # 3) Gerar gráficos -------------------------------------------------
        _progress("Gerando gráficos", 0.25)
        figures_dir = workdir / config.figures_subdir
        charts.generate_charts(load, figures_dir, config)

        # 4) Substituir chaves + normalizar Unicode + placeholders ----------
        _progress("Substituindo chaves no LaTeX", 0.40)
        fill = latex_filler.fill_template(load.resolved, config, workdir=workdir)
        warnings.extend(fill.brace_warnings)
        if fill.missing_in_planilha:
            warnings.append(
                f"Chaves no LaTeX sem valor (-> '{config.missing_placeholder}'): "
                f"{fill.missing_in_planilha}"
            )
        if fill.planilha_only:
            info.append(f"Chaves só na planilha (ignoradas): {fill.planilha_only}")
        if fill.placeholders_created:
            info.append(
                f"Placeholders gerados para {len(fill.placeholders_created)} "
                f"imagem(ns) ausente(s) do template: {fill.placeholders_created}"
            )

        # 5) Verificar substituição completa (autoritativa) + compilar PDF -
        leftover = latex_filler.unsubstituted_tokens(workdir)
        if leftover:
            raise latex_compiler.CompilationError(
                f"Substituição incompleta — tokens remanescentes nos .tex: {leftover}"
            )
        _progress("Compilando LaTeX (pode demorar na 1ª execução)", 0.55)
        comp = latex_compiler.compile_and_verify(workdir, out_pdf, config)
        info.append(f"PDF: {comp.page_count} páginas, sem '<<>>' (verificado).")

        summary = {
            "xlsx": str(xlsx_path),
            "pdf": str(comp.pdf_path),
            "pages": comp.page_count,
            "keys_total": len(load.resolved),
            "keys_substituted": len(fill.substituted_keys),
            "conflicts": [c.key for c in load.conflicts],
            "missing_in_latex": fill.missing_in_planilha,
            "planilha_only": fill.planilha_only,
            "placeholders_created": fill.placeholders_created,
            "pie_slices": dict(zip(load.pie.labels, load.pie.values)),
            "bar_months": load.bar.months,
            "no_placeholder_violations": not comp.placeholder_violations,
        }
        logger.info("Pipeline concluído. PDF: %s", comp.pdf_path)
        _progress("Concluído", 1.0)
        return PipelineResult(
            pdf_path=comp.pdf_path,
            warnings=warnings, info=info, summary=summary,
        )
    finally:
        if not keep_workdir:
            shutil.rmtree(base_tmp, ignore_errors=True)
        else:
            logger.info("Workdir mantido para inspeção: %s", workdir)
