"""
filling_sheet.py
================

The coefficients still waiting for a real number, HARDEST-HITTING FIRST.

    ./.venv/bin/python tools/filling_sheet.py

Every transfer coefficient in this project is a placeholder, and there are 378
of them across the two cases. Working through that alphabetically wastes most
of the effort: a handful of rows carry most of the answer's spread and the rest
barely move it. This ranks them, so the first afternoon of literature work is
spent on the rows that matter.

HOW THE RANKING IS MADE
-----------------------
One Monte Carlo run, then two numbers per coefficient.

**`spread_share`** is what the ranking uses: the fraction of the answer's
variance that this one coefficient accounts for, and so the fraction that would
disappear if it were measured exactly. That is the question a measurement
answers. `cumulative` says what the rows above it come to, so it is easy to see
where the list stops being worth working down.

**`influence`** is the Spearman rank correlation with the total -- the measure
the `sensitivity` figure uses. It says how closely the coefficient TRACKS the
answer, which is a different question. A row can score high on influence and
low on share: it matters, but its range is already tight enough that pinning it
down buys little. Seeing both is the point of keeping the second column.

WHAT IT DOES NOT DO
-------------------
It writes no numbers into the case. The sheet is a reading list, and the place
to type a measurement is still the `TCs` sheet of `case.xlsx`, which has the
dropdowns and the checks. Two files holding coefficients is how they drift.

    ./.venv/bin/python tools/filling_sheet.py --pick     choose from a list
    ./.venv/bin/python tools/filling_sheet.py <folder>   one case
    ./.venv/bin/python tools/filling_sheet.py -l         list the cases
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

from src.params_schema import ParameterError, current
from src.plot_structure import choose, find_cases


FILENAME = 'filling_sheet.csv'

# What a `source` starts with when the number in that row was invented rather
# than measured. `derived:` rows are arithmetic on their neighbours, so they
# are not sourced separately -- they follow whatever those rows become.
INVENTED = ('PLACEHOLDER', 'MADE UP')

# Where the list stops being worth working down, as a share of total influence.
WORTH_IT = 0.80

# How many rows to print. The car composition case needs 88 rows to reach 80%,
# which is a useful thing to know and an unreadable thing to print.
PRINTED = 15


def tidy(value) -> str:
    """A bound as a person would write it, without the float noise."""
    try:
        return f'{round(float(value), 6):g}'
    except (TypeError, ValueError):
        return str(value)


def total_recovered(run, folder: str) -> np.ndarray:
    """Recovered mass per draw: element-depth rows of the recovered flows."""
    from src.plot_monte_carlo import recovered_flows, totals_by_flow_and_element

    recovered = set(recovered_flows(run, folder))
    per_pair = totals_by_flow_and_element(run)
    chosen = [values for (flow, _), values in per_pair.items() if flow in recovered]
    if not chosen:
        return np.zeros(run.values.shape[1])
    return np.sum(chosen, axis=0)


def influence(run, target: np.ndarray) -> np.ndarray:
    """
    |Spearman| between each coefficient and the target, one per TC row.

    The target is ranked once and each coefficient ranked in turn, then
    correlated linearly -- which is what Spearman is, and is far quicker than
    asking for the full statistic 632 times.
    """
    from scipy.stats import rankdata

    ranked_target = rankdata(target)
    ranked_target = ranked_target - ranked_target.mean()
    target_norm = np.sqrt(np.sum(ranked_target ** 2))

    out = np.zeros(len(run.tcs))
    if target_norm == 0 or run.tc_values is None:
        return out

    for position in range(len(run.tcs)):
        coefficient = run.tc_values[position]
        if coefficient.std() == 0:
            continue          # no spread, so nothing to correlate
        ranked = rankdata(coefficient)
        ranked = ranked - ranked.mean()
        norm = np.sqrt(np.sum(ranked ** 2))
        if norm > 0:
            out[position] = abs(float(np.dot(ranked, ranked_target)
                                      / (norm * target_norm)))
    return out


# What identifies one coefficient, for looking its `source` back up.
#
# The layer columns are deliberately NOT in here. The engine rewrites them --
# 'element' becomes 'Layer 4', 'component' becomes 'Layer 2' -- so a key that
# included them matched nothing and the sheet came back empty. These four are
# unique in both tables, checked on both cases.
IDENTITY = ['Input_FlowID', 'Input_layer_key', 'Output_FlowID', 'TC_target_key']


def sources_for(folder: str, resolved: pd.DataFrame) -> list[str]:
    """
    Each resolved row's `source`, taken from the case's own TC table.

    The engine drops the column on its way through -- it is documentation, not
    arithmetic -- and the resolved table can hold rows the written one does not,
    since wildcards expand and `rest` rows are derived. So this looks each row
    up by identity rather than assuming the two line up, and a row that was
    never written by hand comes back blank, which is the truth about it.
    """
    from src import case_tables

    written = case_tables.read(folder, 'TCs')
    if 'source' not in written.columns:
        return [''] * len(resolved)

    known: dict[tuple, str] = {}
    for _, row in written.iterrows():
        key = tuple(str(row.get(column, '')).strip() for column in IDENTITY)
        known.setdefault(key, str(row['source']).strip())

    return [known.get(tuple(str(row.get(column, '')).strip()
                            for column in IDENTITY), '')
            for _, row in resolved.iterrows()]


def spread_shares(run, target: np.ndarray) -> np.ndarray:
    """
    Per coefficient, the share of the result's spread it accounts for.

    `influence` says how closely a coefficient tracks the answer. This says
    what pinning it down would BUY -- the fraction of the variance that
    disappears if it were known exactly. They are different questions, and the
    second is the one a measurement answers: a coefficient can track the answer
    almost perfectly and still be worth nothing to measure, because its range
    is already narrow enough not to matter.
    """
    from src.sampling import variance_share

    out = np.zeros(len(run.tcs))
    if run.tc_values is None:
        return out
    for position in range(len(run.tcs)):
        out[position] = variance_share(run.tc_values[position], target)
    return out


def sheet(folder: str, params) -> pd.DataFrame:
    """The rows still waiting for a number, ranked by how much they matter."""
    from src.model_run import LAYER_NAMES
    from src.monte_carlo import solve_draws
    from src.sampling import MAX_COLUMN, MIN_COLUMN, MODE_COLUMN
    from src.upstream import load as refresh
    from src import source as source_module

    draws = (source_module.read(folder, params)['draws']
             if source_module.exists(folder) else params.data.draws)
    tables = refresh(params, folder, quiet=True)
    run = solve_draws(folder, LAYER_NAMES, draws=draws,
                      seed=params.monte_carlo.seed, tables=tables,
                      chunk=params.monte_carlo.chunk,
                      budget_gb=params.monte_carlo.memory_budget_gb,
                      rule=params.monte_carlo.sum_to_one)

    # The resolved table does not carry a 0-based index -- it has been through
    # wildcard expansion and rest derivation -- so everything here is done by
    # position, and the mask is taken out to numpy before it indexes anything.
    target = total_recovered(run, folder)
    tcs = run.tcs.reset_index(drop=True).copy()
    tcs['influence'] = influence(run, target)
    tcs['spread_share'] = spread_shares(run, target)
    tcs['source'] = sources_for(folder, tcs)

    source = tcs['source'].astype(str).str.strip()
    waiting = tcs[source.str.startswith(INVENTED).to_numpy()].copy()
    # Ranked by what a measurement BUYS, not by how closely the coefficient
    # tracks the answer. See spread_shares for why those differ.
    waiting = waiting.sort_values('spread_share', ascending=False).reset_index(drop=True)

    total = waiting['spread_share'].sum()
    waiting['cumulative'] = (waiting['spread_share'].cumsum() / total
                             if total > 0 else 0.0)

    out = pd.DataFrame({
        'rank': np.arange(1, len(waiting) + 1),
        # How much of the answer's spread this one coefficient accounts for --
        # what would go away if it were measured exactly.
        'spread_share': waiting['spread_share'].round(4),
        'cumulative': waiting['cumulative'].round(4),
        # How closely it tracks the answer. Kept because a high influence with
        # a low share means the coefficient matters but its range is already
        # tight enough, which is worth seeing rather than inferring.
        'influence': waiting['influence'].round(4),
        'Input_FlowID': waiting['Input_FlowID'],
        'Input_layer_key': waiting['Input_layer_key'],
        'Output_FlowID': waiting['Output_FlowID'],
        'TC_target_key': waiting['TC_target_key'],
        'process': waiting.get('process', ''),
        'technology': waiting.get('technology', ''),
        # Rounded: capping the maxima upstream leaves values like
        # 0.6499999999999999, which is noise in a sheet meant to be read.
        'guessed_value': waiting[MODE_COLUMN].map(tidy),
        'guessed_min': waiting[MIN_COLUMN].map(tidy),
        'guessed_max': waiting[MAX_COLUMN].map(tidy),
        'why_it_was_guessed': waiting['source'],
        # Yours. Type the numbers into the TCs sheet of case.xlsx; these are
        # here so the reading and the typing can happen at different times.
        'measured_value': '',
        'measured_min': '',
        'measured_max': '',
        'citation': '',
    })
    return out


def report(folder: str, params) -> int:
    """Print the head of the sheet and write the whole of it."""
    table = sheet(folder, params)
    print(f'\n{folder}')
    if not len(table):
        print('  No rows are marked as guesses. Either every coefficient has '
              'been measured,\n  or the `source` column does not say which '
              'were invented.')
        return 0

    enough = int((table['cumulative'] <= WORTH_IT).sum()) + 1
    enough = min(enough, len(table))
    print(f'  {len(table)} coefficients still waiting for a real number')
    print(f'  the first {enough} carry {WORTH_IT:.0%} of the spread in total '
          f'recovered mass')
    print(f'  measuring all {len(table)} exactly would remove '
          f'{table["spread_share"].sum():.0%} of that spread')

    shown = min(enough, PRINTED)
    print(f"\n  {'#':>3} {'share':>6} {'cum':>6} {'infl':>6}  "
          f"{'coefficient':<52} guess")
    for _, row in table.head(shown).iterrows():
        name = (f"{row['Input_layer_key']}/{row['TC_target_key']} "
                f"{row['Input_FlowID']} -> {row['Output_FlowID']}")
        guess = (f"{tidy(row['guessed_min'])}-{tidy(row['guessed_value'])}"
                 f"-{tidy(row['guessed_max'])}")
        print(f"  {row['rank']:>3} {row['spread_share']:>6.1%} "
              f"{row['cumulative']:>6.1%} {row['influence']:>6.3f}  "
              f"{name[:52]:<52} {guess}")
    if enough > shown:
        print(f'  ... to row {enough} for the first {WORTH_IT:.0%}; '
              f'the file has all of them')
    if len(table) > enough:
        print(f'  the remaining {len(table) - enough} are together worth '
              f'{1 - table.iloc[enough - 1]["cumulative"]:.0%}')

    out = os.path.join(folder, 'output_data', FILENAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    table.to_csv(out, index=False)
    print(f'\n  {out}')
    print('  Type the numbers into the TCs sheet of case.xlsx, not into this '
          'file: it is\n  rewritten on every run, and two files holding '
          'coefficients is how they drift.')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Rank the coefficients still waiting for a measurement.')
    parser.add_argument('folder', nargs='?',
                        help='use this case, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true',
                        help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases available, then stop')
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

    folder = args.folder or (choose() if args.pick else params.run.data_folder)
    if not os.path.isdir(folder):
        print(f"There is no case folder called '{folder}'.", file=sys.stderr)
        return 1

    from src.monte_carlo import MemoryBudgetExceeded
    from src.sampling import SamplingError
    from src.upstream import UpstreamError
    from src.validate_inputs import InputDataError

    try:
        return report(folder, params)
    except (InputDataError, UpstreamError, MemoryBudgetExceeded,
            SamplingError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
