"""
compare_sum_rules.py
====================

Show WHICH RESULTS DEPEND ON THE SUM-TO-1 RULE, and by how much.

    ./.venv/bin/python tools/compare_sum_rules.py

NOT a numbered step, and it writes no result. It solves the case twice --
once conditioning, once normalising -- and puts the two answers side by side,
so that `monte_carlo.sum_to_one` can be chosen on this case's own numbers
rather than on the argument for it.

Only a group with no `is_residual` row can differ between the two. A group that
names a residual is settled by that row either way, and a group whose rows are
all single numbers has no spread to redistribute. If a case has neither kind,
this says so and stops rather than drawing two identical curves and letting you
conclude the rule does not matter.

Solving twice is the whole cost: about twice one `03_run_monte_carlo.py`.

    ./.venv/bin/python tools/compare_sum_rules.py --pick     choose from a list
    ./.venv/bin/python tools/compare_sum_rules.py <folder>   compare one case
    ./.venv/bin/python tools/compare_sum_rules.py -l         list the cases
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

from src import figure_style
from src.params_schema import ParameterError, current
from src.plot_structure import choose, find_cases


# The two rules, in the order they are drawn, with a colour each. Conditioning
# first because it is the default and the one the case is presumed to use.
RULES = ('condition', 'normalise')
COLOURS = {'condition': '#2E6F9E', 'normalise': '#7A7A7A'}

# Below this the two answers are the same number twice, and naming the element
# would suggest a difference that is only the last bit of a float.
MEANINGFUL = 1e-9


def solve_once(folder: str, params, rule: str):
    """One full Monte Carlo run of `folder` under one sum-to-1 rule."""
    from src.model_run import LAYER_NAMES
    from src.monte_carlo import solve_draws
    from src.upstream import load as refresh
    from src import source as source_module

    draws = (source_module.read(folder, params)['draws']
             if source_module.exists(folder) else params.data.draws)
    tables = refresh(params, folder, quiet=True)
    return solve_draws(folder, LAYER_NAMES, draws=draws,
                       seed=params.monte_carlo.seed, tables=tables,
                       chunk=params.monte_carlo.chunk,
                       budget_gb=params.monte_carlo.memory_budget_gb,
                       rule=rule)


def recovered_by_element(run, folder: str):
    """
    {element: {year: draws}} for the terminal flows that count as recovered.

    Element-depth rows only, and summed across the recovered flows rather than
    across depths: a deeper row is PART of its parent, so adding the two counts
    the same mass twice (MODEL_MECHANICS.md section 1).
    """
    from src.plot_monte_carlo import finest_layer, recovered_flows

    keys = run.keys
    layer = finest_layer(keys)
    recovered = recovered_flows(run, folder)
    in_recovered = keys['Stock/Flow ID'].isin(recovered).to_numpy()

    out = {}
    for element in sorted({e for e in keys[layer].unique() if e}):
        is_element = (keys[layer] == element).to_numpy()
        per_year = {}
        for year in sorted(keys['Year'].unique()):
            rows = in_recovered & is_element & (keys['Year'] == year).to_numpy()
            if rows.any():
                per_year[year] = run.values[rows].sum(axis=0)
        if per_year:
            out[element] = per_year
    return out


def summarise(series: dict) -> dict:
    """
    {element: {year: (p5, p50, p95)}}, plus the last year's draws kept whole.

    The percentiles are all the trajectory panel needs; keeping every draw of
    every year for both rules is the one thing here that would not fit.
    """
    bands, last_draws = {}, {}
    for element, per_year in series.items():
        years = sorted(per_year)
        bands[element] = {year: tuple(np.percentile(per_year[year], [5, 50, 95]))
                          for year in years}
        last_draws[element] = per_year[years[-1]].copy()
    return {'bands': bands, 'last': last_draws}


def widths(bands: dict) -> dict:
    """{element: 5th-to-95th width in the last year}."""
    return {element: per_year[max(per_year)][2] - per_year[max(per_year)][0]
            for element, per_year in bands.items()}


def draw(folder: str, results: dict, differing: list, params) -> list:
    """Two panels: the width per element, and the element that differs most."""
    import matplotlib.pyplot as plt

    from src.plot_monte_carlo import header
    from src.units import scale_for

    theme = params.figures.theme
    every = np.concatenate([results[RULES[0]]['last'][e] for e in differing])
    scale, unit = scale_for(every, params.run.working_unit)

    figure, (left, right), colours = figure_style.chart(
        1080, 420, theme, rows=1, columns=2)

    # Left: how wide each element's answer is under each rule.
    positions = np.arange(len(differing))
    bar = 0.38
    for offset, rule in enumerate(RULES):
        values = [widths(results[rule]['bands'])[e] * scale for e in differing]
        left.bar(positions + (offset - 0.5) * bar, values, bar,
                 label=rule, color=COLOURS[rule])
    left.set_xticks(positions)
    left.set_xticklabels(differing, rotation=0)
    # Fixed margins either side, so one element gives one pair of ordinary bars
    # rather than two slabs filling the panel.
    left.set_xlim(-0.7, len(differing) - 0.3)
    left.set_ylabel(f'5th-95th width ({unit})')
    left.set_title('How wide the answer is, per element', loc='left',
                   fontsize=10, color=colours['title'])
    left.legend(frameon=False, fontsize=8)
    left.grid(alpha=0.2, axis='y')

    # Right: the last year's distribution for whichever element moved most.
    gaps = {e: abs(widths(results['condition']['bands'])[e]
                   - widths(results['normalise']['bands'])[e]) for e in differing}
    worst = max(gaps, key=gaps.get)
    year = max(results[RULES[0]]['bands'][worst])
    for rule in RULES:
        draws = results[rule]['last'][worst] * scale
        low, _, high = np.percentile(draws, [5, 50, 95])
        right.hist(draws, bins=200, density=True, histtype='step', lw=1.6,
                   color=COLOURS[rule],
                   label=f'{rule}\n5-95%: {low:.3g}-{high:.3g} {unit} '
                         f'(width {high - low:.3g})')
    right.set_xlabel(unit)
    right.set_ylabel('density')
    right.set_title(f'{worst} recovered in {year} -- the element the rule moves most',
                    loc='left', fontsize=10, color=colours['title'])
    right.legend(frameon=False, fontsize=8)
    right.grid(alpha=0.2)

    # tight_layout BEFORE the header: it reflows the axes to fill the figure,
    # so a header written first ends up underneath the panel titles. The rect
    # keeps the top strip clear for it.
    figure.tight_layout(rect=(0, 0, 1, 0.86))
    header(figure, 'Conditioning against normalising',
           colours,
           'the same case solved twice; only groups with no is_residual row can differ')

    out_dir = figure_style.folder_for(params.figures.out_dir, folder)
    written = figure_style.write(figure, out_dir, 'compare_sum_rules',
                                 params.figures.enabled(), params.figures.dpi)
    plt.close(figure)
    return written


def report(folder: str, params) -> int:
    """Solve twice, say what differs, and draw it. Returns an exit code."""
    results = {}
    for rule in RULES:
        print(f'Solving {folder} with sum_to_one={rule!r} ...')
        run = solve_once(folder, params, rule)
        conditioned = run.report.get('conditioned', 0)
        if rule == 'condition':
            print(f'  conditioned groups: {conditioned}'
                  f"   worst effective sample: {run.report.get('worst_ess', 1):.1%}")
            if not conditioned:
                print()
                print('Nothing to compare. Every constrained group in this case '
                      'either names an\n`is_residual` row -- which settles it under '
                      'either rule -- or has no spread\nto redistribute.')
                print()
                print('To make the rule matter, give a group a measurement on every '
                      'row: clear its\n`is_residual` mark and fill in value_min and '
                      'value_max. See the TCs section\nof documentation/CASES.md.')
                return 0
        results[rule] = summarise(recovered_by_element(run, folder))
        del run

    shared = sorted(set(results['condition']['bands']) & set(results['normalise']['bands']))
    condition_width = widths(results['condition']['bands'])
    normalise_width = widths(results['normalise']['bands'])
    differing = [e for e in shared
                 if abs(condition_width[e] - normalise_width[e]) > MEANINGFUL]

    if not differing:
        print('\nThe two rules give the same answer for every element, to within '
              'floating point.')
        return 0

    from src.units import scale_for
    every = np.concatenate([results['condition']['last'][e] for e in differing])
    scale, unit = scale_for(every, params.run.working_unit)
    year = max(results['condition']['bands'][differing[0]])

    print(f'\n{len(differing)} of {len(shared)} elements differ, in {year} '
          f'({unit}):')
    # The three widths here are the row format below: 10 for the name, then
    # 8+1+8+1+8 = 26 for each triple, then three spaces, then 8 for the change.
    print(f"  {'element':<10}{'conditioned':^26}   {'normalised':^26}   "
          f"{'width':>8}")
    print(f"  {'':<10}{'p5      p50      p95':^26}   "
          f"{'p5      p50      p95':^26}   {'change':>8}")
    for element in sorted(differing, key=lambda e: -abs(condition_width[e]
                                                        - normalise_width[e])):
        a = [v * scale for v in results['condition']['bands'][element][year]]
        b = [v * scale for v in results['normalise']['bands'][element][year]]
        change = (condition_width[element] / normalise_width[element] - 1) * 100 \
            if normalise_width[element] else 0.0
        print(f'  {element:<10}'
              f'{a[0]:8.3g} {a[1]:8.3g} {a[2]:8.3g}   '
              f'{b[0]:8.3g} {b[1]:8.3g} {b[2]:8.3g}   {change:+7.1f}%')

    print('\nA narrower conditioned answer is the expected direction: it is the '
          'only one of\nthe two that uses every row\'s own measurement. See '
          'documentation/CASES.md.')

    for path in draw(folder, results, differing, params):
        print(path)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Solve a case under both sum-to-1 rules and compare them.')
    parser.add_argument('folder', nargs='?',
                        help='compare this case, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true',
                        help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases that can be compared, then stop')
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

    # These already say what is wrong and which setting to change. A traceback
    # on top of that helps nobody who is here to compare two rules.
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
