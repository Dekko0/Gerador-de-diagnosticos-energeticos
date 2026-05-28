# -*- coding: utf-8 -*-
import pytest

from app import charts
from app.config import Config
from app.excel_loader import BarData, PieData

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_pie_chart_creates_valid_png(tmp_path, config):
    pie = PieData(labels=["A", "B", "C"], values=[10.0, 20.0, 5.0])
    out = charts.save_pie_chart(pie, tmp_path / "Grafico 1.png", config)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == _PNG_MAGIC


def test_bar_chart_creates_valid_png(tmp_path, config):
    bar = BarData(months=["jan/25", "fev/25"], values=[100.0, 200.0])
    out = charts.save_bar_chart(bar, tmp_path / "Grafico 2.png", config)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == _PNG_MAGIC


def test_pie_raises_on_empty(tmp_path, config):
    with pytest.raises(ValueError):
        charts.save_pie_chart(PieData(labels=[], values=[]), tmp_path / "x.png", config)


def test_bar_raises_on_empty(tmp_path, config):
    with pytest.raises(ValueError):
        charts.save_bar_chart(BarData(months=[], values=[]), tmp_path / "x.png", config)


def test_generate_charts_from_real_data(tmp_path, load_result, config):
    paths = charts.generate_charts(load_result, tmp_path, config)
    assert (tmp_path / config.graph1_output_name).exists()
    assert (tmp_path / config.graph2_output_name).exists()
    for p in paths.values():
        assert p.stat().st_size > 0


def test_generate_charts_falls_back_to_placeholder(tmp_path, config):
    """Sem dados plotáveis, gera placeholder em vez de falhar."""
    from app.excel_loader import LoadResult

    empty = LoadResult(
        resolved={}, occurrences={}, conflicts=[], planilha_keys=set(),
        pie=PieData(labels=[], values=[]), bar=BarData(months=[], values=[]),
        marker_warnings=[],
    )
    paths = charts.generate_charts(empty, tmp_path, config)
    for p in paths.values():
        assert p.exists()
        assert p.read_bytes()[:8] == _PNG_MAGIC
