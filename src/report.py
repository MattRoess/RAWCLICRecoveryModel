"""
src/report.py
=============

Everything the run produced, in one Excel workbook.

WHY A WORKBOOK AND NOT A CSV
----------------------------
A Monte Carlo result is not one table. It is a distribution per row, a set of
totals per element and per year, a mass balance that either closes or does not,
and a coefficient table whose provenance decides how much any of it is worth.
Those are separate sheets, and putting them in one file means the numbers and
the thing that produced them cannot drift apart.

THE SHEETS
----------
    Overview      what produced this run -- case, years, draws, seed, unit
    Recovered     the headline: mass recovered per element per year, with the
                  95% interval and how far the deterministic run sits from it
    By flow       where the mass ended up, per flow and year
    Mass balance  what entered against what left, per year
    Distribution  every result row: mean, mode, sd, the reported percentiles,
                  and a 23-point percentile grid -- the shape itself, in a form
                  something else can read back and sample from
    Coefficients  the TC table as used, including the `source` column
    Composition   what upstream handed over, for the years in this run

The `source` column is carried into Coefficients on purpose. A recovery number
computed from placeholders and one computed from measurements look identical in
a spreadsheet, and only one of them should be reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# Column widths that make the sheets readable without hand-fitting every time.
WIDTHS = {'Year': 8, 'Stock/Flow ID': 24, 'Layer 1': 10, 'Layer 2': 12,
          'Layer 3': 16, 'Layer 4': 10, 'element': 10, 'flow': 24,
          'source': 70, 'setting': 30, 'value': 46}


def terminal_flows(tcs: pd.DataFrame) -> set[str]:
    return set(tcs['Output_FlowID']) - set(tcs['Input_FlowID'])


def start_flows(tcs: pd.DataFrame) -> set[str]:
    return set(tcs['Input_FlowID']) - set(tcs['Output_FlowID'])


def _shallowest(frame: pd.DataFrame, column: str = 'mean') -> float:
    """
    Total a flow's rows without double counting.

    Rows are nested: an element row is part of its material row, so summing
    every depth counts the same mass up to four times. Each flow is totalled at
    its own shallowest depth, which is that flow's own aggregate.
    """
    if frame.empty:
        return 0.0
    depth = (frame[LAYERS] != '').sum(axis=1)
    return float(frame[depth == depth.min()][column].sum())


def overview(params, run) -> pd.DataFrame:
    """What produced this run. First sheet, so a stray file can be identified."""
    report = run.report
    rows = [
        ('case', params.run.data_folder),
        ('scenario', params.run.scenario or 'BAU'),
        ('years', params.run.years or 'all available'),
        ('upstream flow', params.data.upstream_flow),
        ('domains', ', '.join(params.data.groups) or 'all'),
        ('draws', f'{run.draws:,}'),
        ('seed', params.monte_carlo.seed),
        ('unit', params.run.working_unit),
        ('engine', params.run.engine),
        ('constrained groups', f"{report.get('groups', 0)} summing to 1"),
        ('bounds clamped into [0,1]', len(report.get('clamped', []))),
        ('negative residuals', report.get('negative_residuals', 0)),
        ('', ''),
        ('WHAT THE INFLOW IS',
         'the electronics in the collected vehicles, not the vehicles'),
        ('WHY RECOVERY IS A LOWER BOUND',
         'unspecified material (`rest`) is treated as unrecovered'),
        ('CHECK THE SOURCE COLUMN',
         'coefficients marked PLACEHOLDER are not data'),
    ]
    return pd.DataFrame(rows, columns=['setting', 'value'])


from src.rest import drop_unused_layers


def finest_layer(summary: pd.DataFrame) -> str:
    """
    The deepest layer this case actually resolves.

    NOT always Layer 4. 04_02 resolves elements within a placeholder material,
    so Layer 4 is the answer; 04_01 stops at material, so Layer 4 is empty
    everywhere and Layer 3 is. Assuming Layer 4 gave an empty headline sheet
    and a KeyError rather than a wrong number, which is the good failure, but
    reading it from the data is the right one.
    """
    for column in ('Layer 4', 'Layer 3', 'Layer 2'):
        if column in summary.columns and (summary[column] != '').any():
            return column
    return 'Layer 2'


def recovered(summary: pd.DataFrame, tcs: pd.DataFrame, case: str) -> pd.DataFrame:
    """
    The headline: recovered mass per resource per year, at the finest layer the
    case resolves -- element for 04_02, material for 04_01.

    Recovered means reaching a terminal flow that is not a loss. The gap to the
    deterministic run is given as a percentage of the mean, because that is the
    number that says whether the Monte Carlo changed the answer or only put
    error bars on it.
    """
    # Which flows count as recovered is stated in processes.csv, not guessed
    # from the name -- a handoff to a separate recovery model is neither
    # recovered here nor lost (src/rest.py, ROLES).
    from src.rest import recovered_flows
    keep = recovered_flows(case, tcs)

    layer = finest_layer(summary)
    label = {'Layer 4': 'element', 'Layer 3': 'material'}.get(layer, 'component')

    rows = []
    for (year, resource), group in summary[
            summary['Stock/Flow ID'].isin(keep) & (summary[layer] != '')
            ].groupby(['Year', layer]):
        mean = group['mean'].sum()
        point = group['deterministic'].sum()
        rows.append({
            'Year': year, label: resource,
            'mean': mean, 'p2.5': group['p2_5'].sum(), 'p50': group['p50'].sum(),
            'p97.5': group['p97_5'].sum(),
            'deterministic': point,
            'deterministic vs mean %': (100.0 * (point - mean) / mean) if mean else np.nan,
            'relative spread %': (100.0 * (group['p97_5'].sum() - group['p2_5'].sum()) / mean)
                                 if mean else np.nan,
        })
    return pd.DataFrame(rows).sort_values([label, 'Year'])


def by_flow(summary: pd.DataFrame) -> pd.DataFrame:
    """Where the mass ended up: one row per flow and year, totalled honestly."""
    rows = []
    for (year, flow), group in summary.groupby(['Year', 'Stock/Flow ID']):
        rows.append({'Year': year, 'flow': flow,
                     'mean': _shallowest(group),
                     'p2.5': _shallowest(group, 'p2_5'),
                     'p50': _shallowest(group, 'p50'),
                     'p97.5': _shallowest(group, 'p97_5'),
                     'deterministic': _shallowest(group, 'deterministic')})
    return pd.DataFrame(rows).sort_values(['Year', 'flow'])


def mass_balance(summary: pd.DataFrame, tcs: pd.DataFrame) -> pd.DataFrame:
    """What entered against what left, per year. The check that it means anything."""
    starts, ends = start_flows(tcs), terminal_flows(tcs)
    rows = []
    for year, group in summary.groupby('Year'):
        entering = sum(_shallowest(group[group['Stock/Flow ID'] == f]) for f in starts)
        leaving = sum(_shallowest(group[group['Stock/Flow ID'] == f]) for f in ends)
        rows.append({'Year': year, 'in': entering, 'out': leaving,
                     'residual': entering - leaving,
                     'relative residual': (entering - leaving) / entering if entering else 0.0})
    return pd.DataFrame(rows)


def write(path: str, params, run, summary: pd.DataFrame, tcs: pd.DataFrame,
          composition: pd.DataFrame, case: str = '') -> list[str]:
    """Write the workbook. Returns the sheet names written."""
    sheets = {
        'Overview': overview(params, run),
        'Recovered': recovered(summary, tcs, case or params.run.data_folder),
        'By flow': by_flow(summary),
        'Mass balance': mass_balance(summary, tcs),
        'Distribution': drop_unused_layers(summary),
        'Coefficients': tcs,
        'Composition': drop_unused_layers(composition),
    }

    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            # Freeze the header and size the columns, so the file opens usable
            # rather than as a wall of ####.
            sheet.freeze_panes = 'A2'
            for position, column in enumerate(frame.columns, start=1):
                width = WIDTHS.get(str(column))
                if width is None:
                    longest = frame[column].astype(str).str.len().max() if len(frame) else 0
                    width = int(min(max(len(str(column)) + 2, longest + 2), 18))
                sheet.column_dimensions[
                    sheet.cell(row=1, column=position).column_letter].width = width
                if frame[column].dtype.kind == 'f':
                    for cell in sheet[sheet.cell(row=1, column=position).column_letter][1:]:
                        cell.number_format = '#,##0.000'

    return list(sheets)
