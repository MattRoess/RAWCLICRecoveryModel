"""
src/report.py
=============

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

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

    NOT always Layer 4. 04_02 resolves elements within a placeholder material;
    04_01 stops at material, so Layer 4 is empty everywhere and Layer 3 is.

    ⚠️ ONE DEPTH FOR THE WHOLE CASE, which is why `recovered` no longer uses
    this. See `resource_of`.
    """
    for column in ('Layer 4', 'Layer 3', 'Layer 2'):
        if column in summary.columns and (summary[column] != '').any():
            return column
    return 'Layer 2'


def resource_of(frame: pd.DataFrame) -> pd.Series:
    """
    What each row is a quantity OF: the value of its own deepest filled layer.

    A CASE DOES NOT HAVE ONE DEPTH. The traction motor resolves the magnet to
    elements -- Nd, Pr, Dy, Tb at Layer 4 -- and copper, aluminium, steel and
    lamination to materials at Layer 3. Asking `finest_layer` for one answer
    gives Layer 4, because the rare earths fill it, and every metal row then
    has a blank in that column.

    2026-09-25: that is exactly what happened. Copper, aluminium and steel were
    solved correctly, reached their recovered flows, and were then dropped by a
    `summary[layer] != ''` filter before anything was reported -- 0.6% of the
    recovered mass was being shown. Copper alone is nineteen times the whole
    rare-earth output by weight and has its own figure upstream.

    Reading the depth PER ROW is the same rule the mass balance already uses:
    each flow totalled at its own depth, never at one depth chosen for all.
    """
    layers = [column for column in LAYERS if column in frame.columns]
    if not layers:
        return pd.Series([''] * len(frame), index=frame.index)
    # Deepest first, so the first non-empty value found is the row's own.
    deepest = frame[layers[::-1]].astype(str)
    out = deepest.iloc[:, 0].copy()
    for column in deepest.columns[1:]:
        out = out.where(out != '', deepest[column])
    return out.fillna('')


def recovered(summary: pd.DataFrame, tcs: pd.DataFrame, case: str,
              run=None) -> pd.DataFrame:
    """
    The headline: mass recovered per resource per year, at each row's own depth.

    Recovered means reaching a terminal flow that is not a loss. The gap to the
    deterministic run is given as a percentage of the mean, because that is the
    number that says whether the Monte Carlo changed the answer or only put
    error bars on it.

    INTERVALS COME FROM THE DRAWS WHEN A RESOURCE ARRIVES BY SEVERAL FLOWS.
    Adding the p50s of two flows does not give the median of their sum, and the
    same goes for the interval bounds -- only the mean adds. Where a group has
    one row the two agree exactly and the percentile columns are used directly;
    where it has more, `run` supplies the draws, they are summed per draw, and
    the percentiles are taken from that. The split case needs this: it sends the
    magnet down both loops, so every rare earth arrives by two flows.

    Without `run` a multi-row group cannot be done correctly, so its interval is
    left empty rather than filled with a number that adds percentiles.
    """
    # Which flows count as recovered is stated in processes.csv, not guessed
    # from the name -- a handoff to a separate recovery model is neither
    # recovered here nor lost (src/rest.py, ROLES).
    from src.rest import recovered_flows
    keep = recovered_flows(case, tcs)

    frame = summary[summary['Stock/Flow ID'].isin(keep)].copy()
    frame['resource'] = resource_of(frame)
    frame = frame[frame['resource'] != '']

    # Position in the draw array, for the groups that need it. `summarise`
    # builds the summary from `run.keys` in order, so row i of the summary is
    # row i of `run.values`; the merge that adds `deterministic` is a left join
    # on unique keys and keeps that order.
    draws = None
    if run is not None and getattr(run, 'values', None) is not None:
        if len(run.values) == len(summary):
            draws = run.values
            frame['position'] = [summary.index.get_loc(i) for i in frame.index]

    rows = []
    for (year, resource), group in frame.groupby(['Year', 'resource']):
        mean = group['mean'].sum()
        point = group['deterministic'].sum()
        if len(group) == 1 or draws is None:
            low, mid, high = (group['p2_5'].sum(), group['p50'].sum(),
                              group['p97_5'].sum())
            exact = len(group) == 1
        else:
            total = draws[group['position'].to_numpy()].sum(axis=0)
            low, mid, high = np.percentile(total, [2.5, 50, 97.5])
            exact = True
        rows.append({
            'Year': year, 'resource': resource, 'flows': len(group),
            'mean': mean, 'p2.5': low if exact else np.nan,
            'p50': mid if exact else np.nan,
            'p97.5': high if exact else np.nan,
            'deterministic': point,
            'deterministic vs mean %': (100.0 * (point - mean) / mean) if mean else np.nan,
            'relative spread %': (100.0 * (high - low) / mean)
                                 if mean and exact else np.nan,
        })
    return pd.DataFrame(rows).sort_values(['resource', 'Year'])


def contributions(summary: pd.DataFrame, tcs: pd.DataFrame, case: str,
                  run=None) -> pd.DataFrame:
    """
    WHAT MADE UP EACH TOTAL: one row per contributing flow, not per resource.

    `recovered` answers "how much Nd came back". This answers "from where" --
    the split case recovers Nd down both loops and the headline total says only
    that it arrived, which is the question asked on 2026-09-25: "I want to know,
    what contributed to the total!!".

    Each row carries the feeding flow as well as the recovered one, so the chain
    is readable without opening the coefficient table: F_recycled_magnet is
    reached from F_magnet_short, F_nd from F_ree_oxides.

    THE SHARE IS OF MEANS, and means add exactly -- that is the one central
    value that does. The intervals are each flow's own; they are NOT shares and
    do not sum to the total's interval, which is why the total is reported by
    `recovered` from the summed draws rather than from this sheet.
    """
    from src.rest import recovered_flows
    keep = recovered_flows(case, tcs)

    frame = summary[summary['Stock/Flow ID'].isin(keep)].copy()
    frame['resource'] = resource_of(frame)
    frame = frame[frame['resource'] != '']

    # Which flow feeds each recovered one. A recovered flow reached from two
    # different places for the SAME resource cannot be told apart in this
    # table, so say so rather than printing one of them.
    feeds = {}
    for (target, key), group in tcs.groupby(['Output_FlowID', 'TC_target_key']):
        sources = sorted(set(group['Input_FlowID']))
        feeds[(target, key)] = (sources[0] if len(sources) == 1
                                else ' + '.join(sources))

    totals = frame.groupby(['Year', 'resource'])['mean'].sum()
    rows = []
    for _, row in frame.iterrows():
        whole = totals.get((row['Year'], row['resource']), 0.0)
        rows.append({
            'Year': row['Year'], 'resource': row['resource'],
            'recovered flow': row['Stock/Flow ID'],
            'fed by': feeds.get((row['Stock/Flow ID'], row['resource']), ''),
            'mean': row['mean'],
            'share of total %': (100.0 * row['mean'] / whole) if whole else np.nan,
            'p2.5': row['p2_5'], 'p50': row['p50'], 'p97.5': row['p97_5'],
            'deterministic': row['deterministic'],
        })
    out = pd.DataFrame(rows)
    return out.sort_values(['resource', 'Year', 'recovered flow']) if len(out) else out


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
        'Recovered': recovered(summary, tcs, case or params.run.data_folder,
                               run=run),
        'Contributions': contributions(summary, tcs,
                                       case or params.run.data_folder),
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
