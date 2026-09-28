"""
tools/compare_routes.py
=======================

THE FOUR RECOVERY ROUTES, COMPARED. One figure per rare earth.

    ./.venv/bin/python tools/compare_routes.py

WHY THIS IS NOT PART OF 04. `05_combine_cases.py` ADDS cases, because wiring,
boards and the battery are different parts of one car, and it runs over the
BATTERY's scenarios S1/S2/S3. Neither fits here. The rare earths are not
affected by a battery chemistry scenario, and the four traction motor cases are
COMPETING ROUTES for the same motors -- adding them would count one fleet four
times. Said plainly on 2026-09-25: "REE are not affected by S1/S2/S3 so have
them separate".

SO THERE IS NO TOTAL ON THESE FIGURES, and that is the point. Four lines, one
per route, each with the 95% interval of its own draws. The question they
answer is which route recovers more, not how much the fleet recovers.

WHERE THE NUMBERS COME FROM. Each case's `Recovered` sheet, written by
03_run_monte_carlo.py. That sheet carries the interval taken from the summed
DRAWS, which matters for the split case: it recovers each rare earth down both
loops, and adding the two flows' percentiles is not the interval of their sum
(p2.5 comes out 5.4% low, p97.5 4.7% high -- measured on Nd in 2050).

A workbook written before 2026-09-25 has no `resource` column and only the four
rare earths in it. Re-run 03 rather than reading it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bootstrap import ensure_venv
ensure_venv()

import numpy as np
import pandas as pd

from src.figure_style import chart, write
from src.params_schema import current
from src.units import factor

# The four routes, in the order they are meant to be read: most disassembly
# first, none at all last, the share between them at the end as the blend.
ROUTES = [('data_folder/tractionmotor', 'long loop (hydromet)'),
          ('data_folder/tractionmotor_shortloop', 'short loop (HD/HPMS)'),
          ('data_folder/tractionmotor_shredder', 'shredder, no disassembly'),
          ('data_folder/tractionmotor_split', 'share of both loops')]

REE = ['Nd', 'Pr', 'Dy', 'Tb']

# What each route DOES with the resource, as two questions. `in the fleet` is
# deliberately not among them: the stock is inflow minus outflow, both read
# from the upstream arrays, which are the same folder for every route -- what
# recycling does afterwards cannot change how much is driving around. Four
# identical lines would be a comparison of nothing.
STOCKS = (('recovered', 'recovered', 'came back'),
          ('lost', 'lost', 'did not come back'))

# The magnet and its elements, and copper. DECISIONS 29: what the route
# decides is the magnet and the copper; the bulk metals come back either way.
RESOURCES = REE + ['copper']
AXIS_UNIT = 'kt'
COLOURS = ['#1F4E79', '#C0392B', '#7F8C8D', '#D68910']


def recovered_sheet(case: str, scenario: str) -> pd.DataFrame | None:
    """The `Recovered` sheet of one case and scenario, or None if not written."""
    path = os.path.join(case, 'output_data', scenario, 'recovery_results.xlsx')
    if not os.path.exists(path):
        return None
    frame = pd.read_excel(path, sheet_name='Recovered')
    if 'resource' not in frame.columns:
        raise SystemExit(
            f'{path} was written before 2026-09-25: it has no `resource` column '
            f'and holds only the rare earths.\nRe-run 03_run_monte_carlo.py.')
    frame['Year'] = frame['Year'].astype(int)
    return frame


LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# ⚠️ THE SUBTITLE WRAPS. These figures say in the subtitle what they will not
# say with a band -- that percentiles do not add, that there is no total -- and
# a sentence that runs off the right edge takes the caveat with it. The axes
# are about 1,040 points wide at 11pt, so roughly 180 characters fit; 150
# leaves room for a long resource name.
SUBTITLE_CHARS = 150
LINE = 0.055          # axes fractions between heading lines


def heading(panel, title: str, subtitle: str, colours) -> int:
    """Title and a wrapped subtitle above the axes. Returns the line count."""
    import textwrap

    lines = textwrap.wrap(subtitle, SUBTITLE_CHARS) or ['']
    top = 1.06 + LINE * len(lines)
    panel.text(0.0, top, title, transform=panel.transAxes, fontsize=17,
               fontweight='bold', color=colours['title'], va='center',
               parse_math=False)
    for number, line in enumerate(lines):
        panel.text(0.0, top - LINE * (number + 1), line,
                   transform=panel.transAxes, fontsize=11,
                   color=colours['sub'], va='center', parse_math=False)
    return len(lines)


def lost_sheet(case: str, scenario: str) -> pd.DataFrame | None:
    """
    Lost per resource per year, from the `Distribution` sheet.

    The `Recovered` sheet covers recovered flows only, so the losses have to be
    read from every row and filtered by the case's own `processes` table -- a
    flow is a loss because the table says so, never because of its name.

    ⚠️ ONE ROW PER RESOURCE PER FLOW PER YEAR, at its own depth. The sheet
    holds every depth, and a component named after its material answers the
    same resource twice with the same mass (DEFECTS 3.21). Shallowest wins.

    MEANS ONLY. Several loss flows feed one resource and percentiles do not
    add, so an interval summed across them would be a number nobody measured.
    """
    from src.rest import flow_roles

    path = os.path.join(case, 'output_data', scenario, 'recovery_results.xlsx')
    if not os.path.exists(path):
        return None
    frame = pd.read_excel(path, sheet_name='Distribution').fillna('')
    for column in LAYERS:
        if column not in frame.columns:
            frame[column] = ''
    losses = {flow for flow, role in flow_roles(case).items() if role == 'loss'}
    frame = frame[frame['Stock/Flow ID'].isin(losses)].copy()
    if not len(frame):
        return None

    deepest = frame[LAYERS[::-1]].astype(str)
    resource = deepest.iloc[:, 0].copy()
    for column in deepest.columns[1:]:
        resource = resource.where(resource != '', deepest[column])
    frame['resource'] = resource.fillna('')
    frame['depth'] = (frame[LAYERS].astype(str) != '').sum(axis=1)
    keys = ['Stock/Flow ID', 'Year', 'resource']
    frame = frame[frame['depth'] == frame.groupby(keys)['depth'].transform('min')]

    out = (frame[frame['resource'] != '']
           .groupby(['Year', 'resource'], as_index=False)['mean'].sum())
    out['Year'] = out['Year'].astype(int)
    return out


def figure_stock(element: str, kind: str, phrase: str, series: list,
                 scenario: str, unit: str, theme: str):
    """
    One resource, one question, the four routes as lines.

    Two panels, because a total and a rate are different quantities: what has
    {phrase} ALTOGETHER since 2020 above, and what does so each year below.

    ⚠️ THE CUMULATIVE PANEL CARRIES NO BAND. Means add, so a running sum of
    means is exact; percentiles do not, so a running sum of percentiles is not
    an interval of anything. The annual panel bands what it honestly can.
    """
    scale = factor(unit, AXIS_UNIT)
    fig, axes, colours = chart(1180, 940, theme, 2, 1)
    total, annual = axes.ravel()

    for place, (name, frame) in enumerate(series):
        colour = COLOURS[place % len(COLOURS)]
        years = frame['Year'].to_numpy()
        values = frame['mean'].to_numpy() * scale
        total.plot(years, np.cumsum(values), color=colour, linewidth=2.6,
                   solid_capstyle='round',
                   label=f'{name}   {np.cumsum(values)[-1]:,.1f} {AXIS_UNIT}')
        if {'p2.5', 'p97.5'} <= set(frame.columns):
            annual.fill_between(years, frame['p2.5'] * scale,
                                frame['p97.5'] * scale, color=colour,
                                alpha=0.12, linewidth=0, zorder=1)
        annual.plot(years, values, color=colour, linewidth=2.6, zorder=3,
                    solid_capstyle='round', label=name)

    banded = {'p2.5', 'p97.5'} <= set(series[0][1].columns)
    total.set_ylabel(f'{element} {kind} in total ({AXIS_UNIT})',
                     color=colours['title'], fontsize=14)
    annual.set_ylabel(f'{element} {kind} per year ({AXIS_UNIT}/year)',
                      color=colours['title'], fontsize=14)
    for panel in (total, annual):
        panel.set_xlabel('year', color=colours['meta'], fontsize=13)
        panel.set_ylim(bottom=0)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)
        panel.tick_params(labelsize=13)
        panel.legend(fontsize=11.5, frameon=False, loc='upper left')

    drawn = heading(
        total, f'{element}: what {phrase}, by route',
        f'grade {scenario}.  above: added up from 2020; below: each year.  '
        + ("the band is that route's own 95%, on the annual panel only -- "
           'percentiles do not add, so a running sum of them would be an '
           'interval of nothing.  '
           if banded else 'MEANS ONLY: several loss flows feed one resource '
           'and their percentiles do not add.  ')
        + 'NO TOTAL: the routes are alternatives for the same motors.',
        colours)
    fig.subplots_adjust(top=0.88 - 0.022 * drawn, left=0.10, right=0.98,
                        bottom=0.08, hspace=0.30)
    return fig


def figure(element: str, series: list, scenario: str, unit: str, theme: str):
    """One rare earth, the routes as lines, each with its own 95% band."""
    scale = factor(unit, AXIS_UNIT)
    fig, panel, colours = chart(1180, 700, theme)

    for place, (name, frame) in enumerate(series):
        colour = COLOURS[place % len(COLOURS)]
        years = frame['Year'].to_numpy()
        panel.fill_between(years, frame['p2.5'] * scale, frame['p97.5'] * scale,
                           color=colour, alpha=0.12, linewidth=0, zorder=1)
        panel.plot(years, frame['mean'] * scale, color=colour, linewidth=2.6,
                   zorder=3, solid_capstyle='round', label=name)

    panel.set_ylabel(f'{element} recovered per year ({AXIS_UNIT}/year)',
                     color=colours['title'], fontsize=15)
    panel.set_xlabel('year', color=colours['meta'], fontsize=15)
    panel.set_ylim(bottom=0)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)
    panel.tick_params(labelsize=14)
    panel.legend(fontsize=12, frameon=False, loc='upper left')

    # `label` lays text out in the point coordinates `canvas` uses; this is a
    # `chart`, so the title goes on the axes in their own fraction coordinates.
    drawn = heading(
        panel, f'{element}: the four recovery routes compared',
        f'grade {scenario}.  Monte Carlo, band is the 95% interval of each '
        f"route's own draws.  NO TOTAL: the routes are alternatives for the "
        f'same motors, so they are not added.', colours)
    fig.subplots_adjust(top=0.90 - 0.035 * drawn, left=0.09, right=0.98,
                        bottom=0.11)
    return fig


def main() -> int:
    params = current()
    scenarios = sorted({name for case, _ in ROUTES
                        for name in os.listdir(os.path.join(case, 'output_data'))
                        if os.path.isdir(os.path.join(case, 'output_data', name))})
    if not scenarios:
        print('No output_data/<scenario>/ folders. Run 03 first.', file=sys.stderr)
        return 1

    written = 0
    for scenario in scenarios:
        sheets = [(name, recovered_sheet(case, scenario))
                  for case, name in ROUTES]
        sheets = [(name, frame) for name, frame in sheets if frame is not None]
        if not sheets:
            continue
        for element in REE:
            series = [(name, frame[frame['resource'] == element].sort_values('Year'))
                      for name, frame in sheets]
            series = [(name, frame) for name, frame in series if len(frame)]
            if not series:
                continue
            fig = figure(element, series, scenario, params.run.working_unit,
                         params.figures.theme)
            out = os.path.join(params.figures.out_dir, 'routes', scenario)
            for path in write(fig, out, element, params.figures.enabled(),
                              params.figures.dpi, essential=True):
                print(f'  wrote {path}')
                written += 1

        # ---- and the two questions each route answers differently ------
        lost = [(name, lost_sheet(case, scenario)) for case, name in ROUTES]
        lost = [(name, frame) for name, frame in lost if frame is not None]
        for resource in RESOURCES:
            for stem, kind, phrase in STOCKS:
                source = sheets if stem == 'recovered' else lost
                series = [(name, frame[frame['resource'] == resource]
                           .sort_values('Year'))
                          for name, frame in source]
                series = [(name, frame) for name, frame in series if len(frame)]
                if not series:
                    continue
                fig = figure_stock(resource, kind, phrase, series, scenario,
                                   params.run.working_unit,
                                   params.figures.theme)
                out = os.path.join(params.figures.out_dir, 'routes', scenario)
                for path in write(fig, out, f'{resource}_{stem}',
                                  params.figures.enabled(), params.figures.dpi,
                                  essential=True):
                    print(f'  wrote {path}')
                    written += 1
                import matplotlib.pyplot as plt
                plt.close(fig)
    print(f'\n{written} figure(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
