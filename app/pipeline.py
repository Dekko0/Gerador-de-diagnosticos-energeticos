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


def _write_uploaded_images(images: dict[str, bytes], figures_dir: Path) -> list[str]:
    """Grava as fotos enviadas (filename -> bytes PNG) em ``figures_dir``.

    Feito ANTES de ``ensure_referenced_images`` para que essas imagens sejam
    usadas no lugar dos placeholders. Retorna os nomes efetivamente gravados.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, data in images.items():
        if not data:
            continue
        (figures_dir / name).write_bytes(data)
        written.append(name)
    if written:
        logger.info("Imagens de inspeção aplicadas (%d): %s", len(written), written)
    return written


def run(
    xlsx_path: str | Path,
    out_pdf: str | Path | None = None,
    config: Config | None = None,
    keep_workdir: bool = False,
    images: dict[str, bytes] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    """Executa o pipeline completo.

    * ``out_pdf`` — caminho do PDF final. Default: ``output/<stem>.pdf``.
    * ``images`` — opcional. Mapa ``nome_arquivo -> bytes PNG`` de fotos de
      inspeção (ex.: ``"NR01ACFT.png"``) gravadas em ``Figuras/`` antes da
      geração de placeholders.
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
    info.append(
        f"Gráficos gerados: 1 (pizza), 2 (consumo), 3 (Ponta/Fora Ponta: "
        f"{len(load.stacked.months)} mês), 4 (demanda: {len(load.demand.months)} mês), "
        f"5 (despesa: {len(load.expense.months)} mês)."
    )

    # 2) Preparar cópia de trabalho do template ----------------------------
    _progress("Preparando template", 0.15)
    workdir = latex_filler.prepare_workdir(config)
    base_tmp = workdir.parent
    try:
        # 3) Gerar gráficos + aplicar fotos de inspeção enviadas ------------
        _progress("Gerando gráficos", 0.25)
        figures_dir = workdir / config.figures_subdir
        charts.generate_charts(load, figures_dir, config)
        if images:
            applied = _write_uploaded_images(images, figures_dir)
            if applied:
                info.append(f"{len(applied)} foto(s) de inspeção aplicada(s): {applied}")

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
            "stacked_months": load.stacked.months,
            "demand_months": load.demand.months,
            "expense_months": load.expense.months,
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
