# -*- coding: utf-8 -*-
"""Fixtures compartilhadas dos testes."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Config
from app import excel_loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_XLSX = PROJECT_ROOT / "RAD CMEI Olga Benário.xlsx"


@pytest.fixture(scope="session")
def fixture_xlsx() -> Path:
    assert FIXTURE_XLSX.exists(), f"Fixture não encontrada: {FIXTURE_XLSX}"
    return FIXTURE_XLSX


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture(scope="session")
def load_result():
    """Resultado do excel_loader sobre a planilha de exemplo (cacheado)."""
    return excel_loader.load(FIXTURE_XLSX, Config())
