"""
Pin the handling of incomplete composition -- the `rest` child.

    ./.venv/bin/python test_rest.py

Real composition data is incomplete in a particular way: the copper in a wire
is known, the wire's own weight is not. The rule is that a parent is the sum of
its known children plus a rest, so that closure to one holds at every layer and
the unspecified part is a row rather than an absence.

The test that matters is `test_partial_composition_closes_after_rest`. Before
this existed, a laminate parent read 400 with children summing to 340 and the
missing 60 had no row at all -- nothing on the page was wrong, the mass was
simply gone.
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
import shutil
import sys
import tempfile
import traceback

import numpy as np
import pandas as pd


from src.recovery_model_optimized import RecoveryModelOptimized
from src.rest import REST, LAYERS, RestError, add_rest, is_rest, stranded

NAMES = ['product', 'component', 'material', 'element']
SOURCE = 'data_folder/reference/template/input_data'


def _case(drop_element: str | None = None) -> str:
    """A copy of `template`, optionally with one element's rows removed."""
    folder = tempfile.mkdtemp()
    os.makedirs(f'{folder}/input_data')
    shutil.copy(f'{SOURCE}/inputs.csv', f'{folder}/input_data/')

    read = dict(keep_default_na=False, na_values=[])
    composition = pd.read_csv(f'{SOURCE}/composition.csv', **read)
    tcs = pd.read_csv(f'{SOURCE}/TCs.csv', **read)
    if drop_element:
        composition = composition[composition['Layer 4'] != drop_element]
        tcs = tcs[tcs['TC_target_key'] != drop_element]
    composition.to_csv(f'{folder}/input_data/composition.csv', index=False)
    tcs.to_csv(f'{folder}/input_data/TCs.csv', index=False)
    return folder


def _solve(folder: str) -> pd.DataFrame:
    solution = RecoveryModelOptimized(
        data_folder=folder, layer_names=NAMES, working_unit='Mg', years=''
    ).solve_models_and_write_to_output()
    solution['Value'] = pd.to_numeric(solution['Value'])
    return solution


def test_complete_composition_gets_no_rest() -> None:
    """`template` closes to 1 everywhere, so nothing should be added."""
    composition = pd.read_csv(f'{SOURCE}/composition.csv',
                              keep_default_na=False, na_values=[])
    with_rest, notes = add_rest(composition)
    assert not notes, f'a complete composition had rest derived: {notes}'
    assert len(with_rest) == len(composition), 'rows were added to a complete table'


def test_partial_composition_gets_a_rest_per_short_parent() -> None:
    """Removing gold leaves two parents short, so two rests are derived."""
    composition = pd.read_csv(f'{SOURCE}/composition.csv',
                              keep_default_na=False, na_values=[])
    partial = composition[composition['Layer 4'] != 'Au']
    with_rest, notes = add_rest(partial)

    assert len(notes) == 2, f'expected 2 rests, got {len(notes)}: {notes}'
    rests = with_rest[with_rest['Layer 4'] == REST]
    assert len(rests) == 2, 'rest rows were not appended'
    shares = sorted(rests['Value'].round(6))
    assert shares == [0.02, 0.15], f'rest shares are {shares}, expected [0.02, 0.15]'


def test_every_parent_closes_to_one_after_rest() -> None:
    """The rule itself: known children plus rest is the whole, at every layer."""
    composition = pd.read_csv(f'{SOURCE}/composition.csv',
                              keep_default_na=False, na_values=[])
    partial = composition[composition['Layer 4'] != 'Au']
    with_rest, _ = add_rest(partial)

    depth = (with_rest[LAYERS] != '').sum(axis=1)
    for level in (2, 3, 4):
        at_level = with_rest[depth == level]
        if at_level.empty:
            continue
        parent = ['Stock/ID'] + LAYERS[:level - 1]
        totals = at_level.groupby(parent)['Value'].sum()
        worst = float(np.max(np.abs(totals - 1.0)))
        assert worst < 1e-9, f'depth {level} closes to 1 +/- {worst:.3e}'


def test_partial_composition_closes_after_rest() -> None:
    """
    End to end. The 60 kg that used to have no row is now a row, and the
    laminate's children sum to the laminate.
    """
    solution = _solve(_case(drop_element='Au'))
    inflow = solution[solution['Stock/Flow ID'] == 'F1_collected']
    laminate = inflow[inflow['Layer 3'] == 'Laminate']

    parent = float(laminate[laminate['Layer 4'] == '']['Value'].sum())
    children = float(laminate[laminate['Layer 4'] != '']['Value'].sum())
    assert abs(parent - children) < 1e-9, \
        f'laminate parent {parent:g}, children {children:g} -- {parent - children:g} unaccounted'

    rest_row = laminate[laminate['Layer 4'] == REST]
    assert len(rest_row) == 1 and abs(float(rest_row['Value'].iloc[0]) - 60.0) < 1e-9, \
        'the missing 60 did not appear as a rest row'


def test_parts_exceeding_the_whole_are_refused() -> None:
    """A rest cannot be negative, so shares summing past 1 must raise."""
    composition = pd.read_csv(f'{SOURCE}/composition.csv',
                              keep_default_na=False, na_values=[])
    broken = composition.copy()
    broken.loc[broken['Layer 4'] == 'Cu', 'Value'] = 0.99   # 0.99 + 0.15 > 1
    try:
        add_rest(broken)
    except RestError as error:
        assert 'more than the whole' in str(error), f'unhelpful message: {error}'
    else:
        raise AssertionError('shares summing past 1 were accepted')


def test_reserved_name_is_refused() -> None:
    """A real resource called 'rest' would be merged with the derived one."""
    composition = pd.read_csv(f'{SOURCE}/composition.csv',
                              keep_default_na=False, na_values=[])
    collides = composition.copy()
    collides.loc[collides['Layer 4'] == 'Au', 'Layer 4'] = REST
    try:
        add_rest(collides)
    except RestError as error:
        assert 'reserved' in str(error), f'unhelpful message: {error}'
    else:
        raise AssertionError("a resource named 'rest' was accepted")


def test_rest_rides_along_coarse_coefficients() -> None:
    """
    A component-level coefficient carries the whole subtree, so rest reaches
    the dismantled flow without needing coefficients of its own. This is why
    generating rest coefficients automatically would double-count.
    """
    solution = _solve(_case(drop_element='Au'))
    dismantled = solution[(solution['Stock/Flow ID'] == 'F2_dismantled')
                          & is_rest(solution)]
    assert len(dismantled), 'rest did not ride along the dismantling coefficients'
    assert float(dismantled['Value'].sum()) > 0, 'rest arrived with no mass'


def test_stranded_rest_is_detected() -> None:
    """
    Rest stops at the first process keyed finer than itself, and then sits in an
    intermediate flow where totalling the terminal flows never sees it. That has
    to be reported, not left silent.
    """
    folder = _case(drop_element='Au')
    model = RecoveryModelOptimized(data_folder=folder, layer_names=NAMES,
                                   working_unit='Mg', years='')
    solution = model.solve_models_and_write_to_output()
    solution['Value'] = pd.to_numeric(solution['Value'])
    # The model's own coefficient table, layers already renamed. The raw CSV
    # still says 'component'/'element', which the join would not match.
    tcs = model.input_data[0]['tcs_df']

    stalled = stranded(solution, tcs)
    assert len(stalled), 'stranded rest was not detected'

    total = float(stalled['Value'].sum())
    assert abs(total - 68.4) < 0.1, f'stranded mass is {total:g}, expected about 68.4'
    assert set(stalled['Stock/Flow ID']) == {'F2_dismantled', 'F3_shredded'}, \
        f"stranded in unexpected flows: {sorted(set(stalled['Stock/Flow ID']))}"


def test_nothing_strands_when_composition_is_complete() -> None:
    """The companion: a complete table has no rest, so nothing can strand."""
    folder = _case()
    model = RecoveryModelOptimized(data_folder=folder, layer_names=NAMES,
                                   working_unit='Mg', years='')
    solution = model.solve_models_and_write_to_output()
    solution['Value'] = pd.to_numeric(solution['Value'])
    assert not len(stranded(solution, model.input_data[0]['tcs_df'])), \
        'a complete composition produced stranded rest'


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
