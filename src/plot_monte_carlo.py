"""
src/plot_monte_carlo.py
=======================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

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
import os

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


def resource_key(frame) -> str:
    """
    Add each row's own resource to `frame` and return the column's name.

    A CASE DOES NOT HAVE ONE DEPTH, which is what `finest_layer` below assumes.
    The traction motor resolves the magnet to elements -- Nd, Pr, Dy, Tb at
    Layer 4 -- while copper, aluminium, steel and lamination stop at materials
    in Layer 3. Picking one column for the whole case picks Layer 4, because the
    rare earths fill it, and every metal row is then blank there: no copper
    figure was drawn at all, and the metals never reached the headline table
    either (2026-09-25, see src/report.resource_of).

    Written onto the frame rather than returned as a Series so the seventeen
    `keys[layer] == resource` comparisons in this module keep working unchanged.
    Idempotent: called again on the same frame it recomputes in place.

    IT ALSO MARKS `own_depth`, because matching the resource is not enough to
    sum it. See `own`.
    """
    layers = [column for column in LAYERS if column in frame.columns]
    if layers:
        deepest = frame[layers[::-1]].astype(str)
        out = deepest.iloc[:, 0].copy()
        for column in deepest.columns[1:]:
            out = out.where(out != '', deepest[column])
        frame['resource'] = out.fillna('')
        depth = (frame[layers].astype(str) != '').sum(axis=1)
        shallowest = depth.groupby(
            [frame['Stock/Flow ID'], frame['Year'].astype(str),
             frame['resource']]).transform('min')
        frame['own_depth'] = (depth == shallowest).to_numpy()
    elif 'resource' not in frame.columns:
        frame['resource'] = ''
        frame['own_depth'] = True
    return 'resource'


def own(frame) -> np.ndarray:
    """
    Rows that are their resource's OWN depth, within their flow and year.

    ⚠️ MATCHING THE RESOURCE IS NOT ENOUGH TO SUM IT. A component named after
    the thing it is made of answers the same name twice -- a `copper` component
    holding a `copper` material -- and the child is the whole of its parent, so
    the two rows carry the same mass. Adding both doubles it.

    Upstream does this as a matter of course: 04_03 exports copper, aluminium,
    lamination, steel and magnet as components, 04_04 all twelve battery parts.
    Only the electronics cases escape, because there a component and its
    material have different names (`Wiring`/`copper`, `PCB`/`Ag`).

    Found on 2026-09-28 in the Sankey (DEFECTS 3.21) and, the same day, here --
    `account` read copper's collected mass as 140.94 kt against a true 70.47,
    and because `lost` is `collected - recovered` while recovered flows hold
    one depth only, copper appeared to lose 91.7 kt of the 70.5 it had. The
    account still CLOSED, because closure is by construction.

    Grouping on (flow, year, resource) is what makes it safe where a resource
    legitimately appears twice: copper in Wiring and copper in Motors are two
    rows at the SAME depth in the same flow, and both are kept and added.
    """
    if 'own_depth' not in frame.columns:
        resource_key(frame)
    return frame['own_depth'].to_numpy()


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


def handed_flows(run, case: str) -> list[str]:
    """
    Which terminal flows hold mass HANDED ON: sent to a separate model, so
    neither recovered here nor lost here (src/rest.py, ROLES).

    The black mass of a mechanical-only road is the plain example. It is not
    metal recovered by this recycler and it is not destroyed either; it goes on
    to be processed elsewhere, and a number that called it "lost inside
    recycling" would be wrong about what happens to it. Every case before
    2026-10-08 had no mass in such a flow, so for them this is empty in effect
    and nothing they draw changes.
    """
    from src.rest import flow_roles
    roles = flow_roles(case)
    return sorted(f for f in terminal_flows(run) if roles.get(f) == 'handoff')


def element_rows(run, flow: str, element: str) -> np.ndarray:
    """
    Positions of the rows holding `element` inside `flow`.

    Element-depth rows only. Summing across depths would count the same mass
    several times over, because a deeper row is part of its parent rather than
    an addition to it (MODEL_MECHANICS.md section 1).
    """
    keys = run.keys
    return np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                          & (keys[resource_key(keys)] == element).to_numpy())


def totals_by_flow_and_element(run) -> dict[tuple[str, str], np.ndarray]:
    """{(flow, element): (draws,)} for every terminal flow and element."""
    layer = resource_key(run.keys)
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

def figure_over_time(run, deterministic: pd.DataFrame | None, theme: str,
                     unit: str, resources=()):
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
    layer = resource_key(run.keys)
    recovered = recovered_flows(run, run.case)
    if not recovered:
        return None

    keys = run.keys
    series: dict[str, dict[str, np.ndarray]] = {}
    # ⚠️ THE RESOURCES THIS STUDY IS ABOUT. This drew every resource in the
    # data whatever `figures.resources` said -- nine lines on the traction
    # study, five of which are the bulk metals that come back either way. They
    # are not the question here (DECISIONS 29) and they crowd the ones that
    # are. Asked for on 2026-09-28: *"I am not interested in al, steel but REE
    # and copper."* The metals remain on `spread`, `mode_vs_mean` and the
    # total Sankey, which read every resource regardless.
    for element in chosen(run, resources):
        median, low, high = [], [], []
        for year in years:
            rows = np.flatnonzero(
                keys['Stock/Flow ID'].isin(recovered).to_numpy()
                & (keys[layer] == element).to_numpy() & own(keys)
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

    # ⚠️ A LOG MASS AXIS, so that every legend number can be READ OFF. On one
    # shared linear axis running to copper's 55 kt, dysprosium's 928 kg lies on
    # the zero line: the legend said `928 kg` where the reader could see
    # nothing, which is the same fault as a title quoting what a figure cannot
    # show. Removing the number would leave a flat invisible line with a name,
    # so the axis changes instead. `spread.png` is log for exactly this reason.
    #
    # Only when the resources actually span orders of magnitude -- on a case
    # whose resources are alike, a log axis makes a real difference look small.
    positive = [v for s in series.values()
                for v in (s['median'][0], s['median'][-1]) if v > 0]
    logarithmic = bool(positive) and max(positive) / min(positive) >= 100
    if logarithmic:
        panel.set_yscale('log')

    panel.set_title('Recovered mass over time   (solid: median, with the 95% '
                    'interval.  dashed: the deterministic run)',
                    color=colours['title'], fontsize=12, fontweight='bold',
                    loc='left')
    panel.set_xlabel('year', color=colours['meta'], fontsize=11)
    panel.set_ylabel(f'mass per year ({shown}/year)',
                     color=colours['meta'], fontsize=11)
    panel.set_xticks([y for y in years if y % 10 == 0] or years)
    panel.tick_params(labelsize=11)
    # No `1e6` in the corner and no `2,020` on the year axis: an offset is a
    # multiplication left for the reader, and a thousands separator on a year
    # turns it into a quantity. A log axis has no ScalarFormatter to ask, and
    # labels its decades itself.
    if not logarithmic:
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

    ⚠️ THE SPLIT IS NOT ALWAYS AT THE FIRST FLOW. The fleet traction case
    divides twice: at `F_collected`, where a vehicle is collected or is not,
    and then at `F_captured`, where the motor is taken out or stays in the hulk
    to be shredded. Only the second is a road -- the first has nothing
    recovered on its other side, because a vehicle nobody collected yields
    nothing. Testing the first flow only, this returned no roads at all for
    that case and the whole point of it, which road the material came back on,
    went unanswered.

    So a split with material recovered below exactly ONE of its branches is not
    a choice, and the search steps through it to that branch. A split with
    several such branches is where the search stops, and the road test below
    decides whether it is roads or material streams.
    """
    recovered = set(recovered_flows(run, run.case))
    if not recovered:
        return {}
    tcs = run.tcs
    from src.report import start_flows
    parent = dict(zip(tcs['Output_FlowID'], tcs['Input_FlowID']))

    def _below(branch: str) -> list[str]:
        """The recovered flows that descend from one branch."""
        found = []
        for flow in sorted(recovered):
            at, seen = flow, set()
            while at != branch and at in parent and at not in seen:
                seen.add(at)
                at = parent[at]
            if at == branch:
                found.append(flow)
        return found

    at_flows = sorted(start_flows(tcs))
    while True:
        split = tcs[tcs['Input_FlowID'].isin(at_flows)]
        branches = sorted(set(split['Output_FlowID']))
        if len(branches) < 2:
            return {}
        bearing = [b for b in branches if _below(b)]
        if len(bearing) != 1:
            break
        at_flows = bearing            # step through, it was never a choice

    # ⚠️ A ROAD SPLIT SENDS THE SAME RESOURCE TWO WAYS. A network can divide at
    # its first flow without there being any road: the shredder case divides
    # into `F_cu_stream`, `F_al_stream`, `F_ndfeb_stream`, `F_steel_stream`,
    # which are MATERIAL streams, each carrying a resource none of the others
    # does. Read as roads they gave four, and the account figure then drew
    # `recovered, ndfeb stream` for dysprosium at 0.3396 kt beside `recovered`
    # at 0.3396 kt -- one number, twice, under two names.
    # ⚠️ TESTED ON THE BRANCHES RECOVERED MATERIAL DESCENDS FROM, and on those
    # only. My first attempt at this test included `F_loss_upstream`, which
    # carries EVERY resource by construction, so it overlapped with all of them
    # and the four streams were read as roads again.
    carries = {branch: {str(r) for r in rows['TC_target_key'] if str(r)}
               for branch, rows in split.groupby('Output_FlowID')}
    process = split['process'].iloc[0] if 'process' in split.columns else ''

    # Each recovered flow belongs to the branch it descends from. Parents are
    # unique here: a flow is produced once, by one process.
    names = _road_names(branches, process)
    on_road = {b: _below(b) for b in names}                  # positive first

    # A road split sends the SAME resource more than one way. Branches that
    # carry disjoint resources are material STREAMS, and a stream is not a
    # choice -- see the note above.
    travelled = [carries.get(b, set()) for b, flows in on_road.items() if flows]
    if not any(a & b for i, a in enumerate(travelled)
               for b in travelled[i + 1:]):
        return {}
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
    layer = resource_key(run.keys)
    every = sorted({e for e in run.keys[layer].unique() if e and e != REST})
    if not wanted:
        return every
    asked = [r.strip() for r in wanted if r.strip()]
    return [r for r in every if r in asked] or every


# ⚠️ `figure_routes` WAS HERE AND IS GONE, 2026-09-29. It drew each resource's
# recovered mass on each road, plus the split as a strip underneath, and on the
# traction fleet case it came out 7,777 pixels wide to report one number:
# 98-99% of every rare earth comes back on the disassembly road, 93-97% of the
# copper.
#
# Removed at Matthias's instruction: *"I do not want such routes figures. One
# sees that shredding does not work."*
#
# THE NUMBER WAS RIGHT AND THE QUESTION WAS WRONG, which is the part worth
# keeping. A share of what COMES BACK folds two different things together --
# the shredder road gets only 7% of the motors AND recovers 2% of their rare
# earth -- and reports them as one figure that makes the road look irrelevant
# rather than bad. What the fork actually costs is already on the Sankey, on
# `account_<r>.png` (which still draws a line per road) and in the workbook's
# `Contributions` sheet, where it can be read exactly.
#
# `routes()` itself stays: `figure_account` and `05_combine_cases.py` both use
# it to label their per-road lines.


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
    keys, layer = run.keys, resource_key(run.keys)

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
            wanted &= (keys[layer] == resource) & own(keys)
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
                wanted &= (keys[layer] == resource).to_numpy() & own(keys)
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
    layer = resource_key(keys)
    recovered = recovered_flows(run, run.case)
    handed = handed_flows(run, run.case)
    if not recovered:
        return None

    panels_for = chosen(run, resources)
    series: dict[str, dict[str, np.ndarray]] = {}
    for resource in panels_for:
        domains = sorted({d for d in keys.loc[keys[layer] == resource, 'Layer 2'].unique() if d})
        got = {name: [] for name in ('recovered', 'handed', 'lost', 'uncollected',
                                     'outflow_low', 'outflow_high', 'inflow')}
        usable = True
        for year in years:
            def rows_of(flows):
                return np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy() & own(keys)
                    & (keys['Year'].astype(str) == str(year)).to_numpy())

            collected = run.values[rows_of(starts)].sum(axis=0)
            back = run.values[rows_of(recovered)].sum(axis=0)
            gave = run.values[rows_of(handed)].sum(axis=0)       # zeros when there are none
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
            got['handed'].append(gave.mean())
            got['lost'].append((collected - back - gave).mean())
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
        # Handed on is a part of the outflow only where something is. A case
        # without it keeps its three parts, so the figure is the one it was.
        if s['handed'].max() > 0:
            parts.insert(1, ('handed on, not counted here', s['handed'], PALETTE[5]))
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

        total = (s['recovered'][-1] + s['handed'][-1] + s['lost'][-1]
                 + s['uncollected'][-1])
        share = 100 * s['uncollected'][-1] / total if total else 0
        panel.set_title(f'{resource}   {share:.0f}% never collected in {years[-1]}',
                        color=colours['title'], fontsize=10, fontweight='bold')
        panel.set_xlabel('year', color=colours['meta'], fontsize=8.5)
        panel.set_ylabel(f'mass per year ({shown}/year)',
                         color=colours['meta'], fontsize=8.5)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        legend = panel.legend(fontsize=8, frameon=False, loc='upper left')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    header(figure, 'What becomes of it, once it leaves the fleet', colours,
           f'{years_listed(run)}.  the three parts are MEANS and sum to the '
           f'outflow.  thin lines: the outflow 95%.  dashed: entering the fleet')
    return figure


def account(run, resource: str, domain: str | None = None) -> dict[str, np.ndarray] | None:
    """
    One resource's whole account, per draw and per year, in the working unit.

    Every quantity the account needs, gathered once so that the figure built on
    it never has to divide a per-draw number by a mean. The keys:

        inflow        entering the fleet          (upstream)
        outflow       leaving the fleet           (upstream)
        collected     reaching a recycler         (the model's own start flow)
        uncollected   outflow - collected         (never reaches one)
        recovered     coming back as material     (the model's recovered flows)
        handed        handed on to a separate model (the `handoff` flows)
        lost          collected - recovered - handed   (lost inside recycling)

    They close by construction: recovered + handed + lost + uncollected =
    outflow, in every draw and not only on average, which is what lets them be
    stacked. `handed` is zero for every case without a `handoff` flow, and then
    `lost` is what it always was.

    UPSTREAM ARRAYS ARE IN kt AND THE MODEL IS IN kg, so the three upstream
    quantities are scaled by the model's own collected mass over the upstream
    collected mass. No unit constant appears here on purpose: whatever the two
    sides are in, that ratio is the conversion between them.

    `domain` narrows the whole account to ONE STREAM -- Wiring, Motors, PCB or
    Sensors -- rather than the case as a whole. A case carries several, and
    "which stream returns the copper" cannot be asked of a case-level total.
    Both sides narrow together: the upstream arrays are read for that domain
    alone and the model's rows are filtered on it, so the account still closes.
    """
    # CACHED ON THE RUN. `figure_account`, `figure_losses`, `figure_trapped`
    # and the shared-unit scan below each ask for the same account, so it was
    # being rebuilt four times per resource -- every one of them re-reading the
    # upstream arrays for every year.
    store = getattr(run, '_accounts', None)
    if store is None:
        store = {}
        try:
            run._accounts = store
        except AttributeError:
            store = None
    if store is not None and (resource, domain) in store:
        return store[(resource, domain)]

    source = getattr(run, 'upstream', None)
    if source is None or not getattr(source, 'propagates', False):
        return None
    from src.report import start_flows
    starts, keys = start_flows(run.tcs), run.keys
    layer = resource_key(keys)
    recovered_ids = recovered_flows(run, run.case)
    handed_ids = handed_flows(run, run.case)
    years = sorted(int(y) for y in keys['Year'].unique())
    domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                          'Layer 2'].unique() if d})
    if domain is not None:
        domains = [d for d in domains if d == domain]
    if not recovered_ids or not domains:
        return None

    got = {name: [] for name in ('inflow', 'outflow', 'collected',
                                 'uncollected', 'recovered', 'handed', 'lost')}
    for year in years:
        def rows_of(flows):
            wanted = (keys['Stock/Flow ID'].isin(flows).to_numpy()
                      & (keys[layer] == resource).to_numpy() & own(keys)
                      & (keys['Year'].astype(str) == str(year)).to_numpy())
            if domain is not None:
                wanted &= (keys['Layer 2'] == domain).to_numpy()
            return np.flatnonzero(wanted)

        collected = run.values[rows_of(starts)].sum(axis=0)
        back = run.values[rows_of(recovered_ids)].sum(axis=0)
        gave = run.values[rows_of(handed_ids)].sum(axis=0)     # zeros when there are none
        raw = source.other_flow('collected', resource, domains, year, 0, run.draws)
        out = source.other_flow('outflow', resource, domains, year, 0, run.draws)
        into = source.other_flow('inflow', resource, domains, year, 0, run.draws)
        if collected.mean() <= 0 or raw is None or out is None or raw.mean() <= 0:
            if store is not None:
                store[(resource, domain)] = None
            return None
        to_working = collected.mean() / raw.mean()
        out = out * to_working
        got['inflow'].append(np.full(run.draws, np.nan) if into is None
                             else into * to_working)
        got['outflow'].append(out)
        got['collected'].append(collected)
        got['uncollected'].append(np.clip(out - collected, 0, None))
        got['recovered'].append(back)
        got['handed'].append(gave)
        got['lost'].append(collected - back - gave)
    built = {name: np.column_stack(columns)     # draws x years
             for name, columns in got.items()} | {'years': np.array(years)}
    if store is not None:
        store[(resource, domain)] = built
    return built


def _round_step(rough: float) -> float:
    """
    The nearest step a person would actually count in: 1, 1.5, 2, 2.5, 3, 4 or
    5 times a power of ten.

    An axis ruled at 63.4 is an axis nobody reads a value off. Rounding the
    wanted spacing UP to one of these keeps the gridlines at numbers that can
    be added in the head, which is the whole point of ruling the axis when
    every quantity on it is meant to be compared against every other.

    ⚠️ IT USED TO OFFER ONLY 1, 2, 2.5 AND 5, and that wastes the panel. A top
    of 24.3 rounds its quarter-step from 6.08 up to 10 and rules the axis to
    40: the data reaches the middle and the upper 40% is white.
    `05_combine_cases` added the finer ladder on 2026-09-25 as `_tight_step`
    and this one was left coarse. Said on 2026-09-29: *"the axis scales are
    quite often shit. Use the full space."*
    """
    if not np.isfinite(rough) or rough <= 0:
        return 1.0
    power = 10.0 ** np.floor(np.log10(rough))
    for nice in (1, 1.5, 2, 2.5, 3, 4, 5, 10):
        if rough <= nice * power:
            return float(nice * power)
    return float(10 * power)


def _ruling(top: float) -> tuple[float, int]:
    """
    A step and a count for an axis reaching `top`, wasting as little as it can.

    FOUR INTERVALS OR FIVE, whichever leaves less white above the data. Fixed
    at four, a top of 24.3 rules to 40; at five the same data rules to 25. Both
    are readable; one of them uses the panel.
    """
    if not np.isfinite(top) or top <= 0:
        return 1.0, 4
    return min(((_round_step(top / n), n) for n in (4, 5)),
               key=lambda pair: pair[0] * pair[1])


def draw_account(panel, title: str, a: dict, roads: dict, years,
                 scale: float, shown: str, colours, unit: str = 'kg',
                 show_title: bool = True):
    """
    ONE ACCOUNT ON ONE SET OF AXES. Returns the per-cent axis it adds.

    Extracted so the per-case figure and the combined figure across cases
    (`05_combine_cases.py`) are the SAME picture rather than two that drift
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
        # ⚠️ THE LEGEND NAMES THE LINE AND NOTHING ELSE. It used to print each
        # line's first and last value, and on a linear axis running to
        # kilotonnes the first value is pressed flat against zero -- so the
        # legend asserted `4.8 kg` where the reader can see nothing, and
        # `0 kt` where the line plainly rises. Said on 2026-09-28: *"what you
        # write which can not be seen in the figures has no place there."*
        # The numbers are in the workbook's Recovered sheet, where they can be
        # read exactly instead of estimated off a flattened axis.
        panel.plot(years, series * scale, color=colour, linewidth=width,
                   linestyle=style, marker='o', markersize=3, label=name)

    # TWO BANDS, AND THEY ARE THE TWO THE FIGURE EXISTS FOR.
    #
    # The outflow's: the fleet's own uncertainty, which every mass on this axis
    # inherits.
    #
    # ⚠️ AND RECOVERED'S, WHICH WAS MISSING. `recovered` is what this whole
    # stage computes -- the Monte Carlo's actual output -- and it was the one
    # line drawn as a bare mean, while the outflow, which this model does not
    # compute at all, carried the only band. Asked on 2026-09-29: *"why is
    # there no uncertainty band for the recovered?"*
    #
    # The old defence was that the recovery rate's band already showed the
    # coefficients' uncertainty. It does not cover this. The rate is formed per
    # draw, so the fleet's uncertainty CANCELS in it (DECISIONS 32) -- that is
    # the point of forming it that way. So the rate band shows the
    # coefficients alone, the outflow band shows the fleet alone, and the
    # uncertainty on the recovered MASS, which is both together and is the
    # number anyone actually quotes, appeared nowhere on the figure.
    #
    # `lost inside recycling` deliberately gets no band: it is
    # collected - recovered, so its interval is this one mirrored, and drawing
    # it would be the same information twice at twice the ink.
    _, low, high_of_all = band(a['outflow'])
    panel.fill_between(years, low * scale, high_of_all * scale,
                       color=colours['title'], alpha=0.10, linewidth=0,
                       label='leaving the fleet, 95%')
    _, back_low, back_high = band(a['recovered'])
    panel.fill_between(years, back_low * scale, back_high * scale,
                       color=PALETTE[1], alpha=0.20, linewidth=0,
                       label='recovered, 95%')

    draw('inflow', 'entering the fleet', colours['meta'], (0, (1, 2)), 1.6)
    draw('outflow', 'leaving the fleet', colours['title'], '-', 2.4)
    draw('collected', 'reaching a recycler', colours['title'], (0, (5, 2)), 1.8)
    draw('recovered', 'recovered', PALETTE[1], '-', 2.4)
    draw('uncollected', 'never collected', PALETTE[0], (0, (4, 1, 1, 1)), 1.8)
    draw('lost', 'lost inside recycling', PALETTE[3], (0, (4, 1, 1, 1)), 1.8)
    # Only where some mass is handed on. A case without a `handoff` flow has an
    # all-zero array here and draws exactly the lines it always did.
    if 'handed' in mean_of and np.nanmax(mean_of['handed']) > 0:
        draw('handed', 'handed on, not counted here', PALETTE[5], (0, (1, 1.5)), 2.0)
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
                   marker='o', markersize=4, label='recovery rate')
    # FOUR INTERVALS ON BOTH AXES, AND NOT ONE MORE. Five labels a side is what
    # a reader takes in at a glance; ruling the mass axis every 100 against a
    # rate axis every 10 gave twenty numbers down the page and two sets of
    # gridlines that did not agree. At four apiece the two rule the SAME lines,
    # so one set of horizontal rules serves both axes and a mass on the left and
    # a per cent on the right are read off the same place.
    rate_axis.set_ylim(0, 100)
    rate_axis.set_yticks([0, 25, 50, 75, 100])
    rate_axis.set_ylabel('recovery rate (%)', color=PALETTE[2], fontsize=15)
    rate_axis.tick_params(colors=PALETTE[2], labelsize=17)
    for side in ('top', 'left', 'bottom'):
        rate_axis.spines[side].set_visible(False)
    rate_axis.spines['right'].set_color(PALETTE[2])
    rate_axis.grid(False)

    top = float(np.nanmax(high_of_all) * scale)
    step, count = _ruling(top)
    panel.set_ylim(0, step * count)
    panel.set_yticks([step * n for n in range(count + 1)])

    # ⚠️ THE TITLE SAYS WHAT THE PANEL IS. It does not summarise it.
    #
    # It has carried two wrong statements in one day. First `Dy in 2070: 2 kt
    # left the fleet, 1 reached a recycler, 0 came back` -- a snapshot on a
    # figure about eleven years, rounded until dysprosium read as never coming
    # back. Then `N% of it recovered` placed directly after `leaving the
    # fleet`, where `it` reads as the outflow while the rate drawn is over
    # COLLECTED: 24.3% against 21.4%, the wrong quantity, not a loose word.
    #
    # Both survived being looked at because NEITHER COULD BE CHECKED ON THE
    # FIGURE: the mass axis is linear to kilotonnes, so the early years lie
    # flat on zero and no reader can tell 2.83 t from nothing, or one
    # denominator from another. A claim a figure cannot demonstrate does not
    # belong on it -- it belongs where it can be read exactly, which is the
    # workbook.
    # Named only when there is more than one panel. With one resource to a
    # figure the header above already says which resource it is, and repeating
    # it directly underneath is a second title saying nothing new.
    if show_title:
        panel.set_title(f'{title}', color=colours['title'], fontsize=13,
                        fontweight='bold')
    panel.set_xlabel('year', color=colours['meta'], fontsize=14)
    panel.set_ylabel(f'mass per year ({shown}/year)',
                     color=colours['meta'], fontsize=14)
    # Every decade, not every point. The points are still drawn as markers, so
    # nothing is hidden -- but eleven labels along the bottom is a row of
    # numbers to read where six is a scale to glance at.
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=17)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    panel.set_zorder(rate_axis.get_zorder() + 1)
    panel.patch.set_visible(False)
    return rate_axis


def account_legend(figure, for_legend, colours, rows_of: int) -> None:
    """
    The shared legend, UNDER the figure rather than on it.

    Ten entries is a block, and a block placed anywhere inside these axes lands
    on lines: upper left is where the rate runs, centre left is where the
    inflow climbs through. Below the axes it covers nothing and reads in one
    pass across rather than as a tall column.

    ONE PANEL'S WORTH, not every panel's. Every panel draws the same lines, so
    collecting them all repeated the legend once per resource -- twenty-one
    times on the boards case, and the reserved space came out taller than the
    figure.

    It used to take a `strip_numbers` flag, because the labels carried each
    line's value and a value belongs to one panel. No label carries a number
    any more -- they are all readable off the axes -- so the flag had nothing
    left to strip and is gone rather than left as a parameter nobody passes
    anything but a constant to.
    """
    panel, rate_axis = for_legend[0]
    handles, labels = panel.get_legend_handles_labels()
    extra = rate_axis.get_legend_handles_labels()
    handles, labels = handles + extra[0], labels + extra[1]
    room = min(0.35, 0.055 + 0.038 * np.ceil(len(labels) / 3) / max(1, rows_of))
    figure.subplots_adjust(bottom=room)
    legend = figure.legend(handles, labels, fontsize=11, frameon=False,
                           ncol=3, loc='lower center',
                           bbox_to_anchor=(0.5, 0.012),
                           handlelength=3.2, columnspacing=2.5,
                           labelspacing=0.7)
    for text in legend.get_texts():
        text.set_color(colours['meta'])


# ⚠️ NO NUMBER ON A FIGURE THAT THE FIGURE ALREADY SHOWS. Said on 2026-09-29:
# *"I do not need numbers in the figure, if I can read them from the figure."*
# A line that ends against a labelled axis states its own last value; printing
# it in the legend beside it is the same number twice, and it crowds the label
# that says WHICH line it is.
#
# This is the same rule as its opposite, from 2026-09-28: *"what you write
# which can not be seen in the figures has no place there."* Between them:
# a figure carries what can be seen ON it, stated once. A DATE is the
# exception that proves it -- nobody reads 2055 off a peak, so the year a
# curve turns is still written, next to the rule that marks it.

def figure_account(run, theme: str, unit: str, resources=(), only: str = '',
                   fixed=None):
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

    BANDS ARE 95%, ON THREE THINGS: what left the fleet, what came back, and
    the recovery rate. Not on every line -- that is mud -- but these three are
    not interchangeable and no two of them cover the third:

        outflow band    the fleet's uncertainty, alone
        rate band       the coefficients' uncertainty, alone, because the rate
                        is formed per draw and the fleet cancels in it
        recovered band  BOTH together, which is the interval on the number
                        anyone actually quotes

    The recovered band was missing until 2026-09-29, so the one quantity this
    stage exists to compute was the one drawn without an interval.

    Every ratio is formed inside the draw, numerator and denominator together,
    so the fleet's own uncertainty cancels where it should (DECISIONS 32) and
    no rate can exceed 100%.
    """
    # ⚠️ ONE RESOURCE PER FIGURE when `only` names one. Six accounts in a grid
    # came out 9,833 pixels wide and the panel titles were unreadable at any
    # size a screen shows; the losses version was 19,166. Said on 2026-09-28:
    # *"Have them in individual figures, so one can see them."* The grid is
    # kept for the case that asks for one or two.
    wanted = [only] if only else chosen(run, resources)
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

    layer, keys = resource_key(run.keys), run.keys
    roads_for: dict[str, dict[str, np.ndarray]] = {}
    for resource in accounts:
        per_road = {}
        for road, flows in by_road.items():
            columns = []
            for year in years:
                rows = np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy() & own(keys)
                    & (keys['Year'].astype(str) == str(year)).to_numpy())
                columns.append(run.values[rows].sum(axis=0) if rows.size
                               else np.zeros(run.draws))
            draws = np.column_stack(columns)
            if draws.mean(axis=0).max() > 0:
                per_road[road] = draws
        roads_for[resource] = per_road

    every = np.concatenate([np.nanpercentile(a['outflow'], 97.5, axis=0)
                            for a in accounts.values()])
    # ⚠️ ONE UNIT FOR EVERY RESOURCE OF THIS FIGURE TYPE, handed in by
    # `draw_all`. Scaled per figure, `account_Pr` came out in tonnes beside
    # `account_copper` in kilotonnes and the two could not be put side by side
    # without converting in your head. Said on 2026-09-29: *"I told you before
    # to have always the same units on the y axis, so figures can be
    # compared."* The RANGE still differs -- it has to, copper is four orders
    # above terbium -- but the unit on the label does not.
    scale, shown = fixed or scale_for(every, unit)

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
                                 years, scale, shown, colours, unit,
                                 show_title=len(accounts) > 1)
        for_legend.append((panel, rate_axis))

    names = ', '.join(sorted(accounts))
    # ⚠️ THE TITLE SAYS WHAT THE FIGURE MEANS, NOT HOW IT IS DRAWN. It read
    # `the whole account, on one axis`, which describes a layout decision --
    # true, and of no use to anyone asking what the figure is for. Said on
    # 2026-09-29: *"The title just bad. Give it a meaning."* The question this
    # figure answers is where the material ends up, so that is the title.
    header(figure, f'{names}: how much comes back, and where the rest goes',
           colours,
           f'{years_listed(run)}.  every mass is a MEAN in the same unit, so '
           f'any two compare by the distance between them: recovered + lost + '
           f'never collected = what left the fleet.  bands are 95%, on what '
           f'left the fleet and on what came back.  the recovery rate is '
           f'formed per draw and read on the right axis')
    account_legend(figure, for_legend, colours, rows_of)
    return figure


def fleet_flows(run, resource: str):
    """
    Every annual quantity this resource has, per draw, over ALL exported years.

    Returns a dict of (years x draws) arrays in the ARRAYS' own unit, plus the
    year list and the years the model solved:

        inflow      entering the fleet
        outflow     leaving it
        collected   reaching a recycler
        recovered   coming back as material, reusable
        net         inflow - outflow, what the fleet absorbs that year

    EVERY YEAR THE EXPORT HOLDS, AND A STOCK IS AN INTEGRAL OVER THEM. All of
    the export is read rather than the case's solved years, which are coarser
    still.

    ⚠️ THE EXPORTS DO NOT SHARE A STEP. The electronics are annual; the battery
    and the traction motor are five-yearly. This docstring used to assert the
    export "is annual", and the figure added the samples with `np.cumsum` as
    though each stood for one year -- understating every traction and battery
    stock about fivefold. See `_running_total`.

    `recovered` IS THE ONE INTERPOLATED QUANTITY, and it has to be, because the
    model solves the years the case names and not every year. What is
    interpolated is the RATE -- recovered over collected -- between the solved
    years, and then applied to the annual collected mass. That is consistent
    with how the model itself moves: an improving case ramps its coefficients
    linearly between two tables (DECISIONS 27-29), so a linearly moving rate is
    the model's own shape rather than a curve invented for a figure. The figure
    says it is interpolated.
    """
    source = getattr(run, 'upstream', None)
    if source is None or not getattr(source, 'propagates', False):
        return None
    a = account(run, resource)
    if a is None:
        return None
    keys, layer = run.keys, resource_key(run.keys)
    domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                          'Layer 2'].unique() if d})
    if not domains:
        return None

    every = [int(year) for year in source.years]
    got = {'inflow': [], 'outflow': [], 'collected': []}
    for year in every:
        for name in got:
            piece = source.other_flow(name, resource, domains, year, 0, run.draws)
            if piece is None:
                return None
            got[name].append(piece)
    out = {name: np.array(block) for name, block in got.items()}
    out['net'] = out['inflow'] - out['outflow']

    # The rate the model found, at the years it solved, carried across the rest.
    solved = [int(y) for y in a['years']]
    with np.errstate(invalid='ignore', divide='ignore'):
        rate = np.where(a['collected'] > 0,
                        a['recovered'] / a['collected'], np.nan)   # draws x years
    rate = np.nan_to_num(rate, nan=0.0)
    annual = np.empty((len(every), run.draws))
    for draw in range(0, run.draws, 20000):                # in slices, for memory
        end = min(draw + 20000, run.draws)
        annual[:, draw:end] = np.array(
            [np.interp(every, solved, rate[one, :]) for one in range(draw, end)]).T
    out['recovered'] = out['collected'] * annual
    return {'years': every, 'solved': solved, **out}


def _running_total(block, years):
    """
    A per-year flow turned into its running total, BY TRAPEZOID.

    ⚠️ NOT `np.cumsum`, WHICH IS WHAT THIS FIGURE USED. The upstream exports do
    not all have the same year step: the electronics are annual, the battery
    and the traction motor are FIVE-YEARLY. Adding five-yearly samples as
    though each stood for one year understates every stock about fivefold --
    a different answer, not a rounding difference.

    `figure_trapped` said in its own docstring that "the upstream export is
    annual and all of it is read", which was true of the only case it had been
    looked at on. `05_combine_cases._accumulate` has done this correctly since
    it was written; this figure never picked it up. Found on 2026-09-29 from
    the question *"is it not per year?"*

    The gaps are taken from the years themselves, so an export at any step is
    integrated correctly and an annual one is unchanged in all but the
    end points.
    """
    gaps = np.diff(np.asarray(years, dtype=float))
    middles = 0.5 * (block[1:, :] + block[:-1, :]) * gaps[:, None]
    return np.concatenate([np.zeros((1, block.shape[1])),
                           np.cumsum(middles, axis=0)], axis=0)


def _shared_unit(values, unit: str):
    """
    One display unit for a set of figures, or None to let each pick its own.

    Judged on the LARGEST value any of them will draw, so the biggest axis
    reads in whole numbers and the smaller resources read as fractions of the
    same unit -- 1.4 kt beside 0.05 kt rather than 1,400 t beside 50 t on two
    axes labelled differently.

    ⚠️ EVERY VALUE HANDED IN MUST ALREADY BE IN `unit`. This took a set of
    numbers and a key to pull them out with, and for the stocks it pulled them
    straight out of `fleet_flows` -- which returns the UPSTREAM arrays, in the
    upstream's unit, because the conversion to the model's working unit happens
    afterwards inside `figure_trapped`. So a copper stock of 260 kt was judged
    as 260 kg, 260 kg does not reach a tonne, and the axis came out in
    kilograms with `1e8` stuck in the corner: *"what the hell kg."*

    Taking values rather than a key and a dict is the fix. A caller that has
    not converted cannot now pass the wrong thing by accident, because it has
    to produce the number itself.
    """
    values = [abs(float(v)) for v in values if np.isfinite(v)]
    return scale_for(np.array(values), unit, by='max') if values else None


def _stock_tops(run, wanted) -> list:
    """
    The largest accumulated stock each resource reaches, in the WORKING unit.

    The same conversion `figure_trapped` applies, for the same reason and by
    the same arithmetic: the upstream arrays and the model's table are in
    different units, and the ratio between them is the model's own collected
    mass over the upstream's.
    """
    tops = []
    for resource in wanted:
        found = fleet_flows(run, resource)
        a = account(run, resource)
        if not found or not a or 'collected' not in found:
            continue
        first = np.nanmean(found['collected'][0])
        if not np.isfinite(first) or first <= 0:
            continue
        to_working = float(np.nanmean(a['collected'][:, 0]) / first)
        stock = _running_total(found['net'], found['years']) * to_working
        top = np.nanpercentile(stock, 97.5)
        if np.isfinite(top):
            tops.append(abs(float(top)))
    return tops


def _crosses(years, series, level: float):
    """
    Where the DRAWN line first reaches `level`, interpolated between samples.

    ⚠️ NOT THE FIRST SAMPLED YEAR PAST IT. The model solves every fifth year,
    so a curve climbing 9% -> 18% steps straight over 10%: the first sample at
    or above the level is 2040, and a dot placed at (2040, 10) sits eight
    points BELOW the line. That is what it did until 2026-09-29 -- *"I have
    points in green which do not align with the curve. Why?"*

    The figure joins its samples with straight segments, so the linear crossing
    of a segment IS a point on the line as drawn. The dot lands on it exactly,
    and the year printed is that crossing rounded -- 2037, not 2040.

    Returns None when the line never reaches the level, which the caller then
    says in words. A line that wanders gives its FIRST crossing; later ones are
    not marked, because the question is when it starts to count.
    """
    for index in range(1, len(series)):
        low, high = series[index - 1], series[index]
        if index == 1 and np.isfinite(low) and low >= level:
            return years[0]
        if not (np.isfinite(low) and np.isfinite(high)):
            continue
        if low < level <= high:
            span = high - low
            return years[index - 1] + ((level - low) / span if span else 0.0) \
                * (years[index] - years[index - 1])
    return None


def figure_trapped(run, theme: str, unit: str, resources=(), only: str = '',
                   fixed=None):
    """
    STILL DRIVING, COME BACK, OR GONE -- every tonne that entered the fleet.

    Between what a fleet takes in and what it gives back there is a stock, and
    it is the largest number in this model: copper bought years ago, still
    driving around, unavailable to anybody. `account_<r>.png` draws the inflow
    and the outflow per year and leaves that gap to be imagined. This
    accumulates it.

    TWO QUESTIONS, ASKED ON 2026-09-29, AND THE FIGURE IS BUILT ON THEM:
    *"I want to know how much is in the fleet, and when recovery actually
    starts contributing to the inflow."*

    **Top: how much is in the fleet.** The stock still driving, which is the
    largest number in this model, with recovered-to-date and lost-to-date
    beside it so the three account for everything that entered. The year the
    fleet stops growing is marked -- it is the peak of the stock curve, so the
    mark sits where a reader can see the thing it claims.

    **Bottom: when does recovery start contributing?** Recovered as a share of
    what the fleet is BUYING, and THE YEARS IT CROSSES 10%, 25%, 50% AND 100%.
    The crossings are the answer to the question: a curve shows that it rises,
    the marks say when. At 100% every new car could be built from old ones.

    A date is the one number still written on these figures, because nobody
    reads a year off a crossing -- see the rule above `figure_account`.

    ⚠️ THE STRIP USED TO BE A FULL PANEL OF MASSES, AND IT WAS A CHEAP REPEAT.
    It drew entering, leaving and recovered per year -- four lines, every one
    of them already on `account_<r>.png` -- in order to deliver the one
    quantity that is NOT there: the share over the INFLOW rather than over
    what was collected. Said on 2026-09-29: *"First figure is a cheap repeat."*
    So the repeated masses are gone and the strip carries only the thing that
    is its own.

    The two are different quantities, which is why they are not on one axis:
    a share in per cent and a stock in kilotonnes.

    Counting starts at the first exported year and what was already on the road
    then is NOT in it -- see `fleet_flows`.
    """
    # One resource per figure when `only` names one -- see `figure_account`.
    # Six in a grid came out 3,819 x 4,308 pixels, which is a poster, not a
    # figure.
    wanted = [only] if only else chosen(run, resources)
    series = {}
    for resource in wanted:
        found = fleet_flows(run, resource)
        if found is None:
            continue
        a = account(run, resource)
        first = int(a['years'][0])
        keys, layer = run.keys, resource_key(run.keys)
        domains = sorted({d for d in keys.loc[keys[layer] == resource,
                                              'Layer 2'].unique() if d})
        raw = run.upstream.other_flow('collected', resource, domains, first,
                                      0, run.draws)
        if raw is None or raw.mean() <= 0:
            continue
        # The arrays' unit against the model's, from the model's own collected
        # mass. No unit constant appears here on purpose.
        to_working = float(np.nanmean(a['collected'][:, 0]) / raw.mean())
        # ⚠️ BY NAME, NOT BY TYPE. This scaled every value that happened to be
        # an ndarray, which is right only while `years` and `solved` are lists.
        # The moment either became an array it would have been multiplied by a
        # mass ratio and the figure would have been labelled 2020.0-2070.0 --
        # caught in a stub render on 2026-09-29, where they are arrays.
        masses = ('inflow', 'outflow', 'collected', 'recovered', 'net')
        series[resource] = {k: (v * to_working if k in masses else v)
                            for k, v in found.items()}
    if not series:
        return None

    biggest = np.concatenate([
        np.nanpercentile(_running_total(s['net'], s['years']), 97.5, axis=1)
        for s in series.values()])
    # One unit across every resource -- see `figure_account`. Its own, because
    # these are ACCUMULATED stocks and the account draws annual flows; sharing
    # one unit between the two would put a stock axis in the flow's unit.
    scale, shown = fixed or scale_for(biggest, unit)

    across = min(2, len(series))
    down = -(-len(series) // across)
    # A STRIP AND A PANEL, not two panels. The share is one line and needs a
    # sixth of the height; the stocks are what the figure is for.
    figure, axes, colours = chart(1250 * across, 900 * down, theme,
                                  2 * down, across,
                                  height_ratios=(2.2, 1.5) * down)
    grid = np.array(axes, dtype=object).reshape(2 * down, across)

    def band(draws):
        return (np.nanpercentile(draws, 50, axis=1),
                np.nanpercentile(draws, 2.5, axis=1),
                np.nanpercentile(draws, 97.5, axis=1))

    for index, (resource, s) in enumerate(sorted(series.items())):
        row, column = 2 * (index // across), index % across
        # `stock` is the question asked first, so it is the panel on top.
        stock, contribution = grid[row][column], grid[row + 1][column]
        years = s['years']
        end = years[-1]

        # ---- 1. how much is in the fleet -----------------------------
        # TOTALS AT EACH YEAR, integrated over the gaps between samples --
        # see `_running_total`. The first is a STOCK (what is in the fleet at
        # that moment); the other two are running totals since the first year.
        stocks = (('in the fleet at that year, still driving',
                   _running_total(s['net'], years), PALETTE[0], 3.4),
                  ('recovered by that year, in total',
                   _running_total(s['recovered'], years), PALETTE[1], 2.2),
                  ('lost by that year, in total',
                   _running_total(s['outflow'] - s['recovered'], years),
                   PALETTE[3], 2.2))
        for name, block, colour, width in stocks:
            median, low, high = band(block)
            stock.fill_between(years, low * scale, high * scale, color=colour,
                               alpha=0.16, linewidth=0)
            stock.plot(years, median * scale, color=colour, linewidth=width,
                       label=name)

        # THE YEAR THE FLEET STOPS GROWING, READ OFF THE CURVE THAT IS DRAWN.
        # It used to be the first year whose NET FLOW is negative, which is the
        # year AFTER the peak: the stock at 2055 is the stock at 2050 plus a
        # negative net, so the highest point plotted was 2050 while the label
        # pointed at 2055. Same fault as the crossings below, reported on
        # 2026-09-29: *"I have points in green which do not align with the
        # curve."*
        #
        # argmax of the median stock IS the top of the line a reader sees, so
        # the label and the picture cannot disagree.
        stock_median = band(_running_total(s['net'], years))[0]
        peak = int(np.nanargmax(stock_median))
        turned = years[peak] if 0 < peak < len(years) - 1 else None
        if turned is not None:
            stock.axvline(turned, color=colours['meta'], linewidth=1.0,
                          linestyle=(0, (3, 3)))
            # ON WHATEVER SIDE HAS ROOM. Anchored always to the right, a peak
            # late in the range put two lines of text straight through the
            # `lost to date` curve, which by then is the highest thing on the
            # panel.
            late = turned > (years[0] + years[-1]) / 2
            stock.annotate(f'{turned}: the stock peaks -- after this\n'
                           f'more {resource} leaves the fleet\nthan enters it',
                           xy=(turned, stock.get_ylim()[1]),
                           xytext=(-8 if late else 8, -12),
                           textcoords='offset points', color=colours['meta'],
                           fontsize=11, va='top',
                           ha='right' if late else 'left')
        stock.set_title(f'{resource}: how much is in the fleet, and where the '
                        f'rest of what entered since {years[0]} has got to',
                        color=colours['title'], fontsize=13, fontweight='bold')
        stock.set_ylabel(f'total mass ({shown})',
                         color=colours['meta'], fontsize=13)
        stock.set_xticklabels([])

        # ---- 2. when does recovery start contributing? ----------------
        with np.errstate(invalid='ignore', divide='ignore'):
            share = np.where(s['inflow'] > 0,
                             100 * s['recovered'] / s['inflow'], np.nan)
        median, low, high = band(share)
        contribution.fill_between(years, low, high, color=PALETTE[2],
                                  alpha=0.16, linewidth=0)
        contribution.plot(years, median, color=PALETTE[2], linewidth=3.0)

        # ⚠️ THE CROSSINGS ARE THE ANSWER. The curve shows that recovery
        # rises; the question was WHEN it starts to count. Each threshold is
        # marked at the first year the median reaches it, and a threshold the
        # resource never reaches is simply not drawn rather than implied.
        # ⚠️ AN AXIS THAT FITS THE CURVE. Fixed at 0-105 the copper reads well
        # and neodymium, which may never pass 5%, is a flat line on the floor.
        # The thresholds below adapt with it, so only the ones in range are
        # drawn and none is implied.
        #
        # RULED FROM THE DATA, NOT FROM A PADDED CEILING. It padded the top by
        # 25% and then `_ruling` rounded that up again, so a curve reaching 5%
        # was drawn on an axis running to 12 -- the double padding wasted more
        # of the panel than the fixed 0-105 it replaced.
        # ⚠️ 100% IS NOT A CEILING, AND THIS USED TO CLIP THE AXIS THERE.
        # The share is recovered over what the fleet BUYS, and a fleet that has
        # stopped growing returns more than it takes: the battery's cobalt
        # passes 100% around 2055 and keeps going, which is the finding, not an
        # artefact. Clipped at 100 the curve ran along the top of the panel and
        # read as a hard limit it had hit. Said on 2026-09-30: *"why not go
        # beyond -- there is more Co coming back than being used. This is true.
        # It is not a hard 100%."*
        #
        # (The recovery rate on `account_<r>.png` IS capped at 100 and stays
        # so: that one is recovered over COLLECTED, and nothing can come back
        # more than once.)
        step, count = _ruling(float(max(np.nanmax(high), 1e-9)))
        ceiling = step * count
        marked = 0
        # 75 IS THERE BECAUSE IT IS THE ONE WORTH DATING. Asked for on
        # 2026-09-30. Between 50% and 100% is where a metal stops being a
        # minor contribution and starts being most of the supply, and the gap
        # in the marks ran across exactly that stretch.
        for place, level in enumerate((10, 25, 50, 75, 100, 150, 200)):
            if level > ceiling:
                continue
            reached = _crosses(years, median, level)
            contribution.axhline(level, color=colours['rule'], linewidth=0.7)
            if reached is None:
                continue
            marked += 1
            contribution.plot([reached], [level], marker='o', markersize=7,
                              color=PALETTE[2], zorder=5)
            # Flipped to the left once the crossing is near the end of the
            # range, where a label anchored right runs off the page.
            near_end = reached > years[0] + 0.85 * (years[-1] - years[0])
            contribution.annotate(
                f'{level}% in {round(reached)}', xy=(reached, level),
                xytext=(-6 if near_end else 6, -14 if place % 2 else 6),
                textcoords='offset points', color=colours['title'],
                fontsize=11, fontweight='bold',
                ha='right' if near_end else 'left')

        # ⚠️ "NEVER" IS ALSO AN ANSWER, AND IT HAS TO BE SAID. With no
        # threshold reached the panel drew a rising line and no mark, which
        # reads as though the question had not been asked. For a resource whose
        # recovery stays in single figures -- the shredded magnet is one -- the
        # answer to "when does it start contributing" is that within this
        # horizon it does not, and that is the finding.
        if not marked:
            contribution.annotate(
                f'{resource} recovery never reaches 10% of what the fleet '
                f'buys, in any year to {years[-1]}',
                xy=(years[0], ceiling), xytext=(8, -8),
                textcoords='offset points', color=colours['title'],
                fontsize=11, fontweight='bold', va='top')

        # Four intervals or five, whichever wastes less -- keeping the fixed
        # 0/25/50/75/100 left a panel topping out at 12% with a single label on
        # its axis, so no value on it could be read at all.
        contribution.set_ylim(0, ceiling)
        contribution.set_yticks([step * n for n in range(count + 1)])
        contribution.set_ylabel('% of what is entering', color=PALETTE[2],
                                fontsize=13)
        contribution.set_xlabel('year', color=colours['meta'], fontsize=13)
        contribution.tick_params(colors=PALETTE[2], labelsize=14)
        # Two lines: one title and one gloss. On one line it ran off the
        # right edge the moment the 100% sentence grew.
        contribution.set_title(
            f'{resource}: when does recovery start contributing to what the '
            f'fleet buys?\n'
            f'100% = every new car could be built from old ones.  '
            f'Above it, the fleet gives back more than it takes.',
            color=colours['title'], fontsize=13, fontweight='bold',
            linespacing=1.5)

        for panel in (stock, contribution):
            panel.tick_params(labelsize=15)
            panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        legend = stock.legend(fontsize=11, frameon=False, loc='upper left')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    first = min(s['years'][0] for s in series.values())
    names = ', '.join(sorted(series))
    # ⚠️ THE TITLE SAYS WHAT THE FIGURE MEANS. `What the fleet holds, gives
    # back, and loses` names three quantities and says nothing about what
    # reading them tells you. Said on 2026-09-29: *"Titles impossible. Give
    # them the proper meaning."*
    step = (series[next(iter(series))]['years'][1]
            - series[next(iter(series))]['years'][0]) if len(
                series[next(iter(series))]['years']) > 1 else 1
    header(figure, f'{names}: how much is in the fleet, and when recovery '
           f'starts to count', colours,
           f'{every_years(series)}, sampled every {step}.  the upper panel is '
           f'a TOTAL AT EACH YEAR, not a per-year flow: what is in the fleet '
           f'at that moment, and what has come back or been lost in all the '
           f'years up to it, integrated over the gaps between samples.  '
           f'counted from {first}, so what was already on the road then is NOT '
           f'in it.  medians with 95% bands.  recovered uses the model\'s own '
           f'rate carried linearly between the years it solves')
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
    keys, layer = run.keys, resource_key(run.keys)
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
                & (keys[layer] == resource).to_numpy() & own(keys)
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            columns.append(run.values[rows].sum(axis=0) if rows.size
                           else np.zeros(run.draws))
        block = np.column_stack(columns)
        if block.mean(axis=0).max() > 0:
            found[f'lost in {name}'] = found.get(f'lost in {name}', 0) + block

    # HANDED ON IS A REASON TOO: what is neither recovered here nor destroyed.
    # Without it the reasons would not sum to the outflow with what was
    # recovered, which is what the figure built on this claims they do.
    if np.nanmean(a['handed'], axis=0).max() > 0:
        found['handed on (not counted here)'] = a['handed']

    found['never collected'] = a['uncollected']
    return {'years': np.array(years), 'reasons': found,
            'outflow': a['outflow'], 'recovered': a['recovered']}


def figure_losses(run, theme: str, unit: str, resources=(), only: str = '',
                  fixed=None):
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
    # One resource per figure when `only` names one -- see `figure_account`.
    wanted = [only] if only else chosen(run, resources)
    series = {r: found for r in wanted if (found := losses(run, r)) is not None}
    series = {r: s for r, s in series.items() if s['reasons']}
    if not series:
        return None

    every = np.concatenate([np.nanmean(s['outflow'], axis=0)
                            for s in series.values()])
    scale, shown = fixed or scale_for(every, unit)   # shared -- see figure_account

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
        # ⚠️ THE SUMMARY IS THE FIGURE'S, NOT THE PANEL'S. Written as a panel
        # title it was wider than the panel and ran through the title of the
        # one beside it. A panel title says what the panel is; the header says
        # what the figure found. And it is a SHAPE -- see the note on the
        # account panel's title for why one year was the wrong thing to quote.
        # The panel says what it is. The masses it used to quote -- 68.4 t in
        # 2020 against 31 kt in 2070 -- cannot be told apart from zero on a
        # linear stack running to kilotonnes, so they were a claim the figure
        # could not support. They are exact in the workbook's Recovered and
        # Contributions sheets. `most of it {biggest}` stays: the largest wedge
        # IS visible, which is the whole test.
        summary = f'most of it {biggest}'
        mass.set_title(f'{resource}: how much, by reason',
                       color=colours['title'], fontsize=12, fontweight='bold')
        mass.set_ylabel(f'lost per year ({shown}/year)',
                        color=colours['meta'], fontsize=13)

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
                           linewidth=2.0, marker='o', markersize=3, label=name)
        share.set_title(f'{resource}: the same, as a share of the outflow',
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

    one = summary if len(series) == 1 else ''
    header(figure, 'Why it does not come back'
           + (f'   --   {one}' if one else ''), colours,
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
    layer = resource_key(run.keys)
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
                & (keys[layer] == element).to_numpy() & own(keys)
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
    layer = resource_key(run.keys)
    keys, values = run.keys, run.values
    ends = terminal_flows(run)
    if not ends:
        return None

    def at(flow: str, element: str, year: int):
        rows = np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                              & (keys[layer] == element).to_numpy() & own(keys)
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
    keys, layer = run.keys, resource_key(run.keys)
    resource_key(deterministic)        # compared against `keys[layer]` below
    year_of = keys['Year'].astype(int).to_numpy()
    point_year = deterministic['Year'].astype(int).to_numpy()

    def gap(flow: str, element: str, year: int):
        """(percent away, deterministic mass, mean mass) for one year, or None."""
        rows = np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                              & (keys[layer] == element).to_numpy() & own(keys)
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
    panel.set_ylabel(f'{name[0]} · {name[1]}  ({shown}/year)',
                     color=colours['meta'], fontsize=9)
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
             resources=(), scenario: str = '') -> list[str]:
    """
    Draw every Monte Carlo figure. Returns the paths written.

    EVERY CASE GETS ITS OWN FOLDER (figure_style.folder_for). These used to be
    written flat, so two cases wrote `mc_pdf_Cu.png` to the same place and the
    second run replaced the first's silently -- a figures/ directory holding
    half of one study and half of another, with nothing but the file timestamps
    to say which was which.
    """
    import matplotlib.pyplot as plt

    out_dir = folder_for(out_dir, case, scenario) if case else out_dir

    # DRAWN ONE AT A TIME, hence the lambdas. Building the list eagerly built
    # every figure before writing any of them, so all 27 of the boards case's
    # were open at once -- matplotlib says so at 20 -- each holding its own
    # histogram of 200,000 draws. They were closed after writing, which looked
    # like enough right up until a case had more than a handful of resources.
    figures = [
        ('over_time',
         lambda: figure_over_time(run, deterministic, theme, unit, resources)),
        ('recovery_rate',
         lambda: figure_recovery_rate(run, deterministic, theme, unit)),

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
    # THE ACCOUNT AND THE LOSSES, ONE FILE EACH. Both used to be a grid of
    # every chosen resource in a single image, which at six resources is
    # unreadable at any size (see `figure_account`).
    # ⚠️ ONE UNIT PER FIGURE TYPE, WORKED OUT BEFORE ANY OF THEM IS DRAWN.
    # Each figure used to pick its own, so `account_Pr` was in tonnes and
    # `account_copper` in kilotonnes -- the same quantity, two labels, and no
    # way to lay them side by side. Judged on the LARGEST resource, so the
    # biggest axis reads in whole numbers and the smaller ones read as
    # fractions of the same unit.
    wanted = chosen(run, resources)
    flow_unit = _shared_unit(
        [np.nanpercentile(a['outflow'], 97.5)
         for r in wanted if (a := account(run, r))], unit)
    stock_unit = _shared_unit(_stock_tops(run, wanted), unit)

    for resource in wanted:
        figures.append((f'account_{resource}',
                        lambda resource=resource: figure_account(
                            run, theme, unit, resources, only=resource,
                            fixed=flow_unit)))
        figures.append((f'losses_{resource}',
                        lambda resource=resource: figure_losses(
                            run, theme, unit, resources, only=resource,
                            fixed=flow_unit)))
        # WHAT THE FLEET IS HOLDING, and what is gone -- the stock the account
        # leaves to be imagined. Asked for on 2026-09-28: *"how much is in the
        # fleet etc. how much is lost over time."*
        figures.append((f'fleet_{resource}',
                        lambda resource=resource: figure_trapped(
                            run, theme, unit, resources, only=resource,
                            fixed=stock_unit)))

    layer = resource_key(run.keys)
    for resource in wanted:
        figures.append((f'pdf_{resource}',
                        # bound now, not at call time: a bare `resource` would
                        # be the last one for every entry in the list.
                        lambda resource=resource: figure_pdf(
                            run, resource, deterministic, theme, unit, layer=layer)))

    # THE SANKEY, FROM THE DRAWS. 02 draws the same picture from one point
    # solve, and it is the only figure set in the project carrying no
    # uncertainty at all -- while the flow picture is exactly where a reader
    # looks to find out where the copper went. `plot_flows.figure_for_draws`
    # was written on 2026-09-25 and left wired into nothing; it is called here
    # at the user's instruction on 2026-09-28, "yes wire it into 03, I want
    # full MC".
    #
    # ONE YEAR, THE LAST, as `spread_last_year` and `mode_vs_mean` already are.
    # A ribbon's width is a single number and cannot carry a range, so the
    # figure draws MEANS -- the only central value that balances, because means
    # add -- and prints each node's 95% interval under it. The subtitle says
    # both limits out loud.
    #
    # WRITTEN UNDER THE NAMES 02 USES, so a case folder holds one Sankey per
    # resource rather than a Monte Carlo one sitting beside a deterministic one
    # with nothing but the subtitle to tell them apart. The stages run 02 then
    # 03, so the Monte Carlo version is what survives a full pass. Run 02 on
    # its own and the point-solve pictures come back.
    from src import plot_flows

    display = os.path.basename(str(case).rstrip('/')) or str(case)
    last_year = max(int(year) for year in run.keys['Year'].unique())
    for resource in [None] + chosen(run, resources):
        figures.append((resource or 'total',
                        # bound now, not at call time -- see the pdf loop above.
                        lambda resource=resource: plot_flows.figure_for_draws(
                            display, run, run.tcs, resource, unit, theme,
                            last_year)))

    written = []
    for stem, draw in figures:
        figure = draw()
        if figure is None:
            continue
        written.extend(write(figure, out_dir, stem, formats, dpi))
        plt.close(figure)

    # ⚠️ AND CLEAR WHAT 03 USED TO DRAW AND NO LONGER DOES. A figure that is
    # renamed or dropped stays in the folder looking current -- see
    # `figure_style.sweep`, which exists because `trapped.png` was read as this
    # model's answer eleven days after anything stopped producing it.
    from src.figure_style import report_sweep
    report_sweep(out_dir, 'monte carlo', written)
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
        & (keys[layer] == element).to_numpy() & own(keys)
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
                             layer: str = 'resource') -> float | None:
    # The deterministic frame is built separately from `run.keys`, so it does
    # not carry the resource column yet. Same rule, same result.
    if layer == 'resource':
        resource_key(deterministic)
    recovered = recovered_flows(run, run.case)
    rows = deterministic[(deterministic['Stock/Flow ID'].isin(recovered))
                         & (deterministic[layer] == element)
                         & (deterministic['Year'].astype(str) == str(year))]
    return float(rows['Value'].sum()) if len(rows) else None
