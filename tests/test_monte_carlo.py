"""
Check that the Monte Carlo engine solves the same model as the deterministic one.

    ./.venv/bin/python test_monte_carlo.py

Plain asserts and no test framework, matching test_regression.py.

THE TEST THAT MATTERS
---------------------
`test_zero_width_ranges_reproduce_the_deterministic_answer`. A range of zero
width is a point mass at the mode, so a Monte Carlo over such a table must
return the deterministic answer -- not close to it, exactly it. That single
check covers the whole chain: the composition cascade, the process order, the
join, the multiplication and the final grouping. If any of them differs from
the deterministic engine, this fails.

The rest check the claims the engine makes on top of that: that chunking is
safe, that a constrained table conserves mass on every draw, and that the
nesting invariant survives sampling.
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


from src.monte_carlo import solve_draws
from src.recovery_model_optimized import RecoveryModelOptimized

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
KEYS = ['Year', 'Stock/Flow ID'] + LAYERS
NAMES = ['product', 'component', 'material', 'element']


def _deterministic(case: str) -> pd.DataFrame:
    solution = RecoveryModelOptimized(
        data_folder=f'data_folder/reference/{case}', layer_names=NAMES, years=''
    ).solve_models_and_write_to_output()
    solution['Value'] = pd.to_numeric(solution['Value'])
    solution['Year'] = solution['Year'].astype(str)
    return solution


def _monte_carlo(case: str, draws: int = 500, **kwargs):
    kwargs.setdefault('years', '')
    run = solve_draws(f'data_folder/reference/{case}', NAMES, draws=draws, **kwargs)
    run.keys['Year'] = run.keys['Year'].astype(str)
    return run.keys, run.values, run.report


def test_zero_width_ranges_reproduce_the_deterministic_answer() -> None:
    """
    A table whose ranges have no width must give the deterministic answer
    exactly. This is the identity check on the whole engine.

    `basic_test` has no range columns at all, which is the same thing: every
    draw is the stated coefficient.
    """
    determined = _deterministic('basic_test')
    keys, values, report = _monte_carlo('basic_test', draws=16)

    assert not report['uncertain'], 'basic_test has no ranges but was treated as uncertain'
    assert np.all(values == values[:, [0]]), 'a table without ranges varied between draws'

    merged = determined.merge(keys.assign(mc=values[:, 0]), on=KEYS, how='left')
    assert merged['mc'].notna().all(), \
        f"{int(merged['mc'].isna().sum())} deterministic rows are missing from the Monte Carlo"
    worst = np.max(np.abs(merged['Value'] - merged['mc']))
    assert worst < 1e-12, f'Monte Carlo differs from the deterministic answer by {worst:.3e}'


def test_template_with_ranges_collapsed_matches_deterministic() -> None:
    """
    The same identity check on `template`, whose ranges are collapsed onto the
    mode. This one exercises the constrained groups as well.
    """
    determined = _deterministic('template')

    import src.sampling as sampling
    original = sampling.clamp_bounds

    def collapse(tcs):
        tcs = tcs.copy()
        tcs['value_min'] = tcs['value']
        tcs['value_max'] = tcs['value']
        return original(tcs)

    sampling.clamp_bounds = collapse
    try:
        keys, values, _ = _monte_carlo('template', draws=16)
    finally:
        sampling.clamp_bounds = original

    assert np.allclose(values, values[:, [0]]), 'collapsed ranges still varied between draws'
    merged = determined.merge(keys.assign(mc=values[:, 0]), on=KEYS, how='left')
    assert merged['mc'].notna().all(), 'deterministic rows missing from the Monte Carlo'
    worst = np.max(np.abs(merged['Value'] - merged['mc']))
    assert worst < 1e-10, f'collapsed Monte Carlo differs by {worst:.3e}'


def test_the_chunk_setting_cannot_change_the_answer() -> None:
    """
    `chunk` is memory tuning and must not touch the result, under either rule.

    That is why the coefficients are drawn at full width, once, before anything
    is evaluated in blocks: conditioning resamples within whatever set it is
    handed, so drawing per block would have made the answer depend on a number
    chosen from `memory_budget_gb`.
    """
    for rule in ('normalise', 'condition'):
        _, whole, _ = _monte_carlo('template', draws=300, chunk=300, rule=rule)
        _, blocked, _ = _monte_carlo('template', draws=300, chunk=7, rule=rule)
        worst = np.max(np.abs(whole - blocked))
        assert worst == 0.0, \
            f'{rule}: the chunk size moved the answer by {worst:.3e}'


def test_a_result_on_disk_is_the_same_result() -> None:
    """
    THE PATH ADDED 2026-09-04, AND IT IS THE ONE NOBODY WOULD NOTICE BREAKING.

    A result larger than `memory_budget_gb` is memory-mapped to a file instead
    of the run being refused, which is what lets the boards case run at every
    year: 16.6 GB of draws on a 17 GB machine. The danger is that it works and
    is silently WRONG -- a memmap that is not flushed, or a dtype that differs
    from the in-memory array, gives plausible numbers nobody checks.

    So: the same run, once in memory and once forced onto disk by a budget of
    almost nothing, must agree to the last bit. The file must also be gone
    afterwards, since it is one run's draws and worthless once summarised.
    """
    import os

    from src.monte_carlo import solve_draws

    resident = solve_draws(f'data_folder/reference/template', NAMES, draws=200,
                           seed=0, budget_gb=1e9)
    on_disk = solve_draws(f'data_folder/reference/template', NAMES, draws=200,
                          seed=0, budget_gb=1e-9)

    assert on_disk.backing is not None, \
        'a budget of a nanogram should have forced the result onto disk'
    assert os.path.exists(on_disk.backing), 'the backing file was not created'

    worst = float(np.max(np.abs(np.asarray(resident.values)
                                - np.asarray(on_disk.values))))
    assert worst == 0.0, f'the result on disk differs by {worst:.3e}'

    path = on_disk.backing
    on_disk.close()
    assert not os.path.exists(path), f'{path} was left behind after close()'
    on_disk.close()          # twice must be harmless


def test_a_run_repeats_exactly_at_the_same_width_and_seed() -> None:
    """
    What the stable draw index is actually for: two runs at the same width and
    seed must agree value for value, so a comparison between two scenarios
    shows the scenario rather than the noise.
    """
    for rule in ('normalise', 'condition'):
        _, once, _ = _monte_carlo('template', draws=300, seed=0, rule=rule)
        _, twice, _ = _monte_carlo('template', draws=300, seed=0, rule=rule)
        assert np.max(np.abs(once - twice)) == 0.0, f'{rule} did not repeat'


def test_splitting_a_run_composes_only_when_normalising() -> None:
    """
    Under 'normalise', draw i is fixed by its own stream, so a run split into
    two calls reproduces an unsplit one value for value.

    Under 'condition' it cannot, and this pins that down rather than leaving it
    to be discovered. The group is resampled within whatever set it is given,
    so a 100-draw call and a 200-draw call are not the two halves of a 300-draw
    one. Each is a valid sample of the same distribution; they are not the SAME
    sample. Nothing in the pipeline splits a run this way -- `chunk` does not,
    as the test above shows -- but anyone reaching for `start` should know.
    """
    def split(rule: str) -> float:
        _, whole, _ = _monte_carlo('template', draws=300, start=0, rule=rule)
        _, first, _ = _monte_carlo('template', draws=100, start=0, rule=rule)
        _, second, _ = _monte_carlo('template', draws=200, start=100, rule=rule)
        return float(np.max(np.abs(whole - np.hstack([first, second]))))

    assert split('normalise') == 0.0, 'normalise no longer composes across calls'
    assert split('condition') > 0.0, \
        'conditioning composed exactly, which resampling cannot do -- has the ' \
        'resampling stopped happening?'


def test_mass_is_conserved_on_every_draw() -> None:
    """
    `template` has explicit loss flows and every group sums to 1, so what enters
    must equal what leaves -- on each draw separately, not just on average.

    This is the strongest single statement about the whole chain: sampling,
    the sum-to-1 constraint and the flow arithmetic all have to be right for it
    to hold.
    """
    keys, values, report = _monte_carlo('template', draws=400)
    assert report['groups'] == 10, f"expected 10 constrained groups, got {report['groups']}"

    depth = (keys[LAYERS] != '').sum(axis=1).to_numpy()
    flow = keys['Stock/Flow ID'].to_numpy()

    for element in ('Cu', 'Au'):
        is_element = (keys['Layer 4'] == element).to_numpy()
        entering = is_element & (flow == 'F1_collected')
        # Terminal flows: nothing leaves them.
        terminal = is_element & np.isin(flow, ['F6_refined', 'F7_loss_shredding',
                                               'F9_loss_refining', 'F8_loss_dismantling'])
        into = values[entering].sum(axis=0)
        out = values[terminal].sum(axis=0)
        worst = np.max(np.abs(into - out))
        assert worst < 1e-9, \
            f'{element}: mass in and out differ by up to {worst:.3e} across draws'


def test_nesting_holds_on_every_draw() -> None:
    """
    Children must still sum to their parent row after sampling. A coarse-layer
    coefficient scales a whole subtree, so this is what says that survived
    being turned into arrays.
    """
    keys, values, _ = _monte_carlo('template', draws=200)
    depth = (keys[LAYERS] != '').sum(axis=1).to_numpy()

    worst = 0.0
    for level in (2, 3, 4):
        parent_columns = ['Stock/Flow ID'] + LAYERS[:level - 1]
        children = keys[depth == level].groupby(parent_columns, sort=False).indices
        parents = keys[depth == level - 1]
        parent_lookup = {tuple(row): position for position, row
                         in zip(parents.index, parents[parent_columns].to_numpy())}
        for key, rows in children.items():
            key = key if isinstance(key, tuple) else (key,)
            if key not in parent_lookup:
                continue          # a flow truncated at this layer has no parent row
            total = values[keys.index[depth == level][rows]].sum(axis=0)
            worst = max(worst, float(np.max(np.abs(total - values[parent_lookup[key]]))))
    assert worst < 1e-9, f'children stopped summing to their parent by up to {worst:.3e}'


def test_sampling_actually_moves_the_answer() -> None:
    """
    The negative control. If the ranges reached the engine, the result must
    vary between draws -- otherwise every test above would pass on a Monte
    Carlo that silently did nothing, which is exactly what a dropped
    value_min column caused once.
    """
    _, values, report = _monte_carlo('template', draws=500)
    assert report['uncertain'], 'template has ranges but was treated as deterministic'
    assert values.std(axis=1).max() > 1.0, 'sampling produced no spread at all'


def test_running_at_the_mode_is_not_the_mean() -> None:
    """
    The property that makes the Monte Carlo worth running. The model is a
    product of coefficients, so the deterministic run -- every coefficient at
    its mode -- is not the mean of the distribution, and the gap is not noise.
    """
    determined = _deterministic('template')
    keys, values, _ = _monte_carlo('template', draws=4000)
    merged = determined.merge(keys.assign(mean=values.mean(axis=1)), on=KEYS, how='left')
    gap = np.abs(merged['Value'] - merged['mean'])
    assert gap.max() > 1.0, \
        'the deterministic answer equals the Monte Carlo mean, which a product of ' \
        'triangular coefficients should not'


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
