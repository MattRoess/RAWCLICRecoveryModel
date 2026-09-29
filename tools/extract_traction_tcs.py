"""
tools/extract_traction_tcs.py -- the study's coefficients, every one referenced.

    ./.venv/bin/python tools/extract_traction_tcs.py

⚠️ SO THAT EVERY NUMBER CAN BE CHECKED AGAINST THE DOCUMENT IT CAME FROM.
Asked for on 2026-09-29: *"I want to see a full overview of the processes and
the transfer coefficients, so I can verify what you use"*, and *"everything
which is in the document with the transfer coefficient has to be properly
referenced"*.

It reads `documentation/TractionMotorStudy/RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx`
-- the workbook itself, now inside the project -- and writes one row per
(horizon, route, step, material) with the workbook's own Min | Mode | Max, its
reliability rating, its note, AND its `Ref #` numbers RESOLVED against the
References sheet: author, year, title and DOI.

Nothing is interpreted here and nothing is filled in. A cell the workbook
leaves as `NR` or blank stays that way, because the report's finding 9 is that
no evidence-supported full-chain TC exists for either horizon and the gaps are
part of what has to be visible.

Two files, both in `documentation/`:

    traction_transfer_coefficients.csv   one row per coefficient, for checking
    TRACTION_COEFFICIENTS.md             the same, readable, with the sources
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bootstrap import ensure_venv

ensure_venv()

BOOK = ('documentation/TractionMotorStudy/'
        'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx')
SHEETS = [('2030', 'disassembly', 'TC_2030_Disassembly_Route'),
          ('2030', 'shredder', 'TC_2030_Shredder_Route'),
          ('2060', 'disassembly', 'TC_2060_Disassembly_Route'),
          ('2060', 'shredder', 'TC_2060_Shredder_Route')]
COLUMNS = ['Step #', 'Step Name', 'Material', 'TC Min', 'TC Mode', 'TC Max',
           'Loss (Mode)', 'Units', 'Ref #', 'Rel. %', 'Notes']


def header_row(frame: pd.DataFrame) -> int:
    """The row that names the columns. The sheets carry a title above it."""
    for index in range(len(frame)):
        if str(frame.iloc[index, 0]).strip() == 'Step #':
            return index
    raise SystemExit('no `Step #` header found -- the workbook changed shape')


def references() -> dict:
    """{ref number: one line naming author, year, title and DOI}."""
    raw = pd.read_excel(BOOK, sheet_name='References', header=None)
    start = next(i for i in range(len(raw))
                 if str(raw.iloc[i, 0]).strip() == 'Ref #')
    table = raw.iloc[start + 1:].copy()
    table.columns = list(raw.iloc[start])[:len(table.columns)]
    out = {}
    for _, row in table.iterrows():
        number = str(row['Ref #']).strip()
        if not number or number == 'nan':
            continue
        number = number.split('.')[0]
        author = str(row.get('Author(s) / Source', '')).strip()
        year = str(row.get('Year', '')).strip().split('.')[0]
        title = str(row.get('Title / Description', '')).strip()
        where = str(row.get('DOI or URL', '')).strip()
        out[number] = ' '.join(
            part for part in (f'{author} ({year}).' if author else '',
                              title, f'-- {where}' if where and where != 'nan'
                              else '') if part).strip()
    return out


def resolved(refs: str, table: dict) -> str:
    """`6,7,8,9` -> the four citations, joined. Unknown numbers say so."""
    numbers = [n for n in re.split(r'[,;/]\s*', str(refs)) if n.strip().isdigit()]
    if not numbers:
        return ''
    return ' | '.join(table.get(n, f'[ref {n} not in the References sheet]')
                      for n in numbers)


def main() -> int:
    if not os.path.exists(BOOK):
        raise SystemExit(f'{BOOK} is not there.')
    table = references()
    rows = []
    for horizon, route, sheet in SHEETS:
        raw = pd.read_excel(BOOK, sheet_name=sheet, header=None)
        start = header_row(raw)
        frame = raw.iloc[start + 1:].copy()
        frame.columns = (list(raw.iloc[start])[:frame.shape[1]])
        for _, row in frame.iterrows():
            step = str(row.get('Step #', '')).strip()
            if not step or step == 'nan':
                continue
            rows.append({
                'horizon': horizon, 'route': route, 'sheet': sheet,
                'step': step.split('.')[0],
                'step_name': str(row.get('Step Name', '')).strip(),
                'material': str(row.get('Material', '')).strip(),
                'min': row.get('TC Min'), 'mode': row.get('TC Mode'),
                'max': row.get('TC Max'),
                'loss_mode': row.get('Loss (Mode)'),
                'units': str(row.get('Units', '')).strip(),
                'reliability': str(row.get('Rel. %', '')).strip(),
                'ref_numbers': str(row.get('Ref #', '')).strip(),
                'references': resolved(row.get('Ref #', ''), table),
                'note': str(row.get('Notes', '')).strip(),
            })

    out = pd.DataFrame(rows)
    csv = 'documentation/traction_transfer_coefficients.csv'
    out.to_csv(csv, index=False)

    lines = ['# Traction motor transfer coefficients, as the study gives them',
             '',
             'Generated by `tools/extract_traction_tcs.py` from',
             '`documentation/TractionMotorStudy/'
             'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx`.',
             'Nothing here is interpreted, filled in or rounded: it is the '
             'workbook,',
             'with every `Ref #` resolved against its References sheet.',
             '',
             f'{len(out)} coefficients, {out.step.nunique()} steps, '
             f'{out.material.nunique()} materials, '
             f'{len([r for r in table])} references.',
             '',
             '⚠️ The report’s own finding 9: *no evidence-supported '
             'full-chain TC exists',
             'for 2030 or 2060*. Its section 5.2 table is almost entirely '
             '`NR`, and the',
             'workbook fills those cells anyway, labelled as scenario '
             'assumptions. **Every',
             'coefficient below is a scenario assumption unless its reference '
             'says otherwise.**',
             '']
    for (horizon, route), block in out.groupby(['horizon', 'route'], sort=True):
        lines += [f'## {horizon} — {route} route', '',
                  '| step | process | material | min | mode | max | rel. | refs |',
                  '|---|---|---|---|---|---|---|---|']
        for _, row in block.iterrows():
            lines.append(
                f"| {row['step']} | {row['step_name']} | {row['material']} | "
                f"{row['min']} | {row['mode']} | {row['max']} | "
                f"{row['reliability']} | {row['ref_numbers']} |")
        lines.append('')
    lines += ['## The references, in full', '']
    for number in sorted(table, key=lambda n: int(n)):
        lines.append(f'**{number}.** {table[number]}')
        lines.append('')
    doc = 'documentation/TRACTION_COEFFICIENTS.md'
    open(doc, 'w', encoding='utf-8').write('\n'.join(lines))

    print(f'{csv}: {len(out)} coefficients')
    print(f'{doc}: {len(table)} references resolved')
    missing = out[out['references'] == '']
    print(f'  {len(missing)} coefficient(s) carry no reference number')
    return 0


if __name__ == '__main__':
    sys.exit(main())
