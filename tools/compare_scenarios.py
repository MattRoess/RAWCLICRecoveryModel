"""
compare_scenarios.py
====================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

Put a case's SCENARIOS side by side, each solved in its own right.

    ./.venv/bin/python tools/compare_scenarios.py data/battery

NOT a numbered step. One run is one scenario -- `src/selection.chosen_scenario`
refuses to guess -- so comparing them is analysis, and this does it by SOLVING
each scenario rather than reading what a previous run left behind.

WHY IT SOLVES RATHER THAN READS. `monte_carlo_summary.csv` keeps percentiles
and drops the draws. A figure built on those can show a median and nothing
honest about the spread: an interval read off a summary is that scenario's own
interval, and there is no way back from it to the draws. Solving keeps them, so
every band here is the Monte Carlo's -- the 2.5 and 97.5 percentiles OF THE
DRAWS, per year, per scenario.

    scenarios_recovered.png      recovered mass, one panel per resource
    scenarios_recovery_rate.png  what fraction comes back, resources pooled

Both belong to no single scenario, so they go to the case's own figure folder,
`figures/<case>/`, one level above the per-scenario ones.

THE BANDS ARE MEANT TO OVERLAP OR NOT. Where two scenarios' bands overlap, the
model does not resolve a difference between them, whatever the lines do. That
is the thing this figure is for, and it is why the bands are drawn rather than
the lines alone.

WHAT IT COSTS. One solve per scenario, at the case's own draw count -- so three
scenarios of the battery at 200,000 draws is three Monte Carlo runs. `--draws`
cuts that for a look; the shape settles long before the last digit does.

    ./tools/compare_scenarios.py <case> --draws 2000    a quick look
    ./tools/compare_scenarios.py <case> --all           every recovered resource
    ./tools/compare_scenarios.py -l                     list the cases
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
import copy

import numpy as np

from src import figure_style, source as source_module, upstream
from src.monte_carlo import solve_draws
from src.params_schema import ParameterError, current
from src.plot_monte_carlo import account, finest_layer, header
from src.plot_structure import choose, find_cases
from src.units import scale_for

# ONE COLOUR PER SCENARIO, held across both figures and every panel, so a
# reader learns the three colours once. From the shared palette, so a scenario
# and a stream in the combined figures cannot mean different things in one
# colour.
SCENARIO_COLOURS = figure_style.PALETTE


class NoScenarios(RuntimeError):
    """Raised when a case has no scenario dimension to compare."""


def scenarios_of(case: str, params) -> list[str]:
    """
    The scenarios this case's upstream export actually holds.

    Read off the export rather than off a previous run's output: this solves
    for itself, so what has been run before says nothing about what can be
    compared. A case whose `scenario_alias` sends every name to one folder has
    no scenario dimension of its own and is refused, rather than drawn as three
    identical lines.
    """
    described = source_module.read(case, params)
    root = os.path.normpath(os.path.join(params.data.upstream_root,
                                         described['upstream_dir']))
    if not os.path.isdir(root):
        raise NoScenarios(f'{root} does not exist -- nothing to read.')

    alias = described.get('scenario_alias') or {}
    if alias:
        raise NoScenarios(
            f'{case} maps every scenario onto {sorted(set(alias.values()))} '
            f'through `scenario_alias` in its source.csv,\nso it has one set of '
            f'draws and nothing to compare. Remove that line once its upstream '
            f'stage exports the scenarios itself.')

    found = sorted(name for name in os.listdir(root)
                   if os.path.isdir(os.path.join(root, name))
                   and not name.startswith('.'))
    if len(found) < 2:
        raise NoScenarios(
            f'{root} holds {len(found)} scenario folder(s)'
            + (f' ({", ".join(found)})' if found else '')
            + '.\nThere is nothing to compare until upstream exports at least two.')
    return found


def solved(case: str, params, scenario: str, draws: int):
    """One scenario's Monte Carlo run."""
    one = copy.deepcopy(params)
    one.run.scenario = scenario
    tables = upstream.load(one, case, quiet=True)
    return solve_draws(case, ['product', 'component', 'material', 'element'],
                       draws=draws, seed=one.monte_carlo.seed,
                       scenario=scenario, tables=tables,
                       chunk=one.monte_carlo.chunk,
                       budget_gb=one.monte_carlo.memory_budget_gb,
                       rule=one.monte_carlo.sum_to_one, quiet=True)


def accounts_of(run, resources: list[str]) -> dict[str, dict]:
    """
    {resource: its whole account, draws x years}, for the ones that come back.

    A resource with an account but NO RECOVERED MASS is dropped. The battery
    carries oxygen and silicon -- both lost outright, by a coefficient that
    says so -- and a panel per resource drew them as a flat zero, which is a
    true line and a wasted panel. What is lost has its own figure.
    """
    out = {}
    for resource in resources:
        one = account(run, resource)
        if one is not None and float(np.nansum(one['recovered'])) > 0:
            out[resource] = one
    return out


def band(draws_by_year: np.ndarray) -> tuple:
    """Mean and the 95% interval OF THE DRAWS, per year."""
    return (np.nanmean(draws_by_year, axis=0),
            np.nanpercentile(draws_by_year, 2.5, axis=0),
            np.nanpercentile(draws_by_year, 97.5, axis=0))


def reserve_strip(figure, points: float) -> None:
    """
    Keep `points` of the figure's foot clear, for the legend strip.

    AFTER `header`, which ends with `tight_layout(rect=[0, 0, 1, ...])`. A
    bottom margin passed before it is thrown away and the legend lands on the
    bottom row's tick labels. In points rather than a fraction: this figure's
    height changes with the number of resources.
    """
    figure.subplots_adjust(bottom=(points / 72.0) / figure.get_figheight())


def draw(case: str, per_scenario: dict, resources: list[str], years, params):
    """Both figures. Returns the paths written."""
    import matplotlib.pyplot as plt

    names = sorted(per_scenario)
    colour = {name: SCENARIO_COLOURS[i % len(SCENARIO_COLOURS)]
              for i, name in enumerate(names)}
    out_dir = figure_style.folder_for(params.figures.out_dir, case)
    handles = [plt.Line2D([], [], color=colour[n], linewidth=2.6, label=n)
               for n in names]
    written = []

    # ---- one panel per resource, recovered mass ---------------------------
    columns = min(3, len(resources))
    rows = -(-len(resources) // columns)
    figure, axes, colours = figure_style.chart(
        360 * columns, 300 * rows + 170, params.figures.theme, rows, columns)
    panels = axes.ravel() if hasattr(axes, 'ravel') else [axes]

    for panel, resource in zip(panels, resources):
        unit = None
        for name in names:
            got = per_scenario[name].get(resource)
            if got is None:
                continue
            middle, low, high = band(got['recovered'])
            if unit is None:
                scale, unit = scale_for(middle, params.run.working_unit)
            panel.fill_between(years, low * scale, high * scale,
                               color=colour[name], alpha=0.13, linewidth=0)
            panel.plot(years, middle * scale, color=colour[name], linewidth=2.2,
                       solid_capstyle='round')
        panel.set_title(resource, loc='left', fontsize=13, color=colours['title'])
        panel.set_ylabel(unit or params.run.working_unit,
                         color=colours['meta'], fontsize=10)
        panel.grid(alpha=0.2)
        panel.set_ylim(bottom=0)
    for panel in panels[len(resources):]:
        panel.axis('off')

    figure.tight_layout()
    header(figure, f'{os.path.basename(case)}: the scenarios side by side', colours,
           'recovered per year, means, with 95% of the draws.  the coefficients '
           'are the same in all of them -- what differs is what arrives.  '
           'where two bands overlap, the difference is not resolved')
    reserve_strip(figure, 78)
    figure.legend(handles=handles, loc='lower center', ncol=len(names),
                  frameon=False, fontsize=13, bbox_to_anchor=(0.5, 0.008))
    written += figure_style.write(figure, out_dir, 'scenarios_recovered',
                                  params.figures.enabled(), params.figures.dpi)
    plt.close(figure)

    # ---- one panel, the pooled recovery rate ------------------------------
    # POOLED PER DRAW, not by pooling percentiles: draw i's recovered over draw
    # i's collected, summed over the resources first. A ratio of two summaries
    # is not a ratio any draw ever had.
    figure, panel, colours = figure_style.chart(900, 620, params.figures.theme)
    ends = {}
    for name in names:
        got = per_scenario[name]
        if not got:
            continue
        back = sum(one['recovered'] for one in got.values())
        came = sum(one['collected'] for one in got.values())
        rate = np.divide(back, came, out=np.zeros_like(back), where=came > 0) * 100
        middle, low, high = band(rate)
        ends[name] = (middle[0], middle[-1])
        panel.fill_between(years, low, high, color=colour[name], alpha=0.13,
                           linewidth=0)
        panel.plot(years, middle, color=colour[name], linewidth=2.6,
                   solid_capstyle='round')
    panel.set_ylabel('recovered, % of what was collected',
                     color=colours['title'], fontsize=12)
    panel.set_xlabel('year', color=colours['meta'], fontsize=12)
    panel.set_ylim(0, 100)
    panel.grid(alpha=0.2)

    figure.tight_layout()
    header(figure, f'{os.path.basename(case)}: recovery rate by scenario', colours,
           'every tracked resource pooled PER DRAW, means with 95% of the draws.  '
           'the coefficients are the same in all of them')
    reserve_strip(figure, 86)
    figure.legend(handles=[plt.Line2D([], [], color=colour[n], linewidth=2.6,
                                      label=f'{n}   {ends[n][0]:.1f} -> '
                                            f'{ends[n][1]:.1f}%')
                           for n in names if n in ends],
                  loc='lower center', ncol=len(names), frameon=False,
                  fontsize=13, bbox_to_anchor=(0.5, 0.008))
    written += figure_style.write(figure, out_dir, 'scenarios_recovery_rate',
                                  params.figures.enabled(), params.figures.dpi)
    plt.close(figure)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Compare a case across its scenarios.')
    parser.add_argument('folder', nargs='?', help='the case to compare')
    parser.add_argument('--pick', action='store_true', help='choose from a list')
    parser.add_argument('-l', '--list', action='store_true', help='list the cases')
    parser.add_argument('--all', action='store_true',
                        help='every recovered resource, not just figures.resources')
    parser.add_argument('--draws', type=int, default=None,
                        help="fewer draws than the case's own, for a quick look")
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

    case = args.folder or (choose() if args.pick else params.run.data_folder)
    try:
        names = scenarios_of(case, params)
    except NoScenarios as error:
        print(error, file=sys.stderr)
        return 1

    described = source_module.read(case, params)
    draws = args.draws or described['draws']
    print(f'{case}: {len(names)} scenarios -- {", ".join(names)}')
    print(f'  solving each at {draws:,} draws')

    wanted = list(params.figures.resources)
    per_scenario, years = {}, None
    for name in names:
        print(f'  solving {name} ...', flush=True)
        run = solved(case, params, name, draws)
        here = sorted(int(y) for y in run.keys['Year'].unique())
        if years is None:
            years = here
        elif here != years:
            print(f'{name} covers {here[0]}-{here[-1]} but {names[0]} covers '
                  f'{years[0]}-{years[-1]}.', file=sys.stderr)
            return 1
        # The finest layer the case fills, the way `account` finds it --
        # not the last column, which is a dead `Layer 4` for a
        # material-keyed case.
        carrying = sorted({r for r in run.keys[finest_layer(run.keys)].unique() if r})
        per_scenario[name] = accounts_of(run, carrying if args.all or not wanted
                                         else [r for r in carrying if r in wanted])
        del run

    resources = sorted({r for got in per_scenario.values() for r in got})
    if not resources:
        print('No resource carried an account in any scenario.', file=sys.stderr)
        return 1
    print(f'  drawing: {", ".join(resources)}')

    for path in draw(case, per_scenario, resources, years, params):
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
