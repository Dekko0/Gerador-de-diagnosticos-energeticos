"""Geração dos cinco gráficos (PNG, headless) a partir dos dados da planilha.

* Gráfico 1 — pizza pseudo-3D com **linhas de chamada rotuladas** (nome da
  categoria + percentual) em vez de legenda colorida ao lado.
* Gráfico 2 — barras do perfil de consumo mensal (consumo total).
* Gráfico 3 — barras empilhadas Ponta + Fora Ponta por mês.
* Gráfico 4 — demanda comparativa Ponta/Fora Ponta (barras agrupadas) com
  linhas de demanda contratada e tolerância(s).
* Gráfico 5 — barras da despesa mensal com energia elétrica.

Efeito 3D da pizza
------------------
O matplotlib não tem pizza 3D nativa. Desenhamos o disco em perspectiva:
achatamento vertical (``tilt``) vira uma elipse, cada fatia ganha uma "parede"
lateral (``depth``) mais escura, e a ordem de desenho faz a oclusão correta.

Tudo renderizado com o backend ``Agg`` (sem display), seguro em servidor.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless — precisa vir antes do pyplot

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .config import Config  # noqa: E402
from .excel_loader import (  # noqa: E402
    BarData,
    DemandData,
    ExpenseData,
    LoadResult,
    PieData,
    StackedBarData,
)

logger = logging.getLogger(__name__)

# Paleta agradável e com bom contraste para as fatias/barras.
_PALETTE = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728",
    "#9467BD", "#8C564B", "#E377C2", "#17BECF",
]
_BAR_COLOR = "#1F3864"
# Cores Ponta / Fora Ponta (gráficos 3 e 4), no estilo do modelo de demanda.
_PONTA_COLOR = "#FF7F0E"        # azul claro
_FORA_PONTA_COLOR = "#1F4E79"   # azul escuro
_EXPENSE_COLOR = "#2E7D32"      # verde (despesa)
# Linhas de referência do Gráfico 4.
_CONTRATADA_COLOR = "#7030A0"   # roxo (contratada)
_TOL_COLOR = "#C55A11"          # laranja (tolerância única)
_TOL_NP_COLOR = "#C55A11"       # laranja (tolerância Ponta)
_TOL_FP_COLOR = "#ED9B40"       # laranja claro (tolerância Fora Ponta)


def _darker(hex_color: str, factor: float = 0.62) -> tuple[float, float, float]:
    """Retorna uma versão mais escura de uma cor (para as paredes 3D)."""
    r, g, b = matplotlib.colors.to_rgb(hex_color)
    return (r * factor, g * factor, b * factor)


def _fmt_ptbr(value: float, config: Config) -> str:
    """Formata número p/ rótulo do gráfico no padrão pt-BR (sem casas se inteiro)."""
    if float(value).is_integer():
        s = f"{int(round(value)):,}"
        return s.replace(",", config.thousands_sep)
    s = f"{value:,.{config.number_decimals}f}"
    return s.replace(",", "\x00").replace(".", config.decimal_sep).replace("\x00", config.thousands_sep)


# --------------------------------------------------------------------------- #
# Gráfico 1 — Pizza pseudo-3D com linhas de chamada
# --------------------------------------------------------------------------- #
def save_pie_chart(pie: PieData, out_path: str | Path, config: Config) -> Path:
    """Desenha e salva a pizza pseudo-3D com rótulos por linha de chamada.

    Cada fatia recebe um rótulo externo (nome da categoria + percentual) ligado
    à fatia por uma linha-guia, dispensando a legenda colorida lateral. Lança
    ValueError se não houver dados positivos.
    """
    out_path = Path(out_path)
    values = list(pie.values)
    labels = list(pie.labels)
    if not values or sum(values) <= 0:
        raise ValueError("Gráfico 1: sem fatias com valor positivo para plotar.")

    total = float(sum(values))
    tilt = 0.58          # achatamento vertical (perspectiva)
    depth = 0.16         # espessura do disco
    radius = 1.0
    explode = 0.04       # leve separação das fatias
    start = 90.0         # começa no topo

    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(values))]

    # Ângulos acumulados (graus), sentido anti-horário a partir de `start`.
    angles = [start]
    for v in values:
        angles.append(angles[-1] + v / total * 360.0)

    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    ax.set_aspect("equal")
    ax.axis("off")

    def arc_points(a0: float, a1: float, cx: float, cy: float, n: int = 60):
        ts = np.deg2rad(np.linspace(a0, a1, max(2, int(n * (a1 - a0) / 360) + 2)))
        xs = cx + radius * np.cos(ts)
        ys = cy + tilt * radius * np.sin(ts)
        return xs, ys

    # Sombra suave no chão (profundidade extra).
    shadow = plt.matplotlib.patches.Ellipse(
        (0, -depth - 0.04), 2 * radius * 1.02, 2 * tilt * radius * 1.02,
        facecolor=(0, 0, 0, 0.12), edgecolor="none", zorder=0,
    )
    ax.add_patch(shadow)

    centers = []
    for a0, a1 in zip(angles[:-1], angles[1:]):
        mid = np.deg2rad((a0 + a1) / 2)
        cx, cy = explode * np.cos(mid), explode * tilt * np.sin(mid)
        centers.append((cx, cy))

    # Paredes laterais (mais escuras) — zorder baixo.
    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        cx, cy = centers[i]
        xs, ys = arc_points(a0, a1, cx, cy)
        wall_x = np.concatenate([xs, xs[::-1]])
        wall_y = np.concatenate([ys, (ys - depth)[::-1]])
        ax.fill(wall_x, wall_y, facecolor=_darker(colors[i]), edgecolor=_darker(colors[i]),
                linewidth=0.4, zorder=1)

    # Faces do topo — zorder alto (cobrem as paredes de trás).
    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        cx, cy = centers[i]
        xs, ys = arc_points(a0, a1, cx, cy)
        face_x = np.concatenate([[cx], xs, [cx]])
        face_y = np.concatenate([[cy], ys, [cy]])
        ax.fill(face_x, face_y, facecolor=colors[i], edgecolor="white",
                linewidth=1.2, zorder=2)

    # Linhas de chamada com nome da categoria + percentual (em vez de legenda).
    # Calcula os pontos de borda e separa por lado para evitar sobreposição
    # vertical dos rótulos (fatias pequenas e adjacentes colidiriam).
    edge = []  # (i, ex, ey, side)
    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        cx, cy = centers[i]
        ang = np.deg2rad((a0 + a1) / 2)
        cosang, sinang = np.cos(ang), np.sin(ang)
        ex = cx + radius * cosang
        ey = cy + tilt * radius * sinang
        side = 1.0 if cosang >= 0 else -1.0
        edge.append((i, ex, ey, side))

    min_gap = 0.34  # separação vertical mínima entre rótulos do mesmo lado
    label_y: dict[int, float] = {}
    for side in (1.0, -1.0):
        group = sorted([e for e in edge if e[3] == side], key=lambda e: e[2], reverse=True)
        placed: list[float] = []
        for _i, _ex, ey, _s in group:
            y = ey
            if placed and placed[-1] - y < min_gap:
                y = placed[-1] - min_gap
            placed.append(y)
        for (idx, _ex, _ey, _s), y in zip(group, placed):
            label_y[idx] = y

    for i, ex, ey, side in edge:
        pct = values[i] / total * 100.0
        pct_str = f"{pct:.1f}%".replace(".", config.decimal_sep)
        ly = label_y[i]
        mx = side * 1.22
        lx = side * 1.46
        ha = "left" if side > 0 else "right"
        ax.plot([ex, mx, lx], [ey, ly, ly], color="0.45", lw=0.9, zorder=3)
        ax.scatter([ex], [ey], s=8, color=colors[i], zorder=4)
        label_txt = f"{labels[i]}\n{_fmt_ptbr(values[i], config)} kWh · {pct_str}"
        ax.text(lx + side * 0.03, ly, label_txt, ha=ha, va="center",
                fontsize=9.5, fontweight="bold", color="#222", zorder=4)

    ax.set_xlim(-2.25, 2.25)
    ax.set_ylim(-1.0 - depth, 1.35)
    ax.set_title(config.graph1_title, fontsize=13, fontweight="bold", pad=14)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 1 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Gráfico 2 — Barras mensais (consumo total)
# --------------------------------------------------------------------------- #
def save_bar_chart(bar: BarData, out_path: str | Path, config: Config) -> Path:
    """Desenha e salva o perfil de consumo mensal (barras). ValueError se vazio."""
    out_path = Path(out_path)
    if not bar.months:
        raise ValueError("Gráfico 2: nenhum mês com histórico para plotar.")

    x = np.arange(len(bar.months))
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)

    if config.graph2_chart_type == "line":
        ax.plot(x, bar.values, marker="o", color=_BAR_COLOR, linewidth=2)
    else:
        bars = ax.bar(x, bar.values, color=_BAR_COLOR, edgecolor="white", width=0.7)
        for rect, v in zip(bars, bar.values):
            ax.annotate(_fmt_ptbr(v, config), (rect.get_x() + rect.get_width() / 2,
                        rect.get_height()), ha="center", va="bottom",
                        fontsize=9, xytext=(0, 2), textcoords="offset points")

    ax.set_xticks(x)
    ax.set_xticklabels(bar.months, rotation=45, ha="right")
    ax.set_xlabel(config.graph2_xlabel, fontsize=11)
    ax.set_ylabel(config.graph2_ylabel, fontsize=11)
    ax.set_title(config.graph2_title, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_ylim(0, max(bar.values) * 1.15 if max(bar.values) > 0 else 1)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 2 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Gráfico 3 — Barras empilhadas Ponta + Fora Ponta
# --------------------------------------------------------------------------- #
def save_stacked_bar_chart(data: StackedBarData, out_path: str | Path, config: Config) -> Path:
    """Barras empilhadas de consumo Ponta + Fora Ponta por mês. ValueError se vazio."""
    out_path = Path(out_path)
    if not data.months or (sum(data.ponta) + sum(data.fora_ponta)) <= 0:
        raise ValueError("Gráfico 3: sem dados de consumo Ponta/Fora Ponta para plotar.")

    x = np.arange(len(data.months))
    ponta = np.array(data.ponta, dtype=float)
    fora = np.array(data.fora_ponta, dtype=float)
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)

    ax.bar(x, ponta, width=0.7, color=_PONTA_COLOR, edgecolor="white",
           label=config.graph3_ponta_label)
    ax.bar(x, fora, width=0.7, bottom=ponta, color=_FORA_PONTA_COLOR,
           edgecolor="white", label=config.graph3_fora_ponta_label)

    # Total acima de cada pilha.
    totals = ponta + fora
    for xi, t in zip(x, totals):
        if t > 0:
            ax.annotate(_fmt_ptbr(float(t), config), (xi, t), ha="center", va="bottom",
                        fontsize=8.5, xytext=(0, 2), textcoords="offset points")

    ax.set_xticks(x)
    ax.set_xticklabels(data.months, rotation=45, ha="right")
    ax.set_xlabel(config.graph2_xlabel, fontsize=11)
    ax.set_ylabel(config.graph3_ylabel, fontsize=11)
    ax.set_title(config.graph3_title, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_ylim(0, float(totals.max()) * 1.15 if totals.max() > 0 else 1)
    ax.legend(frameon=False, fontsize=10, ncol=2, loc="upper right")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 3 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Gráfico 4 — Demanda comparativa + linhas de contrato/tolerância
# --------------------------------------------------------------------------- #
def save_demand_chart(data: DemandData, out_path: str | Path, config: Config) -> Path:
    """Barras agrupadas (Demanda Ponta/Fora Ponta) + linhas de referência.

    Linhas horizontais:
      * Demanda Contratada (sólida), se houver valor.
      * Tolerância: UMA tracejada se ``demandaContratadaTolerancia`` tem valor;
        caso contrário, DUAS tracejadas (Ponta e Fora Ponta) se ambas as chaves
        ``...ToleranciaNP``/``...ToleranciaFP`` tiverem valor.
    ValueError se não houver nenhum dado (barras e linhas todas vazias).
    """
    out_path = Path(out_path)
    ponta = np.array(data.ponta, dtype=float)
    fora = np.array(data.fora_ponta, dtype=float)
    has_bars = bool(data.months) and (ponta.sum() + fora.sum()) > 0
    ref_values = [v for v in (data.contratada, data.tolerancia,
                              data.tolerancia_np, data.tolerancia_fp) if v is not None]
    if not has_bars and not ref_values:
        raise ValueError("Gráfico 4: sem dados de demanda para plotar.")

    n = len(data.months) if data.months else 1
    x = np.arange(n)
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=150)

    bar_max = 0.0
    if has_bars:
        ax.bar(x - width / 2, ponta, width=width, color=_PONTA_COLOR,
               edgecolor="white", label=config.graph4_ponta_label, zorder=2)
        ax.bar(x + width / 2, fora, width=width, color=_FORA_PONTA_COLOR,
               edgecolor="white", label=config.graph4_fora_ponta_label, zorder=2)
        bar_max = float(max(ponta.max(), fora.max()))

    # Linhas horizontais de referência.
    line_vals: list[float] = []

    def _hline(value: float, color: str, style: str, label: str) -> None:
        ax.axhline(value, color=color, linestyle=style, linewidth=2.0,
                   label=label, zorder=3)
        line_vals.append(value)

    if data.contratada is not None:
        _hline(data.contratada, _CONTRATADA_COLOR, "-", "Demanda Contratada")

    if data.tolerancia is not None:
        _hline(data.tolerancia, _TOL_COLOR, "--", "Demanda Contratada c/ Tolerância")
    elif data.tolerancia_np is not None and data.tolerancia_fp is not None:
        _hline(data.tolerancia_np, _TOL_NP_COLOR, "--",
               "Demanda Contratada c/ Tolerância Ponta")
        _hline(data.tolerancia_fp, _TOL_FP_COLOR, "--",
               "Demanda Contratada c/ Tolerância Fora da Ponta")

    if has_bars:
        ax.set_xticks(x)
        ax.set_xticklabels(data.months, rotation=45, ha="right")
    else:
        ax.set_xticks([])
    ax.set_xlabel(config.graph2_xlabel, fontsize=11)
    ax.set_ylabel(config.graph4_ylabel, fontsize=11)
    ax.set_title(config.graph4_title, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    top = max([bar_max] + line_vals) if (bar_max or line_vals) else 1.0
    ax.set_ylim(0, top * 1.18 if top > 0 else 1)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.18))

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 4 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Gráfico 5 — Barras de despesa mensal
# --------------------------------------------------------------------------- #
def save_expense_bar_chart(data: ExpenseData, out_path: str | Path, config: Config) -> Path:
    """Barras da despesa mensal com energia elétrica. ValueError se vazio."""
    out_path = Path(out_path)
    if not data.months or sum(data.values) <= 0:
        raise ValueError("Gráfico 5: sem dados de despesa mensal para plotar.")

    x = np.arange(len(data.months))
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    bars = ax.bar(x, data.values, color=_EXPENSE_COLOR, edgecolor="white", width=0.7)
    for rect, v in zip(bars, data.values):
        ax.annotate(f"R$ {_fmt_ptbr(v, config)}",
                    (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    ha="center", va="bottom", fontsize=8.5, xytext=(0, 2),
                    textcoords="offset points")

    ax.set_xticks(x)
    ax.set_xticklabels(data.months, rotation=45, ha="right")
    ax.set_xlabel(config.graph2_xlabel, fontsize=11)
    ax.set_ylabel(config.graph5_ylabel, fontsize=11)
    ax.set_title(config.graph5_title, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_ylim(0, max(data.values) * 1.15 if max(data.values) > 0 else 1)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 5 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Placeholder para dados ausentes
# --------------------------------------------------------------------------- #
def save_placeholder_chart(title: str, message: str, out_path: str | Path) -> Path:
    """Gera uma imagem 'sem dados' (mantém o relatório íntegro p/ unidades sem dados)."""
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12,
            color="#666666", style="italic", transform=ax.transAxes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Placeholder salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def generate_charts(
    result: LoadResult, figures_dir: str | Path, config: Config
) -> dict[str, Path]:
    """Gera os cinco gráficos na pasta de figuras do template. Retorna os caminhos.

    Se uma série não tiver dados plotáveis (ex.: unidade sem histórico, ou o
    modelo em branco), gera um placeholder em vez de falhar — assim o relatório
    é sempre produzido e a verificação de imagens embutidas continua válida.
    """
    figures_dir = Path(figures_dir)
    g1 = figures_dir / config.graph1_output_name
    g2 = figures_dir / config.graph2_output_name
    g3 = figures_dir / config.graph3_output_name
    g4 = figures_dir / config.graph4_output_name
    g5 = figures_dir / config.graph5_output_name

    def _try(fn, out: Path, title: str, empty_msg: str) -> None:
        try:
            fn()
        except ValueError as exc:
            logger.warning("%s sem dados (%s); gerando placeholder.", title, exc)
            save_placeholder_chart(title, empty_msg, out)

    _try(lambda: save_pie_chart(result.pie, g1, config), g1, config.graph1_title,
         "Sem dados de consumo por uso final disponíveis")
    _try(lambda: save_bar_chart(result.bar, g2, config), g2, config.graph2_title,
         "Sem histórico de consumo mensal disponível")
    _try(lambda: save_stacked_bar_chart(result.stacked, g3, config), g3, config.graph3_title,
         "Sem dados de consumo Ponta/Fora Ponta disponíveis")
    _try(lambda: save_demand_chart(result.demand, g4, config), g4, config.graph4_title,
         "Sem dados de demanda disponíveis")
    _try(lambda: save_expense_bar_chart(result.expense, g5, config), g5, config.graph5_title,
         "Sem dados de despesa mensal disponíveis")

    return {"grafico1": g1, "grafico2": g2, "grafico3": g3, "grafico4": g4, "grafico5": g5}
