"""
Pin the deterministic behaviour of the model, so that later work cannot move it
without saying so.

    ./.venv/bin/python test_regression.py

Plain asserts and no test framework, so it needs nothing that is not already in
requirements.txt. The functions are named `test_*` and take no arguments, so
`pytest test_regression.py` also collects them if pytest is ever added.

WHY THIS EXISTS
---------------
Defect 1.3 (documentation/DEFECTS.md) was a 300,000x intermediate blow-up that
went unnoticed for months **because the output stayed correct**. Nothing about
a wrong answer announced itself. The Monte Carlo restructuring ahead touches
exactly the code that produced that defect, so the deterministic answer needs
to be nailed down before it starts.

WHAT IS PINNED
--------------
1. Both engines reproduce the committed reference for `basic_test`.
2. The two engines agree with each other on that case.
3. The intermediate frames stay small -- the direct guard against defect 1.3.
4. Every defect case in DEFECTS.md §2 gives the same answer on both engines.
   These were non-zero until 2026-08-17; a case reappearing here means a
   divergence has come back.
5. The loader refuses what it is supposed to refuse: unknown keys, a
   composition row with a gap, a bad mass unit, a percentage where a fraction
   was meant, a same-layer transformation.
6. The two resolved semantics produce the agreed numbers -- overlapping rules
   resolve to the specific one, and a scenario is matched exactly rather than
   by prefix.
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

import pandas as pd


from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

LAYER_NAMES = ['product', 'component', 'material', 'element']
KEYS = ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

CASE = 'data_folder/reference/basic_test'
REFERENCE = f'{CASE}/output_data/solution.csv'

# Compared with a tolerance rather than exactly, for two reasons: the reference
# CSV round-trips through decimal text, and the LA engine's own answer moves by
# about 1.5 ULP between runs because it builds its integer encoding from an
# unordered set (DEFECTS.md §3.5). Measured worst case against the committed
# reference is 5.7e-14; 1e-9 leaves four orders of magnitude of headroom while
# still catching any change that means anything.
TOLERANCE = 1e-9

# Peak intermediate rows for basic_test is 214. Defect 1.3 grew the frame 16x
# per process step, so a recurrence reaches 704 at the first step and 3,062,016
# by the last. 1000 sits above the real figure with headroom and below anything
# a blow-up could produce.
MAX_INTERMEDIATE_ROWS = 1000

# The largest absolute disagreement between the two engines on each case.
#
# All three were non-zero until 2026-08-17 -- 100.0, 50.0 and 50.0 -- when
# DEFECTS.md §2.1, §2.2 and §2.3 were resolved. They are zero now and this test
# is what holds them there. Every remaining entry in section 2 of DEFECTS.md is
# either caught at load or documented as an input error, so there is no longer
# a case where the two engines are expected to differ.
DOCUMENTED_DIVERGENCES = {
    'data_folder/reference/defect_cases/composition_stock_id': 0.0,
    'data_folder/reference/defect_cases/wildcard_star': 0.0,
    'data_folder/reference/defect_cases/tc_specificity': 0.0,
    'data_folder/reference/defect_cases/scenario_prefix': 0.0,
}


# Cases that declare scenarios have to say which one they mean, since one run
# is one scenario. Everything else has no scenario dimension at all.
SCENARIO_FOR = {'data_folder/reference/defect_cases/scenario_prefix': 'BAU'}


# The committed reference and the defect cases are all written in Mg, so they
# are solved in Mg. The project's working_unit is a reporting choice, and
# letting it reach these tests would make changing it look like the algebra had
# moved -- every pinned number would shift by a clean factor of 1000.
# test_units.py is where the conversion itself is pinned.
REFERENCE_UNIT = 'Mg'

# Blank means 'every year in the file'. Pinned here for the same reason as the
# unit: these tests pin the ALGEBRA, and inheriting run.years made all sixteen
# fail the moment the live setting moved to a range the reference does not hold.
REFERENCE_YEARS = ''


def solve(engine, folder: str) -> pd.DataFrame:
    model = engine(data_folder=folder, layer_names=LAYER_NAMES,
                   scenario=SCENARIO_FOR.get(folder),
                   working_unit=REFERENCE_UNIT, years=REFERENCE_YEARS)
    frame = model.solve_models_and_write_to_output()
    for key in KEYS:
        frame[key] = frame[key].astype(str)
    frame['Value'] = pd.to_numeric(frame['Value'])
    return frame[KEYS + ['Value']]


def load_reference() -> pd.DataFrame:
    frame = pd.read_csv(REFERENCE, keep_default_na=False, na_values=[])
    for key in KEYS:
        frame[key] = frame[key].astype(str)
    frame['Value'] = pd.to_numeric(frame['Value'])
    return frame[KEYS + ['Value']]


def compare(left: pd.DataFrame, right: pd.DataFrame, left_name: str, right_name: str) -> None:
    """Assert two solutions hold the same rows with the same values."""
    merged = left.merge(right, on=KEYS, how='outer',
                        suffixes=('_left', '_right'), indicator=True)

    only_left = merged[merged['_merge'] == 'left_only']
    only_right = merged[merged['_merge'] == 'right_only']
    assert only_left.empty, (
        f'{len(only_left)} row(s) in {left_name} missing from {right_name}:\n'
        f'{only_left[KEYS].head().to_string(index=False)}')
    assert only_right.empty, (
        f'{len(only_right)} row(s) in {right_name} missing from {left_name}:\n'
        f'{only_right[KEYS].head().to_string(index=False)}')

    difference = (merged['Value_left'] - merged['Value_right']).abs()
    worst = difference.max()
    assert worst <= TOLERANCE, (
        f'{left_name} and {right_name} differ by up to {worst:g}, above the '
        f'{TOLERANCE:g} tolerance. Worst rows:\n'
        f'{merged.loc[difference.nlargest(5).index].to_string(index=False)}')


def test_optimized_matches_committed_reference() -> None:
    reference = load_reference()
    result = solve(RecoveryModelOptimized, CASE)
    assert len(result) == len(reference), (
        f'{len(result)} rows, reference has {len(reference)}')
    compare(result, reference, 'optimized', 'committed reference')


def test_LA_matches_committed_reference() -> None:
    reference = load_reference()
    result = solve(RecoveryModelLA, CASE)
    assert len(result) == len(reference), (
        f'{len(result)} rows, reference has {len(reference)}')
    compare(result, reference, 'LA', 'committed reference')


def test_engines_agree_on_basic_test() -> None:
    compare(solve(RecoveryModelOptimized, CASE), solve(RecoveryModelLA, CASE),
            'optimized', 'LA')


def test_no_intermediate_blowup() -> None:
    """
    Replay the process loop and watch the frame size -- the direct guard
    against defect 1.3, which was invisible in the output and only ever
    showed up as memory and time.
    """
    model = RecoveryModelOptimized(data_folder=CASE, layer_names=LAYER_NAMES,
                                   working_unit=REFERENCE_UNIT, years=REFERENCE_YEARS)
    entry = model.input_data[0]
    tcs = entry['tcs_df']
    result = model.create_initial_flows(inflows_df=entry['inflows_df'],
                                        composition_df=entry['composition_df'])

    peak = len(result)
    for _, step in model.get_process_sequence_from_tcs(tcs).iterrows():
        source, target = step['Input_FlowID'], step['Output_FlowID']
        inflow = result[result['Stock/Flow ID'] == source].drop(columns=['Stock/Flow ID'])
        step_tcs = tcs[(tcs['Input_FlowID'] == source) & (tcs['Output_FlowID'] == target)]
        outflow = model.solve_process(process_tcs=step_tcs, process_inflow=inflow)

        unmatched = outflow['Value'].isna().sum()
        assert unmatched == 0, (
            f'{source}->{target} produced {unmatched} NaN values. Unmatched TCs '
            f'are no longer being zero-filled -- this is defect 1.3 returning.')

        outflow['Stock/Flow ID'] = target
        result = pd.concat([result, outflow], ignore_index=True)
        peak = max(peak, len(result))

    assert peak <= MAX_INTERMEDIATE_ROWS, (
        f'peak intermediate frame reached {peak:,} rows, above the '
        f'{MAX_INTERMEDIATE_ROWS:,} bound. Expected 214 for this case; defect '
        f'1.3 reached 3,062,016.')


def test_documented_divergences_unchanged() -> None:
    """
    The known engine divergences, pinned at their documented magnitude.

    These assert current behaviour, not correct behaviour. Fixing one is
    supposed to break this -- update the expected value in the same commit.
    """
    for folder, expected in DOCUMENTED_DIVERGENCES.items():
        optimized = solve(RecoveryModelOptimized, folder)
        linear_algebra = solve(RecoveryModelLA, folder)
        merged = optimized.merge(linear_algebra, on=KEYS, how='outer',
                                 suffixes=('_optimized', '_LA')).fillna(
            {'Value_optimized': 0, 'Value_LA': 0})
        worst = (merged['Value_optimized'] - merged['Value_LA']).abs().max()
        assert abs(worst - expected) <= TOLERANCE, (
            f'{folder}: engines now differ by {worst:g}, documented value is '
            f'{expected:g}. If this is a fix, update DOCUMENTED_DIVERGENCES and '
            f'the matching section of documentation/DEFECTS.md in the same commit.')


def test_composition_closes_on_basic_test() -> None:
    """Every parent's composition shares sum to 1, at all three depths."""
    layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
    composition = pd.read_csv(f'{CASE}/input_data/composition.csv',
                              keep_default_na=False, na_values=[])
    composition['depth'] = (composition[layers] != '').sum(axis=1)

    for depth in sorted(composition['depth'].unique()):
        parent = ['Stock/ID'] + layers[:depth - 1]
        totals = composition[composition['depth'] == depth].groupby(parent)['Value'].sum()
        worst = (totals - 1).abs().max()
        assert worst <= TOLERANCE, (
            f'composition at depth {depth} does not close to 1: worst parent is '
            f'off by {worst:g}')


def _case_with(case: str = None, **edits):
    """
    A throwaway copy of a committed case with one table edited.

    Returns the folder. Used to prove the loader rejects what it is supposed to
    reject, without committing a data folder for every possible mistake.
    """
    import shutil
    import tempfile

    folder = tempfile.mkdtemp()
    shutil.copytree(f'{case or CASE}/input_data', f'{folder}/input_data',
                    dirs_exist_ok=True)
    for name, edit in edits.items():
        path = f'{folder}/input_data/{name.replace("_", ".")}'
        frame = pd.read_csv(path, keep_default_na=False, na_values=[])
        edit(frame).to_csv(path, index=False)
    return folder


def test_validation_accepts_every_committed_case() -> None:
    """No committed data folder may fail its own loader."""
    from src.validate_inputs import check

    folders = [CASE, 'data_folder/reference/template'] + list(DOCUMENTED_DIVERGENCES)
    for folder in folders:
        errors = [p for p in check(folder) if p.severity == 'ERROR']
        assert not errors, (
            f'{folder} does not pass validation:\n'
            + '\n'.join(str(problem) for problem in errors))




def test_a_process_keyed_at_an_empty_layer_is_refused() -> None:
    """
    HANDOVER.md section 5 -- the `child_layer` trap.

    Declaring the wrong child layer does not fail anywhere else: the reader
    files materials where elements belong, every element-keyed coefficient
    matches nothing, and the run still balances and still plots. The observable
    symptom is a process keyed at a layer the composition never fills, so that
    is what is checked -- built here by removing the element rows rather than
    by mis-declaring `child_layer`, so the test needs no upstream data.
    """
    from src.validate_inputs import check

    folder = _case_with(composition_csv=lambda f: f[f['Layer 4'] == ''])
    pd.DataFrame([
        dict(Input_FlowID='F1', Output_FlowID='F2', process='sorting',
             technology='manual', keyed_at='element', role='recovered'),
    ]).to_csv(f'{folder}/input_data/processes.csv', index=False)

    keyed = [p for p in check(folder)
             if p.severity == 'ERROR' and 'keyed at the' in p.message]
    assert keyed, 'a process keyed at a layer nothing fills was accepted'
    assert 'child_layer' in keyed[0].message, (
        'the error does not name the setting that causes it: ' + keyed[0].message)


def test_a_residual_that_could_go_negative_is_refused() -> None:
    """
    HANDOVER.md section 5 -- negative mass that still balances.

    A residual is `1 - the others`, so if the others can all be drawn high at
    once and sum past 1, the residual goes negative. It happened on 17 of 278
    resources in the first 04_01 table and was visible only afterwards, as a
    negative 2.5th percentile on a loss flow.

    The same arithmetic is FINE without a residual row -- conditioning enforces
    the constraint by weighting -- so the second half of this test insists the
    check stays quiet there. Refusing it would wrongly reject a measured case.
    """
    from src.validate_inputs import check

    from src.mass_balance import RESOURCE as KEY
    # reference/template rather than basic_test: this needs a resource reaching
    # THREE flows. With only two, one partner capped at 1 sums to exactly 1 and
    # the residual is pinned at 0 -- tight, but not negative and not a defect.
    TEMPLATE = 'data_folder/reference/template' 

    def widen(frame, residual: bool):
        frame = frame.copy()
        # Text, not floats: a residual row carries a blank bound, and a float
        # column will not take one.
        frame['value_min'] = frame['value'].astype(str)
        frame['value_max'] = frame['value'].astype(str)
        frame['is_residual'] = ''
        # The first group that actually splits: a resource reaching one flow
        # has no partners to sum past 1 with.
        sizes = frame.groupby(KEY, dropna=False).size()
        split = [name for name, count in sizes.items() if count > 1]
        assert split, 'fixture has no group with more than one row'
        group = frame.index[(frame[KEY] == pd.Series(split[0], index=KEY)).all(axis=1)]
        frame.loc[group[1:], 'value_max'] = '1.0'
        if residual:
            frame.loc[group[0], 'is_residual'] = '1'
            frame.loc[group[0], ['value_min', 'value_max']] = ''
        return frame

    found = [p for p in check(_case_with(TCs_csv=lambda f: widen(f, True), case=TEMPLATE))
             if p.severity == 'ERROR' and 'negative mass' in p.message]
    assert found, 'a residual that can be driven negative was accepted'

    quiet = [p for p in check(_case_with(TCs_csv=lambda f: widen(f, False), case=TEMPLATE))
             if 'negative mass' in p.message]
    assert not quiet, (
        'the same maxima were refused without a residual row, where conditioning '
        'handles them: ' + str(quiet[0]))


def test_a_range_restating_its_own_group_is_flagged() -> None:
    """
    HANDOVER.md section 5 -- one measurement counted twice.

    `1 - the rest of the group` looks like a second opinion and is not: the
    target becomes f(x)*f(x) and the answer narrows for no reason.

    Checked against `reference/template`, whose loss rows are exactly this --
    a real, documented instance rather than a fixture built to be caught. It
    must stay a WARNING: arithmetic cannot tell it from a genuine second
    measurement, only the `source` column can, so an error here would refuse
    tables that are merely unproven.
    """
    from src.validate_inputs import check

    flagged = [p for p in check('data_folder/reference/template')
               if 'already implies' in p.message]
    assert flagged, ("reference/template's loss rows restate their own groups, "
                     'and nothing said so')
    assert all(p.severity == 'WARNING' for p in flagged), (
        'this must warn, not refuse -- only the source column can tell it from '
        'a real second measurement')

    # And it must not fire where the ranges are genuinely independent.
    assert not [p for p in check(CASE) if 'already implies' in p.message], \
        'basic_test was flagged, so the check does not distinguish anything'



def _two_tables(improved_by: float = 0.2):
    """A two-row group and an improved version of it, for the ramp tests."""
    current = pd.DataFrame({
        'Input_FlowID': ['F1', 'F1'], 'Input_layer': ['product', 'product'],
        'Input_layer_key': ['BEV', 'BEV'],
        'Output_FlowID': ['F_recovered', 'F_loss'],
        'TC_target_layer': ['component', 'component'],
        'TC_target_key': ['Wiring', 'Wiring'],
        'value_min': [0.50, 0.20], 'value': [0.60, 0.40],
        'value_max': [0.70, 0.50]})
    improved = current.copy()
    improved[['value_min', 'value', 'value_max']] = [
        [0.50 + improved_by, 0.60 + improved_by, 0.70 + improved_by],
        [0.20 - improved_by, 0.40 - improved_by, 0.50 - improved_by]]
    return current, improved


def test_an_improvement_ramps_between_the_two_tables() -> None:
    """
    Current before the window, improved after it, a straight line between.

    The user's shape, 2026-09-03: 2020 and 2070 are the data, 2030 and 2060 the
    window. Before 2030 nothing has changed; by 2060 the improvement is fully
    in; after that it holds.
    """
    from src.case_tables import ramp

    current, improved = _two_tables()
    out = ramp(current, improved, start=2030, end=2060,
               years=[2020, 2030, 2045, 2060, 2070])
    recovered = out[out['Output_FlowID'] == 'F_recovered'].set_index('Year')

    for year, expected in (('2020', 0.60), ('2030', 0.60), ('2045', 0.70),
                           ('2060', 0.80), ('2070', 0.80)):
        got = float(recovered.loc[year, 'value'])
        assert abs(got - expected) < 1e-12, \
            f'{year}: value {got}, expected {expected}'

    # The bounds ramp too, or the improved situation would carry the current
    # one's uncertainty.
    assert abs(float(recovered.loc['2045', 'value_min']) - 0.60) < 1e-12
    assert abs(float(recovered.loc['2045', 'value_max']) - 0.80) < 1e-12


def test_a_ramped_group_still_sums_to_one_every_year() -> None:
    """
    Closure survives the ramp by construction, and is checked anyway.

    Each year is a convex combination of two tables whose groups sum to 1, and
    a convex combination of two such vectors sums to 1. Nothing renormalises,
    so if this ever failed it would mean the two tables did not close.
    """
    from src.case_tables import ramp

    current, improved = _two_tables()
    years = list(range(2020, 2075, 5))
    out = ramp(current, improved, start=2030, end=2060, years=years)
    totals = out.groupby('Year')['value'].sum()
    worst = float((totals - 1.0).abs().max())
    assert worst < 1e-12, f'a year does not close to 1: worst {worst:g}'
    assert len(totals) == len(years), 'a year went missing'


def test_one_draw_is_one_world_across_the_ramp() -> None:
    """
    THE PROPERTY THAT WOULD BREAK SILENTLY.

    Draw 7 has to be the same optimism about a process in 2030 and in 2060 --
    the improvement ramped, not two unrelated guesses. Independent draws per
    year would invent a year-to-year wobble nobody measured, and the answer
    would look plausible.

    It holds because `src/sampling._stream_key` is built from which resource
    moves from where to where and NOT from the year, so both years draw the
    same uniform. Checked by shifting the whole triangle by a constant: with
    one uniform, every draw must move by exactly the ramped shift.

    The group is deliberately left UNCONSTRAINED -- its modes sum to 0.8 -- so
    conditioning does not touch the values and the arithmetic is exact.
    """
    import numpy as np

    from src.case_tables import ramp
    from src.sampling import sample

    current, improved = _two_tables(improved_by=0.2)
    current['value'] = [0.60, 0.20]          # sums to 0.8: nothing to constrain
    improved['value'] = [0.80, 0.00]
    out = ramp(current, improved, start=2030, end=2060, years=[2030, 2060])

    early = out[out['Year'] == '2030'].reset_index(drop=True)
    late = out[out['Year'] == '2060'].reset_index(drop=True)
    assert not sample(early, draws=500)[1]['groups'], \
        'the fixture became constrained; conditioning would move the values'

    first, _ = sample(early, draws=2000, seed=0)
    second, _ = sample(late, draws=2000, seed=0)

    # Row 0's triangle moves +0.2 wholesale between the two years, so with one
    # uniform behind both, every single draw moves by exactly that.
    shift = second[0] - first[0]
    assert np.allclose(shift, 0.2, atol=1e-9), (
        'the same coefficient drew different uniforms in two years -- one draw '
        f'is no longer one world. Shift ranged {shift.min():.4f} to '
        f'{shift.max():.4f}, expected 0.2 throughout.')


def test_validation_rejects_unknown_keys() -> None:
    """DEFECTS.md §2.7 -- the phantom-mass and unreadable-TypeError case."""
    from src.validate_inputs import InputDataError, validate

    def unknown_product(frame):
        row = frame.iloc[[0]].copy()
        row['Substance_main_parent'] = 'P9'
        return pd.concat([frame, row], ignore_index=True)

    def unknown_flow(frame):
        row = frame.iloc[[0]].copy()
        row['Stock/Flow ID'] = 'FZZ'
        return pd.concat([frame, row], ignore_index=True)

    for edit, expected in ((unknown_product, 'P9'), (unknown_flow, 'FZZ')):
        try:
            validate(_case_with(inputs_csv=edit))
        except InputDataError as error:
            assert expected in str(error), f'error does not name {expected}: {error}'
        else:
            raise AssertionError(f'an inflow naming {expected} was accepted')


def test_validation_rejects_a_composition_row_with_a_hole() -> None:
    """DEFECTS.md §2.6 -- the row that invents its own product's mass."""
    from src.validate_inputs import InputDataError, validate

    def layer_one_only(frame):
        row = frame.iloc[[0]].copy()
        row[['Layer 2', 'Layer 3', 'Layer 4']] = ''
        row['Value'] = 1.0
        return pd.concat([frame, row], ignore_index=True)

    try:
        validate(_case_with(composition_csv=layer_one_only))
    except InputDataError as error:
        assert 'composition.csv' in str(error)
    else:
        raise AssertionError('a composition row with only Layer 1 was accepted')


def test_validation_rejects_bad_units() -> None:
    """
    DEFECTS.md §3.3. The model never reads the unit, so a wrong one is wrong by
    a clean factor of 1000 with nothing in the output to show for it.
    """
    from src.validate_inputs import InputDataError, validate

    def mixed(frame):
        frame = frame.copy()
        frame['Unit'] = ['Mg'] + ['kg'] * (len(frame) - 1)
        return frame

    def nonsense(frame):
        frame = frame.copy()
        frame['Unit'] = 'bananas'
        return frame

    for edit, description in ((mixed, 'two units in one file'),
                              (nonsense, 'an unrecognised unit')):
        try:
            validate(_case_with(inputs_csv=edit))
        except InputDataError as error:
            assert 'Unit' in str(error)
        else:
            raise AssertionError(f'{description} was accepted')


def test_overlapping_rules_resolve_to_the_specific_one() -> None:
    """
    DEFECTS.md §2.3. Two rules cover the harness in a BEV: one naming BEV at
    0.80, one naming no product at 0.20. The row naming the parent governs.

    Pinned as masses rather than as an engine difference, because the numbers
    are the point: 800 t of BEV harness at 0.80 is 640 t, and the hybrid's
    3000 t at 0.20 is 600 t. Adding the rules instead gives 800 t -- the whole
    harness, perfectly recovered, which is what the optimized engine used to
    report.
    """
    folder = 'data_folder/reference/defect_cases/overlapping_rules'
    expected = {('F2_dismantled', 'BEV', 'Harness'): 640.0,
                ('F2_dismantled', 'HEV', 'Harness'): 600.0}

    for engine in (RecoveryModelOptimized, RecoveryModelLA):
        solution = solve(engine, folder)
        for (flow, product, component), mass in expected.items():
            rows = solution[(solution['Stock/Flow ID'] == flow)
                            & (solution['Layer 1'] == product)
                            & (solution['Layer 2'] == component)
                            & (solution['Layer 3'] == '')]
            assert len(rows) == 1, f'{engine.__name__}: {flow}/{product}/{component} not found'
            got = float(rows['Value'].iloc[0])
            assert abs(got - mass) <= TOLERANCE, (
                f'{engine.__name__}: {component} in {product} is {got:g}, expected {mass:g}')


def test_scenario_is_matched_exactly() -> None:
    """
    DEFECTS.md §2.4. One inflow in scenario 'BAU', and TC rows for 'BAU' at
    0.30 and 'BAU_high' at 0.90. Only the BAU row applies, so 100 t gives 30 t.

    The LA engine used to select with str.contains, so 'BAU' also matched
    'BAU_high' and it returned 90 t -- silently running a different scenario
    than the one asked for.
    """
    folder = 'data_folder/reference/defect_cases/scenario_prefix'
    for engine in (RecoveryModelOptimized, RecoveryModelLA):
        solution = solve(engine, folder)
        rows = solution[(solution['Stock/Flow ID'] == 'F2')
                        & (solution['Layer 2'] == 'C1')
                        & (solution['Layer 3'] == '')]
        assert len(rows) == 1, f'{engine.__name__}: F2/P1/C1 not found'
        got = float(rows['Value'].iloc[0])
        assert abs(got - 30.0) <= TOLERANCE, (
            f'{engine.__name__}: got {got:g}, expected 30 -- 90 means the '
            f'BAU_high row was matched as well')


def test_a_scenario_must_be_chosen() -> None:
    """
    One run is one scenario. Where the data holds scenarios and none is
    chosen, the run stops and lists them rather than solving all of them --
    which used to write each scenario's output over the last one's.
    """
    from src.validate_inputs import InputDataError

    folder = 'data_folder/reference/defect_cases/scenario_prefix'
    try:
        RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                               scenario='', years=REFERENCE_YEARS)
    except InputDataError as error:
        assert 'BAU' in str(error), f'error does not list what it found: {error}'
    else:
        raise AssertionError('a case with scenarios ran without one being chosen')

    try:
        RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                               scenario='not_a_scenario', years=REFERENCE_YEARS)
    except InputDataError as error:
        assert 'not_a_scenario' in str(error)
    else:
        raise AssertionError('an unknown scenario name was accepted')


def test_years_can_be_narrowed() -> None:
    """
    A run covers every year in the data, one year, a range, or a range
    thinned by a step -- real inflow data is annual over ~50 years, so a step
    is usually what is wanted.

    Not just convenience: 200,000 draws x 96 years is the memory problem in
    DESIGN_monte_carlo.md §2, and the year axis is the most direct lever on it.
    """
    from src.validate_inputs import InputDataError

    folder = 'data_folder/reference/defect_cases/year_range'   # annual, 2020 to 2070
    expected = {
        '': [str(y) for y in range(2020, 2071)],
        '2040': ['2040'],
        '2030-2035': [str(y) for y in range(2030, 2036)],
        ',10': ['2020', '2030', '2040', '2050', '2060', '2070'],
        '2030-2070,10': ['2030', '2040', '2050', '2060', '2070'],
    }

    for engine in (RecoveryModelOptimized, RecoveryModelLA):
        for setting, wanted in expected.items():
            model = engine(data_folder=folder, layer_names=LAYER_NAMES, years=setting)
            solution = model.solve_models_and_write_to_output()
            got = sorted(str(year) for year in solution['Year'].unique())
            assert got == wanted, (
                f'{engine.__name__} with years={setting!r}: got {got}, '
                f'expected {wanted}')

    for bad, why in (('1999', 'a year matching nothing'), ('2030-2050,0', 'a step of zero')):
        try:
            RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES, years=bad)
        except InputDataError as error:
            assert bad.split(',')[0] in str(error) or '0' in str(error)
        else:
            raise AssertionError(f'{why} was accepted')


def test_validation_rejects_a_same_layer_transformation() -> None:
    """
    DEFECTS.md §2.5. A transfer within one layer carries a resource unchanged,
    so its two keys must name the same resource.

    Uses the committed case rather than a temporary one, because the point of
    that folder is to hold an input the loader must refuse.
    """
    from src.validate_inputs import InputDataError, validate

    try:
        validate('data_folder/reference/defect_cases/same_layer_key')
    except InputDataError as error:
        assert "'C1' -> 'C2'" in str(error), f'error does not name both keys: {error}'
    else:
        raise AssertionError("a same-layer TC reading C1 -> C2 was accepted")


def test_validation_rejects_percentages() -> None:
    """A share written as 25 rather than 0.25 inflates the answer 100-fold."""
    from src.validate_inputs import InputDataError, validate

    def as_percentage(frame):
        frame = frame.copy()
        frame.loc[0, 'Value'] = 25.0
        return frame

    try:
        validate(_case_with(composition_csv=as_percentage))
    except InputDataError as error:
        assert 'fraction' in str(error)
    else:
        raise AssertionError('a composition share of 25 was accepted')


# ----------------------------------------------------------------------
#  The LA engine must give the same answer in every process
# ----------------------------------------------------------------------

# Run in a subprocess because PYTHONHASHSEED is read once at interpreter start.
# Inside one process the set iteration order is already fixed, so no test that
# stays here can see the defect this guards.
_REPRODUCIBILITY_PROBE = """
import hashlib, os, sys
sys.path.insert(0, os.getcwd())
from src.recovery_model_LA import RecoveryModelLA
model = RecoveryModelLA(data_folder='data_folder/reference/basic_test',
                        layer_names=['product', 'component', 'material', 'element'],
                        working_unit='Mg', years='')
frame = model.solve_models_and_write_to_output()
frame = frame.sort_values(list(frame.columns)).reset_index(drop=True)
values = frame['Value'].astype(float).to_numpy()
print(hashlib.sha256(values.tobytes()).hexdigest())
print(','.join(model.decoding_dict['Stock/Flow ID'].values()))
"""


def _solve_under_hash_seed(seed: str) -> tuple[str, str]:
    """(hash of the solution's values, the flow encoding order) in a fresh process."""
    import subprocess

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    finished = subprocess.run(
        [sys.executable, '-c', _REPRODUCIBILITY_PROBE], cwd=root, text=True,
        capture_output=True, env=dict(os.environ, PYTHONHASHSEED=seed))
    assert finished.returncode == 0, \
        f'the probe failed under PYTHONHASHSEED={seed}:\n{finished.stderr[-800:]}'
    lines = finished.stdout.strip().splitlines()
    return lines[-2], lines[-1]


def test_LA_gives_the_same_answer_in_every_process() -> None:
    """
    The LA engine encoded flows and resources with `list(set(...))`, whose order
    depends on Python's per-process hash randomisation. That changed the
    ordering of the sparse system, and with it the floating-point accumulation
    order in `spsolve` -- so the same input gave different last bits in
    different processes. Measured before the fix: three seeds gave three
    different encodings and two different result hashes.

    About 1.5 ULP, so it never mattered for an answer. It mattered because the
    LA engine is the independent oracle the optimized engine is checked
    against, and an oracle that will not repeat itself cannot settle an
    argument about the last digit.
    """
    first_hash, first_order = _solve_under_hash_seed('1')
    second_hash, second_order = _solve_under_hash_seed('2')

    assert first_order == second_order, (
        'the flow encoding depends on hash randomisation:\n'
        f'  seed 1: {first_order}\n  seed 2: {second_order}')
    assert first_hash == second_hash, (
        'the LA engine produced different values in two processes:\n'
        f'  seed 1: {first_hash}\n  seed 2: {second_hash}')


# ----------------------------------------------------------------------
#  A composition row that describes nothing must contribute nothing
# ----------------------------------------------------------------------

def _one_product_composition(extra: list[dict] | None = None) -> tuple:
    """1000 of P1 in F1, split 60/40 between two components."""
    inflows = pd.DataFrame([{'Stock/Flow ID': 'F1',
                             'Substance_main_parent': 'P1', 'Value': 1000.0}])
    rows = [
        {'Stock/ID': 'F1', 'Layer 1': 'P1', 'Layer 2': 'C1',
         'Layer 3': '', 'Layer 4': '', 'Value': 0.6},
        {'Stock/ID': 'F1', 'Layer 1': 'P1', 'Layer 2': 'C2',
         'Layer 3': '', 'Layer 4': '', 'Value': 0.4},
    ]
    return inflows, pd.DataFrame(rows + (extra or []))


def _depths(frame: pd.DataFrame) -> pd.Series:
    return (frame[['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']] != '').sum(axis=1)


def test_a_layer_1_only_composition_row_invents_no_mass() -> None:
    """
    The product-to-component filter asked only that Layer 3 and Layer 4 be
    empty, never that Layer 2 be filled. A row with Layer 1 alone therefore
    passed it, merged on Layer 1, and duplicated the product row -- so the
    shallowest depth, which is where a flow's own total is read
    (MODEL_MECHANICS.md section 1), held 2000 against an inflow of 1000.

    Exactly the mass of F1/P1, created by a row that says nothing. The LA
    engine was never affected, which is what made it findable.

    `src/validate_inputs.py` has refused such a row at the file since
    2026-08-17, so this is tested against the function rather than a case
    folder: the guard would stop the input long before the filter saw it, and
    the filter is what is under test.
    """
    inflows, plain = _one_product_composition()
    baseline = RecoveryModelOptimized.create_initial_flows(inflows, plain)
    shallow = baseline[_depths(baseline) == 1]['Value'].sum()
    assert abs(shallow - 1000.0) < 1e-9, f'baseline already wrong: {shallow}'

    inflows, with_empty = _one_product_composition(
        [{'Stock/ID': 'F1', 'Layer 1': 'P1', 'Layer 2': '',
          'Layer 3': '', 'Layer 4': '', 'Value': 1.0}])
    result = RecoveryModelOptimized.create_initial_flows(inflows, with_empty)

    shallow = result[_depths(result) == 1]['Value'].sum()
    assert abs(shallow - 1000.0) < 1e-9, (
        f'a Layer-1-only composition row added mass: {shallow} against an '
        f'inflow of 1000')
    assert len(result) == len(baseline), (
        f'{len(result)} rows with the empty row present, {len(baseline)} '
        f'without -- it should contribute nothing')


def test_a_composition_row_with_a_gap_contributes_nothing() -> None:
    """
    The same under-constraint one layer down: the filters checked the tail of
    each row and never its prefix, so a row with Layer 3 filled and Layer 2
    empty would be treated as a component-to-material share of nothing.
    """
    inflows, with_gap = _one_product_composition(
        [{'Stock/ID': 'F1', 'Layer 1': 'P1', 'Layer 2': '',
          'Layer 3': 'M1', 'Layer 4': '', 'Value': 1.0}])
    result = RecoveryModelOptimized.create_initial_flows(inflows, with_gap)

    assert not len(result[(result['Layer 2'] == '') & (result['Layer 3'] != '')]), \
        'a row with a gap produced output at material depth'
    total = result[_depths(result) == 1]['Value'].sum()
    assert abs(total - 1000.0) < 1e-9, f'mass changed to {total}'


# ----------------------------------------------------------------------
#  An unknown key must be named, not hit as a TypeError deep in numpy
# ----------------------------------------------------------------------

def test_the_LA_engine_names_an_unknown_key() -> None:
    """
    The LA engine encoded every key with `.replace(mapping)`, which leaves an
    unmapped value as the original STRING. That string then reached
    `ravel_multi_index`'s arithmetic and failed as

        TypeError: unsupported operand type(s) for +: 'int' and 'str'

    naming neither the column, the value, nor the file. `.map()` yields NaN for
    a miss, which can be reported properly.

    `src/validate_inputs.py` has refused an unknown key since 2026-08-17, so
    this calls the encoder directly: the guard runs in the constructor and the
    encoder is what was wrong. It is worth fixing behind the guard because a
    guard that is bypassed -- by a caller handing tables over in memory, or by
    a key that becomes unknown only after wildcard expansion -- lands back on
    this message.
    """
    model = RecoveryModelLA(data_folder=CASE, layer_names=LAYER_NAMES,
                            working_unit=REFERENCE_UNIT, years=REFERENCE_YEARS)
    inflows = pd.read_csv(f'{CASE}/input_data/inputs.csv',
                          keep_default_na=False, na_values=[])
    poisoned = inflows.copy()
    poisoned.loc[0, 'Substance_main_parent'] = 'NOT_A_PRODUCT'

    try:
        model.create_inflows_vector(
            poisoned, year=str(inflows['Year'].iloc[0]), scenario=None,
            location=None, additional_specification=None)
    except TypeError as error:
        raise AssertionError(
            f'still failing inside numpy with an unreadable message: {error}')
    except Exception as error:
        message = str(error)
        assert 'NOT_A_PRODUCT' in message, \
            f'the offending value is not named:\n{message}'
        assert 'product' in message, \
            f'the column is not named:\n{message}'
    else:
        raise AssertionError('an unknown key was encoded without complaint')


# ----------------------------------------------------------------------
#  One sparse API, not two
# ----------------------------------------------------------------------

def test_the_LA_engine_builds_only_sparse_arrays() -> None:
    """
    `create_sparse_matrix` built a legacy `coo_matrix(...).tocsr()` -- the
    `spmatrix` branch -- while `solve_model` combined the result with
    `eye_array` from the newer sparse ARRAY API, and every type hint claimed
    `csr_array`, which is not what came back.

    It worked. The reason to care is that the two APIs differ in operator
    semantics -- `*` is matrix multiplication for `spmatrix` and elementwise
    for `sparray` -- so a mix is a trap for whoever edits this next, and the
    hints pointed the wrong way for anyone checking.
    """
    import numpy as np
    from scipy import sparse

    from src.recovery_model_LA import HelperFunctions

    matrix = HelperFunctions.create_sparse_matrix(
        np.array([1.0, 2.0]), np.array([0, 1]), np.array([1, 2]), 3)
    vector = HelperFunctions.create_vector(np.array([3.0]), np.array([1]), 3)

    for name, built in (('create_sparse_matrix', matrix),
                        ('create_vector', vector)):
        assert isinstance(built, sparse.sparray), (
            f'{name} returned {type(built).__name__}, which is the spmatrix '
            f'branch; the rest of this engine uses the sparse array API')

    assert matrix.shape == (3, 3), matrix.shape
    assert vector.shape == (3, 1), vector.shape
    assert matrix.toarray()[0, 1] == 1.0 and matrix.toarray()[1, 2] == 2.0
    assert vector.toarray()[1, 0] == 3.0


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
