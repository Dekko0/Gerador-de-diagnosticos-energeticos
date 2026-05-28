"""Preenchimento do template LaTeX.

Etapas:

1. :func:`prepare_workdir` — copia o template para um diretório temporário
   (o original em ``templates/latex`` nunca é modificado).
2. :func:`substitute` — substitui ``<<chave>>`` por valores formatados em
   **todos** os ``.tex`` da cópia, numa única passada com casamento exato de
   token (imune a colisões de prefixo, ex.: ``<<consumoTotal>>`` vs
   ``<<consumoTotalUm>>``).
3. :func:`normalize_unicode_for_latex` — converte ``—`` / ``–`` / ``…`` nas
   ligaduras LaTeX correspondentes (xelatex + T1 fontenc + lmodern não tem
   glifo direto para esses pontos de código).
4. :func:`ensure_referenced_images` — gera PNG de placeholder para qualquer
   ``\\includegraphics`` cuja imagem não exista (ex.: fotos de inspeção que
   serão tiradas em campo); sem isso o Tectonic falha o link de recurso.
5. :func:`validate_braces` — opcional, detecta chaves ``{`` desbalanceadas e
   emite aviso acionável (xelatex tolera; pandoc/Tectonic-strict não).
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless para gerar placeholders
import matplotlib.pyplot as plt  # noqa: E402

from . import formatters  # noqa: E402
from .config import Config  # noqa: E402

logger = logging.getLogger(__name__)

# Token de chave: '<<' ... '>>' sem '<' ou '>' no meio (casa o token inteiro).
_KEY_TOKEN = re.compile(r"<<[^<>]+>>")
# Caminho de imagem em \includegraphics[...]{path}
_INCLUDEGRAPHICS = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
# Para contagem de chaves: descarta % comentários e \{ \} escapados.
_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
_ESC_BRACE = re.compile(r"\\[{}]")


@dataclass
class FillReport:
    workdir: Path
    tex_keys: set[str] = field(default_factory=set)
    substituted_keys: set[str] = field(default_factory=set)
    missing_in_planilha: list[str] = field(default_factory=list)
    planilha_only: list[str] = field(default_factory=list)
    per_file_counts: dict[str, int] = field(default_factory=dict)
    brace_warnings: list[str] = field(default_factory=list)
    placeholders_created: list[str] = field(default_factory=list)


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def iter_tex_files(workdir: Path) -> list[Path]:
    return sorted(workdir.rglob("*.tex"))


def scan_tex_keys(workdir: Path) -> set[str]:
    keys: set[str] = set()
    for tex in iter_tex_files(workdir):
        keys.update(_KEY_TOKEN.findall(_read_text(tex)))
    return keys


def count_braces(text: str) -> tuple[int, int]:
    """Conta ``{`` e ``}`` ignorando comentários e chaves escapadas (``\\{``)."""
    t = _COMMENT.sub("", text)
    t = _ESC_BRACE.sub("", t)
    return t.count("{"), t.count("}")


# --------------------------------------------------------------------------- #
# 1) Preparar workdir
# --------------------------------------------------------------------------- #
def prepare_workdir(config: Config, base_dir: str | Path | None = None) -> Path:
    """Copia o template para um diretório de trabalho temporário e o retorna."""
    if not Path(config.template_dir).exists():
        raise FileNotFoundError(
            f"Template não encontrado em {config.template_dir}. "
            "Descompacte o template em templates/latex/."
        )
    base = Path(base_dir) if base_dir else Path(tempfile.mkdtemp(prefix="diag_"))
    workdir = base / "latex"
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(config.template_dir, workdir)
    logger.info("Template copiado para workdir: %s", workdir)
    return workdir


# --------------------------------------------------------------------------- #
# 2) Substituição
# --------------------------------------------------------------------------- #
def build_repl_map(resolved: dict[str, object], config: Config) -> dict[str, str]:
    """Mapa chave -> valor já formatado/escapado pronto para o LaTeX."""
    return {k: formatters.format_value(v, config) for k, v in resolved.items()}


def substitute(workdir: Path, resolved: dict[str, object], config: Config) -> FillReport:
    """Substitui as chaves em todos os ``.tex`` da cópia de trabalho."""
    repl = build_repl_map(resolved, config)
    report = FillReport(workdir=workdir)
    report.tex_keys = scan_tex_keys(workdir)
    missing: set[str] = set()
    used: set[str] = set()

    def _replace(match: re.Match) -> str:
        token = match.group()
        if token in repl:
            used.add(token)
            return repl[token]
        missing.add(token)
        return config.missing_placeholder

    for tex in iter_tex_files(workdir):
        text = _read_text(tex)
        new_text, n = _KEY_TOKEN.subn(_replace, text)
        if n:
            tex.write_text(new_text, encoding="utf-8")
            report.per_file_counts[tex.name] = n

    report.substituted_keys = used
    report.missing_in_planilha = sorted(missing)
    report.planilha_only = sorted(set(resolved) - report.tex_keys)

    if report.missing_in_planilha:
        logger.warning(
            "%d chave(s) no LaTeX sem valor na planilha (-> '%s'): %s",
            len(report.missing_in_planilha), config.missing_placeholder,
            report.missing_in_planilha,
        )
    if report.planilha_only:
        logger.info(
            "%d chave(s) só na planilha (sem alvo no LaTeX, ignoradas): %s",
            len(report.planilha_only), report.planilha_only,
        )
    logger.info(
        "Substituição concluída: %d chaves usadas em %d arquivo(s).",
        len(used), len(report.per_file_counts),
    )
    return report


# --------------------------------------------------------------------------- #
# 3) Normalização Unicode -> ligaduras LaTeX
# --------------------------------------------------------------------------- #
def normalize_unicode_for_latex(workdir: Path, config: Config) -> int:
    """Substitui em todos os ``.tex`` caracteres Unicode "exóticos" pelas
    ligaduras LaTeX (``—`` -> ``---``, ``–`` -> ``--``, ``…`` -> ``\\ldots{}``).

    Devolve o número total de substituições. Necessário porque o template usa
    ``\\usepackage[T1]{fontenc}`` + lmodern: o glifo correto vem da ligadura,
    não do code point Unicode bruto sob xelatex.
    """
    if not config.unicode_replacements:
        return 0
    table = str.maketrans(config.unicode_replacements)
    total = 0
    for tex in iter_tex_files(workdir):
        txt = _read_text(tex)
        new = txt.translate(table)
        if new != txt:
            tex.write_text(new, encoding="utf-8")
            total += sum(txt.count(k) for k in config.unicode_replacements)
    if total:
        logger.info("Normalização Unicode: %d substituição(ões) aplicadas.", total)
    return total


# --------------------------------------------------------------------------- #
# 4) Placeholders para imagens referenciadas mas ausentes
# --------------------------------------------------------------------------- #
def _make_placeholder_png(path: Path, label: str, config: Config) -> None:
    fig, ax = plt.subplots(figsize=(6, 4), dpi=130)
    ax.axis("off")
    ax.set_facecolor("#f4f4f4")
    ax.text(0.5, 0.5, f"{config.missing_image_label}:\n{label}",
            ha="center", va="center", fontsize=14, color="#666",
            style="italic", transform=ax.transAxes)
    ax.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                                fill=False, edgecolor="#999", linewidth=1, linestyle="--"))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def ensure_referenced_images(workdir: Path, config: Config) -> list[str]:
    """Para cada ``\\includegraphics{X}`` cujo arquivo não exista, cria um PNG
    de placeholder em ``X.png`` (ou no caminho exato se já tiver extensão).

    Retorna a lista de placeholders criados (caminhos relativos ao workdir).
    Sem isso, o Tectonic falha o link de recurso e não gera o PDF.
    """
    referenced: set[str] = set()
    for tex in iter_tex_files(workdir):
        for m in _INCLUDEGRAPHICS.finditer(_read_text(tex)):
            referenced.add(m.group(1).strip())

    created: list[str] = []
    for ref in referenced:
        candidates = [ref] if Path(ref).suffix else [f"{ref}.png", f"{ref}.jpg", f"{ref}.pdf"]
        if any((workdir / c).exists() for c in candidates):
            continue
        target = workdir / (ref if ref.endswith(".png") else f"{ref}.png")
        _make_placeholder_png(target, target.name, config)
        created.append(str(target.relative_to(workdir)))
    if created:
        logger.info("Placeholders gerados para %d imagem(ns) ausente(s): %s",
                    len(created), created)
    return created


# --------------------------------------------------------------------------- #
# 5) Validação opcional de chaves
# --------------------------------------------------------------------------- #
def unsubstituted_tokens(workdir: Path) -> list[str]:
    """Lista tokens ``<<...>>`` remanescentes em qualquer ``.tex`` do workdir.

    Esta é a verificação **autoritativa** da DoD: se a lista é vazia, nenhum
    placeholder sobreviveu à substituição. (A checagem equivalente no PDF
    falsa para xelatex+lmodern, que renderiza ``<<`` ``>>`` como guillemets
    ``«`` ``»``; por isso validamos na fonte.)
    """
    leftover: set[str] = set()
    for tex in iter_tex_files(workdir):
        leftover.update(_KEY_TOKEN.findall(_read_text(tex)))
    return sorted(leftover)


def validate_braces(workdir: Path) -> list[str]:
    """Detecta desbalanceamento de ``{`` / ``}`` por capítulo. Útil para
    flagrar typos do template antes de a compilação falhar de forma críptica.
    """
    warnings: list[str] = []
    for tex in iter_tex_files(workdir):
        if "capitulo" not in tex.name and tex.name != "DIAG_PMS.tex":
            continue  # ignora arquivos auxiliares
        opens, closes = count_braces(_read_text(tex))
        if opens != closes:
            msg = (
                f"{tex.name}: chaves LaTeX desbalanceadas "
                f"({opens} '{{' vs {closes} '}}'). Provável typo no template."
            )
            warnings.append(msg)
            logger.warning(msg)
    return warnings


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def fill_template(
    resolved: dict[str, object],
    config: Config,
    workdir: Path | None = None,
) -> FillReport:
    """Pipeline completo de preparação do `.tex`:

    prepara workdir -> substitui -> normaliza Unicode -> gera placeholders ->
    valida chaves. Retorna :class:`FillReport`.
    """
    if workdir is None:
        workdir = prepare_workdir(config)
    report = substitute(workdir, resolved, config)
    normalize_unicode_for_latex(workdir, config)
    report.placeholders_created = ensure_referenced_images(workdir, config)
    report.brace_warnings = validate_braces(workdir)
    return report
