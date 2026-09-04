"""
src/units.py
============

Mass units, and converting between them.

WHY THIS EXISTS
---------------
The model multiplies fractions, so it never looks at the unit. That is exactly
what makes a wrong one dangerous: an inflow in kilotonnes solved as though it
were tonnes gives an answer 1000x out, and nothing about the result looks
unusual -- the ratios are all still right.

Until now the project only *checked* the unit and refused a mismatch, telling
the reader to convert the data by hand. That is a poor arrangement when three
units are genuinely in play at once: the data folders here are written in Mg,
the upstream pipeline delivers kilotonnes, and the results are wanted in kg.
Converting by hand is a step that can be forgotten, and forgetting it is
invisible.

So the inflow is now converted on load, from whatever the file declares to the
unit the project works in (`working_unit` in src/params_schema.py). The file
keeps saying what it is; the setting says what the answer should be in.

WHY ONE UNIT IS AWKWARD, WHICHEVER ONE IT IS
--------------------------------------------
The two ends of this model are five or six orders of magnitude apart. A year's
collected fleet is around 500 kt; the gold recovered from it is a few tonnes.
In kilograms those are 500,000,000 and 3,000 -- one unreadable, one fine. In
kilotonnes they are 500 and 0.003, with the problem the other way round.

There is no single unit that suits both, so the two jobs are separated: one
canonical unit for the arithmetic and the output files, and a display scale
chosen per figure. `scale_for` does the second.
"""
from __future__ import annotations

import numpy as np

# What one of each unit is, in kilograms. Kilograms because it is the SI base
# unit for mass, which makes it the natural hub for a conversion table.
MASS_UNITS = {
    'mg': 1e-6, 'g': 1e-3, 'kg': 1.0,
    't': 1e3, 'tonne': 1e3, 'tonnes': 1e3, 'Mg': 1e3,     # 1 Mg = 1 tonne
    'kt': 1e6, 'Gg': 1e6,                                  # 1 kt = 1 Gg
    'Mt': 1e9, 'Tg': 1e9,
    'Gt': 1e12,
}

# Units that name more than one quantity. 'ton' is 1000 kg in one country and
# 907 or 1016 in others, which is a 10% error that looks like a rounding
# difference rather than a unit mistake. Refused rather than guessed at.
AMBIGUOUS_UNITS = {'ton', 'tons', 'T', 'MT', 'KT'}

# Units offered for reading a figure, coarsest last. Only these are used for
# display; the conversion table above is what the data may declare.
#
# `mg` is on the ladder for the printed numbers, not for axes: the boards case
# recovers germanium in grams and copper in kilotonnes, nine orders apart, and a
# number printed in a legend can carry its own unit where an axis cannot.
DISPLAY_LADDER = ['mg', 'g', 'kg', 't', 'kt', 'Mt']


class UnitError(ValueError):
    """Raised when a unit is unknown, ambiguous, or cannot be converted."""


def factor(from_unit: str, to_unit: str) -> float:
    """
    How much to multiply a value in `from_unit` by to express it in `to_unit`.

    Raises rather than returning 1.0 for an unknown unit: silently treating an
    unrecognised label as "no conversion needed" is the failure this module
    exists to prevent.
    """
    for unit in (from_unit, to_unit):
        if unit in AMBIGUOUS_UNITS:
            raise UnitError(
                f"{unit!r} names more than one quantity depending on where it is "
                f"written, so this project refuses it. Use 't', 'Mg' or 'kt'.")
        if unit not in MASS_UNITS:
            raise UnitError(
                f"{unit!r} is not a mass unit this project recognises. "
                f"Known: {', '.join(sorted(MASS_UNITS))}.")
    return MASS_UNITS[from_unit] / MASS_UNITS[to_unit]


def convert(values, from_unit: str, to_unit: str):
    """Values expressed in `from_unit`, re-expressed in `to_unit`."""
    scale = factor(from_unit, to_unit)
    return values if scale == 1.0 else values * scale


def scale_for(values, unit: str, by: str = 'median') -> tuple[float, str]:
    """
    A readable unit for a set of numbers, and what to multiply them by.

    Picks the coarsest unit on the ladder that still leaves the judged value
    at or above 1, so an axis reads "3.2 t" rather than "3200 kg" or
    "0.0032 kt". Returns (multiplier, unit name).

    `by='median'`, the default, judges on the median of the non-zero values, so
    one large flow does not push every other panel into a unit that makes it
    unreadable. That is right for a figure of many panels, each scaled to
    itself.

    `by='max'` judges on the largest value instead, and is what a figure with
    ONE SHARED AXIS needs. The boards case recovers 5,180 t of copper beside
    370 g of germanium; the median lands in kilograms, and an axis in kilograms
    then runs to five million and gets drawn with a `1e6` stuck in the corner --
    which is matplotlib telling the reader to multiply in their head. Judged on
    the largest, the axis is in kilotonnes and the numbers on it are 0 to 7.
    """
    values = np.asarray(values, dtype=float)
    positive = values[values > 0]
    if positive.size == 0:
        return 1.0, unit

    judged = float(np.max(positive) if by == 'max' else np.median(positive))
    best_scale, best_unit = 1.0, unit
    for candidate in DISPLAY_LADDER:
        scale = factor(unit, candidate)
        if judged * scale >= 1.0:
            best_scale, best_unit = scale, candidate
    return best_scale, best_unit


def readable(value: float, unit: str) -> str:
    """
    One number with ITS OWN unit, never in scientific notation.

    A legend that says `5.51e+04 kg` beside `0.000349 kg` has made the reader
    do the arithmetic that the unit exists to do for them. Each printed number
    gets the unit that puts it in a range a person reads at sight -- `55.1 t`,
    `349 mg` -- which is safe precisely because it is PRINTED: it carries its
    unit with it, unlike a position on a shared axis, which cannot.
    """
    if not np.isfinite(value) or value == 0:
        return f'0 {unit}'
    scale, shown = scale_for([abs(value)], unit)
    size = value * scale
    if abs(size) >= 100:
        return f'{size:,.0f} {shown}'
    return f'{size:,.1f} {shown}' if abs(size) >= 10 else f'{size:,.2f} {shown}'


def convert_inflows(inflows, working_unit: str):
    """
    Re-express an inflow table in the unit the project works in.

    Only the inflow carries a unit. Composition and transfer coefficients are
    fractions, so they are dimensionless and are left alone -- which is also why
    converting the inflow alone is enough to put the whole solution in the new
    unit.

    The 'Unit' column is rewritten to the working unit, so a file that has been
    through here says what its numbers now are rather than what they were.

    Args:
        inflows: the inputs.csv table, with a 'Unit' column
        working_unit: what the project works in

    Returns:
        (converted table, note) where `note` describes the conversion, or None
        when nothing needed converting.
    """
    if 'Unit' not in inflows.columns:
        return inflows, None

    declared = {str(unit).strip() for unit in inflows['Unit'] if str(unit).strip()}
    if len(declared) != 1:
        # Zero or several: not this function's problem. src/validate_inputs.py
        # refuses both, with a message naming the file and the column.
        return inflows, None

    from_unit = declared.pop()
    if from_unit == working_unit:
        return inflows, None

    scale = factor(from_unit, working_unit)
    converted = inflows.copy()
    converted['Value'] = converted['Value'].astype(float) * scale
    converted['Unit'] = working_unit
    return converted, (f'inputs.csv is in {from_unit}; converted to {working_unit} '
                       f'(x{scale:g})')
