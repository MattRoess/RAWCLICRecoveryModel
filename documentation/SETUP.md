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
It is also not relocatable — moving the project folder breaks it, see the second
troubleshooting note under step 4.

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

### If the prompt shows `(.venv)` but `python` is not found

The venv is not relocatable. A venv records the absolute path it was created at
in `.venv/pyvenv.cfg` and hardcodes it into `.venv/bin/activate`, so **moving
the project folder breaks it.** Activation then exports a `VIRTUAL_ENV` that no
longer exists, prepends a dead directory to `PATH`, and still prints `(.venv)`
in the prompt. macOS has no system `python`, so the symptom is:

```
(.venv) % which python
python not found
```

This happened on 2026-08-17: the venv had been created while the project sat in
`~/Documents/GitHub/`, and the folder was later moved into iCloud Drive. Note
that `./.venv/bin/python` keeps working throughout — Python resolves its own
prefix from the executable's location — so the scripts in step 5 all pass while
the bare `python` name stays broken. Checking only those hides the problem.

Confirm the diagnosis by comparing the recorded path against the real one:

```bash
grep "^command" .venv/pyvenv.cfg && pwd
```

The fix is to rebuild, which takes about a minute:

```bash
rm -rf .venv && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

Nothing is lost — everything in `.venv/` is reproducible from
`requirements.txt`. Afterwards, close any terminal that was open before the
rebuild: it still holds the stale `VIRTUAL_ENV` in its own environment.

## 5. The settings

Everything the model reads — which case, which engine, which figures, which
file formats — is in **`src/params_schema.py`**. Each value has a plain comment
above it explaining what it does and whether it is safe to change.

To see what is currently set, without opening the file:

```bash
./.venv/bin/python 00_parameters.py --check
```

After changing a value, run this so the written record matches the code:

```bash
./.venv/bin/python 00_parameters.py
```

That rewrites `params.xlsx` and PARAMETER_REFERENCE.md. Both are **reports**:
nothing reads them, so editing either changes nothing about how the model runs.
The file to edit is always `src/params_schema.py`.

## 6. Verify

```bash
./.venv/bin/python tools/compare_engines.py data_folder/reference/basic_test
```

Expected: 180 rows and `Engines agree`, with a largest difference on the order
of 1e-15. That figure moves slightly between runs, which is expected and
understood (DEFECTS.md §3.5).

Then the regression test, which pins the deterministic answer:

```bash
./.venv/bin/python test_regression.py
```

Expected: `6 of 6 passed`.

Then the workflow itself, all of which should run clean:

```bash
./.venv/bin/python 04_run_model.py
./.venv/bin/python 03_check_inputs.py data_folder/reference/template
./.venv/bin/python tools/plot_structure.py data_folder/reference/template
```

Once the interpreter is selected in Positron, `./.venv/bin/python` can be
shortened to `python` in its terminals.

## 7. Why the versions are pinned

Not caution for its own sake. A pandas copy-on-write change turned a `fillna`
call into a silent no-op and inflated this model's intermediates 300,000-fold
**without changing its output** (DEFECTS.md §1.3). Unpinned, that class of
failure recurs invisibly.

Do not relax the pins without running step 6 afterwards.
