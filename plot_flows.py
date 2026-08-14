"""
Draw the flow network of a data folder as a Sankey diagram, straight to SVG.

    ./.venv/bin/python plot_flows.py data_folder/template

Writes figures/<case>_total.svg plus one figure per element. No plotting
library is needed, and the SVGs open in a browser, in Positron, and render on
GitHub.

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
import sys

import pandas as pd

from src.recovery_model_optimized import RecoveryModelOptimized

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
LAYER_NAMES = ['product', 'component', 'material', 'element']

# Colour-blind-safe qualitative palette, cycled per source node.
PALETTE = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2',
           '#B279A2', '#EECA3B', '#9D755D', '#BAB0AC']


def depth_of(frame: pd.DataFrame) -> pd.Series:
    """How many layer columns a row populates. 1 = product, 4 = element."""
    return (frame[LAYERS] != '').sum(axis=1)


def replay(folder: str):
    """
    Re-run the model's process loop, recording the mass on every edge.

    Returns (edges, flows) where edges maps (source, target) -> dataframe of
    the transferred rows, and flows maps flow id -> dataframe of its contents.
    """
    model = RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES)
    entry = model.input_data[0]
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


def render(nodes, links, column, title, subtitle) -> str:
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

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
        '<style>'
        '  .bg{fill:#ffffff} .ttl{fill:#111827} .sub{fill:#6b7280} .lbl{fill:#111827}'
        '  .val{fill:#6b7280}'
        '  @media (prefers-color-scheme: dark){'
        '    .bg{fill:#0b0f19} .ttl{fill:#f3f4f6} .sub{fill:#9ca3af} .lbl{fill:#f3f4f6}'
        '    .val{fill:#9ca3af}}'
        '</style>',
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="ttl" x="{left}" y="30" font-size="17" font-weight="600">{title}</text>',
        f'<text class="sub" x="{left}" y="52" font-size="12.5">{subtitle}</text>',
    ]

    colour = {node: PALETTE[i % len(PALETTE)] for i, node in enumerate(sorted(nodes))}

    # Ribbons first, so nodes and labels sit on top.
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
        parts.append(
            f'<path d="M{x0:.1f},{y0:.1f} C{mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {x1:.1f},{y1:.1f}" '
            f'fill="none" stroke="{colour[source]}" stroke-opacity="0.42" stroke-width="{thickness:.1f}"/>')

    for node, (x, y, size) in box.items():
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{node_width}" height="{size:.1f}" '
                     f'rx="2" fill="{colour[node]}"/>')
        label_x = x + node_width + 7
        anchor = 'start'
        if column[node] == max(columns):
            label_x, anchor = x + node_width + 7, 'start'
        parts.append(f'<text class="lbl" x="{label_x:.1f}" y="{y + size / 2 - 1:.1f}" '
                     f'font-size="12" text-anchor="{anchor}">{node}</text>')
        parts.append(f'<text class="val" x="{label_x:.1f}" y="{y + size / 2 + 12:.1f}" '
                     f'font-size="10.5" text-anchor="{anchor}">{nodes[node]:,.1f}</text>')

    parts.append('</svg>')
    return '\n'.join(parts)


def figure(folder: str, edges, flows, element: str | None, unit: str) -> str | None:
    """Build one figure, for total mass or for a single element."""
    nodes = {flow: mass(frame, element) for flow, frame in flows.items()}
    nodes = {flow: value for flow, value in nodes.items() if value > 1e-12}
    links = [(s, t, mass(frame, element)) for (s, t), frame in edges.items()
             if s in nodes and t in nodes and mass(frame, element) > 1e-12]
    if not links:
        return None

    case = os.path.basename(folder.rstrip('/'))
    if element:
        title = f'{case} — {element} through the recovery system'
        subtitle = (f'Element-depth rows only. Node and ribbon size are mass in {unit}. '
                    f'{len(nodes)} flows, {len(links)} transfers.')
    else:
        title = f'{case} — material flows'
        subtitle = (f'Each flow totalled at its own shallowest depth, so nesting is not '
                    f'double counted. Mass in {unit}. {len(nodes)} flows, {len(links)} transfers.')
    return render(nodes, links, assign_columns(list(nodes), links), title, subtitle)


def main(folder: str) -> None:
    unit = 'Mg'
    inputs = pd.read_csv(f'{folder}/input_data/inputs.csv', keep_default_na=False, na_values=[])
    if 'Unit' in inputs.columns and inputs['Unit'].nunique() == 1:
        unit = inputs['Unit'].iloc[0]

    edges, flows = replay(folder)
    case = os.path.basename(folder.rstrip('/'))
    os.makedirs('figures', exist_ok=True)

    written = []
    for element in [None] + sorted({e for f in flows.values() for e in f['Layer 4'].unique() if e}):
        svg = figure(folder, edges, flows, element, unit)
        if svg is None:
            continue
        path = f'figures/{case}_{element or "total"}.svg'
        with open(path, 'w') as handle:
            handle.write(svg)
        written.append(path)

    print(f'{folder}: {len(flows)} flows, {len(edges)} transfers')
    for path in written:
        print(f'  wrote {path}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'data_folder/template')
