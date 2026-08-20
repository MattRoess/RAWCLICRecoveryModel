"""
src/bootstrap.py
================

Make every script run under the project's own interpreter, whatever was typed.

WHY
---
The dependencies live in `.venv`. Run a script with any other Python -- the
pyenv one, the system one, whatever Positron happens to have selected -- and it
fails on the first third-party import:

    ModuleNotFoundError: No module named 'matplotlib'

which says nothing about the actual problem. That has bitten repeatedly, and
telling someone to type a longer command is not a fix: the same mistake is
available every single time.

So each entry script calls `ensure_venv()` before importing anything that
matters. If the current interpreter is not the project's, it re-executes the
same command under the right one. `python x.py`, `python3 x.py`, an absolute
path to some other interpreter, or a Run button in an editor all end up in the
same place.

This module imports nothing but the standard library, on purpose: it has to be
able to run under the *wrong* interpreter, which by definition cannot import
anything else.
"""
from __future__ import annotations

import os
import sys

# Set on the re-executed process so a broken venv cannot cause a loop.
GUARD = 'RECOVERY_MODEL_BOOTSTRAPPED'


def project_root() -> str:
    """The repository root, from this file's location."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def venv_python() -> str:
    """Where the project interpreter should be."""
    return os.path.join(project_root(), '.venv', 'bin', 'python')


def ensure_venv() -> None:
    """
    Re-execute under the project interpreter if this is not already it.

    Returns normally when nothing needs doing -- either because the right
    interpreter is already running, or because there is no venv to switch to,
    in which case the caller fails later with its own message rather than
    being silently redirected somewhere worse.
    """
    # Always make the repo root importable, however the script was invoked.
    root = project_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    if os.environ.get(GUARD):
        return

    target = venv_python()
    if not os.path.exists(target):
        print(f'No interpreter at {target}.\n'
              f'Create it with:\n'
              f'  python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt',
              file=sys.stderr)
        return

    if os.path.realpath(sys.executable) == os.path.realpath(target):
        return

    os.environ[GUARD] = '1'
    os.execv(target, [target, *sys.argv])
