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
    panel.text(0.0, 1.10, f'{element}: the four recovery routes compared',
               transform=panel.transAxes, fontsize=17, fontweight='bold',
               color=colours['title'], va='center', parse_math=False)
    panel.text(0.0, 1.045,
               f'grade {scenario}.  Monte Carlo, band is the 95% interval of '
               f"each route's own draws.  NO TOTAL: the routes are "
               f'alternatives for the same motors, so they are not added.',
               transform=panel.transAxes, fontsize=11.5,
               color=colours['sub'], va='center', parse_math=False)
    fig.subplots_adjust(top=0.84, left=0.09, right=0.98, bottom=0.11)
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
                              params.figures.dpi):
                print(f'  wrote {path}')
                written += 1
    print(f'\n{written} figure(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
