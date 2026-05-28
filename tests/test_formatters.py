# -*- coding: utf-8 -*-
import datetime as dt

import pytest

from app.config import Config
from app.formatters import escape_latex, format_number, format_value


@pytest.fixture
def cfg():
    return Config()


# --- escaping ------------------------------------------------------------- #
def test_escape_all_specials():
    src = r"100% & R$ a_b #c {d} ~ ^ \ "
    out = escape_latex(src)
    assert r"\%" in out and r"\&" in out and r"\$" in out
    assert r"\_" in out and r"\#" in out and r"\{" in out and r"\}" in out
    assert r"\textasciitilde{}" in out
    assert r"\textasciicircum{}" in out
    assert r"\textbackslash{}" in out
    # nenhum caractere especial cru deve sobrar (exceto dentro das sequências)
    assert "%" not in out.replace(r"\%", "")
    assert "&" not in out.replace(r"\&", "")


def test_escape_no_double_escaping_of_backslash():
    # '\' vira \textbackslash{}; as chaves geradas NÃO podem ser re-escapadas
    assert escape_latex("\\") == r"\textbackslash{}"


def test_escape_empty():
    assert escape_latex("") == ""


# --- números -------------------------------------------------------------- #
def test_number_integer_exact_no_decimals(cfg):
    assert format_number(80, cfg) == "80"
    assert format_number(80.0, cfg) == "80"
    assert format_number(0, cfg) == "0"


def test_number_thousands_separator(cfg):
    assert format_number(7041435180, cfg) == "7.041.435.180"
    assert format_number(1000, cfg) == "1.000"


def test_number_float_two_decimals_ptbr(cfg):
    assert format_number(1976.92963427423, cfg) == "1.976,93"
    assert format_number(4707.45, cfg) == "4.707,45"
    assert format_number(0.154, cfg) == "0,15"


def test_number_negative(cfg):
    assert format_number(-12.5, cfg) == "-12,50"


# --- format_value --------------------------------------------------------- #
def test_value_datetime(cfg):
    assert format_value(dt.datetime(2026, 3, 5), cfg) == "05/03/2026"
    assert format_value(dt.date(2026, 12, 31), cfg) == "31/12/2026"


def test_value_none_and_empty_use_placeholder(cfg):
    assert format_value(None, cfg) == cfg.missing_placeholder
    assert format_value("", cfg) == cfg.missing_placeholder


def test_value_text_is_escaped(cfg):
    assert format_value("R$ 100 & cia", cfg) == r"R\$ 100 \& cia"


def test_value_keeps_plain_text(cfg):
    assert format_value("71 9935-2628", cfg) == "71 9935-2628"
