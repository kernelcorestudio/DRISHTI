"""Pickle compatibility for learners exported on a different Python / OS.

Stage 2 is exported from Kaggle (Python 3.13, Linux) but loaded on the operator's machine,
which is Windows + Python 3.11 here. Two properties of the archive break that jump:

    * Python 3.13 pickles `Path` as `pathlib._local.Path`. Older interpreters have no such
      module, so `unpickler.find_class` raises
      `ModuleNotFoundError: No module named 'pathlib._local'`.
    * The exporter ran on Linux, so every stored path is a `PosixPath`. Instantiating one
      on Windows raises `NotImplementedError: cannot instantiate 'PosixPath'`.

`ensure_pickle_compatibility()` registers a `pathlib._local` alias built from the local
`pathlib` and rebinds the Posix classes to their Windows counterparts, which is enough for
`load_learner` to rebuild the archive. Call it before importing fastai; it is a no-op on
Python 3.13+ and on Linux.
"""

import pathlib
import sys
import types


def ensure_pickle_compatibility() -> None:
    if "pathlib._local" in sys.modules:
        return

    shim = types.ModuleType("pathlib._local")
    for name in dir(pathlib):
        setattr(shim, name, getattr(pathlib, name))

    if sys.platform == "win32":
        # Paths stored by the Linux exporter are Posix ones; keep the values, change the class.
        shim.PosixPath = pathlib.WindowsPath
        shim.PurePosixPath = pathlib.PureWindowsPath

    sys.modules["pathlib._local"] = shim
    setattr(pathlib, "_local", shim)
