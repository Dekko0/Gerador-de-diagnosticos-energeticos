"""CSS customizado + CDN do Google Material Icons.

A função :func:`setup_page` configura o ``st.set_page_config`` e injeta o
``<link>`` do CDN e o ``<style>`` **uma única vez** no topo da página. Tudo o
mais (componentes) pode então usar ``<span class="material-icons">…</span>``
e as classes definidas aqui.

Se o CDN não carregar (ambiente offline), os ícones ficam invisíveis mas
**a UI não quebra** — botões e headers preservam emojis de fallback
(▶, 📥, ✅, ⚠️, ℹ️) garantindo legibilidade.

Paleta:
    success  ``#4CAF50`` · warning ``#FF9800`` · info ``#2196F3`` · primary ``#7C83FD``
"""

from __future__ import annotations

import streamlit as st

_GLOBAL_CSS = """
<link href="https://fonts.googleapis.com/icon?family=Material+Icons|Material+Icons+Outlined"
      rel="stylesheet">
<style>
  
</style>
"""


def setup_page() -> None:
    """Configura a página Streamlit e injeta CSS + CDN **uma única vez**.

    Deve ser a **primeira** chamada Streamlit em ``main()`` — qualquer outra
    chamada antes do ``st.set_page_config`` causaria warning/erro.
    """
    st.set_page_config(
        page_title="Gerador de Relatórios",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
