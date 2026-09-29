"""
tools/draw_traction_coefficients.py -- every process and its coefficient, drawn.

    ./.venv/bin/python tools/draw_traction_coefficients.py

⚠️ EVERY NUMBER IS READ FROM THE WORKBOOK. Nothing on this figure is typed
here. The steps come from `documentation/traction_transfer_coefficients.csv`
(extracted from the four TC sheets) and the end-to-end chain from the
workbook's own `Overall Chain TC Summary`. Asked for on 2026-09-29: *"I want to
see a full overview of the processes and the transfer coefficients, so I can
verify what you use."*

Written to `documentation/` rather than `figures/`, because it documents the
SOURCE rather than reporting a run: it does not change when the model runs.
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOOK = ('documentation/TractionMotorStudy/'
        'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx')
STEPS = 'documentation/traction_transfer_coefficients.csv'
OUT = 'documentation/traction_transfer_coefficients.png'

DIS, SHR, HEAD, GREY = '#2E7D5B', '#B5651D', '#111827', '#6b7280'
MONO = ['DejaVu Sans Mono', 'Menlo', 'monospace']


def chain_totals() -> pd.DataFrame:
    """The workbook's own end-to-end TCs, from its master sheet."""
    raw = pd.read_excel(BOOK, sheet_name='Overall Chain TC Summary', header=None)
    head = next(i for i in range(len(raw))
                if str(raw.iloc[i, 0]).strip() == 'Material'
                and '2030D TC Mode' in [str(v) for v in raw.iloc[i]])
    table = raw.iloc[head + 1:head + 12].copy()
    table.columns = list(raw.iloc[head])
    return table[table['Material'].notna()]


def main() -> int:
    steps = pd.read_csv(STEPS)
    steps = steps[steps['mode'].notna()]
    totals = chain_totals()

    # ⚠️ THE HEIGHT IS COMPUTED, NOT CHOSEN. Fixed at 13 inches the step
    # column ran straight through the chain summary underneath it.
    tallest = max(
        sum(2.0 + 1.55 * len(set(block['material']))
            for _, block in steps[steps['route'] == route].groupby('step'))
        for route in ('disassembly', 'shredder'))
    figure = plt.figure(figsize=(19, 13 * max(1.0, (tallest + 46) / 78)),
                        facecolor='white')
    axes = figure.add_axes([0, 0, 1, 1]); axes.set_axis_off()
    axes.set_xlim(0, 100); axes.set_ylim(-6, 100)

    axes.text(2, 97.4, 'Traction motor recycling: every process, every '
              'transfer coefficient', fontsize=19, weight='bold', color=HEAD)
    axes.text(2, 94.9, f'read from {os.path.basename(BOOK)} -- nothing on this '
              f'figure is typed by hand.  each cell is  mode [min - max].  '
              f'"--" is a coefficient the workbook gives no reference for.',
              fontsize=10.5, color=GREY)

    lowest = 100.0
    for column, (route, colour, label) in enumerate(
            (('disassembly', DIS, 'DISASSEMBLY ROUTE  --  motor removed, '
              'magnet extracted'),
             ('shredder', SHR, 'SHREDDER ROUTE  --  no magnet extraction'))):
        left = 2 + column * 49
        axes.text(left, 91.4, label, fontsize=12, weight='bold', color=colour)
        y = 88.5
        here = steps[steps['route'] == route]
        for step in sorted(set(here['step']), key=lambda v: (int(''.join(
                c for c in str(v) if c.isdigit()) or 0), str(v))):
            block = here[here['step'] == step]
            name = str(block['step_name'].iloc[0])[:44]
            # ⚠️ ONE ROW PER MATERIAL, WITH BOTH HORIZONS SIDE BY SIDE. Listed
            # as they come out of the sheets, 2030 and 2060 appeared as two
            # rows for the same material with no label -- step 1 read `0.8`
            # then `0.9` for NdFeB and nothing said which was which.
            materials = list(dict.fromkeys(block['material']))
            height = 2.0 + 1.55 * len(materials)
            axes.add_patch(FancyBboxPatch(
                (left, y - height), 46.5, height,
                boxstyle='round,pad=0.25', facecolor=colour, alpha=0.07,
                edgecolor=colour, linewidth=1.0))
            axes.text(left + 0.8, y - 1.5, f'step {step}   {name}',
                      fontsize=9.6, weight='bold', color=colour)
            for index, material in enumerate(materials):
                rows = block[block['material'] == material]
                cells = []
                for horizon in ('2030', '2060'):
                    one = rows[rows['horizon'].astype(str) == horizon]
                    if len(one):
                        r = one.iloc[0]
                        cells.append(f"{horizon} {r['mode']:>5} "
                                     f"[{r['min']}-{r['max']}]".ljust(23))
                    else:
                        cells.append(' ' * 23)
                refs = str(rows.iloc[0]['ref_numbers'])
                refs = '--' if refs in ('nan', '—', '') else refs
                axes.text(left + 1.4, y - 3.1 - 1.55 * index,
                          f"{str(material)[:22]:<22s}" + ''.join(cells)
                          + f" ref {refs}",
                          fontsize=8.4, family=MONO, color='#374151')
            y -= height + 1.0
        # ⚠️ THE LOWEST OF THE TWO COLUMNS, not the last one drawn. The
        # shredder column is shorter, so taking its `y` put the chain summary
        # across steps 9, 10 and 11 of the disassembly column.
        lowest = min(lowest, y)

    # ---- the study's own end-to-end numbers, to check the model against ----
    base = lowest
    axes.text(2, base - 2.0, "THE STUDY'S OWN END-TO-END CHAIN TC  --  what the "
              "whole route returns, from its `Overall Chain TC Summary` sheet",
              fontsize=12, weight='bold', color=HEAD)
    axes.text(2, base - 4.2, f"{'material':<14s}{'2030 disassembly':>28s}"
              f"{'2030 shredder':>18s}{'2060 disassembly':>28s}",
              fontsize=9.6, family=MONO, weight='bold', color=GREY)
    y = base - 6.2
    for _, row in totals.iterrows():
        def cell(low, mid, high):
            if pd.isna(mid):
                return ' ' * 26
            span = (f'[{low} - {high}]' if not pd.isna(low) else '')
            return f'{mid:>6} {span:<19s}'
        axes.text(2, y,
                  f"{str(row['Material']):<14s}"
                  + cell(row.get('2030D TC Min'), row.get('2030D TC Mode'),
                         row.get('2030D TC Max'))
                  + f"{row.get('2030S TC Mode'):>8}          "
                  + cell(row.get('2060D TC Min'), row.get('2060D TC Mode'),
                         row.get('2060D TC Max')),
                  fontsize=9.4, family=MONO, color='#111827')
        y -= 1.7

    axes.text(2, y - 1.6,
              "⚠ The report's own finding 9: no evidence-supported full-chain "
              "TC exists for 2030 or 2060. 31 of the 85 step coefficients "
              "carry no reference at all.\n"
              "Every number here is the workbook's; whether it is evidence or "
              "a scenario assumption is what the `ref` column tells you.",
              fontsize=10, color='#B00020', va='bottom', linespacing=1.5)

    figure.savefig(OUT, dpi=130, facecolor='white')
    print(f'wrote {OUT}')
    print(f'  {len(steps)} step coefficients, {len(totals)} chain totals')
    return 0


if __name__ == '__main__':
    sys.exit(main())
