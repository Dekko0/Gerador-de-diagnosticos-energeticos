"""Formatação de valores e escaping de caracteres especiais do LaTeX.

Separa duas responsabilidades:

* :func:`escape_latex` — torna um texto seguro para inserção em LaTeX.
* :func:`format_value` — converte um valor cru (datetime/float/int/str/None)
  na string final pt-BR pronta para o documento (já com escaping aplicado
  ao conteúdo textual).
"""

from __future__ import annotations

import datetime as _dt
import re
from numbers import Real

from .config import Config

# --------------------------------------------------------------------------- #
# Escaping LaTeX
# --------------------------------------------------------------------------- #
# Mapa caractere -> sequência LaTeX. A barra invertida vem primeiro porque a
# substituição é feita em UMA passada (re.sub não reprocessa a própria saída),
# então as chaves introduzidas por \textbackslash{} etc. não são re-escapadas.
_LATEX_SPECIALS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

_LATEX_PATTERN = re.compile("|".join(re.escape(c) for c in _LATEX_SPECIALS))


def escape_latex(text: str) -> str:
    """Escapa os caracteres especiais do LaTeX num texto.

    Trata corretamente ``~``, ``^`` e ``\\`` (que exigem comandos dedicados)
    em uma única passada, evitando duplo-escape.

    >>> escape_latex("100% & R$ a_b ~x^2 \\\\ {c}")
    '100\\\\% \\\\& R\\\\$ a\\\\_b \\\\textasciitilde{}x\\\\textasciicircum{}2 \\\\textbackslash{} \\\\{c\\\\}'
    """
    if not text:
        return text
    return _LATEX_PATTERN.sub(lambda m: _LATEX_SPECIALS[m.group()], text)


# --------------------------------------------------------------------------- #
# Formatação numérica pt-BR
# --------------------------------------------------------------------------- #
def _swap_separators(text: str, thousands: str, decimal: str) -> str:
    """Converte o formato US ('1,234.56') para o configurado (pt-BR: '1.234,56')."""
    placeholder = "\x00"
    return (
        text.replace(",", placeholder)  # milhar US -> placeholder
        .replace(".", decimal)          # decimal US -> decimal pt-BR
        .replace(placeholder, thousands)  # placeholder -> milhar pt-BR
    )


def _is_integer_value(value: Real) -> bool:
    """True para int ou float sem parte fracionária (ex.: 80, 80.0)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    try:
        return float(value).is_integer()
    except (ValueError, OverflowError):
        return False


def format_number(value: Real, config: Config) -> str:
    """Formata um número em pt-BR.

    * Inteiros exatos: sem casas decimais (``80`` -> ``"80"``, ``0`` -> ``"0"``).
    * Demais floats: arredondados para ``config.number_decimals`` casas.
    Em ambos os casos com separador de milhar.
    """
    if _is_integer_value(value):
        us = f"{int(round(float(value))):,}"  # ex.: "7,041,435,180"
        return _swap_separators(us, config.thousands_sep, config.decimal_sep)
    us = f"{float(value):,.{config.number_decimals}f}"  # ex.: "1,976.93"
    return _swap_separators(us, config.thousands_sep, config.decimal_sep)


def format_value(value: object, config: Config) -> str:
    """Converte um valor cru da planilha na string final pronta para o LaTeX.

    Regras:
    * ``None``/``""`` -> placeholder configurável.
    * ``datetime``/``date`` -> ``config.date_format`` (default ``dd/mm/aaaa``).
    * ``int``/``float`` -> :func:`format_number` (pt-BR; dígitos não precisam
      de escaping).
    * texto -> :func:`escape_latex`.
    """
    if value is None:
        return config.missing_placeholder

    # datetime antes de Real (datetime não é Real, mas deixamos explícito).
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.strftime(config.date_format)

    if isinstance(value, bool):
        # Evita que True/False caiam no ramo numérico.
        return escape_latex(str(value))

    if isinstance(value, Real):
        return format_number(value, config)

    text = str(value)
    if text == "":
        return config.missing_placeholder
    return escape_latex(text)
