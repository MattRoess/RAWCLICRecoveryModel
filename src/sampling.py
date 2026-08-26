"""
src/sampling.py
===============

Drawing transfer coefficients from their asymmetric triangular ranges.

This module is the whole of the "what value does a coefficient take on draw i"
question. It does not touch the flow network; `src/monte_carlo.py` does that.

THE DISTRIBUTION
----------------
A coefficient is given as three numbers -- `value_min` (a), `value` (c, the
mode) and `value_max` (b) -- with a <= c <= b. The mode sits off-centre, which
is the point: expert judgement about a recovery yield is rarely symmetric.

The triangular density is

    f(x) = 2(x - a) / ((b - a)(c - a))     a <= x <  c
    f(x) = 2(b - x) / ((b - a)(b - c))     c <= x <= b

and its distribution function is

    F(x) = (x - a)^2 / ((b - a)(c - a))            a <= x <= c
    F(x) = 1 - (b - x)^2 / ((b - a)(b - c))        c <  x <= b

Sampling is by inverse transform: draw u uniform on [0, 1) and invert F. With
F(c) = (c - a) / (b - a),

    x = a + sqrt(u (b - a)(c - a))            u <  F(c)
    x = b - sqrt((1 - u)(b - a)(b - c))       u >= F(c)

Inverse transform is used rather than numpy's `Generator.triangular` because
this way the value of draw i depends only on u_i, so it survives chunking and
reordering -- see SEEDING below. The two are checked against each other, and
against scipy's independent implementation, in `test_sampling.py`.

BOUNDS OUTSIDE [0, 1]
---------------------
A transfer coefficient is a fraction of a resource, so it cannot be negative
and cannot exceed one. An elicited range that runs past either end is not an
error in the judgement, it is the judgement bumping into the physical limit:
"somewhere around 0.05, could be nothing at all" is naturally written as
-0.02 to 0.15.

So a bound outside [0, 1] is pulled back to the boundary rather than refused.
`clamp_bounds` does it, and says what it changed. Note the consequence: pulling
a to 0 makes the distribution steeper on that side, because the same probability
mass now sits in a narrower interval. That is the correct reading of a bound
that was never physically reachable.

Ordering is still enforced after clamping. a <= c <= b is not a range problem
that a boundary can fix -- a mode outside its own bounds means the three numbers
disagree about what they describe, and that is refused.

SEEDING
-------
Draw i of a given coefficient is the same number no matter how the run is
chunked, how many draws are asked for, or what order the table is in. Two
things make that true:

  * each coefficient gets its own stream, keyed by a stable hash of its
    identity -- not by its position in the file, which changes when a row is
    added; and
  * a chunk starting at draw `start` advances that stream by exactly `start`
    before drawing, rather than continuing from wherever the last chunk left
    off.

This is what lets two scenarios be compared: the same draw index means the same
underlying u in both, so the difference between them is the scenario and not
noise.

THE SUM-TO-1 CONSTRAINT
-----------------------
Coefficients are constrained in groups: everything a single resource can turn
into, across all the output flows it reaches (`RESOURCE` in
`src/mass_balance.py`). Sampling each member independently does not respect it.

A group is treated as constrained **only if its modes already sum to 1**. That
is deliberate. In a table with explicit loss flows every group sums to 1 and
every group is constrained. In a table without them a group sums to whatever it
sums to -- 0.25, say -- and forcing that to 1 would not conserve mass, it would
invent recovery fourfold. Sum-to-1 is a property a well-formed table has, not
one this module may impose on a table that lacks it.

See documentation/DESIGN_monte_carlo.md section 4 for the two ways to enforce
it and what each costs.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

# A resource is where it comes from and what it becomes. Output_FlowID is
# absent on purpose: that is the axis a constrained group sums over. Imported
# rather than redefined so that the grouping the sampler constrains is the same
# one 01_check_inputs.py reports on.
from src.mass_balance import RESOURCE

# How close to 1 a group's modes must sum before it is treated as constrained.
# Loose enough for the rounding in a hand-written table, tight enough that a
# group summing to 0.99 by intent is not silently rescaled.
SUM_TOLERANCE = 1e-6

MIN_COLUMN = 'value_min'
MODE_COLUMN = 'value'
MAX_COLUMN = 'value_max'

# Optional column naming the row that absorbs the rounding in a constrained
# group -- normally the loss flow. See `enforce_sum_to_one`.
RESIDUAL_COLUMN = 'is_residual'


class SamplingError(ValueError):
    """Raised when a coefficient's three numbers cannot describe a distribution."""


def numeric_bounds(tcs: pd.DataFrame) -> pd.DataFrame:
    """
    Read the three columns as numbers, treating a blank bound as "no spread".

    A row derived as the residual of its group carries no range of its own --
    its spread follows from the rows it is derived from, so writing one would be
    asserting something twice. Blank therefore means "this value exactly", and
    the row becomes a point mass rather than an error.
    """
    tcs = tcs.copy()
    tcs[MODE_COLUMN] = pd.to_numeric(tcs[MODE_COLUMN], errors='coerce')
    for column in (MIN_COLUMN, MAX_COLUMN):
        if column in tcs.columns:
            tcs[column] = pd.to_numeric(
                tcs[column].astype(str).str.strip().replace('', None),
                errors='coerce').fillna(tcs[MODE_COLUMN])
    return tcs


def clamp_bounds(tcs: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Pull every bound into [0, 1], and report what moved.

    A coefficient is a fraction, so a bound outside [0, 1] names a value the
    quantity cannot take. Clamping is the documented behaviour, not a silent
    repair, so the second return value lists every change in full.

    Returns:
        The table with bounds clamped, and one line per row that changed.
    """
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        return tcs, []

    tcs = numeric_bounds(tcs)
    notes: list[str] = []

    for column in (MIN_COLUMN, MODE_COLUMN, MAX_COLUMN):
        original = tcs[column].astype(float)
        clamped = original.clip(0.0, 1.0)
        for position in np.flatnonzero((original != clamped).to_numpy()):
            row = tcs.iloc[position]
            notes.append(
                f"{row['Input_FlowID']} {row['Input_layer_key']} -> "
                f"{row['Output_FlowID']} {row['TC_target_key']}: "
                f"{column} {original.iloc[position]:g} -> {clamped.iloc[position]:g}")
        tcs[column] = clamped

    return tcs, notes


def check_ordering(tcs: pd.DataFrame) -> None:
    """
    Refuse a row whose three numbers do not satisfy min <= mode <= max.

    Clamping cannot fix this. A mode above its own maximum is not a bound that
    overshot a physical limit, it is three numbers that disagree about what they
    describe, and guessing which one is wrong would be inventing data.
    """
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        return

    low = tcs[MIN_COLUMN].astype(float)
    mode = tcs[MODE_COLUMN].astype(float)
    high = tcs[MAX_COLUMN].astype(float)
    broken = tcs[(low > mode) | (mode > high)]
    if len(broken):
        lines = [f"  {row['Input_FlowID']} {row['Input_layer_key']} -> "
                 f"{row['Output_FlowID']} {row['TC_target_key']}: "
                 f"min {row[MIN_COLUMN]:g}, mode {row[MODE_COLUMN]:g}, max {row[MAX_COLUMN]:g}"
                 for _, row in broken.iterrows()]
        raise SamplingError(
            f'{len(broken)} transfer coefficient(s) do not satisfy '
            f'min <= mode <= max, after bounds were clamped into [0, 1]:\n'
            + '\n'.join(lines)
            + '\n\nCorrect the three numbers in TCs.csv. They cannot all be right.')


def check_residual_bounds(tcs: pd.DataFrame) -> None:
    """
    Refuse a range written on a row that is derived rather than measured.

    A row marked `is_residual` is overwritten with 1 - the rest of its group on
    every draw, so a spread typed on it has no effect at all. The run used to
    read those two numbers and discard them without a word, which is worse than
    refusing them: nothing told you a measurement had been dropped.

    A bound EQUAL to the mode is not a range -- that is what a blank becomes
    once `numeric_bounds` has run -- so only a genuine spread is refused, and a
    table that has already been through that step reads the same as a raw one.
    """
    if RESIDUAL_COLUMN not in tcs.columns:
        return
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        return

    tcs = numeric_bounds(tcs)
    residual = tcs[RESIDUAL_COLUMN].astype(bool).to_numpy()
    mode = tcs[MODE_COLUMN].to_numpy(dtype=np.float64)
    spread = ((tcs[MIN_COLUMN].to_numpy(dtype=np.float64) < mode)
              | (tcs[MAX_COLUMN].to_numpy(dtype=np.float64) > mode))

    offending = tcs[residual & spread]
    if not len(offending):
        return

    lines = [f"  {row['Input_FlowID']} {row['Input_layer_key']} -> "
             f"{row['Output_FlowID']} {row['TC_target_key']}: "
             f"min {row[MIN_COLUMN]:g}, mode {row[MODE_COLUMN]:g}, "
             f"max {row[MAX_COLUMN]:g}"
             for _, row in offending.iterrows()]
    raise SamplingError(
        f'{len(offending)} row(s) marked {RESIDUAL_COLUMN} carry a range of '
        f'their own:\n' + '\n'.join(lines)
        + f'\n\nA {RESIDUAL_COLUMN} row is computed as 1 - the rest of its '
        f'group on every\ndraw, so this range would be discarded rather than '
        f'used. Either clear\n{MIN_COLUMN} and {MAX_COLUMN} and let the row be '
        f'derived, or clear\n{RESIDUAL_COLUMN} and let it be sampled from its '
        f'own measurement like any\nother row. See documentation/CASES.md.')


def triangular_quantile(low, mode, high, u):
    """
    The inverse distribution function of the triangular distribution.

    Vectorised and shape-broadcasting: `low`, `mode` and `high` are per
    coefficient, `u` is per (coefficient, draw).

    Args:
        low:  a, the smallest value the coefficient can take
        mode: c, the most likely value
        high: b, the largest value
        u:    uniform variates on [0, 1)

    Returns:
        Values distributed Triangular(a, c, b), the same shape as `u`.
    """
    low = np.asarray(low, dtype=np.float64)
    mode = np.asarray(mode, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64)

    width = high - low
    # A zero-width range is a point mass, not a distribution. Guard the division
    # rather than special-casing afterwards, so the branch arithmetic below
    # never sees a divide by zero and never produces a NaN to clean up.
    safe_width = np.where(width > 0, width, 1.0)
    split = (mode - low) / safe_width          # F(c), the share of mass below the mode

    lower = low + np.sqrt(u * width * (mode - low))
    upper = high - np.sqrt((1.0 - u) * width * (high - mode))

    drawn = np.where(u < split, lower, upper)
    return np.where(width > 0, drawn, np.broadcast_to(low, np.shape(drawn)))


def _stream_key(row: pd.Series) -> int:
    """
    A stable 64-bit seed for one coefficient's own random stream.

    Built from the identity of the coefficient -- which resource, moving from
    where to where -- so that adding, removing or reordering rows in TCs.csv
    does not change the draws for any other row.

    Python's built-in hash() is deliberately not used: it is randomised per
    process, so it would give different numbers on every run.
    """
    identity = '|'.join(str(row[column]) for column in
                        ('Input_FlowID', 'Input_layer', 'Input_layer_key',
                         'Output_FlowID', 'TC_target_layer', 'TC_target_key'))
    digest = hashlib.blake2b(identity.encode('utf-8'), digest_size=8).digest()
    return int.from_bytes(digest, 'big')


def uniforms(tcs: pd.DataFrame, draws: int, start: int = 0, seed: int = 0) -> np.ndarray:
    """
    Uniform variates, one row per coefficient and one column per draw.

    Each coefficient draws from its own stream, advanced to `start`, so that
    draw i is the same value whatever chunk it arrives in. Verified in
    `test_sampling.py`: a chunked run reproduces a single run exactly.

    Args:
        tcs:   the coefficient table, one row per coefficient
        draws: how many draws this chunk covers
        start: index of the first draw in this chunk
        seed:  shifts every stream together, for a genuinely independent repeat

    Returns:
        Array of shape (len(tcs), draws), values on [0, 1).
    """
    out = np.empty((len(tcs), draws), dtype=np.float64)
    for position, (_, row) in enumerate(tcs.iterrows()):
        bit_generator = np.random.PCG64(_stream_key(row) ^ np.uint64(seed))
        if start:
            # Advance rather than generate-and-discard: same result, but O(1)
            # instead of O(start), which matters when start is 190,000.
            bit_generator = bit_generator.advance(start)
        out[position] = np.random.Generator(bit_generator).random(draws)
    return out


def constrained_groups(tcs: pd.DataFrame) -> dict[tuple, np.ndarray]:
    """
    Which coefficients must sum to 1 together, by row position.

    A group is everything one resource turns into, across the output flows it
    reaches. It is included **only if its modes already sum to 1** -- a table
    without explicit loss flows has groups summing to well under 1, and forcing
    those to 1 would invent recovery rather than conserve mass.

    Returns:
        {group key: array of row positions}, only for constrained groups.
    """
    positions = np.arange(len(tcs))
    groups: dict[tuple, np.ndarray] = {}
    for key, index in tcs.groupby(RESOURCE, sort=False).indices.items():
        members = positions[index] if index.dtype != np.intp else index
        if abs(float(tcs.iloc[members][MODE_COLUMN].sum()) - 1.0) <= SUM_TOLERANCE:
            groups[key] = np.asarray(members)
    return groups


def group_consistency(tcs: pd.DataFrame) -> pd.DataFrame:
    """
    Whether each constrained group's measured ranges agree with summing to 1.

    The modes of a constrained group sum to 1 by definition -- that is what
    makes it constrained. The MEANS need not. A triangular's mean is
    (min + mode + max) / 3, so a range whose mode sits off centre has a mean
    away from its mode, and a group of such rows lands somewhere other than 1
    when its rows are drawn independently.

    That gap is what forces the constraint to move the answer away from the
    numbers that were typed in, and it is reported here as `offset`: how many
    standard deviations of the independent sum separate 1 from where that sum
    actually lands. Near zero means the ranges already agree with the
    constraint and enforcing it changes almost nothing. Large means the
    measured distributions and sum-to-1 are pulling in different directions,
    and whichever rule is applied will have to override something.

    Rows with no range of their own -- the residuals -- are point masses, so
    they add their mode and no spread. The offset therefore measures exactly
    the skew of the rows that DO carry a measurement.

    Returns:
        One row per constrained group: its members, the sums, and the offset.
        Empty when nothing is constrained.
    """
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        return pd.DataFrame()

    tcs = numeric_bounds(tcs)
    low = tcs[MIN_COLUMN].to_numpy(dtype=np.float64)
    mode = tcs[MODE_COLUMN].to_numpy(dtype=np.float64)
    high = tcs[MAX_COLUMN].to_numpy(dtype=np.float64)

    # Closed form, so this costs nothing next to sampling the table.
    mean = (low + mode + high) / 3.0
    variance = (low ** 2 + mode ** 2 + high ** 2
                - low * mode - low * high - mode * high) / 18.0

    rows = []
    for key, members in constrained_groups(tcs).items():
        spread = float(np.sqrt(variance[members].sum()))
        sum_mean = float(mean[members].sum())
        rows.append({
            **dict(zip(RESOURCE, key)),
            'rows': len(members),
            'sum_mode': float(mode[members].sum()),
            'sum_mean': sum_mean,
            'sd': spread,
            # A group with no spread at all sits exactly where its modes put
            # it, so there is nothing for the constraint to move.
            'offset': 0.0 if spread == 0 else (sum_mean - 1.0) / spread,
        })
    return pd.DataFrame(rows)


def triangular_density(low, mode, high, x):
    """
    The triangular pdf, vectorised, and zero outside [low, high].

    A degenerate row -- low == high -- has no density to speak of, so it
    returns zero everywhere and the caller must not use it as the derived row.
    """
    low = np.asarray(low, dtype=np.float64)
    mode = np.asarray(mode, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)

    width = high - low
    out = np.zeros_like(x)
    if np.all(width <= 0):
        return out

    rising = (x >= low) & (x <= mode) & (mode > low)
    falling = (x > mode) & (x <= high) & (high > mode)
    with np.errstate(divide='ignore', invalid='ignore'):
        out = np.where(rising, 2 * (x - low) / (width * (mode - low)), out)
        out = np.where(falling, 2 * (high - x) / (width * (high - mode)), out)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def _systematic(weights: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Indices drawn in proportion to `weights`, as many as there are weights.

    Systematic rather than multinomial: one uniform for the whole sweep, so the
    resampling adds the least extra noise of any scheme with these weights.
    """
    total = np.cumsum(weights)
    if total[-1] <= 0:
        raise SamplingError(
            'A constrained group has no draw with any weight at all: no '
            'combination of\nthe measured ranges can sum to 1. The ranges in '
            'that group contradict\neach other -- see the SUM TO 1 section of '
            '01_check_inputs.py.')
    positions = (rng.random() + np.arange(len(weights))) / len(weights)
    return np.searchsorted(total / total[-1], positions)


def condition_on_sum(values: np.ndarray, groups: dict[tuple, np.ndarray],
                     low: np.ndarray, mode: np.ndarray, high: np.ndarray,
                     seed: int = 0) -> tuple[np.ndarray, dict]:
    """
    Enforce sum-to-1 by conditioning, keeping every row's own measurement.

    The residual rule overwrites one row and throws its measurement away.
    Normalising divides the whole group and shifts every marginal off the
    triangular it was drawn from. Neither uses what the sheet says about the
    row it adjusts.

    Conditioning is the third answer, and it is what "sum to 1" actually means
    probabilistically: the target is the product of every row's own density,
    restricted to the draws that do sum to 1. Sampling it directly:

      * draw every row from its own range, as already happened;
      * take one row -- the widest, purely for efficiency -- as determined by
        the others, so the group sums to 1 exactly;
      * weight each draw by that row's OWN density at the value it was forced
        to take, which is how its measurement re-enters;
      * resample in proportion to those weights, so the draws come out equally
        weighted again and nothing downstream has to know about any of this.

    Which row is taken as determined does not change the answer -- the target
    is the same product either way -- so there is no arbitrary choice here of
    the kind `is_residual` makes.

    A draw forced outside its own range gets density zero and is dropped by the
    resampling. If that happens to nearly all of them, the ranges in the group
    cannot all be true, and the effective sample size collapses instead of the
    contradiction being quietly absorbed.

    Returns:
        The corrected values, and notes carrying the effective sample size of
        the worst group as a fraction of the draws.
    """
    values = values.copy()
    draws = values.shape[1]
    rng = np.random.default_rng(np.uint64(seed) ^ np.uint64(0x5EED_C0FFEE))
    survival = []

    for members in groups.values():
        spread = high[members] - low[members]
        if not np.any(spread > 0):
            continue          # every row is a point mass; nothing to condition

        # The widest row carries the flattest density, which makes the weights
        # flattest and keeps the most of the sample.
        derived = int(np.argmax(spread))
        others = np.setdiff1d(np.arange(len(members)), derived)

        block = values[members]
        forced = 1.0 - block[others].sum(axis=0)
        weights = triangular_density(low[members][derived], mode[members][derived],
                                     high[members][derived], forced)

        block[derived] = forced
        keep = _systematic(weights, rng)
        values[members] = block[:, keep]

        # Kish's effective sample size: how many independent draws this
        # weighted set is worth.
        squared = float(np.sum(weights ** 2))
        survival.append(float(weights.sum()) ** 2 / squared / draws
                        if squared > 0 else 0.0)

    return values, {
        'conditioned': len(survival),
        'worst_ess': min(survival) if survival else 1.0,
    }


def enforce_sum_to_one(values: np.ndarray, groups: dict[tuple, np.ndarray],
                       residual: np.ndarray | None = None) -> tuple[np.ndarray, int]:
    """
    Make each constrained group sum to exactly 1 on every draw.

    Two ways, per documentation/DESIGN_monte_carlo.md section 4:

    * **Residual** -- when the group names one row as the residual, the others
      keep the values they were drawn with and the residual takes 1 - their
      sum. This is the right causal direction where the residual is a loss
      flow: loss is whatever was not recovered, and it is the term with the
      weakest independent data. It leaves the marginals of the coefficients
      that *do* have data undistorted.

    * **Normalise** -- otherwise, divide the group by its own sum. This always
      works and needs nothing added to the table, at the cost of shifting every
      marginal off the triangular it was drawn from.

    A residual coming out negative means the sampled recovery fractions summed
    past 1, which is physically impossible and says the input ranges are wrong.
    It is counted and returned, never silently clipped.

    Args:
        values:   (n_coefficients, n_draws), as drawn
        groups:   from `constrained_groups`
        residual: boolean per row, True for a row that absorbs the remainder

    Returns:
        The corrected values, and how many (group, draw) pairs went negative.
    """
    values = values.copy()
    negatives = 0

    for members in groups.values():
        block = values[members]

        if residual is not None and residual[members].any():
            which = np.flatnonzero(residual[members])
            if len(which) > 1:
                raise SamplingError(
                    f'A constrained group names {len(which)} residual rows; '
                    f'at most one row per group may carry {RESIDUAL_COLUMN}.')
            others = np.setdiff1d(np.arange(len(members)), which)
            remainder = 1.0 - block[others].sum(axis=0)
            negatives += int((remainder < 0).sum())
            block[which[0]] = remainder
        else:
            total = block.sum(axis=0)
            # A group whose draws all came out zero cannot be normalised. It can
            # only happen if every member has max 0, which the mode sum check
            # above already excludes, but dividing by it would poison the array
            # with NaN rather than failing loudly, so it is guarded.
            block = np.divide(block, total, out=np.zeros_like(block),
                              where=total > 0)

        values[members] = block

    return values, negatives


# How a constrained group with no `is_residual` row is made to sum to 1.
#
# 'condition' is the default and the one to use: it keeps every row's own
# measurement, which is what sum-to-1 means probabilistically. See
# `condition_on_sum`.
#
# 'normalise' divides the group by its own sum. It is kept for two reasons and
# no others: reproducing a result computed before conditioning existed, and
# getting a number out of a group whose ranges CONTRADICT each other, which
# conditioning refuses. Note what the second one means -- normalising a
# contradictory group does not resolve it, it hides it.
#
# Groups that name a residual row are unaffected either way.
SUM_RULES = ('normalise', 'condition')


def sample(tcs: pd.DataFrame, draws: int, start: int = 0, seed: int = 0,
           rule: str = 'condition') -> tuple[np.ndarray, dict]:
    """
    Draw every transfer coefficient, respecting the sum-to-1 groups.

    This is the entry point; the functions above are its steps, kept separate
    so each can be checked against the mathematics on its own.

    Args:
        tcs:   coefficient table, with value_min / value / value_max
        draws: how many draws this chunk covers
        start: index of the first draw, for chunked runs
        seed:  shifts every stream together

    Returns:
        (n_coefficients, draws) of sampled values, and a report describing what
        was clamped, which groups are constrained, and any negative residuals.
    """
    if MIN_COLUMN not in tcs.columns or MAX_COLUMN not in tcs.columns:
        # A deterministic table. Every draw is the mode, which is the honest
        # answer: a coefficient given as one number has no spread to sample.
        modes = tcs[MODE_COLUMN].to_numpy(dtype=np.float64)
        return np.repeat(modes[:, None], draws, axis=1), {
            'uncertain': False, 'clamped': [], 'groups': 0, 'negative_residuals': 0}

    check_residual_bounds(tcs)
    tcs, clamped = clamp_bounds(tcs)
    check_ordering(tcs)

    values = triangular_quantile(
        tcs[MIN_COLUMN].to_numpy(dtype=np.float64),
        tcs[MODE_COLUMN].to_numpy(dtype=np.float64),
        tcs[MAX_COLUMN].to_numpy(dtype=np.float64),
        uniforms(tcs, draws, start=start, seed=seed).T,
    ).T

    groups = constrained_groups(tcs)
    residual = (tcs[RESIDUAL_COLUMN].astype(bool).to_numpy()
                if RESIDUAL_COLUMN in tcs.columns else None)

    # A group naming a residual row is settled by that row and stays on the
    # residual rule: the residual carries no measurement of its own -- blank
    # bounds, enforced by `check_residual_bounds` -- so there is nothing there
    # to condition on, and for a two-row group the rule is exact anyway.
    conditioning: dict = {'conditioned': 0, 'worst_ess': 1.0}
    if rule == 'condition':
        named = {key: members for key, members in groups.items()
                 if residual is not None and residual[members].any()}
        free = {key: members for key, members in groups.items() if key not in named}
        values, negatives = enforce_sum_to_one(values, named, residual)
        values, conditioning = condition_on_sum(
            values, free,
            tcs[MIN_COLUMN].to_numpy(dtype=np.float64),
            tcs[MODE_COLUMN].to_numpy(dtype=np.float64),
            tcs[MAX_COLUMN].to_numpy(dtype=np.float64),
            seed=seed)
    elif rule == 'normalise':
        values, negatives = enforce_sum_to_one(values, groups, residual)
    else:
        raise SamplingError(
            f'rule={rule!r} is not one of {", ".join(SUM_RULES)}.')

    return values, {
        'uncertain': True,
        'clamped': clamped,
        'groups': len(groups),
        'unconstrained': len(tcs.groupby(RESOURCE, sort=False)) - len(groups),
        'negative_residuals': negatives,
        **conditioning,
    }
