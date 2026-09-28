"""
Build the MIXED traction motor case: both roads at once, with a share.

    ./.venv/bin/python tools/build_tractionmotor_mixed_case.py

⚠️ WHY THIS EXISTS. The four traction motor cases each send 100% of the
collected motors down ONE route. That answers "what if every motor were taken
out" and "what if none were", which are the extremes, and the real fleet is
neither. Asked for on 2026-09-28: *"We still can have extremes, but we should
display the real world."*

So the route stops being a case and becomes a COEFFICIENT. The branch sits at
the top of the network, exactly as it does in the wiring and boards cases
(DECISIONS 10 and 11 -- disassembly, or it stays in the car and goes to the
general shredder; nothing is lost by not being disassembled, it simply travels
the other road):

    F_collected --> F_disassembled --> ... long loop      d x (1 - s)
                |                  \\-> ... short loop     d x s
                \\-> F_in_car ------> ... shredder         1 - d

`d` is the new number. `s`, the share of clean magnet feed to HD/HPMS, already
existed inside the split case and is reused unchanged.

⚠️ THE FOUR PURE CASES STAY. They are this case with `d` at 1 or 0, and they
are the bounds worth quoting. Nothing here replaces them.

⚠️ NOTHING IS RE-DERIVED HERE. Both chains are imported from the builders that
own them, so a change to a process coefficient reaches this case too. What
this file adds is the branch and the renaming, and nothing else.

EVERY FLOW SAYS WHICH ROAD IT IS ON. The two chains share nine flow names --
`F_cu_stream`, `F_cu_recovered`, `F_loss_metals` and the rest -- and merging
them on those names would pour the disassembled copper and the shredded copper
into one flow and give the pair a single yield, which is the whole thing this
case exists to avoid. So every flow but `F_collected` carries `_dis` or `_shr`.
That also lets `routes()` find two roads, and the workbook's `Contributions`
sheet then says how much of the recovered neodymium came back by each.
"""
import importlib.util
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ⚠️ THE DISASSEMBLY RATE, AND IT IS A PLACEHOLDER. Neither the review nor the
# workbook gives one: they describe both routes and say nothing about their
# market shares. The band is deliberately wide and DELIBERATELY THE SAME IN
# BOTH HORIZONS -- asserting a trajectory for it would be inventing a second
# number on top of the first. Set both ends yourself; `tools/filling_sheet.py`
# will rank this row first, which is exactly what it deserves.
DISASSEMBLY_SHARE = {'2030': (0.05, 0.20, 0.50),
                     '2060': (0.05, 0.20, 0.50)}

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']


def load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, f'build_tractionmotor_{name}_case.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIS = load('shortloop')      # capture -> motor -> magnet -> long/short split
SHR = load('shredder')       # capture -> shredder -> fates


def road(name: str, suffix: str) -> str:
    """Put a flow on one road. `F_collected` is the inflow and belongs to both."""
    return name if name == 'F_collected' else f'{name}_{suffix}'


def rename(frame: pd.DataFrame, suffix: str, entry: str) -> pd.DataFrame:
    """One chain's rows, moved onto its own road and fed by `entry`."""
    out = frame.copy()
    for column in ('Input_FlowID', 'Output_FlowID'):
        out[column] = [road(str(v), suffix) for v in out[column]]
    out.loc[out['Input_FlowID'] == 'F_collected', 'Input_FlowID'] = entry
    return out


def branch(share, horizon: str) -> pd.DataFrame:
    """The one new decision: how much of the fleet is taken apart."""
    lo, mid, hi = share
    rows = []
    for group in GROUPS:
        for flow, value, note in (
                ('F_disassembled', (lo, mid, hi),
                 f'PLACEHOLDER (Claude, not data) -- the share of collected '
                 f'motors taken out whole for selective disassembly in '
                 f'{horizon}. Neither the review nor the workbook gives a '
                 f'rate; they describe the routes, not their shares'),
                ('F_in_car', (round(1 - hi, 6), round(1 - mid, 6),
                              round(1 - lo, 6)),
                 f'PLACEHOLDER (Claude, not data) -- the remainder, shredded '
                 f'without magnet extraction in {horizon}. NOT AN INDEPENDENT '
                 f'MEASUREMENT: it is 1 minus the row beside it')):
            rows.append(dict(
                Input_FlowID='F_collected', Input_layer='product',
                Input_layer_key='BEV', Output_FlowID=flow,
                TC_target_layer='component', TC_target_key=group,
                value=value[1], value_min=value[0], value_max=value[2],
                process='route_choice', technology='fleet_practice',
                source=note))
    return pd.DataFrame(rows)


def tcs_for(horizon: str) -> pd.DataFrame:
    table_dis = DIS.S30 if horizon == '2030' else DIS.S60
    table_shr = SHR.S30 if horizon == '2030' else SHR.S60
    return pd.concat([
        branch(DISASSEMBLY_SHARE[horizon], horizon),
        rename(DIS.tc_rows(table_dis, horizon,
                           DIS.SHORT_LOOP_SHARE[horizon]), 'dis',
               'F_disassembled'),
        rename(SHR.tc_rows(table_shr), 'shr', 'F_in_car'),
    ], ignore_index=True)


def processes_for() -> pd.DataFrame:
    columns = ['Input_FlowID', 'Output_FlowID', 'process', 'technology',
               'keyed_at', 'role']
    top = pd.DataFrame([
        ('F_collected', 'F_disassembled', 'route_choice', 'fleet_practice',
         'component', 'intermediate'),
        ('F_collected', 'F_in_car', 'route_choice', 'fleet_practice',
         'component', 'intermediate'),
    ], columns=columns)
    dis = DIS.processes_for(DIS.SHORT_LOOP_SHARE['2060'])
    return pd.concat([top, rename(dis, 'dis', 'F_disassembled'),
                      rename(SHR.processes, 'shr', 'F_in_car')],
                     ignore_index=True)[columns]


def main() -> int:
    folder = 'data_folder/tractionmotor_mixed'
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

    share = DISASSEMBLY_SHARE['2030']
    print(f'{path}: {len(tcs_for("2030"))} TC rows, '
          f'{len(processes_for())} processes')
    print(f'  disassembled {share[1]:.0%} [{share[0]:.0%}-{share[2]:.0%}], '
          f'the rest shredded -- PLACEHOLDER, nobody measured it')
    return 0


if __name__ == '__main__':
    sys.exit(main())
