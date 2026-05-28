# Gerador de Relatório de Diagnóstico Energético — Excel → LaTeX → PDF

Aplicação que recebe uma planilha `.xlsx` de diagnóstico energético, mescla os
dados em um template LaTeX (classe `DIAG_PMS.cls` / abnTeX2), gera dois
gráficos e compila um **PDF visualmente idêntico ao template original**.

> **PDF é o formato oficial e único entregável.**

---

## 1. Início rápido

> Pré-requisitos: **Python 3.11+** (testado em 3.14). **Não é preciso instalar
> LaTeX no sistema** — usamos o **Tectonic** (XeLaTeX portátil) embutido em
> `bin/`, que baixa os pacotes do CTAN sob demanda na primeira execução.

```powershell
# 1) Criar o ambiente virtual e instalar dependências
.\setup.ps1

# 2) Iniciar a interface web (abre no navegador)
.\run_ui.ps1
```

Na interface: **envie o `.xlsx` → clique em "Gerar Relatório" → baixe o PDF**.

### Linha de comando

```powershell
.\.venv\Scripts\python.exe -m app "RAD CMEI Olga Benário.xlsx"
# opções: --keep-workdir | --first-wins
```

### Testes

```powershell
.\.venv\Scripts\python.exe -m pytest
```

---

## 2. Por que PDF como deliverable

O template usa `DIAG_PMS.cls` (baseada em **abnTeX2**), com comandos
customizados (`\imprimircapa`, listas de figuras/tabelas, sumário próprio,
cores e tabelas formatadas com `\rowcolor`/`\cellcolor`). Esse design existe
**para PDF**.

- **PDF (Tectonic / XeLaTeX):** mantém **100% da fidelidade** — capa, cores
  de tabela (verde/vermelho/amarelo no checklist NR), listas de figuras e
  tabelas, sumário ABNT, numeração de página, fontes Latin Modern.

---

## 3. Pipeline

```
.xlsx ─▶ excel_loader ─▶ charts ───────▶ Figuras/Grafico 1.png, Grafico 2.png
                │                                   │
                ▼                                   ▼
          mapa chave→valor          latex_filler (cópia temp do template,
          + conflitos + dados        substitui <<chaves>>, normaliza Unicode,
            dos gráficos             gera placeholders) ─▶ latex_compiler
                                       (Tectonic + verifica fonte) ─▶ PDF
```

1. **Lê** a aba `Tabela de Transferência` (col **D** = chave `<<...>>`,
   col **E** = valor); aplica política de conflito; extrai dados dos gráficos.
2. **Gera** os dois gráficos (PNG) em `Figuras/`.
3. **Copia** o template para um diretório temporário (o original não é tocado),
   **substitui** todas as chaves, **normaliza** Unicode `—`/`–`/`…` para as
   ligaduras LaTeX (`---`/`--`/`\ldots{}`), e **gera placeholders** para
   imagens referenciadas que ainda não existam (ex.: fotos de inspeção que
   serão tiradas em campo).
4. **Verifica** que nenhum `<<...>>` sobrou nos `.tex` (verificação
   autoritativa da DoD; o equivalente no PDF é frágil — xelatex renderiza
   `<<`/`>>` como guillemets `«`/`»`).
5. **Compila** via Tectonic (`tectonic -X compile -Z continue-on-errors …`)
   produzindo o PDF.

### Estrutura

```
app/
  config.py          # parâmetros configuráveis (dataclass)
  formatters.py      # escaping LaTeX + formatação data/número pt-BR
  excel_loader.py    # parsing da aba, conflitos, extração dos gráficos
  charts.py          # Gráfico 1 (pizza 3D) e Gráfico 2 (barras) + placeholders
  latex_filler.py    # cópia, substituição, normalização Unicode, placeholders
  latex_compiler.py  # Tectonic + verificação no PDF
  tectonic_setup.py  # baixa o Tectonic estático no Linux (Streamlit Cloud)
  pipeline.py        # orquestra tudo
  ui/
    app.py           # entry-point Streamlit (run_ui.* aponta aqui)
    components.py    # header, upload, progresso, downloads…
    styles.py        # CSS + CDN Google Material Icons
  __main__.py        # CLI (python -m app)
bin/tectonic.exe     # XeLaTeX portátil no Windows (no Linux é baixado em runtime)
templates/latex/     # template empacotado (cópia; não é mutado em execução)
tests/               # pytest (usa RAD CMEI Olga Benário.xlsx como fixture)
```

---

## 4. Regras de negócio

### Substituição de chaves
- Casamento **exato de token** (`<<...>>`), em uma única passada — imune a
  colisão de prefixo (`<<consumoTotal>>` **não** casa dentro de
  `<<ConsumoTotalUm>>`).
- Chave no LaTeX **sem** valor → placeholder `—` (configurável) + **aviso**.
- Chave **só** na planilha → ignorada com registro (as 11 chaves alimentadoras
  dos gráficos, ex.: `<<consumoIluminacao>>`, `<<propFotovoltaico>>`).

### Conflito de chaves duplicadas
- Política padrão **`last-wins`** (última linha não-vazia vence); aviso só em
  divergência real de valores.
- Caso real: `<<consumoTotal>>` = `47,95` (linha 52, kWh) **vs** `18,74`
  (linha 141, MWh). Como a chave só é usada no capítulo 10 (contexto MWh),
  `last-wins` → `18,74` é o valor correto.

### Formatação (pt-BR)
- **Datas** → `dd/mm/aaaa` (ex.: `2026-03-05` → `05/03/2026`).
- **Números** → milhar `.`, decimal `,`, 2 casas; inteiros exatos sem casas.
- **Ausentes/None** → placeholder `—`.

### Escaping LaTeX
`& % $ # _ { } ~ ^ \` são escapados em uma passada (sem duplo-escape).

### Gráfico 1 — Pizza com aparência 3D
- Fatias: Iluminação, Climatização, Sistemas Motrizes, Refrigeração, Outros.
- **Total excluído** (evita dupla contagem); fatias com valor **0 omitidas**
  e registradas.
- Efeito 3D: disco em perspectiva (elipse achatada) com paredes laterais por
  fatia e oclusão correta + sombra. Percentuais dentro (fatias grandes) ou
  fora com linha-guia (fatias <8%).

### Gráfico 2 — Barras (consumo mensal)
- 12 meses pareados posicionalmente; meses "Sem Histórico Disponível" são
  descartados (no exemplo, 4 últimos).
- Barras com valores anotados em pt-BR, eixos rotulados, grade leve.

### Placeholders para imagens ausentes
O template referencia fotos de inspeção (`NR01ACFT.png`, `sub01.png`, etc.)
que serão tiradas em campo. Se uma imagem referenciada não existir, é gerado
um **PNG de placeholder** ("Imagem indisponível: NR01ACFT.png") com o mesmo
nome, para que o Tectonic compile com sucesso. Em produção, o operador
substitui esses arquivos pelas fotos reais antes de gerar o relatório.

---

## 5. Decisões técnicas e limitações

### LaTeX engine: Tectonic (no lugar de TeX Live / MiKTeX)
Tectonic é um binário XeLaTeX único (~19 MB), instala em `bin/` sem admin,
baixa pacotes do CTAN sob demanda (cacheados depois). Equivalente a
`latexmk -xelatex`. **Primeiro `run` é mais lento** (downloads); execuções
subsequentes são imediatas.

### Erros recuperáveis tolerados
Usamos `-Z continue-on-errors` para igualar o comportamento padrão do
pdflatex/xelatex. O template original tem um padrão na capa
(`\end{minipage}\\` em modo vertical) que Tectonic classificaria como erro
fatal por padrão; com a flag o engine recupera, exatamente como faria um
`xelatex` clássico.

### Normalização Unicode
Como o template usa `\usepackage[T1]{fontenc}` + lmodern, alguns caracteres
Unicode (`—`, `–`, `…`) não têm glifo direto sob xelatex; convertemos para
as ligaduras LaTeX (`---`, `--`, `\ldots{}`) antes da compilação. Isso é
aplicado a todos os `.tex` da cópia de trabalho.

### Verificação anti-`<<>>` autoritativa em **fonte**, não em PDF
xelatex + lmodern renderizam `<<` e `>>` como guillemets `«` `»`; uma
verificação pelo texto extraído do PDF é frágil. Por isso a verificação
oficial é em **fonte**: após `substitute()`, varre todos os `.tex` em busca
de `<<...>>` e aborta o build se encontrar. Como `substitute()` sempre
substitui (por valor ou por placeholder), esta verificação serve como
assertion paranoico; se um dia falhar, indica bug do filler.

---

## 6. Critérios de aceite (Definition of Done)

| # | Critério | Status |
|---|----------|:---:|
| 1 | PDF gerado e baixável pela interface | ✅ |
| 2 | PDF **sem** `<<`/`>>` (verificado em fonte, autoritativo) | ✅ |
| 3 | PDF **visualmente idêntico** ao template (cores, tabelas, fontes ABNT) | ✅ |
| 4 | `Figuras/Grafico 1.png` (pizza 3D, sem total) e `Grafico 2.png` (barras, sem "Sem Histórico") embutidos | ✅ |
| 5 | Datas `dd/mm/aaaa` e números pt-BR | ✅ |
| 6 | Conflitos e chaves sem valor nos logs/avisos | ✅ |
| 7 | `pytest` passa; README documenta a estratégia | ✅ (38 testes) |
