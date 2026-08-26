"""
Check `src/sampling.py` against the mathematics it claims to implement.

    ./.venv/bin/python test_sampling.py

Plain asserts and no test framework, matching test_regression.py.

WHY THIS IS WRITTEN THIS WAY
----------------------------
A sampler is the easiest kind of code to get subtly wrong and never notice: it
produces plausible numbers whatever it does. "It runs" says nothing. So none of
these tests check that a function returns something -- each one compares the
code against an independent statement of what it should produce.

  * The quantile function is compared with `scipy.stats.triang`, a separate
    implementation by other people, not with itself.
  * The draws are compared with the distribution's closed-form mean and
    variance, and with its distribution function through a Kolmogorov-Smirnov
    statistic.
  * The seeding claim -- that draw i is the same number however the run is
    chunked -- is checked by chunking a run and comparing it to an unchunked
    one, value for value.
  * The sum-to-1 claim is checked on the constrained table (`template`) and on
    the unconstrained one (`basic_test`), because the interesting failure is
    normalising a table that was never meant to sum to 1.
"""

from __future__ import annotations

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if os.path.basename(os.path.dirname(os.path.abspath(__file__)))
                in ('tests', 'tools')
                else os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()


import os
import sys
import traceback

import numpy as np
import pandas as pd


from src.sampling import (SamplingError, clamp_bounds, check_ordering,
                          constrained_groups, numeric_bounds, sample,
                          triangular_quantile, uniforms)

TOLERANCE = 1e-12


def _tcs(path: str) -> pd.DataFrame:
    return pd.read_csv(f'data_folder/reference/{path}/input_data/TCs.csv',
                       keep_default_na=False, na_values=[])


# ----------------------------------------------------------------------
#  The distribution itself
# ----------------------------------------------------------------------

def test_quantile_matches_scipy() -> None:
    """
    The inverse CDF must agree with an independent implementation.

    scipy parameterises the triangular by shape c = (mode - a) / (b - a) with
    loc = a and scale = b - a.
    """
    from scipy import stats

    cases = [(0.0, 0.5, 1.0),      # symmetric
             (0.1, 0.15, 0.9),     # mode near the bottom
             (0.2, 0.85, 0.9),     # mode near the top
             (0.0, 0.0, 1.0),      # mode at the minimum
             (0.0, 1.0, 1.0),      # mode at the maximum
             (0.3, 0.4, 0.42)]     # narrow
    u = np.linspace(0.0, 1.0, 2001)

    for low, mode, high in cases:
        mine = triangular_quantile(low, mode, high, u)
        theirs = stats.triang.ppf(u, c=(mode - low) / (high - low),
                                  loc=low, scale=high - low)
        worst = np.max(np.abs(mine - theirs))
        assert worst < 1e-12, \
            f'quantile differs from scipy by {worst:.3e} for ({low}, {mode}, {high})'


def test_quantile_inverts_the_cdf() -> None:
    """F(F-inverse(u)) == u, checked against the CDF written in the docstring."""
    low, mode, high = 0.05, 0.2, 0.9
    u = np.linspace(1e-9, 1 - 1e-9, 5001)
    x = triangular_quantile(low, mode, high, u)

    below = (x - low) ** 2 / ((high - low) * (mode - low))
    above = 1.0 - (high - x) ** 2 / ((high - low) * (high - mode))
    recovered = np.where(x <= mode, below, above)

    worst = np.max(np.abs(recovered - u))
    assert worst < 1e-9, f'F(F^-1(u)) differs from u by {worst:.3e}'


def test_draws_match_closed_form_moments() -> None:
    """
    Mean and variance of the draws must match the distribution's own.

        mean = (a + b + c) / 3
        var  = (a^2 + b^2 + c^2 - ab - ac - bc) / 18
    """
    low, mode, high = 0.1, 0.25, 0.95
    u = np.random.default_rng(12345).random(400_000)
    x = triangular_quantile(low, mode, high, u)

    expected_mean = (low + high + mode) / 3.0
    expected_var = (low ** 2 + high ** 2 + mode ** 2
                    - low * high - low * mode - high * mode) / 18.0

    # Tolerance from the standard error of the estimates, generously widened.
    assert abs(x.mean() - expected_mean) < 5.0 * np.sqrt(expected_var / x.size), \
        f'mean {x.mean():.6f} against {expected_mean:.6f}'
    assert abs(x.var() - expected_var) < 0.01 * expected_var, \
        f'variance {x.var():.6e} against {expected_var:.6e}'


def test_draws_follow_the_distribution() -> None:
    """A Kolmogorov-Smirnov test against scipy's triangular, not just moments."""
    from scipy import stats

    low, mode, high = 0.0, 0.8, 1.0
    u = np.random.default_rng(7).random(200_000)
    x = triangular_quantile(low, mode, high, u)

    result = stats.kstest(x, stats.triang(c=(mode - low) / (high - low),
                                          loc=low, scale=high - low).cdf)
    assert result.pvalue > 0.001, \
        f'draws do not follow the triangular: KS statistic {result.statistic:.5f}'


def test_mode_is_the_most_common_value() -> None:
    """The densest part of the sample must sit at the mode, not the midpoint."""
    low, mode, high = 0.0, 0.1, 1.0     # strongly left-leaning
    x = triangular_quantile(low, mode, high,
                            np.random.default_rng(3).random(200_000))
    counts, edges = np.histogram(x, bins=50, range=(low, high))
    peak = 0.5 * (edges[counts.argmax()] + edges[counts.argmax() + 1])
    assert abs(peak - mode) < 0.05, f'sample peaks at {peak:.3f}, mode is {mode}'


def test_degenerate_range_is_a_point_mass() -> None:
    """min == max has no spread; every draw is that value, and none is NaN."""
    x = triangular_quantile(0.4, 0.4, 0.4, np.random.default_rng(1).random(1000))
    assert np.all(x == 0.4), 'a zero-width range did not give a constant'
    assert not np.isnan(x).any(), 'a zero-width range produced NaN'


def test_draws_stay_inside_the_bounds() -> None:
    """No draw may fall outside [min, max], for any shape including the corners."""
    for low, mode, high in [(0.0, 0.0, 1.0), (0.0, 1.0, 1.0), (0.2, 0.5, 0.7)]:
        x = triangular_quantile(low, mode, high,
                                np.random.default_rng(9).random(50_000))
        assert x.min() >= low - TOLERANCE and x.max() <= high + TOLERANCE, \
            f'draw outside [{low}, {high}] for mode {mode}'


# ----------------------------------------------------------------------
#  Bounds outside [0, 1] -- the rule is clamp, not refuse
# ----------------------------------------------------------------------

def test_bounds_below_zero_and_above_one_are_clamped() -> None:
    """A negative minimum becomes 0 and a maximum above 1 becomes 1."""
    tcs = _tcs('template').copy()
    tcs.loc[0, 'value_min'] = -0.2
    tcs.loc[1, 'value_max'] = 1.4

    clamped, notes = clamp_bounds(tcs)
    assert clamped.loc[0, 'value_min'] == 0.0, 'a negative minimum was not clamped to 0'
    assert clamped.loc[1, 'value_max'] == 1.0, 'a maximum above 1 was not clamped to 1'
    assert len(notes) == 2, f'clamping reported {len(notes)} changes, expected 2'


def test_clamping_leaves_valid_bounds_untouched() -> None:
    """Nothing inside [0, 1] may be altered, and nothing reported."""
    tcs = _tcs('template')
    clamped, notes = clamp_bounds(tcs)
    assert not notes, f'clamping changed rows that were already valid: {notes}'
    for column in ('value_min', 'value', 'value_max'):
        assert np.allclose(clamped[column].astype(float),
                           tcs[column].astype(float)), f'{column} was altered'


def test_clamped_bounds_still_produce_draws_in_range() -> None:
    """After clamping, sampling must stay within [0, 1]."""
    low, mode, high = np.clip([-0.2, 0.05, 1.4], 0.0, 1.0)
    x = triangular_quantile(low, mode, high, np.random.default_rng(2).random(20_000))
    assert x.min() >= 0.0 and x.max() <= 1.0, 'clamped bounds still produced out-of-range draws'


def test_ordering_is_refused_not_clamped() -> None:
    """min <= mode <= max is not a range problem, so it must raise."""
    tcs = _tcs('template').copy()
    tcs.loc[0, 'value_min'] = 0.9
    tcs.loc[0, 'value'] = 0.2
    try:
        check_ordering(tcs)
    except SamplingError as error:
        assert 'min <= mode <= max' in str(error), f'unhelpful message: {error}'
    else:
        raise AssertionError('a mode below its own minimum was accepted')


# ----------------------------------------------------------------------
#  Seeding: draw i is the same number however the run is chunked
# ----------------------------------------------------------------------

def test_chunked_draws_match_an_unchunked_run() -> None:
    """The claim that makes chunking safe. Checked value for value."""
    tcs = _tcs('template')
    whole = uniforms(tcs, draws=500)
    chunks = np.concatenate(
        [uniforms(tcs, draws=n, start=s) for s, n in ((0, 200), (200, 150), (350, 150))],
        axis=1)
    assert np.array_equal(whole, chunks), 'chunked draws differ from an unchunked run'


def test_draws_are_reproducible_across_runs() -> None:
    """Two calls must give identical numbers -- no hidden global state."""
    tcs = _tcs('template')
    assert np.array_equal(uniforms(tcs, 100), uniforms(tcs, 100)), \
        'two identical calls gave different draws'


def test_reordering_the_table_does_not_change_a_row_draws() -> None:
    """
    A coefficient's stream is keyed by its identity, not its position, so adding
    or moving rows must not disturb any other row.
    """
    tcs = _tcs('template')
    shuffled = tcs.iloc[::-1].reset_index(drop=True)
    original = uniforms(tcs, 50)
    reversed_draws = uniforms(shuffled, 50)
    assert np.array_equal(original, reversed_draws[::-1]), \
        'reordering the table changed the draws'


def test_seed_changes_the_draws() -> None:
    """A different seed must give a genuinely different repeat."""
    tcs = _tcs('template')
    assert not np.array_equal(uniforms(tcs, 100, seed=0), uniforms(tcs, 100, seed=1)), \
        'changing the seed did not change the draws'


def test_uniforms_are_uniform() -> None:
    """The stream feeding the quantile function must itself be flat on [0, 1)."""
    from scipy import stats
    tcs = _tcs('template')
    u = uniforms(tcs, 20_000).ravel()
    assert u.min() >= 0.0 and u.max() < 1.0, 'uniforms fell outside [0, 1)'
    assert stats.kstest(u, 'uniform').pvalue > 0.001, 'stream is not uniform'


# ----------------------------------------------------------------------
#  The sum-to-1 constraint
# ----------------------------------------------------------------------

def test_template_groups_are_all_constrained() -> None:
    """Every resource in `template` has explicit loss flows, so all sum to 1."""
    tcs = _tcs('template')
    groups = constrained_groups(tcs)
    assert len(groups) == 10, f'expected 10 constrained groups, found {len(groups)}'


def test_basic_test_groups_are_not_constrained() -> None:
    """
    The important negative. `basic_test` has no loss flows and its groups sum to
    between 0 and 0.66. Treating those as constrained would rescale them to 1 --
    inventing recovery rather than conserving mass.
    """
    tcs = _tcs('basic_test')
    assert len(constrained_groups(tcs)) == 0, \
        'a table without loss flows was treated as summing to 1'


def test_constrained_groups_sum_to_one_on_every_draw() -> None:
    """After sampling, each constrained group must total exactly 1."""
    from src.mass_balance import RESOURCE
    tcs = _tcs('template')
    values, report = sample(tcs, draws=2000)

    assert report['uncertain'], 'template has ranges but was treated as deterministic'
    for members in constrained_groups(tcs).values():
        totals = values[members].sum(axis=0)
        worst = np.max(np.abs(totals - 1.0))
        assert worst < 1e-9, f'a constrained group sums to 1 +/- {worst:.3e}'


def test_unconstrained_table_keeps_its_own_totals() -> None:
    """
    `basic_test` must come out near its stated coefficients, not rescaled. Its
    single-destination resources have no group to normalise against.
    """
    tcs = _tcs('basic_test')
    values, report = sample(tcs, draws=500)
    assert not report['clamped'], f'basic_test needed clamping: {report["clamped"]}'
    # Deterministic table: no ranges, so every draw is the mode.
    assert not report['uncertain'], 'basic_test has no ranges but was sampled'
    assert np.allclose(values[:, 0], tcs['value'].to_numpy(dtype=float)), \
        'a table without ranges did not return its own values'


def test_sampled_values_stay_inside_their_ranges_before_constraining() -> None:
    """
    Every draw of an unconstrained coefficient must lie inside its own [min, max].
    Checked on a copy of `template` with the constraint removed, since
    normalising deliberately moves values off their marginals.

    All three columns are scaled together: halving the mode alone would push it
    below its own minimum, which is refused rather than clamped, and the test
    would be measuring that instead.
    """
    tcs = _tcs('template').copy()
    for column in ('value_min', 'value', 'value_max'):
        tcs[column] = tcs[column].astype(float) * 0.5   # breaks every group's sum to 1
    values, report = sample(tcs, draws=1000)
    assert report['groups'] == 0, 'halving the ranges still left constrained groups'

    low = tcs['value_min'].to_numpy(dtype=float)[:, None]
    high = tcs['value_max'].to_numpy(dtype=float)[:, None]
    assert np.all(values >= low - TOLERANCE) and np.all(values <= high + TOLERANCE), \
        'a draw fell outside its own range'


def test_residual_row_absorbs_the_remainder() -> None:
    """
    With a residual named, the other rows keep their drawn values exactly and
    the residual takes 1 - their sum.
    """
    tcs = _tcs('template').copy()
    # Mark every loss destination as the residual of its group. A residual row
    # carries no range of its own -- it is computed from the others -- so its
    # bounds are cleared, which is what sample() now requires.
    tcs['is_residual'] = tcs['Output_FlowID'].str.contains('loss').astype(int)
    marked = tcs['is_residual'].astype(bool)
    for column in ('value_min', 'value_max'):
        tcs[column] = tcs[column].astype(object)
        tcs.loc[marked, column] = ''

    # The normalise comparison needs the fixture as written, ranges and all.
    plain, _ = sample(_tcs('template'), draws=200)
    with_residual, _ = sample(tcs, draws=200)

    recovery = ~tcs['Output_FlowID'].str.contains('loss').to_numpy()
    # Recovery rows must be untouched by the residual scheme, unlike normalising.
    # The residual rows now hold blanks, so fill them the way sample() does
    # before reading them as numbers. Only the recovery rows are compared, and
    # their bounds are untouched by that. The random streams are keyed on the
    # identity columns, so they are the same either way.
    filled = numeric_bounds(tcs)
    drawn = triangular_quantile(
        filled['value_min'].to_numpy(float), filled['value'].to_numpy(float),
        filled['value_max'].to_numpy(float), uniforms(tcs, 200).T).T
    assert np.allclose(with_residual[recovery], drawn[recovery]), \
        'the residual scheme altered rows that have their own data'
    assert not np.allclose(plain[recovery], drawn[recovery]), \
        'normalising left the recovery rows unchanged, so the two schemes are not distinct'

    for members in constrained_groups(tcs).values():
        totals = with_residual[members].sum(axis=0)
        assert np.max(np.abs(totals - 1.0)) < 1e-9, 'residual scheme broke sum to 1'


def _synthetic(rows: list[dict]) -> pd.DataFrame:
    """A minimal TC table, for cases the real data folders do not contain."""
    frame = pd.DataFrame(rows)
    frame['Input_layer'] = 'material'
    frame['TC_target_layer'] = 'element'
    frame['Input_FlowID'] = 'F_in'
    frame['Input_layer_key'] = 'M1'
    frame['TC_target_key'] = 'E1'
    return frame


def test_negative_residuals_are_counted_not_hidden() -> None:
    """
    A residual below zero means the drawn recovery fractions exceeded 1. It is a
    data problem and must be reported, never clipped away.

    Built explicitly rather than by mangling `template`: the group has to stay
    constrained -- its modes must still sum to 1 -- while the recovery rows are
    given enough headroom that their draws can pass 1 together. Mangling the
    template breaks the mode sum, which quietly un-constrains the group and
    makes the test pass for the wrong reason.
    """
    tcs = _synthetic([
        # modes sum to 1, so the group is constrained ...
        dict(Output_FlowID='F_recovered', value_min=0.30, value=0.50, value_max=0.70,
             is_residual=0),
        dict(Output_FlowID='F_other', value_min=0.25, value=0.45, value_max=0.65,
             is_residual=0),
        # ... and the loss row absorbs the remainder.
        # ... with no range of its own: it IS 1 - the other two.
        dict(Output_FlowID='F_loss', value_min='', value=0.05, value_max='',
             is_residual=1),
    ])
    # 0.70 + 0.65 = 1.35, so some draws must overshoot.
    assert len(constrained_groups(tcs)) == 1, 'the synthetic group is not constrained'

    _, report = sample(tcs, draws=2000)
    assert report['negative_residuals'] > 0, \
        'recovery fractions summing past 1 produced no negative residual report'


def test_residual_stays_exact_when_the_data_is_consistent() -> None:
    """
    The companion to the test above: ranges that cannot sum past 1 must produce
    no negative residuals at all, so the count means something.
    """
    tcs = _synthetic([
        # Modes sum to 1 (0.50 + 0.43 + 0.07), so the group is constrained,
        # but the maxima sum to 0.99 so the recovery rows cannot overshoot.
        dict(Output_FlowID='F_recovered', value_min=0.40, value=0.50, value_max=0.55,
             is_residual=0),
        dict(Output_FlowID='F_other', value_min=0.30, value=0.43, value_max=0.44,
             is_residual=0),
        dict(Output_FlowID='F_loss', value_min='', value=0.07, value_max='',
             is_residual=1),
    ])
    assert len(constrained_groups(tcs)) == 1, 'the synthetic group is not constrained'
    _, report = sample(tcs, draws=2000)
    assert report['negative_residuals'] == 0, \
        f"consistent ranges still reported {report['negative_residuals']} negative residuals"


# ----------------------------------------------------------------------
#  A range typed on a residual row -- refused, not discarded
# ----------------------------------------------------------------------

def _two_row_group(residual_min='', residual_max='') -> pd.DataFrame:
    """One constrained group: a recovery row with a range, and its residual."""
    common = dict(Input_FlowID='F_in', Input_layer='Layer 3',
                  Input_layer_key='Motors_mixed', TC_target_layer='Layer 4',
                  TC_target_key='Cu')
    return pd.DataFrame([
        dict(**common, Output_FlowID='F_recovered',
             value='0.10', value_min='0.02', value_max='0.30', is_residual=''),
        dict(**common, Output_FlowID='F_loss',
             value='0.90', value_min=residual_min, value_max=residual_max,
             is_residual='1'),
    ])


def test_a_range_on_a_residual_row_is_refused() -> None:
    """
    Bounds on a residual row used to be read, then thrown away: the row is
    overwritten with 1 - the others, so whatever was typed had no effect at
    all. Silently ignoring a number somebody measured is worse than refusing
    it, because nothing says the measurement was dropped.
    """
    for low, high in (('0.85', '0.95'), ('0.85', ''), ('', '0.95')):
        try:
            sample(_two_row_group(low, high), draws=64)
        except SamplingError as error:
            assert 'F_loss' in str(error), f'the offending row is not named: {error}'
            assert 'is_residual' in str(error), f'the reason is not given: {error}'
        else:
            raise AssertionError(
                f'a residual row with bounds ({low!r}, {high!r}) was accepted')


def test_a_residual_row_with_blank_bounds_still_samples() -> None:
    """The ordinary case must be untouched: blank bounds mean 'derive me'."""
    values, notes = sample(_two_row_group(), draws=4096)
    assert values.shape == (2, 4096)
    total = values.sum(axis=0)
    assert np.allclose(total, 1.0, atol=TOLERANCE), \
        f'the group does not sum to 1: [{total.min()}, {total.max()}]'
    # The derived row is exactly the reflection of the measured one.
    assert np.abs(values[1] - (1.0 - values[0])).max() == 0.0


# ----------------------------------------------------------------------
#  Are the measured distributions compatible with summing to 1?
# ----------------------------------------------------------------------

def test_symmetric_ranges_sit_centred_on_one() -> None:
    """
    When every measured range is symmetric, independent draws already average
    to 1, so the constraint has nothing to correct and the offset is zero.
    """
    from src.sampling import group_consistency

    tcs = _synthetic([
        dict(Output_FlowID='F_recovered', value_min=0.30, value=0.50, value_max=0.70,
             is_residual=0),
        dict(Output_FlowID='F_other', value_min=0.30, value=0.45, value_max=0.60,
             is_residual=0),
        dict(Output_FlowID='F_loss', value_min='', value=0.05, value_max='',
             is_residual=1),
    ])
    report = group_consistency(tcs)
    assert len(report) == 1, f'{len(report)} groups reported, expected 1'
    row = report.iloc[0]
    assert abs(row['sum_mode'] - 1.0) < 1e-12
    assert abs(row['sum_mean'] - 1.0) < 1e-12, \
        f"symmetric ranges gave a mean sum of {row['sum_mean']}"
    assert abs(row['offset']) < 1e-9, f"offset {row['offset']} should be zero"


def test_a_skewed_range_shows_up_as_an_offset() -> None:
    """
    A range whose mode is off-centre means the independent draws do NOT average
    to 1, even though the modes do. The constraint then has to move the result
    away from the numbers that were typed in, and `offset` says by how many
    standard deviations -- which is what makes a silent shift visible.
    """
    from src.sampling import group_consistency

    tcs = _synthetic([
        # mode 0.50 but the range runs to 0.95: mean 0.6167, far above the mode.
        dict(Output_FlowID='F_recovered', value_min=0.40, value=0.50, value_max=0.95,
             is_residual=0),
        dict(Output_FlowID='F_loss', value_min='', value=0.50, value_max='',
             is_residual=1),
    ])
    row = group_consistency(tcs).iloc[0]
    assert abs(row['sum_mode'] - 1.0) < 1e-12, 'the group should be constrained'
    assert row['sum_mean'] > 1.05, \
        f"a strongly right-skewed range gave a mean sum of {row['sum_mean']}"
    # Order one standard deviation. The exact figure depends on the range, so
    # the claim under test is that the offset is material, not that it is 0.98.
    assert abs(row['offset']) > 0.5, \
        f"offset {row['offset']} does not flag a group this far off centre"


def test_consistency_ignores_groups_that_are_not_constrained() -> None:
    """Only groups whose modes sum to 1 are corrected, so only they are judged."""
    from src.sampling import group_consistency

    tcs = _synthetic([
        dict(Output_FlowID='F_recovered', value_min=0.10, value=0.20, value_max=0.30,
             is_residual=0),
        dict(Output_FlowID='F_other', value_min=0.10, value=0.20, value_max=0.30,
             is_residual=0),
    ])
    assert len(group_consistency(tcs)) == 0, \
        'a group whose modes sum to 0.4 was judged against sum-to-1'


# ----------------------------------------------------------------------
#  Conditioning: enforce sum-to-1 without discarding anybody's measurement
# ----------------------------------------------------------------------

def _all_measured() -> pd.DataFrame:
    """A constrained group where every row carries a range of its own."""
    return _synthetic([
        dict(Output_FlowID='F_recovered', value_min=0.30, value=0.50, value_max=0.70,
             is_residual=0),
        dict(Output_FlowID='F_other', value_min=0.25, value=0.35, value_max=0.50,
             is_residual=0),
        dict(Output_FlowID='F_loss', value_min=0.05, value=0.15, value_max=0.30,
             is_residual=0),
    ])


def test_conditioning_keeps_the_group_summing_to_one() -> None:
    """Whatever else it does, the constraint must hold on every draw."""
    values, notes = sample(_all_measured(), draws=20_000, rule='condition')
    total = values.sum(axis=0)
    assert np.max(np.abs(total - 1.0)) < 1e-9, \
        f'conditioned group sums to [{total.min()}, {total.max()}]'
    assert notes['conditioned'] == 1, \
        f"{notes['conditioned']} groups conditioned, expected 1"


def test_conditioning_matches_brute_force_rejection() -> None:
    """
    The point of the method. Conditioning must give the same distribution as
    drawing every row from its own range and keeping only the draws that come
    to 1 -- which is the definition of what we want, just far too slow to run.
    """
    tcs = _all_measured()
    conditioned, _ = sample(tcs, draws=200_000, rule='condition')

    low = tcs['value_min'].to_numpy(float)
    mode = tcs['value'].to_numpy(float)
    high = tcs['value_max'].to_numpy(float)
    rng = np.random.default_rng(17)
    drawn = np.array([rng.triangular(l, m, h, 4_000_000)
                      for l, m, h in zip(low, mode, high)])
    keep = np.abs(drawn.sum(axis=0) - 1.0) < 0.004
    assert keep.sum() > 20_000, f'only {keep.sum()} draws survived rejection'

    for row in range(len(tcs)):
        a = np.percentile(conditioned[row], [5, 50, 95])
        b = np.percentile(drawn[row][keep], [5, 50, 95])
        assert np.allclose(a, b, atol=0.004), \
            f'row {row}: conditioning {a} vs rejection {b}'


def test_conditioning_reports_how_much_of_the_sample_survived() -> None:
    """
    Effective sample size is the diagnostic: it says how much the constraint
    and the measurements are fighting. Ranges that agree keep most of it.
    """
    _, notes = sample(_all_measured(), draws=50_000, rule='condition')
    assert 0.0 < notes['worst_ess'] <= 1.0, notes['worst_ess']
    assert notes['worst_ess'] > 0.3, \
        f"compatible ranges kept only {notes['worst_ess']:.1%} of the sample"


def test_contradictory_ranges_collapse_the_sample_instead_of_hiding() -> None:
    """
    Ranges that cannot all be true must show up as a collapsing effective
    sample, not as a quietly adjusted answer. This is the behaviour the
    residual and normalise rules do not have.
    """
    tcs = _synthetic([
        # These modes sum to 1, so the group is constrained -- but the two
        # measured rows sit nowhere near able to leave room for the third.
        dict(Output_FlowID='F_recovered', value_min=0.80, value=0.85, value_max=0.90,
             is_residual=0),
        dict(Output_FlowID='F_loss', value_min=0.10, value=0.15, value_max=0.20,
             is_residual=0),
    ])
    healthy, _ = sample(_all_measured(), draws=50_000, rule='condition')
    _, notes = sample(tcs, draws=50_000, rule='condition')
    assert notes['worst_ess'] < 0.9, \
        f"contradictory ranges still kept {notes['worst_ess']:.1%} of the sample"


def test_normalise_stays_the_default() -> None:
    """
    Conditioning is opt-in. Asking for nothing must give exactly what this
    project gave before it existed.
    """
    tcs = _all_measured()
    before, _ = sample(tcs, draws=5_000, rule='normalise')
    default, _ = sample(tcs, draws=5_000)
    assert np.array_equal(before, default), 'the default rule is no longer normalise'


def main() -> int:
    tests = [value for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as error:
            failures += 1
            print(f'FAIL  {test.__name__}\n      {error}\n')
        except Exception:
            failures += 1
            print(f'ERROR {test.__name__}')
            traceback.print_exc()
        else:
            print(f'ok    {test.__name__}')

    print(f'\n{len(tests) - failures} of {len(tests)} passed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
