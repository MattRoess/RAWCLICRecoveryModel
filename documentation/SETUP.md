# Setting up on a new machine

Written for picking this up on a different Mac. **No conda** — this project
uses a plain virtual environment and a pinned `requirements.txt`.

Verified end to end from a clean clone on 2026-08-14.

## 1. Python 3.14

Check what is there:

```bash
python3 -V
```

If it is not 3.14.x, install it — any of these, none involving conda:

- **python.org installer** (simplest on a fresh Mac): download the macOS
  installer for 3.14 from python.org and run it. It installs to
  `/Library/Frameworks/Python.framework/Versions/3.14/`.
- **pyenv**, if already installed: `pyenv install 3.14.2`
- **Homebrew**: `brew install python@3.14`

The environment is verified on **3.14.2**. If only 3.13 is available the pins
will most likely still resolve, but that combination is untested — step 5 will
tell you immediately either way.

## 2. Clone

```bash
git clone https://github.com/MattRoess/RAWCLICRecoveryModel.git
cd RAWCLICRecoveryModel
```

The repo is private, so the machine needs GitHub access — either `gh auth login`
or an SSH key already registered.

## 3. Create the environment

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

If `python3` is not 3.14, point at the interpreter directly, for example:

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv .venv
```

`.venv/` is gitignored and is meant to be rebuilt per machine. Never commit it.

## 4. Positron

1. **Open the folder** `RAWCLICRecoveryModel` (not a parent directory — the
   committed `.vscode/settings.json` only applies to this workspace root).
2. **Select the interpreter**: Command Palette (`Cmd+Shift+P`) →
   `Python: Select Interpreter` → pick the one at `./.venv/bin/python` inside
   the project.
3. **Open a new terminal.** The prompt should show `(.venv)`.

The committed settings handle the rest: `.venv` is the default interpreter,
terminals activate it automatically, the console and notebooks run from the
project root, and `import src.recovery_model_optimized` resolves for the
language server.

### If the prompt shows something other than `(.venv)`

This happened on the original machine: the prompt read `(3.14.4)` because
Positron had a **pyenv** interpreter selected, and a stored workspace selection
beats `python.defaultInterpreterPath`. That environment had pandas but no
scipy, so the model would have crashed on import.

Fix it by redoing step 4.2. To confirm which interpreter a terminal is actually
using:

```bash
which python && python -V && python -c "import scipy; print('scipy', scipy.__version__)"
```

It must print a path inside the project's `.venv`. As a one-off override for
the current terminal only:

```bash
source .venv/bin/activate
```

## 5. Verify

```bash
./.venv/bin/python compare_engines.py data_folder/basic_test
```

Expected: 180 rows and `Engines agree`, with a largest difference on the order
of 1e-15. That figure moves slightly between runs, which is expected and
understood (DEFECTS.md §3.5).

Then the rest, all of which should run clean:

```bash
./.venv/bin/python run_model.py
./.venv/bin/python check_mass_balance.py data_folder/template
./.venv/bin/python plot_structure.py data_folder/template
./.venv/bin/python plot_flows.py data_folder/template
```

Once the interpreter is selected in Positron, `./.venv/bin/python` can be
shortened to `python` in its terminals.

## 6. Why the versions are pinned

Not caution for its own sake. A pandas copy-on-write change turned a `fillna`
call into a silent no-op and inflated this model's intermediates 300,000-fold
**without changing its output** (DEFECTS.md §1.3). Unpinned, that class of
failure recurs invisibly.

Do not relax the pins without running step 5 afterwards.
