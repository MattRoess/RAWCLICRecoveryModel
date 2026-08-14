"""
Draw the STRUCTURE of a data folder: what connects to what, and what each
process does. Nothing is scaled by mass -- this is the diagram for
understanding the setup, not for reading quantities off.

    ./.venv/bin/python plot_structure.py data_folder/template

Writes figures/<case>_structure.svg. Every box is a flow, every arrow is a
process, and the transfer coefficients behind each arrow are listed underneath
so the whole configuration is visible at once.

For mass-weighted Sankey diagrams instead, see plot_flows.py.
"""
import os
import sys

import pandas as pd

PALETTE = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2',
           '#B279A2', '#EECA3B', '#9D755D', '#BAB0AC']


def load(folder: str) -> pd.DataFrame:
    return pd.read_csv(f'{folder}/input_data/TCs.csv', keep_default_na=False, na_values=[])


def assign_columns(edges: list[tuple[str, str]], nodes: list[str]) -> dict[str, int]:
    """Place each flow one column to the right of its furthest upstream source."""
    column = {node: 0 for node in nodes}
    for _ in range(len(nodes)):
        changed = False
        for source, target in edges:
            if column[target] < column[source] + 1:
                column[target] = column[source] + 1
                changed = True
        if not changed:
            break
    return column


def escape(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def render(tcs: pd.DataFrame, case: str) -> str:
    has_range = {'value_min', 'value_max'}.issubset(tcs.columns)
    process_col = 'process' if 'process' in tcs.columns else None
    technology_col = 'technology' if 'technology' in tcs.columns else None

    nodes = sorted(set(tcs['Input_FlowID']) | set(tcs['Output_FlowID']))
    edges = list(dict.fromkeys(zip(tcs['Input_FlowID'], tcs['Output_FlowID'])))
    column = assign_columns(edges, nodes)

    columns: dict[int, list[str]] = {}
    for node in nodes:
        columns.setdefault(column[node], []).append(node)

    box_w, box_h, gap_y = 178, 46, 30
    col_gap = 118
    left, top = 24, 84
    tallest = max(len(group) for group in columns.values())
    diagram_h = top + tallest * (box_h + gap_y)

    # Lay out the per-edge TC listing below the diagram, in two columns.
    blocks = []
    for source, target in edges:
        rows = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        head = f'{source}  →  {target}'
        layers = f"{rows['Input_layer'].iloc[0]} → {rows['TC_target_layer'].iloc[0]}"
        tag = ''
        if process_col and rows[process_col].iloc[0]:
            tag = rows[process_col].iloc[0]
            if technology_col and rows[technology_col].iloc[0]:
                tag += f" / {rows[technology_col].iloc[0]}"
        lines = []
        for _, row in rows.iterrows():
            text = f"{row['Input_layer_key'] or '*'} → {row['TC_target_key']}   {row['value']:g}"
            if has_range:
                text += f"  [{row['value_min']:g}–{row['value_max']:g}]"
            lines.append(text)
        blocks.append((head, f'{layers}{"  ·  " + tag if tag else ""}', lines))

    per_col = (len(blocks) + 1) // 2
    tallest_block = max(sum(len(b[2]) + 3 for b in blocks[i * per_col:(i + 1) * per_col])
                        for i in range(2)) if blocks else 0
    legend_h = 54 + tallest_block * 15
    width = max(left * 2 + max(columns) * (box_w + col_gap) + box_w, 960)
    height = diagram_h + legend_h

    colour = {node: PALETTE[i % len(PALETTE)] for i, node in enumerate(nodes)}
    position = {}
    for index, group in sorted(columns.items()):
        group.sort()
        offset = (tallest - len(group)) * (box_h + gap_y) / 2
        for i, node in enumerate(group):
            position[node] = (left + index * (box_w + col_gap), top + offset + i * (box_h + gap_y))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
        '<style>'
        ' .bg{fill:#ffffff} .ttl{fill:#111827} .sub{fill:#6b7280} .nd{fill:#111827}'
        ' .ed{fill:#4b5563} .hd{fill:#111827} .mt{fill:#6b7280} .tc{fill:#374151}'
        ' .bx{fill:#f9fafb;stroke:#d1d5db} .ar{stroke:#9ca3af;fill:none}'
        ' .rule{stroke:#e5e7eb}'
        ' @media (prefers-color-scheme: dark){'
        '  .bg{fill:#0b0f19} .ttl{fill:#f3f4f6} .sub{fill:#9ca3af} .nd{fill:#f3f4f6}'
        '  .ed{fill:#9ca3af} .hd{fill:#f3f4f6} .mt{fill:#9ca3af} .tc{fill:#d1d5db}'
        '  .bx{fill:#111827;stroke:#374151} .ar{stroke:#6b7280} .rule{stroke:#1f2937}}'
        '</style>',
        f'<rect class="bg" width="{width}" height="{height}"/>',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9ca3af"/></marker></defs>',
        f'<text class="ttl" x="{left}" y="32" font-size="17" font-weight="600">'
        f'{escape(case)} — how the flows connect</text>',
        f'<text class="sub" x="{left}" y="54" font-size="12.5">'
        f'Structure only, nothing scaled by mass. {len(nodes)} flows, {len(edges)} processes, '
        f'{len(tcs)} transfer coefficients.</text>',
    ]

    placed: list[tuple[float, float]] = []
    for source, target in edges:
        x0, y0 = position[source][0] + box_w, position[source][1] + box_h / 2
        x1, y1 = position[target]
        y1 += box_h / 2
        mid = (x0 + x1) / 2
        out.append(f'<path class="ar" d="M{x0},{y0} C{mid},{y0} {mid},{y1} {x1 - 9},{y1}" '
                   f'marker-end="url(#a)" stroke-width="1.6"/>')
        rows = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        label = rows[process_col].iloc[0] if process_col and rows[process_col].iloc[0] else \
            f"{rows['Input_layer'].iloc[0][:4]}→{rows['TC_target_layer'].iloc[0][:4]}"

        # Nudge the label clear of any already placed nearby, so that arrows
        # converging on the same area do not stack their labels on top of
        # each other.
        label_y = (y0 + y1) / 2 - 5
        while any(abs(mid - px) < 62 and abs(label_y - py) < 12 for px, py in placed):
            label_y += 13
        placed.append((mid, label_y))
        out.append(f'<text class="ed" x="{mid}" y="{label_y}" font-size="10.5" '
                   f'text-anchor="middle">{escape(label)}</text>')

    for node in nodes:
        x, y = position[node]
        out.append(f'<rect class="bx" x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="7" '
                   f'stroke-width="1.2"/>')
        out.append(f'<rect x="{x}" y="{y}" width="4.5" height="{box_h}" rx="2" fill="{colour[node]}"/>')
        expressed = tcs.loc[tcs['Output_FlowID'] == node, 'TC_target_layer']
        role = expressed.iloc[0] if len(expressed) else 'inflow'
        out.append(f'<text class="nd" x="{x + 14}" y="{y + 20}" font-size="12.5" '
                   f'font-weight="600">{escape(node)}</text>')
        out.append(f'<text class="mt" x="{x + 14}" y="{y + 35}" font-size="10.5">'
                   f'expressed at: {escape(role)}</text>')

    out.append(f'<line class="rule" x1="{left}" y1="{diagram_h - 10}" x2="{width - left}" '
               f'y2="{diagram_h - 10}" stroke-width="1"/>')
    out.append(f'<text class="hd" x="{left}" y="{diagram_h + 14}" font-size="13" '
               f'font-weight="600">Transfer coefficients behind each arrow</text>')

    col_x = [left, width / 2 + 10]
    for c in range(2):
        y = diagram_h + 42
        for head, meta, lines in blocks[c * per_col:(c + 1) * per_col]:
            out.append(f'<text class="hd" x="{col_x[c]}" y="{y}" font-size="11.5" '
                       f'font-weight="600">{escape(head)}</text>')
            y += 14
            out.append(f'<text class="mt" x="{col_x[c]}" y="{y}" font-size="10">{escape(meta)}</text>')
            y += 14
            for line in lines:
                out.append(f'<text class="tc" x="{col_x[c] + 10}" y="{y}" font-size="10.5" '
                           f'font-family="ui-monospace, SFMono-Regular, Menlo, monospace">'
                           f'{escape(line)}</text>')
                y += 13
            y += 14

    out.append('</svg>')
    return '\n'.join(out)


def main(folder: str) -> None:
    case = os.path.basename(folder.rstrip('/'))
    os.makedirs('figures', exist_ok=True)
    path = f'figures/{case}_structure.svg'
    with open(path, 'w') as handle:
        handle.write(render(load(folder), case))
    print(f'wrote {path}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'data_folder/template')
