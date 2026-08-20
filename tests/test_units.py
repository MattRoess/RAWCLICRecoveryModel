"""
Pin the unit conversion, which is the one thing in this project that can be
wrong by a clean factor of 1000 without looking wrong.

    ./.venv/bin/python test_units.py

The model multiplies fractions, so every ratio in the output stays correct
whatever unit went in. Nothing about a solution in the wrong unit looks odd --
which is exactly why the conversion needs pinning rather than trusting.
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


from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized
from src.units import (MASS_UNITS, UnitError, convert_inflows, factor, scale_for)

LAYER_NAMES = ['product', 'component', 'material', 'element']
KEYS = ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']


def _solve(case: str, unit: str, engine=RecoveryModelOptimized) -> pd.DataFrame:
    frame = engine(data_folder=f'data_folder/reference/{case}', layer_names=LAYER_NAMES,
                   working_unit=unit, years='').solve_models_and_write_to_output()
    frame['Value'] = pd.to_numeric(frame['Value'])
    for key in KEYS:
        frame[key] = frame[key].astype(str)
    return frame[KEYS + ['Value']].sort_values(KEYS).reset_index(drop=True)


# ----------------------------------------------------------------------
#  The conversion table
# ----------------------------------------------------------------------

def test_known_factors() -> None:
    """The relationships everything else rests on."""
    assert factor('Mg', 'kg') == 1000.0, '1 Mg must be 1000 kg'
    assert factor('kt', 'Mg') == 1000.0, '1 kt must be 1000 Mg'
    assert factor('kt', 'kg') == 1e6, '1 kt must be a million kg'
    assert factor('kg', 'kg') == 1.0, 'a unit to itself must be 1'
    assert factor('t', 'Mg') == 1.0, 'a tonne and a megagram are the same thing'


def test_conversion_round_trips() -> None:
    """Converting there and back must return the original, for every unit."""
    for unit in MASS_UNITS:
        there_and_back = factor('kg', unit) * factor(unit, 'kg')
        assert abs(there_and_back - 1.0) < 1e-12, \
            f'kg -> {unit} -> kg is off by {there_and_back - 1.0:.3e}'


def test_unknown_unit_raises() -> None:
    """An unrecognised label must not be treated as 'no conversion needed'."""
    try:
        factor('furlong', 'kg')
    except UnitError as error:
        assert 'not a mass unit' in str(error), f'unhelpful message: {error}'
    else:
        raise AssertionError("'furlong' was accepted as a mass unit")


def test_ambiguous_unit_raises() -> None:
    """'ton' is 1000, 907 or 1016 kg depending on where it is written."""
    try:
        factor('ton', 'kg')
    except UnitError as error:
        assert 'more than one quantity' in str(error), f'unhelpful message: {error}'
    else:
        raise AssertionError("'ton' was accepted despite being ambiguous")


# ----------------------------------------------------------------------
#  Converting an inflow table
# ----------------------------------------------------------------------

def test_inflow_conversion_scales_and_relabels() -> None:
    """Values scale, and the Unit column is rewritten to say what they now are."""
    inflows = pd.DataFrame({'Stock/Flow ID': ['F1'], 'Substance_main_parent': ['P1'],
                            'Value': [1000.0], 'Unit': ['Mg']})
    converted, note = convert_inflows(inflows, 'kg')
    assert converted['Value'].iloc[0] == 1_000_000.0, 'value did not scale by 1000'
    assert converted['Unit'].iloc[0] == 'kg', 'Unit column still claims the old unit'
    assert note and 'Mg' in note and 'kg' in note, f'unhelpful note: {note}'


def test_matching_unit_is_left_alone() -> None:
    """No conversion, no note, and the original object handed back untouched."""
    inflows = pd.DataFrame({'Value': [5.0], 'Unit': ['kg']})
    converted, note = convert_inflows(inflows, 'kg')
    assert note is None, f'a no-op conversion still reported: {note}'
    assert converted['Value'].iloc[0] == 5.0, 'a matching unit was altered'


# ----------------------------------------------------------------------
#  The whole model
# ----------------------------------------------------------------------

def test_kg_run_is_exactly_a_thousand_times_the_mg_run() -> None:
    """
    The claim that makes the setting safe to change. Every row, not the total:
    a mistake that scaled only the inflow rows and not their descendants would
    still balance in aggregate.
    """
    for case in ('basic_test', 'template'):
        in_mg = _solve(case, 'Mg')
        in_kg = _solve(case, 'kg')

        assert in_mg[KEYS].equals(in_kg[KEYS]), \
            f'{case}: changing the unit changed which rows exist'
        ratio = in_kg['Value'].to_numpy() / in_mg['Value'].to_numpy()
        worst = np.max(np.abs(ratio - 1000.0))
        assert worst < 1e-6, f'{case}: rows scaled by 1000 +/- {worst:.3e}'


def test_both_engines_convert_the_same_way() -> None:
    """
    A conversion applied in one engine and not the other would be a 1000x
    divergence that every existing comparison test would miss, because they
    each solve in whatever the current setting says.
    """
    optimized = _solve('basic_test', 'kg', RecoveryModelOptimized)
    linear = _solve('basic_test', 'kg', RecoveryModelLA)
    merged = optimized.merge(linear, on=KEYS, suffixes=('_opt', '_la'))
    worst = np.max(np.abs(merged['Value_opt'] - merged['Value_la']))
    assert worst < 1e-6, f'engines disagree under conversion by {worst:.3e}'


def test_conversion_does_not_disturb_the_fractions() -> None:
    """
    Composition and transfer coefficients are dimensionless, so the shape of
    the answer must be identical in any unit -- only its scale moves.
    """
    in_mg = _solve('template', 'Mg')
    in_kt = _solve('template', 'kt')
    share_mg = in_mg['Value'] / in_mg['Value'].sum()
    share_kt = in_kt['Value'] / in_kt['Value'].sum()
    worst = np.max(np.abs(share_mg - share_kt))
    assert worst < 1e-12, f'the shares moved between units by {worst:.3e}'


def test_working_unit_is_validated() -> None:
    """A nonsense working_unit must be caught in the settings, not at a merge."""
    from src.params_schema import Params

    params = Params()
    params.run.working_unit = 'furlong'
    issues = params.validate()
    assert any('working_unit' in issue for issue in issues), \
        f'a nonsense working_unit passed validation: {issues}'


# ----------------------------------------------------------------------
#  Choosing a unit to read a figure in
# ----------------------------------------------------------------------

def test_display_scale_picks_a_readable_unit() -> None:
    """
    The point of `scale_for`: no single unit suits both ends of this model, so
    a figure picks one that leaves its own numbers legible.
    """
    fleet_kg = np.array([5e8, 4e8, 6e8])          # ~500 kt of vehicles
    scale, unit = scale_for(fleet_kg, 'kg')
    assert unit == 'kt', f'a 500,000-tonne flow should read in kt, got {unit}'
    assert abs(fleet_kg[0] * scale - 500.0) < 1e-6, 'scale does not match the unit'

    gold_kg = np.array([3000.0, 2500.0, 3500.0])  # a few tonnes of gold
    scale, unit = scale_for(gold_kg, 'kg')
    assert unit == 't', f'a 3-tonne flow should read in t, got {unit}'
    assert abs(gold_kg[0] * scale - 3.0) < 1e-9, 'scale does not match the unit'


def test_display_scale_survives_an_empty_or_zero_series() -> None:
    """A flow that is all zeros must not send the scaler into a divide or a loop."""
    for values in (np.zeros(5), np.array([])):
        scale, unit = scale_for(values, 'kg')
        assert scale == 1.0 and unit == 'kg', 'an empty series changed the unit'


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
