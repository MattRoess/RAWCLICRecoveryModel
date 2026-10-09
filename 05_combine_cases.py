"""
05_combine_cases.py
===================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

**One metal across several streams, added per draw.**

Press Run. Nothing to type. What is added, and which metal, is set in
`src/params_schema.py` under `combine`.

WHY THIS IS ITS OWN STAGE
-------------------------
The wiring case and the boards case are separate studies: separate folders,
separate networks, separate coefficients, separate runs. They stay that way
(DECISIONS 20). But the copper the wiring recovers and the copper the boards
recover are the same metal coming out of the same car, and the question "how
much copper does BEV electronics return" is answered by neither case alone.

So this adds them. It is reporting, exactly as DECISIONS 11 reports the two
roads apart and also combined -- an addition made for the reader, never a third
flow in anybody's network.

It is a separate stage because the list will grow. Battery packs and
drivetrains join by getting a case folder and being named in `combine.cases`;
nothing here knows how many there are or what they are called.

ADDED PER DRAW, NOT PER PERCENTILE
----------------------------------
Every case reads the same upstream draws with the same seed, so draw i is one
world in all of them: the same fleet, the same year, the same number of cars.
Adding within the draw and taking percentiles afterwards therefore gives the
interval of the sum.

Adding the percentiles instead would give something wider than any world -- it
would assume every stream hits its own 97.5th percentile simultaneously, which
is the mistake the Monte Carlo exists to avoid (DECISIONS 14).

WHAT IT COSTS
-------------
Each case is solved in full, one after another, and only the two series this
figure needs are kept: recovered and collected, for the one metal, per year,
per draw. That is 11 x 200,000 x 8 bytes -- about 18 MB a case -- so the
memory does not grow with the number of cases, only the time does.
"""
from __future__ import annotations

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
#
# THE ONLY NUMBERED STAGE THAT DID NOT DO THIS, until 2026-09-17. It worked
# for as long as it happened to be started with ./.venv/bin/python, and died
# on `import matplotlib` the first time it was run from Positron, which uses
# the pyenv interpreter. The other five stages have carried this block all
# along.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if os.path.basename(os.path.dirname(os.path.abspath(__file__)))
                in ('tests', 'tools')
                else os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()

import copy
import re

import numpy as np

from src.figure_style import chart, write
from src.monte_carlo import solve_draws
from src.params_schema import Params
from src.plot_monte_carlo import account, header, losses, routes
from src.rest import REST
from src.units import factor, readable
from src.upstream import (cases_to_run, load as refresh, offers_scenario,
                          scenarios_available, scenarios_to_run)

LAYER_NAMES = ['product', 'component', 'material', 'element']

# COLOURS FOR THE STREAMS, fixed and far apart, so each is told apart at a
# glance and keeps the same colour from one figure to the next. The total is
# not among them: it is black, and solid, because it is the main line.
# The recovery rate is not a mass, so it does not take a stream colour.
RATE_COLOUR = '#2e7d32'

# FOUR WAS ENOUGH FOR THE ELECTRONICS AND IS NOT ENOUGH NOW. Wiring, motors,
# PCBs and sensors are four; adding the battery brings its own components and
# copper alone runs to seven, so the list wrapped and `wiring` and
# `currentCollectorAnode` came out the same green -- two lines a reader cannot
# tell apart, which is worse than no colour. The first four are unchanged, so
# no existing figure moves. Beyond that the list still wraps, and a run that
# needs more than this says so.
STREAM_COLOURS = ('#1f77b4',   # blue
                  '#d62728',   # red
                  '#2ca02c',   # green
                  '#ff7f0e',   # orange
                  '#9467bd',   # purple
                  '#8c564b',   # brown
                  '#17becf',   # cyan
                  '#bcbd22',   # olive
                  '#e377c2',   # pink
                  '#7f7f7f')   # grey


# HOW MANY LINES A PANEL MAY HOLD AND STILL BAND EVERY ONE OF THEM.
#
# Every quantity drawn here is per draw, so every line COULD carry its 2.5 to
# 97.5 interval, and a mean drawn without one invites a difference to be read
# where the draws do not support one. What stops it being done everywhere is
# the panel: bands overlap, and past a handful they stop being intervals and
# become a wash that hides the lines they belong to.
#
# Eight, set 2026-09-18 by the user. Below it every series is banded, in its
# own line's colour so a band can only belong to one line. At it or above, only
# the TOTAL is banded -- that one always is. Counted at draw time, not written
# in, so a fourth case pushing the streams past the limit drops the per-stream
# bands on its own rather than needing this file edited.
BANDS_BELOW = 8


class CombineError(ValueError):
    """Raised when the cases named cannot be added together."""


def _resource_of(run) -> str:
    """
    The column holding each row's OWN resource, whatever depth it sits at.

    ⚠️ A CASE DOES NOT HAVE ONE DEPTH, and this file assumed it did. Every
    helper here picked `the deepest layer with anything in it` and compared
    against that one column. On the traction motor case that column is Layer 4,
    filled by Nd, Pr, Dy and Tb -- while copper, aluminium, steel and lamination
    stop at Layer 2/3 and are blank in it.

    So `named_in` returned None for copper, and 05 printed "none of copper, Cu
    in this case -- skipped" and left the traction motor's copper out of the
    combined figure entirely. Silently: a skip is a normal thing to print.

    `src/plot_monte_carlo.resource_key` already solved this for the figures on
    2026-09-25 and this file never picked it up. It marks each row with its own
    resource and with `own_depth`, so a component named after its own material
    is not counted twice.
    """
    from src.plot_monte_carlo import resource_key
    return resource_key(run.keys)


def named_in(run, names) -> str | None:
    """
    Which spelling of the metal this case uses, if any.

    The wiring case resolves materials and calls it `copper`; the boards case
    resolves elements and calls it `Cu`. A case with none of the names given
    contributes nothing and says so, rather than counting zero quietly.

    Looked for at EVERY depth -- see `_resource_of`.
    """
    keys = run.keys
    layer = _resource_of(run)
    present = {value for value in keys[layer].unique() if value and value != REST}
    return next((name for name in names if name in present), None)


def could_carry(folder: str, names, params) -> bool:
    """
    Whether this case could possibly hold the metal -- WITHOUT solving it.

    `combine_one` used to solve every case at full draws and only then ask
    `named_in` whether the metal was in it, so a run of eight metals across
    four cases did 32 Monte Carlos to use 10 of them. Neodymium solved the
    wiring case in full in order to print "none of Nd in this case".

    Read from the case's own coefficient table instead: a resource that no
    coefficient targets and no flow is keyed at cannot come out of the model.

    ⚠️ IT MAY ONLY SAY NO WHEN IT IS CERTAIN. Anything it cannot read -- a
    missing table, an unreadable one -- returns True and the case is solved, so
    a failure here costs time and never a number. The names it checks are the
    same ones `named_in` checks afterwards, and `named_in` still has the last
    word on what was actually resolved.
    """
    try:
        from src import case_tables
        tcs = case_tables.read(folder, 'TCs')
    except Exception:
        return True
    columns = [c for c in ('TC_target_key', 'Input_layer_key') if c in tcs.columns]
    if not columns:
        return True
    present = {str(v).strip() for c in columns for v in tcs[c].unique()}
    return any(name in present for name in names)


def roads_of(run, resource: str, years) -> dict:
    """That case's recovered mass per road, per year per draw."""
    keys = run.keys
    layer = _resource_of(run)          # every depth, not just the deepest
    out = {}
    for road, flows in routes(run).items():
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
            out[road] = draws
    return out


def added(parts: list[dict]) -> dict:
    """
    Several accounts added, per draw.

    Every key is (draws x years), and draw i is the same world in every case --
    same fleet, same year -- so adding within the draw and taking percentiles
    afterwards gives the interval of the SUM. Adding percentiles instead would
    assume every stream hits its own 97.5th at once, which is wider than any
    world can be.
    """
    keys = [k for k in parts[0] if k != 'years']
    whole = {k: sum(part[k] for part in parts) for k in keys}
    whole['years'] = parts[0]['years']
    return whole


def domains_of(run, resource: str) -> list[str]:
    """The streams this case carries for the metal: Wiring, Motors, PCB ..."""
    keys = run.keys
    layer = _resource_of(run)          # every depth, not just the deepest
    return sorted({d for d in keys.loc[keys[layer] == resource,
                                       'Layer 2'].unique() if d})


def _tight_step(rough: float) -> float:
    """
    A step a person counts in: 1, 1.5, 2, 2.5, 3, 4 or 5 times a power of ten.

    Finer than the shared one in src/plot_monte_carlo, which offers only 1, 2,
    2.5 and 5: on 11 Mt that gives a step of 5 and an axis running to 20, with
    nearly half the panel empty above the data.
    """
    if not np.isfinite(rough) or rough <= 0:
        return 1.0
    power = 10.0 ** np.floor(np.log10(rough))
    for nice in (1, 1.5, 2, 2.5, 3, 4, 5, 10):
        if rough <= nice * power:
            return float(nice * power)
    return float(10 * power)


def _accumulate(block, years):
    """
    A per-year flow turned into its running total, BY TRAPEZOID.

    These years are five apart. Summing them as though each stood for one year
    would understate the total fivefold -- a different answer, not a rounding
    difference -- so the gaps between them are used.
    """
    gaps = np.diff(np.asarray(years, dtype=float))
    middles = 0.5 * (block[:, 1:] + block[:, :-1]) * gaps
    return np.concatenate([np.zeros((block.shape[0], 1)),
                           np.cumsum(middles, axis=1)], axis=1)


def _five(per_stream: dict, label: str, per_year_of):
    """
    The five things every figure here shows, in order: total, and then the
    metal in wire, motors, PCBs and sensors.

    `per_year_of` takes one account and returns that entity's annual flow, so
    the same five are built for "with the BEV" and for "lost" without either
    figure knowing how the other is defined.
    """
    order = sorted(per_stream)
    whole = {k: sum(one[k] for one in per_stream.values())
             for k in ('inflow', 'outflow', 'recovered')}
    return ([(f'total {label}', per_year_of(whole))]
            + [(f'{label} in {stream}', per_year_of(per_stream[stream]))
               for stream in order])


# THE UNIT EVERY FIGURE HERE IS DRAWN IN.
#
# PINNED, NOT CHOSEN PER FIGURE. `scale_for` picks the coarsest readable unit
# from each figure's own magnitudes, which is right for a page of panels each
# read on its own. Across THIS set it is wrong: the running totals landed in Mt
# and the annual flows in kt, so two figures side by side could not be compared
# without reading both axes first. Asked for 2026-09-25: "you have Mt, kt and
# it should be either kt/year or total kt or Mt".
#
# A RATE AXIS CARRIES `/year`. Half of these panels are an annual flow and half
# are its running total, and both used to be labelled with a bare mass unit.
# The unit itself now says which, so the axis reads without the subtitle.
AXIS_UNIT = 'kt'


def figure_combined(whole: dict, roads: dict, years, theme: str, unit: str,
                    label: str, title: str, streams: list[str]):
    """
    THE ACCOUNT, in the same language as the other two figures.

    Nothing on top of the lines, a legend of names under the axes, and one
    meaning per line style: SOLID is a mass on the left axis, DASHED is the
    part of the recovered mass that came back on one road, and the recovery
    rate has the right axis to itself. The mixed dotted, dash-dot and dashed
    patterns this replaces were a code with nothing behind it.

    The order is the order the metal travels -- entering the fleet, leaving it,
    reaching a recycler, recovered, then what did not come back -- so the
    legend can be read straight down rather than matched item by item.
    """
    scale, shown = factor(unit, AXIS_UNIT), AXIS_UNIT
    figure, axes, colours = chart(1320, 880, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    rate_axis = panel.twinx()
    mean = lambda block: np.nanmean(block, axis=0)

    # The 95% band of what leaves the fleet: the fleet's own uncertainty, which
    # every mass here inherits and none of the others can show without turning
    # the figure into mud.
    low = np.nanpercentile(whole['outflow'], 2.5, axis=0)
    high = np.nanpercentile(whole['outflow'], 97.5, axis=0)
    panel.fill_between(years, low * scale, high * scale, color=colours['title'],
                       alpha=0.10, linewidth=0, zorder=0)

    # DASHED MEANS LOST. Never collected and lost inside recycling are the two
    # ways the metal fails to come back, and they are the only dashed lines
    # here; everything else -- what enters, what leaves, what reaches a
    # recycler, what is recovered -- is solid. One code, one meaning.
    # SEVEN SERIES ON THIS PANEL -- four solid, two dashed, and the rate on its
    # own axis -- so under BANDS_BELOW every one of them is banded. `outflow`
    # and the two losses already were; this is what makes the figure
    # consistent, which is the whole of the 2026-09-18 change.
    solid = (('inflow', 'entering the fleet', colours['meta'], 1.8),
             ('outflow', 'leaving the fleet', colours['title'], 3.2),
             ('collected', 'reaching a recycler', STREAM_COLOURS[0], 2.2),
             ('recovered', 'recovered', STREAM_COLOURS[3], 2.6))
    band_all = len(solid) + 3 < BANDS_BELOW      # + the two losses and the rate

    for key, name, colour, width in solid:
        line = mean(whole[key])
        if not np.isfinite(line).any():
            continue
        if band_all and key != 'outflow':        # outflow's band is drawn above
            panel.fill_between(years,
                               np.nanpercentile(whole[key], 2.5, axis=0) * scale,
                               np.nanpercentile(whole[key], 97.5, axis=0) * scale,
                               color=colour, alpha=0.09, linewidth=0, zorder=1)
        panel.plot(years, line * scale, color=colour, linewidth=width,
                   zorder=3, solid_capstyle='round', label=name)

    # THE TWO LOSSES CARRY THEIR OWN BANDS, from their own draws. They were the
    # only quantities on this figure drawn as a bare mean, and they are the two
    # a reader is least willing to take on trust -- the metal that does not
    # come back. Each band is the 2.5 and 97.5 percentiles of THAT array, which
    # `account` built per draw as outflow - collected and collected - recovered
    # in every draw; nothing here adds one interval to another.
    for key, name, colour in (('uncollected', 'never collected', STREAM_COLOURS[1]),
                              ('lost', 'lost inside recycling', STREAM_COLOURS[2])):
        panel.fill_between(years,
                           np.nanpercentile(whole[key], 2.5, axis=0) * scale,
                           np.nanpercentile(whole[key], 97.5, axis=0) * scale,
                           color=colour, alpha=0.10, linewidth=0, zorder=1)
        panel.plot(years, mean(whole[key]) * scale, color=colour, linewidth=2.2,
                   linestyle=(0, (5, 3)), zorder=3, label=name)

    # HANDED ON, only where some of it is: neither recovered here nor lost, so
    # it is solid like the recovered mass and not dashed like the losses. A set
    # of cases with no `handoff` flow has an all-zero array and this draws
    # nothing -- the figure is the one it always was.
    handed = whole.get('handed')
    if handed is not None and np.nanmax(mean(handed)) > 0:
        panel.fill_between(years,
                           np.nanpercentile(handed, 2.5, axis=0) * scale,
                           np.nanpercentile(handed, 97.5, axis=0) * scale,
                           color=STREAM_COLOURS[4], alpha=0.10, linewidth=0, zorder=1)
        panel.plot(years, mean(handed) * scale, color=STREAM_COLOURS[4],
                   linewidth=2.2, zorder=3, label='handed on, not counted here')

    with np.errstate(invalid='ignore', divide='ignore'):
        rate = np.where(whole['collected'] > 0,
                        100 * whole['recovered'] / whole['collected'], np.nan)
    median = np.nanpercentile(rate, 50, axis=0)
    rate_axis.fill_between(years, np.nanpercentile(rate, 2.5, axis=0),
                           np.nanpercentile(rate, 97.5, axis=0),
                           color=RATE_COLOUR, alpha=0.14, linewidth=0)
    rate_axis.plot(years, median, color=RATE_COLOUR, linewidth=3.2, zorder=4,
                   label='recovery rate')
    rate_axis.set_ylim(0, 100)
    rate_axis.set_yticks([0, 25, 50, 75, 100])
    rate_axis.set_ylabel('recovery rate (%)', color=RATE_COLOUR, fontsize=16)
    rate_axis.tick_params(colors=RATE_COLOUR, labelsize=17)
    for side in ('top', 'left', 'bottom'):
        rate_axis.spines[side].set_visible(False)
    rate_axis.spines['right'].set_color(RATE_COLOUR)
    rate_axis.grid(False)
    panel.set_zorder(rate_axis.get_zorder() + 1)
    panel.patch.set_visible(False)

    step = _tight_step(float((high * scale).max()) / 4)
    panel.set_ylim(0, step * 4)
    panel.set_yticks([step * n for n in range(5)])
    panel.set_ylabel(f'mass per year ({shown}/year)',
                     color=colours['title'], fontsize=16)
    panel.set_xlim(years[0], years[-1])
    panel.set_xlabel('year', color=colours['meta'], fontsize=17)
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=18)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)

    header(figure, f'{title}: {label}, every stream added', colours,
           f'{years[0]}-{years[-1]}, means, added per draw.  '
           f'{" + ".join(streams)}.  DASHED: lost -- never collected, and lost '
           f'inside recycling.  solid: everything else.  each band is 95% of '
           f"that line's own draws")
    figure.subplots_adjust(bottom=0.155)
    handles, labels = panel.get_legend_handles_labels()
    extra = rate_axis.get_legend_handles_labels()
    legend = figure.legend(handles + extra[0], labels + extra[1], fontsize=13.5,
                           frameon=False, ncol=5, loc='lower center',
                           bbox_to_anchor=(0.5, 0.022), handlelength=1.9,
                           columnspacing=1.6, handletextpad=0.45,
                           borderpad=0.0, labelspacing=0.4)
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    return figure


def _short(name: str, end) -> str:
    """
    The name with nothing repeated in it: no year, no metal, no run-on words.

    `_five` builds every entry as `total <metal>` or `<metal> in <stream>`, so
    the metal is on all of them and says nothing -- the figure is titled with
    it. THE METAL IS STRIPPED BY SHAPE, NOT BY NAME: this used to match the
    literal word `copper`, which was the only metal there was until
    `--resource` arrived, so every nickel, cobalt and lithium legend read
    "nickel in wiring" and "total nickel".

    AND A camelCase NAME IS SPLIT INTO WORDS BEFORE IT IS LOWERED.
    `batteryPackCellTerminals` came out as `batterypackcellterminals`, which is
    a word nobody can read at legend size. The electronics streams were Wiring,
    Motors, PCB and Sensors and none of them showed the fault; the battery's
    components are named the way the composition workbook names them.
    """
    text = re.sub(rf'\s+(in|by)\s+{end}\s*$', '', str(name))
    text = re.sub(r',?\s*(right axis|of what was collected|reusable)\s*', ' ',
                  text, flags=re.IGNORECASE)

    if re.fullmatch(r'(the\s+)?total\s+\S+', text.strip(), flags=re.IGNORECASE):
        return 'total'
    text = re.sub(r'^(the\s+)?\S+\s+in\s+', '', text, flags=re.IGNORECASE)

    # aBc -> aB c, and ABCd -> ABC d, so an acronym keeps its run.
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    return re.sub(r'\s{2,}', ' ', text).strip().lower() or 'total'


def _one_panel(entries, years, theme, unit, title, subtitle, left, right):
    """
    TWO PANELS, ONE ABOVE THE OTHER, AND NOTHING ON TOP OF EITHER.

    It was one panel with a twin axis: the running total on the left, the
    annual flow that builds it on the right, the second said with dashes. That
    shape held four streams and a single band. It could not hold a band on BOTH
    totals, and the reason is structural rather than cosmetic -- the two axes
    are tied so their zeros share a line, so making room for one band rescales
    the other axis too. Filled, the two bands were the same grey and crossed;
    drawn as dashed edges they read as more lines; ruled to fit, the left axis
    doubled and the total fell into the lower half of its own figure. Three
    attempts, three different faults, one cause.

    Split, each quantity has its own panel, its own ruling and its own filled
    band, and there is no ambiguity about which band belongs to which line.
    THE DASH CODE GOES WITH IT: colour now means stream and nothing else, which
    is one thing fewer to hold.

    BOTH PANELS SHARE A UNIT, NOT AN AXIS. They are drawn in the same unit --
    kt, see AXIS_UNIT -- but `rule` gives each panel limits from its own data,
    so a running total reaching 20,000 and an annual flow reaching 1,200 both
    fill their own panel. A HEIGHT IN ONE THEREFORE DOES NOT COMPARE WITH A
    HEIGHT IN THE OTHER; read the numbers.

    That comparison was the point of the twin axis this replaced, and it did
    NOT survive the split -- the docstring and both subtitles claimed it still
    did until 2026-09-25. Letting the panels share limits would put the annual
    flow in the bottom twentieth of its own panel, which is why they do not.

    Only the bottom panel is ticked and labelled in years; they are the same
    years.
    """
    running = [(name, _accumulate(block, years)) for name, block in entries]
    scale, shown = factor(unit, AXIS_UNIT), AXIS_UNIT

    figure, axes, colours = chart(1320, 1000, theme, 2, 1, height_ratios=(3, 2))
    top, bottom = axes.ravel()

    def rule(axis, blocks):
        # ONLY AS MUCH ROOM BELOW ZERO AS THE DATA ACTUALLY NEEDS. Reserving a
        # whole tick for a dip of -8 kt against 550 left a third of the panel
        # empty; the floor is the dip itself, with a little air. The band is in
        # `blocks`, so an interval is never clipped.
        low = min(float((b * scale).min()) for b in blocks)
        high = max(float((b * scale).max()) for b in blocks)
        if high <= 0:
            step, count = 1.0, 4
        else:
            # FOUR INTERVALS OR FIVE, whichever wastes less. Fixed at four, a
            # top of 24.3 rounded its step from 6.08 up to 10 and ruled the
            # panel to 40 -- the line reached the middle and the upper half was
            # white. Five intervals put the same data at 25.
            step, count = min(((_tight_step(high / n), n) for n in (4, 5)),
                              key=lambda pair: pair[0] * pair[1])
        axis.set_ylim(0.0 if low >= -1e-12 else low * 1.2, step * count)
        axis.set_yticks([step * n for n in range(count + 1)])

    # TOTAL FIRST, then the streams alphabetically. The total is the headline,
    # so it leads the legend; the streams follow in an order a reader can
    # predict rather than one that depends on which happens to be largest this
    # run. Colour follows that same order, so a stream keeps its colour when
    # the numbers change.
    ranked = sorted(range(1, len(entries)),
                    key=lambda i: _short(entries[i][0], years[-1]))

    # THE TOP PANEL IS A TOTAL, THE BOTTOM ONE A RATE, so they do not carry
    # the same unit string even though both are drawn in kt.
    for axis, blocks, label, units in (
            (top, [b for _, b in running], left, shown),
            (bottom, [b for _, b in entries], right, f'{shown}/year')):
        whole = blocks[0]
        low = np.nanpercentile(whole, 2.5, axis=0)
        high = np.nanpercentile(whole, 97.5, axis=0)
        axis.fill_between(years, low * scale, high * scale,
                          color=colours['title'], alpha=0.12, linewidth=0,
                          zorder=1)
        axis.plot(years, np.nanmean(whole, axis=0) * scale,
                  color=colours['title'], linewidth=3.2, zorder=4,
                  solid_capstyle='round')
        for place, i in enumerate(ranked):
            axis.plot(years, np.nanmean(blocks[i], axis=0) * scale,
                      color=STREAM_COLOURS[place % len(STREAM_COLOURS)],
                      linewidth=2.2, zorder=3, solid_capstyle='round')

        # THE LINES AND THE BAND, NOT THE RAW DRAWS. `blocks` is draws x years,
        # so its .max() is the single most extreme draw -- that ruled the top
        # panel to 40 Mt for a band reaching 24 and left half the panel white.
        rule(axis, [np.nanmean(b, axis=0) for b in blocks] + [low, high])
        axis.set_ylabel(f'{label} ({units})', color=colours['title'],
                        fontsize=15)
        axis.set_xlim(years[0], years[-1])
        axis.set_xticks([y for y in years if y % 10 == 0] or list(years))
        axis.tick_params(labelsize=16)
        axis.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)
        axis.axhline(0, color=colours['rule'], linewidth=0.9, zorder=0)

    top.tick_params(labelbottom=False)
    bottom.set_xlabel('year', color=colours['meta'], fontsize=16)

    header(figure, title, colours, subtitle)

    from matplotlib.lines import Line2D
    names = [_short(entries[0][0], years[-1])] + \
        [_short(entries[i][0], years[-1]) for i in ranked]
    handles = [Line2D([], [], color=colours['title'], linewidth=3.2)] + [
        Line2D([], [], color=STREAM_COLOURS[place % len(STREAM_COLOURS)],
               linewidth=2.2) for place in range(len(ranked))]

    # ONE STRIP, RESERVED AFTER `header` -- that function ends with
    # tight_layout(rect=[0, 0, ...]), so a bottom margin set before it is
    # thrown away and the legend lands on the `year` label. It wraps at five.
    per_row = 5
    rows_of_legend = -(-len(names) // per_row)
    figure.subplots_adjust(
        bottom=((62 + 26 * rows_of_legend) / 72.0) / figure.get_figheight(),
        hspace=0.12)
    legend = figure.legend(handles, names, fontsize=13.5, frameon=False,
                           ncol=min(per_row, len(names)), loc='lower center',
                           bbox_to_anchor=(0.5, 0.012), handlelength=1.9,
                           columnspacing=1.5, handletextpad=0.45,
                           borderpad=0.0)
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    return figure


def figure_with_the_bev(per_stream: dict, years, theme: str, unit: str,
                        label: str, title: str):
    """
    THE METAL THAT IS WITH THE BEV, for the five: total, wire, motors, PCBs,
    sensors.

    Per year is what the fleet takes in and does not give back: entering minus
    leaving. In complete is the running total of that -- the metal sitting in
    cars on the road. It counts from the first year shown, so what was already
    on the road then is not in it.
    """
    entries = _five(per_stream, label, lambda a: a['inflow'] - a['outflow'])
    return _one_panel(
        entries, years, theme, unit,
        f'{title}: the {label} that is with the BEV',
        f'{years[0]}-{years[-1]}, means, added per draw.  above: what the fleet '
        f'holds; below: what it takes in each year.  a band on each total, 95% '
        f'of its draws.  each panel is ruled to its own data -- same unit, '
        f'different heights.  counted from {years[0]}',
        'in the fleet', 'added per year')


def figure_lost(per_stream: dict, years, theme: str, unit: str,
                label: str, title: str):
    """
    THE METAL LOST AND NOT RECYCLED, for the same five.

    Per year is what left the fleet and did not come back: leaving minus
    recovered. In total is its running sum.
    """
    entries = _five(per_stream, label, lambda a: a['outflow'] - a['recovered'])
    return _one_panel(
        entries, years, theme, unit,
        f'{title}: the {label} lost and not recycled',
        f'{years[0]}-{years[-1]}, means, added per draw.  above: lost in total; '
        f'below: lost each year.  a band on each total, 95% of its draws.  '
        f'each panel is ruled to its own data -- same unit, different heights.  '
        f'counted from {years[0]}',
        'lost in total', 'lost per year')


















def reasons_of(run, resource: str, domain: str, years) -> dict:
    """Why this ONE stream's metal did not come back, per year per draw."""
    from src.rest import flow_roles
    keys = run.keys
    layer = _resource_of(run)          # every depth, not just the deepest
    process_of = dict(zip(run.tcs['Output_FlowID'], run.tcs['process']))
    out = {}
    for flow, role in flow_roles(run.case).items():
        if role != 'loss':
            continue
        name = f'lost in {str(process_of.get(flow, flow)).replace("_", " ")}'
        columns = []
        for year in years:
            rows = np.flatnonzero(
                (keys['Stock/Flow ID'] == flow).to_numpy()
                & (keys[layer] == resource).to_numpy()
                & (keys['Layer 2'] == domain).to_numpy()
                & (keys['Year'].astype(str) == str(year)).to_numpy())
            columns.append(run.values[rows].sum(axis=0) if rows.size
                           else np.zeros(run.draws))
        block = np.column_stack(columns)
        if block.mean(axis=0).max() > 0:
            out[name] = out.get(name, 0) + block
    return out




def _shared_prefix(names: list[str]) -> int:
    """
    How much of every case's folder name is the same, to the last underscore.

    `bev_electronics_wiring` and `bev_electronics_boards` share
    `bev_electronics_`, so the legend can say `wiring` and `boards` -- the part
    that distinguishes them, which is the part a reader needs. Cut on an
    underscore so a shared prefix never chops a word in half, and only when
    something is left over: two cases named the same but for a digit keep their
    full names rather than becoming `1` and `2`.
    """
    if len(names) < 2:
        return 0
    cut = 0
    for position, character in enumerate(names[0]):
        if any(len(name) <= position or name[position] != character
               for name in names[1:]):
            break
        if character == '_':
            cut = position + 1
    return cut if all(len(name) > cut for name in names) else 0


def combine_one(params, wanted, label: str) -> int:
    """
    One metal, across every case in `combine.cases`. Returns an exit code.

    THE METAL IS PASSED, not read back out of a mutated copy of the settings.
    `combine.resources` names several and this draws one of them; handing it in
    means the caller's loop is the only thing that knows which.
    """
    wanted = tuple(wanted)
    parts, streams, roads, years = [], [], {}, None
    per_stream, reasons, per_stream_reasons = {}, {}, {}
    shorten = _shared_prefix([os.path.basename(c) for c in params.combine.cases])

    print(f'Combining : {label} across '
          f'{len(params.combine.cases)} case(s)')
    for folder in params.combine.cases:
        if not os.path.isdir(folder):
            raise CombineError(
                f'{folder} is not a folder. `combine.cases` in '
                f'src/params_schema.py names the case folders to add.')
        # A CASE LEAVES A PASS IT HAS NO SCENARIO FOR. Sodium has no S1 and
        # solid-state has neither S1 nor S2, so without this the S1 pass reached
        # sodium, was refused, and stopped the run (2026-10-09).
        if not offers_scenario(params, folder):
            print(f'  {folder}: has no {params.run.scenario} -- not solved')
            continue
        if not could_carry(folder, wanted, params):
            print(f'  {folder}: no {" / ".join(wanted)} in its coefficients '
                  f'-- not solved')
            continue
        print(f'  solving {folder} ...', flush=True)
        run = solve_draws(folder, LAYER_NAMES,
                          draws=params.data.draws,
                          seed=params.monte_carlo.seed,
                          # PASSED, NOT LOOKED UP. solve_draws falls back to a
                          # Params() of its own, which cannot see a flag set on
                          # this one -- the second source of truth that made
                          # every upstream case refuse its own scenario.
                          scenario=params.run.scenario,
                          tables=refresh(params, folder, quiet=True),
                          chunk=params.monte_carlo.chunk,
                          budget_gb=params.monte_carlo.memory_budget_gb,
                          rule=params.monte_carlo.sum_to_one,
                          quiet=True)
        used = named_in(run, wanted)
        these = sorted(int(year) for year in run.keys['Year'].unique())
        if years is None:
            years = these
        elif these != years:
            raise CombineError(
                f'{folder} covers {these[0]}-{these[-1]} ({len(these)} years) '
                f'but the case before it covers {years[0]}-{years[-1]} '
                f'({len(years)}). Cases can only be added year by year, so set '
                f'`years` in src/params_schema.py to a span they all have.')
        if used is None:
            print(f'    none of {", ".join(wanted)} in this case -- skipped')
            continue
        stream = os.path.basename(folder)[shorten:].replace('_', ' ') \
            or os.path.basename(folder)
        one = account(run, used)
        if one is None:
            print(f'    {used}: no upstream draws for this case -- skipped')
            continue
        parts.append(one)
        streams.append(f'{stream} ({used})')
        for road, draws_of in roads_of(run, used, years).items():
            roads[road] = roads.get(road, 0) + draws_of
        # For the second figure: each stream apart, and why it was lost.
        for domain in domains_of(run, used):
            piece = account(run, used, domain=domain)
            if piece is None:
                continue
            # ⚠️ A STREAM NAMED AFTER THE METAL SAYS NOTHING. The stream label
            # is the case's Layer 2 -- `Wiring`, `PCB`, `Sensors`,
            # `batteryPackCables` -- which names the part the metal sits in.
            # The traction case's components ARE the materials, so its copper
            # stream is called `copper`, and the copper figure came out with a
            # line in its legend labelled `copper`: *"what is the copper?"*
            #
            # Where the domain is the metal's own name it is replaced by the
            # case's, which is what actually distinguishes it. A collision
            # between two cases takes both names.
            name = domain
            if name.strip().lower() in {w.lower() for w in wanted} | {label.lower()}:
                name = stream
            if name in per_stream:
                name = f'{stream} · {domain}'
            per_stream[name] = piece
            per_stream_reasons[name] = reasons_of(run, used, domain, years)
        why = losses(run, used)
        for name, block in (why or {}).get('reasons', {}).items():
            reasons[name] = reasons.get(name, 0) + block
        print(f'    {used}: '
              f'{readable(float(np.nanmean(one["recovered"][:, -1])), params.run.working_unit)} '
              f'recovered in {years[-1]}')
        del run

    if not parts:
        raise CombineError(
            f'None of the cases resolve any of: {", ".join(wanted)}.\n'
            f'`combine.resources` in src/params_schema.py lists every spelling '
            f'the metal has -- the wiring case calls it `copper`, the boards '
            f'case calls it `Cu`.')

    # THE COMBINED FIGURES CARRY THE SCENARIO TOO. They belong to no one case,
    # so they cannot use figure_style.folder_for -- but three scenarios writing
    # `copper_combined.png` to one folder is the same collision.
    combined_dir = (os.path.join(params.combine.out_dir, params.run.scenario)
                    if params.run.scenario else params.combine.out_dir)
    # AND A FOLDER PER CHOICE (run.variants, src/case_tables.py) when any case
    # added here offers one -- the combined figures answer differently for each,
    # and the frozen copper figures above are exactly what must not be replaced
    # by a different answer written to the same name. No such case, no folder.
    from src import case_tables
    choice = case_tables.label_for(params.combine.cases, params)
    if choice:
        combined_dir = os.path.join(combined_dir, choice)

    figure = figure_combined(added(parts), roads, years, params.figures.theme,
                             params.run.working_unit, label,
                             params.combine.whole, streams)
    # ⚠️ ESSENTIAL, ALL FOUR. `figures/combined/` is the whole output of this
    # stage -- there is no detail here to separate them from, so burying them
    # in `detail/` was sorting a folder into itself. Asked on 2026-09-29:
    # *"why is it in the details folder."*
    written = write(figure, combined_dir,
                    f'{label}_combined',
                    params.figures.enabled(), params.figures.dpi,
                    essential=True)


    with_bev = figure_with_the_bev(per_stream, years, params.figures.theme,
                                   params.run.working_unit,
                                   label, params.combine.whole)
    written += write(with_bev, combined_dir,
                     f'{label}_with_the_bev',
                     params.figures.enabled(), params.figures.dpi,
                     essential=True)

    lost = figure_lost(per_stream, years, params.figures.theme,
                       params.run.working_unit, label,
                       params.combine.whole)
    written += write(lost, combined_dir,
                     f'{label}_lost',
                     params.figures.enabled(), params.figures.dpi,
                     essential=True)

    back = figure_recovered(per_stream, years, params.figures.theme,
                            params.run.working_unit, label,
                            params.combine.whole)
    written += write(back, combined_dir,
                     f'{label}_recovered',
                     params.figures.enabled(), params.figures.dpi,
                     essential=True)

    for path in written:
        print(path)
    return 0


def figure_recovered(per_stream: dict, years, theme: str, unit: str,
                     label: str, title: str):
    """
    WHERE THE RECOVERED METAL COMES FROM, per year: the total and each stream.

    `<label>_combined.png` answers how much comes back. This answers how much
    of it each stream contributed, which is the question the moment a run holds
    more than one case -- and the only question for a metal whose cases are
    about to grow.

    THE BAND IS THE MONTE CARLO'S, NOT A SUM OF INTERVALS. It is the 2.5 and
    97.5 percentiles of the TOTAL PER DRAW: draw i's wiring plus draw i's
    battery, then the percentile over draws. Adding each stream's own interval
    would give a band wider than any single world -- every stream at its low
    end at once is not a world the model ever drew. `_five` sums per draw for
    exactly this reason, and that is the array the band is taken from.

    ONLY THE TOTAL CARRIES A BAND. Five overlapping bands are a wash, and the
    thing a reader compares here is the height of one line against another.
    """
    entries = _five(per_stream, label, lambda a: a['recovered'])
    total_draws = entries[0][1]
    scale, shown = factor(unit, AXIS_UNIT), AXIS_UNIT

    figure, axes, colours = chart(1320, 860, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]

    low = np.nanpercentile(total_draws, 2.5, axis=0) * scale
    high = np.nanpercentile(total_draws, 97.5, axis=0) * scale
    panel.fill_between(years, low, high, color=colours['title'], alpha=0.10,
                       linewidth=0, zorder=1)
    panel.plot(years, np.nanmean(total_draws, axis=0) * scale,
               color=colours['title'], linewidth=3.4, zorder=4,
               solid_capstyle='round', label=_short(entries[0][0], years[-1]))

    for place, (name, block) in enumerate(
            sorted(entries[1:], key=lambda pair: _short(pair[0], years[-1]))):
        panel.plot(years, np.nanmean(block, axis=0) * scale,
                   color=STREAM_COLOURS[place % len(STREAM_COLOURS)],
                   linewidth=2.4, zorder=3, solid_capstyle='round',
                   label=_short(name, years[-1]))

    panel.set_ylabel(f'recovered per year ({shown}/year)',
                     color=colours['title'], fontsize=16)
    panel.set_xlabel('year', color=colours['meta'], fontsize=17)
    panel.set_xlim(years[0], years[-1])
    panel.set_ylim(bottom=0)
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=18)
    panel.grid(alpha=0.2)

    figure.tight_layout()
    header(figure, f'{title}: where the {label} comes back from', colours,
           f'{years[0]}-{years[-1]}, means, added per draw.  band: the total, '
           f'95% of the draws -- the interval of the sum, not the sum of the '
           f'intervals')

    # AFTER `header`, WHICH ENDS WITH tight_layout(rect=[0, 0, ...]). A bottom
    # margin set before it is thrown away and the legend lands on the x label.
    # In points, not a fraction: the strip is one or two rows depending on how
    # many streams the run holds.
    handles, labels = panel.get_legend_handles_labels()
    per_row = 5
    rows_of_legend = -(-len(labels) // per_row)
    figure.subplots_adjust(
        bottom=((62 + 26 * rows_of_legend) / 72.0) / figure.get_figheight())
    figure.legend(handles, labels, loc='lower center',
                  ncol=min(per_row, len(labels)), frameon=False,
                  fontsize=13.5, bbox_to_anchor=(0.5, 0.008))
    return figure


def main(argv=None) -> int:
    """
    Everything this draws is decided in `src/params_schema.py`.

    NO ARGUMENTS, AND NOT BY OVERSIGHT. This project is run by pressing Run on
    the numbered stages; a switch that only exists on a command line is a
    switch the person running this never sees. `combine.cases` says which cases
    are added, `combine.resources` says which metals are drawn, and the case's
    own export says which scenarios -- so this file has nothing left to be told.
    """
    params = Params()
    # WHICH CASE DECIDES THE SET. Wiring and boards alias every name to BAU, so
    # they have no scenarios of their own; the battery does, and it is the one
    # that says how many passes this makes.
    deciding = next((case for case in params.combine.cases
                     if scenarios_available(params, case)),
                    cases_to_run(params)[0])
    scenarios = scenarios_to_run(params, deciding)
    metals = [(names, name) for name, names in params.combine.resources.items()]

    # EVERY METAL, IN EVERY SCENARIO, FROM ONE COMMAND. Each pass is its own
    # combine with its own copy of the settings -- a copy rather than mutating
    # in place, so a failure part way through cannot leave the next pass under
    # the last one's label or scenario. The figures are named from
    # the metal's own label and written under the scenario, so nothing
    # collides.
    #
    # ONLY THE BATTERY DIFFERS BETWEEN SCENARIOS. Wiring and boards send every
    # name to BAU, so a three-scenario run re-solves those two for identical
    # answers. It is done anyway rather than cached: a combine that quietly
    # reused another scenario's solve would be the hardest kind of wrong to
    # notice.
    if len(scenarios) > 1:
        print(f'Scenarios : {", ".join(scenarios)}')
    if len(metals) > 1:
        print(f'Metals    : {", ".join(name for _, name in metals)}')
    for scenario in scenarios:
        for spellings, name in metals:
            one = copy.deepcopy(params)
            one.run.scenario = scenario
            print()
            code = combine_one(one, spellings, name)
            if code:
                return code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
