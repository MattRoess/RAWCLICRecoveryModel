"""
src/plot_monte_carlo.py
=======================

Figures that show what the Monte Carlo actually did.

A Monte Carlo result is a distribution per row, and a table of medians throws
away the thing that was expensive to compute. These five figures each answer a
different question about the spread, and together they are what "understanding
the effect of the Monte Carlo" means in practice:

  1. `over_time`        -- is it growing, and how sure is that? Median per
     resource per year, with the 95% interval.
  2. `pdf_all`          -- what does each answer look like, and where does the
     deterministic run sit inside it? The `pdf_<resource>` panels on one page,
     resources as rows and years as columns.
  3. `spread`           -- how uncertain is each result, and does that change
     over the years? The 95% interval as a percentage of the mean, per year.
  4. `mode_vs_mean`     -- how far is running at the mode from the mean, per
     flow? This is the figure that says whether the Monte Carlo changed the
     answer or only added error bars to it.
  5. `convergence`      -- how many draws are actually needed?
  6. `sensitivity`      -- which coefficients drive the spread?

THERE IS NO FIGURE THAT SUMS THE YEAR AXIS FOR AN ABSOLUTE MASS. `distribution`
did, and was deleted on 2026-09-02: adding 2030's 10 kt of copper to 2050's 254
gives a quantity nobody has a use for, dominated by whichever year is last.
Per-year is the only honest way to draw a distribution here.

Figure 4 is the one to look at first. A deterministic run sets every
coefficient to its mode, and a product of triangular variables does not put its
mode at its mean, so the two differ systematically rather than randomly. If
that gap is large, every number produced before this existed was biased, not
merely uncertain.

All of them read a `MonteCarloRun` and nothing else, so none can drift from the
result it describes.
"""
from __future__ import annotations


import itertools

import numpy as np
import pandas as pd

from src.figure_style import PALETTE, chart, folder_for, write
from src.units import readable, scale_for

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# How many bars a ranked chart will draw. Beyond this the figure stops being a
# figure -- 04_01's few hundred (flow, resource) pairs made one 10,277 pixels
# tall. The full table is in the workbook; a chart is for seeing the shape.
MAX_BARS = 30

# The whole inflow, as against one resource's own. Named rather than repeated,
# because which denominator a line uses is the thing this figure got wrong once.
EVERYTHING = 'every resource'

# Cycled so coincident lines stay tellable apart. Two resources measured the
# same way produce the same curve, and a reader has to see two, not one.
DASHES = ['-', (0, (5, 2)), (0, (1, 1.6)), (0, (7, 2, 1.5, 2))]


def header(figure, title: str, colours, subtitle: str = '') -> None:
    """
    A title, and an optional line under it, that do not collide.

    THE GAP IS IN POINTS, NOT IN FIGURE FRACTIONS. matplotlib places suptitle
    and figure.text at a FRACTION of the figure height, so a pair of positions
    tuned on a tall figure lands on top of itself on a short one -- which is
    exactly what happened once 04_01 produced single-year figures a third the
    height of 04_02's five-year ones, and the title printed straight through
    the legend line. Converting a fixed number of points into a fraction of
    THIS figure's height keeps the spacing the same whatever the shape.

    Also reserves the space it used, so tight_layout does not put a panel there.
    """
    inches = figure.get_figheight()

    def fraction(points: float) -> float:
        return 1.0 - (points / 72.0) / inches

    figure.suptitle(title, color=colours['title'], fontsize=13,
                    fontweight='bold', x=0.01, ha='left', y=fraction(16))
    if subtitle:
        figure.text(0.01, fraction(34), subtitle, color=colours['meta'],
                    fontsize=8.5, ha='left', va='top')
    figure.tight_layout(rect=[0, 0, 1, fraction(46 if subtitle else 28)])


def years_covered(run) -> str:
    """
    Which years a figure that sums over them is actually showing.

    EVERY FIGURE HERE EXCEPT `figure_pdf` SUMS THE YEAR AXIS, and none of them
    used to say so. A histogram headed "Recovered mass" over 2030-2050 looks
    exactly like the same histogram for 2050 alone -- five times smaller and
    equally plausible -- so the reader cannot tell what they are holding. It
    was asked, in exactly those words: "which year is this?"
    """
    years = sorted(str(y) for y in run.keys['Year'].unique())
    if len(years) == 1:
        return years[0]
    return f'{years[0]}\u2013{years[-1]}, all {len(years)} years summed'


def years_listed(run) -> str:
    """
    The span a PER-YEAR figure covers.

    Not `years_covered`, which ends "all N years summed" -- true of the figures
    that collapse the axis, and a plain falsehood on one that plots a point per
    year. Saying "summed" on a trajectory is worse than saying nothing, and
    DECISIONS 14 and 15 want the years named either way.
    """
    years = sorted(str(y) for y in run.keys['Year'].unique())
    if len(years) == 1:
        return years[0]
    return f'{years[0]}\u2013{years[-1]}, {len(years)} years, one point each'


def every_other(years: list) -> list:
    """
    Half the years, ends included: 2020, 2030, 2040, 2050, 2060, 2070.

    A DENSITY FIGURE IS ONE PANEL PER YEAR, and eleven of them per resource is
    a wall. Densities change slowly here -- the coefficients do not vary by
    year, so consecutive years differ only by the inflow that scales them -- and
    a panel that is nearly its neighbour costs space and adds nothing.

    Taking every second entry keeps both ends and halves the count, which on a
    5-year step gives a 10-year one. The trajectory figures still carry every
    year; this thins only the shapes.
    """
    return years[::2] if len(years) > 6 else years


def finest_layer(frame) -> str:
    """
    The deepest layer this case actually resolves.

    NOT always Layer 4. 04_02 resolves elements within a placeholder material;
    04_01 stops at material and leaves Layer 4 empty in every row. Reading it
    from the data is the only way one figure module serves both -- assuming
    Layer 4 gave 04_01 no per-resource figures at all, silently.
    """
    for column in ('Layer 4', 'Layer 3', 'Layer 2'):
        if column in frame.columns and (frame[column] != '').any():
            return column
    return 'Layer 2'


def terminal_flows(run) -> list[str]:
    """
    Flows that nothing leaves -- where the recovered and lost mass ends up.

    Read from the coefficient table rather than assumed from names, so a flow
    called `F6_refined` is terminal because nothing transfers out of it, not
    because of what it is called.
    """
    leaves = set(run.tcs['Input_FlowID'])
    arrives = set(run.tcs['Output_FlowID'])
    return sorted(arrives - leaves)


def recovered_flows(run, case: str) -> list[str]:
    """
    Which terminal flows count as recovered, from the case's processes.csv.

    Not guessed from the flow name: that counted a handoff to a separate
    recovery model as recovered here, because the word 'loss' did not appear in
    it (src/rest.py, ROLES).
    """
    from src.rest import recovered_flows as roles_for
    return roles_for(case, run.tcs)


def element_rows(run, flow: str, element: str) -> np.ndarray:
    """
    Positions of the rows holding `element` inside `flow`.

    Element-depth rows only. Summing across depths would count the same mass
    several times over, because a deeper row is part of its parent rather than
    an addition to it (MODEL_MECHANICS.md section 1).
    """
    keys = run.keys
    return np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                          & (keys[finest_layer(keys)] == element).to_numpy())


def totals_by_flow_and_element(run) -> dict[tuple[str, str], np.ndarray]:
    """{(flow, element): (draws,)} for every terminal flow and element."""
    layer = finest_layer(run.keys)
    elements = sorted({e for e in run.keys[layer].unique() if e})
    out = {}
    for flow in terminal_flows(run):
        for element in elements:
            rows = element_rows(run, flow, element)
            if rows.size:
                out[(flow, element)] = run.values[rows].sum(axis=0)
    return out


# The reported interval. 95% throughout -- figures, tables and the workbook --
# so a number quoted from one matches a number quoted from another.
INTERVAL = (2.5, 25, 50, 75, 97.5)


def _band(values: np.ndarray) -> tuple[float, float, float, float, float]:
    """Median with the 50% and 95% intervals around it."""
    return tuple(np.percentile(values, list(INTERVAL)))


# ----------------------------------------------------------------------
#  1. What the answer looks like
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
#  1b. How it moves over the years
# ----------------------------------------------------------------------

def figure_over_time(run, deterministic: pd.DataFrame | None, theme: str, unit: str):
    """
    Median recovered mass per year, per resource, with the 95% interval.

    THE FIGURE THAT ANSWERS "IS IT GROWING". Every other figure here either
    collapses the year axis into one number -- which for absolute masses adds
    2030's 10 kt to 2050's 254 kt and means nothing -- or splits it into
    separate histograms, one per year, which shows five shapes and no
    trajectory. Neither lets you see the trend, which is the first thing anyone
    asks of a projection.

    A line for the median, a band for the 95% interval, and a DASHED line for
    the deterministic run -- every coefficient at its mode, the single-value
    answer. Seeing it against the band is the point: on this case it sits high
    in every year, so the one-number answer is not a central estimate of the
    distribution around it.

    The band is computed per year across the draws and never by adding
    percentiles:
    summing a 97.5th percentile across years assumes every year hits its
    extreme in the same world, which is exactly the mistake the Monte Carlo
    exists to avoid.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    if len(years) < 2:
        return None                     # a trend through one point is a dot
    layer = finest_layer(run.keys)
    recovered = recovered_flows(run, run.case)
    if not recovered:
        return None

    keys = run.keys
    series: dict[str, dict[str, np.ndarray]] = {}
    for element in sorted({e for e in keys[layer].unique() if e}):
        median, low, high = [], [], []
        for year in years:
            rows = np.flatnonzero(
                keys['Stock/Flow ID'].isin(recovered).to_numpy()
                & (keys[layer] == element).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            totals = (run.values[rows].sum(axis=0) if rows.size
                      else np.zeros(run.draws))
            median.append(np.percentile(totals, 50))
            low.append(np.percentile(totals, 2.5))
            high.append(np.percentile(totals, 97.5))
        if max(median) > 0:
            point = []
            for year in years:
                value = (None if deterministic is None else
                         _deterministic_recovered(deterministic, run, element, year, layer))
                point.append(np.nan if value is None else value)
            series[element] = {'median': np.array(median), 'low': np.array(low),
                               'high': np.array(high), 'deterministic': np.array(point)}
    if not series:
        return None

    # ONE SHARED AXIS TAKES ITS UNIT FROM THE LARGEST SERIES. Judged on the
    # median, the boards case put a kilogram axis under five million kilograms
    # of copper and matplotlib wrote `1e6` in the corner -- an instruction to
    # multiply in your head. The legend numbers each carry their OWN unit,
    # which a printed number can do and an axis cannot.
    every = np.concatenate([s['high'] for s in series.values()])
    scale, shown = scale_for(every, unit, by='max')

    figure, axes, colours = chart(1100, 620, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]

    for index, (element, s) in enumerate(series.items()):
        colour = PALETTE[index % len(PALETTE)]
        panel.fill_between(years, s['low'] * scale, s['high'] * scale,
                           color=colour, alpha=0.18, linewidth=0)
        panel.plot(years, s['median'] * scale, color=colour, linewidth=2.0,
                   marker='o', markersize=4,
                   label=f"{element}   {readable(s['median'][0], unit)} "
                         f"\u2192 {readable(s['median'][-1], unit)}")
        if np.isfinite(s['deterministic']).any():
            panel.plot(years, s['deterministic'] * scale, color=colour,
                       linewidth=1.4, linestyle='--', alpha=0.9)

    panel.set_title('Recovered mass over time   (solid: median, with the 95% '
                    'interval.  dashed: the deterministic run)',
                    color=colours['title'], fontsize=12, fontweight='bold',
                    loc='left')
    panel.set_xlabel('year', color=colours['meta'], fontsize=11)
    panel.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=11)
    panel.set_xticks([y for y in years if y % 10 == 0] or years)
    panel.tick_params(labelsize=11)
    # No `1e6` in the corner and no `2,020` on the year axis: an offset is a
    # multiplication left for the reader, and a thousands separator on a year
    # turns it into a quantity.
    panel.ticklabel_format(style='plain', axis='y', useOffset=False)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    legend = panel.legend(fontsize=9, frameon=False, loc='upper left')
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    figure.tight_layout()
    return figure




def _in_words(flow: str) -> str:
    """`F_disassembled` -> `disassembled`. The id without its bookkeeping."""
    text = str(flow)
    if text[:2].upper() == 'F_':
        text = text[2:]
    return text.replace('_', ' ').strip()


def _road_names(branches: list[str], process: str) -> dict[str, str]:
    """
    Name the two sides of a split: the thing that happened, and it not
    happening.

    A SPLIT IS ONE DECISION AND ITS NEGATION, not two unrelated destinations.
    At `disassembly` a part is either taken out or it is not, and once it is
    taken out it is no longer in the car -- so the honest pair of names is
    `disassembled` / `not disassembled`. Naming the sides after where they end
    up instead (`own recycling`, `general recycling`) hides that they are
    complements and reads as two independent roads somebody chose between.

    The branch the process happened to is the one whose flow id shares the
    process's own stem -- `disassembly` and `F_disassembled` agree for ten
    characters. That is the modelling convention already in the case files, not
    a guess about English. Where it does not hold, or where a split has more
    than two sides, each branch keeps its own words and nothing is negated.

    THE POSITIVE SIDE COMES FIRST in the returned order, and the figure keeps
    that order: `not disassembled` is defined as the leftover of
    `disassembled`, so it is the disassembled share that the figure states and
    the other that is read off as the rest. Alphabetical order gets this right
    for `disassembled`/`not disassembled` by accident, which is not a reason to
    rely on it.
    """
    plain = {b: _in_words(b) for b in branches}
    if len(branches) != 2:
        return plain
    stem = str(process).replace('_', ' ').strip().lower()
    for did, other in (branches, branches[::-1]):
        word = plain[did].lower()
        shared = sum(1 for _ in itertools.takewhile(
            lambda pair: pair[0] == pair[1], zip(word, stem)))
        if shared >= 5:
            return {did: plain[did], other: f'not {plain[did]}'}
    return plain


def routes(run) -> dict[str, list[str]]:
    """
    The recovered flows, grouped by the ROAD each one travelled.

    A ROAD IS A SIDE OF THE SPLIT, traced back to the branch the material took
    where the network first divides. In the wiring case that split is
    `disassembly`, so the roads are `disassembled` and `not disassembled`, and
    every recovered flow belongs to whichever side it descends from.

    Two earlier versions named the roads by something nearer to hand and both
    misled. Grouping by the flow a stream leaves put `F_disassembled` in a panel
    title -- an internal identifier standing where a reader expects the name of
    a thing. Grouping by the `process` column gave `own recycling` and
    `general recycling`, which are real words but name the DESTINATION, and so
    describe two roads as though a part could take both. It cannot: taken out,
    it is not in the car any more.

    General: any case's split is found from its own network, and a case that
    never splits has one road and nothing to compare, so the figure returns
    None.
    """
    recovered = set(recovered_flows(run, run.case))
    if not recovered:
        return {}
    tcs = run.tcs
    from src.report import start_flows
    split = tcs[tcs['Input_FlowID'].isin(start_flows(tcs))]
    branches = sorted(set(split['Output_FlowID']))
    if len(branches) < 2:
        return {}
    process = split['process'].iloc[0] if 'process' in split.columns else ''

    # Walk each recovered flow back up to the branch it descends from. Parents
    # are unique here: a flow is produced once, by one process.
    parent = dict(zip(tcs['Output_FlowID'], tcs['Input_FlowID']))
    names = _road_names(branches, process)
    on_road: dict[str, list[str]] = {b: [] for b in names}   # positive first
    for flow in sorted(recovered):
        at, seen = flow, set()
        while at not in branches and at in parent and at not in seen:
            seen.add(at)
            at = parent[at]
        if at in branches:
            on_road[at].append(flow)
    return {names[b]: flows for b, flows in on_road.items() if flows}


def chosen(run, wanted) -> list[str]:
    """
    The resources a figure should cover: `figures.resources`, or all of them.

    A case can resolve twenty-odd elements, and a reader usually wants two. The
    setting narrows what is DRAWN and never what is solved -- every resource is
    still in the workbook and the summary.

    `rest` IS NOT A RESOURCE. It is the part of a parent nobody itemised --
    fibreglass, resin, plastics, solder on a board -- derived by src/rest.py so
    that composition closes to 1. It is waste: no coefficient sends it to a
    recovered flow and none ever will. Drawing it beside gold and palladium
    puts a quantity that is not a material in a figure about materials.
    """
    from src.rest import REST
    layer = finest_layer(run.keys)
    every = sorted({e for e in run.keys[layer].unique() if e and e != REST})
    if not wanted:
        return every
    asked = [r.strip() for r in wanted if r.strip()]
    return [r for r in every if r in asked] or every


def figure_routes(run, theme: str, unit: str, resources=()):
    """
    Recovered mass by ROAD, per year -- which road the material came back on.

    DECISIONS 10 and 11: the two roads are the point of the wiring case, and
    they are reported apart and also combined. `over_time.png` gives the
    combined trajectory; this one splits it, because the reason to disassemble
    at all is that the dedicated road returns more than the general shredder.

    THE TWO ROADS ARE COMPLEMENTS, AND THE FIGURE HAS TO SAY SO. A part taken
    out of the car is not in the car any anymore, so a draw that disassembles a
    lot leaves little to the shredder: the two masses are anti-correlated by
    construction, and two 95% bands drawn side by side invite the reader to
    imagine both at their upper edge at once, which cannot happen. So each
    resource gets two panels stacked in a column:

    - **top, the masses**, one line and band per road, each computed per draw;
    - **bottom, the split ITSELF** -- the share of that resource's recovered
      mass that came back on the first road, per draw. The shares sum to 100%
      in every single draw, which is exactly the correlation made visible: the
      other road is the distance up to the ceiling, and its interval is this
      one's mirrored. That panel is where an improvement in disassembly shows;
      the mass panel above it is dominated by the fleet growing.

    Each resource keeps its own mass axis (DECISIONS 13): copper's tonnage is an
    order of magnitude above aluminium's, and a shared axis would make
    aluminium's road split unreadable while looking tidy. No stacking on the
    mass panel -- a stack shows the total and hides the smaller road, which is
    the one under question.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    by_route = routes(run)
    if len(years) < 2 or len(by_route) < 2:
        return None                # one road is not a comparison

    layer = finest_layer(run.keys)
    keys = run.keys

    series: dict[str, dict] = {}
    for resource in chosen(run, resources):
        # Per draw, per year, per road. Kept as draws rather than reduced on the
        # spot: the share below has to be formed draw by draw, because the ratio
        # of two medians is not the median of the ratio.
        per_road = {}
        for route, flows in by_route.items():      # positive side of the split first
            columns = []
            for year in years:
                rows = np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy()
                    & (keys['Year'].astype(str) == str(year)).to_numpy())
                columns.append(run.values[rows].sum(axis=0) if rows.size
                               else np.zeros(run.draws))
            draws = np.column_stack(columns)          # draws x years
            if draws.mean(axis=0).max() > 0:
                per_road[route] = draws
        if len(per_road) > 1:
            series[resource] = per_road
    if not series:
        return None

    def band(draws):
        return {'median': np.percentile(draws, 50, axis=0),
                'low': np.percentile(draws, 2.5, axis=0),
                'high': np.percentile(draws, 97.5, axis=0)}

    every = np.concatenate([band(d)['high'] for roads in series.values()
                            for d in roads.values()])
    scale, shown = scale_for(every, unit)

    # Wide enough for the subtitle to fit on one line even with one resource,
    # and the split is a strip under the masses rather than a second full panel:
    # it is one number a year, and the space it needs is the space to read it.
    columns_of = len(series)
    figure, axes, colours = chart(max(560 * columns_of, 900), 560, theme,
                                  2, columns_of, height_ratios=(2.1, 1))
    # subplots(2, 1) hands back a flat pair, subplots(2, n) a 2 x n array.
    grid = np.array(axes, dtype=object).reshape(2, columns_of)

    for column, (resource, per_road) in enumerate(sorted(series.items())):
        top, bottom = grid[0][column], grid[1][column]
        first = next(iter(per_road))       # the positive side of the split
        for index, route in enumerate(per_road):
            s, colour = band(per_road[route]), PALETTE[index % len(PALETTE)]
            top.fill_between(years, s['low'] * scale, s['high'] * scale,
                             color=colour, alpha=0.18, linewidth=0)
            top.plot(years, s['median'] * scale, color=colour, linewidth=2.0,
                     marker='o', markersize=3, label=route)

        total = sum(per_road.values())
        with np.errstate(invalid='ignore', divide='ignore'):
            share = np.where(total > 0, 100 * per_road[first] / total, np.nan)
        s = {'median': np.nanpercentile(share, 50, axis=0),
             'low': np.nanpercentile(share, 2.5, axis=0),
             'high': np.nanpercentile(share, 97.5, axis=0)}
        bottom.fill_between(years, s['low'], s['high'], color=PALETTE[0],
                            alpha=0.18, linewidth=0)
        bottom.plot(years, s['median'], color=PALETTE[0], linewidth=2.0,
                    marker='o', markersize=3)

        rest = [r for r in per_road if r != first][0]
        top.set_title(f'{resource}   {s["median"][-1]:.0f}% of it came back '
                      f'{first} in {years[-1]}',
                      color=colours['title'], fontsize=10, fontweight='bold')
        top.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=8.5)
        # No x label on the top panel: the years are the same axis as the strip
        # directly under it, and the label would sit between the two.
        bottom.set_xlabel('year', color=colours['meta'], fontsize=8.5)
        bottom.set_ylabel(f'% {first}', color=colours['meta'], fontsize=8.5)
        for panel in (top, bottom):
            panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        # 0 to 100, always: the strip is a share of the whole, and the gap
        # between the line and the ceiling IS the other road. Zooming to the
        # data would make a split of 94/6 look like an even one.
        bottom.set_ylim(0, 100)
        bottom.set_title(f'the split itself -- the rest came back {rest}',
                         color=colours['meta'], fontsize=9, loc='left')
        legend = top.legend(fontsize=8, frameon=False, loc='upper left')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    header(figure, 'Recovered mass by road', colours,
           f'{years_listed(run)}.  solid: median, band: 95%.  the two roads are '
           f'complements -- taken out of the car means no longer in it -- so '
           f'the strip below is the split itself, formed per draw')
    return figure


def figure_recovery_rate(run, deterministic: pd.DataFrame | None,
                         theme: str, unit: str):
    """
    Recovered as a SHARE of what was collected, per year.

    Every other figure here reports a mass, and a mass grows with the fleet
    whatever recycling does -- 2070 recovers more than 2030 because there are
    more cars, not because anything improved. This is the one number that
    separates the two, and until now it could only be got by dividing two
    columns of the workbook by hand.

    It is also what an improvement scenario moves. A ramped coefficient barely
    shows in the absolute trajectory, which is dominated by inflow growth; it
    shows here.

    THE RATIO IS FORMED WITHIN ONE DRAW, numerator and denominator both. It has
    to be: since the inflow draws are propagated (DECISIONS 32) a draw with a
    big fleet recovers proportionally more, so dividing that draw's recovered
    mass by the MEAN inflow hands the fleet's whole spread to a number the
    fleet cannot move. That version put copper's 2020 band up to 142% -- a
    recovery rate above 100%, which is not a wide estimate but an impossible
    one. Divided within the draw the fleet cancels exactly, and what is left is
    the coefficients' uncertainty, which is what a rate is uncertain BY.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    if len(years) < 2:
        return None
    recovered = recovered_flows(run, run.case)
    if not recovered:
        return None

    from src.report import start_flows
    starts = start_flows(run.tcs)
    keys, layer = run.keys, finest_layer(run.keys)

    def collected_in(year, resource: str | None) -> np.ndarray | None:
        """
        What was collected, of the thing being asked about, PER DRAW.

        EACH RESOURCE IS DIVIDED BY ITS OWN INFLOW. Dividing copper recovered by
        the TOTAL collected mass answers a different question, and the answer
        looks like a recovery rate falling when nothing about recovery moved:
        on the wiring case copper's own recovery holds at 77-78% while its share
        of the inflow drops 36% to 28% as motors grow against harnesses. The
        first version of this figure made that mistake and reported it as
        copper being recovered worse.

        The total line divides by the whole RECOVERABLE inflow -- everything
        collected except `rest`.

        `rest` IS WASTE AND IS NOT IN THE DENOMINATOR. It is the part of a
        parent nobody itemised, derived by src/rest.py so composition closes to
        1: fibreglass, resin, plastics, solder on a board. No coefficient sends
        it to a recovered flow, so it contributes nothing to the numerator and
        never improves -- and on the boards case it is 45% of the collected
        mass. Left in, it puts a fixed ceiling of 55% on the total line and
        makes a real improvement look flat: 46.5 -> 51.9%, where the same
        improvement against the recoverable inflow is 84.1 -> 94.8%. A rate
        whose denominator is half unrecoverable by construction is not a
        recovery rate, it is a composition figure.
        """
        from src.rest import REST
        wanted = (keys['Stock/Flow ID'].isin(starts)
                  & (keys['Year'].astype(str) == str(year)))
        if resource is not None:
            wanted &= (keys[layer] == resource)
        rows = keys[wanted]
        if rows.empty:
            return None
        if resource is None:
            # Nesting: a resource row is part of its parent's, so the inflow is
            # totalled at its own shallowest depth (MODEL_MECHANICS.md 1) --
            # except that `rest` has to come off, and it only exists at the
            # finest layer. So the total is taken there instead, over the
            # resources that are not waste, which sums to the same whole minus
            # the waste.
            deep = rows[(rows[layer] != '') & (rows[layer] != REST)]
            if not deep.empty:
                rows = deep
            else:
                depth = (rows[[c for c in LAYERS if c in rows.columns]] != '').sum(axis=1)
                rows = rows[depth == depth.min()]
        return run.values[keys.index.get_indexer(rows.index)].sum(axis=0)

    lines: dict[str, dict[str, np.ndarray]] = {}
    for resource in [EVERYTHING] + chosen(run, ()):
        median, low, high = [], [], []
        for year in years:
            wanted = keys['Stock/Flow ID'].isin(recovered).to_numpy() & \
                     (keys['Year'].astype(str) == str(year)).to_numpy()
            if resource != 'every resource':
                wanted &= (keys[layer] == resource).to_numpy()
            rows = np.flatnonzero(wanted)
            total = (run.values[rows].sum(axis=0) if rows.size
                     else np.zeros(run.draws))
            inflow = collected_in(year, None if resource == EVERYTHING else resource)
            if inflow is None:
                rate = np.zeros(run.draws)
            else:
                with np.errstate(invalid='ignore', divide='ignore'):
                    rate = np.where(inflow > 0, 100 * total / inflow, np.nan)
            median.append(np.nanpercentile(rate, 50))
            low.append(np.nanpercentile(rate, 2.5))
            high.append(np.nanpercentile(rate, 97.5))
        if max(median) > 0:
            lines[resource] = {'median': np.array(median), 'low': np.array(low),
                               'high': np.array(high)}
    if not lines:
        return None

    figure, axes, colours = chart(1100, 620, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    # BANDS ONLY WHILE THEY CAN STILL BE TOLD APART. Twenty-one translucent
    # rectangles laid over each other are not twenty-one intervals, they are a
    # grey wash with lines in it, and the wash hides the lines it is meant to
    # qualify. Past a handful the bands come off and the figure says so; each
    # resource's spread is still drawn in full on its own pdf_<resource>.png.
    banded = len(lines) <= 7
    for index, (resource, s) in enumerate(lines.items()):
        colour = colours['title'] if resource == EVERYTHING \
            else PALETTE[(index - 1) % len(PALETTE)]
        width = 2.6 if resource == EVERYTHING else 1.8
        # A DASH PATTERN PER RESOURCE. Two resources given the same coefficients
        # have the same rate exactly, and one solid line then sits invisibly
        # under another -- which reads as a missing resource rather than as two
        # that agree. On the wiring case alalloy and fealloy do exactly this.
        style = '-' if resource == EVERYTHING else DASHES[(index - 1) % len(DASHES)]
        if banded:
            panel.fill_between(years, s['low'], s['high'], color=colour,
                               alpha=0.10 if resource == EVERYTHING else 0.16,
                               linewidth=0)
        panel.plot(years, s['median'], color=colour, linewidth=width,
                   linestyle=style, marker='o', markersize=4,
                   label=f"{resource}   {s['median'][0]:.1f} \u2192 "
                         f"{s['median'][-1]:.1f}%")

    panel.set_xlabel('year', color=colours['meta'], fontsize=11)
    panel.set_ylabel('recovered, % of that resource collected',
                     color=colours['meta'], fontsize=11)
    panel.set_ylim(0, 100)
    panel.set_xticks([y for y in years if y % 10 == 0] or years)
    panel.tick_params(labelsize=11)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)

    header(figure, 'Recovery rate over time', colours,
           f'{years_listed(run)}.  each resource against ITS OWN inflow, the '
           f'black line against every resource together.  `rest` is waste and '
           f'is in neither.  ratio per draw.  '
           + ('median and 95%' if banded else
              f'median only -- {len(lines)} bands would overlap into a wash; '
              f'each spread is on its own pdf figure'))

    # UNDER THE FIGURE, NOT ON IT. `loc="best"` had nowhere to go with
    # twenty-one entries and dropped the block in the middle of the lines.
    handles, labels = panel.get_legend_handles_labels()
    columns = 1 if len(labels) <= 8 else (2 if len(labels) <= 16 else 4)
    room = min(0.4, 0.06 + 0.035 * np.ceil(len(labels) / columns))
    figure.subplots_adjust(bottom=room)
    legend = figure.legend(handles, labels, fontsize=10, frameon=False,
                           ncol=columns, loc='lower center',
                           bbox_to_anchor=(0.5, 0.012), handlelength=3.2,
                           columnspacing=2.5, labelspacing=0.6)
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    return figure



def figure_fate(run, theme: str, unit: str, resources=()):
    """
    What becomes of the resource that LEAVES THE FLEET, per year.

    The model starts at what a recycler receives, so until now nothing said how
    much never got there. On the wiring case in 2070 that is the larger number
    by far: 71 kt of copper is never collected against 20 kt lost inside
    recycling, three and a half times as much. A figure that begins at
    `F_collected` cannot show it, and it is arguably the case's headline.

    Three parts, stacked, and they ARE the whole -- recovered, lost in the
    recycling process, and never collected sum to the outflow. Stacking is
    honest only when that holds, which is why the parts are MEANS: a mean is
    additive, so the stack is exact, where three medians would not add up to
    the median of their total.

    The 95% interval of the outflow is drawn as a pair of thin lines rather
    than a band per layer -- stacked bands would overlap into mud and imply an
    uncertainty on each slice that the stack cannot honestly show. Inflow is
    dashed, for context: by 2070 it has roughly met the outflow, which is what
    a fleet reaching steady state looks like.

    `inflow`, `outflow` and never-collected are UPSTREAM quantities, read for
    reporting only (src.upstream.Draws.other_flow). Nothing about the solve
    changes, and the scale between the arrays and the table is taken from the
    model's own collected mass rather than assumed.
    """
    source = getattr(run, 'upstream', None)
    if source is None or not getattr(source, 'propagates', False):
        return None
    years = sorted(int(y) for y in run.keys['Year'].unique())
    if len(years) < 2:
        return None

    from src.report import start_flows
    starts, keys = start_flows(run.tcs), run.keys
    layer = finest_layer(keys)
    recovered = recovered_flows(run, run.case)
    if not recovered:
        return None

    panels_for = chosen(run, resources)
    series: dict[str, dict[str, np.ndarray]] = {}
    for resource in panels_for:
        domains = sorted({d for d in keys.loc[keys[layer] == resource, 'Layer 2'].unique() if d})
        got = {name: [] for name in ('recovered', 'lost', 'uncollected',
                                     'outflow_low', 'outflow_high', 'inflow')}
        usable = True
        for year in years:
            def rows_of(flows):
                return np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy()
                    & (keys['Year'].astype(str) == str(year)).to_numpy())

            collected = run.values[rows_of(starts)].sum(axis=0)
            back = run.values[rows_of(recovered)].sum(axis=0)
            if collected.mean() <= 0:
                usable = False
                break
            raw = source.other_flow('collected', resource, domains, year, 0, run.draws)
            out = source.other_flow('outflow', resource, domains, year, 0, run.draws)
            into = source.other_flow('inflow', resource, domains, year, 0, run.draws)
            if raw is None or out is None or raw.mean() <= 0:
                usable = False
                break
            # The table's unit, from the model's own collected mass against the
            # array it came from. No unit constant appears here on purpose.
            scale = collected.mean() / raw.mean()
            out = out * scale
            got['recovered'].append(back.mean())
            got['lost'].append((collected - back).mean())
            got['uncollected'].append(max((out - collected).mean(), 0.0))
            got['outflow_low'].append(np.percentile(out, 2.5))
            got['outflow_high'].append(np.percentile(out, 97.5))
            got['inflow'].append(np.nan if into is None else (into * scale).mean())
        if usable and max(got['recovered']) > 0:
            series[resource] = {k: np.array(v) for k, v in got.items()}
    if not series:
        return None

    every = np.concatenate([s['outflow_high'] for s in series.values()])
    scale_to, shown = scale_for(every, unit)

    columns = min(3, len(series))
    rows_of_panels = -(-len(series) // columns)
    # At least 900 wide however few panels there are: the subtitle is one line
    # and a narrow figure cuts it off mid-sentence.
    figure, axes, colours = chart(max(470 * columns, 900),
                                  380 * rows_of_panels, theme,
                                  rows_of_panels, columns)
    panels = list(axes.ravel()) if hasattr(axes, 'ravel') else [axes]
    for spare in panels[len(series):]:
        spare.set_visible(False)

    for panel, (resource, s) in zip(panels, sorted(series.items())):
        parts = [('recovered', s['recovered'], PALETTE[1]),
                 ('lost in recycling', s['lost'], PALETTE[3]),
                 ('never collected', s['uncollected'], PALETTE[0])]
        panel.stackplot(years, *[part * scale_to for _, part, _ in parts],
                        labels=[name for name, _, _ in parts],
                        colors=[colour for _, _, colour in parts], alpha=0.85)
        # Labelled and dotted. Unlabelled thin lines crossing a stack read as
        # a boundary of the stack rather than as the interval of its total,
        # which is what they are -- the lower one passes THROUGH the coloured
        # area, so it has to say what it is.
        for position, edge in enumerate(('outflow_low', 'outflow_high')):
            panel.plot(years, s[edge] * scale_to, color=colours['title'],
                       linewidth=1.1, linestyle=(0, (2, 2)), alpha=0.8,
                       label='leaving the fleet, 95%' if position == 0 else None)
        if np.isfinite(s['inflow']).any():
            panel.plot(years, s['inflow'] * scale_to, color=colours['meta'],
                       linewidth=1.4, linestyle='--', label='entering the fleet')

        total = s['recovered'][-1] + s['lost'][-1] + s['uncollected'][-1]
        share = 100 * s['uncollected'][-1] / total if total else 0
        panel.set_title(f'{resource}   {share:.0f}% never collected in {years[-1]}',
                        color=colours['title'], fontsize=10, fontweight='bold')
        panel.set_xlabel('year', color=colours['meta'], fontsize=8.5)
        panel.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=8.5)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        legend = panel.legend(fontsize=8, frameon=False, loc='upper left')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    header(figure, 'What becomes of it, once it leaves the fleet', colours,
           f'{years_listed(run)}.  the three parts are MEANS and sum to the '
           f'outflow.  thin lines: the outflow 95%.  dashed: entering the fleet')
    return figure


def account(run, resource: str) -> dict[str, np.ndarray] | None:
    """
    One resource's whole account, per draw and per year, in the working unit.

    Every quantity the account needs, gathered once so that the figure built on
    it never has to divide a per-draw number by a mean. The keys:

        inflow        entering the fleet          (upstream)
        outflow       leaving the fleet           (upstream)
        collected     reaching a recycler         (the model's own start flow)
        uncollected   outflow - collected         (never reaches one)
        recovered     coming back as material     (the model's recovered flows)
        lost          collected - recovered       (lost inside recycling)

    They close by construction: recovered + lost + uncollected = outflow, in
    every draw and not only on average, which is what lets them be stacked.

    UPSTREAM ARRAYS ARE IN kt AND THE MODEL IS IN kg, so the three upstream
    quantities are scaled by the model's own collected mass over the upstream
    collected mass. No unit constant appears here on purpose: whatever the two
    sides are in, that ratio is the conversion between them.
    """
    source = getattr(run, 'upstream', None)
    if source is None or not getattr(source, 'propagates', False):
        return None
    from src.report import start_flows
    starts, keys = start_flows(run.tcs), run.keys
    layer = finest_layer(keys)
    recovered_ids = recovered_flows(run, run.case)
    years = sorted(int(y) for y in keys['Year'].unique())
    domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                          'Layer 2'].unique() if d})
    if not recovered_ids or not domains:
        return None

    got = {name: [] for name in ('inflow', 'outflow', 'collected',
                                 'uncollected', 'recovered', 'lost')}
    for year in years:
        def rows_of(flows):
            return np.flatnonzero(
                keys['Stock/Flow ID'].isin(flows).to_numpy()
                & (keys[layer] == resource).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())

        collected = run.values[rows_of(starts)].sum(axis=0)
        back = run.values[rows_of(recovered_ids)].sum(axis=0)
        raw = source.other_flow('collected', resource, domains, year, 0, run.draws)
        out = source.other_flow('outflow', resource, domains, year, 0, run.draws)
        into = source.other_flow('inflow', resource, domains, year, 0, run.draws)
        if collected.mean() <= 0 or raw is None or out is None or raw.mean() <= 0:
            return None
        to_working = collected.mean() / raw.mean()
        out = out * to_working
        got['inflow'].append(np.full(run.draws, np.nan) if into is None
                             else into * to_working)
        got['outflow'].append(out)
        got['collected'].append(collected)
        got['uncollected'].append(np.clip(out - collected, 0, None))
        got['recovered'].append(back)
        got['lost'].append(collected - back)
    return {name: np.column_stack(columns)      # draws x years
            for name, columns in got.items()} | {'years': np.array(years)}


def _round_step(rough: float) -> float:
    """
    The nearest step a person would actually count in: 1, 2, 2.5 or 5 times a
    power of ten.

    An axis ruled at 63.4 is an axis nobody reads a value off. Rounding the
    wanted spacing UP to one of these keeps the gridlines at numbers that can
    be added in the head, which is the whole point of ruling the axis when
    every quantity on it is meant to be compared against every other.
    """
    if not np.isfinite(rough) or rough <= 0:
        return 1.0
    power = 10.0 ** np.floor(np.log10(rough))
    for nice in (1, 2, 2.5, 5, 10):
        if rough <= nice * power:
            return float(nice * power)
    return float(10 * power)


def draw_account(panel, title: str, a: dict, roads: dict, years,
                 scale: float, shown: str, colours):
    """
    ONE ACCOUNT ON ONE SET OF AXES. Returns the per-cent axis it adds.

    Extracted so the per-case figure and the combined figure across cases
    (`04_combine_cases.py`) are the SAME picture rather than two that drift
    apart. The combined one hands in an account summed per draw across its
    cases; nothing here knows or cares which kind it was given.

    See `figure_account` for why the lines are the lines and why the rate is on
    its own axis.
    """
    def band(draws):
        return (np.nanpercentile(draws, 50, axis=0),
                np.nanpercentile(draws, 2.5, axis=0),
                np.nanpercentile(draws, 97.5, axis=0))

    mean_of = {k: np.nanmean(v, axis=0) for k, v in a.items() if k != 'years'}
    end = years[-1]

    def draw(key, name, colour, style, width, values=None):
        series = mean_of[key] if values is None else values
        if not np.isfinite(series).any():
            return
        panel.plot(years, series * scale, color=colour, linewidth=width,
                   linestyle=style, marker='o', markersize=3,
                   label=f'{name}   {series[-1] * scale:,.0f} {shown} in {end}')

    # The 95% band of what leaves the fleet: the fleet's own uncertainty, which
    # every mass on this axis inherits and none of the others can show without
    # turning the figure into mud.
    _, low, high_of_all = band(a['outflow'])
    panel.fill_between(years, low * scale, high_of_all * scale,
                       color=colours['title'], alpha=0.10, linewidth=0,
                       label='leaving the fleet, 95%')

    draw('inflow', 'entering the fleet', colours['meta'], (0, (1, 2)), 1.6)
    draw('outflow', 'leaving the fleet', colours['title'], '-', 2.4)
    draw('collected', 'reaching a recycler', colours['title'], (0, (5, 2)), 1.8)
    draw('recovered', 'recovered', PALETTE[1], '-', 2.4)
    draw('uncollected', 'never collected', PALETTE[0], (0, (4, 1, 1, 1)), 1.8)
    draw('lost', 'lost inside recycling', PALETTE[3], (0, (4, 1, 1, 1)), 1.8)
    for place, (road, draws_of) in enumerate(roads.items()):
        draw(road, f'recovered, {road}', PALETTE[(place + 4) % len(PALETTE)],
             (0, (2, 1.5)), 1.5, values=np.nanmean(draws_of, axis=0))

    # The rate, on its own axis because it is the only thing here that is not a
    # mass. Per draw, so the fleet cancels and what is left is the
    # coefficients' uncertainty.
    rate_axis = panel.twinx()
    with np.errstate(invalid='ignore', divide='ignore'):
        rate = np.where(a['collected'] > 0,
                        100 * a['recovered'] / a['collected'], np.nan)
    median, low, high = band(rate)
    rate_axis.fill_between(years, low, high, color=PALETTE[2], alpha=0.14,
                           linewidth=0)
    rate_axis.plot(years, median, color=PALETTE[2], linewidth=3.0,
                   marker='o', markersize=4,
                   label=f'RECOVERY RATE, right axis   '
                         f'{median[0]:.0f} → {median[-1]:.0f}% of what '
                         f'was collected')
    # FOUR INTERVALS ON BOTH AXES, AND NOT ONE MORE. Five labels a side is what
    # a reader takes in at a glance; ruling the mass axis every 100 against a
    # rate axis every 10 gave twenty numbers down the page and two sets of
    # gridlines that did not agree. At four apiece the two rule the SAME lines,
    # so one set of horizontal rules serves both axes and a mass on the left and
    # a per cent on the right are read off the same place.
    rate_axis.set_ylim(0, 100)
    rate_axis.set_yticks([0, 25, 50, 75, 100])
    rate_axis.set_ylabel('recovered, % of what was collected',
                         color=PALETTE[2], fontsize=14)
    rate_axis.tick_params(colors=PALETTE[2], labelsize=17)
    for side in ('top', 'left', 'bottom'):
        rate_axis.spines[side].set_visible(False)
    rate_axis.spines['right'].set_color(PALETTE[2])
    rate_axis.grid(False)

    top = float(np.nanmax(high_of_all) * scale)
    step = _round_step(top / 4)
    panel.set_ylim(0, step * 4)
    panel.set_yticks([step * n for n in range(5)])

    panel.set_title(
        f'{title}   in {end}: {mean_of["outflow"][-1] * scale:,.0f} {shown} '
        f'left the fleet, {mean_of["collected"][-1] * scale:,.0f} reached a '
        f'recycler, {mean_of["recovered"][-1] * scale:,.0f} came back',
        color=colours['title'], fontsize=13, fontweight='bold')
    panel.set_xlabel('year', color=colours['meta'], fontsize=14)
    panel.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=14)
    # Every decade, not every point. The points are still drawn as markers, so
    # nothing is hidden -- but eleven labels along the bottom is a row of
    # numbers to read where six is a scale to glance at.
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=17)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    panel.set_zorder(rate_axis.get_zorder() + 1)
    panel.patch.set_visible(False)
    return rate_axis


def account_legend(figure, for_legend, colours, rows_of: int,
                   strip_numbers: bool) -> None:
    """
    The shared legend, UNDER the figure rather than on it.

    Ten entries is a block, and a block placed anywhere inside these axes lands
    on lines: upper left is where the rate runs, centre left is where the
    inflow climbs through. Below the axes it covers nothing and reads in one
    pass across rather than as a tall column.

    ONE PANEL'S WORTH, not every panel's. Every panel draws the same lines, so
    collecting them all repeated the legend once per resource -- twenty-one
    times on the boards case, and the reserved space came out taller than the
    figure. `strip_numbers` drops each label's value where there are several
    panels, since a value belongs to one of them and each panel's title carries
    its own.
    """
    panel, rate_axis = for_legend[0]
    handles, labels = panel.get_legend_handles_labels()
    extra = rate_axis.get_legend_handles_labels()
    handles, labels = handles + extra[0], labels + extra[1]
    if strip_numbers:
        labels = [text.split('   ')[0] for text in labels]
    room = min(0.35, 0.055 + 0.038 * np.ceil(len(labels) / 3) / max(1, rows_of))
    figure.subplots_adjust(bottom=room)
    legend = figure.legend(handles, labels, fontsize=11, frameon=False,
                           ncol=3, loc='lower center',
                           bbox_to_anchor=(0.5, 0.012),
                           handlelength=3.2, columnspacing=2.5,
                           labelspacing=0.7)
    for text in legend.get_texts():
        text.set_color(colours['meta'])


def figure_account(run, theme: str, unit: str, resources=()):
    """
    THE WHOLE ACCOUNT OF A RESOURCE ON ONE SET OF AXES, so that every quantity
    can be compared against every other one directly.

    ONE AXES, NOT A PAGE OF PANELS. Panels were the first attempt and they are
    the same mistake as separate files, only smaller: the moment two quantities
    sit in different panels, comparing them means reading one axis, remembering
    a number, and looking at another. Everything here is a mass in the same
    unit, so it belongs on the same axis, and then the comparisons the case
    exists to make are just distances on the page:

        outflow to collected      what is never collected
        collected to recovered    what recycling loses
        the two roads             which one brings the material back

    The lines, all of them means, all in the same unit:

        entering the fleet        upstream inflow
        leaving the fleet         upstream outflow
        reaching a recycler       the model's own start flow
        never collected           outflow - collected
        recovered                 the model's recovered flows
        lost inside recycling     collected - recovered
        recovered, per road       one line per side of the split

    Recovered + lost + never collected = outflow in every draw, so the three
    can be read off against the outflow line without an adjustment.

    THE RECOVERY RATE IS THE ONE THING THAT IS NOT A MASS, and it is on a right
    hand axis in per cent, drawn heavier than everything else. It is the number
    that separates recycling getting better from the fleet getting bigger, and
    it cannot be compared by distance to a mass -- so it is the single line
    that says on its own axis, in its own words, what it is.

    Bands are 95%, on the outflow and on the recovery rate only. Every line
    could carry one and the figure would be mud; those two are the ones whose
    uncertainty is the point -- the fleet's, and the coefficients'. The legend
    prints each line's value in the last year, so a number is read rather than
    estimated off an axis.

    Every ratio is formed inside the draw, numerator and denominator together,
    so the fleet's own uncertainty cancels where it should (DECISIONS 32) and
    no rate can exceed 100%.
    """
    wanted = chosen(run, resources)
    by_road = routes(run)
    accounts = {r: a for r in wanted if (a := account(run, r)) is not None}
    if not accounts:
        return None

    years = next(iter(accounts.values()))['years']
    if len(years) < 2:
        return None

    def band(draws):
        return (np.nanpercentile(draws, 50, axis=0),
                np.nanpercentile(draws, 2.5, axis=0),
                np.nanpercentile(draws, 97.5, axis=0))

    layer, keys = finest_layer(run.keys), run.keys
    roads_for: dict[str, dict[str, np.ndarray]] = {}
    for resource in accounts:
        per_road = {}
        for road, flows in by_road.items():
            columns = []
            for year in years:
                rows = np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy()
                    & (keys['Year'].astype(str) == str(year)).to_numpy())
                columns.append(run.values[rows].sum(axis=0) if rows.size
                               else np.zeros(run.draws))
            draws = np.column_stack(columns)
            if draws.mean(axis=0).max() > 0:
                per_road[road] = draws
        roads_for[resource] = per_road

    every = np.concatenate([np.nanpercentile(a['outflow'], 97.5, axis=0)
                            for a in accounts.values()])
    scale, shown = scale_for(every, unit)

    # A GRID ONCE THERE ARE MORE THAN THREE. One row is right for the case that
    # asked for two or three resources; the boards case resolves twenty-one, and
    # twenty-one panels in a row is a strip nobody can hold in view.
    across = min(3, len(accounts))
    rows_of = -(-len(accounts) // across)
    figure, axes, colours = chart(1180 * across, 820 * rows_of, theme,
                                  rows_of, across)
    panels = list(axes.ravel()) if hasattr(axes, 'ravel') else [axes]
    for spare in panels[len(accounts):]:
        spare.set_visible(False)
    for_legend = []

    for panel, (resource, a) in zip(panels, sorted(accounts.items())):
        rate_axis = draw_account(panel, resource, a,
                                 roads_for.get(resource, {}),
                                 years, scale, shown, colours)
        for_legend.append((panel, rate_axis))

    names = ', '.join(sorted(accounts))
    header(figure, f'{names}: the whole account, on one axis', colours,
           f'{years_listed(run)}.  masses are MEANS in the same unit, so any two '
           f'can be compared by the distance between them: recovered + lost + '
           f'never collected = the outflow.  band: the outflow 95%.  '
           f'the rate is per draw, on the right axis')
    account_legend(figure, for_legend, colours, rows_of,
                   strip_numbers=len(accounts) > 1)
    return figure


def in_the_fleet(run, resource: str):
    """
    What is still in the cars: the net annual flow, and the stock it builds.

    EVERY YEAR THE ARRAYS HOLD, not the years the case solves. A stock is the
    integral of a net flow, so integrating a five-yearly sample would either
    miss four years in five or need a step factor pretending to be data. The
    upstream export is annual and this reads all of it -- the case's own year
    selection governs what is SOLVED, not what is integrated.

    THE ACCUMULATION STARTS AT THE FIRST YEAR THE ARRAYS HOLD, and what was
    already on the road then is NOT in it. The export begins in 2020, by which
    time some electric cars existed, so this is what the fleet has taken in
    SINCE 2020 and not the whole in-use stock. It is close to it -- the fleet
    was small in 2020 against 11 Mt by 2065 -- but close is not the same, and a
    figure that called it the stock would be asserting a zero nobody exported.
    The subtitle says which it is; if a stock array is exported upstream one
    day, read that instead of integrating.

    Returns (years, net, stock, layer name) with net and stock as (years,
    draws), or None when this case has no upstream arrays.
    """
    source = getattr(run, 'upstream', None)
    if source is None or not getattr(source, 'propagates', False):
        return None
    keys, layer = run.keys, finest_layer(run.keys)
    domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                          'Layer 2'].unique() if d})
    if not domains:
        return None

    every = [int(year) for year in source.years]
    net = []
    for year in every:
        into = source.other_flow('inflow', resource, domains, year, 0, run.draws)
        out = source.other_flow('outflow', resource, domains, year, 0, run.draws)
        if into is None or out is None:
            return None
        net.append(into - out)
    net = np.array(net)                       # years x draws, arrays' own unit
    return every, net, np.cumsum(net, axis=0), layer


def figure_trapped(run, theme: str, unit: str, resources=()):
    """
    HOW MUCH IS LOCKED UP IN CARS ON THE ROAD, per year and in total.

    Between what a fleet takes in and what it gives back there is a stock, and
    it is the largest number in this whole model: copper bought years ago,
    still driving around, unavailable to anybody. Nothing here showed it --
    `account.png` draws the inflow and the outflow as two lines and leaves the
    gap between them to be imagined.

    Two panels, because they are two different quantities and one axis would
    be a lie about units:

    - **per year**, the net flow: what entered minus what left. Positive while
      the fleet grows. Where it crosses zero the fleet has stopped absorbing
      copper and begins returning more than it takes -- the single most
      consequential date on this figure, so it is marked and named.
    - **over time**, the stock that net flow builds: what the fleet has taken
      in and not yet given back, counting from the first year exported.

    Both are computed over EVERY year the upstream arrays hold, not the years
    the case solves, because a stock is an integral (see `in_the_fleet`). The
    solved years are marked on the stock so the two figures can be lined up.

    Scaled to the model's own unit by the same ratio `account` uses: the
    model's collected mass over the array's, so no unit constant appears here.
    """
    wanted = chosen(run, resources)
    series = {}
    for resource in wanted:
        found = in_the_fleet(run, resource)
        if found is None:
            continue
        every, net, stock, layer = found
        a = account(run, resource)
        if a is None:
            continue
        # The arrays are in their own unit and the model in another. The ratio
        # is taken from the model's own collected mass against the array it came
        # from, exactly as `account` does it.
        keys = run.keys
        domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                              'Layer 2'].unique() if d})
        first = int(a['years'][0])
        raw = run.upstream.other_flow('collected', resource, domains, first,
                                      0, run.draws)
        if raw is None or raw.mean() <= 0:
            continue
        to_working = float(np.nanmean(a['collected'][:, 0]) / raw.mean())
        series[resource] = {'years': every, 'net': net * to_working,
                            'stock': stock * to_working,
                            'solved': [int(y) for y in a['years']]}
    if not series:
        return None

    every_stock = np.concatenate([np.nanpercentile(s['stock'], 97.5, axis=1)
                                  for s in series.values()])
    scale, shown = scale_for(every_stock, unit)

    across = min(3, len(series))
    down = -(-len(series) // across)
    figure, axes, colours = chart(1180 * across, 900 * down, theme,
                                  2 * down, across, height_ratios=(1, 1.5) * down)
    grid = np.array(axes, dtype=object).reshape(2 * down, across)

    for index, (resource, s) in enumerate(sorted(series.items())):
        top, bottom = grid[2 * (index // across)][index % across], \
            grid[2 * (index // across) + 1][index % across]
        years = s['years']

        def band(draws):
            return (np.nanpercentile(draws, 50, axis=1),
                    np.nanpercentile(draws, 2.5, axis=1),
                    np.nanpercentile(draws, 97.5, axis=1))

        median, low, high = band(s['net'])
        top.fill_between(years, low * scale, high * scale, color=PALETTE[0],
                         alpha=0.16, linewidth=0)
        top.plot(years, median * scale, color=PALETTE[0], linewidth=2.2)
        top.axhline(0, color=colours['title'], linewidth=1.0)
        # WHERE IT TURNS. The first year the fleet gives back more than it
        # takes is a date somebody wants; reading it off a crossing is guessing.
        turned = next((year for year, value in zip(years, median) if value < 0),
                      None)
        if turned is not None:
            top.axvline(turned, color=colours['meta'], linewidth=1.0,
                        linestyle=(0, (3, 3)))
            top.annotate(f'{turned}: the fleet starts giving back\nmore than it '
                         f'takes', xy=(turned, 0), xytext=(6, 8),
                         textcoords='offset points', color=colours['meta'],
                         fontsize=11)
        top.set_title(f'{resource}: entering the fleet minus leaving it, per year',
                      color=colours['title'], fontsize=13, fontweight='bold')
        top.set_ylabel(f'net ({shown}/yr)', color=colours['meta'], fontsize=13)

        median, low, high = band(s['stock'])
        bottom.fill_between(years, low * scale, high * scale, color=PALETTE[1],
                            alpha=0.18, linewidth=0)
        bottom.plot(years, median * scale, color=PALETTE[1], linewidth=2.6)
        peak = int(np.argmax(median))
        bottom.annotate(f'{years[peak]}: {median[peak] * scale:,.0f} {shown} '
                        f'held since {years[0]}',
                        xy=(years[peak], median[peak] * scale),
                        xytext=(-10, 12), textcoords='offset points',
                        color=colours['title'], fontsize=12, fontweight='bold',
                        ha='right')
        marks = [y for y in s['solved'] if y in years]
        bottom.plot(marks, [median[years.index(y)] * scale for y in marks],
                    linestyle='none', marker='o', markersize=4,
                    color=PALETTE[1])
        bottom.set_title(f'{resource}: how much the fleet is holding, '
                         f'accumulated from {years[0]}',
                         color=colours['title'], fontsize=13, fontweight='bold')
        bottom.set_ylabel(f'in the fleet ({shown})', color=colours['meta'],
                          fontsize=13)
        bottom.set_xlabel('year', color=colours['meta'], fontsize=13)

        for panel in (top, bottom):
            panel.tick_params(labelsize=15)
            panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)

    first = min(s['years'][0] for s in series.values())
    header(figure, 'What is trapped in the fleet', colours,
           f'every year the upstream arrays hold, {every_years(series)}.  '
           f'solid: median, band: 95%.  the lower panel is the running total of '
           f'the upper one, so it counts from {first} and does NOT include what '
           f'was already on the road then.  dots mark the years the model solves')
    return figure


def every_years(series: dict) -> str:
    """`1975-2070, 96 years` from whichever series is longest. Not a setting."""
    years = max((s['years'] for s in series.values()), key=len)
    return f'{years[0]}-{years[-1]}, {len(years)} years'


def losses(run, resource: str) -> dict[str, np.ndarray] | None:
    """
    Every reason this resource fails to come back, per year per draw.

    One entry per loss flow, NAMED BY ITS PROCESS (DECISIONS 33) -- `own
    recycling`, `general recycling` -- plus `never collected`, which is not a
    flow in any network here: it is the outflow that never reached a recycler
    at all, and it is read from the upstream arrays.

    General: a case's own `processes` table says which flows are losses, so a
    case with one loss reason gets one wedge and a case with five gets five.
    """
    a = account(run, resource)
    if a is None:
        return None
    from src.rest import flow_roles
    keys, layer = run.keys, finest_layer(run.keys)
    years = [int(y) for y in a['years']]
    roles = flow_roles(run.case)
    process_of = dict(zip(run.tcs['Output_FlowID'], run.tcs.get(
        'process', pd.Series(dtype=str))))

    found: dict[str, np.ndarray] = {}
    for flow, role in roles.items():
        if role != 'loss':
            continue
        name = str(process_of.get(flow, flow)).replace('_', ' ')
        columns = []
        for year in years:
            rows = np.flatnonzero(
                (keys['Stock/Flow ID'] == flow).to_numpy()
                & (keys[layer] == resource).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            columns.append(run.values[rows].sum(axis=0) if rows.size
                           else np.zeros(run.draws))
        block = np.column_stack(columns)
        if block.mean(axis=0).max() > 0:
            found[f'lost in {name}'] = found.get(f'lost in {name}', 0) + block

    found['never collected'] = a['uncollected']
    return {'years': np.array(years), 'reasons': found,
            'outflow': a['outflow'], 'recovered': a['recovered']}


def figure_losses(run, theme: str, unit: str, resources=()):
    """
    WHERE IT GOES WHEN IT DOES NOT COME BACK, one wedge per reason.

    `account.png` says how much is lost; this says WHY, which is the question
    that decides what to do about it. On the wiring case the answer is blunt:
    far more copper is lost by never being collected than by anything that
    happens inside a recycling plant, so a better process is worth less than a
    better collection rate. That is not visible until the reasons are apart.

    Stacked, and the parts ARE the whole -- every reason plus what was
    recovered sums to the outflow. Stacking is honest only when that holds,
    which is why the parts are MEANS: a mean is additive, so the stack is
    exact, where medians would not add up to the median of their total.

    Beside it, the same thing as shares of the outflow, per draw. The masses
    grow with the fleet whatever recycling does; the shares are what a
    programme moves, and they are where an improvement shows.
    """
    wanted = chosen(run, resources)
    series = {r: found for r in wanted if (found := losses(run, r)) is not None}
    series = {r: s for r, s in series.items() if s['reasons']}
    if not series:
        return None

    every = np.concatenate([np.nanmean(s['outflow'], axis=0)
                            for s in series.values()])
    scale, shown = scale_for(every, unit)

    across = len(series)
    figure, axes, colours = chart(1150 * across, 780, theme, 1, 2 * across)
    grid = np.array(axes, dtype=object).reshape(2 * across)

    for index, (resource, s) in enumerate(sorted(series.items())):
        mass, share = grid[2 * index], grid[2 * index + 1]
        years = list(s['years'])
        names = sorted(s['reasons'], key=lambda n: -float(
            np.nanmean(s['reasons'][n][:, -1])))
        means = [np.nanmean(s['reasons'][name], axis=0) for name in names]
        colours_for = [PALETTE[(place + 3) % len(PALETTE)]
                       for place in range(len(names))]

        mass.stackplot(years, *[m * scale for m in means], labels=names,
                       colors=colours_for, alpha=0.85)
        # NO OUTFLOW LINE HERE. It is six times the losses on the wiring case,
        # so drawing it put the whole stack in the bottom sixth of the panel --
        # scale for a quantity this figure is not about, at the cost of the one
        # it is. The outflow is the denominator of the panel beside it, and the
        # title carries its number.
        end, biggest = years[-1], names[0]
        total = sum(m[-1] for m in means) * scale
        mass.set_title(
            f'{resource}: why it did not come back   in {end}, '
            f'{total:,.0f} {shown} of {np.nanmean(s["outflow"], axis=0)[-1] * scale:,.0f} '
            f'lost, most of it {biggest}',
            color=colours['title'], fontsize=12, fontweight='bold')
        mass.set_ylabel(f'lost ({shown})', color=colours['meta'], fontsize=13)

        with np.errstate(invalid='ignore', divide='ignore'):
            for place, name in enumerate(names):
                fraction = np.where(s['outflow'] > 0,
                                    100 * s['reasons'][name] / s['outflow'],
                                    np.nan)
                median = np.nanpercentile(fraction, 50, axis=0)
                low = np.nanpercentile(fraction, 2.5, axis=0)
                high = np.nanpercentile(fraction, 97.5, axis=0)
                share.fill_between(years, low, high, color=colours_for[place],
                                   alpha=0.16, linewidth=0)
                share.plot(years, median, color=colours_for[place],
                           linewidth=2.0, marker='o', markersize=3,
                           label=f'{name}   {median[0]:.0f} → {median[-1]:.0f}%')
        share.set_title(f'{resource}: the same, as a share of what left the fleet',
                        color=colours['title'], fontsize=12, fontweight='bold')
        share.set_ylabel('% of the outflow', color=colours['meta'], fontsize=13)

        for panel in (mass, share):
            panel.set_xlabel('year', color=colours['meta'], fontsize=13)
            panel.set_xticks([y for y in years if y % 10 == 0] or years)
            panel.tick_params(labelsize=15)
            panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
            legend = panel.legend(fontsize=11, frameon=False, loc='upper left')
            for text in legend.get_texts():
                text.set_color(colours['meta'])

    header(figure, 'Why it does not come back', colours,
           f'{years_listed(run)}.  one wedge per reason; the reasons plus what '
           f'was recovered sum to the outflow, which is why they are MEANS.  '
           f'shares are medians with 95%, formed per draw')
    return figure


def figure_pdf_grid(run, deterministic: pd.DataFrame | None, theme: str,
                    unit: str, resources=(), bins: int = 120):
    """
    Every resource's density, on one page: one row per resource, one column
    per year.

    THE `pdf_<resource>` FIGURES SIDE BY SIDE. Those are one file each, so
    comparing three alloys means opening three files and holding them in your
    head. This is the same panels in one grid, so a comparison is a glance:
    ACROSS a row is one resource through the years, DOWN a column is the
    resources in one year.

    THE DETERMINISTIC RUN IS ON IT, dashed, as it is on the `pdf_<resource>`
    figures. Leaving it off was an omission: the distance between that line and
    the distribution around it is the reason to draw a distribution at all, and
    a page of shapes without it says only that the answer is uncertain, not that
    the single-value answer sits anywhere in particular inside it.

    Absolute mass on every axis and nothing rescaled. Each panel is scaled to
    its own data, which is what makes every shape visible at full size -- at
    2050 aluminium alloy is 27 kt beside copper's 254, and a shared axis makes
    one of them a needle. Differing scales are safe here because every panel
    states its own median and 95% interval: the numbers are read, not estimated
    off an axis.

    Two things were tried before this and both were wrong. Dividing each curve
    by its own median made them overlay beautifully and made copper's
    uncertainty -- ten times aluminium's in kilotonnes -- look identical to it.
    Sharing one axis per year was honest and unreadable.
    """
    years = every_other(sorted(int(y) for y in run.keys['Year'].unique()))
    layer = finest_layer(run.keys)
    recovered = recovered_flows(run, run.case)
    if not recovered or not years:
        return None

    keys = run.keys
    series: dict[str, dict[int, np.ndarray]] = {}
    for element in chosen(run, resources):
        per_year = {}
        for year in years:
            rows = np.flatnonzero(
                keys['Stock/Flow ID'].isin(recovered).to_numpy()
                & (keys[layer] == element).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            if rows.size:
                per_year[year] = run.values[rows].sum(axis=0)
        if per_year and max(v.max() for v in per_year.values()) > 0:
            series[element] = per_year
    if not series:
        return None

    figure, axes, colours = chart(430 * len(years), 300 * len(series), theme,
                                  len(series), len(years))
    grid = np.atleast_2d(axes) if hasattr(axes, 'shape') else np.array([[axes]])

    for row, (element, per_year) in enumerate(series.items()):
        colour = PALETTE[row % len(PALETTE)]
        for column, year in enumerate(years):
            panel = grid[row][column]
            values = per_year.get(year)
            if values is None or values.std() == 0:
                panel.set_visible(False)
                continue
            scale, shown = scale_for(values, unit)
            density, edges = np.histogram(values * scale, bins=bins, density=True)
            centres = 0.5 * (edges[:-1] + edges[1:])
            density = np.convolve(density, np.ones(5) / 5.0, mode='same')

            median = float(np.median(values)) * scale
            low = float(np.percentile(values, 2.5)) * scale
            high = float(np.percentile(values, 97.5)) * scale
            panel.axvspan(low, high, color=colours['meta'], alpha=0.10)
            panel.fill_between(centres, density, color=colour, alpha=0.35, linewidth=0)
            panel.plot(centres, density, color=colour, linewidth=1.8)
            panel.axvline(median, color=colours['title'], linewidth=1.3)

            point = (None if deterministic is None else
                     _deterministic_recovered(deterministic, run, element, year, layer))
            if point is not None:
                panel.axvline(point * scale, color=PALETTE[3], linewidth=1.4,
                              linestyle='--')

            panel.set_title(f'{element}   {year}', color=colours['title'],
                            fontsize=11, fontweight='bold', loc='left')
            label = (f'median {median:,.3g} {shown}   '
                     f'95% {low:,.3g}\u2013{high:,.3g}')
            if point is not None:
                label += f'   deterministic {point * scale:,.3g}'
            panel.set_xlabel(label, color=colours['meta'], fontsize=9)
            panel.set_ylabel('density' if column == 0 else '',
                             color=colours['meta'], fontsize=9)
            panel.set_yticks([])
            panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)

    header(figure, 'Probability density of recovered mass', colours,
           'the pdf_<resource> figures on one page; absolute mass, each panel on '
           'its own axis. Solid line: the median. Dashed: the deterministic run')
    return figure


# ----------------------------------------------------------------------
#  2. Which flows are uncertain
# ----------------------------------------------------------------------

# How much a result's relative spread has to move between the first year and
# the last before the earlier year is drawn beside it.
SPREAD_MOVED = 1.0          # percentage points


def figure_spread(run, theme: str, unit: str, most: int = 20,
                  both_years: bool = True):
    """
    THE SPREAD ITSELF, as a bar per result -- and where it changed over time,
    both years' bars side by side on the same row.

    Each bar is that result's own distribution: the thick part the 50%
    interval, the thin line the 95%, the tick its median.

    MASS ON A LOG AXIS, so both questions are answered by one picture: WHERE the
    bar sits is how much, HOW WIDE it is is how uncertain. A percent-of-own-mean
    axis was tried and centred every bar on 100%, which showed the spread and
    threw away the magnitude -- 232 kt and 2.5 kt drawn on top of each other.
    Linear mass fails the other way: these results span 0.02 to 232 kt and the
    same result grows a thousandfold across the years, so the small ones and the
    early years vanish. On a log axis a relative spread has the same width
    wherever it sits, so the bars stay comparable to one another and between
    the two years.

    THE SECOND BAR APPEARS ONLY WHERE IT DIFFERS. A result whose spread has
    moved by at least SPREAD_MOVED points gets the first year drawn above the
    last, hollow, so the two can be compared directly. The rest get one bar,
    because their spread is identical in every year -- the coefficients do not
    vary by year, so it is a fixed fraction of a growing mass.

    On this case two of fourteen move, both COPPER, the one material present in
    both Wiring and Motors: the mix of the two shifts as the fleet turns over,
    so copper's total is a blend in changing proportion and the blend's spread
    moves with it.

    `both_years=False` draws the last year alone, and IS WORTH HAVING SEPARATELY
    rather than being the same figure with less on it. The two early bars are
    what force the axis down to 1e-2: showing them costs three decades to
    display two pale bars, and every other bar is squeezed for it. Dropped, the
    range is 2.5 to 232 kt -- two decades instead of five -- and each bar is
    roughly twice as wide to read. Both are drawn: `spread.png` for the change,
    `spread_last_year.png` for reading the answer.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    if not years:
        return None
    first, last = years[0], years[-1]
    layer = finest_layer(run.keys)
    keys, values = run.keys, run.values
    ends = terminal_flows(run)
    if not ends:
        return None

    def at(flow: str, element: str, year: int):
        rows = np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                              & (keys[layer] == element).to_numpy()
                              & (keys['Year'].astype(str) == str(year)).to_numpy())
        if not rows.size:
            return None
        totals = values[rows].sum(axis=0)
        mean = float(totals.mean())
        if mean <= 0:
            return None
        low, q1, median, q3, high = _band(totals)
        return (low, q1, median, q3, high, 100 * (high - low) / mean, median)

    entries = []
    for flow in ends:
        for element in sorted({e for e in keys[layer].unique() if e}):
            now = at(flow, element, last)
            if now is None:
                continue
            before = (at(flow, element, first)
                      if both_years and first != last else None)
            was = (before if before is not None
                   and abs(before[5] - now[5]) >= SPREAD_MOVED else None)
            entries.append((f'{flow}  \u00b7  {element}', now, was))
    if not entries:
        return None

    entries.sort(key=lambda item: item[1][2])          # by mass, biggest at top
    trimmed = max(0, len(entries) - most)
    entries = entries[-most:]
    scale, shown = scale_for(
        np.array([v for _, now, _ in entries for v in now[:5]]), unit)

    figure, panel, colours = chart(1080, 150 + 44 * len(entries), theme)

    def bar(low, q1, median, q3, high, y, colour, hollow):
        panel.plot([low, high], [y, y], color=colour, linewidth=1.4,
                   alpha=0.45 if hollow else 0.6)
        panel.plot([q1, q3], [y, y], color=colour,
                   linewidth=7 if hollow else 10, solid_capstyle='butt',
                   alpha=0.35 if hollow else 0.85)
        panel.plot([median], [y], marker='|', markersize=11 if hollow else 14,
                   color=colours['title'], markeredgewidth=1.5,
                   alpha=0.55 if hollow else 1.0)

    for position, (name, now, was) in enumerate(entries):
        colour = PALETTE[position % len(PALETTE)]
        if was is None:
            bar(*[v * scale for v in now[:5]], position, colour, hollow=False)
            panel.annotate(f'{now[2] * scale:,.3g}   \u00b1{now[5]:,.0f}%',
                           (now[4] * scale, position), textcoords='offset points',
                           xytext=(10, 0), va='center', fontsize=9.5,
                           color=colours['meta'])
        else:
            bar(*[v * scale for v in was[:5]], position + 0.21, colour, hollow=True)
            bar(*[v * scale for v in now[:5]], position - 0.21, colour, hollow=False)
            for band_, offset, year in ((was, 0.21, first), (now, -0.21, last)):
                panel.annotate(f'{year}   {band_[2] * scale:,.3g}   '
                               f'\u00b1{band_[5]:,.0f}%',
                               (band_[4] * scale, position + offset),
                               textcoords='offset points', xytext=(10, 0),
                               va='center', fontsize=9, color=colours['meta'])

    changed = sum(1 for _, _, was in entries if was is not None)
    # LOG, so position says how much and width says how uncertain, on one axis.
    # These results span 0.02 kt to 232 kt and the same result grows a
    # thousandfold across the years -- linear shows the big ones and nothing
    # else. On a log axis a relative spread has the same width wherever it sits,
    # so the bars are comparable to each other AND between the two years.
    panel.set_xscale('log')

    # LIMITS FROM THE DATA, not from margins(). A margin is a FRACTION OF THE
    # AXIS RANGE, and on a log axis that range is in decades -- so 0.45 padded
    # by nearly half a decade at each end and left the bars squeezed into the
    # middle third with empty space out to 1e-3 and 1e4. Explicit limits: a
    # little air on the left, and enough on the right for the labels, which are
    # drawn in data coordinates and would otherwise fall off the figure.
    drawn = [v for _, now, was in entries for band_ in (now, was)
             if band_ is not None for v in band_[:5] if v > 0]
    panel.set_xlim(min(drawn) * scale / 2.5, max(drawn) * scale * 12)
    panel.xaxis.set_minor_locator(
        __import__('matplotlib').ticker.LogLocator(base=10, subs=tuple(range(2, 10)),
                                                   numticks=100))
    panel.grid(True, axis='x', which='minor', color=colours['rule'],
               linewidth=0.4, alpha=0.5)

    panel.set_yticks(range(len(entries)))
    panel.set_yticklabels([e[0] for e in entries], fontsize=9.5,
                          color=colours['meta'])
    panel.set_xlabel(f'mass ({shown}, log scale)   '
                     f'(thick: 50% interval, thin: 95%, tick: median)',
                     color=colours['meta'], fontsize=9.5)
    panel.margins(y=0.05)
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    header(figure, f'How much, and how sure -- in {last}'
           + (f'   --  the {len(entries)} widest of {len(entries) + trimmed}'
              if trimmed else ''), colours,
           (f'{changed} result(s) changed since {first} and carry both years, '
            f'{first} above {last}. The rest are identical in every year.'
            if changed else
            f'every result, {last} only. Nothing here changed between {first} '
            f'and {last}; spread.png carries the ones that did.'
            if not both_years else
            f'no result changed between {first} and {last}.'))
    return figure


def figure_mode_vs_mean(run, deterministic: pd.DataFrame, theme: str, unit: str):
    """
    How far the deterministic run sits from the Monte Carlo mean, IN ONE YEAR.

    Expressed as a percentage of the mean, because the absolute gap is only
    meaningful next to the size of the flow. A bar to the left means the
    deterministic run *understates* the expected mass.

    ONE YEAR, NOT EVERY YEAR ADDED TOGETHER. This used to total 2020's mass
    with 2070's on both sides of the ratio -- the same defect distribution.png
    was deleted for (DECISIONS.md 14). The percentage still came out close to
    right, because both halves were wrong in the same direction, which is the
    worst kind of wrong: it looks correct and nothing justifies it. The value
    written at the end of each bar was the one that gave it away -- a mass no
    year has.

    Which year is shown barely matters here, and the figure SAYS SO with a
    measurement instead of leaving the reader to hope. `drift` is the largest
    distance any one gap travels across all the years in the run; on this case
    it is under a percentage point on a scale reaching -48%, because the gap is
    a ratio of two quantities that both scale with the inflow.
    """
    if deterministic is None:
        return None
    years = sorted(int(y) for y in run.keys['Year'].unique())
    if not years:
        return None
    last = years[-1]
    keys, layer = run.keys, finest_layer(run.keys)
    year_of = keys['Year'].astype(int).to_numpy()
    point_year = deterministic['Year'].astype(int).to_numpy()

    def gap(flow: str, element: str, year: int):
        """(percent away, deterministic mass, mean mass) for one year, or None."""
        rows = np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                              & (keys[layer] == element).to_numpy()
                              & (year_of == year))
        point_rows = deterministic[(deterministic['Stock/Flow ID'] == flow).to_numpy()
                                   & (deterministic[layer] == element).to_numpy()
                                   & (point_year == year)]
        if not rows.size or not len(point_rows):
            return None
        mean = float(run.values[rows].sum(axis=0).mean())
        if mean <= 0:
            return None
        point = float(point_rows['Value'].sum())
        return 100.0 * (point - mean) / mean, point, mean

    pairs = [(flow, element) for flow in terminal_flows(run)
             for element in sorted({e for e in keys[layer].unique() if e})]
    here = {pair: found for pair in pairs if (found := gap(*pair, last)) is not None}
    if not here:
        return None

    scale, shown = scale_for(np.array([found[2] for found in here.values()]), unit)

    entries, drift = [], 0.0
    for (flow, element), (percent, point, mean) in here.items():
        entries.append((f'{flow}  ·  {element}', percent,
                        point * scale, mean * scale))
        across = [found[0] for year in years
                  if (found := gap(flow, element, year)) is not None]
        if len(across) > 1:
            drift = max(drift, max(across) - min(across))

    # THE BIGGEST GAPS, NOT EVERY ROW. 04_01 produces hundreds of
    # (flow, resource) pairs, and one bar each made a figure 10,277 pixels tall
    # whose labels ran into one another. The tail of near-zero gaps is exactly
    # the part nobody reads; the workbook's Distribution sheet has all of them.
    shown_count = min(len(entries), MAX_BARS)
    trimmed = len(entries) - shown_count
    entries.sort(key=lambda item: abs(item[1]), reverse=True)
    entries = entries[:shown_count]
    entries.sort(key=lambda item: item[1])

    figure, panel, colours = chart(880, 90 + 26 * len(entries), theme)
    for position, (name, percent, point, mean) in enumerate(entries):
        colour = PALETTE[3] if percent < 0 else PALETTE[2]
        panel.barh(position, percent, height=0.62, color=colour, alpha=0.85)
        offset = 0.4 if percent >= 0 else -0.4
        panel.text(percent + offset, position, f'  {point:,.1f} vs {mean:,.1f} {shown}',
                   color=colours['meta'], fontsize=7.5, va='center',
                   ha='left' if percent >= 0 else 'right')

    panel.axvline(0, color=colours['node'], linewidth=1.0)
    # Room for the value written at the end of each bar. Without it the longest
    # bar's label runs off the axis and collides with the tick labels.
    reach = max(abs(entry[1]) for entry in entries)
    panel.set_xlim(-reach * 1.9 if any(e[1] < 0 for e in entries) else 0,
                   reach * 1.9 if any(e[1] >= 0 for e in entries) else 0)
    panel.set_yticks(range(len(entries)))
    panel.set_yticklabels([entry[0] for entry in entries], fontsize=8.5,
                          color=colours['node'])
    panel.set_xlabel('deterministic run, as % away from the Monte Carlo mean',
                     color=colours['meta'], fontsize=9)
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    panel.grid(False, axis='y')
    header(figure, f'Deterministic run against the Monte Carlo mean, in {last}'
           + (f'   --  the {len(entries)} largest gaps of '
              f'{len(entries) + trimmed}' if trimmed else ''), colours,
           f'a bar to the left means the single-value answer understates the '
           f'expected mass.  across {years[0]}-{years[-1]} no gap moves by more '
           f'than {drift:.1f} percentage points, so this year stands for all of '
           f'them.')
    return figure


# ----------------------------------------------------------------------
#  4. How many draws are needed
# ----------------------------------------------------------------------

def figure_convergence(run, theme: str, unit: str):
    """
    Running mean and running 5th/95th percentile against the number of draws.

    The mean settles long before the tails do, so a draw count chosen by
    watching the mean will understate the interval. This figure is how the
    setting in `data.draws` should be argued for rather than guessed.
    """
    totals = totals_by_flow_and_element(run)
    if not totals:
        return None

    # The largest flow: the one whose convergence anyone will care about.
    name, values = max(totals.items(), key=lambda item: item[1].mean())
    scale, shown = scale_for(values, unit)
    values = values * scale
    steps = np.unique(np.geomspace(20, run.draws, 60).astype(int))

    running_mean = np.array([values[:n].mean() for n in steps])
    running_low = np.array([np.percentile(values[:n], INTERVAL[0]) for n in steps])
    running_high = np.array([np.percentile(values[:n], INTERVAL[-1]) for n in steps])

    figure, panel, colours = chart(720, 340, theme)
    panel.fill_between(steps, running_low, running_high, color=PALETTE[0], alpha=0.18,
                       label='2.5th to 97.5th percentile')
    panel.plot(steps, running_mean, color=PALETTE[0], linewidth=1.8, label='mean')
    for series, style in ((running_low, ':'), (running_high, ':')):
        panel.plot(steps, series, color=PALETTE[0], linewidth=1.0, linestyle=style)

    panel.axhline(values.mean(), color=colours['meta'], linewidth=0.9, linestyle='--')
    panel.set_xscale('log')
    panel.set_xlabel('draws used', color=colours['meta'], fontsize=9)
    panel.set_ylabel(f'{name[0]} · {name[1]}  ({shown})', color=colours['meta'], fontsize=9)
    panel.set_title(f'Convergence with draw count   ({years_covered(run)})',
                    color=colours['title'],
                    fontsize=12, fontweight='bold', loc='left')
    legend = panel.legend(fontsize=8, frameon=False)
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    figure.tight_layout()
    return figure


# ----------------------------------------------------------------------
#  5. What drives the spread
# ----------------------------------------------------------------------

def figure_sensitivity(run, theme: str):
    """
    Rank correlation between each coefficient and the largest result.

    Spearman rather than Pearson: the model is multiplicative, so the
    relationship between a coefficient and an output is monotone but not
    straight, and a linear correlation would understate it.

    A coefficient with a high absolute correlation is where narrowing the input
    range would narrow the answer. One near zero is not worth arguing about,
    however uncertain it is in itself.
    """
    from scipy import stats

    totals = totals_by_flow_and_element(run)
    if not totals or run.tc_values is None or not run.report.get('uncertain'):
        return None

    name, values = max(totals.items(), key=lambda item: item[1].mean())

    correlations = []
    for position in range(len(run.tcs)):
        coefficient = run.tc_values[position]
        if coefficient.std() == 0:
            continue
        rho = stats.spearmanr(coefficient, values).statistic
        row = run.tcs.iloc[position]
        correlations.append((f"{row['Input_FlowID']} → {row['Output_FlowID']}"
                             f"  ·  {row['Input_layer_key']}→{row['TC_target_key']}",
                             0.0 if np.isnan(rho) else float(rho)))
    if not correlations:
        return None

    correlations.sort(key=lambda item: abs(item[1]))
    correlations = correlations[-18:]

    figure, panel, colours = chart(760, 60 + 24 * len(correlations), theme)
    for position, (label_text, rho) in enumerate(correlations):
        panel.barh(position, rho, height=0.62,
                   color=PALETTE[2] if rho >= 0 else PALETTE[3], alpha=0.85)
    panel.axvline(0, color=colours['node'], linewidth=1.0)
    panel.set_yticks(range(len(correlations)))
    panel.set_yticklabels([item[0] for item in correlations], fontsize=7.5,
                          color=colours['node'])
    panel.set_xlim(-1, 1)
    panel.set_xlabel(f'rank correlation with {name[0]} · {name[1]}',
                     color=colours['meta'], fontsize=9)
    panel.set_title(f'Sensitivity to each coefficient   ({years_covered(run)})',
                    color=colours['title'], fontsize=12, fontweight='bold', loc='left')
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    panel.grid(False, axis='y')
    figure.tight_layout()
    return figure


# ----------------------------------------------------------------------

def draw_all(run, deterministic: pd.DataFrame | None, out_dir: str, formats,
             dpi: int, theme: str, unit: str = 'Mg', case: str = '',
             resources=()) -> list[str]:
    """
    Draw every Monte Carlo figure. Returns the paths written.

    EVERY CASE GETS ITS OWN FOLDER (figure_style.folder_for). These used to be
    written flat, so two cases wrote `mc_pdf_Cu.png` to the same place and the
    second run replaced the first's silently -- a figures/ directory holding
    half of one study and half of another, with nothing but the file timestamps
    to say which was which.
    """
    import matplotlib.pyplot as plt

    out_dir = folder_for(out_dir, case) if case else out_dir

    # DRAWN ONE AT A TIME, hence the lambdas. Building the list eagerly built
    # every figure before writing any of them, so all 27 of the boards case's
    # were open at once -- matplotlib says so at 20 -- each holding its own
    # histogram of 200,000 draws. They were closed after writing, which looked
    # like enough right up until a case had more than a handful of resources.
    figures = [
        ('over_time', lambda: figure_over_time(run, deterministic, theme, unit)),
        ('recovery_rate',
         lambda: figure_recovery_rate(run, deterministic, theme, unit)),
        ('account', lambda: figure_account(run, theme, unit, resources)),
        ('trapped', lambda: figure_trapped(run, theme, unit, resources)),
        ('losses', lambda: figure_losses(run, theme, unit, resources)),
        ('routes', lambda: figure_routes(run, theme, unit, resources)),
        ('fate', lambda: figure_fate(run, theme, unit, resources)),
        ('pdf_all',
         lambda: figure_pdf_grid(run, deterministic, theme, unit, resources)),
        ('spread', lambda: figure_spread(run, theme, unit)),
        ('spread_last_year',
         lambda: figure_spread(run, theme, unit, both_years=False)),
        ('mode_vs_mean',
         lambda: figure_mode_vs_mean(run, deterministic, theme, unit)),
        ('convergence', lambda: figure_convergence(run, theme, unit)),
        ('sensitivity', lambda: figure_sensitivity(run, theme)),
    ]

    # One distribution figure per resource: the histograms ARE the result, and a
    # single combined panel hides which one is uncertain and which is not.
    #
    # At the finest layer the case resolves, NOT always Layer 4 -- 04_01 stops at
    # material and leaves Layer 4 empty, which produced no per-resource figures
    # at all rather than an error.
    layer = finest_layer(run.keys)
    for resource in chosen(run, resources):
        figures.append((f'pdf_{resource}',
                        # bound now, not at call time: a bare `resource` would
                        # be the last one for every entry in the list.
                        lambda resource=resource: figure_pdf(
                            run, resource, deterministic, theme, unit, layer=layer)))

    written = []
    for stem, draw in figures:
        figure = draw()
        if figure is None:
            continue
        written.extend(write(figure, out_dir, stem, formats, dpi))
        plt.close(figure)
    return written


# ----------------------------------------------------------------------
#  6. The distribution itself, per element and per year
# ----------------------------------------------------------------------

def recovered_rows(run, element: str, year, layer: str = 'Layer 4') -> np.ndarray:
    """
    Row positions for one resource recovered in one year, across all routes.

    `layer` because the finest layer is not always Layer 4: 04_02 resolves
    elements, 04_01 stops at material and leaves Layer 4 empty everywhere.
    """
    keys = run.keys
    recovered = recovered_flows(run, run.case)
    return np.flatnonzero(
        keys['Stock/Flow ID'].isin(recovered).to_numpy()
        & (keys[layer] == element).to_numpy()
        & (keys['Year'].astype(str) == str(year)).to_numpy())


def figure_pdf(run, element: str, deterministic: pd.DataFrame | None,
               theme: str, unit: str, layer: str = 'Layer 4'):
    """
    The probability density of one element's recovered mass, one panel per year.

    A histogram of the draws IS the distribution the Monte Carlo produced --
    everything else in this module is a summary of it. Reading it next to the
    deterministic line is the whole argument for running the Monte Carlo: a
    single-value answer is one point inside a shape, and usually not its centre.
    """
    years = every_other(sorted(run.keys['Year'].astype(str).unique()))
    panels_with_data = [y for y in years if recovered_rows(run, element, y, layer).size]
    if not panels_with_data:
        return None

    columns = min(len(panels_with_data), 3)
    rows = int(np.ceil(len(panels_with_data) / columns))
    figure, axes, colours = chart(340 * columns, 260 * rows, theme, rows, columns)
    panels = np.atleast_1d(axes).ravel()

    for panel, year in zip(panels, panels_with_data):
        positions = recovered_rows(run, element, year, layer)
        totals = run.values[positions].sum(axis=0)
        scale, shown = scale_for(totals, unit)
        totals = totals * scale

        # Freedman-Diaconis: the bin width that suits the data, so more draws
        # give a smoother curve instead of the same 60 ragged bars.
        bins = min(200, max(30, int(np.sqrt(totals.size) / 2)))
        panel.hist(totals, bins=bins, density=True, color=PALETTE[0],
                   alpha=0.75, edgecolor='none')

        low, _, median, _, high = _band(totals)
        panel.axvspan(low, high, color=colours['meta'], alpha=0.10)
        panel.axvline(totals.mean(), color=colours['title'], linewidth=1.5)

        if deterministic is not None:
            point = _deterministic_recovered(deterministic, run, element, year, layer)
            if point is not None:
                panel.axvline(point * scale, color=PALETTE[3], linewidth=1.5,
                              linestyle='--')

        panel.set_title(f'{year}   median {median:,.3g} {shown}',
                        color=colours['title'], fontsize=10, fontweight='bold')
        panel.set_xlabel(f'{shown}', color=colours['meta'], fontsize=8.5)
        panel.set_ylabel('density', color=colours['meta'], fontsize=8.5)

    for panel in panels[len(panels_with_data):]:
        panel.axis('off')

    header(figure, f'{element} recovered per year', colours,
           'solid: Monte Carlo mean    dashed: deterministic    '
           'shaded: 95% interval')
    return figure


def _deterministic_recovered(deterministic, run, element: str, year,
                             layer: str = 'Layer 4') -> float | None:
    recovered = recovered_flows(run, run.case)
    rows = deterministic[(deterministic['Stock/Flow ID'].isin(recovered))
                         & (deterministic[layer] == element)
                         & (deterministic['Year'].astype(str) == str(year))]
    return float(rows['Value'].sum()) if len(rows) else None
