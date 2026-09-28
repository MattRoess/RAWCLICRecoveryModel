"""
src/figure_style.py
===================

The rendering settings both plot scripts share: matplotlib configuration, the
two colour schemes, and the writer that turns one figure into every requested
format.

Kept in one place so that a structure diagram and a Sankey of the same case
cannot end up in different palettes or at different resolutions.

THE POINT-PER-UNIT CONVENTION
-----------------------------
Both scripts lay out in typographic points and build their axes so that one
data unit is exactly one point (`canvas()` below). That is what lets font sizes
and line widths be written as plain numbers that mean what they say, and what
makes the same drawing correct at any output resolution -- which is the whole
reason one figure can emit SVG, PNG and PDF.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use('Agg')

# Keep text as text in both vector formats. Matplotlib's default converts every
# glyph to an outline, which makes the SVG an order of magnitude larger and the
# PDF unsearchable. Neither script measures a string -- every position is
# computed -- so a font substitution elsewhere changes glyphs, not layout.
matplotlib.rcParams['svg.fonttype'] = 'none'
matplotlib.rcParams['pdf.fonttype'] = 42

import matplotlib.pyplot as plt  # noqa: E402  (after the backend is fixed)

# Colour-blind-safe qualitative palette, cycled per node.
PALETTE = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2',
           '#B279A2', '#EECA3B', '#9D755D', '#BAB0AC']

MONO = ['DejaVu Sans Mono', 'Menlo', 'monospace']

# A rasterised figure cannot follow prefers-color-scheme the way the old
# hand-written SVG did, so the scheme is chosen when the figure is drawn.
THEMES = {
    'light': dict(bg='#ffffff', title='#111827', sub='#6b7280', node='#111827',
                  edge='#4b5563', meta='#6b7280', tc='#374151',
                  box='#f9fafb', box_line='#d1d5db', arrow='#9ca3af', rule='#e5e7eb'),
    'dark': dict(bg='#0b0f19', title='#f3f4f6', sub='#9ca3af', node='#f3f4f6',
                 edge='#9ca3af', meta='#9ca3af', tc='#d1d5db',
                 box='#111827', box_line='#374151', arrow='#6b7280', rule='#1f2937'),
}


def canvas(width: float, height: float, theme: str):
    """
    A figure whose data coordinates are points, with y increasing downward.

    Returns (figure, axes, colours). The inverted y axis means the layout maths
    in both scripts reads top-down, the way the diagrams are described.
    """
    colours = THEMES[theme]
    figure = plt.figure(figsize=(width / 72, height / 72))
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis('off')
    figure.patch.set_facecolor(colours['bg'])
    return figure, axes, colours


def label(axes, x, y, text, size, colour, weight='normal', ha='left', family=None):
    """
    One line of text. `parse_math=False` because flow and resource names are
    arbitrary strings -- a stray '$' would otherwise be read as mathtext and
    swallow everything up to the next one.
    """
    axes.text(x, y, text, fontsize=size, color=colour, fontweight=weight,
              ha=ha, va='center', parse_math=False,
              **({'fontfamily': family} if family else {}))


def folder_for(out_dir: str, case: str, scenario: str = '') -> str:
    """
    Where one case's figures go: `<out_dir>/<case>/`, or
    `<out_dir>/<case>/<scenario>/` when the run names one.

    A FOLDER PER CASE, NOT A PREFIX. Two cases used to write `mc_pdf_Cu.png`
    into the same directory and the second run replaced the first's silently,
    leaving a figures/ directory holding half of one study and half of another
    with nothing but timestamps to tell them apart. A folder cannot collide, and
    it means the figure names say what the figure IS -- `total.png`,
    `structure.png`, `Cu.png` -- rather than repeating the case in every one.

    AND A FOLDER PER SCENARIO, 2026-09-17, for exactly the same reason. The
    battery is the first case with more than one -- S1, S2, S3 -- and a run is
    one scenario, so three of them wrote the same names to the same place. The
    result would have been the third scenario's figures under the first
    scenario's name, which is the failure above word for word.

    EVERY figure goes under the scenario, including ones that do not depend on
    it such as `structure.png`. One rule and no exceptions beats a rule nobody
    can remember the exceptions to; the cost is an identical drawing written
    three times.
    """
    path = os.path.join(out_dir, os.path.basename(os.path.normpath(case)))
    return os.path.join(path, scenario) if scenario else path


# ⚠️ THE FEW WORTH OPENING FIRST. A traction motor run wrote 512 figures --
# 16 folders of 32 -- and finding the answer in them meant knowing which
# filename to look for. Said on 2026-09-28: *"I want to be able to see what is
# essential and not diluted by hundreds of other figures."*
#
# These six stay in the case's own folder. EVERYTHING ELSE GOES TO `detail/`
# beside them. Nothing stops being drawn: what changes is that the folder you
# open answers the question, and the rest is one directory further in for when
# a number needs chasing.
#
#     over_time      what comes back per year, with its 95% band
#     recovery_rate  the share of what was collected
#     account        the whole account -- in, out, recovered, lost, never collected
#     losses         why it does not come back, and how much of each reason
#     total          the Sankey: where the mass actually went
#     pdf_all        every resource's distribution on one page
#
# A stem not named here is detail, so a new figure lands in `detail/` unless
# somebody decides it belongs in the six.
ESSENTIAL = ('over_time', 'recovery_rate', 'total', 'pdf_all')

# The same, one file per resource: `account_Nd`, `losses_copper`. A grid of six
# was unreadable, so each resource gets its own figure and they all belong at
# the top -- they ARE the answer for the resource they name.
ESSENTIAL_PER_RESOURCE = ('account_', 'losses_', 'fleet_')


def write(figure, out_dir: str, stem: str, formats, dpi: int) -> list[str]:
    """
    Write one figure to every requested format. Returns the paths written.

    The essential six land in `out_dir`; everything else in `out_dir/detail`.
    """
    if stem not in ESSENTIAL and not stem.startswith(ESSENTIAL_PER_RESOURCE):
        out_dir = os.path.join(out_dir, 'detail')
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for fmt in formats:
        path = os.path.join(out_dir, f'{stem}.{fmt}')
        figure.savefig(path, format=fmt, dpi=dpi,
                       facecolor=figure.get_facecolor(), edgecolor='none')
        written.append(path)
    return written


def chart(width: float, height: float, theme: str, rows: int = 1, columns: int = 1,
          height_ratios=None):
    """
    Ordinary axes for a statistical chart, themed to match the diagrams.

    `canvas` above is for the flow diagrams: its coordinates are points and its
    y axis runs downward, which suits a hand-laid-out drawing and suits nothing
    else. A histogram wants real data coordinates and a y axis the right way up.

    Returns (figure, axes, colours). `axes` is a single Axes when one panel is
    asked for, and an array of them otherwise.

    `height_ratios` gives the rows unequal heights, for a figure whose second
    row is a strip under a full panel rather than a second full panel. Left
    alone, every row is the same height, as before.
    """
    colours = THEMES[theme]
    figure, axes = plt.subplots(
        rows, columns, figsize=(width / 72, height / 72),
        gridspec_kw=None if height_ratios is None
        else {'height_ratios': list(height_ratios)})
    figure.patch.set_facecolor(colours['bg'])

    for panel in (axes.ravel() if hasattr(axes, 'ravel') else [axes]):
        panel.set_facecolor(colours['bg'])
        for side in ('top', 'right'):
            panel.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            panel.spines[side].set_color(colours['box_line'])
        panel.tick_params(colors=colours['meta'], labelsize=8)
        panel.grid(True, axis='y', color=colours['rule'], linewidth=0.7, alpha=0.9)
        panel.set_axisbelow(True)

    return figure, axes, colours
