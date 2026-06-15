# -*- coding: utf-8 -*-
from app import excel_loader
from app.config import Config


def test_loads_expected_key_count(load_result):
    # 216 chaves distintas na coluna D do exemplo preenchido.
    assert len(load_result.resolved) == 216


def test_detects_only_real_conflict(load_result):
    # Apenas <<consumoTotal>> tem valores divergentes (47.95 vs 18.74).
    conflict_keys = [c.key for c in load_result.conflicts]
    assert conflict_keys == ["<<consumoTotal>>"]


def test_last_wins_default(load_result):
    # last-wins -> valor da linha 141 (contexto MWh, usado no capítulo 10).
    assert load_result.resolved["<<consumoTotal>>"] == 18.74248


def test_first_wins_policy(fixture_xlsx):
    res = excel_loader.load(fixture_xlsx, Config(conflict_policy="first-wins"))
    assert res.resolved["<<consumoTotal>>"] == 47.95286775


def test_markers_valid_on_model(model_load_result):
    # O modelo novo tem os 5 marcadores nas linhas esperadas
    # (F47=Gráfico 1, F77=Gráfico 3, F102=Gráfico 2, F115=Gráfico 4, F151=Gráfico 5).
    assert model_load_result.marker_warnings == []


def test_model_has_new_graph_keys(model_load_result):
    # As chaves dos novos gráficos (3/4/5) existem no modelo.
    r = model_load_result.resolved
    for k in ("<<ConsumoPontaUm>>", "<<ConsumoForaPontaDoze>>",
              "<<DemandaPontaUm>>", "<<DemandaForaPontaDoze>>",
              "<<despesaEnergiaUm>>", "<<demandaContratadaToleranciaNP>>",
              "<<demandaContratadaToleranciaFP>>"):
        assert k in r


def test_new_graph_series_shapes(model_load_result):
    # Séries posicionais alinhadas com os meses (Ponta/Fora Ponta/Despesa).
    s, d, e = model_load_result.stacked, model_load_result.demand, model_load_result.expense
    assert len(s.ponta) == len(s.fora_ponta) == len(s.months)
    assert len(d.ponta) == len(d.fora_ponta) == len(d.months)
    assert len(e.values) == len(e.months)


def test_pie_excludes_total_and_zero(load_result):
    pie = load_result.pie
    # Motores=0 omitido; total excluído -> restam 4 fatias.
    assert pie.labels == ["Iluminação", "Climatização", "Refrigeração", "Outros"]
    assert pie.dropped_zero == ["Sistemas Motrizes"]
    assert "<<consumoTotal>>" not in pie.labels
    assert abs(pie.values[1] - 38.194308) < 1e-6


def test_bar_drops_sem_historico(load_result):
    bar = load_result.bar
    assert bar.months == ["mai/25", "jul/25", "out/25", "nov/25",
                          "dez/25", "jan/26", "fev/26", "mar/26"]
    assert len(bar.values) == 8
    assert len(bar.dropped) == 4
    assert bar.values[0] == 996.6


def test_bar_drop_zero_optional(fixture_xlsx):
    res = excel_loader.load(fixture_xlsx, Config(graph2_drop_zero_values=True))
    # Sem zeros entre os 8 meses com histórico -> continua 8.
    assert len(res.bar.values) == 8
    assert all(v != 0 for v in res.bar.values)


def test_planilha_only_keys(load_result):
    # As 11 chaves alimentadoras de gráfico não têm alvo no LaTeX, mas existem.
    for k in ("<<consumoIluminacao>>", "<<propFotovoltaico>>", "<<mesMenorConsumo>>"):
        assert k in load_result.resolved
