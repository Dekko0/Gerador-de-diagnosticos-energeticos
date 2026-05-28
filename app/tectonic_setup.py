"""Garantia de disponibilidade do binário do Tectonic.

No Streamlit Cloud (Debian) o Tectonic **não** está disponível via ``apt``.
Por isso, quando não houver um ``tectonic`` no ``PATH`` nem o binário portátil
em ``bin/``, baixamos o **binário estático oficial** (musl, x86_64) das releases
do GitHub e o instalamos em ``bin/tectonic``. O download acontece uma única vez
por instância (o arquivo persiste enquanto a máquina viver).

No Windows usa-se o ``bin/tectonic.exe`` versionado/local — nada é baixado.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import tarfile
import tempfile
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

#: Versão fixada do Tectonic (binário estático Linux x86_64, variante musl).
TECTONIC_VERSION = "0.16.9"

#: URL do tarball estático para Linux x86_64 (musl = sem dependência de glibc).
_LINUX_URL = (
    "https://github.com/tectonic-typesetting/tectonic/releases/download/"
    f"tectonic%40{TECTONIC_VERSION}/"
    f"tectonic-{TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz"
)


def ensure_tectonic(tectonic_path: Path) -> Path:
    """Devolve um caminho utilizável do Tectonic, baixando-o se necessário.

    Ordem de resolução:

    1. Se houver um ``tectonic`` no ``PATH``, usa-o.
    2. Se ``tectonic_path`` já existir (ex.: ``bin/tectonic.exe`` no Windows ou
       um download anterior), usa-o.
    3. Caso contrário, em Linux, baixa o binário estático para ``tectonic_path``.

    No Windows (passo 3 não se aplica) devolve ``tectonic_path`` como está; se
    não existir, o compilador emitirá um erro claro.
    """
    found = shutil.which("tectonic")
    if found:
        return Path(found)

    if tectonic_path.exists():
        return tectonic_path

    if os.name == "nt":
        return tectonic_path  # Windows: espera-se o binário versionado em bin/.

    _download_linux_tectonic(tectonic_path)
    return tectonic_path


def _download_linux_tectonic(dest: Path) -> None:
    """Baixa e instala o binário estático do Tectonic em ``dest`` (Linux)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Tectonic ausente; baixando %s", _LINUX_URL)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tgz = tmp_path / "tectonic.tar.gz"
        urllib.request.urlretrieve(_LINUX_URL, tgz)  # noqa: S310 (URL fixa, https)

        with tarfile.open(tgz) as tar:
            member = next(
                m for m in tar.getmembers() if Path(m.name).name == "tectonic"
            )
            member.name = "tectonic"  # extrai sem subpastas
            tar.extract(member, path=tmp_path)
            extracted = tmp_path / "tectonic"

        shutil.move(str(extracted), str(dest))

    # Garante permissão de execução (owner/group/other).
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    logger.info("Tectonic instalado em %s", dest)
