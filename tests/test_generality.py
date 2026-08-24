"""
Prove the model is not specific to BEV electronics.

    ./.venv/bin/python tests/test_generality.py

WHY THIS EXISTS
---------------
Every other suite runs on vehicle data. They would all keep passing if the code
quietly assumed vehicles, electronics domains, or element names -- which is
exactly the assumption that has to be false for this model to be used on
anything else.

So this one builds a **completely different recovery item** from scratch --
photovoltaic panels, with different groups, different materials and different
elements, in a different unit -- writes it in the upstream format, and puts it
through the same code end to end. Nothing here shares a single name with the
vehicle case.

If it passes, the pipeline is generic. If it fails, the failure names the line
that is still hard-wired.

WHAT IS CHECKED
---------------
1. The upstream reader reads a non-vehicle dataset.
2. The model solves it.
3. Mass balance closes on every year.
4. The Monte Carlo runs on it and produces a spread.
5. `rest` is derived for an incomplete parent, as it is for vehicles.
6. The same fixture read with `child_layer = material` puts the children one
   layer up, with no placeholder -- the 04_01 shape rather than the 04_02 one.
7. Several products in one case each close to 1 on their OWN total, not on the
   pooled one -- the 04_01 drivetrain shape.

The item is named in the case's own `source.csv`, never in `src/params_schema.py`.
That is what lets 04_01 and 04_02 be different cases rather than different runs
of the same settings, so this suite writes one and would fail if the reader
went back to reading the settings instead.
"""

from __future__ import annotations

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bootstrap import ensure_venv
ensure_venv()

import shutil
import tempfile
import traceback

import numpy as np
import pandas as pd

from src.monte_carlo import solve_draws
from src.params_schema import Params
from src.recovery_model_optimized import RecoveryModelOptimized
from src.rest import add_rest

NAMES = ['product', 'component', 'material', 'element']

# A recovery item that is not a vehicle, sharing no name with the real case.
PRODUCT = 'PVPanel'
GROUPS = ('Frame', 'Laminate', 'JunctionBox')
ELEMENTS = {'Frame': {'Al': 1.0},                        # complete: no rest
            'Laminate': {'Si': 0.40, 'Ag': 0.001},       # incomplete -> rest
            'JunctionBox': {'Cu': 0.35, 'Pb': 0.02}}     # incomplete -> rest
YEARS = (2035, 2045)
DRAWS = 400
FLOW = 'PV_collected'

# Two more products, exported to their own folders the way 04_01 writes one per
# drivetrain. `collected` and `inflow` are the single-product case's folders.
PRODUCTS = ('PVMono', 'PVThin')
FOLDERS = ('collected', 'inflow', *(f'{p}_collected' for p in PRODUCTS))


def write_upstream(root: str) -> None:
    """
    A synthetic upstream export, in the layout the reader expects.

    Written with a generator rather than committed as fixtures: the arrays are
    (draws, years) floats and there is no reason to put binaries in git when
    twenty lines reproduce them exactly.
    """
    scenario = os.path.join(root, 'HIGH')
    os.makedirs(scenario, exist_ok=True)
    np.save(os.path.join(scenario, 'years.npy'), np.array(YEARS))

    rng = np.random.default_rng(11)
    for flow in FOLDERS:
        folder = os.path.join(scenario, flow)
        os.makedirs(folder, exist_ok=True)
        # Each product at a clearly different level, so reading one folder
        # twice, or pooling the two, shows up as a total that is out by a
        # factor rather than by a rounding error.
        level = 40.0 * 2 ** FOLDERS.index(flow)
        for group in GROUPS:
            # Group mass in kt, growing between the two years, with spread.
            mass = rng.lognormal(mean=np.log([level, level * 2.25]), sigma=0.15,
                                 size=(DRAWS, len(YEARS)))
            np.save(os.path.join(folder, f'__domain____{group}.npy'),
                    mass.astype(np.float32))
            for element, share in ELEMENTS[group].items():
                np.save(os.path.join(folder, f'{element}__{group}.npy'),
                        (mass * share).astype(np.float32))


def write_case(case: str, child_layer: str = 'element',
               products: tuple[str, ...] | None = None) -> None:
    """The coefficients and the network, for a panel recycler."""
    os.makedirs(os.path.join(case, 'input_data'), exist_ok=True)

    # What the case is, declared by the case. Deliberately NOT in the settings:
    # a second case must be runnable without editing the first one's numbers.
    pd.DataFrame([
        dict(key='product', value=PRODUCT),
        dict(key='inflow_flow_id', value=FLOW),
        dict(key='flow', value='collected'),
        dict(key='child_layer', value=child_layer),
        dict(key='group_marker', value='__domain__'),
        dict(key='material_suffix', value='_mixed'),
        dict(key='groups', value=''),
    ] if products is None else [
        dict(key='product', value=';'.join(products)),
        dict(key='inflow_flow_id', value=FLOW),
        dict(key='flow', value='{product}_collected'),
        dict(key='child_layer', value=child_layer),
        dict(key='group_marker', value='__domain__'),
        dict(key='material_suffix', value='_mixed'),
        dict(key='groups', value=''),
    ]).to_csv(os.path.join(case, 'input_data', 'source.csv'), index=False)

    # A material-keyed case has no element layer to key on.
    finest = 'element' if child_layer == 'element' else 'material'
    pd.DataFrame([
        dict(Input_FlowID=FLOW, Output_FlowID='PV_delaminated', process='delamination',
             technology='thermal', keyed_at='component', is_loss=0, role='intermediate'),
        dict(Input_FlowID=FLOW, Output_FlowID='PV_loss_handling', process='delamination',
             technology='thermal', keyed_at='component', is_loss=1, role='loss'),
        dict(Input_FlowID='PV_delaminated', Output_FlowID='PV_recovered',
             process='leaching', technology='hydro', keyed_at=finest,
             is_loss=0, role='recovered'),
        dict(Input_FlowID='PV_delaminated', Output_FlowID='PV_loss_leaching',
             process='leaching', technology='hydro', keyed_at=finest,
             is_loss=1, role='loss'),
    ]).to_csv(os.path.join(case, 'input_data', 'processes.csv'), index=False)


def settings(root: str, case_name: str) -> Params:
    """A parameter set pointed at the synthetic item, not at the vehicle one."""
    params = Params()
    params.run.data_folder = os.path.join('data_folder', case_name)
    params.run.scenario = 'HIGH'
    params.run.years = ''
    params.run.working_unit = 't'
    params.data.upstream_root = root
    params.data.inflow_draws_dir = '.'
    params.data.upstream_flow = 'collected'
    # NOT set here: product, inflow_flow_id, groups, material_suffix,
    # child_layer. Those come from the case's own source.csv, which is the
    # whole point -- they are left at their vehicle defaults on purpose, so
    # that a reader falling back to the settings names 'BEV' and fails loudly.
    params.data.draws = DRAWS
    return params


def build_everything(child_layer: str = 'element', products=None):
    """Set the whole thing up, and return (params, case folder, temp root)."""
    root = tempfile.mkdtemp()
    upstream = os.path.join(root, 'upstream')
    write_upstream(upstream)

    case_name = f'pv_panels_test_{child_layer}{"_multi" if products else ""}'
    case = os.path.join('data_folder', case_name)
    if os.path.isdir(case):
        shutil.rmtree(case)
    write_case(case, child_layer, products)

    params = settings(upstream, case_name)
    return params, case, root


def coefficients(case: str, composition: pd.DataFrame) -> None:
    """
    Fill every coefficient the network needs, so the case actually solves.

    Generated from the composition rather than written out, so this stays
    correct if the fixture above gains a group or an element.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'tools'))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'make_skeleton', os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), 'tools', 'make_skeleton.py'))
    skeleton = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skeleton)

    tcs = skeleton.build(case, composition=composition)
    blank = tcs['value'].astype(str).str.strip() == ''
    recovery = tcs['Output_FlowID'].isin(['PV_delaminated', 'PV_recovered'])
    tcs.loc[blank & recovery, ['value', 'value_min', 'value_max']] = ['0.7', '0.5', '0.9']
    tcs.loc[blank & ~recovery, ['value', 'value_min', 'value_max']] = ['0.3', '', '']
    tcs.loc[blank & ~recovery, 'is_residual'] = '1'
    tcs.to_csv(os.path.join(case, 'input_data', 'TCs.csv'), index=False)


# ----------------------------------------------------------------------

def test_a_different_recovery_item_can_be_read() -> None:
    """The upstream reader is not tied to vehicles or electronics domains."""
    from src.upstream import load

    params, case, root = build_everything()
    try:
        tables = load(params, params.run.data_folder, quiet=True)
        assert tables is not None, 'the reader did not recognise the case'

        inflow, composition = tables['inputs'], tables['composition']
        assert set(inflow['Substance_main_parent']) == {PRODUCT}, \
            f"product is {set(inflow['Substance_main_parent'])}, expected {PRODUCT}"
        assert set(composition['Layer 2']) == set(GROUPS), \
            f"groups are {set(composition['Layer 2'])}, expected {set(GROUPS)}"
        assert sorted(inflow['Year']) == list(YEARS), 'both years should be read'
        # Upstream reports kilotonnes whatever the project works in; the
        # conversion to working_unit happens in the engine, on load.
        assert set(inflow['Unit']) == {'kt'}, 'upstream mass is kilotonnes'
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(case, ignore_errors=True)


def test_a_different_recovery_item_solves_and_closes() -> None:
    """
    The whole pipeline, on a non-vehicle item: read, derive rest, solve, and
    check that what enters equals what leaves in every year.
    """
    from src.upstream import load

    params, case, root = build_everything()
    try:
        tables = load(params, params.run.data_folder, quiet=True)
        coefficients(case, tables['composition'])

        # Two of the three groups are incomplete, and a rest is derived per
        # parent per year -- the same rule the vehicle case relies on.
        with_rest, notes = add_rest(tables['composition'])
        assert len(notes) == 2 * len(YEARS), \
            f'expected 2 incomplete groups x {len(YEARS)} years, got {len(notes)}'

        solution = RecoveryModelOptimized(
            data_folder=case, layer_names=NAMES, tables=tables,
            working_unit=params.run.working_unit, years='',
        ).solve_models_and_write_to_output()
        solution['Value'] = pd.to_numeric(solution['Value'])

        layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
        depth = (solution[layers] != '').sum(axis=1)
        for year, group in solution.assign(depth=depth).groupby('Year'):
            def total(flow):
                rows = group[group['Stock/Flow ID'] == flow]
                return 0.0 if rows.empty else \
                    rows[rows['depth'] == rows['depth'].min()]['Value'].sum()
            entering = total(FLOW)
            leaving = sum(total(f) for f in ('PV_recovered', 'PV_loss_leaching',
                                             'PV_loss_handling'))
            assert entering > 0, f'{year}: nothing entered'
            assert abs(entering - leaving) / entering < 1e-9, \
                f'{year}: {entering:g} in, {leaving:g} out'
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(case, ignore_errors=True)


def test_children_can_be_materials_instead_of_elements() -> None:
    """
    The 04_01 shape: the upstream child is a material, not an element.

    Same fixture, same files, one line of source.csv different. The children
    must land at Layer 3 with Layer 4 empty and no placeholder material
    invented -- and the case must still solve and close.
    """
    from src.upstream import load

    params, case, root = build_everything(child_layer='material')
    try:
        tables = load(params, params.run.data_folder, quiet=True)
        composition = tables['composition']

        assert set(composition['Layer 4']) == {''}, \
            f"Layer 4 should be unused, found {sorted(set(composition['Layer 4']))}"

        children = {e for group in ELEMENTS.values() for e in group}
        at_three = set(composition['Layer 3']) - {''}
        assert at_three == children, \
            f'Layer 3 holds {sorted(at_three)}, expected {sorted(children)}'
        assert not any(name.endswith('_mixed') for name in at_three), \
            'a placeholder material was invented where the child is already one'

        coefficients(case, composition)
        solution = RecoveryModelOptimized(
            data_folder=case, layer_names=NAMES, tables=tables,
            working_unit=params.run.working_unit, years='',
        ).solve_models_and_write_to_output()
        solution['Value'] = pd.to_numeric(solution['Value'])

        layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
        depth = (solution[layers] != '').sum(axis=1)
        for year, group in solution.assign(depth=depth).groupby('Year'):
            def total(flow):
                rows = group[group['Stock/Flow ID'] == flow]
                return 0.0 if rows.empty else \
                    rows[rows['depth'] == rows['depth'].min()]['Value'].sum()
            entering = total(FLOW)
            leaving = sum(total(f) for f in ('PV_recovered', 'PV_loss_leaching',
                                             'PV_loss_handling'))
            assert entering > 0, f'{year}: nothing entered'
            assert abs(entering - leaving) / entering < 1e-9, \
                f'{year}: {entering:g} in, {leaving:g} out'
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(case, ignore_errors=True)


def test_several_products_close_on_their_own_totals() -> None:
    """
    The 04_01 drivetrain shape: one case, several Layer 1 values.

    Each product is exported to its own folder at its own level, and each must
    come out as its own whole. Pooling them would still balance and still plot
    -- every share would just be wrong by the ratio of one product's mass to
    all of them -- so the check is on the shares, not on the total.
    """
    from src.upstream import load

    params, case, root = build_everything(products=PRODUCTS)
    try:
        tables = load(params, params.run.data_folder, quiet=True)
        inflow, composition = tables['inputs'], tables['composition']

        assert set(inflow['Substance_main_parent']) == set(PRODUCTS), \
            f"products are {set(inflow['Substance_main_parent'])}, expected {PRODUCTS}"
        assert len(inflow) == len(PRODUCTS) * len(YEARS), \
            f'expected one inflow row per product per year, got {len(inflow)}'

        # The folders were written at 40 kt and 80 kt, so the products must
        # differ -- identical totals would mean one folder was read twice.
        totals = inflow.groupby('Substance_main_parent')['Value'].sum()
        assert totals.max() / totals.min() > 1.5, \
            f'the products came out the same size ({dict(totals)}); one folder read twice?'

        # The component share is a share of its OWN product.
        top = composition[composition['Layer 3'] == '']
        for (product, year), rows in top.groupby(['Layer 1', 'Year']):
            assert abs(rows['Value'].sum() - 1.0) < 1e-6, \
                f'{product} {year}: component shares sum to {rows["Value"].sum():.6f}'
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(case, ignore_errors=True)


def test_the_monte_carlo_runs_on_a_different_item() -> None:
    """Sampling, the sum-to-1 groups and the spread all work off vehicle data."""
    from src.upstream import load

    params, case, root = build_everything()
    try:
        tables = load(params, params.run.data_folder, quiet=True)
        coefficients(case, tables['composition'])

        run = solve_draws(case, NAMES, draws=200, seed=0, tables=tables, years='')
        assert run.report['uncertain'], 'the ranges did not reach the sampler'
        assert run.values.std(axis=1).max() > 0, 'the Monte Carlo produced no spread'
        assert run.report['groups'] > 0, 'no constrained groups were found'
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(case, ignore_errors=True)


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
