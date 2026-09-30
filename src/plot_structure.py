"""
Draw the STRUCTURE of a data folder: what connects to what, and what each
process does. Nothing is scaled by mass -- this is the diagram for
understanding the setup, not for reading quantities off.

    ./.venv/bin/python tools/plot_structure.py                    # the case in params_schema.py
    ./.venv/bin/python tools/plot_structure.py data/reference/basic_test
    ./.venv/bin/python tools/plot_structure.py --list

Everything about the output -- which formats, which resolution, which palette --
is a parameter in `src/params_schema.py`, not a flag. Change it there.

The argument, when given, may be a data folder, a folder containing
input_data/, or a TCs.csv anywhere on disk. Pass `--pick` to choose from a
list of the cases found.

Writes <out_dir>/<case>_structure.<fmt> in every format switched on by
`figures.png`, `figures.svg` and `figures.pdf`. Every box is a flow, every arrow is a process, and the transfer
coefficients behind each arrow are listed underneath so the whole configuration
is visible at once.

For mass-weighted Sankey diagrams instead, see plot_flows.py.
"""
import os

import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path

from src.figure_style import MONO, PALETTE, canvas, folder_for, label, write
from src.params_schema import Params, current

SEARCH_ROOTS = ('data', '.')


# --------------------------------------------------------------------------
# Input selection
# --------------------------------------------------------------------------

def find_cases(roots=SEARCH_ROOTS) -> list[str]:
    """
    Every folder under the roots that holds an input_data/TCs.csv.

    The roots overlap ('.' contains 'data'), so paths are normalised
    before de-duplicating or the same case is listed twice under two spellings.
    """
    found = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path, _, files in os.walk(root):
            if os.path.basename(path) != 'input_data':
                continue
            if 'TCs.csv' in files or 'case.xlsx' in files:
                found.add(os.path.normpath(os.path.dirname(path)))
    return sorted(found)


def resolve(target: str) -> tuple[str, str]:
    """
    Turn whatever was pointed at into (tcs_path, case_name).

    Accepts a TCs.csv, a folder containing input_data/TCs.csv, or an
    input_data folder itself.
    """
    target = target.rstrip('/')
    if os.path.isfile(target):
        case = os.path.basename(os.path.dirname(os.path.dirname(target)))
        return target, case or os.path.splitext(os.path.basename(target))[0]

    from src import case_tables

    # A case keeps its coefficients either in case.xlsx or in TCs.csv.
    found = case_tables.where(target, 'TCs')
    if found is not None:
        return found[1], os.path.basename(target)

    direct = os.path.join(target, 'TCs.csv')
    if os.path.isfile(direct):
        return direct, os.path.basename(os.path.dirname(target))

    raise SystemExit(
        f"No transfer coefficients for '{target}'.\n"
        f"Looked for a TCs sheet in {case_tables.workbook_path(target)}, "
        f"{case_tables.csv_path(target, 'TCs')} and {direct}.\n"
        f"Available: {', '.join(find_cases()) or 'none found'}"
    )


def choose() -> str:
    """List the discoverable cases and let the user pick one."""
    cases = find_cases()
    if not cases:
        raise SystemExit('No data folder with transfer coefficients found here.')
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

# What each role is called on the diagram, and the colour it is drawn in.
# THE ROLE IS THE ANSWER TO "and then what?", and until 2026-09-02 the diagram
# did not carry it at all: every box said which layer it was expressed at and
# none said whether the mass in it was recovered, lost, or handed to a process
# this case does not model. Two boxes with no arrow leaving them looked
# identical whether one was gold coming back and the other a shredded board
# nobody follows.
#
# `intermediate` is deliberately absent. It says "an arrow leaves this box",
# which the arrow already says.
ROLE_LABEL = {
    'recovered': 'recovered here',
    'loss': 'lost',
    'handoff': 'handed on, not counted here',
}
ROLE_COLOUR = {'recovered': PALETTE[2], 'loss': PALETTE[3], 'handoff': PALETTE[5]}


def render(tcs: pd.DataFrame, case: str, theme: str = 'light',
           roles: dict[str, str] | None = None):
    """
    Build the figure. One data unit is one typographic point, so the sizes
    below are literal point sizes and the layout is resolution independent --
    which is what lets the same drawing emit SVG, PNG and PDF.
    """
    has_range = {'value_min', 'value_max'}.issubset(tcs.columns)
    process_col = 'process' if 'process' in tcs.columns else None
    technology_col = 'technology' if 'technology' in tcs.columns else None

    nodes = sorted(set(tcs['Input_FlowID']) | set(tcs['Output_FlowID']))
    edges = list(dict.fromkeys(zip(tcs['Input_FlowID'], tcs['Output_FlowID'])))
    column = assign_columns(edges, nodes)

    columns: dict[int, list[str]] = {}
    for node in nodes:
        columns.setdefault(column[node], []).append(node)

    # Room for a third line in the boxes that have a role to state. A case
    # with no processes table has none, and keeps the two-line box it had.
    roles = roles or {}
    shown_roles = {flow: role for flow, role in roles.items() if role in ROLE_LABEL}
    box_w, box_h, gap_y = 214, (62 if shown_roles else 46), 30
    col_gap, left, top = 118, 24, 84
    tallest = max(len(group) for group in columns.values())
    diagram_h = top + tallest * (box_h + gap_y)

    width = max(left * 2 + max(columns) * (box_w + col_gap) + box_w, 960)
    height = diagram_h + 24

    figure, axes, colours = canvas(width, height, theme)

    accent = {node: PALETTE[i % len(PALETTE)] for i, node in enumerate(nodes)}
    parents: dict[str, list[str]] = {}
    for source, target in edges:
        parents.setdefault(target, []).append(source)

    position = {}
    placed: dict[str, int] = {}          # node -> its row in its own column
    for index, group in sorted(columns.items()):
        # BESIDE ITS PARENT, NOT IN THE ALPHABET. Sorting each column by name
        # put the two ends of one road above the two ends of the other, so
        # every arrow crossed every other and the picture said the roads mixed
        # when they do not. Ordering a column by where its parents sit keeps a
        # road travelling straight across the page; name breaks the ties.
        group.sort(key=lambda node: (
            min((placed[p] for p in parents.get(node, []) if p in placed),
                default=0), node))
        offset = (tallest - len(group)) * (box_h + gap_y) / 2
        for i, node in enumerate(group):
            placed[node] = i
            position[node] = (left + index * (box_w + col_gap), top + offset + i * (box_h + gap_y))

    label(axes, left, 26, f'{case} — how the flows connect', 17, colours['title'], 'bold')
    label(axes, left, 50, f'Page 1 of 2.  Structure only, nothing scaled by '
                          f'mass. {len(nodes)} flows, {len(edges)} processes, '
                          f'{len(tcs)} transfer coefficients -- the numbers '
                          f'themselves are on structure_coefficients.png.',
          12.5, colours['sub'])

    placed: list[tuple[float, float]] = []
    for source, target in edges:
        x0, y0 = position[source][0] + box_w, position[source][1] + box_h / 2
        x1, y1 = position[target][0], position[target][1] + box_h / 2
        mid = (x0 + x1) / 2
        curve = Path([(x0, y0), (mid, y0), (mid, y1), (x1 - 3, y1)],
                     [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
        axes.add_patch(FancyArrowPatch(path=curve, arrowstyle='-|>', mutation_scale=11,
                                       linewidth=1.6, color=colours['arrow'],
                                       shrinkA=0, shrinkB=0, joinstyle='round'))

        rows = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        text = rows[process_col].iloc[0] if process_col and rows[process_col].iloc[0] else \
            f"{rows['Input_layer'].iloc[0][:4]}→{rows['TC_target_layer'].iloc[0][:4]}"

        # Nudge the label clear of any already placed nearby, so that arrows
        # converging on the same area do not stack their labels.
        label_y = (y0 + y1) / 2 - 8
        while any(abs(mid - px) < 62 and abs(label_y - py) < 12 for px, py in placed):
            label_y += 13
        placed.append((mid, label_y))
        label(axes, mid, label_y, text, 10.5, colours['edge'], ha='center')

    for node in nodes:
        x, y = position[node]
        axes.add_patch(FancyBboxPatch((x, y), box_w, box_h,
                                      boxstyle='round,pad=0,rounding_size=7',
                                      facecolor=colours['box'], edgecolor=colours['box_line'],
                                      linewidth=1.2, mutation_aspect=1))
        axes.add_patch(Rectangle((x, y + 3), 4.5, box_h - 6, facecolor=accent[node],
                                 edgecolor='none'))
        expressed = tcs.loc[tcs['Output_FlowID'] == node, 'TC_target_layer']
        depth = expressed.iloc[0] if len(expressed) else 'inflow'
        label(axes, x + 14, y + 17, node, 12.5, colours['node'], 'bold')
        label(axes, x + 14, y + 33, f'expressed at: {depth}', 10.5, colours['meta'])
        if node in shown_roles:
            role = shown_roles[node]
            label(axes, x + 14, y + 49, ROLE_LABEL[role], 10.5, ROLE_COLOUR[role], 'bold')

    return figure


# ⚠️ THE NUMBERS ARE THEIR OWN PAGE. They used to sit under the diagram in the
# same image, and they are long: on the traction case the table ran to twice
# the height of the schema, so the schema arrived inside an image 9,566 pixels
# tall and could not be read at any size a screen shows. Asked for on
# 2026-09-29: *"have the numbers on a separate page."*
#
# Two files now, both at the top level of the case's folder:
#
#     structure.png                what connects to what
#     structure_coefficients.png   the number on every arrow, with its range
#                                  and its source
#
# ⚠️ THE SECOND NAME CARRIES THE FIRST. Called plainly `coefficients.png` it
# sat in the folder with nothing to say it belonged to the diagram, and sorted
# nowhere near it. Said on 2026-09-30: *"one does not understand that the
# coefficients belong to the structure."* Sharing the stem puts them side by
# side in any listing and says what they are without opening either.
#
# Neither is a detail, and neither has to be shrunk to make room for the other.
TABLE_COLUMNS = 3


def render_coefficients(tcs: pd.DataFrame, case: str, theme: str = 'light'):
    """
    Every transfer coefficient behind every arrow, as a page of its own.

    Three columns across the full width, because one or two made a strip taller
    than it is wide. The order is the diagram's own: the edges as they are
    drawn, so a reader moves between the two pictures by position.
    """
    has_range = {'value_min', 'value_max'}.issubset(tcs.columns)
    process_col = 'process' if 'process' in tcs.columns else None
    technology_col = 'technology' if 'technology' in tcs.columns else None
    edges = list(dict.fromkeys(zip(tcs['Input_FlowID'], tcs['Output_FlowID'])))
    blocks = tc_blocks(tcs, edges, has_range, process_col, technology_col)

    left, top = 24, 84
    per_col = max(1, -(-len(blocks) // TABLE_COLUMNS))
    tallest = max((sum(len(b[2]) + 3
                       for b in blocks[i * per_col:(i + 1) * per_col])
                   for i in range(TABLE_COLUMNS)), default=0)
    width, height = 1920, top + tallest * 15 + 40
    figure, axes, colours = canvas(width, height, theme)

    label(axes, left, 26,
          f'{case} — how the flows connect: the number on every arrow', 17,
          colours['title'], 'bold')
    label(axes, left, 50,
          f'Page 2 of 2.  The diagram these belong to is structure.png -- '
          f'same case, same {len(edges)} processes, and these are the '
          f'{len(tcs)} transfer coefficients behind its arrows.',
          12.5, colours['sub'])

    span = (width - 2 * left) / TABLE_COLUMNS
    for c in range(TABLE_COLUMNS):
        x, y = left + c * span, top
        for head, meta, lines in blocks[c * per_col:(c + 1) * per_col]:
            label(axes, x, y, head, 11.5, colours['title'], 'bold')
            y += 14
            label(axes, x, y, meta, 10, colours['meta'])
            y += 14
            for line in lines:
                label(axes, x + 10, y, line, 10.5, colours['tc'], family=MONO)
                y += 13
            y += 14
    return figure


# --------------------------------------------------------------------------

def draw(target: str | None = None, params: Params | None = None) -> None:
    params = params or current()
    folder = target or params.run.data_folder
    # Say which case, first thing. Every other tool does, and this one not
    # doing it made a redrawn diagram of the OLD case look like a broken
    # drawing of the new one: pressing Run passes no argument, so the case
    # comes from run.data_folder rather than from whatever was worked on last.
    print(f'Case      : {folder}'
          + ('' if target else '   (from run.data_folder in src/params_schema.py)'))
    tcs_path, case = resolve(folder)
    from src import case_tables
    tcs = (case_tables.read(folder, 'TCs') if case_tables.exists(folder, 'TCs')
           else pd.read_csv(tcs_path, keep_default_na=False, na_values=[]))
    # A row derived as its group's residual has blank bounds, and a blank read as
    # a string breaks the ':g' formatting in tc_blocks. Read blank as "no range",
    # which is what a derived row has, before anything formats it.
    if {'value_min', 'value_max'}.issubset(tcs.columns):
        from src.sampling import numeric_bounds
        tcs = numeric_bounds(tcs)
    from src.rest import flow_roles
    root = folder_for(params.figures.out_dir, case, params.run.scenario)
    import matplotlib.pyplot as plt

    written = []
    for stem, figure in (
            ('structure', render(tcs, case, theme=params.figures.theme,
                                 roles=flow_roles(folder))),
            ('structure_coefficients',
             render_coefficients(tcs, case, theme=params.figures.theme))):
        written += write(figure, root, stem,
                         params.figures.enabled(), params.figures.dpi)
        plt.close(figure)
    for path in written:
        print(f'wrote {path}')

    # Claims `structure.png` in the folder's manifest, so the sweep the other
    # two stages run knows it is current work and not somebody's leftover.
    # See `figure_style.sweep`.
    from src.figure_style import report_sweep
    report_sweep(root, 'structure', written)

    import matplotlib.pyplot as plt
    plt.close(figure)

