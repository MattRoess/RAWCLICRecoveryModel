"""
tools/check_ratios.py -- does the fleet case agree with the review?

    ./.venv/bin/python tools/check_ratios.py

ONE FIGURE, ONE QUESTION. The fleet case blends two routes whose end-to-end
coefficients the review publishes. So its ratio must sit BETWEEN them, at the
place the disassembly share puts it:

    expected  =  d x disassembly  +  (1 - d) x shredder

The figure draws the model's own recovered/collected per year, the review's two
anchors at 2030 and 2060, and that expectation. If the line does not land on
the expectation, either the case or the blend is wrong -- and the figure says
which way it is off rather than leaving it to be taken on trust.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bootstrap import ensure_venv

ensure_venv()

from src.figure_style import PALETTE, chart, write
from src.params_schema import current

# ⚠️ THE REVIEW'S OWN END-TO-END COEFFICIENTS, typed from
# RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx (TC_2030 / TC_2060, both route
# sheets). They are the thing being checked against, so they are not computed
# from the case -- that would be the case checking itself.
#
# The 2030 shredder magnet value is 0.0157, not the sheet's 0.02: that cell
# quotes the STEP as if it were the chain, while the same sheet applies capture
# and feed to copper, aluminium and steel, and the 2060 sheet applies them to
# the magnet too. See tools/build_tractionmotor_shredder_case.py.
REVIEW = {
    'Nd':         {'dis': (0.41, 0.65), 'shr': (0.0157, 0.265)},
    'Pr':         {'dis': (0.41, 0.65), 'shr': (0.0157, 0.265)},
    'Dy':         {'dis': (0.41, 0.65), 'shr': (0.0157, 0.265)},
    'Tb':         {'dis': (0.41, 0.65), 'shr': (0.0157, 0.265)},
    'copper':     {'dis': (0.64, 0.74), 'shr': (0.59, 0.70)},
    'aluminium':  {'dis': (0.66, 0.76), 'shr': (0.61, 0.73)},
    'steel':      {'dis': (0.60, 0.71), 'shr': (0.72, 0.83)},
}
ANCHORS = (2030, 2060)
CASE = 'data_folder/tractionmotor_fleet'


def model_ratio(case: str, scenario: str) -> pd.DataFrame:
    """Recovered over collected, per resource per year, from the workbook."""
    from src.rest import recovered_flows
    from src import case_tables

    path = os.path.join(case, 'output_data', scenario, 'recovery_results.xlsx')
    if not os.path.exists(path):
        raise SystemExit(f'{path} is not there. Run 03_tractionmotors.py.')

    layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
    rows = pd.read_excel(path, sheet_name='Distribution').fillna('')
    for column in layers:
        if column not in rows.columns:
            rows[column] = ''
    deepest = rows[layers[::-1]].astype(str)
    resource = deepest.iloc[:, 0].copy()
    for column in deepest.columns[1:]:
        resource = resource.where(resource != '', deepest[column])
    rows['resource'] = resource.fillna('')
    rows['depth'] = (rows[layers].astype(str) != '').sum(axis=1)
    keys = ['Stock/Flow ID', 'Year', 'resource']
    rows = rows[rows['depth'] == rows.groupby(keys)['depth'].transform('min')]

    keep = set(recovered_flows(case, case_tables.read(case, 'TCs')))
    back = (rows[rows['Stock/Flow ID'].isin(keep)]
            .groupby(['Year', 'resource'], as_index=False)['mean'].sum())
    into = (rows[rows['Stock/Flow ID'] == 'F_collected']
            .groupby(['Year', 'resource'], as_index=False)['mean'].sum())
    joined = back.merge(into, on=['Year', 'resource'], suffixes=('_back', '_in'))
    joined['ratio'] = 100 * joined['mean_back'] / joined['mean_in']
    return joined


def share_of(case: str) -> tuple[float, float]:
    """The disassembly share the case actually carries, both horizons."""
    from src import case_tables
    out = []
    for sheet in ('TCs', 'TCs_improved'):
        table = case_tables.read(case, sheet)
        row = table[(table['Output_FlowID'] == 'F_removed')
                    & (table['TC_target_key'].astype(str) == 'magnet')]
        out.append(float(row['value'].iloc[0]))
    return out[0], out[1]


def main() -> int:
    params = current()
    scenario = params.run.scenario or 'mix'
    ratios = model_ratio(CASE, scenario)
    share = share_of(CASE)

    resources = [r for r in REVIEW if r in set(ratios['resource'])]
    figure, panel, colours = chart(1200, 760, params.figures.theme)

    print(f'{"resource":12s} {"year":>6s} {"model":>8s} {"expected":>9s} {"gap":>8s}')
    worst = 0.0
    for place, resource in enumerate(resources):
        colour = PALETTE[place % len(PALETTE)]
        here = ratios[ratios['resource'] == resource].sort_values('Year')
        panel.plot(here['Year'], here['ratio'], color=colour, linewidth=2.4,
                   marker='o', markersize=3.5, label=resource)
        for index, year in enumerate(ANCHORS):
            dis, shr = REVIEW[resource]['dis'][index], REVIEW[resource]['shr'][index]
            expected = 100 * (share[index] * dis + (1 - share[index]) * shr)
            panel.plot([year], [expected], marker='_', markersize=26,
                       markeredgewidth=3.0, color=colour, zorder=5)
            got = here[here['Year'] == year]['ratio']
            if len(got):
                gap = float(got.iloc[0]) - expected
                worst = max(worst, abs(gap))
                print(f'{resource:12s} {year:6d} {float(got.iloc[0]):7.1f}% '
                      f'{expected:8.1f}% {gap:+7.1f} pp')

    panel.set_ylabel('recovered, % of what reached a recycler',
                     color=colours['title'], fontsize=14)
    panel.set_xlabel('year', color=colours['meta'], fontsize=13)
    panel.set_ylim(0, 100)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    panel.tick_params(labelsize=13)
    panel.legend(fontsize=12, frameon=False, loc='upper left', ncol=2)
    panel.text(0.0, 1.11, 'Does the fleet case agree with the review?',
               transform=panel.transAxes, fontsize=17, fontweight='bold',
               color=colours['title'], va='center', parse_math=False)
    panel.text(0.0, 1.045,
               f'lines: this model, grade {scenario}.  dashes at 2030 and '
               f'2060: the review’s own end-to-end coefficients blended at '
               f'this case’s disassembly share, {share[0]:.0%} and '
               f'{share[1]:.0%}.  worst gap {worst:.1f} pp.',
               transform=panel.transAxes, fontsize=11, color=colours['sub'],
               va='center', parse_math=False)
    figure.subplots_adjust(top=0.85, left=0.09, right=0.98, bottom=0.11)

    out = os.path.join(params.figures.out_dir, 'tractionmotor_fleet', scenario)
    for path in write(figure, out, 'agreement_with_the_review',
                      params.figures.enabled(), params.figures.dpi,
                      essential=True):
        print(f'\nwrote {path}')
    print(f'worst gap: {worst:.1f} percentage points')
    return 0


if __name__ == '__main__':
    sys.exit(main())
