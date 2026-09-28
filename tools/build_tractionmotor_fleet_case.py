"""
Build the FLEET traction motor case: both roads at once, with a share.

    ./.venv/bin/python tools/build_tractionmotor_fleet_case.py

⚠️ THIS IS THE CASE TO READ. The other four each send 100% of collected motors
down ONE route -- the extremes -- and the fleet is neither. Four cases also
means four of every figure and no single answer.

    F_collected --> F_removed    --> REE and copper recovered        d
                \\-> F_shredded  --> REE and copper largely lost    1 - d

`d` is the one new number. The four pure cases stay as the bounds: this case
with `d` at 1 and at 0.

NOT HERE ON PURPOSE: the short loop. The workbook gives HD/HPMS no 2030
coefficient and calls it "pilot to early commercial", and its feasibility was
doubted out loud. A route nobody can cost does not belong in the case that
describes the fleet; `tractionmotor_shortloop` keeps it.

NOTHING IS RE-DERIVED. Both chains are imported from the builders that own
them, so a change to a process coefficient reaches this case too.

EVERY FLOW SAYS WHICH ROAD IT IS ON. The two chains share nine flow names, and
merging on them would pour the disassembled copper and the shredded copper into
one flow and give the pair a single yield -- the thing this case exists to
avoid. So every flow but `F_collected` carries `_dis` or `_shr`, which also
lets `routes()` find two roads and `Contributions` say how much came back on
each.
"""
import importlib.util
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ⚠️ THE DISASSEMBLY RATE, AND IT IS A PLACEHOLDER. Neither the review nor the
# workbook gives one; they describe both routes and say nothing about shares.
# Wide, and THE SAME IN BOTH HORIZONS -- asserting a trajectory would invent a
# second number on top of the first.
#
# The upper bound is not 1 on purpose: even under a policy of taking every
# motor out, accident vehicles arrive in no state to be dismantled. That
# ceiling is a fact about the fleet, not a cap in code.
#
# ⚠️ SET TO THE BATTERY'S OWN DISMANTLING RATE, 2026-09-28, at the user's
# instruction: *"why are only so few traction motors taken out. It will be the
# same as for batteries."* `data_folder/battery` removes the pack at
# 0.95 | 0.98 | 1.00, a number he measured for that case. The reasoning is the
# vehicle's, not the component's: a hulk that has been opened to take a
# high-voltage pack out is a hulk the motor can be taken out of too, so the two
# rates are the same rate.
#
# My placeholder before this was 0.05 | 0.20 | 0.50, which was a guess and is
# now replaced by a number with a source.
DISASSEMBLY_SHARE = {'2030': (0.95, 0.98, 1.00),
                     '2060': (0.95, 0.98, 1.00)}

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
COLUMNS = ['Input_FlowID', 'Output_FlowID', 'process', 'technology',
           'keyed_at', 'role']


def load(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIS = load('build_tractionmotor_case.py')           # disassembly, long loop
SHR = load('build_tractionmotor_shredder_case.py')  # shredded whole


def road(name: str, suffix: str, entry: str) -> str:
    """Put a flow on one road. `F_collected` becomes that road's entry flow."""
    if name == 'F_collected':
        return entry
    return f'{name}_{suffix}'


def rename(frame: pd.DataFrame, suffix: str, entry: str) -> pd.DataFrame:
    out = frame.copy()
    for column in ('Input_FlowID', 'Output_FlowID'):
        out[column] = [road(str(v), suffix, entry) for v in out[column]]
    return out


def branch(share, horizon: str) -> pd.DataFrame:
    """The one new decision: how much of the fleet is taken apart."""
    low, mode, high = share
    rows = []
    for group in GROUPS:
        for flow, value, note in (
                ('F_removed', (low, mode, high),
                 f'the share of collected motors taken out whole for '
                 f'disassembly in {horizon}. The review gives no rate, so this '
                 f'is the BATTERY case\'s own dismantling rate, 0.95|0.98|1.00 '
                 f'-- a hulk opened to take the pack out is one the motor can '
                 f'be taken out of. Set by the user, 2026-09-28'),
                ('F_shredded', (round(1 - high, 6), round(1 - mode, 6),
                                round(1 - low, 6)),
                 f'PLACEHOLDER (Claude, not data) -- the remainder, shredded '
                 f'without magnet extraction in {horizon}. NOT AN INDEPENDENT '
                 f'MEASUREMENT: 1 minus the row beside it')):
            rows.append(dict(
                Input_FlowID='F_collected', Input_layer='product',
                Input_layer_key='BEV', Output_FlowID=flow,
                TC_target_layer='component', TC_target_key=group,
                value=value[1], value_min=value[0], value_max=value[2],
                process='route_choice', technology='fleet_practice',
                source=note))
    return pd.DataFrame(rows)


def tcs_for(horizon: str) -> pd.DataFrame:
    return pd.concat([
        branch(DISASSEMBLY_SHARE[horizon], horizon),
        rename(DIS.tc_rows(DIS.S30 if horizon == '2030' else DIS.S60),
               'dis', 'F_removed'),
        rename(SHR.tc_rows(SHR.S30 if horizon == '2030' else SHR.S60),
               'shr', 'F_shredded'),
    ], ignore_index=True)


def processes_for() -> pd.DataFrame:
    top = pd.DataFrame([
        ('F_collected', 'F_removed', 'route_choice', 'fleet_practice',
         'component', 'intermediate'),
        ('F_collected', 'F_shredded', 'route_choice', 'fleet_practice',
         'component', 'intermediate'),
    ], columns=COLUMNS)
    return pd.concat([top,
                      rename(DIS.processes, 'dis', 'F_removed'),
                      rename(SHR.processes, 'shr', 'F_shredded')],
                     ignore_index=True)[COLUMNS]


def main() -> int:
    folder = 'data_folder/tractionmotor_fleet'
    os.makedirs(f'{folder}/input_data', exist_ok=True)
    source = pd.DataFrame([
        ('upstream_dir', 'data/processed/traction_recovery_draws'),
        ('flow', 'collected'), ('product', 'BEV'),
        ('inflow_flow_id', 'F_collected'), ('child_layer', 'element'),
        ('group_marker', '__component__'), ('material_suffix', None),
        ('groups', None), ('draws', 200000),
        ('improvement_start', 2030), ('improvement_end', 2060),
    ], columns=['key', 'value'])
    lists = pd.DataFrame(
        {'keyed_at': ['component', 'material', 'element', None],
         'role': ['recovered', 'loss', 'handoff', 'intermediate']})

    path = f'{folder}/input_data/case.xlsx'
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        source.to_excel(writer, sheet_name='source', index=False)
        processes_for().to_excel(writer, sheet_name='processes', index=False)
        lists.to_excel(writer, sheet_name='_lists', index=False)
        tcs_for('2030').to_excel(writer, sheet_name='TCs', index=False)
        tcs_for('2060').to_excel(writer, sheet_name='TCs_improved', index=False)

    low, mode, high = DISASSEMBLY_SHARE['2030']
    print(f'{path}: {len(tcs_for("2030"))} TC rows, '
          f'{len(processes_for())} processes')
    print(f'  disassembled {mode:.0%} [{low:.0%}-{high:.0%}], the rest '
          f'shredded -- PLACEHOLDER, nobody measured it')
    return 0


if __name__ == '__main__':
    sys.exit(main())
