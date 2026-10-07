"""
Every transfer coefficient in the RAWCLIC recycling documents, as one table.

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

⚠️ THE POINT IS COMPLETENESS, NOT CONVENIENCE. The two case builders each take
the coefficients they need; this reads ALL of them, from every sheet, and marks
which are used. A coefficient that exists in the source and in no case then
shows up as `used_in = -` rather than being quietly absent.

Writes `documentation/recycling_coefficients.csv`.
"""
from pathlib import Path

import pandas as pd

BOOK = Path('/Users/rm/Downloads/TractionMotor/'
            'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx')

ROUTE_SHEETS = {
    'TC_2030_Disassembly_Route': ('2030', 'disassembly'),
    'TC_2060_Disassembly_Route': ('2060', 'disassembly'),
    'TC_2030_Shredder_Route':    ('2030', 'shredder'),
    'TC_2060_Shredder_Route':    ('2060', 'shredder'),
}

# Which steps each case actually consumes. Kept here rather than inferred, so
# that adding a step to a case without adding it here shows up as a mismatch.
USED = {
    ('disassembly', '1'): 'tractionmotor', ('disassembly', '2'): 'tractionmotor',
    ('disassembly', '3'): 'tractionmotor', ('disassembly', '4a'): 'tractionmotor',
    ('disassembly', '5'): 'tractionmotor', ('disassembly', '6b'): 'tractionmotor',
    ('disassembly', '7'): 'tractionmotor', ('disassembly', '8'): 'tractionmotor',
    ('disassembly', '9'): 'tractionmotor', ('disassembly', '10'): 'tractionmotor',
    ('disassembly', '11'): 'tractionmotor',
    ('disassembly', '6a/d'): 'not modelled: no 2030 coefficient',
    ('shredder', '1'): 'tractionmotor, head (step 1)',
    ('shredder', '2'): 'tractionmotor, shredder road',
    ('shredder', '3'): 'tractionmotor, shredder road',
    ('shredder', '3→6b'): 'tractionmotor, shredder road',
    # ⚠️ PATHWAY MODELLED, COEFFICIENT DELIBERATELY NOT TAKEN. The ferrous
    # stream exists in the case and ends at F_ree_in_steel, but this 0.01
    # "recoverable from the steel melt" is not applied: Matthias 2026-09-25,
    # material going to steel means the rare earth is lost. Recorded so the
    # extractor neither claims it is used nor reports it as overlooked.
    ('shredder', '4'): 'pathway modelled, coefficient not taken',
}


def route_rows() -> pd.DataFrame:
    rows = []
    for sheet, (horizon, route) in ROUTE_SHEETS.items():
        frame = pd.read_excel(BOOK, sheet_name=sheet, header=4)
        columns = list(frame.columns)
        # ⚠️ STOP AT THE FOOTER. Each route sheet ends with its own
        # 'OVERALL CHAIN TC' block, whose rows carry three numbers and parse as
        # step coefficients. Read as steps they made 26 of 28 entries in the
        # "in the source and in no case" list, burying the two that really are
        # missing.
        marker = frame[columns[0]].astype(str).str.contains(
            'OVERALL CHAIN', case=False, na=False)
        if marker.any():
            frame = frame.loc[:marker.idxmax() - 1]
        frame = frame.dropna(subset=[columns[3]])
        for _, row in frame.iterrows():
            step = str(row[columns[0]]).strip()
            if step.lower().startswith(('material', 'nan')) or not step:
                continue
            note = str(row[columns[10]]) if len(columns) > 10 else ''
            rows.append({
                'horizon': horizon, 'route': route, 'step': step,
                'step_name': str(row[columns[1]]).strip(),
                'material': str(row[columns[2]]).strip(),
                'min': row[columns[3]], 'mode': row[columns[4]],
                'max': row[columns[5]],
                'used_in': USED.get((route, step), '-'),
                'sheet': sheet,
                'note': note[:160] if note != 'nan' else '',
            })
    return pd.DataFrame(rows)


def chain_rows() -> pd.DataFrame:
    """The stated end-to-end chains, which the cases are checked against."""
    frame = pd.read_excel(BOOK, sheet_name='Process Comparison', header=None)
    rows = []
    block = frame.iloc[14:19]                      # Table 2, per element
    for _, row in block.iterrows():
        element = str(row[0]).strip()
        if element in ('nan', ''):
            continue
        for horizon, route, column in [('2030', 'disassembly', 1),
                                       ('2030', 'shredder', 2),
                                       ('2060', 'disassembly', 3),
                                       ('2060', 'shredder', 4)]:
            rows.append({'horizon': horizon, 'route': route, 'step': 'CHAIN',
                         'step_name': 'stated full chain',
                         'material': element, 'min': None,
                         'mode': row[column], 'max': None,
                         'used_in': 'verification only', 'sheet': 'Process Comparison',
                         'note': 'the number each case is checked against'})
    block = frame.iloc[22:26]                      # Table 3, non-magnet
    for _, row in block.iterrows():
        material = str(row[0]).strip()
        if material in ('nan', ''):
            continue
        for horizon, route, lo, mid, hi in [('2030', 'disassembly', 1, 2, 3),
                                            ('2030', 'shredder', 4, 5, 6),
                                            ('2060', 'disassembly', 7, 8, 9)]:
            rows.append({'horizon': horizon, 'route': route, 'step': 'CHAIN',
                         'step_name': 'stated full chain',
                         'material': material, 'min': row[lo],
                         'mode': row[mid], 'max': row[hi],
                         'used_in': 'verification only',
                         'sheet': 'Process Comparison',
                         'note': 'the number each case is checked against'})
    return pd.DataFrame(rows)


def main() -> None:
    table = pd.concat([route_rows(), chain_rows()], ignore_index=True)
    out = Path('documentation/recycling_coefficients.csv')
    table.to_csv(out, index=False)

    steps = table[table.step != 'CHAIN']
    unused = steps[steps.used_in == '-']
    print(f'{out}: {len(table)} rows '
          f'({len(steps)} step coefficients, {len(table) - len(steps)} stated chains)')
    print(f'\nsteps by route and horizon:')
    print(steps.groupby(['route', 'horizon']).size().to_string())
    print(f'\n⚠️  {len(unused)} step coefficient(s) in the source and in NO case:')
    for _, row in unused.iterrows():
        print(f'    {row.horizon} {row.route:12} step {row.step:6} '
              f'{row.material:22} {row["min"]} | {row["mode"]} | {row["max"]}')
        print(f'        {row.step_name}')


if __name__ == '__main__':
    main()
