"""Entry-point Streamlit. Rode com ``streamlit run app/ui/app.py``.

Fluxo:
    1. ``setup_page``            — set_page_config + CSS + CDN (uma única vez).
    2. ``render_sidebar``         — opções (políticas, gráficos, entrega).
    3. ``render_header``          — título + subtítulo.
    4. ``render_upload_section``  — ÚNICO ``st.file_uploader`` do app.
    5. Se há arquivo → ``render_generate_button`` → executa pipeline com
       feedback de progresso por etapas.
    6. ``render_warnings`` + ``render_download_cards``.

⚠️ Regras anti-bug seguidas:
  * ``st.file_uploader`` chamado **uma única vez**.
  * Todo o conteúdo pós-upload está dentro de ``if uploaded_file is not None``.
  * CSS/CDN carregado **uma única vez** em ``setup_page`` (1ª chamada Streamlit).
  * ``st.rerun()`` **não** é usado.
"""

from __future__ import annotations

import html
import logging
import sys
import tempfile
from pathlib import Path

# `streamlit run app/ui/app.py` coloca `app/ui/` em sys.path mas não a raiz
# do projeto; garantimos que `from app import ...` funcione.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.config import Config  # noqa: E402
from app.latex_compiler import CompilationError  # noqa: E402
from app.pipeline import run  # noqa: E402
from app.ui import components  # noqa: E402
from app.ui.styles import setup_page  # noqa: E402

logger = logging.getLogger(__name__)


class _ListHandler(logging.Handler):
    """Captura registros em memória para a seção 'Logs detalhados'."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(f"{record.levelname:7} {record.name}: {record.getMessage()}")


def _build_config(cfg_dict: dict) -> Config:
    """Converte o ``dict`` da sidebar num :class:`Config` para o pipeline."""
    return Config(
        conflict_policy=cfg_dict["conflict_policy"],
        missing_placeholder=cfg_dict["missing_placeholder"],
        graph2_chart_type=cfg_dict["chart2_type"],
        graph2_drop_zero_values=cfg_dict["skip_zero_months"],
        graph1_drop_zero_slices=cfg_dict["omit_zero_pie"],
    )


def _run_pipeline_with_progress(
    xlsx_path: Path,
    out_pdf: Path,
    out_docx: Path | None,
    cfg: Config,
    include_docx: bool,
    handler: _ListHandler,
):
    """Executa o pipeline mostrando barra + 4 steps inline; coleta logs."""
    placeholder = st.empty()

    def _render(active_idx: int) -> None:
        steps = components.steps_for(active_idx, include_docx=include_docx)
        with placeholder.container():
            components.render_progress(steps)

    _render(0)  # estado inicial: "Lendo planilha" ativo

    def _on_progress(_label: str, fraction: float) -> None:
        idx = components.fraction_to_step_index(fraction, include_docx=include_docx)
        _render(idx)

    root = logging.getLogger()
    root.addHandler(handler)
    prev_level = root.level
    root.setLevel(logging.INFO)
    try:
        result = run(
            xlsx_path,
            out_pdf=out_pdf,
            out_docx=out_docx,
            config=cfg,
            skip_docx=not include_docx,
            progress_callback=_on_progress,
        )
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)
        placeholder.empty()
    return result


def main() -> None:
    # 1. Setup — set_page_config + CSS + CDN (PRIMEIRA chamada Streamlit)
    setup_page()

    # 2. Sidebar
    cfg_dict = components.render_sidebar()

    # 3. Header
    components.render_header()

    # 4. Upload — ÚNICA chamada de st.file_uploader em todo o app
    uploaded_file = components.render_upload_section()

    if uploaded_file is None:
        st.info("Faça o envio de uma planilha `.xlsx` para continuar.")
        st.stop()

    # — A partir daqui, todo conteúdo é condicional ao upload —
    st.success(
        f"✅ Arquivo carregado: **{html.escape(uploaded_file.name)}** "
        f"({uploaded_file.size / 1024:.1f} KB)"
    )
    st.divider()

    if not components.render_generate_button():
        st.stop()

    # 5. Pipeline com feedback por etapas
    handler = _ListHandler()
    handler.setLevel(logging.INFO)

    tmpdir = Path(tempfile.mkdtemp(prefix="diag_ui_"))
    xlsx_path = tmpdir / uploaded_file.name
    xlsx_path.write_bytes(uploaded_file.getbuffer())
    stem = Path(uploaded_file.name).stem
    cfg = _build_config(cfg_dict)
    include_docx = bool(cfg_dict["include_docx"])

    try:
        result = _run_pipeline_with_progress(
            xlsx_path=xlsx_path,
            out_pdf=tmpdir / f"{stem}.pdf",
            out_docx=tmpdir / f"{stem}.docx" if include_docx else None,
            cfg=cfg,
            include_docx=include_docx,
            handler=handler,
        )
    except CompilationError as exc:
        st.error(f"⚠️ Falha na compilação/verificação: {exc}")
        if cfg_dict["verbose_logs"] and handler.records:
            with st.expander("🪵 Registros completos (erro)", expanded=True):
                st.code("\n".join(handler.records), language="text")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro inesperado")
        st.error(f"⚠️ Erro ao gerar o relatório: {exc}")
        if cfg_dict["verbose_logs"] and handler.records:
            with st.expander("🪵 Registros completos (erro)", expanded=True):
                st.code("\n".join(handler.records), language="text")
        st.stop()

    # 6. Resultado: downloads + avisos
    components.render_download_cards(result, filename_base=stem)
    components.render_warnings(
        warnings=result.warnings,
        infos=result.info,
        verbose_logs=bool(cfg_dict["verbose_logs"]),
        log_records=handler.records,
        summary=result.summary,
    )


if __name__ == "__main__":
    main()
