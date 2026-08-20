"""
src/plot_monte_carlo.py
=======================

Figures that show what the Monte Carlo actually did.

A Monte Carlo result is a distribution per row, and a table of medians throws
away the thing that was expensive to compute. These five figures each answer a
different question about the spread, and together they are what "understanding
the effect of the Monte Carlo" means in practice:

  1. `mc_distribution`  -- what does the answer look like, and where does the
     deterministic run sit inside it?
  2. `mc_spread`        -- which flows are uncertain, and by how much?
  3. `mc_mode_vs_mean`  -- how far is running at the mode from the mean, per
     flow? This is the figure that says whether the Monte Carlo changed the
     answer or only added error bars to it.
  4. `mc_convergence`   -- how many draws are actually needed?
  5. `mc_sensitivity`   -- which coefficients drive the spread?

Figure 3 is the one to look at first. A deterministic run sets every
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

from src.figure_style import PALETTE, chart, write

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']


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


def element_rows(run, flow: str, element: str) -> np.ndarray:
    """
    Positions of the rows holding `element` inside `flow`.

    Element-depth rows only. Summing across depths would count the same mass
    several times over, because a deeper row is part of its parent rather than
    an addition to it (MODEL_MECHANICS.md section 1).
    """
    keys = run.keys
    return np.flatnonzero((keys['Stock/Flow ID'] == flow).to_numpy()
                          & (keys['Layer 4'] == element).to_numpy())


def totals_by_flow_and_element(run) -> dict[tuple[str, str], np.ndarray]:
    """{(flow, element): (draws,)} for every terminal flow and element."""
    elements = sorted({e for e in run.keys['Layer 4'].unique() if e})
    out = {}
    for flow in terminal_flows(run):
        for element in elements:
            rows = element_rows(run, flow, element)
            if rows.size:
                out[(flow, element)] = run.values[rows].sum(axis=0)
    return out


def _band(values: np.ndarray) -> tuple[float, float, float, float, float]:
    """Median with the 50% and 90% intervals around it."""
    return tuple(np.percentile(values, [5, 25, 50, 75, 95]))


# ----------------------------------------------------------------------
#  1. What the answer looks like
# ----------------------------------------------------------------------

def figure_distribution(run, deterministic: pd.DataFrame | None, theme: str, unit: str):
    """
    One histogram per element: total recovered mass, across draws.

    The deterministic value and the Monte Carlo mean are drawn on top, because
    the distance between those two lines is the whole point.
    """
    elements = sorted({e for e in run.keys['Layer 4'].unique() if e})
    recovered = [f for f in terminal_flows(run) if 'loss' not in f.lower()]
    if not elements or not recovered:
        return None

    figure, axes, colours = chart(360 * len(elements), 300, theme, 1, len(elements))
    panels = axes if hasattr(axes, '__len__') else [axes]

    for index, (element, panel) in enumerate(zip(elements, panels)):
        totals = np.zeros(run.draws)
        for flow in recovered:
            rows = element_rows(run, flow, element)
            if rows.size:
                totals += run.values[rows].sum(axis=0)

        panel.hist(totals, bins=60, color=PALETTE[index % len(PALETTE)],
                   alpha=0.75, edgecolor='none')

        mean = totals.mean()
        panel.axvline(mean, color=colours['title'], linewidth=1.6,
                      label=f'Monte Carlo mean  {mean:,.1f}')
        if deterministic is not None:
            point = _deterministic_total(deterministic, recovered, element)
            if point is not None:
                panel.axvline(point, color=PALETTE[3], linewidth=1.6, linestyle='--',
                              label=f'deterministic (mode)  {point:,.1f}')

        low, _, median, _, high = _band(totals)
        panel.axvspan(low, high, color=colours['meta'], alpha=0.10,
                      label=f'90% interval  {low:,.1f} to {high:,.1f}')

        panel.set_title(f'{element} recovered', color=colours['title'],
                        fontsize=11, fontweight='bold')
        panel.set_xlabel(f'mass ({unit})', color=colours['meta'], fontsize=9)
        panel.set_ylabel('draws' if index == 0 else '', color=colours['meta'], fontsize=9)
        legend = panel.legend(fontsize=7.5, frameon=False, loc='upper right')
        for text in legend.get_texts():
            text.set_color(colours['meta'])

    figure.suptitle('Where the answer actually lies', color=colours['title'],
                    fontsize=13, fontweight='bold', x=0.01, ha='left')
    figure.tight_layout(rect=[0, 0, 1, 0.94])
    return figure


def _deterministic_total(deterministic: pd.DataFrame, flows: list[str],
                         element: str) -> float | None:
    rows = deterministic[(deterministic['Stock/Flow ID'].isin(flows))
                         & (deterministic['Layer 4'] == element)]
    return float(rows['Value'].sum()) if len(rows) else None


# ----------------------------------------------------------------------
#  2. Which flows are uncertain
# ----------------------------------------------------------------------

def figure_spread(run, theme: str, unit: str):
    """
    Median, 50% and 90% interval for every terminal flow and element.

    Sorted by relative spread, so the least certain answer is at the top --
    which is the one worth arguing about.
    """
    totals = totals_by_flow_and_element(run)
    if not totals:
        return None

    entries = []
    for (flow, element), values in totals.items():
        low, q1, median, q3, high = _band(values)
        relative = (high - low) / median if median > 0 else 0.0
        entries.append((f'{flow}  ·  {element}', low, q1, median, q3, high, relative))
    entries.sort(key=lambda item: item[-1])

    figure, panel, colours = chart(760, 60 + 26 * len(entries), theme)
    for position, (name, low, q1, median, q3, high, relative) in enumerate(entries):
        colour = PALETTE[position % len(PALETTE)]
        panel.plot([low, high], [position, position], color=colour, linewidth=1.4, alpha=0.55)
        panel.plot([q1, q3], [position, position], color=colour, linewidth=7, alpha=0.85,
                   solid_capstyle='butt')
        panel.plot([median], [position], marker='|', markersize=11,
                   color=colours['bg'], markeredgewidth=1.8)
        panel.text(high, position + 0.32, f'  ±{relative * 100:,.0f}%',
                   color=colours['meta'], fontsize=8, va='center')

    panel.set_yticks(range(len(entries)))
    panel.set_yticklabels([entry[0] for entry in entries], fontsize=8.5,
                          color=colours['node'])
    panel.set_xlabel(f'mass ({unit})   —   bar is the 50% interval, line the 90%',
                     color=colours['meta'], fontsize=9)
    panel.set_title('How uncertain each result is', color=colours['title'],
                    fontsize=12, fontweight='bold', loc='left')
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    panel.grid(False, axis='y')
    figure.tight_layout()
    return figure


# ----------------------------------------------------------------------
#  3. The effect of running the Monte Carlo at all
# ----------------------------------------------------------------------

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

    entries = []
    for (flow, element), values in totals.items():
        rows = deterministic[(deterministic['Stock/Flow ID'] == flow)
                             & (deterministic['Layer 4'] == element)]
        if not len(rows):
            continue
        point = float(rows['Value'].sum())
        mean = float(values.mean())
        if mean > 0:
            entries.append((f'{flow}  ·  {element}', 100.0 * (point - mean) / mean,
                            point, mean))
    if not entries:
        return None
    entries.sort(key=lambda item: item[1])

    figure, panel, colours = chart(760, 60 + 26 * len(entries), theme)
    for position, (name, percent, point, mean) in enumerate(entries):
        colour = PALETTE[3] if percent < 0 else PALETTE[2]
        panel.barh(position, percent, height=0.62, color=colour, alpha=0.85)
        offset = 0.4 if percent >= 0 else -0.4
        panel.text(percent + offset, position, f'  {point:,.1f} vs {mean:,.1f} {unit}',
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
    panel.set_title('What the Monte Carlo changes, not just how uncertain it is',
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
    steps = np.unique(np.geomspace(20, run.draws, 60).astype(int))

    running_mean = np.array([values[:n].mean() for n in steps])
    running_low = np.array([np.percentile(values[:n], 5) for n in steps])
    running_high = np.array([np.percentile(values[:n], 95) for n in steps])

    figure, panel, colours = chart(720, 340, theme)
    panel.fill_between(steps, running_low, running_high, color=PALETTE[0], alpha=0.18,
                       label='5th to 95th percentile')
    panel.plot(steps, running_mean, color=PALETTE[0], linewidth=1.8, label='mean')
    for series, style in ((running_low, ':'), (running_high, ':')):
        panel.plot(steps, series, color=PALETTE[0], linewidth=1.0, linestyle=style)

    panel.axhline(values.mean(), color=colours['meta'], linewidth=0.9, linestyle='--')
    panel.set_xscale('log')
    panel.set_xlabel('draws used', color=colours['meta'], fontsize=9)
    panel.set_ylabel(f'{name[0]} · {name[1]}  ({unit})', color=colours['meta'], fontsize=9)
    panel.set_title('How many draws the answer needs', color=colours['title'],
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
    panel.set_title('Which coefficients the answer is sensitive to',
                    color=colours['title'], fontsize=12, fontweight='bold', loc='left')
    panel.grid(True, axis='x', color=colours['rule'], linewidth=0.7)
    panel.grid(False, axis='y')
    figure.tight_layout()
    return figure


# ----------------------------------------------------------------------

def draw_all(run, deterministic: pd.DataFrame | None, out_dir: str, formats,
             dpi: int, theme: str, unit: str = 'Mg') -> list[str]:
    """Draw every Monte Carlo figure. Returns the paths written."""
    import matplotlib.pyplot as plt

    figures = [
        ('mc_distribution', figure_distribution(run, deterministic, theme, unit)),
        ('mc_spread', figure_spread(run, theme, unit)),
        ('mc_mode_vs_mean', figure_mode_vs_mean(run, deterministic, theme, unit)),
        ('mc_convergence', figure_convergence(run, theme, unit)),
        ('mc_sensitivity', figure_sensitivity(run, theme)),
    ]

    written = []
    for stem, figure in figures:
        if figure is None:
            continue
        written.extend(write(figure, out_dir, stem, formats, dpi))
        plt.close(figure)
    return written
