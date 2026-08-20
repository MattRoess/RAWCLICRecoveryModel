"""
99_check_all.py
===============

Run everything and say, in one line, whether it is all still working.

    ./.venv/bin/python 99_check_all.py

Run it after changing anything -- a coefficient, a setting, the flow network,
the code. It is the answer to "did I break something".

WHAT IT RUNS
------------
1. The five test suites in `tests/`. These pin behaviour that must not move:
   the deterministic answer, the sampler against the mathematics, the Monte
   Carlo against the deterministic model, unit conversion, and the handling of
   incomplete composition.

2. The pipeline itself, on the case in `src/params_schema.py`, exactly as you
   would run it. A suite can pass while the actual thing is broken -- the tests
   use the reference cases, and the real case has its own data, settings and
   coefficients.

3. Mass balance on the result: what enters must equal what leaves, in every
   year. That is the one check that says the numbers mean something rather
   than merely that nothing raised.

Nothing here writes to the repository except the figures and output files the
stages write anyway.
"""

from __future__ import annotations

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()

import glob
import subprocess

import numpy as np
import pandas as pd

from src.params_schema import ParameterError, current

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, '.venv', 'bin', 'python')
LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']


def run(label: str, script: str, *args) -> tuple[bool, str]:
    """Run one script, returning whether it succeeded and its last useful line."""
    result = subprocess.run([PYTHON, os.path.join(ROOT, script), *args],
                            capture_output=True, text=True, cwd=ROOT)
    # On failure the useful line is the error, not the last thing printed before
    # it. Reporting stdout for a failed stage showed a cheerful progress message
    # next to the word FAIL.
    stream = result.stdout if result.returncode == 0 else (result.stderr or result.stdout)
    lines = [line for line in stream.strip().split('\n') if line.strip()]
    return result.returncode == 0, lines[-1] if lines else '(no output)' 


def suites() -> list[tuple[str, bool, str]]:
    """Every test suite, in a fixed order so the output is comparable run to run."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'tests', 'test_*.py'))):
        name = os.path.basename(path)
        ok, tail = run(name, os.path.join('tests', name))
        out.append((name, ok, tail))
    return out


def pipeline(params) -> list[tuple[str, bool, str]]:
    """The stages, run on the real case exactly as a person would run them."""
    stages = [('02_check_inputs.py', ()), ('03_run_model.py', ('--quiet',)),
              ('04_run_monte_carlo.py', ())]
    out = []
    for script, args in stages:
        ok, tail = run(script, script, *args)
        out.append((script, ok, tail))
        if not ok:
            break                       # a later stage cannot mean anything
    return out


def mass_balance(params) -> tuple[bool, str]:
    """
    What enters must equal what leaves, in every year.

    Read from the Monte Carlo summary rather than recomputed, so this checks the
    file that would actually be reported from. Totals are taken at each flow's
    own shallowest depth: rows are nested, so summing every depth counts the
    same mass several times (MODEL_MECHANICS.md section 1).
    """
    path = os.path.join(params.run.data_folder, 'output_data', 'monte_carlo_summary.csv')
    if not os.path.exists(path):
        return False, f'{path} was not written'

    summary = pd.read_csv(path, keep_default_na=False, na_values=[])
    summary['mean'] = pd.to_numeric(summary['mean'])
    summary['depth'] = (summary[LAYERS] != '').sum(axis=1)

    tcs = pd.read_csv(os.path.join(params.run.data_folder, 'input_data', 'TCs.csv'),
                      keep_default_na=False, na_values=[])
    sources = set(tcs['Input_FlowID'])
    terminals = set(tcs['Output_FlowID']) - sources
    starts = sources - set(tcs['Output_FlowID'])

    def total(frame, flows):
        chosen = frame[frame['Stock/Flow ID'].isin(flows)]
        if chosen.empty:
            return 0.0
        return sum(group[group['depth'] == group['depth'].min()]['mean'].sum()
                   for _, group in chosen.groupby('Stock/Flow ID'))

    worst, years = 0.0, 0
    for _, group in summary.groupby('Year'):
        entering, leaving = total(group, starts), total(group, terminals)
        if entering > 0:
            worst = max(worst, abs(entering - leaving) / entering)
        years += 1

    ok = worst < 1e-9
    return ok, (f'{years} year(s), worst relative residual {worst:.2e}'
                + ('' if ok else '  -- MASS IS NOT CONSERVED'))


def main() -> int:
    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    print(f'Case   : {params.run.data_folder}')
    print(f'Years  : {params.run.years or "all"}    '
          f'Draws: {params.data.draws:,}    Unit: {params.run.working_unit}')

    print('\nTest suites')
    results = suites()
    for name, ok, tail in results:
        print(f'  {"ok  " if ok else "FAIL"}  {name:<24} {tail}')

    print('\nPipeline, on the real case')
    stage_results = pipeline(params)
    for name, ok, tail in stage_results:
        print(f'  {"ok  " if ok else "FAIL"}  {name:<24} {tail[:78]}')
    results += stage_results

    print('\nMass balance')
    # Only meaningful if the run that produced the summary actually succeeded.
    # Reading it after a failed pipeline checks the PREVIOUS run's file and
    # reports "ok" for a case that did not solve at all.
    if all(passed for _, passed, _ in stage_results):
        ok, detail = mass_balance(params)
    else:
        ok, detail = False, 'not checked -- the pipeline did not complete'

    print(f'  {"ok  " if ok else "FAIL"}  {"in == out":<24} {detail}')
    results.append(('mass balance', ok, detail))

    failed = [name for name, passed, _ in results if not passed]
    print()
    if failed:
        print(f'{len(failed)} of {len(results)} FAILED: {", ".join(failed)}')
        return 1
    print(f'All {len(results)} checks passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
