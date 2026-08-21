"""
RUN.py
======

**Open this file in Positron and press Run.**

No terminal, no arguments, no commands to remember. Everything a run produces --
the deterministic answer, the Monte Carlo, the workbook and every figure -- comes
out of pressing Run on this file.

WHICH PIPELINE RUNS
-------------------
`run.data_folder` in `src/params_schema.py`:

    'data_folder/bev_electronics'         04_02  electronics in BEVs,
                                                 resolved to ELEMENTS
    'data_folder/carcomposition_mockup'   04_01  whole cars, five drivetrains,
                                                 resolved to MATERIALS

**One at a time.** They are different studies -- different networks, different
coefficients, different layers -- and a result is reported for one of them,
never for both together. Change the setting, press Run again.

There is nothing to change in THIS file. Everything -- the case, the years, the
scenario, the working unit, the memory budget -- is in `src/params_schema.py`,
which is also just a file you open and edit.

WHAT COMES OUT, AND WHERE
-------------------------
    data_folder/<case>/output_data/
        recovery_results.xlsx        <-- open this one, start at Mass balance
        monte_carlo_summary.csv      every result row, every percentile
        solution_optimized_model.csv the deterministic answer

    figures/<case>/
        structure.png    the flow network and its coefficients
        total.png        the Sankey
        distribution.png recovered mass across draws
        pdf_<x>.png      the distribution, one panel per year
        spread.png       the widest intervals
        ... and the rest

A folder per case, with the same names in each, so the two pipelines cannot
overwrite each other and their figures compare directly.

HOW LONG
--------
A few minutes. The Monte Carlo is the slow part, and how slow depends on
`run.years` and on the case's own draw count.
"""
from __future__ import annotations

import os
import sys

# Run under the project's own interpreter whatever Positron was started with,
# and put the repo root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()

import importlib.util
import time

from src.params_schema import ParameterError, current

# The test suites, before the run. They take about a minute, run on fixed
# fixtures, and are what tells you the code still does what it did. Set to
# False only when you are re-running the same case and nothing has changed.
CHECK = True

ROOT = os.path.dirname(os.path.abspath(__file__))


def _script(name: str):
    """Load one of the numbered scripts. They start with a digit, so no import."""
    spec = importlib.util.spec_from_file_location(
        name.replace('.py', ''), os.path.join(ROOT, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _banner(text: str) -> None:
    print(f'\n{"=" * 74}\n{text}\n{"=" * 74}')


def _cases() -> list[str]:
    """Every folder that looks like a case, for an error message worth reading."""
    root = os.path.join(ROOT, 'data_folder')
    if not os.path.isdir(root):
        return []
    return sorted(f'data_folder/{name}' for name in os.listdir(root)
                  if os.path.isdir(os.path.join(root, name, 'input_data')))


def main() -> int:
    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    folder = params.run.data_folder
    if not os.path.isdir(folder):
        print(f"run.data_folder is {folder!r}, which does not exist.\n"
              f"Set it in src/params_schema.py to one of:", file=sys.stderr)
        for case in _cases():
            print(f'    {case}', file=sys.stderr)
        return 1

    if CHECK:
        _banner('Checking the code')
        # --code only: the suites, on fixed fixtures. The rest of 99_check_all
        # runs the pipeline, which is what this file is about to do anyway.
        if _script('99_check_all.py').main(['--code']) != 0:
            print('\nThe code checks did not pass. Nothing was run.', file=sys.stderr)
            return 1

    _banner(f'{os.path.basename(folder)}   ({params.run.scenario or "BAU"}, '
            f'years {params.run.years or "all"}, {params.run.working_unit})')
    started = time.time()

    # The deterministic answer and the flow diagrams. Both engines validate the
    # inputs themselves, so there is no separate checking step to remember.
    if _script('02_run_model.py').main([folder, '--quiet']) != 0:
        return 1

    # The Monte Carlo, the workbook and the distribution figures.
    if _script('03_run_monte_carlo.py').main([folder]) != 0:
        return 1

    case = os.path.basename(folder)
    _banner('Done')
    print(f'  {case} finished in {time.time() - started:,.0f}s\n')
    print(f'  results  {folder}/output_data/recovery_results.xlsx')
    print(f'  figures  figures/{case}/\n')
    print(f'  Open the workbook and start with the Mass balance sheet.')
    print(f'\n  To run the other pipeline, change run.data_folder in')
    print(f'  src/params_schema.py and press Run again.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
