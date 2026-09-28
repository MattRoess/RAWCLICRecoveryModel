"""
Build the SHORT-LOOP and the SPLIT traction motor cases.

Both share the disassembly front end -- capture, motor removal, dehousing,
extraction, milling -- and differ only in what happens to the milled magnet.

    tractionmotor_shortloop   all of it to hydrogen decrepitation (HD/HPMS)
    tractionmotor_split       a share to the short loop, the rest to hydromet

⚠️ WHY THE SHORT LOOP IS NOT A VARIANT OF THE LONG ONE. Hydrometallurgy
dissolves the magnet and separates the elements, so its output is Nd, Pr, Dy
and Tb as oxide or metal. Hydrogen decrepitation keeps the ALLOY: the output is
magnet feedstock in which the four elements are still together, and dysprosium
and terbium are returned where they already were instead of being separated and
re-added. The two routes therefore differ in the SHAPE of what they recover,
not only in how much, which is why they are separate cases rather than a
coefficient swap.

⚠️ THE 2030 COLUMN CARRIES THE SAME PROCESS COEFFICIENT AS 2060, and that is
not an oversight. The workbook gives step 6a/d only for 2060 -- `Process
Comparison` marks HD/HPMS as NR for 2030, "Pilot to early commercial". This
case answers "what does the short loop yield WHEN IT IS USED", so the process
coefficient is the one published value in both columns, and the improvement
between the two horizons comes from steps 1-5, which do have 2030 values. It
is NOT a claim that the short loop is available at scale in 2030; the share in
the split case is where that belongs.
"""
import sys

import pandas as pd

SRC = 'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, TC_2030/2060_Disassembly_Route'

# ⚠️ THE SHARE IS NOT IN EITHER DOCUMENT. The review says 2060 routes clean
# feed to the short loop and mixed or contaminated feed to hydrometallurgy, and
# gives no number for the split. These are assumptions, they are the only
# assumptions in this case that are not the workbook's, and they are here on
# purpose so that changing them is one line.
#     2030  0.00 | 0.00 | 0.05 -- the workbook gives HD/HPMS no 2030
#           coefficient at all and Process Comparison calls it "pilot to early
#           commercial", so the mode is nothing and the upper bound is small
#           rather than zero
#     2060  0.35 | 0.50 | 0.65 -- half, as a neutral reading of "major for
#           clean feed", with a wide band because nothing constrains it
#
# ⚠️ AN INTERVAL, NOT A POINT, AND FOR TWO REASONS. A share this uncertain
# reported as a single number claims a precision nobody has. And a degenerate
# min = mode = max does not survive the ramp: Excel keeps 15 significant
# digits, so after interpolation the bounds came back 6.6e-17 below the mode
# and the checker refused the table -- correctly, since it cannot tell that
# apart from a real ordering fault.
SHORT_LOOP_SHARE = {'2030': (0.00, 0.00, 0.05),
                    '2060': (0.35, 0.50, 0.65)}

S30 = {
    'capture': (0.70, 0.80, 0.90), 'removal': (0.85, 0.93, 0.98),
    'pre_magnet': (0.80, 0.88, 0.95), 'pre_cu': (0.90, 0.95, 0.98),
    'pre_al': (0.92, 0.96, 0.99), 'pre_steel': (0.85, 0.92, 0.97),
    'extract': (0.70, 0.82, 0.92), 'magnet_prep': (0.88, 0.93, 0.97),
    # step 6a/d, published for 2060 only -- see the module docstring
    'short_loop': (0.88, 0.93, 0.97),
    'hyd_Nd': (0.85, 0.92, 0.97), 'hyd_Pr': (0.83, 0.90, 0.96),
    'hyd_Dy': (0.80, 0.88, 0.95), 'hyd_Tb': (0.78, 0.86, 0.94),
    'sx_Nd': (0.88, 0.93, 0.98), 'sx_Pr': (0.86, 0.91, 0.97),
    'sx_Dy': (0.85, 0.91, 0.97), 'sx_Tb': (0.83, 0.89, 0.96),
    'oxide_Nd': (0.90, 0.95, 0.98), 'oxide_Pr': (0.90, 0.95, 0.98),
    'oxide_Dy': (0.90, 0.95, 0.98), 'oxide_Tb': (0.90, 0.95, 0.98),
    'cu_refine': (0.82, 0.90, 0.96), 'al_recover': (0.88, 0.93, 0.97),
    'steel_recover': (0.80, 0.88, 0.95),
}
S60 = {
    'capture': (0.82, 0.90, 0.96), 'removal': (0.92, 0.97, 0.99),
    'pre_magnet': (0.88, 0.94, 0.98), 'pre_cu': (0.93, 0.97, 0.99),
    'pre_al': (0.95, 0.98, 0.99), 'pre_steel': (0.90, 0.95, 0.98),
    'extract': (0.82, 0.92, 0.97), 'magnet_prep': (0.92, 0.96, 0.99),
    'short_loop': (0.88, 0.93, 0.97),
    'hyd_Nd': (0.90, 0.96, 0.99), 'hyd_Pr': (0.88, 0.94, 0.98),
    'hyd_Dy': (0.86, 0.93, 0.97), 'hyd_Tb': (0.84, 0.92, 0.97),
    'sx_Nd': (0.92, 0.96, 0.99), 'sx_Pr': (0.90, 0.95, 0.99),
    'sx_Dy': (0.90, 0.95, 0.98), 'sx_Tb': (0.88, 0.94, 0.98),
    'oxide_Nd': (0.93, 0.97, 0.99), 'oxide_Pr': (0.93, 0.97, 0.99),
    'oxide_Dy': (0.93, 0.97, 0.99), 'oxide_Tb': (0.93, 0.97, 0.99),
    'cu_refine': (0.88, 0.94, 0.98), 'al_recover': (0.92, 0.96, 0.99),
    'steel_recover': (0.85, 0.92, 0.97),
}

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
ELEMENTS = ['Nd', 'Pr', 'Dy', 'Tb']


def prod(steps, table):
    lo = mid = hi = 1.0
    for s in steps:
        a, b, c = table[s]
        lo, mid, hi = lo * a, mid * b, hi * c
    return round(lo, 6), round(mid, 6), round(hi, 6)


def inv(v):
    return round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)


def tc_rows(table, horizon, share):
    rows = []

    def add(inflow, inkey, inlayer, outflow, tlayer, tkey, v, process, tech,
            note):
        lo, mid, hi = v
        rows.append(dict(
            Input_FlowID=inflow, Input_layer=inlayer, Input_layer_key=inkey,
            Output_FlowID=outflow, TC_target_layer=tlayer, TC_target_key=tkey,
            value=mid, value_min=lo, value_max=hi, process=process,
            technology=tech, source=f'{note} [{SRC}]'))

    # 1-2  capture and motor removal
    up = prod(['capture', 'removal'], table)
    for g in GROUPS:
        add('F_collected', 'BEV', 'product', 'F_motor', 'component', g, up,
            'motor_recovery', 'dismantling',
            'steps 1-2: EoL capture x motor removal')
        add('F_collected', 'BEV', 'product', 'F_loss_upstream', 'component', g,
            inv(up), 'motor_recovery', 'dismantling',
            'not captured or not removed')

    # 3  pre-processing
    routes = [('magnet', 'F_magnet_rotor', 'pre_magnet', 'magnet_extraction'),
              ('copper', 'F_cu_stream', 'pre_cu', 'winding_separation'),
              ('aluminium', 'F_al_stream', 'pre_al', 'housing_recovery'),
              ('lamination', 'F_steel_stream', 'pre_steel', 'lamination_recovery'),
              ('steel', 'F_steel_stream', 'pre_steel', 'lamination_recovery')]
    for g, out, step, process in routes:
        v = table[step]
        add('F_motor', 'BEV', 'product', out, 'component', g, v, process,
            'disassembly', 'step 3: dehousing, demagnetisation, separation')
        add('F_motor', 'BEV', 'product', 'F_loss_preprocessing', 'component', g,
            inv(v), process, 'disassembly', 'not separated at pre-processing')

    # 4a + 5  extraction and milling
    v = prod(['extract', 'magnet_prep'], table)
    add('F_magnet_rotor', 'BEV', 'product', 'F_magnet_feed', 'component',
        'magnet', v, 'magnet_extraction', 'disassembly',
        'steps 4a-5: extraction x decoat and mill')
    add('F_magnet_rotor', 'BEV', 'product', 'F_loss_extraction', 'component',
        'magnet', inv(v), 'magnet_extraction', 'disassembly',
        'magnet not liberated')

    # ---- the fork -------------------------------------------------------
    if share is None:
        short_feed = 'F_magnet_feed'          # no fork: it all goes short loop
    else:
        short_feed = 'F_shortloop_feed'
        add('F_magnet_feed', 'BEV', 'product', 'F_shortloop_feed', 'component',
            'magnet', share, 'route_split', 'disassembly',
            f'ASSUMPTION, not from the source: {share[1]:.0%} of clean feed to '
            f'the short loop in {horizon}')
        add('F_magnet_feed', 'BEV', 'product', 'F_longloop_feed', 'component',
            'magnet', inv(share), 'route_split', 'disassembly',
            f'the remainder to hydrometallurgy in {horizon}')

    # ---- short loop: the alloy is kept, the elements stay together -------
    v = table['short_loop']
    for element in ELEMENTS:
        add(short_feed, 'magnet', 'component', 'F_recycled_magnet', 'element',
            element, v, 'short_loop', 'hydrogen_decrepitation',
            'step 6a/d: HD/HPMS to new magnet feedstock, alloy intact')
        add(short_feed, 'magnet', 'component', 'F_loss_shortloop', 'element',
            element, inv(v), 'short_loop', 'hydrogen_decrepitation',
            'lost in decrepitation, cleaning and consolidation')
    add(short_feed, 'magnet', 'component', 'F_loss_shortloop', 'element',
        'rest', (1.0, 1.0, 1.0), 'short_loop', 'hydrogen_decrepitation',
        'the iron and boron of the magnet are not a recovery target here')

    # ---- long loop, when there is one -----------------------------------
    if share is not None:
        for element in ELEMENTS:
            v = prod([f'hyd_{element}', f'sx_{element}', f'oxide_{element}'],
                     table)
            add('F_longloop_feed', 'magnet', 'component',
                f'F_{element.lower()}', 'element', element, v, 'ree_recovery',
                'hydrometallurgical',
                'steps 6b-8: leach x solvent extraction x oxide/metal')
            add('F_longloop_feed', 'magnet', 'component', 'F_loss_ree',
                'element', element, inv(v), 'ree_recovery',
                'hydrometallurgical', 'lost in the long loop')
        add('F_longloop_feed', 'magnet', 'component', 'F_loss_ree', 'element',
            'rest', (1.0, 1.0, 1.0), 'ree_recovery', 'hydrometallurgical',
            'the iron and boron of the magnet are not a recovery target here')

    # 9-11  the bulk metals
    metals = [('F_cu_stream', 'copper', 'F_cu_recovered', 'cu_refine',
               'step 9: winding separation and refining'),
              ('F_al_stream', 'aluminium', 'F_al_recovered', 'al_recover',
               'step 10: housing to secondary aluminium'),
              ('F_steel_stream', 'lamination', 'F_steel_recovered',
               'steel_recover', 'step 11: laminations to ferrous scrap'),
              ('F_steel_stream', 'steel', 'F_steel_recovered', 'steel_recover',
               'step 11: shaft and gearbox steel to ferrous scrap')]
    for inflow, g, out, step, note in metals:
        v = table[step]
        process = out.replace('F_', '').replace('_recovered', '_recovery')
        add(inflow, g, 'component', out, 'material', g, v, process,
            'metallurgical', note)
        add(inflow, g, 'component', 'F_loss_metals', 'material', g, inv(v),
            process, 'metallurgical', 'lost in separation and melting')
    return pd.DataFrame(rows)


def processes_for(share):
    rows = [
        ('F_collected', 'F_motor', 'motor_recovery', 'dismantling', 'component', 'intermediate'),
        ('F_collected', 'F_loss_upstream', 'motor_recovery', 'dismantling', 'component', 'loss'),
        ('F_motor', 'F_magnet_rotor', 'magnet_extraction', 'disassembly', 'component', 'intermediate'),
        ('F_motor', 'F_cu_stream', 'winding_separation', 'disassembly', 'component', 'intermediate'),
        ('F_motor', 'F_al_stream', 'housing_recovery', 'disassembly', 'component', 'intermediate'),
        ('F_motor', 'F_steel_stream', 'lamination_recovery', 'disassembly', 'component', 'intermediate'),
        ('F_motor', 'F_loss_preprocessing', 'magnet_extraction', 'disassembly', 'component', 'loss'),
        ('F_magnet_rotor', 'F_magnet_feed', 'magnet_extraction', 'disassembly', 'component', 'intermediate'),
        ('F_magnet_rotor', 'F_loss_extraction', 'magnet_extraction', 'disassembly', 'component', 'loss'),
    ]
    short_feed = 'F_magnet_feed' if share is None else 'F_shortloop_feed'
    if share is not None:
        rows += [
            ('F_magnet_feed', 'F_shortloop_feed', 'route_split', 'disassembly', 'component', 'intermediate'),
            ('F_magnet_feed', 'F_longloop_feed', 'route_split', 'disassembly', 'component', 'intermediate'),
        ]
        for el in ELEMENTS:
            rows.append(('F_longloop_feed', f'F_{el.lower()}', 'ree_recovery',
                         'hydrometallurgical', 'element', 'recovered'))
        rows.append(('F_longloop_feed', 'F_loss_ree', 'ree_recovery',
                     'hydrometallurgical', 'element', 'loss'))
    rows += [
        (short_feed, 'F_recycled_magnet', 'short_loop', 'hydrogen_decrepitation', 'element', 'recovered'),
        (short_feed, 'F_loss_shortloop', 'short_loop', 'hydrogen_decrepitation', 'element', 'loss'),
        ('F_cu_stream', 'F_cu_recovered', 'cu_recovery', 'metallurgical', 'material', 'recovered'),
        ('F_al_stream', 'F_al_recovered', 'al_recovery', 'metallurgical', 'material', 'recovered'),
        ('F_steel_stream', 'F_steel_recovered', 'steel_recovery', 'metallurgical', 'material', 'recovered'),
        ('F_cu_stream', 'F_loss_metals', 'cu_recovery', 'metallurgical', 'material', 'loss'),
        ('F_al_stream', 'F_loss_metals', 'al_recovery', 'metallurgical', 'material', 'loss'),
        ('F_steel_stream', 'F_loss_metals', 'steel_recovery', 'metallurgical', 'material', 'loss'),
    ]
    return pd.DataFrame(rows, columns=['Input_FlowID', 'Output_FlowID',
                                       'process', 'technology', 'keyed_at',
                                       'role'])


def build(folder: str, share_2030, share_2060) -> None:
    source = pd.DataFrame([
        ('upstream_dir', 'data/processed/traction_recovery_draws'),
        ('flow', 'collected'), ('product', 'BEV'),
        ('inflow_flow_id', 'F_collected'), ('child_layer', 'element'),
        ('group_marker', '__component__'), ('material_suffix', None),
        ('groups', None), ('draws', 200000),
        ('improvement_start', 2030), ('improvement_end', 2060),
    ], columns=['key', 'value'])
    lists = pd.DataFrame({'keyed_at': ['component', 'material', 'element', None],
                          'role': ['recovered', 'loss', 'handoff', 'intermediate']})
    path = f'data_folder/{folder}/input_data/case.xlsx'
    with pd.ExcelWriter(path, engine='openpyxl') as w:
        source.to_excel(w, sheet_name='source', index=False)
        processes_for(share_2060).to_excel(w, sheet_name='processes', index=False)
        lists.to_excel(w, sheet_name='_lists', index=False)
        tc_rows(S30, '2030', share_2030).to_excel(w, sheet_name='TCs', index=False)
        tc_rows(S60, '2060', share_2060).to_excel(w, sheet_name='TCs_improved',
                                                  index=False)
    label = ('pure short loop' if share_2060 is None
             else f'share {share_2030[1]:.0%} -> {share_2060[1]:.0%}')
    print(f'{path}: {label}, {len(tc_rows(S60, "2060", share_2060))} TC rows')


if __name__ == '__main__':
    build('tractionmotor_shortloop', None, None)
    build('tractionmotor_split', SHORT_LOOP_SHARE['2030'],
          SHORT_LOOP_SHARE['2060'])
