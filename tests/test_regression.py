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
import traceback

import pandas as pd

# tests/ is not the repo root, so put the root on the path before
# importing src.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

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


def solve(engine, folder: str) -> pd.DataFrame:
    model = engine(data_folder=folder, layer_names=LAYER_NAMES,
                   scenario=SCENARIO_FOR.get(folder),
                   working_unit=REFERENCE_UNIT)
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
                                   working_unit=REFERENCE_UNIT)
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


def _case_with(**edits):
    """
    A throwaway copy of basic_test with one table edited.

    Returns the folder. Used to prove the loader rejects what it is supposed to
    reject, without committing a data folder for every possible mistake.
    """
    import shutil
    import tempfile

    folder = tempfile.mkdtemp()
    shutil.copytree(f'{CASE}/input_data', f'{folder}/input_data', dirs_exist_ok=True)
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
        RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES, scenario='')
    except InputDataError as error:
        assert 'BAU' in str(error), f'error does not list what it found: {error}'
    else:
        raise AssertionError('a case with scenarios ran without one being chosen')

    try:
        RecoveryModelOptimized(data_folder=folder, layer_names=LAYER_NAMES,
                               scenario='not_a_scenario')
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
