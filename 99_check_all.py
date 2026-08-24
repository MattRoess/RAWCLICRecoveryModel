"""
99_check_all.py
===============

Run everything and say, in one line, whether it is all still working.

    ./.venv/bin/python 99_check_all.py

Run it after changing anything -- a coefficient, a setting, the flow network,
the code. It is the answer to "did I break something".

TWO SEPARATE QUESTIONS, ANSWERED SEPARATELY
-------------------------------------------
    THE CODE   is the model still correct?
    YOUR CASE  is the table you are editing still valid?

They are kept apart because transfer coefficients change constantly, and a
half-edited table must not look like broken code.

**The code checks never read your case.** The six suites in `tests/` run
entirely against the fixed fixtures in `data_folder/reference/`, with their own
years and their own unit pinned, so nothing you do to TCs.csv -- editing it,
emptying it, deleting it -- can make them fail. If they pass, the model is
sound whatever state your table is in.

    ./.venv/bin/python 99_check_all.py --code

runs only those, which is what you want while a coefficient table is
half-written.

The case checks then run the pipeline on the case in `src/params_schema.py`
and check that mass balance closes. Those depend on your data by definition:
they are asking whether the table is complete and consistent, not whether the
code is. A failure there names your table, not the model.

Neither section asserts any particular coefficient value. Mass balance holds
for any well-formed table -- it is a property of the coefficients summing to 1,
not of what they sum from -- so changing every number in TCs.csv leaves every
check here still meaningful.
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
    stages = [('01_check_inputs.py', ()), ('02_run_model.py', ('--quiet',)),
              ('03_run_monte_carlo.py', ())]
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


def main(argv=None) -> int:
    code_only = '--code' in (argv if argv is not None else sys.argv[1:])

    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    # ---- THE CODE -- nothing here touches your case or your coefficients ----
    print('THE CODE   (fixed fixtures; independent of your TCs.csv)')
    code = suites()
    for name, ok, tail in code:
        print(f'  {"ok  " if ok else "FAIL"}  {name:<24} {tail}')
    code_failed = [name for name, ok, _ in code if not ok]

    if code_only:
        print()
        print(f'{len(code_failed)} of {len(code)} FAILED: {", ".join(code_failed)}'
              if code_failed else f'The code is sound: all {len(code)} checks passed.')
        return 1 if code_failed else 0

    # ---- YOUR CASE -- depends on your data, and is meant to -----------------
    print(f'\nYOUR CASE  {params.run.data_folder}')
    print(f'           years {params.run.years or "all"}, {params.data.draws:,} draws, '
          f'{params.run.working_unit}, domains '
          f'{", ".join(params.data.groups) or "all"}')
    stages = pipeline(params)
    for name, ok, tail in stages:
        print(f'  {"ok  " if ok else "FAIL"}  {name:<24} {tail[:76]}')

    # Only meaningful if the run that produced the summary actually succeeded.
    # Reading it after a failed pipeline checks the PREVIOUS run's file and
    # reports "ok" for a case that did not solve at all.
    if all(ok for _, ok, _ in stages):
        ok, detail = mass_balance(params)
    else:
        ok, detail = False, 'not checked -- the pipeline did not complete'
    print(f'  {"ok  " if ok else "FAIL"}  {"mass balance":<24} {detail}')
    case = stages + [('mass balance', ok, detail)]
    case_failed = [name for name, passed, _ in case if not passed]

    print()
    if code_failed:
        print(f'THE CODE IS BROKEN: {", ".join(code_failed)}')
        if case_failed:
            print('  (the case failures below are probably a consequence)')
        return 1
    if case_failed:
        print(f'The code is sound. YOUR CASE has {len(case_failed)} problem(s): '
              f'{", ".join(case_failed)}')
        print('  Your data or coefficients, not the model. Fix the table and run again.')
        return 1
    print(f'All {len(code) + len(case)} checks passed -- code and case.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
