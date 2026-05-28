"""Geração dos dois gráficos (PNG, headless) a partir dos dados da planilha.

* Gráfico 1 — pizza com aparência 3D ("Distribuição do consumo por uso final").
* Gráfico 2 — barras do perfil de consumo mensal.

Abordagem do efeito 3D da pizza
-------------------------------
O matplotlib não tem pizza 3D nativa. Em vez de um simples ``shadow=True``,
desenhamos a pizza **manualmente** como um disco visto em perspectiva:

1. O círculo é achatado verticalmente (``tilt``) → vira uma elipse (disco
   visto de cima em ângulo);
2. cada fatia ganha uma "parede" lateral (``depth``) num tom mais escuro;
3. a ordem de desenho (paredes atrás, faces no topo) faz a oclusão correta —
   só as paredes da frente ficam visíveis, exatamente como numa pizza 3D real.

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
from .excel_loader import BarData, LoadResult, PieData  # noqa: E402

logger = logging.getLogger(__name__)

# Paleta agradável e com bom contraste para as fatias/barras.
_PALETTE = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728",
    "#9467BD", "#8C564B", "#E377C2", "#17BECF",
]
_BAR_COLOR = "#1F3864"


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
# Gráfico 1 — Pizza pseudo-3D
# --------------------------------------------------------------------------- #
def save_pie_chart(pie: PieData, out_path: str | Path, config: Config) -> Path:
    """Desenha e salva a pizza pseudo-3D. Lança ValueError se não houver dados."""
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

    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
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

    # 1ª passada: paredes laterais (mais escuras) — zorder baixo.
    # 2ª passada: faces do topo — zorder alto (cobrem as paredes de trás).
    centers = []
    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        mid = np.deg2rad((a0 + a1) / 2)
        cx, cy = explode * np.cos(mid), explode * tilt * np.sin(mid)
        centers.append((cx, cy))

    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        cx, cy = centers[i]
        xs, ys = arc_points(a0, a1, cx, cy)
        # Parede: do contorno superior até o mesmo deslocado para baixo (depth).
        wall_x = np.concatenate([xs, xs[::-1]])
        wall_y = np.concatenate([ys, (ys - depth)[::-1]])
        ax.fill(wall_x, wall_y, facecolor=_darker(colors[i]), edgecolor=_darker(colors[i]),
                linewidth=0.4, zorder=1)

    for i, (a0, a1) in enumerate(zip(angles[:-1], angles[1:])):
        cx, cy = centers[i]
        xs, ys = arc_points(a0, a1, cx, cy)
        face_x = np.concatenate([[cx], xs, [cx]])
        face_y = np.concatenate([[cy], ys, [cy]])
        ax.fill(face_x, face_y, facecolor=colors[i], edgecolor="white",
                linewidth=1.2, zorder=2)

        # Rótulo de percentual. Fatias grandes: dentro (branco). Fatias
        # pequenas (<8%): fora, com linha-guia, para não se sobreporem.
        pct = values[i] / total * 100.0
        pct_str = f"{pct:.1f}%".replace(".", config.decimal_sep)
        ang = np.deg2rad((a0 + a1) / 2)
        if pct >= 8.0:
            lr = 0.62
            ax.text(cx + lr * radius * np.cos(ang), cy + lr * tilt * radius * np.sin(ang),
                    pct_str, ha="center", va="center", fontsize=10,
                    fontweight="bold", color="white", zorder=3)
        else:
            rx = cx + radius * np.cos(ang)
            ry = cy + tilt * radius * np.sin(ang)
            ox = cx + 1.28 * radius * np.cos(ang)
            oy = cy + 1.28 * tilt * radius * np.sin(ang) + 0.05
            ha = "left" if np.cos(ang) >= 0 else "right"
            ax.plot([rx, ox], [ry, oy], color="0.45", lw=0.8, zorder=3)
            ax.text(ox + (0.02 if ha == "left" else -0.02), oy, pct_str, ha=ha,
                    va="center", fontsize=9, fontweight="bold", color="black", zorder=4)

    ax.set_xlim(-1.6, 1.7)
    ax.set_ylim(-1.0 - depth, 1.28)
    ax.set_title(config.graph1_title, fontsize=13, fontweight="bold", pad=12)

    # Legenda (categoria + valor).
    legend_labels = [f"{lab} ({_fmt_ptbr(v, config)})" for lab, v in zip(labels, values)]
    handles = [plt.matplotlib.patches.Patch(facecolor=colors[i], edgecolor="white")
               for i in range(len(values))]
    ax.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
              frameon=False, fontsize=10)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 1 salvo em %s", out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Gráfico 2 — Barras mensais
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
    # Folga no topo para os rótulos.
    ax.set_ylim(0, max(bar.values) * 1.15 if max(bar.values) > 0 else 1)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Gráfico 2 salvo em %s", out_path)
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
    """Gera os dois gráficos na pasta de figuras do template. Retorna os caminhos.

    Se uma série não tiver dados plotáveis (ex.: unidade sem histórico, ou o
    modelo em branco), gera um placeholder em vez de falhar — assim o relatório
    é sempre produzido e a verificação de imagens embutidas continua válida.
    """
    figures_dir = Path(figures_dir)
    g1 = figures_dir / config.graph1_output_name
    g2 = figures_dir / config.graph2_output_name
    try:
        save_pie_chart(result.pie, g1, config)
    except ValueError as exc:
        logger.warning("Gráfico 1 sem dados (%s); gerando placeholder.", exc)
        save_placeholder_chart(config.graph1_title,
                               "Sem dados de consumo por uso final disponíveis", g1)
    try:
        save_bar_chart(result.bar, g2, config)
    except ValueError as exc:
        logger.warning("Gráfico 2 sem dados (%s); gerando placeholder.", exc)
        save_placeholder_chart(config.graph2_title,
                               "Sem histórico de consumo mensal disponível", g2)
    return {"grafico1": g1, "grafico2": g2}
