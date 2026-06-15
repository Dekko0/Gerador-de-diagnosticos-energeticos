# -*- coding: utf-8 -*-
"""Fixtures compartilhadas dos testes."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Config
from app import excel_loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
#: Exemplo PREENCHIDO no formato novo (5 gráficos com dados reais). Uso local.
FIXTURE_XLSX = PROJECT_ROOT / "RD_CMEI_TESTE.xlsx"
#: Modelo novo (em branco) com os 5 marcadores de gráfico e as chaves novas.
FIXTURE_MODEL = PROJECT_ROOT / "RD_MODELO.xlsx"


# As planilhas são de uso LOCAL (não versionadas — ver .gitignore). Quando
# ausentes (ex.: checkout limpo / Streamlit Cloud), os testes que dependem
# delas são PULADOS em vez de falharem.
@pytest.fixture(scope="session")
def fixture_xlsx() -> Path:
    if not FIXTURE_XLSX.exists():
        pytest.skip(f"Planilha de teste local ausente: {FIXTURE_XLSX.name}")
    return FIXTURE_XLSX


@pytest.fixture(scope="session")
def model_xlsx() -> Path:
    if not FIXTURE_MODEL.exists():
        pytest.skip(f"Modelo local ausente: {FIXTURE_MODEL.name}")
    return FIXTURE_MODEL


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture(scope="session")
def load_result():
    """Resultado do excel_loader sobre a planilha de exemplo (cacheado)."""
    if not FIXTURE_XLSX.exists():
        pytest.skip(f"Planilha de teste local ausente: {FIXTURE_XLSX.name}")
    return excel_loader.load(FIXTURE_XLSX, Config())


@pytest.fixture(scope="session")
def model_load_result():
    """Resultado do excel_loader sobre o modelo novo (cacheado)."""
    if not FIXTURE_MODEL.exists():
        pytest.skip(f"Modelo local ausente: {FIXTURE_MODEL.name}")
    return excel_loader.load(FIXTURE_MODEL, Config())
