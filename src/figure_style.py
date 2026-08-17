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


def write(figure, out_dir: str, stem: str, formats, dpi: int) -> list[str]:
    """Write one figure to every requested format. Returns the paths written."""
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for fmt in formats:
        path = os.path.join(out_dir, f'{stem}.{fmt}')
        figure.savefig(path, format=fmt, dpi=dpi,
                       facecolor=figure.get_facecolor(), edgecolor='none')
        written.append(path)
    return written
