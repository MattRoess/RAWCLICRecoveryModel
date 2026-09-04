"""
04_combine_cases.py
===================

**One metal across several streams, added per draw.**

Press Run. Nothing to type. What is added, and which metal, is set in
`src/params_schema.py` under `combine`.

WHY THIS IS ITS OWN STAGE
-------------------------
The wiring case and the boards case are separate studies: separate folders,
separate networks, separate coefficients, separate runs. They stay that way
(DECISIONS 20). But the copper the wiring recovers and the copper the boards
recover are the same metal coming out of the same car, and the question "how
much copper does BEV electronics return" is answered by neither case alone.

So this adds them. It is reporting, exactly as DECISIONS 11 reports the two
roads apart and also combined -- an addition made for the reader, never a third
flow in anybody's network.

It is a separate stage because the list will grow. Battery packs and
drivetrains join by getting a case folder and being named in `combine.cases`;
nothing here knows how many there are or what they are called.

ADDED PER DRAW, NOT PER PERCENTILE
----------------------------------
Every case reads the same upstream draws with the same seed, so draw i is one
world in all of them: the same fleet, the same year, the same number of cars.
Adding within the draw and taking percentiles afterwards therefore gives the
interval of the sum.

Adding the percentiles instead would give something wider than any world -- it
would assume every stream hits its own 97.5th percentile simultaneously, which
is the mistake the Monte Carlo exists to avoid (DECISIONS 14).

WHAT IT COSTS
-------------
Each case is solved in full, one after another, and only the two series this
figure needs are kept: recovered and collected, for the one metal, per year,
per draw. That is 11 x 200,000 x 8 bytes -- about 18 MB a case -- so the
memory does not grow with the number of cases, only the time does.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.figure_style import PALETTE, chart, write
from src.monte_carlo import solve_draws
from src.params_schema import Params
from src.plot_monte_carlo import (header, recovered_flows, years_listed)
from src.report import start_flows
from src.rest import REST, LAYERS
from src.units import readable, scale_for
from src.upstream import load as refresh

LAYER_NAMES = ['product', 'component', 'material', 'element']


class CombineError(ValueError):
    """Raised when the cases named cannot be added together."""


def series_for(run, names) -> tuple[np.ndarray, np.ndarray, str] | None:
    """
    One case's recovered and collected mass for the metal, per year per draw.

    `names` is every spelling the metal has across the cases -- the wiring case
    resolves materials and calls it `copper`, the boards case resolves elements
    and calls it `Cu`. Whichever this case has is the one used; a case with none
    of them contributes nothing and says so, rather than counting zero quietly.

    Returns (recovered, collected, the name this case used), each array shaped
    (years, draws).
    """
    keys = run.keys
    layer = next((column for column in reversed(LAYERS)
                  if column in keys.columns
                  and keys[column].astype(str).str.strip().any()), None)
    if layer is None:
        return None
    present = {value for value in keys[layer].unique() if value and value != REST}
    used = next((name for name in names if name in present), None)
    if used is None:
        return None

    years = sorted(int(year) for year in keys['Year'].unique())
    recovered_ids = recovered_flows(run, run.case)
    starts = start_flows(run.tcs)

    def rows_for(flows, year):
        return np.flatnonzero(
            keys['Stock/Flow ID'].isin(flows).to_numpy()
            & (keys[layer] == used).to_numpy()
            & (keys['Year'].astype(str) == str(year)).to_numpy())

    got, came = [], []
    for year in years:
        back = rows_for(recovered_ids, year)
        into = rows_for(starts, year)
        got.append(run.values[back].sum(axis=0) if back.size
                   else np.zeros(run.draws))
        came.append(run.values[into].sum(axis=0) if into.size
                    else np.zeros(run.draws))
    return np.array(got), np.array(came), used


def figure_combined(parts: dict, years, theme: str, unit: str,
                    label: str, whole: str):
    """
    The metal across every stream, added, with each stream shown beneath it.

    Two panels, sharing the year axis:

    - **the mass**, one line per stream and a heavier line for the total, each
      with its own 95% band. The total's band is NARROWER than the sum of the
      streams' bands would be, because it is formed inside the draw.
    - **the rate**, recovered over collected, for the whole and for each
      stream. This is where a stream that recovers well but carries little mass
      shows up: it is invisible in the panel above and obvious here.
    """
    order = list(parts)
    got = sum(parts[case]['recovered'] for case in order)
    came = sum(parts[case]['collected'] for case in order)

    def band(draws):
        return (np.percentile(draws, 50, axis=1),
                np.percentile(draws, 2.5, axis=1),
                np.percentile(draws, 97.5, axis=1))

    scale, shown = scale_for(np.percentile(got, 97.5, axis=1), unit)
    figure, axes, colours = chart(1180, 820, theme, 2, 1,
                                  height_ratios=(1.6, 1))
    mass, rate = np.array(axes, dtype=object).reshape(2)

    median, low, high = band(got)
    mass.fill_between(years, low * scale, high * scale, color=colours['title'],
                      alpha=0.12, linewidth=0)
    mass.plot(years, median * scale, color=colours['title'], linewidth=3.0,
              marker='o', markersize=4,
              label=f'{whole}, all streams   {readable(median[-1], unit)} '
                    f'in {years[-1]}')
    for index, case in enumerate(order):
        colour = PALETTE[index % len(PALETTE)]
        one_median, one_low, one_high = band(parts[case]['recovered'])
        mass.fill_between(years, one_low * scale, one_high * scale,
                          color=colour, alpha=0.16, linewidth=0)
        mass.plot(years, one_median * scale, color=colour, linewidth=1.9,
                  marker='o', markersize=3,
                  label=f'{parts[case]["name"]}   '
                        f'{readable(one_median[-1], unit)} in {years[-1]}')

    with np.errstate(invalid='ignore', divide='ignore'):
        whole_rate = np.where(came > 0, 100 * got / came, np.nan)
    median, low, high = (np.nanpercentile(whole_rate, 50, axis=1),
                         np.nanpercentile(whole_rate, 2.5, axis=1),
                         np.nanpercentile(whole_rate, 97.5, axis=1))
    rate.fill_between(years, low, high, color=colours['title'], alpha=0.12,
                      linewidth=0)
    rate.plot(years, median, color=colours['title'], linewidth=3.0,
              marker='o', markersize=4,
              label=f'{whole}   {median[0]:.0f} → {median[-1]:.0f}%')
    for index, case in enumerate(order):
        colour = PALETTE[index % len(PALETTE)]
        with np.errstate(invalid='ignore', divide='ignore'):
            one = np.where(parts[case]['collected'] > 0,
                           100 * parts[case]['recovered']
                           / parts[case]['collected'], np.nan)
        one_median = np.nanpercentile(one, 50, axis=1)
        rate.plot(years, one_median, color=colour, linewidth=1.9,
                  linestyle=(0, (5, 2)), marker='o', markersize=3,
                  label=f'{parts[case]["name"]}   {one_median[0]:.0f} → '
                        f'{one_median[-1]:.0f}%')
    rate.set_ylim(0, 100)
    rate.set_yticks([0, 25, 50, 75, 100])

    mass.set_ylabel(f'{label} recovered ({shown})', color=colours['meta'],
                    fontsize=13)
    rate.set_ylabel('% of that stream collected', color=colours['meta'],
                    fontsize=13)
    rate.set_xlabel('year', color=colours['meta'], fontsize=13)
    # The rate panel's legend goes at the BOTTOM: every stream recovers well,
    # so all its lines run along the top and an upper-left legend is drawn
    # straight through them.
    for panel, where in ((mass, 'upper left'), (rate, 'lower left')):
        panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
        panel.tick_params(labelsize=15)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        legend = panel.legend(fontsize=10, frameon=False, loc=where)
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    header(figure, f'{whole}: {label}, every stream added', colours,
           f'{years[0]}-{years[-1]}, {len(years)} years, one point each.  '
           f'solid: median, band: 95%.  the streams are ADDED PER DRAW, so the '
           f'total\'s interval is the interval of the sum, not the sum of the '
           f'intervals')
    return figure


def _shared_prefix(names: list[str]) -> int:
    """
    How much of every case's folder name is the same, to the last underscore.

    `bev_electronics_wiring` and `bev_electronics_boards` share
    `bev_electronics_`, so the legend can say `wiring` and `boards` -- the part
    that distinguishes them, which is the part a reader needs. Cut on an
    underscore so a shared prefix never chops a word in half, and only when
    something is left over: two cases named the same but for a digit keep their
    full names rather than becoming `1` and `2`.
    """
    if len(names) < 2:
        return 0
    cut = 0
    for position, character in enumerate(names[0]):
        if any(len(name) <= position or name[position] != character
               for name in names[1:]):
            break
        if character == '_':
            cut = position + 1
    return cut if all(len(name) > cut for name in names) else 0


def main() -> int:
    params = Params()
    wanted = tuple(params.combine.resource)
    parts, years = {}, None
    shorten = _shared_prefix([os.path.basename(c) for c in params.combine.cases])

    print(f'Combining : {params.combine.label} across '
          f'{len(params.combine.cases)} case(s)')
    for folder in params.combine.cases:
        if not os.path.isdir(folder):
            raise CombineError(
                f'{folder} is not a folder. `combine.cases` in '
                f'src/params_schema.py names the case folders to add.')
        print(f'  solving {folder} ...', flush=True)
        run = solve_draws(folder, LAYER_NAMES,
                          draws=params.data.draws,
                          seed=params.monte_carlo.seed,
                          tables=refresh(params, folder, quiet=True),
                          chunk=params.monte_carlo.chunk,
                          budget_gb=params.monte_carlo.memory_budget_gb,
                          rule=params.monte_carlo.sum_to_one,
                          quiet=True)
        found = series_for(run, wanted)
        these = sorted(int(year) for year in run.keys['Year'].unique())
        if years is None:
            years = these
        elif these != years:
            raise CombineError(
                f'{folder} covers {these[0]}-{these[-1]} ({len(these)} years) '
                f'but the case before it covers {years[0]}-{years[-1]} '
                f'({len(years)}). Cases can only be added year by year, so set '
                f'`years` in src/params_schema.py to a span they all have.')
        if found is None:
            print(f'    none of {", ".join(wanted)} in this case -- skipped')
            continue
        got, came, used = found
        stream = os.path.basename(folder)[shorten:].replace('_', ' ') \
            or os.path.basename(folder)
        parts[folder] = {'recovered': got, 'collected': came,
                         'name': f'{stream} ({used})'}
        print(f'    {used}: {readable(float(got[-1].mean()), params.run.working_unit)} '
              f'recovered in {years[-1]}')
        del run

    if not parts:
        raise CombineError(
            f'None of the cases resolve any of: {", ".join(wanted)}.\n'
            f'`combine.resource` in src/params_schema.py lists every spelling '
            f'the metal has -- the wiring case calls it `copper`, the boards '
            f'case calls it `Cu`.')

    figure = figure_combined(parts, years, params.figures.theme,
                             params.run.working_unit, params.combine.label,
                             params.combine.whole)
    written = write(figure, params.combine.out_dir,
                    f'{params.combine.label}_combined',
                    params.figures.enabled(), params.figures.dpi)
    for path in written:
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
