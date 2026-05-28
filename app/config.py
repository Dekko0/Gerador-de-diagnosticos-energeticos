"""Configuração central da aplicação.

Todos os parâmetros ajustáveis vivem aqui, num único :class:`Config` (dataclass).
Nada de "números mágicos" espalhados pelos módulos: política de conflito,
placeholders, formatos de data/número, marcadores e chaves dos gráficos, etc.
são todos definidos (e documentados) neste arquivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Raiz do projeto (…/Gerador de Diagnosticos)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
    graph2_marker_expected_row: int = 101  # apenas para validação/aviso
    graph2_output_name: str = "Grafico 2.png"
    graph2_title: str = "Perfil de consumo mensal de energia elétrica"
    graph2_ylabel: str = "Consumo (kWh)"
    graph2_xlabel: str = "Mês"
    graph2_chart_type: str = "bar"         # "bar" | "line"
    #: Rótulo que indica mês sem histórico — pontos assim são descartados.
    graph2_no_history_label: str = "Sem Histórico Disponível"
    #: Se True, descarta também meses com consumo igual a zero.
    graph2_drop_zero_values: bool = False
    #: Pares (chave de valor, chave de mês), posicionais 1..12.
    graph2_value_keys: list[str] = field(
        default_factory=lambda: [
            "<<ConsumoTotalUm>>", "<<ConsumoTotalDois>>", "<<ConsumoTotalTres>>",
            "<<ConsumoTotalQuatro>>", "<<ConsumoTotalCinco>>", "<<ConsumoTotalSeis>>",
            "<<ConsumoTotalSete>>", "<<ConsumoTotalOito>>", "<<ConsumoTotalNove>>",
            "<<ConsumoTotalDez>>", "<<ConsumoTotalOnze>>", "<<ConsumoTotalDoze>>",
        ]
    )
    graph2_month_keys: list[str] = field(
        default_factory=lambda: [
            "<<mesUm>>", "<<mesDois>>", "<<mesTres>>", "<<mesQuatro>>",
            "<<mesCinco>>", "<<mesSeis>>", "<<mesSete>>", "<<mesOito>>",
            "<<mesNove>>", "<<mesDez>>", "<<mesOnze>>", "<<mesDoze>>",
        ]
    )

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
    tectonic_path: Path = PROJECT_ROOT / "bin" / "tectonic.exe"
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
    # Conversão PDF -> DOCX (deliverable SECUNDÁRIO; opcional)
    # ------------------------------------------------------------------ #
    #: Onde procurar o LibreOffice. Se ``None`` em todos, o DOCX é pulado.
    libreoffice_candidates: list[Path] = field(
        default_factory=lambda: [
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
            Path(r"C:\Users\Dekko\AppData\Local\Programs\LibreOffice\program\soffice.exe"),
            Path("/usr/bin/libreoffice"),
            Path("/usr/local/bin/libreoffice"),
        ]
    )

    # ------------------------------------------------------------------ #
    # Normalização de Unicode para xelatex + T1
    # ------------------------------------------------------------------ #
    #: O template usa ``[T1]{fontenc}`` + lmodern; com xelatex, caracteres
    #: Unicode "exóticos" (— en/em-dash, …) precisam ser convertidos nas
    #: ligaduras LaTeX correspondentes ou ficam ausentes na fonte.
    unicode_replacements: dict[str, str] = field(
        default_factory=lambda: {
            "—": "---",   # em-dash
            "–": "--",    # en-dash
            "−": "-",     # minus sign
            "…": r"\ldots{}",
        }
    )

    #: Texto usado em PNGs gerados para imagens referenciadas mas ausentes
    #: (a inspeção real produz fotos NRxxACFT.png, sub01.png, etc.).
    missing_image_label: str = "Imagem indisponível"

    @property
    def figures_dirname(self) -> str:
        return self.figures_subdir

    def find_libreoffice(self) -> Path | None:
        """Retorna o primeiro LibreOffice existente entre os candidatos, ou None."""
        import shutil
        for p in self.libreoffice_candidates:
            if p.exists():
                return p
        for name in ("soffice", "libreoffice"):
            found = shutil.which(name)
            if found:
                return Path(found)
        return None
