"""Configuração central da aplicação.

Todos os parâmetros ajustáveis vivem aqui, num único :class:`Config` (dataclass).
Nada de "números mágicos" espalhados pelos módulos: política de conflito,
placeholders, formatos de data/número, marcadores e chaves dos gráficos, etc.
são todos definidos (e documentados) neste arquivo.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Raiz do projeto (…/Gerador de Diagnosticos)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_tectonic_path() -> Path:
    """Localiza o Tectonic de forma multiplataforma.

    Procura primeiro no ``PATH`` (ex.: instalado via ``packages.txt``/apt no
    Linux do Streamlit Cloud); se não encontrar, cai para o binário portátil em
    ``bin/`` do projeto — ``tectonic.exe`` no Windows, ``tectonic`` nos demais.
    """
    found = shutil.which("tectonic")
    if found:
        return Path(found)
    binary = "tectonic.exe" if os.name == "nt" else "tectonic"
    return PROJECT_ROOT / "bin" / binary

#: Política de resolução de chaves duplicadas com valores divergentes.
ConflictPolicy = str  # "last-wins" | "first-wins"


@dataclass
class GraphSeriesKey:
    """Uma fatia/ponto de um gráfico, identificado pela chave estável da planilha.

    Usamos a chave ``<<...>>`` (única e estável) em vez de números de linha
    fixos, o que é robusto a edições do template e produz exatamente o mesmo
    pareamento posicional exigido pela especificação.
    """

    key: str          # ex.: "<<consumoIluminacao>>"
    label: str        # rótulo limpo p/ exibição, ex.: "Iluminação"


#: Sufixos ordinais por extenso usados nas chaves mensais (1..12).
_MONTH_SUFFIXES = (
    "Um", "Dois", "Tres", "Quatro", "Cinco", "Seis",
    "Sete", "Oito", "Nove", "Dez", "Onze", "Doze",
)


def month_keys(prefix: str) -> list[str]:
    """Gera as 12 chaves ``<<prefixUm>>`` .. ``<<prefixDoze>>`` (posicionais)."""
    return [f"<<{prefix}{suf}>>" for suf in _MONTH_SUFFIXES]


@dataclass
class Config:
    """Parâmetros de execução do pipeline. Instanciável com overrides."""

    # ------------------------------------------------------------------ #
    # Planilha — aba e colunas
    # ------------------------------------------------------------------ #
    sheet_name: str = "Tabela de Transferência"
    header_row: int = 1
    col_label: str = "A"      # rótulo/descrição do campo
    col_key: str = "D"        # chave <<...>>
    col_value: str = "E"      # valor
    col_marker: str = "F"     # marcador de gráfico ("Grafico 1"/"Grafico 2")
    key_pattern: str = r"^<<.+>>$"

    # ------------------------------------------------------------------ #
    # Resolução de conflitos / chaves faltantes
    # ------------------------------------------------------------------ #
    conflict_policy: ConflictPolicy = "last-wins"  # ou "first-wins"
    #: Placeholder visível para chaves do LaTeX sem valor na planilha
    #: (e para valores None/ausentes).
    missing_placeholder: str = "—"

    # ------------------------------------------------------------------ #
    # Formatação de valores
    # ------------------------------------------------------------------ #
    date_format: str = "%d/%m/%Y"          # 05/03/2026
    number_decimals: int = 2               # casas para floats não-inteiros
    thousands_sep: str = "."               # separador de milhar pt-BR
    decimal_sep: str = ","                 # separador decimal pt-BR

    # ------------------------------------------------------------------ #
    # Gráfico 1 — Pizza (pseudo-3D): distribuição do consumo por uso final
    # ------------------------------------------------------------------ #
    graph1_marker: str = "Grafico 1"
    graph1_marker_expected_row: int = 47   # apenas para validação/aviso
    graph1_total_key: str = "<<consumoTotal>>"  # total — EXCLUÍDO da pizza
    graph1_output_name: str = "Grafico 1.png"
    graph1_title: str = "Distribuição do consumo de energia elétrica por uso final"
    #: Se True, fatias com valor <= 0 são omitidas da pizza (e registradas em log).
    graph1_drop_zero_slices: bool = True
    graph1_slices: list[GraphSeriesKey] = field(
        default_factory=lambda: [
            GraphSeriesKey("<<consumoIluminacao>>", "Iluminação"),
            GraphSeriesKey("<<consumoClimatizacao>>", "Climatização"),
            GraphSeriesKey("<<consumoMotores>>", "Sistemas Motrizes"),
            GraphSeriesKey("<<consumoRefrigeracao>>", "Refrigeração"),
            GraphSeriesKey("<<consumoOutros>>", "Outros"),
        ]
    )

    # ------------------------------------------------------------------ #
    # Gráfico 2 — Barras: perfil de consumo mensal (12 meses)
    # ------------------------------------------------------------------ #
    graph2_marker: str = "Grafico 2"
    graph2_marker_expected_row: int = 102  # apenas para validação/aviso
    graph2_output_name: str = "Grafico 2.png"
    graph2_title: str = "Perfil de consumo mensal de energia elétrica"
    graph2_ylabel: str = "Consumo (kWh)"
    graph2_xlabel: str = "Mês"
    graph2_chart_type: str = "bar"         # "bar" | "line"
    #: Rótulo que indica mês sem histórico — pontos assim são descartados.
    graph2_no_history_label: str = "Sem Histórico Disponível"
    #: Se True, descarta também meses com consumo igual a zero.
    graph2_drop_zero_values: bool = False
    #: Chaves de valor (consumo total) e de mês, posicionais 1..12.
    graph2_value_keys: list[str] = field(default_factory=lambda: month_keys("ConsumoTotal"))
    graph2_month_keys: list[str] = field(default_factory=lambda: month_keys("mes"))

    # ------------------------------------------------------------------ #
    # Gráfico 3 — Barras empilhadas: consumo Ponta vs. Fora Ponta (12 meses)
    # ------------------------------------------------------------------ #
    graph3_marker: str = "Grafico 3"
    graph3_marker_expected_row: int = 77   # apenas para validação/aviso
    graph3_output_name: str = "Grafico 3.png"
    graph3_title: str = "Perfil de consumo mensal — Ponta e Fora Ponta"
    graph3_ylabel: str = "Consumo (kWh)"
    graph3_ponta_label: str = "Ponta"
    graph3_fora_ponta_label: str = "Fora Ponta"
    graph3_ponta_keys: list[str] = field(default_factory=lambda: month_keys("ConsumoPonta"))
    graph3_fora_ponta_keys: list[str] = field(default_factory=lambda: month_keys("ConsumoForaPonta"))

    # ------------------------------------------------------------------ #
    # Gráfico 4 — Demanda comparativa Ponta/Fora Ponta + linhas de contrato
    # ------------------------------------------------------------------ #
    graph4_marker: str = "Grafico 4"
    graph4_marker_expected_row: int = 115  # apenas para validação/aviso
    graph4_output_name: str = "Grafico 4.png"
    graph4_title: str = "Demandas"
    graph4_ylabel: str = "kW"
    graph4_ponta_label: str = "Ponta"
    graph4_fora_ponta_label: str = "Fora Ponta"
    graph4_ponta_keys: list[str] = field(default_factory=lambda: month_keys("DemandaPonta"))
    graph4_fora_ponta_keys: list[str] = field(default_factory=lambda: month_keys("DemandaForaPonta"))
    #: Linhas horizontais de referência (demanda contratada e tolerâncias).
    graph4_contratada_key: str = "<<demandaContratada>>"
    graph4_tolerancia_key: str = "<<demandaContratadaTolerancia>>"
    graph4_tolerancia_np_key: str = "<<demandaContratadaToleranciaNP>>"   # Ponta
    graph4_tolerancia_fp_key: str = "<<demandaContratadaToleranciaFP>>"   # Fora Ponta

    # ------------------------------------------------------------------ #
    # Gráfico 5 — Barras: despesa mensal com energia elétrica (12 meses)
    # ------------------------------------------------------------------ #
    graph5_marker: str = "Grafico 5"
    graph5_marker_expected_row: int = 151  # apenas para validação/aviso
    graph5_output_name: str = "Grafico 5.png"
    graph5_title: str = "Despesa mensal com energia elétrica"
    graph5_ylabel: str = "Despesa (R$)"
    graph5_value_keys: list[str] = field(default_factory=lambda: month_keys("despesaEnergia"))

    # ------------------------------------------------------------------ #
    # Template / saída
    # ------------------------------------------------------------------ #
    template_dir: Path = PROJECT_ROOT / "templates" / "latex"
    figures_subdir: str = "Figuras"
    main_tex_name: str = "DIAG_PMS.tex"  # arquivo principal do template

    # ------------------------------------------------------------------ #
    # Compilação LaTeX -> PDF (deliverable PRIMÁRIO)
    # ------------------------------------------------------------------ #
    #: Caminho do Tectonic (XeLaTeX portátil; baixa pacotes do CTAN sob demanda).
    #: Detectado em runtime: ``tectonic`` no PATH ou binário local em ``bin/``.
    tectonic_path: Path = field(default_factory=_default_tectonic_path)
    #: Argumentos do Tectonic. ``continue-on-errors`` deixa o engine "perdoar"
    #: erros recuperáveis (como o ``\\`` no fim de minipage da capa abntex2),
    #: equivalente ao comportamento padrão do pdflatex/xelatex.
    tectonic_extra_args: list[str] = field(
        default_factory=lambda: [
            "-X", "compile",
            "--keep-intermediates", "--keep-logs",
            "-Z", "continue-on-errors",
        ]
    )

    # ------------------------------------------------------------------ #
    # Normalização de Unicode para xelatex + T1
    # ------------------------------------------------------------------ #
    #: O template usa ``[T1]{fontenc}`` + lmodern; com xelatex, caracteres
    #: Unicode "exóticos" precisam ser convertidos nos comandos LaTeX
    #: correspondentes ou renderizam errado (ex.: ``º`` virava ``z``, fazendo
    #: ``nº`` aparecer como ``nz``). Aplicado a TODOS os ``.tex`` (template e
    #: valores substituídos).
    #: Mapa completo verificado empiricamente (Tectonic) — cada caractere cru
    #: renderizava errado sob T1+lmodern e o comando ao lado produz o glifo
    #: correto. Requer ``textcomp`` (carregado no DIAG_PMS.cls) para os símbolos.
    unicode_replacements: dict[str, str] = field(
        default_factory=lambda: {
            # Travessões, reticências e sinal de menos
            "—": "---",                   # em-dash
            "–": "--",                    # en-dash
            "−": "-",                     # minus sign (U+2212)
            "…": r"\ldots{}",
            # Ordinais e grau
            "º": r"\textordmasculine{}",  # ordinal masculino (nº) — saía "ž"
            "ª": r"\textordfeminine{}",   # ordinal feminino (1ª) — saía "ł"
            "°": r"\textdegree{}",        # grau (25°C) — saía "ř"
            # Sobrescritos (ex.: m² saía "m2"/"mš")
            "¹": r"\textsuperscript{1}",
            "²": r"\textsuperscript{2}",
            "³": r"\textsuperscript{3}",
            "⁰": r"\textsuperscript{0}",
            "⁴": r"\textsuperscript{4}",
            "⁵": r"\textsuperscript{5}",
            "⁶": r"\textsuperscript{6}",
            "⁷": r"\textsuperscript{7}",
            "⁸": r"\textsuperscript{8}",
            "⁹": r"\textsuperscript{9}",
            "ⁿ": r"\textsuperscript{n}",
            "ⁱ": r"\textsuperscript{i}",
            "⁺": r"\textsuperscript{+}",
            "⁻": r"\textsuperscript{-}",
            "⁼": r"\textsuperscript{=}",
            "⁽": r"\textsuperscript{(}",
            "⁾": r"\textsuperscript{)}",
            # Subscritos (ex.: CO₂, H₂O)
            "₀": r"\textsubscript{0}",
            "₁": r"\textsubscript{1}",
            "₂": r"\textsubscript{2}",
            "₃": r"\textsubscript{3}",
            "₄": r"\textsubscript{4}",
            "₅": r"\textsubscript{5}",
            "₆": r"\textsubscript{6}",
            "₇": r"\textsubscript{7}",
            "₈": r"\textsubscript{8}",
            "₉": r"\textsubscript{9}",
            "₊": r"\textsubscript{+}",
            "₋": r"\textsubscript{-}",
            "₌": r"\textsubscript{=}",
            "₍": r"\textsubscript{(}",
            "₎": r"\textsubscript{)}",
            # Símbolos matemáticos / unidades (textcomp)
            "µ": r"\textmu{}",            # micro (U+00B5)
            "μ": r"\textmu{}",            # mu grego (U+03BC)
            "×": r"\texttimes{}",
            "÷": r"\textdiv{}",
            "±": r"\textpm{}",
            "½": r"\textonehalf{}",
            "¼": r"\textonequarter{}",
            "¾": r"\textthreequarters{}",
            "·": r"\textperiodcentered{}",
            "•": r"\textbullet{}",
            # Aspas tipográficas, espaço inquebrável e emoji comum (defesa)
            "\u00a0": "~",                # NBSP — saía "ă"
            "“": "``",
            "”": "''",
            "‘": "`",
            "’": "'",
            "❌": "[x]",                  # emoji sem glifo em lmodern/T1
        }
    )

    #: Texto usado em PNGs gerados para imagens referenciadas mas ausentes
    #: (a inspeção real produz fotos NRxxACFT.png, sub01.png, etc.).
    missing_image_label: str = "Imagem indisponível"

    @property
    def figures_dirname(self) -> str:
        return self.figures_subdir
