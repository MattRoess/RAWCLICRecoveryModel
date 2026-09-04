"""
04_combine_cases.py
===================

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
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.figure_style import PALETTE, chart, write
from src.monte_carlo import solve_draws
from src.params_schema import Params
from src.figure_style import PALETTE
from src.plot_monte_carlo import (_round_step, account, account_legend,
                                  draw_account,
                                  header, losses, routes)
from src.rest import LAYERS, REST
from src.units import readable, scale_for
from src.upstream import load as refresh

LAYER_NAMES = ['product', 'component', 'material', 'element']

# FOUR COLOURS FOR THE FOUR STREAMS, fixed and far apart, so wire, motors, PCBs
# and sensors are told apart at a glance and keep the same colour from one
# figure to the next. The total is not among them: it is black, and solid,
# because it is the main line.
# The recovery rate is not a mass, so it does not take a stream colour.
RATE_COLOUR = '#2e7d32'

STREAM_COLOURS = ('#1f77b4',   # blue
                  '#d62728',   # red
                  '#2ca02c',   # green
                  '#ff7f0e')   # orange


class CombineError(ValueError):
    """Raised when the cases named cannot be added together."""


def named_in(run, names) -> str | None:
    """
    Which spelling of the metal this case uses, if any.

    The wiring case resolves materials and calls it `copper`; the boards case
    resolves elements and calls it `Cu`. A case with none of the names given
    contributes nothing and says so, rather than counting zero quietly.
    """
    keys = run.keys
    layer = next((column for column in reversed(LAYERS)
                  if column in keys.columns
                  and keys[column].astype(str).str.strip().any()), None)
    if layer is None:
        return None
    present = {value for value in keys[layer].unique() if value and value != REST}
    return next((name for name in names if name in present), None)


def roads_of(run, resource: str, years) -> dict:
    """That case's recovered mass per road, per year per draw."""
    keys = run.keys
    layer = next(column for column in reversed(LAYERS)
                 if column in keys.columns
                 and keys[column].astype(str).str.strip().any())
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
    layer = next(column for column in reversed(LAYERS)
                 if column in keys.columns
                 and keys[column].astype(str).str.strip().any())
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
    scale, shown = scale_for(np.nanpercentile(whole['outflow'], 97.5, axis=0),
                             unit)
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
    for key, name, colour, width in (
            ('inflow', 'entering the fleet', colours['meta'], 1.8),
            ('outflow', 'leaving the fleet', colours['title'], 3.2),
            ('collected', 'reaching a recycler', STREAM_COLOURS[0], 2.2),
            ('recovered', 'recovered', STREAM_COLOURS[3], 2.6)):
        line = mean(whole[key])
        if np.isfinite(line).any():
            panel.plot(years, line * scale, color=colour, linewidth=width,
                       zorder=3, solid_capstyle='round', label=name)

    for key, name, colour in (('uncollected', 'never collected', STREAM_COLOURS[1]),
                              ('lost', 'lost inside recycling', STREAM_COLOURS[2])):
        panel.plot(years, mean(whole[key]) * scale, color=colour, linewidth=2.2,
                   linestyle=(0, (5, 3)), zorder=3, label=name)

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
    panel.set_ylabel(f'mass ({shown})', color=colours['title'], fontsize=16)
    panel.set_xlim(years[0], years[-1])
    panel.set_xlabel('year', color=colours['meta'], fontsize=17)
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=18)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)

    header(figure, f'{title}: {label}, every stream added', colours,
           f'{years[0]}-{years[-1]}, means, added per draw.  '
           f'{" + ".join(streams)}.  DASHED: lost -- never collected, and lost '
           f'inside recycling.  solid: everything else.  band: what leaves the '
           f'fleet, 95%')
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
    """The name with nothing repeated in it: no year, no `copper in`."""
    text = re.sub(rf'\s+(in|by)\s+{end}\s*$', '', str(name))
    text = re.sub(r',?\s*(right axis|of what was collected|reusable)\s*', ' ',
                  text, flags=re.IGNORECASE)
    text = re.sub(r'^(the\s+)?(total\s+)?copper(\s+in)?\s*', '', text,
                  flags=re.IGNORECASE)
    return re.sub(r'\s{2,}', ' ', text).strip().lower() or 'total'


def _one_panel(entries, years, theme, unit, title, subtitle, left, right):
    """
    ONE PANEL, AND NOTHING ON TOP OF IT.

    The plotting area holds only lines: five solid for the running total, five
    dashed for the annual flow that builds it. The legend sits BELOW the axes,
    where it explains without covering anything -- a legend dropped into the
    panel lands on a line as soon as the data moves.

    THE LEGEND SAYS THE TWO THINGS A READER NEEDS AND STOPS. Which colour is
    which stream, and what solid and dashed mean. No numbers: they were on the
    lines, then in the legend, then in a table beside it, and every version put
    a dozen figures in front of the picture they were meant to support. The
    axes are ruled well enough to read a value off, and an exact number belongs
    in recovery_results.xlsx.

    A stream keeps its colour across solid and dashed, so the eye follows a
    colour rather than learning a second code. The total is black and heaviest,
    because it is the answer.

    BOTH AXES CARRY THE SAME UNIT, ruled in four intervals, so one set of
    gridlines serves them both and a height on the left compares with a height
    on the right. Five numbers an axis, at a size that can be read.
    """
    running = [(name, _accumulate(block, years)) for name, block in entries]
    scale, shown = scale_for(np.nanmean(running[0][1], axis=0), unit)

    figure, axes, colours = chart(1320, 860, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    flow_axis = panel.twinx()

    # TOTAL FIRST, then the streams alphabetically. The total is the headline,
    # so it leads the legend; the four streams follow in an order a reader can
    # predict rather than one that depends on which happens to be largest this
    # run. Colour follows that same order, so a stream keeps its colour when
    # the numbers change.
    ranked = sorted(running[1:], key=lambda pair: _short(pair[0], years[-1]))
    by_name = dict(entries)
    total = np.nanmean(running[0][1], axis=0) * scale

    panel.plot(years, total, color=colours['title'], linewidth=3.4, zorder=4,
               solid_capstyle='round', label=_short(entries[0][0], years[-1]))
    flow_axis.plot(years, np.nanmean(entries[0][1], axis=0) * scale,
                   color=colours['title'], linewidth=1.7, linestyle=(0, (5, 3)),
                   alpha=0.55, zorder=1)

    for place, (name, block) in enumerate(ranked):
        colour = STREAM_COLOURS[place % len(STREAM_COLOURS)]
        panel.plot(years, np.nanmean(block, axis=0) * scale, color=colour,
                   linewidth=2.4, zorder=3, solid_capstyle='round',
                   label=_short(name, years[-1]))
        flow_axis.plot(years, np.nanmean(by_name[name], axis=0) * scale,
                       color=colour, linewidth=1.5, linestyle=(0, (5, 3)),
                       alpha=0.55, zorder=1)

    def rule(axis, low, high):
        # ONLY AS MUCH ROOM BELOW ZERO AS THE DATA ACTUALLY NEEDS. Reserving a
        # whole tick for a dip of -8 kt against 550 left a third of the panel
        # empty; the floor is the dip itself, with a little air.
        step = _tight_step(high / 4) if high > 0 else 1.0
        floor = 0.0 if low >= -1e-12 else low * 1.2
        axis.set_ylim(floor, step * 4)
        axis.set_yticks([step * n for n in range(5)])

    # THE TWO ZEROS SIT ON THE SAME LINE. The annual flow dips slightly below
    # zero once the fleet gives back more than it takes, so its axis needs a
    # little room underneath; giving that room to one axis and not the other
    # put the two zeros at different heights, and then a dashed line crossing a
    # solid one meant nothing. Both axes take the same relative floor, so the
    # baseline is shared and only the left is ticked below zero when it has to
    # be.
    flows = [np.nanmean(b, axis=0) * scale for _, b in entries]
    rule(flow_axis, float(min(f.min() for f in flows)),
         float(max(f.max() for f in flows)))
    low, high = flow_axis.get_ylim()
    share = (0.0 - low) / (high - low) if high > low else 0.0

    step = _tight_step(float(total.max()) / 4)
    top = step * 4
    panel.set_ylim(-top * share / (1 - share) if 0 < share < 1 else 0, top)
    panel.set_yticks([step * n for n in range(5)])

    panel.set_ylabel(f'{left} ({shown})', color=colours['title'], fontsize=17)
    flow_axis.set_ylabel(f'{right} ({shown})', color=colours['meta'], fontsize=16)
    flow_axis.tick_params(colors=colours['meta'], labelsize=17)
    for side in ('top', 'left', 'bottom'):
        flow_axis.spines[side].set_visible(False)
    flow_axis.spines['right'].set_color(colours['rule'])
    flow_axis.grid(False)
    panel.set_zorder(flow_axis.get_zorder() + 1)
    panel.patch.set_visible(False)

    panel.set_xlim(years[0], years[-1])
    panel.set_xlabel('year', color=colours['meta'], fontsize=17)
    panel.set_xticks([y for y in years if y % 10 == 0] or list(years))
    panel.tick_params(labelsize=18)
    panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, zorder=0)

    header(figure, title, colours, subtitle)
    figure.subplots_adjust(bottom=0.125)

    handles, labels = panel.get_legend_handles_labels()
    # ONE STRIP, AND IT EXPLAINS ITSELF. The names and the solid/dashed code
    # were two rows plus a caption, which took a fifth of the figure to say
    # seven short things. Two neutral keys carry the code, so the whole legend
    # is one line under the axes -- clear of the `year` label, and the picture
    # keeps the space.
    from matplotlib.lines import Line2D
    handles += [Line2D([], [], color=colours['meta'], linewidth=2.2),
                Line2D([], [], color=colours['meta'], linewidth=1.5,
                       linestyle=(0, (5, 3)))]
    labels += [f'{left} (left)', f'{right} (right)']
    legend = figure.legend(handles, labels, fontsize=13.5, frameon=False,
                           ncol=len(labels), loc='lower center',
                           bbox_to_anchor=(0.5, 0.022), handlelength=1.9,
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
        f'{years[0]}-{years[-1]}, means, added per draw.  SOLID: in the fleet, left '
        f'axis.  DASHED, same colour: added per year, right axis.  labelled '
        f'values are {years[-1]}.  counted from {years[0]}',
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
        f'{years[0]}-{years[-1]}, means, added per draw.  SOLID: lost in total, left '
        f'axis.  DASHED, same colour: lost per year, right axis.  labelled '
        f'values are {years[-1]}.  counted from {years[0]}',
        'lost in total', 'lost per year')


















def figure_streams(whole: dict, roads: dict, reasons: dict, per_stream: dict,
                   years, theme: str, unit: str, label: str, title: str):
    """
    WHERE THE COPPER IS -- the combination, and the four streams it is made of.

    A SEPARATE FIGURE from `copper_combined.png`, which stays the account and
    nothing else. This one answers a different question: not how much comes
    back, but where the metal actually sits and which stream it sits in.

    On one set of axes, because everything drawn is a mass in the same unit and
    the point is that any two compare by the distance between them:

    - the account itself, as the combined figure draws it, so the two can be
      read against each other;
    - **each stream apart** -- Wiring, Motors, PCB, Sensors -- as the copper it
      returns. The four are what the total is made of;
    - **what the fleet absorbs each year**, the flow that builds the stock;
    - **why the rest does not come back**, one line per reason rather than one
      lumped `lost inside recycling`.

    THE FLEET'S STOCK IS A NUMBER, NOT A LINE. It is 11 Mt against half a
    megatonne of annual flow, so drawn on this axis it would press every flow
    onto zero -- a stock and an annual flow cannot share a linear mass axis.
    Stated instead, where it can be read exactly.

    `recovered as a share of what the fleet BUYS` shares the rate axis rather
    than adding a third scale to read.
    """
    net, held = trapped(whole, years)
    scale, shown = scale_for(np.nanpercentile(whole['outflow'], 97.5, axis=0),
                             unit)
    figure, axes, colours = chart(1300, 900, theme, 1, 1)
    panel = axes if not hasattr(axes, 'ravel') else axes.ravel()[0]
    rate_axis = draw_account(panel, f'{title} {label}', whole, roads, years,
                             scale, shown, colours)
    end = years[-1]

    held_mean = np.nanmean(held, axis=0)
    out_mean = np.nanmean(whole['outflow'], axis=0)
    panel.annotate(f'held by the fleet by {end}: {readable(held_mean[-1], unit)}\n'
                   f'accumulated from {years[0]}, about '
                   f'{held_mean[-1] / max(out_mean[-1], 1e-9):.0f}x a year\u2019s outflow',
                   xy=(0.015, 0.60), xycoords='axes fraction',
                   color=PALETTE[5], fontsize=13, fontweight='bold', va='top')
    net_mean = np.nanmean(net, axis=0)
    panel.plot(years, net_mean * scale, color=PALETTE[5], linewidth=1.8,
               linestyle=(0, (4, 2)), marker='o', markersize=3,
               label=f'absorbed by the fleet, per year   '
                     f'{readable(net_mean[-1], unit)} in {end}')

    for place, (stream, one) in enumerate(sorted(per_stream.items())):
        mean = np.nanmean(one['recovered'], axis=0)
        panel.plot(years, mean * scale, color=PALETTE[place % len(PALETTE)],
                   linewidth=1.7, linestyle=(0, (6, 2)), marker='o',
                   markersize=3,
                   label=f'recovered from {stream}   '
                         f'{readable(mean[-1], unit)} in {end}')

    # `never collected` is already drawn by the account; only the RECYCLING
    # losses are split here, or it would appear twice under two names.
    split = {why: block for why, block in reasons.items()
             if 'never collected' not in why}
    for place, (why, block) in enumerate(sorted(
            split.items(), key=lambda pair: -float(np.nanmean(pair[1][:, -1])))):
        mean = np.nanmean(block, axis=0)
        panel.plot(years, mean * scale, color=PALETTE[(place + 6) % len(PALETTE)],
                   linewidth=1.6, linestyle=(0, (1, 1.5)), marker='o',
                   markersize=3,
                   label=f'{why}   {readable(mean[-1], unit)} in {end}')

    with np.errstate(invalid='ignore', divide='ignore'):
        circular = np.where(whole['inflow'] > 0,
                            100 * whole['recovered'] / whole['inflow'], np.nan)
    median = np.nanpercentile(circular, 50, axis=0)
    rate_axis.plot(years, median, color=PALETTE[2], linewidth=2.2,
                   linestyle=(0, (5, 2)), marker='o', markersize=3,
                   label=f'recovered as a share of what the fleet BUYS, right '
                         f'axis   {median[0]:.0f} \u2192 {median[-1]:.0f}%')

    header(figure, f'{title}: where the {label} is', colours,
           f'{years[0]}-{years[-1]}, {len(years)} years, one point each.  the '
           f'combination and the four streams it is made of, ADDED PER DRAW.  '
           f'masses are MEANS in the same unit, so any two compare by the '
           f'distance between them.  the fleet stock is stated, not drawn: it '
           f'is a stock, and this axis carries flows')
    # THE SAME LEGEND AS THE OTHER TWO: one block under the axes, names only,
    # nothing on top of the lines. The end-of-line labels this replaces put a
    # dozen names and numbers down the right edge of the picture.
    handles, labels = panel.get_legend_handles_labels()
    extra = rate_axis.get_legend_handles_labels()
    handles, labels = handles + extra[0], labels + extra[1]
    labels = [_short(text, years[-1]) for text in labels]
    figure.subplots_adjust(bottom=0.175)
    legend = figure.legend(handles, labels, fontsize=13.5, frameon=False,
                           ncol=4, loc='lower center',
                           bbox_to_anchor=(0.5, 0.022), handlelength=1.9,
                           columnspacing=1.6, handletextpad=0.45,
                           borderpad=0.0, labelspacing=0.4)
    for text in legend.get_texts():
        text.set_color(colours['meta'])
    return figure


































def reasons_of(run, resource: str, domain: str, years) -> dict:
    """Why this ONE stream's metal did not come back, per year per draw."""
    from src.rest import flow_roles
    keys = run.keys
    layer = next(column for column in reversed(LAYERS)
                 if column in keys.columns
                 and keys[column].astype(str).str.strip().any())
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


def main() -> int:
    params = Params()
    wanted = tuple(params.combine.resource)
    parts, streams, roads, years = [], [], {}, None
    per_stream, reasons, per_stream_reasons = {}, {}, {}
    shorten = _shared_prefix([os.path.basename(c) for c in params.combine.cases])

    print(f'Combining : {params.combine.label} across '
          f'{len(params.combine.cases)} case(s)')
    for folder in params.combine.cases:
        if not os.path.isdir(folder):
            raise CombineError(
                f'{folder} is not a folder. `combine.cases` in '
                f'src/params_schema.py names the case folders to add.')
        print(f'  solving {folder} ...', flush=True)
        run = solve_draws(folder, LAYER_NAMES,
                          draws=params.data.draws,
                          seed=params.monte_carlo.seed,
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
        one = account(run, used)
        if one is None:
            print(f'    {used}: no upstream draws for this case -- skipped')
            continue
        stream = os.path.basename(folder)[shorten:].replace('_', ' ') \
            or os.path.basename(folder)
        parts.append(one)
        streams.append(f'{stream} ({used})')
        for road, draws_of in roads_of(run, used, years).items():
            roads[road] = roads.get(road, 0) + draws_of
        # For the second figure: each stream apart, and why it was lost.
        for domain in domains_of(run, used):
            piece = account(run, used, domain=domain)
            if piece is not None:
                per_stream[domain] = piece
                per_stream_reasons[domain] = reasons_of(run, used, domain, years)
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
            f'`combine.resource` in src/params_schema.py lists every spelling '
            f'the metal has -- the wiring case calls it `copper`, the boards '
            f'case calls it `Cu`.')

    figure = figure_combined(added(parts), roads, years, params.figures.theme,
                             params.run.working_unit, params.combine.label,
                             params.combine.whole, streams)
    written = write(figure, params.combine.out_dir,
                    f'{params.combine.label}_combined',
                    params.figures.enabled(), params.figures.dpi)


    with_bev = figure_with_the_bev(per_stream, years, params.figures.theme,
                                   params.run.working_unit,
                                   params.combine.label, params.combine.whole)
    written += write(with_bev, params.combine.out_dir,
                     f'{params.combine.label}_with_the_bev',
                     params.figures.enabled(), params.figures.dpi)

    lost = figure_lost(per_stream, years, params.figures.theme,
                       params.run.working_unit, params.combine.label,
                       params.combine.whole)
    written += write(lost, params.combine.out_dir,
                     f'{params.combine.label}_lost',
                     params.figures.enabled(), params.figures.dpi)

    for path in written:
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
