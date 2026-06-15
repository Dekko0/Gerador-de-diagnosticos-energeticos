# -*- coding: utf-8 -*-
import pytest

from app import charts
from app.config import Config
from app.excel_loader import BarData, DemandData, ExpenseData, PieData, StackedBarData

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


def test_stacked_chart_creates_valid_png(tmp_path, config):
    data = StackedBarData(months=["jan/25", "fev/25"], ponta=[10.0, 20.0],
                          fora_ponta=[30.0, 40.0])
    out = charts.save_stacked_bar_chart(data, tmp_path / "Grafico 3.png", config)
    assert out.exists() and out.read_bytes()[:8] == _PNG_MAGIC


def test_demand_chart_single_tolerance(tmp_path, config):
    data = DemandData(months=["jan/25", "fev/25"], ponta=[5.0, 6.0],
                      fora_ponta=[30.0, 40.0], contratada=80.0, tolerancia=84.0)
    out = charts.save_demand_chart(data, tmp_path / "Grafico 4.png", config)
    assert out.exists() and out.read_bytes()[:8] == _PNG_MAGIC


def test_demand_chart_np_fp_tolerances(tmp_path, config):
    data = DemandData(months=["jan/25", "fev/25"], ponta=[5.0, 6.0],
                      fora_ponta=[30.0, 40.0], contratada=80.0,
                      tolerancia_np=84.0, tolerancia_fp=88.0)
    out = charts.save_demand_chart(data, tmp_path / "Grafico 4b.png", config)
    assert out.exists() and out.read_bytes()[:8] == _PNG_MAGIC


def test_expense_chart_creates_valid_png(tmp_path, config):
    data = ExpenseData(months=["jan/25", "fev/25"], values=[2500.0, 3100.0])
    out = charts.save_expense_bar_chart(data, tmp_path / "Grafico 5.png", config)
    assert out.exists() and out.read_bytes()[:8] == _PNG_MAGIC


def test_demand_raises_on_empty(tmp_path, config):
    with pytest.raises(ValueError):
        charts.save_demand_chart(
            DemandData(months=[], ponta=[], fora_ponta=[]), tmp_path / "x.png", config)


def test_generate_charts_from_real_data(tmp_path, load_result, config):
    paths = charts.generate_charts(load_result, tmp_path, config)
    assert (tmp_path / config.graph1_output_name).exists()
    assert (tmp_path / config.graph2_output_name).exists()
    assert len(paths) == 5
    for p in paths.values():
        assert p.stat().st_size > 0


def _empty_load_result():
    from app.excel_loader import LoadResult
    return LoadResult(
        resolved={}, occurrences={}, conflicts=[], planilha_keys=set(),
        pie=PieData(labels=[], values=[]), bar=BarData(months=[], values=[]),
        stacked=StackedBarData(months=[], ponta=[], fora_ponta=[]),
        demand=DemandData(months=[], ponta=[], fora_ponta=[]),
        expense=ExpenseData(months=[], values=[]),
        marker_warnings=[],
    )


def test_generate_charts_falls_back_to_placeholder(tmp_path, config):
    """Sem dados plotáveis, gera placeholder (5 gráficos) em vez de falhar."""
    paths = charts.generate_charts(_empty_load_result(), tmp_path, config)
    assert len(paths) == 5
    for p in paths.values():
        assert p.exists()
        assert p.read_bytes()[:8] == _PNG_MAGIC
