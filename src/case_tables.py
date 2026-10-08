"""
src/case_tables.py
==================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

Where a case's three tables live, and how to read them.

WHY A WORKBOOK
--------------
`source`, `processes` and `TCs` describe one case and are edited together, by a
person, by hand. Three separate CSVs make that harder than it needs to be: no
dropdown to stop a flow name being mistyped, no room for a note beside a
number, and three files to keep consistent with each other.

So a case may carry a single `input_data/case.xlsx` with one sheet per table.
The workbook is the input -- there is no export step and no second copy, because
two copies of one table, one generated from the other, is exactly the drift this
project keeps finding.

CSV IS STILL READ
-----------------
A case with `source.csv`, `processes.csv` and `TCs.csv` works unchanged. The
reference fixtures under `data_folder/reference/` are CSV and stay that way:
every test suite runs on them, and converting the thing that proves the code
works would be a poor trade for tidiness.

A case may not have both for the same table. Two files of the same name with
different contents is precisely the situation where someone edits one and the
model reads the other.

EMPTY CELLS
-----------
A CSV read with `keep_default_na=False` gives `''` for a blank. Excel gives
`NaN`. The model reads `''` as "this layer is not populated" -- the whole
nesting rule depends on it -- so blanks are normalised here rather than in
every caller.

VARIANTS
--------
Added 2026-10-08. A case can hold several versions of some of its rows and let
the settings pick one -- so a question with more than one answer is asked by
changing a setting, not by editing a table or keeping a copy of the case.

`TCs` and `TCs_improved` may carry an optional column `variant`. Blank means the
row is always used. Otherwise it names the version(s) the row belongs to:

    tc_set=BAU                         used when tc_set is BAU
    tc_set=own|REC                     used when tc_set is own or REC
    tc_set=REC; sodium_route=mixed     used only when BOTH hold

and `run.variants` in `src/params_schema.py` makes the choices, e.g.
`tc_set=own; sodium_route=mechanical`. Rows that are the same in every version
are written ONCE, with the cell blank: two copies of one number is how a table
drifts apart.

Nothing here knows what a variant is called or what it means. A case that has no
`variant` column reads exactly as it always did.

Reading the raw sheet (`read`) still returns every row, so that a tool which
reads a table, changes it and writes it back cannot lose the versions that are
not selected. The model reads through `active` / `coefficients`, which apply the
choice.
"""
from __future__ import annotations

import contextlib
import functools
import os
import re
import warnings

import numpy as np
import pandas as pd

WORKBOOK = 'case.xlsx'

# Sheet name and CSV name are the same word, so a case reads the same either way.
TABLES = ('source', 'processes', 'TCs', 'TCs_improved')

# The coefficients an improved case ends at. Optional: a case without it does
# not change over time, which is every case built before 2026-09-03.
IMPROVED = 'TCs_improved'


@contextlib.contextmanager
def _quiet_workbook():
    """
    Open a workbook without openpyxl's data-validation warning.

    The case workbooks carry dropdowns on `source` and `processes` (added
    2026-08-26 so the vocabulary is offered rather than remembered). openpyxl
    cannot round-trip the extension those use and says so on EVERY open -- nine
    times in one Monte Carlo run, interleaved with the output that matters.

    Narrow on purpose: this filters that one message from that one library. A
    blanket filter here would also hide the pandas and numpy warnings that have
    twice been the first sign of a real defect in this project.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', category=UserWarning, module='openpyxl',
            message='Data Validation extension is not supported.*')
        yield

# What identifies one coefficient, so the two tables can be lined up row for
# row. Not src.mass_balance.RESOURCE: that leaves out Output_FlowID, because a
# resource is the thing split ACROSS the flows. Here a ROW is being matched.
COEFFICIENT = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
               'Output_FlowID', 'TC_target_layer', 'TC_target_key']

# The three numbers that ramp. Everything else -- process, technology,
# is_residual -- is taken from the current table, because a coefficient that
# changed those would be a different coefficient rather than an improved one.
RAMPED = ['value_min', 'value', 'value_max']


class ImprovementError(ValueError):
    """Raised when a case's two coefficient tables do not describe one case."""


def _weight(year: int, start: int, end: int, after: str = 'hold') -> float:
    """
    How far along the improvement this year sits. 0 at `start`, 1 at `end`.

    FLAT BEFORE `start`, ALWAYS. Nothing improves before the year the case
    says improvement begins, so the weight is 0 there and the current table
    stands. `improvement_start` is the parameter that sets it, per case, in the
    source table.

    AFTER `end`, TWO ANSWERS, and the case picks:

        hold      the weight stops at 1 -- the improved table applies from
                  `end` onwards, unchanged
        continue  the weight keeps rising at the same rate, so 2070 is a third
                  of a ramp beyond a 2030-2060 window and the line does not go
                  flat at a year chosen for having a table

    ⚠️ `continue` EXTRAPOLATES, so a coefficient can in principle leave [0, 1]
    far enough out. Nothing here clamps it, on purpose: stage 01 checks every
    year the run will solve for `0 <= min <= mode <= max <= 1` and names the
    row that breaks it. A clamp would quietly bend one coefficient and leave
    its group summing to something other than 1, which is worse than being
    told the window is too short for the horizon.

    Sum-to-1 survives either way. Each year is `a + (b - a) * w`, and summing
    that over a group gives `1 + (1 - 1) * w = 1` for ANY weight -- the
    property does not need w to be between 0 and 1.
    """
    if year <= start:
        return 0.0
    if year >= end and after != 'continue':
        return 1.0
    return (year - start) / (end - start)


def ramp(current, improved, start: int, end: int, years,
         after: str = 'hold', roles: dict | None = None) -> "pd.DataFrame":
    """
    One coefficient table per year, on a straight line from current to improved.

    Before `start` the current numbers hold; between `start` and `end` each of
    value_min, value and value_max moves linearly; after `end` the case's
    `improvement_after_end` decides whether the improved numbers hold or the
    same rate of change carries on. See `_weight`. The result
    carries a `Year` column, which is all the rest of the model needs: both
    engines already select their rows by year
    (`select_df_by_year_scenario_location`), so nothing downstream changes.

    ONE DRAW STAYS ONE WORLD. A coefficient's random stream is keyed on which
    resource moves from where to where and NOT on the year
    (`src/sampling._stream_key`), so every year of one coefficient draws the
    same uniform. Draw 7 is therefore the same optimism about that process in
    2030 and in 2060, ramped -- not two unrelated guesses. Independent draws per
    year would invent a year-to-year wobble nobody measured.

    SUM-TO-1 SURVIVES BY CONSTRUCTION. Each year is `a + (b - a) * w` over two
    tables whose groups each sum to 1, and that sums to `1 + (1 - 1) * w = 1`
    whatever the weight -- so it holds for `continue` past the end of the
    window as well as inside it. Nothing has to be renormalised, and the groups
    are formed within a year, never across them.
    """
    missing = [column for column in COEFFICIENT if column not in current.columns]
    if missing:
        raise ImprovementError(f'the coefficient table has no {missing} column(s).')

    current = current.reset_index(drop=True)
    improved = improved.reset_index(drop=True)

    left = current[COEFFICIENT].astype(str).agg('|'.join, axis=1)
    right = improved[COEFFICIENT].astype(str).agg('|'.join, axis=1)
    only_current = sorted(set(left) - set(right))
    only_improved = sorted(set(right) - set(left))
    if only_current or only_improved:
        raise ImprovementError(
            f'{IMPROVED} must name exactly the coefficients {TABLES[2]} names.\n'
            + (f'  missing from {IMPROVED}: {len(only_current)}, first '
               f'{only_current[0]}\n' if only_current else '')
            + (f'  not in {TABLES[2]}: {len(only_improved)}, first '
               f'{only_improved[0]}\n' if only_improved else '')
            + '  Every coefficient appears in both, so that one edited in one\n'
              '  and not the other cannot become an unintended improvement.')

    for name, keys in ((TABLES[2], left), (IMPROVED, right)):
        repeated = keys[keys.duplicated()].unique()
        if len(repeated):
            raise ImprovementError(
                f'{name} names the same coefficient more than once, so the two '
                f'tables cannot be lined up row for row: {repeated[0]}')

    # Line the improved rows up with the current ones by identity, not by
    # position: the two sheets are edited by hand and a row moved in one of
    # them would otherwise ramp a coefficient towards a different coefficient.
    improved = improved.set_index(right).loc[left].reset_index(drop=True)

    numbers = {column: (pd.to_numeric(current[column], errors='coerce'),
                        pd.to_numeric(improved[column], errors='coerce'))
               for column in RAMPED
               if column in current.columns and column in improved.columns}
    group = (current[[c for c in GROUP if c in current.columns]]
             .astype(str).agg('|'.join, axis=1)
             if any(c in current.columns for c in GROUP) else None)

    blocks, held = [], {}
    for year in years:
        block = current.copy()
        weight = _weight(int(year), start, end, after)
        for column, (a, b) in numbers.items():
            # A SIMPLE LINEAR EXTRAPOLATION. Nothing caps the weight.
            mixed = a + (b - a) * weight
            # A blank bound is a definitional row with no range. Blank in either
            # table stays blank rather than becoming a number out of nowhere.
            block[column] = mixed.where(a.notna() & b.notna(), current[column])
        if weight > 1:
            block, capped = _hold_at_the_bounds(block, group, numbers, roles)
            if capped:
                held[int(year)] = capped
            # ⚠️ AND THE FLOAT DUST IS SWEPT UP. The steps above are each exact
            # in their own terms and the arithmetic between them is not: the
            # battery's loss row takes a shortfall of `1 - 0.99`, which is
            # 0.010000000000000009, and lands 4e-17 above a maximum of 0.01.
            # `numeric_bounds` round-trips the bounds through strings on the
            # way to the checker and the dust survives in one column and not
            # the other, so the row is rejected for being 0.000000000000000044
            # out of range.
            #
            # Twelve decimals keeps every digit any of these coefficients
            # means -- the builders round to six -- and leaves nothing for the
            # exact comparison in stage 01 to trip over.
            for column in RAMPED:
                if column in block.columns:
                    numeric = pd.to_numeric(block[column], errors='coerce')
                    block[column] = numeric.round(12).where(numeric.notna(),
                                                            block[column])
        # ⚠️ ZERO-WIDTH ROWS ARE LEFT ALONE, AND AN ATTEMPT TO WIDEN THEM IS
        # WHY THIS NOTE EXISTS. A row with min == mode == max looked like the
        # cause of "a constrained group has no draw with any weight at all",
        # so every such row was given 1e-6 of space. It is not the cause:
        # `sampling.condition` counts rows with spread > 0, skips a group where
        # none has one, and never weights a point mass -- so a point mass
        # cannot zero a group.
        #
        # Widening them broke something else instead. A constrained group of a
        # single row had spread 0 and was skipped; with 1e-6 it became "one row
        # with a range and the rest fixed", which the sampler refuses outright,
        # and all six cases stopped. The real fault was one row whose MODE had
        # caught its MAX -- see `_hold_at_the_bounds`.

        block['Year'] = str(year)
        blocks.append(block)
    if held:
        first = min(held)
        names = sorted({n for rows in held.values() for n in rows})
        print(f'  improvement extrapolated past {end}; '
              f'{len(names)} coefficient(s) reached 0 or 1 and were held '
              f'there from {first}; any group then summing above 1 was '
              f'set back to 1:')
        for name in names[:6]:
            print(f'    {name}')
        if len(names) > 6:
            print(f'    ... and {len(names) - 6} more')
    return pd.concat(blocks, ignore_index=True)


# The columns that make one sum-to-1 group: every coefficient moving the same
# resource out of the same flow.
#
# ⚠️ ALL FIVE, AND IT WAS THREE. This is `src/mass_balance.RESOURCE`, which is
# what the sampler groups on and what stage 01 totals -- copied here rather
# than imported because mass_balance imports this module, and asserted against
# it below so the copy cannot drift.
#
# With `Input_layer` and `Input_layer_key` missing, two real groups that differ
# only by which input they are keyed at were read as one: on the wiring case
# `F_disassembled -> copper` merged the Wiring rows with the Motors rows and
# totalled 2.0000 before any extrapolation, and on the battery `F_cells ->
# rest` totalled 7.0000. `_hold_at_the_bounds` then saw a group "above 1" and
# divided it -- by two, and by seven. Caught on 2026-09-29 by checking whether
# `continue` was safe for those cases, not by any test.
GROUP = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
         'TC_target_layer', 'TC_target_key']

# What a coefficient extrapolated onto zero is given instead, so it stays a
# distribution rather than a point mass. See `_hold_at_the_bounds`.
FLOOR = 1e-6


def _hold_at_the_bounds(block, group, numbers, roles=None):
    """
    Past the window, a share that would leave [0, 1] is held at the bound.

    ⚠️ THE RULE, SET BY MATTHIAS ON 2026-09-29: *"if it is larger 1 then set it
    to 1 and document."* The same at the other end -- a share that would go
    negative is held at 0. A transfer coefficient is a share of what enters a
    flow; there is no such thing as 119% of it, or -3%.

    AND A GROUP THAT WOULD SUM ABOVE 1 IS SET TO 1. *"If it is larger than 1
    then set it to 1 and document."* A group of transfer coefficients is the
    whole of what leaves a flow, so its sum IS 1 -- 1.0267 of the magnet is not
    a pessimistic number, it is more magnet than there is.

    The group is divided by its own sum, and only when that sum is above 1.
    A group still summing to 1 or below is left exactly as the extrapolation
    put it; nothing is scaled up to reach 1.

    Returns the block and the names of the coefficients that were held, so the
    run can say so out loud rather than doing it silently.
    """
    columns = [c for c in ('value_min', 'value', 'value_max') if c in block.columns]
    del group                     # regrouped here, on the full key -- see GROUP
    group = (block[[c for c in GROUP if c in block.columns]]
             .astype(str).agg('|'.join, axis=1)
             if all(c in block.columns for c in GROUP) else None)
    if not columns:
        return block, []

    before = {c: pd.to_numeric(block[c], errors='coerce') for c in columns}
    after_clip = {c: v.clip(lower=0.0, upper=1.0) for c, v in before.items()}
    moved = np.zeros(len(block), dtype=bool)
    for c in columns:
        moved |= (before[c] - after_clip[c]).abs().gt(1e-12).fillna(False).to_numpy()

    for c in columns:
        block[c] = after_clip[c].where(before[c].notna(), block[c])

    # ⚠️ A COEFFICIENT EXTRAPOLATED TO NOTHING KEEPS A TRACE OF ITSELF.
    #
    # Both tables narrow as they improve, so past the window the three bounds
    # of a falling coefficient converge and then cross: the battery's
    # `F_cells -> F_loss_cell` for nickel is 0.018 wide in 2060, 0.006 in 2065
    # and lands on min = mode = max = 0 in 2070. Zero on all three is not a
    # small number, it is a point mass at nothing -- the draws for that
    # coefficient stop varying, and this is a Monte Carlo. Said on 2026-09-30:
    # *"keep in mind we run here Monte Carlo and deal with uncertainties"*,
    # and then: *"in these cases you can fake a 0 with 0.000001 for mode and
    # max."*
    #
    # So mode and max are floored at 1e-6 where the extrapolation flattened
    # them onto zero. The minimum stays at 0, which is true -- the coefficient
    # may be nothing.
    #
    # IT GOES IN BEFORE THE GROUP IS BALANCED, deliberately. 1e-6 is a
    # thousand times the closure tolerance (1e-9), so a floor applied after
    # balancing would break the sum it had just fixed. Applied here, the steps
    # below take it into account and the group still closes exactly.
    #
    # ⚠️ AND ONLY WHERE THE ZERO WAS MADE BY EXTRAPOLATING. Twelve of the
    # battery's coefficients are 0.0 in BOTH sheets -- the support frame
    # contributes nothing to the cells, and the study says so exactly. Floored
    # without this condition they read 0 from 2020 to 2060 and 1e-6 at 2065 and
    # 2070: mass invented, in the years nobody looks at, for a flow the study
    # states is empty. A coefficient that was always zero stays zero.
    if {'value', 'value_max'} <= set(columns):
        mode = pd.to_numeric(block['value'], errors='coerce')
        high = pd.to_numeric(block['value_max'], errors='coerce')
        source_a, source_b = numbers['value']
        real = source_a.fillna(0).abs().gt(0) | source_b.fillna(0).abs().gt(0)
        flat = mode.le(0.0) & high.le(0.0) & real
        if flat.any():
            moved |= flat.fillna(False).to_numpy()
            block['value'] = mode.mask(flat, FLOOR).where(mode.notna(),
                                                          block['value'])
            block['value_max'] = high.mask(flat, FLOOR).where(high.notna(),
                                                              block['value_max'])

    # ⚠️ AND THE MODE IS HELD INSIDE ITS OWN RANGE. Extrapolating moves
    # value_min, value and value_max at three different rates, so the mode can
    # cross a bound that has stopped moving or is falling faster than it. The
    # battery's cathode nickel is the plain case: the review caps it at 0.99
    # and the mode reaches 0.99 by 2060, so one step further puts the mode at
    # 0.9967 ABOVE its own maximum. On the boards case the maximum falls
    # fastest and the mode passes it going down.
    #
    # Same rule as the one above, on the bound that binds: *"set it to the
    # bound."* The mode is clipped into [value_min, value_max], and the two
    # bounds are ordered first so the interval it is clipped into is never
    # inside out.
    if {'value_min', 'value', 'value_max'} <= set(columns):
        low = pd.to_numeric(block['value_min'], errors='coerce')
        high = pd.to_numeric(block['value_max'], errors='coerce')
        ordered_low, ordered_high = np.minimum(low, high), np.maximum(low, high)
        mode = pd.to_numeric(block['value'], errors='coerce')
        held = mode.clip(lower=ordered_low, upper=ordered_high)
        moved |= (mode - held).abs().gt(1e-12).fillna(False).to_numpy()
        block['value'] = held.where(mode.notna(), block['value'])
        block['value_min'] = ordered_low.where(low.notna(), block['value_min'])
        block['value_max'] = ordered_high.where(high.notna(), block['value_max'])

    # ⚠️ A MODE THAT HAS CAUGHT ITS OWN MAXIMUM IS GIVEN ROOM TO 1.
    #
    # Past the window a rising coefficient reaches the ceiling the study wrote
    # for it and stops: the battery's cathode nickel is min 0.97, mode 0.99,
    # max 0.99 at 2065. That row is then the widest in its group, so the
    # sampler makes it the derived one and forces it to take `1 - the others`
    # -- which, with the others down at 1e-6, is 0.990001 to 0.999181. Every
    # one of those is above its maximum of 0.99, so every draw gets density
    # zero and the run stops with "a constrained group has no draw with any
    # weight at all".
    #
    # Said on 2026-09-30: *"If you are close to min == mode == max after 2060
    # then keep the min and have mode and max == 1."* The minimum stays where
    # the study put it, so the row keeps its spread downwards and its shape;
    # what changes is that the top of the triangle reaches 1, which is where
    # the extrapolated trend was heading anyway.
    #
    # ONLY PAST THE WINDOW, and only where the mode has actually met the
    # maximum -- inside the window the study's own ceiling stands.
    if {'value_min', 'value', 'value_max'} <= set(columns):
        mode = pd.to_numeric(block['value'], errors='coerce')
        high = pd.to_numeric(block['value_max'], errors='coerce')
        caught = mode.notna() & high.notna() & (high - mode).abs().le(1e-12) \
            & mode.gt(0.5)
        if caught.any():
            moved |= caught.fillna(False).to_numpy()
            block['value'] = mode.mask(caught, 1.0).where(mode.notna(),
                                                          block['value'])
            block['value_max'] = high.mask(caught, 1.0).where(high.notna(),
                                                              block['value_max'])

    # Set a group that now sums above 1 back to 1.
    if group is not None and 'value' in columns:
        mode = pd.to_numeric(block['value'], errors='coerce')
        total = mode.groupby(group).transform('sum')
        over = total.gt(1.0 + 1e-12)
        block['value'] = (mode / total).where(over & mode.notna(), block['value'])
        moved |= over.fillna(False).to_numpy()

    # ⚠️ AND A GROUP THAT NOW SUMS BELOW 1 GIVES THE SHORTFALL TO ITS LOSS
    # FLOW. Holding a coefficient at a bound takes mass out of its group, and
    # a group summing to 0.99 is a group destroying 1% of what enters it --
    # which stage 01 refuses, rightly.
    #
    # The battery is the plain case. `F_cells cathodeActiveMaterial -> Ni`
    # recovers 0.99 and loses the rest; the review caps recovery at 0.99 and
    # the mode reaches it by 2060, so past that the recovered coefficient is
    # held at 0.99 and the loss row, falling, is clipped to 0. The group then
    # sums to 0.99 and 1% of the nickel exists in 2065 and not in 2070.
    #
    # It goes to the LOSS flow because that is what the missing mass IS: what
    # is not recovered is lost. Not spread across the group -- that would move
    # recovered coefficients nobody clipped, to hide the clipping. Decided on
    # 2026-09-30: *"put the shortfall on the loss flow."*
    #
    # Several loss flows in one group share it equally. A group with NO loss
    # flow keeps its shortfall and stage 01 reports it: there is nowhere
    # honest to put it, and inventing a home would be the silent kind of wrong.
    if group is not None and roles and 'Output_FlowID' in block.columns:
        mode = pd.to_numeric(block['value'], errors='coerce')
        total = mode.groupby(group).transform('sum')
        short = (1.0 - total).where(total.lt(1.0 - 1e-12), 0.0)
        loss = block['Output_FlowID'].astype(str).map(
            lambda flow: roles.get(flow) == 'loss')
        per_group = loss.astype(float).groupby(group).transform('sum')
        share = (short / per_group).where(loss & per_group.gt(0), 0.0)
        if share.abs().gt(1e-12).any():
            raised = (mode + share).clip(lower=0.0, upper=1.0)
            moved |= (raised - mode).abs().gt(1e-12).fillna(False).to_numpy()
            block['value'] = raised.where(mode.notna(), block['value'])
            # The bound follows the value it now has to contain, rather than
            # the value being pushed back under a bound and the mass lost
            # again.
            if 'value_max' in block.columns:
                high = pd.to_numeric(block['value_max'], errors='coerce')
                block['value_max'] = np.maximum(high, raised).where(
                    high.notna(), block['value_max'])

    # ⚠️ THE INVARIANT IS ASSERTED ONCE, AT THE END. Each step above preserves
    # `min <= mode <= max` on its own, and between them floating point does
    # not: the battery's loss row takes a shortfall of `1 - 0.99`, which is
    # 0.010000000000000009, and lands 4e-17 above a maximum of 0.01. Stage 01
    # compares exactly and is right to -- but the fault is arithmetic noise,
    # not a coefficient out of range.
    #
    # So rather than each step defending the invariant against the next, the
    # bounds are widened to whatever the mode actually is, last. It moves a
    # bound by less than 1e-16 in the float case and is exact in every other.
    if {'value_min', 'value', 'value_max'} <= set(columns):
        mode = pd.to_numeric(block['value'], errors='coerce')
        low = pd.to_numeric(block['value_min'], errors='coerce')
        high = pd.to_numeric(block['value_max'], errors='coerce')
        block['value_min'] = np.minimum(low, mode).where(
            low.notna() & mode.notna(), block['value_min'])
        block['value_max'] = np.maximum(high, mode).where(
            high.notna() & mode.notna(), block['value_max'])

    names = []
    if moved.any():
        have = [c for c in ('Input_FlowID', 'Output_FlowID', 'TC_target_key')
                if c in block.columns]
        if have:
            names = sorted(block.loc[moved, have].astype(str)
                           .agg(' -> '.join, axis=1).unique())
    return block, names


# ----------------------------------------------------------------------
# Variants: one table holding several versions of some of its rows
# ----------------------------------------------------------------------

VARIANT = 'variant'
_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class VariantError(ValueError):
    """Raised when what a case offers and what the settings choose do not fit."""


def parse_selection(text) -> dict[str, str]:
    """
    `run.variants` as a dict: 'tc_set=own; sodium_route=mechanical' ->
    {'tc_set': 'own', 'sodium_route': 'mechanical'}. Blank is no choices.

    Semicolon-separated, like `data_folder` and a case's `groups`.
    """
    selection: dict[str, str] = {}
    for part in str(text or '').split(';'):
        part = part.strip()
        if not part:
            continue
        name, equals, choice = part.partition('=')
        name, choice = name.strip(), choice.strip()
        if (not equals or not _NAME.match(name) or not choice
                or any(mark in choice for mark in '|;=')):
            raise VariantError(
                f"run.variants contains {part!r}, which does not read "
                f"<name>=<choice>, for example 'tc_set=own'. Several are "
                f"separated by semicolons.")
        if name in selection:
            raise VariantError(
                f"run.variants chooses {name!r} twice "
                f"({selection[name]!r} and {choice!r}). Only one can apply.")
        selection[name] = choice
    return selection


def parse_tag(cell) -> dict[str, frozenset]:
    """
    One `variant` cell as {name: the choices it is used for}. Blank is {}.

    'tc_set=own|REC; sodium_route=mixed' ->
    {'tc_set': {'own', 'REC'}, 'sodium_route': {'mixed'}}
    """
    text = '' if cell is None or (isinstance(cell, float) and pd.isna(cell)) \
        else str(cell).strip()
    tag: dict[str, frozenset] = {}
    for clause in text.split(';'):
        clause = clause.strip()
        if not clause:
            continue
        name, equals, options = clause.partition('=')
        name = name.strip()
        choices = frozenset(c.strip() for c in options.split('|') if c.strip())
        if not equals or not _NAME.match(name) or not choices:
            raise VariantError(
                f"{clause!r} does not read <name>=<choice>[|<choice>], for "
                f"example 'tc_set=REC' or 'tc_set=own|REC'.")
        if name in tag:
            raise VariantError(f"{name!r} appears twice in {text!r}.")
        tag[name] = choices
    return tag


def _tags(frame: pd.DataFrame, sheet: str):
    """The parsed tag of every row, or None when the sheet has no such column."""
    if VARIANT not in frame.columns:
        return None
    parsed: dict[str, dict] = {}
    out = []
    for position, cell in enumerate(frame[VARIANT]):
        key = '' if cell is None else str(cell)
        if key not in parsed:
            try:
                parsed[key] = parse_tag(cell)
            except VariantError as error:
                raise VariantError(
                    f"{sheet}, row {position + 2}, column '{VARIANT}': "
                    f"{error}") from None
        out.append(parsed[key])
    return out


def offered(frame: pd.DataFrame, sheet: str = 'TCs') -> dict[str, set[str]]:
    """What one sheet lets be chosen: {name: every choice any row mentions}."""
    found: dict[str, set[str]] = {}
    for tag in _tags(frame, sheet) or ():
        for name, choices in tag.items():
            found.setdefault(name, set()).update(choices)
    return found


def select(frame: pd.DataFrame, selection: dict[str, str],
           sheet: str = 'TCs') -> pd.DataFrame:
    """
    The rows that apply under `selection`, with the `variant` column removed.

    A row applies when it carries no tag, or when, for every name in its tag,
    the selection chose one of the choices the tag lists. The column is dropped
    so that nothing downstream -- which has never heard of it -- sees it.
    """
    tags = _tags(frame, sheet)
    if tags is None:
        return frame
    keep = []
    for tag in tags:
        for name in tag:
            if name not in selection:
                raise VariantError(
                    f"{sheet} has rows for a choice called {name!r} and the "
                    f"selection {selection or '{}'} does not make it.")
        keep.append(all(selection[name] in choices for name, choices in tag.items()))
    return frame.loc[keep].drop(columns=[VARIANT]).reset_index(drop=True)


def _stamp(case: str) -> tuple:
    """When the files holding a case's coefficient tables last changed."""
    stamp = []
    for table in ('TCs', IMPROVED):
        found = where(case, table)
        stamp.append((found[1], os.path.getmtime(found[1])) if found else None)
    return tuple(stamp)


@functools.lru_cache(maxsize=64)
def _offers(case: str, stamp: tuple) -> dict:
    del stamp                      # only here so a changed file is a new key
    found: dict[str, set[str]] = {}
    for table in ('TCs', IMPROVED):
        if not exists(case, table):
            continue
        for name, choices in offered(read(case, table), table).items():
            found.setdefault(name, set()).update(choices)
    return found


def offers(case: str) -> dict[str, set[str]]:
    """
    Everything a case lets be chosen, from both coefficient sheets:
    {name: choices}, names in the order they first appear in `TCs`.
    """
    return {name: set(choices) for name, choices in
            _offers(case, _stamp(case)).items()}


def chosen(case: str, params=None) -> dict[str, str]:
    """
    The choices that apply to THIS case: one for each variant it offers.

    ⚠️ A MISSING OR UNKNOWN CHOICE IS REFUSED, NEVER DEFAULTED. If a case offers
    `tc_set` and the settings say nothing about it, quietly using the first
    version would give an answer that looks like any other and means something
    nobody asked for. The message names what the case offers.

    A choice for a variant this case does not offer is ignored here: one setting
    serves a whole study, and a study holds cases that offer different things.
    """
    if params is None:
        from src.params_schema import current as settings
        params = settings()
    selection = parse_selection(params.run.variants)

    problems = []
    result: dict[str, str] = {}
    for name, choices in offers(case).items():
        listed = ' | '.join(sorted(choices))
        if name not in selection:
            problems.append(
                f"{case} offers a choice called {name!r} ({listed}) and "
                f"run.variants does not make it. Add '{name}=<one of them>'.")
        elif selection[name] not in choices:
            problems.append(
                f"run.variants chooses {name}={selection[name]!r}, but {case} "
                f"offers {listed}.")
        else:
            result[name] = selection[name]
    if problems:
        raise VariantError('\n'.join(problems)
                           + '\nrun.variants is in src/params_schema.py.')
    return result


def active(case: str, table: str, params=None,
           selection: dict[str, str] | None = None) -> pd.DataFrame:
    """
    One of a case's tables as the model should use it: the rows that apply.

    For a table with no `variant` column this IS `read`. `selection` overrides
    the settings, which is how every choice can be checked and not only the one
    that is made.
    """
    frame = read(case, table)
    if VARIANT not in frame.columns:
        return frame
    return select(frame, chosen(case, params) if selection is None else selection,
                  table)


def label(case: str, params=None) -> str:
    """
    A folder name for the choices made on this case: 'REC', 'own_mechanical'.
    Blank for a case that offers none, so every existing case keeps its paths.

    ⚠️ RESULTS OF DIFFERENT CHOICES MUST NOT LAND IN THE SAME FOLDER. A REC run
    written over an `own` run is the failure `figure_style.folder_for` describes
    for scenarios, word for word. The order is the one `run.variants` is written
    in, so the folder reads the way the setting does.
    """
    if not offers(case):
        return ''
    if params is None:
        from src.params_schema import current as settings
        params = settings()
    made = chosen(case, params)
    return '_'.join(made[name] for name in parse_selection(params.run.variants) if name in made)


def label_for(cases, params=None) -> str:
    """
    One folder name for the choices made across SEVERAL cases, each choice once.

    For the combined figures, which belong to no one case but still answer
    differently for each choice. The setting is shared, so a name that two cases
    offer has one choice and appears once.
    """
    if params is None:
        from src.params_schema import current as settings
        params = settings()
    made: dict[str, str] = {}
    for case in cases:
        if offers(case):
            for name, choice in chosen(case, params).items():
                made.setdefault(name, choice)
    return '_'.join(made[name] for name in parse_selection(params.run.variants) if name in made)


def alternatives(case: str, params=None) -> list[tuple[str, dict[str, str]]]:
    """
    Every OTHER choice, one name at a time: [('tc_set=BAU', {...}), ...].

    The rest of the choices stay as they are. Checking every combination would
    multiply, and the questions a check asks -- does it close, does anything
    strand -- are about one version of one thing at a time.
    """
    base = chosen(case, params)
    found = []
    for name, choices in offers(case).items():
        for choice in sorted(choices - {base[name]}):
            other = dict(base)
            other[name] = choice
            found.append((f'{name}={choice}', other))
    return found


def coefficients(case: str, years, params=None,
                 selection: dict[str, str] | None = None) -> "pd.DataFrame":
    """
    The coefficient table this run should use: the rows the variants select,
    ramped if the case improves.

    A case with no TCs_improved sheet and no window gets exactly what it always
    got, unchanged and with no Year column.
    """
    from src import source as source_module

    if params is None:
        from src.params_schema import current as settings
        params = settings()
    # The choice is applied FIRST, to both sheets, so the ramp sees two tables
    # that name the same coefficients -- it matches them by identity and would
    # find the same coefficient twice, once per version.
    if selection is None:
        selection = chosen(case, params)
    current = select(read(case, 'TCs'), selection, 'TCs')
    has_improved = exists(case, IMPROVED)
    described = source_module.read(case, params)
    start, end = described.get('improvement_start'), described.get('improvement_end')

    if not has_improved and start is None:
        return current
    if has_improved and start is None:
        raise ImprovementError(
            f'{case} has a {IMPROVED} table but no improvement_start and '
            f'improvement_end in its source table, so nothing says WHEN it '
            f'improves.')
    if start is not None and not has_improved:
        raise ImprovementError(
            f'{case} sets improvement_start {start} and improvement_end {end} '
            f'but has no {IMPROVED} table, so nothing says WHAT improves.')

    from src.rest import flow_roles          # imported here: rest imports this
    return ramp(current, select(read(case, IMPROVED), selection, IMPROVED),
                start, end, years,
                described.get('improvement_after_end') or 'hold',
                roles=flow_roles(case))


CSV_OPTIONS = dict(keep_default_na=False, na_values=[])


class CaseTableError(ValueError):
    """Raised when a case's tables cannot be located, or are offered twice."""


def workbook_path(case: str) -> str:
    return os.path.join(case, 'input_data', WORKBOOK)


def csv_path(case: str, table: str) -> str:
    return os.path.join(case, 'input_data', f'{table}.csv')



def _sheet_names(path: str) -> list[str]:
    from openpyxl import load_workbook
    with _quiet_workbook():
        book = load_workbook(path, read_only=True)
    try:
        return list(book.sheetnames)
    finally:
        book.close()


def where(case: str, table: str) -> tuple[str, str] | None:
    """
    ('xlsx', path) or ('csv', path) for one table, or None if it has neither.

    Raises when both exist: that is not a preference to resolve silently.
    """
    if table not in TABLES:
        raise CaseTableError(f'{table!r} is not one of {", ".join(TABLES)}')

    book, delimited = workbook_path(case), csv_path(case, table)
    in_book = os.path.exists(book) and table in _sheet_names(book)
    in_csv = os.path.exists(delimited)

    if in_book and in_csv:
        raise CaseTableError(
            f"{case} holds {table} twice: sheet '{table}' in {WORKBOOK}, and "
            f"{table}.csv beside it. Keep one -- otherwise the model reads a "
            f"table that may not be the one being edited.")

    if in_book:
        return ('xlsx', book)
    if in_csv:
        return ('csv', delimited)
    return None


def exists(case: str, table: str) -> bool:
    return where(case, table) is not None


def read(case: str, table: str, dtype=None) -> pd.DataFrame:
    """One of a case's tables, from whichever format it is kept in."""
    found = where(case, table)
    if found is None:
        raise CaseTableError(
            f'{case} has no {table}: expected sheet {table!r} in '
            f'{workbook_path(case)}, or {csv_path(case, table)}.')

    kind, path = found
    if kind == 'csv':
        return pd.read_csv(path, dtype=dtype, **CSV_OPTIONS)

    with _quiet_workbook():
        frame = pd.read_excel(path, sheet_name=table, dtype=dtype)
    return normalise(frame)


def _as_text(value) -> str:
    """One cell as the CSV reader would have produced it."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    if isinstance(value, bool):
        return '1' if value else ''
    if isinstance(value, float) and value.is_integer():
        # Excel stores every number as a float, so a column of 1s arrives as
        # 1.0. Written back out as '1.0' it stops matching the '1' that
        # is_residual is tested against, and residual rows go unrecognised.
        return str(int(value))
    return str(value).strip()


def normalise(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Make a sheet read like the CSV it replaces.

    The CSV reader runs with `keep_default_na=False`, so a column holding any
    blank comes back as strings -- '' and '1' -- while a fully populated
    numeric column comes back numeric. Excel has no empty string: a blank is
    NaN, which makes the whole column float64, and '1' becomes 1.0.

    That difference is not cosmetic. `is_residual` is tested with
    `str(value).strip() in ('1', 'True', 'true')`; against 1.0 that is '1.0',
    which matches nothing, and the Monte Carlo then refuses a group whose
    residual rows it can no longer identify. So columns containing a blank are
    converted to text here, and fully numeric columns are left numeric --
    exactly what reading the CSV produced.
    """
    frame = frame.copy()
    # A wholly empty trailing row is what Excel leaves behind after a delete.
    frame = frame.dropna(how='all')

    for column in frame.columns:
        has_blank = frame[column].isna().any()
        if frame[column].dtype == object or has_blank:
            frame[column] = frame[column].map(_as_text)

    return frame.reset_index(drop=True)


def describe(case: str) -> str:
    """Which file backs each table, for a run to report."""
    parts = []
    for table in TABLES:
        found = where(case, table)
        parts.append(f'{table}={found[0] if found else "missing"}')
    return ', '.join(parts)


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

# Allowed values live on their own hidden sheet and the dropdowns point at
# ranges on it. An inline list -- formula1='"a,b,c"' -- is capped at 255
# characters, which a real element list passes without warning: Excel then
# drops the validation silently and the dropdown simply is not there.
LISTS_SHEET = '_lists'

# Row 1 of every sheet is column names, not data. Freezing it keeps it on
# screen; colouring it is what makes it read as a heading on the first look,
# before anyone has scrolled far enough for the freeze to show.
HEADER_FILL = 'D9E1F2'



def style_header(sheet) -> None:
    """Bold on a fill across row 1, so the column names look like column names."""
    from openpyxl.styles import Font, PatternFill

    fill = PatternFill('solid', start_color=HEADER_FILL, end_color=HEADER_FILL)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = fill


def write_sheet(case: str, table: str, frame: pd.DataFrame, *,
                dropdowns: dict[str, list[str]] | None = None,
                widths: dict[str, int] | None = None) -> str:
    """
    Replace one sheet of a case's workbook, leaving the others alone.

    Written to a temp file beside the target and renamed, for the reason in
    tools/make_skeleton.py: a half-written table looks like a smaller table,
    and this one is read back and merged.
    """
    import tempfile

    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    path = workbook_path(case)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        with _quiet_workbook():
            book = load_workbook(path)
        position = book.sheetnames.index(table) if table in book.sheetnames else None
        if position is not None:
            del book[table]
        sheet = book.create_sheet(table, index=position)
    else:
        book = Workbook()
        book.remove(book.active)
        sheet = book.create_sheet(table)

    sheet.append(list(frame.columns))
    for row in frame.itertuples(index=False):
        sheet.append(['' if value is None else value for value in row])

    sheet.freeze_panes = 'A2'
    style_header(sheet)
    for index, column in enumerate(frame.columns, start=1):
        letter = get_column_letter(index)
        sheet.column_dimensions[letter].width = (widths or {}).get(column, 18)

    held = [None]  # the hidden sheet, made only if something actually needs it

    def offer(name: str, allowed, target: str) -> None:
        """
        Constrain `target` -- any A1 range on this sheet -- to `allowed`.

        The values are written to a column of a hidden sheet and referred to by
        range, not listed inline in the rule: Excel truncates an inline list at
        255 characters without saying so, and the TC key lists go well past it.
        """
        if held[0] is None:
            held[0] = book[LISTS_SHEET] if LISTS_SHEET in book.sheetnames \
                else book.create_sheet(LISTS_SHEET)
            held[0].sheet_state = 'hidden'
        lists = held[0]

        # Reuse the column this name already has. Writing a sheet twice used to
        # append a fresh copy of every list, so _lists grew by seven columns per
        # write and the abandoned copies stayed behind, still holding whatever
        # the keys were at the time.
        headers = {}
        for index in range(1, lists.max_column + 1):
            header = lists.cell(row=1, column=index).value
            if header is not None:
                headers[header] = index
        column = headers.get(name) or (max(headers.values()) + 1 if headers else 1)

        # Clear first: a list that got shorter would otherwise keep its tail.
        for line in range(2, lists.max_row + 1):
            lists.cell(row=line, column=column, value=None)
        lists.cell(row=1, column=column, value=name)
        for line, value in enumerate(allowed, start=2):
            lists.cell(row=line, column=column, value=value)

        letter = get_column_letter(column)
        rule = DataValidation(
            type='list',
            formula1=f"={LISTS_SHEET}!${letter}$2:${letter}${len(allowed) + 1}",
            allow_blank=True, showDropDown=False)
        # showDropDown=False is Excel's spelling for "do show the arrow";
        # setting it True hides the control while still enforcing the list.
        rule.error = 'Not one of the values this case declares.'
        rule.errorTitle = 'Unknown value'
        sheet.add_data_validation(rule)
        rule.add(target)

    def offer_column(name: str, allowed) -> None:
        """Constrain a whole column, header row excepted."""
        letter = get_column_letter(list(frame.columns).index(name) + 1)
        offer(name, allowed, f'{letter}2:{letter}{max(len(frame) + 1, 2)}')

    covered = set()
    for column, allowed in sorted((dropdowns or {}).items()):
        if column not in frame.columns or not allowed:
            continue
        offer_column(column, allowed)
        covered.add(column)

    # `source` is a key/value sheet, so a fixed vocabulary constrains ONE cell
    # rather than a column: the value beside `child_layer` is element or
    # material, while the value beside `product` is anything at all.
    #
    # Applied here rather than passed in by the caller because nothing writes
    # this sheet today -- a parameter nobody passes is a parameter nobody
    # remembers, and the dropdown has to come back on a sheet rewritten later
    # by someone who never read this file.
    if table == 'processes':
        from src.rest import VOCABULARY as PROCESS_VOCABULARY

        for column, allowed in sorted(PROCESS_VOCABULARY.items()):
            if column in frame.columns and column not in covered:
                offer_column(column, allowed)

    if table == 'source' and {'key', 'value'} <= set(frame.columns):
        from src.source import VOCABULARY

        keys = [str(key).strip() for key in frame['key']]
        value_column = get_column_letter(list(frame.columns).index('value') + 1)
        for key, allowed in sorted(VOCABULARY.items()):
            if key in keys:
                line = keys.index(key) + 2  # +1 for the header, +1 to 1-based
                offer(key, allowed, f'{value_column}{line}')

    handle = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(path), prefix='.case-', suffix='.tmp', delete=False)
    handle.close()
    try:
        book.save(handle.name)
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
    return path
