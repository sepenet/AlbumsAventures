"""Shim minimal du module POSIX `fcntl` pour Windows.

Contexte : `tuspyserver` (utilisé pour les uploads TUS resumable côté backend)
importe `fcntl` au niveau module (`tuspyserver/lock.py`). Sur Windows ce module
n'existe pas, ce qui empêche le simple lancement de l'app en dev.

Ce shim fournit des constantes et une fonction `flock()` no-op. Le verrouillage
de fichier n'a donc PAS d'effet réel sur Windows — c'est acceptable uniquement
pour le développement local (un seul utilisateur, un seul worker uvicorn).
En production Linux, le vrai `fcntl` est utilisé et les verrous fonctionnent.

À appeler AVANT tout import de `tuspyserver`, idéalement au tout début du
point d'entrée de l'application.
"""

from __future__ import annotations

import os
import sys


def install_if_windows() -> None:
    """Installe un faux module `fcntl` dans `sys.modules` si on est sur Windows."""
    if os.name != "nt":
        return
    if "fcntl" in sys.modules:
        return

    import types

    fcntl_stub = types.ModuleType("fcntl")
    # Constantes POSIX, valeurs identiques à <sys/file.h>
    fcntl_stub.LOCK_SH = 1  # type: ignore[attr-defined]
    fcntl_stub.LOCK_EX = 2  # type: ignore[attr-defined]
    fcntl_stub.LOCK_NB = 4  # type: ignore[attr-defined]
    fcntl_stub.LOCK_UN = 8  # type: ignore[attr-defined]

    def _flock(_fd, _operation):  # noqa: ANN001 - signature POSIX
        """Verrou no-op (Windows dev uniquement)."""
        return None

    def _fcntl(_fd, _cmd, _arg=0):  # noqa: ANN001
        return 0

    def _ioctl(_fd, _request, _arg=0, _mutate_flag=True):  # noqa: ANN001
        return 0

    fcntl_stub.flock = _flock  # type: ignore[attr-defined]
    fcntl_stub.fcntl = _fcntl  # type: ignore[attr-defined]
    fcntl_stub.ioctl = _ioctl  # type: ignore[attr-defined]

    sys.modules["fcntl"] = fcntl_stub


def patch_tuspyserver_for_windows() -> None:
    """Corrige `tuspyserver.info.UploadInfo.serialize` sur Windows.

    Le code amont fait `os.rename(tmp, dest)` qui échoue sur Windows si la
    destination existe déjà (chaque chunk PATCH réécrit le fichier `.info`).
    On remplace par `os.replace`, équivalent cross-platform et atomique sur
    NTFS.

    À appeler après l'import de `tuspyserver` (et donc après l'app FastAPI),
    et uniquement sur Windows.
    """
    if os.name != "nt":
        return

    try:
        from tuspyserver import info as _tus_info  # type: ignore
    except ImportError:
        return

    import json as _json

    def _serialize(self):  # noqa: ANN001
        temp_path = f"{self.path}.tmp"
        try:
            with open(temp_path, "w") as f:
                f.write(_json.dumps(self._params, indent=4, default=lambda k: k.__dict__))
                f.flush()
                os.fsync(f.fileno())
            # os.replace : atomique cross-platform, écrase la destination existante
            os.replace(temp_path, self.path)
        except Exception:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            raise

    _tus_info.TusUploadInfo.serialize = _serialize  # type: ignore[assignment]
