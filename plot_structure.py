"""
Draw the STRUCTURE of a data folder: what connects to what, and what each
process does. Nothing is scaled by mass -- this is the diagram for
understanding the setup, not for reading quantities off.

    ./.venv/bin/python plot_structure.py                     # pick from a list
    ./.venv/bin/python plot_structure.py data_folder/template
    ./.venv/bin/python plot_structure.py path/to/TCs.csv --formats svg,png

Run with no argument and it lists every folder under the search roots that
holds a TCs.csv, so the input never has to be edited into the source. The
argument may be a data folder, a folder containing input_data/, or a TCs.csv
itself.

Writes figures/<case>_structure.{svg,png,pdf} by default. Every box is a flow,
every arrow is a process, and the transfer coefficients behind each arrow are
listed underneath so the whole configuration is visible at once.

For mass-weighted Sankey diagrams instead, see plot_flows.py.
"""
import argparse
import os

import matplotlib
matplotlib.use('Agg')

# Keep text as text in both vector formats. Matplotlib's default converts every
# glyph to an outline, which makes the SVG an order of magnitude larger and the
# PDF unsearchable. The layout never measures a string -- every position is
# computed from the numbers below -- so a font substitution on another machine
# changes the glyphs and nothing else.
matplotlib.rcParams['svg.fonttype'] = 'none'
matplotlib.rcParams['pdf.fonttype'] = 42

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path

PALETTE = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2',
           '#B279A2', '#EECA3B', '#9D755D', '#BAB0AC']

FORMATS = ('svg', 'png', 'pdf')
SEARCH_ROOTS = ('data_folder', '.')

# Both themes, so the static PNG and PDF can be either. The SVG used to carry a
# prefers-color-scheme rule and switch by itself; a rasterised figure cannot, so
# the theme is chosen at render time instead.
THEMES = {
    'light': dict(bg='#ffffff', title='#111827', sub='#6b7280', node='#111827',
                  edge='#4b5563', meta='#6b7280', tc='#374151',
                  box='#f9fafb', box_line='#d1d5db', arrow='#9ca3af', rule='#e5e7eb'),
    'dark': dict(bg='#0b0f19', title='#f3f4f6', sub='#9ca3af', node='#f3f4f6',
                 edge='#9ca3af', meta='#9ca3af', tc='#d1d5db',
                 box='#111827', box_line='#374151', arrow='#6b7280', rule='#1f2937'),
}

MONO = ['DejaVu Sans Mono', 'Menlo', 'monospace']


# --------------------------------------------------------------------------
# Input selection
# --------------------------------------------------------------------------

def find_cases(roots=SEARCH_ROOTS) -> list[str]:
    """
    Every folder under the roots that holds an input_data/TCs.csv.

    The roots overlap ('.' contains 'data_folder'), so paths are normalised
    before de-duplicating or the same case is listed twice under two spellings.
    """
    found = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path, _, files in os.walk(root):
            if os.path.basename(path) == 'input_data' and 'TCs.csv' in files:
                found.add(os.path.normpath(os.path.dirname(path)))
    return sorted(found)


def resolve(target: str) -> tuple[str, str]:
    """
    Turn whatever the user pointed at into (tcs_path, case_name).

    Accepts a TCs.csv, a folder containing input_data/TCs.csv, or an
    input_data folder itself.
    """
    target = target.rstrip('/')
    if os.path.isfile(target):
        case = os.path.basename(os.path.dirname(os.path.dirname(target)))
        return target, case or os.path.splitext(os.path.basename(target))[0]

    nested = os.path.join(target, 'input_data', 'TCs.csv')
    if os.path.isfile(nested):
        return nested, os.path.basename(target)

    direct = os.path.join(target, 'TCs.csv')
    if os.path.isfile(direct):
        return direct, os.path.basename(os.path.dirname(target))

    raise SystemExit(
        f"No TCs.csv for '{target}'.\n"
        f"Looked for {nested} and {direct}.\n"
        f"Available: {', '.join(find_cases()) or 'none found'}"
    )


def choose() -> str:
    """List the discoverable cases and let the user pick one."""
    cases = find_cases()
    if not cases:
        raise SystemExit('No data folder with an input_data/TCs.csv found here.')
    if len(cases) == 1:
        print(f'Only one case found: {cases[0]}')
        return cases[0]

    print('\nData folders with a TC table:\n')
    for i, case in enumerate(cases, 1):
        print(f'  {i}. {case}')
    try:
        reply = input('\nSelect [1]: ').strip() or '1'
    except EOFError:
        raise SystemExit('\nNo selection given. Pass the folder as an argument instead.')
    if not reply.isdigit() or not 1 <= int(reply) <= len(cases):
        raise SystemExit(f'Not one of 1..{len(cases)}.')
    return cases[int(reply) - 1]


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

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


def tc_blocks(tcs: pd.DataFrame, edges, has_range, process_col, technology_col):
    """The per-process TC listing that goes below the diagram."""
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
    return blocks


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def render(tcs: pd.DataFrame, case: str, theme: str = 'light') -> plt.Figure:
    """
    Build the figure. One data unit is one typographic point, so the font sizes
    below are literal point sizes and the layout is resolution independent --
    which is the whole reason the same code can emit SVG, PNG and PDF.
    """
    colour_of = THEMES[theme]
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
    col_gap, left, top = 118, 24, 84
    tallest = max(len(group) for group in columns.values())
    diagram_h = top + tallest * (box_h + gap_y)

    blocks = tc_blocks(tcs, edges, has_range, process_col, technology_col)
    per_col = max(1, (len(blocks) + 1) // 2)
    tallest_block = max(
        (sum(len(b[2]) + 3 for b in blocks[i * per_col:(i + 1) * per_col]) for i in range(2)),
        default=0)
    legend_h = 54 + tallest_block * 15
    width = max(left * 2 + max(columns) * (box_w + col_gap) + box_w, 960)
    height = diagram_h + legend_h

    fig = plt.figure(figsize=(width / 72, height / 72))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)          # inverted, so y grows downward as in the layout above
    ax.axis('off')
    fig.patch.set_facecolor(colour_of['bg'])

    def text(x, y, s, size, colour, weight='normal', ha='left', family=None):
        ax.text(x, y, s, fontsize=size, color=colour, fontweight=weight,
                ha=ha, va='center', parse_math=False,
                **({'fontfamily': family} if family else {}))

    accent = {node: PALETTE[i % len(PALETTE)] for i, node in enumerate(nodes)}
    position = {}
    for index, group in sorted(columns.items()):
        group.sort()
        offset = (tallest - len(group)) * (box_h + gap_y) / 2
        for i, node in enumerate(group):
            position[node] = (left + index * (box_w + col_gap), top + offset + i * (box_h + gap_y))

    text(left, 26, f'{case} — how the flows connect', 17, colour_of['title'], 'bold')
    text(left, 50, f'Structure only, nothing scaled by mass. {len(nodes)} flows, '
                   f'{len(edges)} processes, {len(tcs)} transfer coefficients.',
         12.5, colour_of['sub'])

    placed: list[tuple[float, float]] = []
    for source, target in edges:
        x0, y0 = position[source][0] + box_w, position[source][1] + box_h / 2
        x1, y1 = position[target][0], position[target][1] + box_h / 2
        mid = (x0 + x1) / 2
        curve = Path([(x0, y0), (mid, y0), (mid, y1), (x1 - 3, y1)],
                     [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
        ax.add_patch(FancyArrowPatch(path=curve, arrowstyle='-|>', mutation_scale=11,
                                     linewidth=1.6, color=colour_of['arrow'],
                                     shrinkA=0, shrinkB=0, joinstyle='round'))

        rows = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        label = rows[process_col].iloc[0] if process_col and rows[process_col].iloc[0] else \
            f"{rows['Input_layer'].iloc[0][:4]}→{rows['TC_target_layer'].iloc[0][:4]}"

        # Nudge the label clear of any already placed nearby, so that arrows
        # converging on the same area do not stack their labels.
        label_y = (y0 + y1) / 2 - 8
        while any(abs(mid - px) < 62 and abs(label_y - py) < 12 for px, py in placed):
            label_y += 13
        placed.append((mid, label_y))
        text(mid, label_y, label, 10.5, colour_of['edge'], ha='center')

    for node in nodes:
        x, y = position[node]
        ax.add_patch(FancyBboxPatch((x, y), box_w, box_h,
                                    boxstyle='round,pad=0,rounding_size=7',
                                    facecolor=colour_of['box'], edgecolor=colour_of['box_line'],
                                    linewidth=1.2, mutation_aspect=1))
        ax.add_patch(Rectangle((x, y + 3), 4.5, box_h - 6, facecolor=accent[node],
                               edgecolor='none'))
        expressed = tcs.loc[tcs['Output_FlowID'] == node, 'TC_target_layer']
        role = expressed.iloc[0] if len(expressed) else 'inflow'
        text(x + 14, y + 17, node, 12.5, colour_of['node'], 'bold')
        text(x + 14, y + 33, f'expressed at: {role}', 10.5, colour_of['meta'])

    ax.plot([left, width - left], [diagram_h - 10] * 2, color=colour_of['rule'], linewidth=1)
    text(left, diagram_h + 14, 'Transfer coefficients behind each arrow', 13,
         colour_of['title'], 'bold')

    col_x = [left, width / 2 + 10]
    for c in range(2):
        y = diagram_h + 42
        for head, meta, lines in blocks[c * per_col:(c + 1) * per_col]:
            text(col_x[c], y, head, 11.5, colour_of['title'], 'bold')
            y += 14
            text(col_x[c], y, meta, 10, colour_of['meta'])
            y += 14
            for line in lines:
                text(col_x[c] + 10, y, line, 10.5, colour_of['tc'], family=MONO)
                y += 13
            y += 14

    return fig


def write(fig: plt.Figure, out_dir: str, case: str, formats, dpi: int) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for fmt in formats:
        path = os.path.join(out_dir, f'{case}_structure.{fmt}')
        fig.savefig(path, format=fmt, dpi=dpi,
                    facecolor=fig.get_facecolor(), edgecolor='none')
        written.append(path)
    return written


# --------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n\n')[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target', nargs='?',
                        help='data folder, or a TCs.csv. Omit to choose from a list.')
    parser.add_argument('-o', '--out', default='figures', help='output directory (default: figures)')
    parser.add_argument('-f', '--formats', default=','.join(FORMATS),
                        help=f'comma separated, any of {"/".join(FORMATS)} (default: all three)')
    parser.add_argument('--theme', choices=sorted(THEMES), default='light',
                        help='colour scheme baked into the output (default: light)')
    parser.add_argument('--dpi', type=int, default=200, help='raster resolution for PNG (default: 200)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the data folders that have a TC table, then exit')
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    if args.list:
        for case in find_cases():
            print(case)
        return

    formats = [f.strip().lower() for f in args.formats.split(',') if f.strip()]
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        raise SystemExit(f'Unknown format(s): {", ".join(unknown)}. Choose from {", ".join(FORMATS)}.')

    tcs_path, case = resolve(args.target or choose())
    tcs = pd.read_csv(tcs_path, keep_default_na=False, na_values=[])
    fig = render(tcs, case, theme=args.theme)
    for path in write(fig, args.out, case, formats, args.dpi):
        print(f'wrote {path}')
    plt.close(fig)


if __name__ == '__main__':
    main()
