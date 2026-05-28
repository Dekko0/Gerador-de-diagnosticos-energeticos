"""Componentes reutilizáveis da UI Streamlit.

Cada função renderiza um pedaço da página. Toda saída usa ``unsafe_allow_html``
com strings escapadas via ``html.escape`` quando vêm de dados do usuário /
logs / nomes de arquivo (defesa em profundidade).

Não chama ``st.set_page_config`` ou injeta CSS — isso é responsabilidade de
:mod:`app.ui.styles`, executado uma única vez no topo de ``main()``.
"""

from __future__ import annotations

import html
import io
from pathlib import Path
from typing import Iterable

import streamlit as st

from app import __version__
from app.pipeline import PipelineResult


# --------------------------------------------------------------------------- #
# Helpers de ícone
# --------------------------------------------------------------------------- #
def icon(name: str, *, color: str | None = None, size_em: float | None = None) -> str:
    """Devolve o HTML inline de um ícone Material — uso seguro com ``unsafe_allow_html``."""
    classes = ["material-icons"]
    if color:
        classes.append(f"icon-{color}")
    cls = " ".join(classes)
    style = f' style="font-size:{size_em}em"' if size_em else ""
    return f'<span class="{cls}"{style}>{html.escape(name)}</span>'


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def render_header() -> None:
    st.markdown(
        f"""
        <div class="app-header">
            {icon("assessment", color="primary", size_em=2.4)}
            <h1>Gerador de Relatórios — Diagnóstico de Eficiência</h1>
        </div>
        <p class="app-subtitle">
            Excel → LaTeX → PDF (oficial) + Word (cópia opcional) · v{html.escape(__version__)}
        </p>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> dict:
    """Renderiza a sidebar e devolve um ``dict`` com as opções escolhidas."""
    cfg: dict = {}
    with st.sidebar:
        st.markdown(
            f'{icon("settings", color="primary")} **Opções**',
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown("**Substituição de chaves**")
        cfg["conflict_policy"] = st.selectbox(
            "Política de conflito de chaves duplicadas",
            ["last-wins", "first-wins"],
            index=0,
            format_func=lambda v: {
                "last-wins": "Usar o último valor encontrado",
                "first-wins": "Usar o primeiro valor encontrado",
            }[v],
            help="O que fazer quando a mesma <<chave>> aparece em múltiplas linhas com valores diferentes.",
        )
        cfg["missing_placeholder"] = st.text_input(
            "Texto exibido quando o campo não tem valor",
            value="—",
            help="Usado quando uma chave do LaTeX não tem valor na planilha.",
        )

        st.divider()
        st.markdown("**Gráficos**")
        cfg["chart2_type"] = st.selectbox("Tipo do Gráfico 2 (mensal)", ["bar", "line"], index=0)
        cfg["skip_zero_months"] = st.checkbox(
            "Descartar meses com consumo zero (Gráfico 2)", value=False
        )
        cfg["omit_zero_pie"] = st.checkbox(
            "Omitir fatias com valor zero (Gráfico 1)", value=True
        )

        st.divider()
        st.markdown(
            f'{icon("file_present", color="info")} **Entrega**',
            unsafe_allow_html=True,
        )
        cfg["include_docx"] = st.checkbox(
            "Incluir Word na entrega (conversão aproximada)",
            value=True,
            help="Requer LibreOffice instalado. Se ausente, é pulado com aviso.",
        )
        cfg["verbose_logs"] = st.checkbox("Exibir registros detalhados")
    return cfg


# --------------------------------------------------------------------------- #
# Upload — chamada ÚNICA do file_uploader
# --------------------------------------------------------------------------- #
def render_upload_section():
    """Renderiza a seção de upload. Retorna o ``UploadedFile`` ou ``None``.

    ⚠️ Este é o **único lugar** onde ``st.file_uploader`` é chamado em todo
    o app. ``key="xlsx_uploader"`` persiste o arquivo em ``st.session_state``
    entre reruns; ``label_visibility="collapsed"`` evita label duplicado.
    """
    st.markdown(
        f'### {icon("cloud_upload", color="primary")}Enviar planilha',
        unsafe_allow_html=True,
    )
    st.caption(
        "Arraste o arquivo `.xlsx` ou clique para selecionar "
        "(ex.: RAD CMEI Olga Benário.xlsx)"
    )
    return st.file_uploader(
        label="Selecione o arquivo Excel",
        type=["xlsx"],
        label_visibility="collapsed",
        key="xlsx_uploader",
    )


# --------------------------------------------------------------------------- #
# Botão de ação
# --------------------------------------------------------------------------- #
def render_generate_button() -> bool:
    """Botão principal (gradiente, full-width). Retorna ``True`` quando clicado."""
    return st.button(
        "▶  Gerar Relatório",
        type="primary",
        use_container_width=True,
        key="generate_button",
    )


# --------------------------------------------------------------------------- #
# Progresso por etapas (4 steps inline)
# --------------------------------------------------------------------------- #
#: Etapas do pipeline, na ordem em que aparecem para o usuário.
STEP_LABELS: tuple[str, ...] = (
    "Lendo planilha",
    "Gerando gráficos",
    "Compilando LaTeX",
    "Convertendo Word",
)

_STEP_ICONS = {
    "done":    "check_circle",
    "active":  "sync",
    "pending": "radio_button_unchecked",
}


def render_progress(steps: list[tuple[str, str]]) -> None:
    """Exibe barra + lista de steps inline.

    ``steps``: lista ordenada de ``(status, label)`` onde
    ``status ∈ {"done", "active", "pending"}``.
    """
    total = len(steps) or 1
    done_count = sum(1 for s, _ in steps if s == "done")
    st.progress(done_count / total)

    cols = st.columns(total)
    for col, (status, label) in zip(cols, steps):
        with col:
            ic = _STEP_ICONS.get(status, "radio_button_unchecked")
            st.markdown(
                f'<div class="step-item step-{status}">'
                f'<span class="material-icons">{html.escape(ic)}</span>'
                f"{html.escape(label)}</div>",
                unsafe_allow_html=True,
            )


def fraction_to_step_index(fraction: float, *, include_docx: bool) -> int:
    """Mapeia uma fração [0,1] do pipeline ao índice do step ativo (0..3).

    Os limiares casam com as fracões emitidas por ``pipeline.run`` (0.05 →
    leitura, 0.25 → gráficos, 0.40/0.55 → compilação, 0.90 → DOCX, 1.0 → done).
    """
    if fraction >= 1.0:
        return 4   # tudo concluído
    if fraction >= 0.85 and include_docx:
        return 3
    if fraction >= 0.40:
        return 2
    if fraction >= 0.20:
        return 1
    return 0


def steps_for(active_idx: int, *, include_docx: bool) -> list[tuple[str, str]]:
    """Constrói a lista de steps a partir do índice ativo."""
    labels = list(STEP_LABELS)
    if not include_docx:
        labels = labels[:3]
    result: list[tuple[str, str]] = []
    for i, label in enumerate(labels):
        if i < active_idx:
            result.append(("done", label))
        elif i == active_idx:
            result.append(("active", label))
        else:
            result.append(("pending", label))
    return result


# --------------------------------------------------------------------------- #
# Avisos e logs
# --------------------------------------------------------------------------- #
def render_warnings(
    warnings: Iterable[str],
    infos: Iterable[str],
    *,
    verbose_logs: bool = False,
    log_records: list[str] | None = None,
    summary: dict | None = None,
) -> None:
    """Seção colapsável de avisos, infos, resumo técnico e (opcionalmente) logs."""
    warnings = list(warnings)
    infos = list(infos)
    total = len(warnings) + len(infos)
    if total or summary or (verbose_logs and log_records):
        head_icon = "warning" if warnings else "info"
        with st.expander(f"{'⚠️' if warnings else 'ℹ️'}  Avisos e Registros ({total} itens)"):
            for w in warnings:
                st.markdown(
                    f'<div>{icon("warning", color="warning")}{html.escape(str(w))}</div>',
                    unsafe_allow_html=True,
                )
            for i in infos:
                st.markdown(
                    f'<div>{icon("info", color="info")}{html.escape(str(i))}</div>',
                    unsafe_allow_html=True,
                )
            if summary:
                st.markdown("---")
                st.markdown("**Resumo técnico**")
                st.json(summary)
            if verbose_logs and log_records:
                st.markdown("---")
                st.markdown("**Registros completos**")
                st.code("\n".join(log_records), language="text")


# --------------------------------------------------------------------------- #
# Cards de download
# --------------------------------------------------------------------------- #
def render_download_cards(result: PipelineResult, filename_base: str) -> None:
    """Dois cards lado a lado: PDF (oficial, verde) e DOCX (opcional, azul)."""
    st.markdown(
        f'### {icon("download_done", color="success")}Relatório gerado com sucesso!',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    pdf_path: Path = result.pdf_path
    pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)

    with col1:
        st.markdown(
            '<div class="download-card official">'
            f'{icon("check_circle", color="success")}'
            ' <strong>PDF — Formato Oficial</strong><br>'
            '<small style="color:#888">100% fiel ao template LaTeX · '
            f"{html.escape(pdf_path.name)} · {pdf_size_mb:.2f} MB</small>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            label="📥  Baixar PDF",
            data=io.BytesIO(pdf_path.read_bytes()),
            file_name=f"{filename_base}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf",
        )

    with col2:
        if result.docx_path is not None:
            docx_size_mb = result.docx_path.stat().st_size / (1024 * 1024)
            st.markdown(
                '<div class="download-card optional">'
                f'{icon("info", color="info")}'
                ' <strong>Word — Cópia Adaptada</strong><br>'
                '<small style="color:#888">Conversão aproximada via LibreOffice · '
                "fidelidade parcial · "
                f"{html.escape(result.docx_path.name)} · {docx_size_mb:.2f} MB</small>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.download_button(
                label="📥  Baixar Word",
                data=io.BytesIO(result.docx_path.read_bytes()),
                file_name=f"{filename_base}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="download_docx",
            )
        elif result.docx_skipped_reason:
            st.info(f"Word não gerado: {result.docx_skipped_reason}")
        else:
            st.info("Word não solicitado (ative na barra lateral para incluir).")
