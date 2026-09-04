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
from src.plot_monte_carlo import (account, account_legend, draw_account,
                                  header, routes)
from src.rest import LAYERS, REST
from src.units import readable, scale_for
from src.upstream import load as refresh

LAYER_NAMES = ['product', 'component', 'material', 'element']


class CombineError(ValueError):
    """Raised when the cases named cannot be added together."""


def named_in(run, names) -> str | None:
    """
    Which spelling of the metal this case uses, if any.

    The wiring case resolves materials and calls it `copper`; the boards case
    resolves elements and calls it `Cu`. A case with none of the names given
    contributes nothing and says so, rather than counting zero quietly.
    """
    keys = run.keys
    layer = next((column for column in reversed(LAYERS)
                  if column in keys.columns
                  and keys[column].astype(str).str.strip().any()), None)
    if layer is None:
        return None
    present = {value for value in keys[layer].unique() if value and value != REST}
    return next((name for name in names if name in present), None)


def roads_of(run, resource: str, years) -> dict:
    """That case's recovered mass per road, per year per draw."""
    keys = run.keys
    layer = next(column for column in reversed(LAYERS)
                 if column in keys.columns
                 and keys[column].astype(str).str.strip().any())
    out = {}
    for road, flows in routes(run).items():
        columns = []
        for year in years:
            rows = np.flatnonzero(
                keys['Stock/Flow ID'].isin(flows).to_numpy()
                & (keys[layer] == resource).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            columns.append(run.values[rows].sum(axis=0) if rows.size
                           else np.zeros(run.draws))
        draws = np.column_stack(columns)
        if draws.mean(axis=0).max() > 0:
            out[road] = draws
    return out


def added(parts: list[dict]) -> dict:
    """
    Several accounts added, per draw.

    Every key is (draws x years), and draw i is the same world in every case --
    same fleet, same year -- so adding within the draw and taking percentiles
    afterwards gives the interval of the SUM. Adding percentiles instead would
    assume every stream hits its own 97.5th at once, which is wider than any
    world can be.
    """
    keys = [k for k in parts[0] if k != 'years']
    whole = {k: sum(part[k] for part in parts) for k in keys}
    whole['years'] = parts[0]['years']
    return whole


def figure_combined(whole: dict, roads: dict, years, theme: str, unit: str,
                    label: str, title: str, streams: list[str]):
    """
    THE SAME PICTURE AS `account.png`, over every stream added together.

    Not a new design: `src.plot_monte_carlo.draw_account` draws it, so the
    combined figure and the per-case one cannot drift apart. What changes is
    only what it is handed -- an account summed per draw across the cases
    instead of one case's.
    """
    scale, shown = scale_for(np.nanpercentile(whole['outflow'], 97.5, axis=0),
                             unit)
    figure, axes, colours = chart(1180, 820, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    rate_axis = draw_account(panel, f'{title} {label}', whole, roads, years,
                             scale, shown, colours)

    header(figure, f'{title}: {label}, every stream added', colours,
           f'{years[0]}-{years[-1]}, {len(years)} years, one point each.  '
           f'{" + ".join(streams)}, ADDED PER DRAW, so every interval is the '
           f'interval of a sum.  masses are MEANS in the same unit: recovered '
           f'+ lost + never collected = the outflow')
    account_legend(figure, [(panel, rate_axis)], colours, 1,
                   strip_numbers=False)
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
    parts, streams, roads, years = [], [], {}, None
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
        used = named_in(run, wanted)
        these = sorted(int(year) for year in run.keys['Year'].unique())
        if years is None:
            years = these
        elif these != years:
            raise CombineError(
                f'{folder} covers {these[0]}-{these[-1]} ({len(these)} years) '
                f'but the case before it covers {years[0]}-{years[-1]} '
                f'({len(years)}). Cases can only be added year by year, so set '
                f'`years` in src/params_schema.py to a span they all have.')
        if used is None:
            print(f'    none of {", ".join(wanted)} in this case -- skipped')
            continue
        one = account(run, used)
        if one is None:
            print(f'    {used}: no upstream draws for this case -- skipped')
            continue
        stream = os.path.basename(folder)[shorten:].replace('_', ' ') \
            or os.path.basename(folder)
        parts.append(one)
        streams.append(f'{stream} ({used})')
        for road, draws_of in roads_of(run, used, years).items():
            roads[road] = roads.get(road, 0) + draws_of
        print(f'    {used}: '
              f'{readable(float(np.nanmean(one["recovered"][:, -1])), params.run.working_unit)} '
              f'recovered in {years[-1]}')
        del run

    if not parts:
        raise CombineError(
            f'None of the cases resolve any of: {", ".join(wanted)}.\n'
            f'`combine.resource` in src/params_schema.py lists every spelling '
            f'the metal has -- the wiring case calls it `copper`, the boards '
            f'case calls it `Cu`.')

    figure = figure_combined(added(parts), roads, years, params.figures.theme,
                             params.run.working_unit, params.combine.label,
                             params.combine.whole, streams)
    written = write(figure, params.combine.out_dir,
                    f'{params.combine.label}_combined',
                    params.figures.enabled(), params.figures.dpi)
    for path in written:
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
