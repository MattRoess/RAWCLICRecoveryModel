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
    years = sorted(int(y) for y in run.keys['Year'].unique())
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

def figure_spread(run, theme: str, unit: str, most: int = 12):
    """
    How uncertain each result is, per year: the 95% interval as a percentage of
    the mean, one line per flow and resource.

    COMPARISON AND TRAJECTORY IN ONE FIGURE. Reading down at any year ranks the
    results by how uncertain they are; reading along a line says whether that is
    getting better or worse. The previous version was a bar per result with the
    years SUMMED, which ranked them and destroyed the trajectory -- and summed
    an absolute mass across years, adding 2030's 10 kt of copper to 2050's 254
    to make a number with no physical meaning.

    A RELATIVE SPREAD IS THE ONE QUANTITY THAT SURVIVES BOTH. It is scale-free,
    so a flow carrying 3 kt and one carrying 300 belong on the same axis without
    anything being rescaled to put them there, and it is meaningful per year, so
    no summing is needed to draw it.

    Losses come out far wider than recoveries and that is arithmetic, not noise:
    a loss is `1 - yield`, so an alloy recovered at 0.95 leaves 0.05, and a
    small movement in a large number is a large movement in a small one.
    """
    years = sorted(int(y) for y in run.keys['Year'].unique())
    layer = finest_layer(run.keys)
    keys, values = run.keys, run.values
    ends = terminal_flows(run)
    if not ends or not years:
        return None

    series: dict[str, dict[int, float]] = {}
    for flow in ends:
        is_flow = (keys['Stock/Flow ID'] == flow).to_numpy()
        for element in sorted({e for e in keys[layer].unique() if e}):
            is_element = (keys[layer] == element).to_numpy()
            per_year = {}
            for year in years:
                rows = np.flatnonzero(is_flow & is_element
                                      & (keys['Year'].astype(str) == str(year)).to_numpy())
                if not rows.size:
                    continue
                totals = values[rows].sum(axis=0)
                mean = float(totals.mean())
                if mean <= 0:
                    continue
                low, high = np.percentile(totals, [2.5, 97.5])
                per_year[year] = 100.0 * (high - low) / mean
            if per_year:
                series[f'{flow}  \u00b7  {element}'] = per_year
    if not series:
        return None

    # The widest at the last year, because a chart with one line per result is
    # readable for this case and a thicket for 04_01's hundreds.
    ranked = sorted(series.items(),
                    key=lambda item: item[1].get(years[-1], 0.0), reverse=True)
    trimmed = max(0, len(ranked) - most)
    ranked = ranked[:most]

    figure, panel, colours = chart(1150, 640, theme)
    for index, (name, per_year) in enumerate(ranked):
        colour = PALETTE[index % len(PALETTE)]
        drawn = sorted(per_year)
        panel.plot(drawn, [per_year[y] for y in drawn], color=colour, linewidth=2.0,
                   marker='o', markersize=4,
                   label=f'{name}   {per_year[drawn[-1]]:,.0f}% in {drawn[-1]}')

    panel.set_title('How uncertain each result is, per year'
                    + (f'   --  the {len(ranked)} widest of {len(ranked) + trimmed}'
                       if trimmed else ''),
                    color=colours['title'], fontsize=12, fontweight='bold', loc='left')
    panel.set_xlabel('year', color=colours['meta'], fontsize=10)
    panel.set_ylabel('95% interval, as % of the mean', color=colours['meta'], fontsize=10)
    panel.set_xticks(years)
    panel.set_ylim(bottom=0)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7)
    # BELOW THE AXES, not inside them. Twelve entries in the upper left covered
    # the two highest lines -- which are the widest spreads, the whole reason to
    # look at the figure. A legend that hides the subject is worse than a taller
    # image.
    legend = panel.legend(fontsize=9, frameon=False, ncol=3,
                          loc='upper center', bbox_to_anchor=(0.5, -0.10))
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    figure.tight_layout()
    return figure


def figure_mode_vs_mean(run, deterministic: pd.DataFrame, theme: str, unit: str):
    """
    How far the deterministic run sits from the Monte Carlo mean, per result.

    Expressed as a percentage of the mean, because the absolute gap is only
    meaningful next to the size of the flow. A bar to the left means the
    deterministic run *understates* the expected mass.
    """
    totals = totals_by_flow_and_element(run)
    if not totals or deterministic is None:
        return None
    layer = finest_layer(run.keys)

    scale, shown = scale_for(np.concatenate(list(totals.values())), unit)

    entries = []
    for (flow, element), values in totals.items():
        rows = deterministic[(deterministic['Stock/Flow ID'] == flow)
                             & (deterministic[layer] == element)]
        if not len(rows):
            continue
        point = float(rows['Value'].sum())
        mean = float(values.mean())
        if mean > 0:
            entries.append((f'{flow}  ·  {element}', 100.0 * (point - mean) / mean,
                            point * scale, mean * scale))
    if not entries:
        return None

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
    panel.set_title(f'Deterministic run against the Monte Carlo mean   '
                    f'({years_covered(run)})'
                    + (f'  --  the {len(entries)} largest gaps of '
                       f'{len(entries) + trimmed}' if trimmed else ''),
                    color=colours['title'], fontsize=12, fontweight='bold', loc='left')
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    panel.grid(False, axis='y')
    figure.tight_layout()
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

    figures = [
        ('over_time', figure_over_time(run, deterministic, theme, unit)),
        ('pdf_all', figure_pdf_grid(run, deterministic, theme, unit)),
        ('spread', figure_spread(run, theme, unit)),
        ('mode_vs_mean', figure_mode_vs_mean(run, deterministic, theme, unit)),
        ('convergence', figure_convergence(run, theme, unit)),
        ('sensitivity', figure_sensitivity(run, theme)),
    ]

    # One distribution figure per resource: the histograms ARE the result, and a
    # single combined panel hides which one is uncertain and which is not.
    #
    # At the finest layer the case resolves, NOT always Layer 4 -- 04_01 stops at
    # material and leaves Layer 4 empty, which produced no per-resource figures
    # at all rather than an error.
    layer = finest_layer(run.keys)
    for resource in sorted({e for e in run.keys[layer].unique() if e}):
        figures.append((f'pdf_{resource}', figure_pdf(run, resource, deterministic,
                                                         theme, unit, layer=layer)))

    written = []
    for stem, figure in figures:
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
    years = sorted(run.keys['Year'].astype(str).unique())
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
