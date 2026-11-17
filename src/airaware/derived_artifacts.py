"""Publicación local de artefactos derivados y comprobación de sus sumas."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from hashlib import file_digest
from pathlib import Path
from tempfile import TemporaryDirectory


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


@contextmanager
def new_bundle(target: Path) -> Generator[Path]:
    """Preparar una carpeta fuera de la ruta final y publicarla cuando esté completa."""
    if target.exists():
        raise FileExistsError(f"La carpeta de salida ya existe: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent, prefix=".airaware-") as tmp:
        staging = Path(tmp) / "bundle"
        staging.mkdir()
        yield staging
        if target.exists():
            raise FileExistsError(f"La carpeta de salida ya existe: {target}")
        os.rename(staging, target)
