"""
03_run_monte_carlo.py
=====================

Run the model over many draws and write the figures that show what the spread
actually is.

    ./.venv/bin/python 03_run_monte_carlo.py

Everything it uses is set in `src/params_schema.py`: which case, which years,
how many draws, the seed, the chunk size and the figure formats. Change a value
there, run `00_parameters.py`, and run this again.

WHAT IT WRITES
--------------
  <data folder>/output_data/[<scenario>/]monte_carlo_summary.csv
      One row per result row, with the mean, the standard deviation and the
      5th, 25th, 50th, 75th and 95th percentiles across draws, next to the
      deterministic value for comparison.

  figures/mc_*.png
      mc_distribution   where the answer lies, and where the deterministic run
                        sits inside it
      mc_spread         how uncertain each flow is
      mc_mode_vs_mean   what the Monte Carlo *changes*, not just how uncertain
                        it is -- read this one first
      mc_convergence    how many draws the answer needs
      mc_sensitivity    which coefficients drive the spread

WHY THE SUMMARY IS PERCENTILES AND NOT THE DRAWS
------------------------------------------------
The full array is rows x draws x 8 bytes, which at 200,000 draws is far larger
than anything worth writing to disk on every run. The percentiles are what a
result is reported as. Draws are processed in chunks and the statistics
accumulated as they go; if per-draw traces are ever needed for a few named
rows, that is a narrow addition rather than a change of approach.
"""

from __future__ import annotations

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
import os
import sys

import numpy as np
import pandas as pd


from src.monte_carlo import MemoryBudgetExceeded, solve_draws
from src.params_schema import ParameterError, current
from src.sampling import SamplingError
from src.upstream import UpstreamError, load as refresh
from src.plot_monte_carlo import draw_all
from src.report import write as write_workbook
from src.recovery_model_optimized import RecoveryModelOptimized
from src.validate_inputs import InputDataError

# These four already say what is wrong and which file or setting to change.
# This is run by pressing Run in an editor, so a traceback on top of that text
# is noise in front of the answer, not a detail.
CLEAR = (InputDataError, UpstreamError, MemoryBudgetExceeded, SamplingError)

LAYER_NAMES = ['product', 'component', 'material', 'element']
KEYS = ['Year', 'Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
# The same interval the figures draw (src/plot_monte_carlo.INTERVAL), so a
# number read off a chart matches a number read out of the workbook.
PERCENTILES = [2.5, 25, 50, 75, 97.5]


def _tables(params, folder):
    """The upstream frames, fetched quietly for a repeat call."""
    return refresh(params, folder, quiet=True)


def deterministic_solution(params, folder) -> pd.DataFrame:
    """The single-value answer, for comparison. Every coefficient at its mode."""
    solution = RecoveryModelOptimized(
        data_folder=folder, layer_names=LAYER_NAMES,
        tables=_tables(params, folder),
    ).solve_models_and_write_to_output()
    solution['Value'] = pd.to_numeric(solution['Value'])
    solution['Year'] = solution['Year'].astype(str)
    return solution


# The percentile grid written beside the summary statistics. Every fifth
# percentile, with the tails at 1 and 99 and the reported interval's own 2.5 and
# 97.5 among them, so the 95% figure quoted everywhere else is a column here
# rather than something to interpolate.
#
# THIS IS THE DISTRIBUTION, IN A FORM SOMETHING ELSE CAN USE. The draws
# themselves are 215 rows x 200,000 x 8 bytes -- 344 MB for one case -- so they
# are not written. A percentile grid is the whole shape at 23 numbers a row:
# read it back, and linear interpolation between the points reconstructs the
# curve or draws from it.
GRID = (1, 2.5, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
        85, 90, 95, 97.5, 99)


def _mode(values: np.ndarray, bins: int = 64) -> np.ndarray:
    """
    The peak of each row's distribution: the midpoint of its fullest bin.

    NOT the same as the `deterministic` column beside it. That is the answer
    with every COEFFICIENT at its mode, which is a different thing and usually
    a different number -- a product of triangular variables does not put its
    mode where its inputs put theirs. Having both is the point: the gap between
    them is what the Monte Carlo is for.

    A histogram peak rather than a kernel estimate, because it needs no extra
    dependency and no bandwidth choice, and 64 bins over 200,000 draws locates
    the peak far more precisely than the coefficients justify.
    """
    out = np.zeros(values.shape[0])
    for row in range(values.shape[0]):
        sample = values[row]
        low, high = sample.min(), sample.max()
        if not np.isfinite(low) or high <= low:
            out[row] = low                     # a point mass: it is its own mode
            continue
        counts, edges = np.histogram(sample, bins=bins, range=(low, high))
        peak = int(counts.argmax())
        out[row] = 0.5 * (edges[peak] + edges[peak + 1])
    return out


def summarise(run) -> pd.DataFrame:
    """
    Mean, mode, median, spread and the percentile grid, per result row.

    Everything a downstream user needs to take a result further without
    re-running: the central values, how wide it is, and the shape itself.
    """
    values = run.values
    summary = run.keys.copy()
    summary['mean'] = values.mean(axis=1)
    summary['mode'] = _mode(values)
    summary['sd'] = values.std(axis=1, ddof=1) if run.draws > 1 else 0.0
    for percentile, column in zip(PERCENTILES,
                              ('p2_5', 'p25', 'p50', 'p75', 'p97_5')):
        summary[column] = np.percentile(values, percentile, axis=1)
    # `p50` above is the median; it is repeated in the grid on purpose, so the
    # grid is a complete curve on its own rather than one with a hole in it.
    for percentile in GRID:
        summary[f'q{percentile:g}'.replace('.', '_')] = \
            np.percentile(values, percentile, axis=1)
    return summary


def run_case(folder, params, draws: int) -> int:
    """
    The run itself: sample, solve, write the summary and draw the figures.

    Every step here reads the case, so any of the four clear errors can come
    out of it. `main` prints them as themselves.
    """
    tables = refresh(params, folder)
    run = solve_draws(folder, LAYER_NAMES, draws=draws,
                      seed=params.monte_carlo.seed, tables=tables,
                      chunk=params.monte_carlo.chunk,
                      budget_gb=params.monte_carlo.memory_budget_gb,
                      rule=params.monte_carlo.sum_to_one,
                      quiet=False)

    report = run.report
    if not report.get('uncertain'):
        print('\nThis case has no value_min / value_max columns, so there is nothing')
        print('to sample: every draw returns the same number. See')
        print('documentation/DESIGN_tc_table.md for the schema that adds them.')
        return 1

    print(f'Constrained groups : {report["groups"]} summing to 1'
          f'   ({report.get("unconstrained", 0)} left free)')
    if report['clamped']:
        print(f'Bounds clamped into [0, 1] : {len(report["clamped"])}')
        for note in report['clamped'][:10]:
            print(f'    {note}')
    if report.get('conditioned'):
        survived = report['worst_ess']
        print(f'Conditioned groups : {report["conditioned"]} -- every row\'s own '
              f'range used, none discarded')
        print(f'    worst effective sample: {survived:.1%} of {draws:,} draws')
        if survived < 0.2:
            print('    THAT IS LOW. It means the measured ranges in that group '
                  'barely admit\n    a combination summing to 1, so they are close '
                  'to contradicting each\n    other. Check the SUM TO 1 section of '
                  '01_check_inputs.py.')

    if report['negative_residuals']:
        print(f'NEGATIVE RESIDUALS : {report["negative_residuals"]} (draw, group) pairs where '
              f'the sampled recovery fractions summed past 1.\n'
              f'    That is physically impossible and says the input ranges are wrong.')

    # Unspecified mass that stops in an intermediate flow is lost invisibly:
    # totalling the terminal flows never sees it. Said plainly rather than
    # folded into a figure.
    from src.rest import stranded
    stalled = stranded(run.keys.assign(Value=run.values.mean(axis=1)), run.tcs)
    if len(stalled):
        total = float(stalled['Value'].sum())
        print(f'\nSTRANDED UNSPECIFIED MASS : {total:,.1f} {params.run.working_unit} '
              f'in {stalled["Stock/Flow ID"].nunique()} intermediate flow(s)')
        print('    Carried by the coarse coefficients, then stopped at the first')
        print("    process keyed finer than itself. It never reaches a terminal flow,")
        print('    so totalling those does not see it. Give `rest` its own')
        print('    coefficients in TCs.csv to route it explicitly.')
        for _, row in stalled.head(6).iterrows():
            path = ' / '.join(x for x in row[['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']] if x)
            print(f'      {row["Stock/Flow ID"]:22s} {path:34s} {row["Value"]:>12,.1f}')

    determined = deterministic_solution(params, folder)
    summary = summarise(run)

    merged = summary.merge(determined[KEYS + ['Value']].rename(
        columns={'Value': 'deterministic'}), on=KEYS, how='left')

    model = RecoveryModelOptimized(data_folder=folder,
                                   layer_names=LAYER_NAMES,
                                   tables=_tables(params, folder))
    path = model.output_path('monte_carlo_summary.csv')
    from src.rest import drop_unused_layers
    drop_unused_layers(merged).to_csv(path, index=False)
    print(f'\n{path}: {len(merged):,} rows')

    # Everything in one workbook: the headline totals, where the mass went, the
    # mass balance, every result row, and the coefficient table with its source
    # column, so the numbers and what produced them stay together.
    workbook = model.output_path('recovery_results.xlsx')
    sheets = write_workbook(workbook, params, run, merged, run.tcs,
                            tables['composition'] if tables else pd.DataFrame(),
                            case=folder)
    print(f'{workbook}: {len(sheets)} sheets -- {", ".join(sheets)}')

    written = draw_all(run, determined, params.figures.out_dir,
                       params.figures.enabled(), params.figures.dpi,
                       params.figures.theme, params.run.working_unit,
                       case=folder)
    for figure_path in written:
        print(f'{figure_path}')

    # The headline: how far the single-value answer sits from the mean.
    comparable = merged[merged['deterministic'].notna() & (merged['mean'] > 0)]
    if len(comparable):
        gap = 100.0 * (comparable['deterministic'] - comparable['mean']) / comparable['mean']
        worst = comparable.iloc[gap.abs().to_numpy().argmax()]
        # The deepest layer this row actually fills. `Layer 4 or Layer 2` named
        # the worst row 'Wiring' -- the component -- on a case whose resources
        # live at Layer 3, so the printed line disagreed with mode_vs_mean.png
        # about which result was worst.
        named = next((worst[layer] for layer in reversed(KEYS[2:]) if worst[layer]), '')
        print(f'\nDeterministic run against the Monte Carlo mean:')
        print(f'  median gap {np.median(np.abs(gap)):.1f}%, largest {gap.abs().max():.1f}% '
              f'on {worst["Stock/Flow ID"]} {named} in {worst["Year"]}')
        print(f'  Running every coefficient at its mode is not the same as the mean.')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', default=None,
                        help='case folder to run; defaults to run.data_folder')
    args = parser.parse_args(argv)

    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    if not params.monte_carlo.enabled:
        print('monte_carlo.enabled is False in src/params_schema.py. Nothing to do.')
        return 0

    folder = args.folder or params.run.data_folder
    if not os.path.isdir(folder):
        print(f"There is no case folder called '{folder}'.", file=sys.stderr)
        return 1

    # The case says how many draws it has (src/source.py); the setting is only
    # the fallback for a case that does not.
    from src import source as source_module
    draws = source_module.read(folder, params)['draws'] \
        if source_module.exists(folder) else params.data.draws
    print(f'Case      : {folder}')
    print(f'Draws     : {draws:,}  (seed {params.monte_carlo.seed})')

    try:
        return run_case(folder, params, draws)
    except CLEAR as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
