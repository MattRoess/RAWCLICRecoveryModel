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
4. The three documented engine divergences still diverge by exactly the
   documented amount. This pins current semantics rather than correct ones:
   fixing DEFECTS.md §2.1, §2.2 or §2.5 SHOULD make check 4 fail, at which
   point the expected value here is updated deliberately, in the same commit
   as the fix. A silent change is what this is here to prevent.
"""
from __future__ import annotations

import sys
import traceback

import pandas as pd

from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

LAYER_NAMES = ['product', 'component', 'material', 'element']
KEYS = ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

CASE = 'data_folder/basic_test'
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
# composition_stock_id and wildcard_star were 100.0 and 50.0 until 2026-08-17,
# when DEFECTS.md §2.1 and §2.2 were fixed in the optimized engine; they are
# now zero and this test is what holds them there. tc_specificity is §2.3, an
# unspecified semantic that needs a method decision before it can be fixed, so
# its 50.0 still pins current behaviour rather than correct behaviour.
DOCUMENTED_DIVERGENCES = {
    'data_folder/defect_cases/composition_stock_id': 0.0,
    'data_folder/defect_cases/wildcard_star': 0.0,
    'data_folder/defect_cases/tc_specificity': 50.0,
}


def solve(engine, folder: str) -> pd.DataFrame:
    model = engine(data_folder=folder, layer_names=LAYER_NAMES)
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
    model = RecoveryModelOptimized(data_folder=CASE, layer_names=LAYER_NAMES)
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

    folders = [CASE, 'data_folder/template'] + list(DOCUMENTED_DIVERGENCES)
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


def test_validation_rejects_a_same_layer_transformation() -> None:
    """
    DEFECTS.md §2.5. A transfer within one layer carries a resource unchanged,
    so its two keys must name the same resource.

    Uses the committed case rather than a temporary one, because the point of
    that folder is to hold an input the loader must refuse.
    """
    from src.validate_inputs import InputDataError, validate

    try:
        validate('data_folder/defect_cases/same_layer_key')
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
