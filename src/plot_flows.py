"""
Draw the flow network of a data folder as a Sankey diagram.

    ./.venv/bin/python plot_flows.py                       # the case in params_schema.py
    ./.venv/bin/python plot_flows.py data_folder/reference/basic_test

Everything about the output -- which formats, which resolution, which palette,
whether the per-element figures are drawn -- is a parameter in
`src/params_schema.py`, not a flag. Change it there.

Writes <out_dir>/<case>/total.<fmt> plus one figure per element, in every
format switched on by `figures.png`, `figures.svg` and `figures.pdf`. Rendering goes through matplotlib, so all
formats come from one drawing and cannot disagree.

Two things this has to get right, both of which a naive script gets wrong:

  * Rows are NESTED. A row at element depth is part of its material row, not an
    addition to it, so summing a flow's Value column counts the same mass up to
    four times. Totals are taken at one depth only -- the shallowest depth the
    flow actually has, since flows are truncated at the layer their TC targeted
    (see documentation/MODEL_MECHANICS.md).

  * Edge magnitudes are not in the solution file, which records the state of
    each flow rather than the transfer between them. They are recomputed here
    by replaying the model's own process loop, so the picture cannot drift from
    what the model actually does.
"""
import os

import pandas as pd
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

from src.figure_style import PALETTE, canvas, folder_for, label, write
from src.params_schema import Params, current
from src.recovery_model_optimized import RecoveryModelOptimized

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
LAYER_NAMES = ['product', 'component', 'material', 'element']


def depth_of(frame: pd.DataFrame) -> pd.Series:
    """How many layer columns a row populates. 1 = product, 4 = element."""
    return (frame[LAYERS] != '').sum(axis=1)


def describe(entry: dict) -> str:
    """A combination as a person would name it: '2050', or '2050 / HIGH'."""
    parts = [str(entry[key]) for key in
             ('Year', 'Scenario', 'Location', 'additionalSpecification')
             if entry.get(key) not in (None, '')]
    return ' / '.join(parts) if parts else 'the only combination'


def chosen_entry(folder: str, tables: dict | None = None) -> tuple[str, int]:
    """
    Which combination the Sankeys describe, and how many there are.

    A Sankey is one snapshot, and a case can hold several years. The LAST is
    taken, not the first: every other output of a run is headlined on the last
    year of the selection, and a diagram quietly showing the first was the
    defect this replaced (DEFECTS.md section 3.7). Narrow `run.years` to draw a
    different one.
    """
    model = RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                                   tables=tables)
    return describe(model.input_data[-1]), len(model.input_data)


def unit_drawn(params: Params) -> str:
    """
    The unit the numbers on the figure are actually in.

    NOT the `Unit` column of the inputs table, which is the unit the source
    file declared -- kt, from upstream. The engine converts every inflow into
    `run.working_unit` on the way in, so a figure labelled from the source
    column was out by a factor of a million: aluminium in the 2030 electronics
    case printed as `887,760.1 kt` when it is 887,760 kg.
    """
    return params.run.working_unit


def replay(folder: str, tables: dict | None = None):
    """
    Re-run the model's process loop, recording the mass on every edge.

    Returns (edges, flows) where edges maps (source, target) -> dataframe of
    the transferred rows, and flows maps flow id -> dataframe of its contents.
    The combination replayed is the one `chosen_entry` names.
    """
    model = RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                                   tables=tables)
    entry = model.input_data[-1]
    inflows, composition, tcs = entry['inflows_df'], entry['composition_df'], entry['tcs_df']

    result = model.create_initial_flows(inflows_df=inflows, composition_df=composition)
    edges = {}
    for _, step in model.get_process_sequence_from_tcs(tcs).iterrows():
        source, target = step['Input_FlowID'], step['Output_FlowID']
        inflow = result[result['Stock/Flow ID'] == source].drop(columns=['Stock/Flow ID'])
        step_tcs = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        outflow = model.solve_process(process_tcs=step_tcs, process_inflow=inflow)
        edges[(source, target)] = outflow.copy()
        outflow['Stock/Flow ID'] = target
        result = pd.concat([result, outflow], ignore_index=True)

    result['Value'] = pd.to_numeric(result['Value'])
    flows = {flow: group for flow, group in result.groupby('Stock/Flow ID')}
    return edges, flows


def mass(frame: pd.DataFrame, element: str | None) -> float:
    """
    Total mass in a set of rows, without double counting the nesting.

    For an element figure, take element-depth rows for that element. Otherwise
    take the shallowest depth present, which is that flow's own aggregate.
    """
    if frame is None or len(frame) == 0:
        return 0.0
    frame = frame.copy()
    frame['Value'] = pd.to_numeric(frame['Value'])
    if element is not None:
        return float(frame.loc[frame['Layer 4'] == element, 'Value'].sum())
    depths = depth_of(frame)
    return float(frame.loc[depths == depths.min(), 'Value'].sum())


def assign_columns(nodes: list[str], links: list[tuple]) -> dict[str, int]:
    """Place each flow in a column: one further right than its furthest source."""
    column = {node: 0 for node in nodes}
    for _ in range(len(nodes)):
        changed = False
        for source, target, _ in links:
            if column[target] < column[source] + 1:
                column[target] = column[source] + 1
                changed = True
        if not changed:
            break
    return column


def render(nodes, links, column, title, subtitle, theme: str):
    """Lay out and draw the Sankey. Node height and ribbon width are mass."""
    width, height = 1180, 620
    left, right, top, bottom = 20, 150, 76, 30
    node_width, gap = 16, 16

    columns = {}
    for node in nodes:
        columns.setdefault(column[node], []).append(node)

    # Order the first column by size, then place each later column near the
    # average position of its sources. This barycentre pass is what stops the
    # ribbons crossing each other unnecessarily.
    order = {}
    for index in sorted(columns):
        if index == 0:
            columns[index].sort(key=lambda n: -nodes[n])
        else:
            def barycentre(node: str) -> float:
                sources = [order[s] for s, t, _ in links if t == node and s in order]
                return sum(sources) / len(sources) if sources else 0.0
            columns[index].sort(key=lambda n: (barycentre(n), -nodes[n]))
        for position, node in enumerate(columns[index]):
            order[node] = position

    usable = height - top - bottom
    tallest = max(sum(nodes[n] for n in group) for group in columns.values())
    busiest = max(len(group) for group in columns.values())
    scale = (usable - gap * (busiest - 1)) / tallest if tallest else 1

    span = (width - left - right - node_width) / max(1, max(columns) or 1)
    box, cursor = {}, {}
    for index, group in columns.items():
        y = top
        for node in group:
            size = max(nodes[node] * scale, 1.5)
            box[node] = (left + index * span, y, size)
            cursor[node] = {'out': y, 'in': y}
            y += size + gap

    figure, axes, colours = canvas(width, height, theme)
    label(axes, left, 24, title, 17, colours['title'], 'bold')
    label(axes, left, 48, subtitle, 12.5, colours['sub'])

    colour = {node: PALETTE[i % len(PALETTE)] for i, node in enumerate(sorted(nodes))}

    # Ribbons first, so nodes and labels sit on top. Each is a stroked curve
    # whose LINE WIDTH is the mass -- one data unit is one point, so a ribbon
    # of thickness t is exactly t points wide however the figure is written out.
    for source, target, value in sorted(links, key=lambda l: -l[2]):
        if value <= 0:
            continue
        thickness = max(value * scale, 0.8)
        x0 = box[source][0] + node_width
        x1 = box[target][0]
        y0 = cursor[source]['out'] + thickness / 2
        y1 = cursor[target]['in'] + thickness / 2
        cursor[source]['out'] += thickness
        cursor[target]['in'] += thickness
        mid = (x0 + x1) / 2
        ribbon = Path([(x0, y0), (mid, y0), (mid, y1), (x1, y1)],
                      [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
        axes.add_patch(PathPatch(ribbon, fill=False, edgecolor=colour[source],
                                 alpha=0.42, linewidth=thickness,
                                 capstyle='butt', joinstyle='round'))

    for node, (x, y, size) in box.items():
        axes.add_patch(Rectangle((x, y), node_width, size, facecolor=colour[node],
                                 edgecolor='none'))
        text_x = x + node_width + 7
        label(axes, text_x, y + size / 2 - 5, node, 12, colours['node'])
        label(axes, text_x, y + size / 2 + 8, f'{nodes[node]:,.1f}', 10.5, colours['meta'])

    return figure


def figure_for(case: str, edges, flows, element: str | None, unit: str, theme: str,
               shows: str = '', of_many: int = 1):
    """Build one figure, for total mass or for a single element."""
    nodes = {flow: mass(frame, element) for flow, frame in flows.items()}
    nodes = {flow: value for flow, value in nodes.items() if value > 1e-12}
    links = [(s, t, mass(frame, element)) for (s, t), frame in edges.items()
             if s in nodes and t in nodes and mass(frame, element) > 1e-12]
    if not links:
        return None

    # A Sankey is one snapshot of a case that may hold several. Saying which,
    # on the figure, is the fix for it having silently been the first one.
    which = f'{shows}. ' if shows else ''
    if of_many > 1:
        which = f'{shows} — one of {of_many} in this run. '

    if element:
        title = f'{case} — {element} through the recovery system'
        subtitle = (f'{which}Element-depth rows only. Node and ribbon size are mass '
                    f'in {unit}. {len(nodes)} flows, {len(links)} transfers.')
    else:
        title = f'{case} — material flows'
        subtitle = (f'{which}Each flow totalled at its own shallowest depth, so nesting '
                    f'is not double counted. Mass in {unit}. '
                    f'{len(nodes)} flows, {len(links)} transfers.')
    return render(nodes, links, assign_columns(list(nodes), links), title, subtitle, theme)


def draw(folder: str | None = None, params: Params | None = None,
         tables: dict | None = None) -> None:
    params = params or current()
    folder = folder or params.run.data_folder

    # The inflow may be handed over in memory rather than read from a CSV --
    # that is how the upstream draws reach the model, with nothing written in
    # between (src/upstream.py).
    # The unit the values are in, not the one the source file declared.
    # See unit_drawn: reading it from the inputs column was out by 1e6.
    unit = unit_drawn(params)

    shows, of_many = chosen_entry(folder, tables)
    edges, flows = replay(folder, tables)
    case = os.path.basename(folder.rstrip('/'))

    elements = [None]
    if params.figures.element_figures:
        elements += sorted({e for f in flows.values() for e in f['Layer 4'].unique() if e})

    print(f'{folder}: {len(flows)} flows, {len(edges)} transfers, '
          f'showing {shows}' + (f' of {of_many} combinations' if of_many > 1 else ''))
    for element in elements:
        figure = figure_for(case, edges, flows, element, unit,
                            params.figures.theme, shows=shows, of_many=of_many)
        if figure is None:
            continue
        stem = element or 'total'
        for path in write(figure, folder_for(params.figures.out_dir, case), stem,
                          params.figures.enabled(), params.figures.dpi):
            print(f'  wrote {path}')
        import matplotlib.pyplot as plt
        plt.close(figure)

