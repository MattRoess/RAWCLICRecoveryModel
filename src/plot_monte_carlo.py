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


import numpy as np
import pandas as pd

from src.figure_style import PALETTE, chart, folder_for, write
from src.units import scale_for

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

    every = np.concatenate([s['high'] for s in series.values()])
    scale, shown = scale_for(every, unit)

    figure, axes, colours = chart(1100, 620, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]

    for index, (element, s) in enumerate(series.items()):
        colour = PALETTE[index % len(PALETTE)]
        panel.fill_between(years, s['low'] * scale, s['high'] * scale,
                           color=colour, alpha=0.18, linewidth=0)
        panel.plot(years, s['median'] * scale, color=colour, linewidth=2.0,
                   marker='o', markersize=4,
                   label=f"{element}   {s['median'][0] * scale:,.3g} "
                         f"\u2192 {s['median'][-1] * scale:,.3g} {shown}")
        if np.isfinite(s['deterministic']).any():
            panel.plot(years, s['deterministic'] * scale, color=colour,
                       linewidth=1.4, linestyle='--', alpha=0.9)

    panel.set_title('Recovered mass over time   (solid: median, with the 95% '
                    'interval.  dashed: the deterministic run)',
                    color=colours['title'], fontsize=12, fontweight='bold',
                    loc='left')
    panel.set_xlabel('year', color=colours['meta'], fontsize=9)
    panel.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=9)
    panel.set_xticks(years)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    legend = panel.legend(fontsize=9, frameon=False, loc='upper left')
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    figure.tight_layout()
    return figure




def routes(run) -> dict[str, list[str]]:
    """
    The recovered flows, grouped by the flow each one leaves.

    THE ROUTE IS THE FLOW IT CAME OUT OF, which is general: nothing here knows
    the words "disassembly" or "shredder". In the wiring case it separates
    F_disassembled's three recovered streams from F_shredded's three, which is
    the two roads DECISIONS 10 says the case exists to compare. In the boards
    case only one flow feeds a recovered stream, so there is nothing to compare
    and the figure that uses this returns None.
    """
    recovered = set(recovered_flows(run, run.case))
    if not recovered:
        return {}
    pairs = run.tcs[run.tcs['Output_FlowID'].isin(recovered)]
    grouped: dict[str, list[str]] = {}
    for source, flows in pairs.groupby('Input_FlowID')['Output_FlowID']:
        grouped[str(source)] = sorted(set(flows))
    return grouped


def figure_routes(run, theme: str, unit: str):
    """
    Recovered mass by ROUTE, per year -- which road the material came back on.

    DECISIONS 10 and 11: the two roads are the point of the wiring case, and
    they are reported apart and also combined. `over_time.png` gives the
    combined trajectory; this one splits it, because the reason to disassemble
    at all is that the dedicated route returns more than the general shredder.

    One panel per resource, each with its own axis (DECISIONS 13): copper's
    tonnage is an order of magnitude above aluminium's, and a shared axis would
    make aluminium's road split unreadable while looking tidy.

    Solid line and band per route, 95% as everywhere. No stacking: a stack
    shows the total and hides the smaller road, which is the one under
    question.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    by_route = routes(run)
    if len(years) < 2 or len(by_route) < 2:
        return None                # one road is not a comparison

    layer = finest_layer(run.keys)
    keys = run.keys
    resources = sorted({e for e in keys[layer].unique() if e})

    series: dict[str, dict[str, dict]] = {}
    for resource in resources:
        per_route = {}
        for route, flows in sorted(by_route.items()):
            median, low, high = [], [], []
            for year in years:
                rows = np.flatnonzero(
                    keys['Stock/Flow ID'].isin(flows).to_numpy()
                    & (keys[layer] == resource).to_numpy()
                    & (keys['Year'].astype(str) == str(year)).to_numpy())
                totals = (run.values[rows].sum(axis=0) if rows.size
                          else np.zeros(run.draws))
                median.append(np.percentile(totals, 50))
                low.append(np.percentile(totals, 2.5))
                high.append(np.percentile(totals, 97.5))
            if max(median) > 0:
                per_route[route] = {'median': np.array(median),
                                    'low': np.array(low), 'high': np.array(high)}
        if len(per_route) > 1:
            series[resource] = per_route
    if not series:
        return None

    every = np.concatenate([r['high'] for res in series.values()
                            for r in res.values()])
    scale, shown = scale_for(every, unit)

    columns = min(3, len(series))
    rows_of = -(-len(series) // columns)
    figure, axes, colours = chart(460 * columns, 360 * rows_of, theme,
                                  rows_of, columns)
    panels = list(axes.ravel()) if hasattr(axes, 'ravel') else [axes]
    for spare in panels[len(series):]:
        spare.set_visible(False)

    for panel, (resource, per_route) in zip(panels, sorted(series.items())):
        for index, (route, s) in enumerate(sorted(per_route.items())):
            colour = PALETTE[index % len(PALETTE)]
            panel.fill_between(years, s['low'] * scale, s['high'] * scale,
                               color=colour, alpha=0.18, linewidth=0)
            panel.plot(years, s['median'] * scale, color=colour, linewidth=2.0,
                       marker='o', markersize=3, label=route)
        last = {route: s['median'][-1] for route, s in per_route.items()}
        share = 100 * max(last.values()) / sum(last.values()) if sum(last.values()) else 0
        biggest = max(last, key=last.get)
        panel.set_title(f'{resource}   {biggest} returns {share:.0f}% of it in {years[-1]}',
                        color=colours['title'], fontsize=10, fontweight='bold')
        panel.set_xlabel('year', color=colours['meta'], fontsize=8.5)
        panel.set_ylabel(f'mass ({shown})', color=colours['meta'], fontsize=8.5)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
        legend = panel.legend(fontsize=8, frameon=False, loc='upper left')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    header(figure, 'Recovered mass by route', colours,
           f'which road it came back on, {years_listed(run)}.  '
           f'solid: median, band: 95%.  each panel has its own axis')
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

    The band is honest: the rate is computed PER DRAW, recovered mass in that
    draw over the inflow of that year, so the interval is the interval of the
    ratio and not two percentiles divided by each other.
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

    def collected_in(year, resource: str | None) -> float:
        """
        What was collected, of the thing being asked about.

        EACH RESOURCE IS DIVIDED BY ITS OWN INFLOW. Dividing copper recovered by
        the TOTAL collected mass answers a different question, and the answer
        looks like a recovery rate falling when nothing about recovery moved:
        on the wiring case copper's own recovery holds at 77-78% while its share
        of the inflow drops 36% to 28% as motors grow against harnesses. The
        first version of this figure made that mistake and reported it as
        copper being recovered worse.

        The total line still divides by the whole inflow, which is the one case
        where that IS the question.
        """
        wanted = (keys['Stock/Flow ID'].isin(starts)
                  & (keys['Year'].astype(str) == str(year)))
        if resource is not None:
            wanted &= (keys[layer] == resource)
        rows = keys[wanted]
        if rows.empty:
            return 0.0
        if resource is None:
            # Nesting: a resource row is part of its parent's, so the inflow is
            # totalled at its own shallowest depth (MODEL_MECHANICS.md 1).
            depth = (rows[[c for c in LAYERS if c in rows.columns]] != '').sum(axis=1)
            rows = rows[depth == depth.min()]
        return float(run.values[keys.index.get_indexer(rows.index)].sum(axis=0).mean())

    lines: dict[str, dict[str, np.ndarray]] = {}
    for resource in [EVERYTHING] + sorted({e for e in keys[layer].unique() if e}):
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
            rate = 100 * total / inflow if inflow else np.zeros(run.draws)
            median.append(np.percentile(rate, 50))
            low.append(np.percentile(rate, 2.5))
            high.append(np.percentile(rate, 97.5))
        if max(median) > 0:
            lines[resource] = {'median': np.array(median), 'low': np.array(low),
                               'high': np.array(high)}
    if not lines:
        return None

    figure, axes, colours = chart(1100, 620, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    for index, (resource, s) in enumerate(lines.items()):
        colour = colours['title'] if resource == EVERYTHING \
            else PALETTE[(index - 1) % len(PALETTE)]
        width = 2.6 if resource == EVERYTHING else 1.8
        # A DASH PATTERN PER RESOURCE. Two resources given the same coefficients
        # have the same rate exactly, and one solid line then sits invisibly
        # under another -- which reads as a missing resource rather than as two
        # that agree. On the wiring case alalloy and fealloy do exactly this.
        style = '-' if resource == EVERYTHING else DASHES[(index - 1) % len(DASHES)]
        panel.fill_between(years, s['low'], s['high'], color=colour,
                           alpha=0.10 if resource == EVERYTHING else 0.16,
                           linewidth=0)
        panel.plot(years, s['median'], color=colour, linewidth=width,
                   linestyle=style, marker='o', markersize=4,
                   label=f"{resource}   {s['median'][0]:.1f} \u2192 "
                         f"{s['median'][-1]:.1f}%")

    panel.set_xlabel('year', color=colours['meta'], fontsize=9)
    panel.set_ylabel('recovered, % of that resource collected',
                     color=colours['meta'], fontsize=9)
    panel.set_xticks(years)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    legend = panel.legend(fontsize=9, frameon=False, loc='best')
    for text in legend.get_texts():
        text.set_color(colours['meta'])

    header(figure, 'Recovery rate over time', colours,
           f'{years_listed(run)}.  each resource against ITS OWN inflow, '
           f'the black line against the whole.  median and 95%, ratio per draw')
    return figure


def figure_pdf_grid(run, deterministic: pd.DataFrame | None, theme: str,
                    unit: str, bins: int = 120):
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
    for element in sorted({e for e in keys[layer].unique() if e}):
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
             dpi: int, theme: str, unit: str = 'Mg', case: str = '') -> list[str]:
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
        ('routes', lambda: figure_routes(run, theme, unit)),
        ('pdf_all', lambda: figure_pdf_grid(run, deterministic, theme, unit)),
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
    for resource in sorted({e for e in run.keys[layer].unique() if e}):
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
