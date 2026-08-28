"""
tc_worklist.py
==============

Say, per sum-to-1 group, WHERE A SECOND MEASUREMENT WOULD BUY SOMETHING.

    ./.venv/bin/python tools/tc_worklist.py

Reads the TC table and nothing else -- no upstream draws, no solving -- so it
runs in a moment on any case.

WHY THIS IS A WORKLIST AND NOT A CONVERSION
-------------------------------------------
`monte_carlo.sum_to_one = 'condition'` uses every row's own range instead of
deriving one of them. That is only worth having where the extra range is an
INDEPENDENT measurement. There is no way to manufacture one from the table:

  * Clearing `is_residual` and leaving the bounds blank makes the row a point
    mass, and the group then has one degree of freedom and no slack. Every
    draw would come out identical, the whole spread gone. src/sampling.py
    refuses this outright now; this lists it before a run rather than during.

  * Filling in the range the constraint already implies -- `1 - the rest of
    the group` -- counts one measurement twice. The target becomes f(x)*f(x)
    rather than f(x), which narrows the answer by about a fifth on a typical
    row and means nothing at all.

So a group with one measurement is ALREADY RIGHT as a residual, and this lists
which groups those are rather than pretending they need fixing. It also flags
the two failures above where they have already crept in.

    ./.venv/bin/python tools/tc_worklist.py --pick     choose from a list
    ./.venv/bin/python tools/tc_worklist.py <folder>   one case
    ./.venv/bin/python tools/tc_worklist.py -l         list the cases
"""

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if os.path.basename(os.path.dirname(os.path.abspath(__file__)))
                in ('tests', 'tools')
                else os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()

import argparse

import numpy as np
import pandas as pd

from src import sampling
from src.params_schema import ParameterError, current
from src.plot_structure import choose, find_cases


FILENAME = 'tc_worklist.csv'

# How close a stated range has to sit to the one the constraint already implies
# before it is treated as the same number rather than a second opinion. The
# bounds are written to two or three decimals, so this is loose on purpose.
SAME = sampling.SAME_AS_IMPLIED

# What a group can be. Only the first is work; the rest are either fine as they
# are or already broken.
NEEDS_A_SECOND = 'one measurement, derived partner -- correct as it stands'
FULLY_MEASURED = 'measured on every row -- conditioning is doing something'
REFLECTED = 'WARNING: the extra range is what the others already imply'
COLLAPSED = 'REFUSED at run time: spreadless row and no is_residual'


# One definition, in src/sampling.py, shared with src/validate_inputs.py.
from src.sampling import implied


def classify(low, mode, high, residual, members) -> tuple[str, tuple]:
    """One group's status, and the range the constraint implies for its odd row."""
    spread = high[members] - low[members]
    marked = np.flatnonzero(residual[members]) if residual is not None else []

    if len(marked):
        position = int(marked[0])
        others = np.setdiff1d(np.arange(len(members)), position)
        return NEEDS_A_SECOND, implied(low[members], mode[members],
                                       high[members], others) + (position,)

    # What the RUN refuses, and nothing more. src/sampling.py stops a group
    # with exactly one free row -- the constraint pins it and its range is
    # discarded. A fixed row beside two or more free ones is fine, and saying
    # otherwise reported a working case as broken, which teaches a reader to
    # ignore the warning.
    free = np.flatnonzero(spread > 0)
    if len(free) == 1:
        position = int(free[0])
        others = np.setdiff1d(np.arange(len(members)), position)
        return COLLAPSED, implied(low[members], mode[members],
                                  high[members], others) + (position,)
    if len(free) == 0:
        # Every row is a single number. Nothing to sample either way.
        return FULLY_MEASURED, (np.nan, np.nan, np.nan, 0)

    # Two or more free rows. Does any one of them merely restate the others?
    for position in free:
        others = np.setdiff1d(np.arange(len(members)), position)
        want = implied(low[members], mode[members], high[members], others)
        got = (low[members][position], mode[members][position],
               high[members][position])
        if all(abs(a - b) <= SAME for a, b in zip(want, got)):
            return REFLECTED, want + (position,)
    return FULLY_MEASURED, (np.nan, np.nan, np.nan, 0)


def worklist(folder: str) -> pd.DataFrame:
    """One row per constrained group, saying what it needs."""
    from src import case_tables
    from src.sampling import (MAX_COLUMN, MIN_COLUMN, MODE_COLUMN,
                              RESIDUAL_COLUMN, constrained_groups, numeric_bounds)

    tcs = numeric_bounds(case_tables.read(folder, 'TCs'))
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        return pd.DataFrame()

    low = tcs[MIN_COLUMN].to_numpy(dtype=np.float64)
    mode = tcs[MODE_COLUMN].to_numpy(dtype=np.float64)
    high = tcs[MAX_COLUMN].to_numpy(dtype=np.float64)
    residual = (tcs[RESIDUAL_COLUMN].astype(bool).to_numpy()
                if RESIDUAL_COLUMN in tcs.columns else None)

    rows = []
    for members in constrained_groups(tcs).values():
        status, (lo, mo, hi, which) = classify(low, mode, high, residual, members)
        odd = tcs.iloc[members[which]]
        rows.append({
            'Input_FlowID': odd['Input_FlowID'],
            'Input_layer_key': odd['Input_layer_key'],
            'TC_target_key': odd['TC_target_key'],
            'rows_in_group': len(members),
            'group_flows': '; '.join(tcs.iloc[members]['Output_FlowID']),
            'row_without_its_own_measurement': odd['Output_FlowID'],
            'value': odd[MODE_COLUMN],
            'implied_min': round(lo, 6) if np.isfinite(lo) else '',
            'implied_max': round(hi, 6) if np.isfinite(hi) else '',
            'status': status,
            # Left blank on purpose. Nothing derivable from this table belongs
            # here -- only a number measured without going through the others.
            'independent_min': '',
            'independent_mode': '',
            'independent_max': '',
            'source_of_that_measurement': '',
        })
    return pd.DataFrame(rows)


def report(folder: str) -> int:
    """Print the worklist and write it beside the case's other outputs."""
    table = worklist(folder)
    print(f'\n{folder}')
    if not len(table):
        print('  No value_min / value_max columns: the table is deterministic, '
              'so no group\n  has a distribution to redistribute.')
        return 0

    counts = table['status'].value_counts()
    print(f'  {len(table)} constrained groups')
    for status in (NEEDS_A_SECOND, FULLY_MEASURED, REFLECTED, COLLAPSED):
        if status in counts:
            print(f'    {counts[status]:4d}  {status}')

    for status, heading in ((COLLAPSED, 'These are refused when the case is run'),
                            (REFLECTED, 'These count one measurement twice')):
        bad = table[table['status'] == status]
        if not len(bad):
            continue
        print(f'\n  {heading}:')
        for _, row in bad.head(10).iterrows():
            # Which row restated which cannot be told from the table -- in a
            # two-row group each range implies the other exactly -- so the
            # group is named rather than a culprit picked out of it.
            print(f"    {row['Input_FlowID']} {row['Input_layer_key']} "
                  f"{row['TC_target_key']}: {row['group_flows']}")
        if len(bad) > 10:
            print(f'    ... and {len(bad) - 10} more')
        if status == REFLECTED:
            print('    Each range in the group is what the others already '
                  'imply, so one of\n    them is not a second opinion. Which '
                  'one was measured first is not\n    recoverable from the '
                  'table -- check the `source` column.')

    out = os.path.join(folder, 'output_data', FILENAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    table.to_csv(out, index=False)
    print(f'\n  {out}')
    print('  The four blank columns are for a measurement taken WITHOUT going '
          'through the\n  rest of the group. Filling in anything derivable from '
          'this table makes the\n  answer narrower and no better founded -- '
          'see the module docstring.')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Say which sum-to-1 groups a second measurement would help.')
    parser.add_argument('folder', nargs='?',
                        help='list this case, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true',
                        help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases available, then stop')
    parser.add_argument('--all', action='store_true',
                        help='every case that has a TC table')
    args = parser.parse_args(argv)

    if args.list:
        print('Cases available:')
        for case in find_cases():
            print(f'  {case}')
        return 0

    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    if args.all:
        from src import case_tables
        for case in find_cases():
            if case_tables.exists(case, 'TCs'):
                report(case)
        return 0

    folder = args.folder or (choose() if args.pick else params.run.data_folder)
    if not os.path.isdir(folder):
        print(f"There is no case folder called '{folder}'.", file=sys.stderr)
        return 1
    return report(folder)


if __name__ == '__main__':
    raise SystemExit(main())
