"""
Build the FLEET traction motor case: both roads at once, split at step 2.

    ./.venv/bin/python tools/build_tractionmotor_fleet_case.py

⚠️ THIS IS THE CASE TO READ. The other four each send 100% of collected motors
down ONE route -- the extremes -- and the fleet is neither. Four cases also
means four of every figure and no single answer.

⚠️ THE SPLIT IS THE REVIEW'S OWN STEP 2, NOT A NUMBER ANYBODY INVENTED.
`RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx`, both disassembly sheets:

    step 1  EoL vehicle collection      0.70 | 0.80 | 0.90   ref 37,38
    step 2  Motor removal from vehicle  0.85 | 0.93 | 0.98   ref 6,7,8,9

So the network is:

    F_collected --step 1--> F_captured --step 2------> F_removed   -> disassembly
                        \\-> F_uncollected         \\-(1 - step 2)-> F_shredded  -> shredder

**What is not removed is shredded, not lost.** In the pure disassembly case
the 7% that step 2 leaves behind goes to `F_loss_upstream` and is written off.
That is right for a case that asks "what does disassembly yield"; it is wrong
for one that asks what the fleet recovers, because a motor nobody pulled out
is still in a hulk that goes to a shredder. DECISIONS 10, in the wiring case's
words: *nothing is lost by not being disassembled, it simply travels the other
road.*

⚠️ AN EARLIER VERSION OF THIS FILE DOUBLE-COUNTED REMOVAL. It put an invented
coefficient `DISASSEMBLY_SHARE` above chains that already applied
capture x removal, so the disassembly road was `d x (0.80 x 0.93)`. Two values
were tried, 0.20 and then the battery case's 0.95|0.98|1.00, and both were a
second copy of a step the review already gives. The check that was supposed to
catch it compared the case against a blend using the same invented `d`, so it
agreed with itself. There is no share in this file now: step 2 is the share.

NOT HERE ON PURPOSE: the short loop. The workbook gives HD/HPMS no 2030
coefficient and calls it "pilot to early commercial". `tractionmotor_shortloop`
keeps it as an extreme.

NOTHING IS RE-DERIVED. Both chains are imported from the builders that own
them, and each chain's own first step -- the one that folds capture into
removal or into feed -- is DROPPED and replaced by the head above, so no
coefficient is applied twice.

EVERY FLOW SAYS WHICH ROAD IT IS ON. The chains share nine flow names, and
merging on them would pour the disassembled copper and the shredded copper
into one flow and give the pair a single yield. So every flow but the head's
carries `_dis` or `_shr`, which also lets `routes()` find two roads and the
workbook's `Contributions` sheet say how much came back on each.
"""
import importlib.util
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
COLUMNS = ['Input_FlowID', 'Output_FlowID', 'process', 'technology',
           'keyed_at', 'role']
SRC = ('RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, '
       'TC_2030/2060_Disassembly_Route')


def load(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIS = load('build_tractionmotor_case.py')           # disassembly, long loop
SHR = load('build_tractionmotor_shredder_case.py')  # shredded whole


def inverse(value):
    return round(1 - value[2], 6), round(1 - value[1], 6), round(1 - value[0], 6)


def road(name: str, suffix: str, entry: dict) -> str:
    """Put a flow on one road. The head's flows keep their own names."""
    return entry.get(name, f'{name}_{suffix}')


def rename(frame: pd.DataFrame, suffix: str, entry: dict) -> pd.DataFrame:
    out = frame.copy()
    for column in ('Input_FlowID', 'Output_FlowID'):
        out[column] = [road(str(v), suffix, entry) for v in out[column]]
    return out


def head(table, horizon: str) -> pd.DataFrame:
    """Steps 1 and 2, and the fork step 2 makes."""
    rows = []

    def add(inflow, outflow, value, process, note):
        for group in GROUPS:
            rows.append(dict(
                Input_FlowID=inflow, Input_layer='product',
                Input_layer_key='BEV', Output_FlowID=outflow,
                TC_target_layer='component', TC_target_key=group,
                value=value[1], value_min=value[0], value_max=value[2],
                process=process, technology='dismantling',
                source=f'{note} [{SRC}]'))

    capture, removal = table['capture'], table['removal']
    add('F_collected', 'F_captured', capture, 'collection',
        f'step 1: EoL vehicle collection in {horizon}')
    add('F_collected', 'F_uncollected', inverse(capture), 'collection',
        'not collected: never reaches any treatment')
    add('F_captured', 'F_removed', removal, 'motor_removal',
        f'step 2: motor removed from the vehicle in {horizon}. THIS IS THE '
        f'FORK -- the share of collected motors taken out whole')
    add('F_captured', 'F_shredded', inverse(removal), 'motor_removal',
        'step 2, the other side: NOT removed, so it stays in the hulk and '
        'goes to the shredder. Not a loss -- it travels the other road')
    return pd.DataFrame(rows)


def feed(table, horizon: str) -> pd.DataFrame:
    """The shredder's own step 2: what reaches the shredder is sorted."""
    rows = []
    for group, stream in (('magnet', 'F_ndfeb_stream_shr'),
                          ('copper', 'F_cu_stream_shr'),
                          ('aluminium', 'F_al_stream_shr'),
                          ('lamination', 'F_steel_stream_shr'),
                          ('steel', 'F_steel_stream_shr')):
        for outflow, value, note in (
                (stream, table['feed'],
                 f'step 2, shredder route: motor to shredder feed, then '
                 f'sorted, in {horizon}'),
                ('F_loss_unfed_shr', inverse(table['feed']),
                 'not fed to the shredder')):
            rows.append(dict(
                Input_FlowID='F_shredded', Input_layer='product',
                Input_layer_key='BEV', Output_FlowID=outflow,
                TC_target_layer='component', TC_target_key=group,
                value=value[1], value_min=value[0], value_max=value[2],
                process='shredder_feed', technology='shredder',
                source=f'{note} [RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, '
                       f'TC_2030/2060_Shredder_Route]'))
    return pd.DataFrame(rows)


def without_first_step(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop the chain's own capture step -- the head supplies it now."""
    return frame[frame['Input_FlowID'] != 'F_collected'].copy()


def tcs_for(horizon: str) -> pd.DataFrame:
    table_dis = DIS.S30 if horizon == '2030' else DIS.S60
    table_shr = SHR.S30 if horizon == '2030' else SHR.S60
    return pd.concat([
        head(table_dis, horizon),
        rename(without_first_step(DIS.tc_rows(table_dis)), 'dis',
               {'F_motor': 'F_removed'}),
        feed(table_shr, horizon),
        rename(without_first_step(SHR.tc_rows(table_shr)), 'shr', {}),
    ], ignore_index=True)


def processes_for() -> pd.DataFrame:
    top = pd.DataFrame([
        ('F_collected', 'F_captured', 'collection', 'dismantling',
         'component', 'intermediate'),
        ('F_collected', 'F_uncollected', 'collection', 'dismantling',
         'component', 'loss'),
        ('F_captured', 'F_removed', 'motor_removal', 'dismantling',
         'component', 'intermediate'),
        ('F_captured', 'F_shredded', 'motor_removal', 'dismantling',
         'component', 'intermediate'),
        ('F_shredded', 'F_ndfeb_stream_shr', 'shredder_feed', 'shredder',
         'component', 'intermediate'),
        ('F_shredded', 'F_cu_stream_shr', 'shredder_feed', 'shredder',
         'component', 'intermediate'),
        ('F_shredded', 'F_al_stream_shr', 'shredder_feed', 'shredder',
         'component', 'intermediate'),
        ('F_shredded', 'F_steel_stream_shr', 'shredder_feed', 'shredder',
         'component', 'intermediate'),
        ('F_shredded', 'F_loss_unfed_shr', 'shredder_feed', 'shredder',
         'component', 'loss'),
    ], columns=COLUMNS)
    dis = DIS.processes[DIS.processes['Input_FlowID'] != 'F_collected']
    shr = SHR.processes[SHR.processes['Input_FlowID'] != 'F_collected']
    return pd.concat([top,
                      rename(dis, 'dis', {'F_motor': 'F_removed'}),
                      rename(shr, 'shr', {})],
                     ignore_index=True)[COLUMNS]


def main() -> int:
    folder = 'data_folder/tractionmotor'
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

    for horizon, table in (('2030', DIS.S30), ('2060', DIS.S60)):
        low, mode, high = table['removal']
        print(f'  {horizon}: step 2 removal {mode} [{low}-{high}] '
              f'-> disassembly;  {round(1 - mode, 2)} -> shredder')
    print(f'{path}: {len(tcs_for("2030"))} TC rows, '
          f'{len(processes_for())} processes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
