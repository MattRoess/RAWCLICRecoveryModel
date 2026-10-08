"""
Draw the flow network of a data folder as a Sankey diagram.

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

    ./.venv/bin/python plot_flows.py                       # the case in params_schema.py
    ./.venv/bin/python plot_flows.py data/reference/basic_test

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

import numpy as np
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


def chosen_entry(folder: str, tables: dict | None = None,
                 scenario: str | None = None) -> tuple[str, int]:
    """
    Which combination the Sankeys describe, and how many there are.

    A Sankey is one snapshot, and a case can hold several years. The LAST is
    taken, not the first: every other output of a run is headlined on the last
    year of the selection, and a diagram quietly showing the first was the
    defect this replaced (DEFECTS.md section 3.7). Narrow `run.years` to draw a
    different one.
    """
    model = RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                                   tables=tables, scenario=scenario)
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


def replay(folder: str, tables: dict | None = None,
           scenario: str | None = None):
    """
    Re-run the model's process loop, recording the mass on every edge.

    Returns (edges, flows) where edges maps (source, target) -> dataframe of
    the transferred rows, and flows maps flow id -> dataframe of its contents.
    The combination replayed is the one `chosen_entry` names.
    """
    model = RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                                   tables=tables, scenario=scenario)
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


def finest_layer(frame: pd.DataFrame) -> str:
    """
    The deepest layer this case actually resolves.

    NOT always Layer 4, and assuming it was is why per-resource Sankeys were
    silently missing. `bev_electronics_wiring` stops at material -- copper,
    alalloy, fealloy at Layer 3, Layer 4 empty in every row -- so a set built
    from Layer 4 came back empty and the loop drew `total` and nothing else. No
    error, no warning, just one figure where there should have been four.
    `carcomposition_mockup` is material-keyed too and never had them either.

    `src/plot_monte_carlo.py` has the same function for the same reason. The fix
    was applied there and not here.

    ⚠️ ONE DEPTH FOR A WHOLE FRAME, which a mixed case does not have. Use
    `resource_of` to ask row by row.
    """
    for column in ('Layer 4', 'Layer 3', 'Layer 2'):
        if column in frame.columns and (frame[column].astype(str) != '').any():
            return column
    return 'Layer 2'


def resource_of(frame: pd.DataFrame) -> pd.Series:
    """
    What each row is a quantity OF: the value of its own deepest filled layer.

    A CASE CAN MIX DEPTHS. The traction motor resolves the magnet to elements
    at Layer 4 and copper, aluminium, steel and lamination to materials at
    Layer 3. `finest_layer` has to answer with one column for the frame, and
    for that case it answers Layer 4 -- so every metal row reads blank and
    silently leaves the figure. That is why 02 drew Nd, Pr, Dy, Tb and nothing
    else: no copper Sankey at all (2026-09-25).
    """
    layers = [column for column in LAYERS if column in frame.columns]
    if not layers:
        return pd.Series([''] * len(frame), index=frame.index)
    deepest = frame[layers[::-1]].astype(str).replace('nan', '')
    out = deepest.iloc[:, 0].copy()
    for column in deepest.columns[1:]:
        out = out.where(out != '', deepest[column])
    return out.fillna('')


def layer_holding(frame: pd.DataFrame, element: str) -> str:
    """Which layer column actually carries `element`, for the subtitle."""
    for column in ('Layer 4', 'Layer 3', 'Layer 2'):
        if column in frame.columns and (frame[column].astype(str) == element).any():
            return column
    return 'Layer 3'


def shallowest_of(frame: pd.DataFrame, resource: str | None):
    """
    A mask for one resource's own rows: the shallowest depth it appears at.

    ⚠️ A RESOURCE CAN MATCH AT TWO DEPTHS AT ONCE, and then summing the matches
    counts its mass twice. `resource_of` gives each row the value of its own
    deepest filled layer, so a component called `copper` holding a material
    called `copper` answers `copper` on BOTH rows -- the parent and its only
    child -- and they carry the same mass by construction.

    That is not a corner case. Every traction motor case is built this way
    (copper, aluminium, steel, lamination, magnet) and so is the battery (all
    twelve components), because upstream names a component after the thing it
    is made of. Found 2026-09-28 by wiring the Monte Carlo Sankey into 03: the
    picture balanced within itself and then failed to match the model --
    F_collected read 141.0 M kg of copper against a true 70.5 M.

    The fix is the nesting rule this module already applies to a flow's
    aggregate (MODEL_MECHANICS §1): a deeper row is a SUB-QUANTITY of its
    parent, never an addition to it, so take the shallowest depth among the
    rows that match and leave the rest alone. Where a resource appears at one
    depth only -- every element case, and every recovered flow in all nine
    cases -- this changes nothing.

    `resource` of None means the flow's own total, which is the same rule with
    nothing to match on.
    """
    depths = depth_of(frame)
    if resource is None:
        return depths == depths.min()
    match = resource_of(frame) == resource
    if not match.any():
        return match
    return match & (depths == depths[match].min())


def mass(frame: pd.DataFrame, element: str | None) -> float:
    """
    Total mass in a set of rows, without double counting the nesting.

    For an element figure, that element's own rows; otherwise the shallowest
    depth present, which is that flow's own aggregate. Both go through
    `shallowest_of`, which is where the rule is written down.
    """
    if frame is None or len(frame) == 0:
        return 0.0
    frame = frame.copy()
    frame['Value'] = pd.to_numeric(frame['Value'])
    return float(frame.loc[shallowest_of(frame, element), 'Value'].sum())


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


# How much subtitle fits on one line, and how far apart the lines sit. 12.5pt
# DejaVu Sans on a 1180pt canvas with a 20pt margin each side takes about 170
# characters; 150 leaves room for the wide glyphs a resource name can bring.
SUBTITLE_CHARS = 150
SUBTITLE_STEP = 17


def render(nodes, links, column, title, subtitle, theme: str,
           intervals=None):
    """Lay out and draw the Sankey. Node height and ribbon width are mass."""
    # TALLER WHEN EVERY NODE CARRIES THREE LINES. At 620 the name, the
    # mean and the interval overlapped their neighbours wherever two
    # small flows sat together.
    # AN INTERVAL LABEL IS THREE LINES AND A LONG ONE. `[597,713,656.8 -
    # 670,589,993.6]` at 9pt is about 155pt wide on its own, so the 150pt right
    # margin that suited a two-line label cut every interval in half, and a gap
    # of 16 let two small nodes print their three lines straight through each
    # other. Both are only visible once the Monte Carlo Sankey is drawn, which
    # is why they surfaced on 2026-09-28 and not before.
    width = 1400 if intervals else 1180
    height = 880 if intervals else 620
    left, right, top, bottom = 20, (300 if intervals else 150), 76, 30
    node_width = 16
    gap = 40 if intervals else 16

    # THE SUBTITLE WRAPS, and the diagram starts below however many lines it
    # took. It used to be one line at 12.5pt from x=20 on a 1180pt canvas, so
    # anything past about 170 characters simply ran off the right edge -- the
    # Monte Carlo subtitle, which has to state that the ribbon is a mean and
    # the interval is printed separately, is longer than that and lost its last
    # clause. A figure has to be readable at the size it is drawn
    # (DECISIONS 17), and a caption that explains what a ribbon cannot show is
    # not the part to truncate.
    import textwrap
    lines = textwrap.wrap(subtitle, SUBTITLE_CHARS) or ['']
    top += SUBTITLE_STEP * (len(lines) - 1)

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
    for line_number, line in enumerate(lines):
        label(axes, left, 48 + SUBTITLE_STEP * line_number, line, 12.5,
              colours['sub'])

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
        # THE INTERVAL GOES ON THE LABEL, because a ribbon cannot carry one.
        # Its width is the mean and the mean alone; without the numbers beside
        # it the figure would state a precision the run does not have.
        if intervals and node in intervals:
            low, high = intervals[node]
            label(axes, text_x, y + size / 2 - 11, node, 12, colours['node'])
            label(axes, text_x, y + size / 2 + 2, f'{nodes[node]:,.1f}',
                  10.5, colours['meta'])
            label(axes, text_x, y + size / 2 + 14,
                  f'[{low:,.1f} - {high:,.1f}]', 9, colours['sub'])
        else:
            label(axes, text_x, y + size / 2 - 5, node, 12, colours['node'])
            label(axes, text_x, y + size / 2 + 8, f'{nodes[node]:,.1f}',
                  10.5, colours['meta'])

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
        # NAME THE LAYER, do not assert it is elements. This said
        # "Element-depth rows only" on every case, including the two that stop
        # at material -- so the wiring case's copper Sankey, drawn from Layer 3
        # material rows, announced an element depth it does not have. `mass()`
        # was already reading the deepest layer each frame fills; only the
        # sentence was stuck on Layer 4.
        # THE LAYER THIS RESOURCE SITS AT, not one chosen for the case.
        # A mixed case has both: Nd at Layer 4, copper at Layer 3.
        depth = max((layer_holding(frame, element) for frame in flows.values()
                     if frame is not None and len(frame)), default='Layer 3')
        title = f'{case} — {element} through the recovery system'
        subtitle = (f'{which}{depth} rows only -- the depth this resource sits at. '
                    f'Node and ribbon size are mass '
                    f'in {unit}. {len(nodes)} flows, {len(links)} transfers.')
    else:
        title = f'{case} — material flows'
        subtitle = (f'{which}Each flow totalled at its own shallowest depth, so nesting '
                    f'is not double counted. Mass in {unit}. '
                    f'{len(nodes)} flows, {len(links)} transfers.')
    return render(nodes, links, assign_columns(list(nodes), links), title, subtitle, theme)


def draws_for(run, flow: str, resource: str | None, year) -> np.ndarray | None:
    """
    The draws behind one node: a flow's mass, for one resource, in one year.

    Returns (draws,) or None when the flow holds nothing there. Rows are summed
    PER DRAW, which is the whole point -- the interval of a sum is not the sum
    of its parts' intervals.
    """
    keys = run.keys
    same_year = keys['Year'].astype(str).to_numpy() == str(year)
    is_flow = (keys['Stock/Flow ID'] == flow).to_numpy()
    here = np.flatnonzero(is_flow & same_year)
    if not here.size:
        return None
    # The shallowest depth, for the aggregate AND for a named resource: a
    # component called `copper` and the material inside it both answer
    # `copper`, and adding them counts the same mass twice. See
    # `shallowest_of`, which states the rule and where it came from.
    rows = here[shallowest_of(keys.iloc[here], resource).to_numpy()]
    if not rows.size:
        return None
    return run.values[rows].sum(axis=0)


def figure_for_draws(case: str, run, tcs, element: str | None, unit: str,
                     theme: str, year, shows: str = '', of_many: int = 1):
    """
    The same Sankey, drawn from the Monte Carlo instead of one point solve.

    ⚠️ WHAT A SANKEY CANNOT DO. A ribbon's width is a single number, so this
    figure shows MEANS and prints each node's 95% interval beside it. It is also
    ONE YEAR out of eleven. Both limits are the figure's, not the model's, and
    2026-09-25 is when they were said out loud: "they are only good for 1 year
    and they do not show uncertainties".

    MEANS ARE THE RIGHT CENTRAL VALUE HERE, and the only one that would work:
    means add, so what enters a node still equals what leaves it and the picture
    balances exactly. Medians would not -- the ribbons into a node would not sum
    to the node -- and the deterministic run this replaces is every coefficient
    at its mode, which is neither.

    EDGES COME FROM THEIR TARGET. A transfer s -> t carrying resource r is that
    resource's whole content of t, because nothing else feeds it: checked across
    all four traction motor cases, every node fed from several places separates
    by resource. Where that does not hold the edge is dropped rather than
    guessed, and the subtitle says how many.
    """
    nodes, intervals, shares = {}, {}, {}
    for flow in dict.fromkeys(list(tcs['Input_FlowID']) + list(tcs['Output_FlowID'])):
        drawn = draws_for(run, flow, element, year)
        if drawn is None or float(drawn.mean()) <= 1e-12:
            continue
        nodes[flow] = float(drawn.mean())
        low, high = np.percentile(drawn, [2.5, 97.5])
        intervals[flow] = (float(low), float(high))

    # AN EDGE IS ITS TARGET'S CONTENT, when nothing else feeds that target.
    # Deriving it from the coefficient's own target key does not work: upstream
    # of the separation the chain is carried by COMPONENT-keyed coefficients
    # (F_collected -> F_motor moves `magnet`, not `Nd`), so an element figure
    # built from TC keys drew only the last two steps and left every node
    # before them stranded. The mass of Nd crossing that edge is simply the Nd
    # in F_motor, because F_motor has one source.
    inbound = {}
    for source, target in dict.fromkeys(zip(tcs['Input_FlowID'], tcs['Output_FlowID'])):
        inbound.setdefault(target, []).append(source)

    links, ambiguous = [], 0
    for (source, target) in dict.fromkeys(zip(tcs['Input_FlowID'],
                                              tcs['Output_FlowID'])):
        if source not in nodes or target not in nodes:
            continue
        if len(inbound[target]) == 1:
            drawn = draws_for(run, target, element, year)
            total = float(drawn.mean()) if drawn is not None else 0.0
        else:
            # Several sources: take only the resources THIS one delivers. Every
            # such node in the four traction motor cases separates cleanly --
            # copper from F_cu_stream, aluminium from F_al_stream, lamination
            # and steel from F_steel_stream.
            mine = tcs[(tcs['Input_FlowID'] == source)
                       & (tcs['Output_FlowID'] == target)]
            wanted = {str(r) for r in mine['TC_target_key'] if str(r)}
            if element is not None:
                wanted &= {element}
            total = 0.0
            for resource in sorted(wanted):
                others = tcs[(tcs['Output_FlowID'] == target)
                             & (tcs['TC_target_key'].astype(str) == resource)]
                if others['Input_FlowID'].nunique() > 1:
                    ambiguous += 1      # two sources, one resource: not separable
                    continue
                drawn = draws_for(run, target, resource, year)
                if drawn is not None:
                    total += float(drawn.mean())
        if total > 1e-12:
            links.append((source, target, total))
    if not links:
        return None

    which = f'{shows}. ' if shows else ''
    if of_many > 1:
        which = f'{shows} — one of {of_many} in this run. '
    what = element or 'all materials'
    note = (f'  {ambiguous} transfer(s) not separable by resource and left out.'
            if ambiguous else '')
    title = f'{case} — {what} through the recovery system, {year}'
    subtitle = (f'{which}Monte Carlo, {run.values.shape[1]:,} draws. Ribbon width '
                f'is the MEAN; the 95% interval is printed under each node, '
                f'because a ribbon cannot carry one. One year of the run. '
                f'Mass in {unit}. {len(nodes)} flows, {len(links)} transfers.{note}')
    return render(nodes, links, assign_columns(list(nodes), links), title,
                  subtitle, theme, intervals=intervals)


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

    shows, of_many = chosen_entry(folder, tables, params.run.scenario)
    edges, flows = replay(folder, tables, params.run.scenario)
    case = os.path.basename(folder.rstrip('/'))

    elements = [None]
    if params.figures.element_figures:
        # THE RESOURCES THIS STUDY IS ABOUT, not every one in the data. 02 drew
        # a Sankey for all nine traction resources while 03 redrew only the six
        # named in `figures.resources`, so three of 02's point-solve pictures
        # stayed on disk beside six Monte Carlo ones, indistinguishable except
        # by their subtitles. Narrowing here keeps the two stages in step.
        wanted = tuple(params.figures.resources or ())
        # EVERY RESOURCE, AT WHATEVER DEPTH IT SITS. The old code picked one
        # layer for the case and fell back to Layer 4 when flows disagreed.
        # That fallback was read as protecting the "no output flow is written
        # at mixed layers" check, but that check forbids ONE FLOW mixing
        # layers, not a case whose different flows sit at different depths --
        # which is what the traction motor is. The fallback silently dropped
        # copper, aluminium, steel and lamination from every figure.
        found = sorted({e for f in flows.values()
                        for e in resource_of(f).unique() if e})
        elements += [e for e in found if e in wanted] or found

    print(f'{folder}: {len(flows)} flows, {len(edges)} transfers, '
          f'showing {shows}' + (f' of {of_many} combinations' if of_many > 1 else ''))
    # The FOLDER, not its name: the choice a case offers (run.variants) is read from the
    # case's own tables, and a bare name cannot be opened. `folder_for` takes the name from it.
    root = folder_for(params.figures.out_dir, folder, params.run.scenario)
    written = []
    for element in elements:
        figure = figure_for(case, edges, flows, element, unit,
                            params.figures.theme, shows=shows, of_many=of_many)
        if figure is None:
            continue
        stem = element or 'total'
        for path in write(figure, root, stem,
                          params.figures.enabled(), params.figures.dpi):
            print(f'  wrote {path}')
            written.append(path)
        import matplotlib.pyplot as plt
        plt.close(figure)

    # ⚠️ AND CLEAR THE SANKEYS 02 USED TO DRAW AND NO LONGER DOES. Narrowing
    # `figures.resources` leaves the dropped resources' pictures on disk, which
    # is the same trap `figure_style.sweep` was written for. Only 02's own
    # files are touched; 03's and the structure's are left alone.
    from src.figure_style import report_sweep
    report_sweep(root, 'flow diagrams', written)

