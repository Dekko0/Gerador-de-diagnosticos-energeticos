"""Pacote da interface Streamlit (``app/ui``).

Submódulos:

* ``styles``     — CSS customizado + CDN do Google Material Icons.
* ``components`` — componentes reutilizáveis (header, upload, progresso, …).
* ``app``        — orquestração do fluxo (`streamlit run app/ui/app.py`).
"""

from app.ui.app import main  # noqa: F401  (entrada conveniente)
