"""Build the traction motor disassembly case from the RAWCLIC recycling workbook."""
import pandas as pd

SRC = 'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, TC_2030/2060_Disassembly_Route'

# ---- the chain, as the recycling workbook states it -----------------------
# step: (min, mode, max) for 2030 and for 2060
S30 = {
    'capture':    (0.70, 0.80, 0.90), 'removal':  (0.85, 0.93, 0.98),
    'pre_magnet': (0.80, 0.88, 0.95), 'pre_cu':   (0.90, 0.95, 0.98),
    'pre_al':     (0.92, 0.96, 0.99), 'pre_steel':(0.85, 0.92, 0.97),
    'extract':    (0.70, 0.82, 0.92), 'magnet_prep':(0.88, 0.93, 0.97),
    'hyd_Nd': (0.85, 0.92, 0.97), 'hyd_Pr': (0.83, 0.90, 0.96),
    'hyd_Dy': (0.80, 0.88, 0.95), 'hyd_Tb': (0.78, 0.86, 0.94),
    'sx_Nd':  (0.88, 0.93, 0.98), 'sx_Pr':  (0.86, 0.91, 0.97),
    'sx_Dy':  (0.85, 0.91, 0.97), 'sx_Tb':  (0.83, 0.89, 0.96),
    'oxide_Nd': (0.90, 0.95, 0.98), 'oxide_Pr': (0.90, 0.95, 0.98),
    'oxide_Dy': (0.90, 0.95, 0.98), 'oxide_Tb': (0.90, 0.95, 0.98),
    'cu_refine': (0.82, 0.90, 0.96), 'al_recover': (0.88, 0.93, 0.97),
    'steel_recover': (0.80, 0.88, 0.95),
}
S60 = {
    'capture':    (0.82, 0.90, 0.96), 'removal':  (0.92, 0.97, 0.99),
    'pre_magnet': (0.88, 0.94, 0.98), 'pre_cu':   (0.93, 0.97, 0.99),
    'pre_al':     (0.95, 0.98, 0.99), 'pre_steel':(0.90, 0.95, 0.98),
    'extract':    (0.82, 0.92, 0.97), 'magnet_prep':(0.92, 0.96, 0.99),
    'hyd_Nd': (0.90, 0.96, 0.99), 'hyd_Pr': (0.88, 0.94, 0.98),
    'hyd_Dy': (0.86, 0.93, 0.97), 'hyd_Tb': (0.84, 0.92, 0.97),
    'sx_Nd':  (0.92, 0.96, 0.99), 'sx_Pr':  (0.90, 0.95, 0.99),
    'sx_Dy':  (0.90, 0.95, 0.98), 'sx_Tb':  (0.88, 0.94, 0.98),
    'oxide_Nd': (0.93, 0.97, 0.99), 'oxide_Pr': (0.93, 0.97, 0.99),
    'oxide_Dy': (0.93, 0.97, 0.99), 'oxide_Tb': (0.93, 0.97, 0.99),
    'cu_refine': (0.88, 0.94, 0.98), 'al_recover': (0.92, 0.96, 0.99),
    'steel_recover': (0.85, 0.92, 0.97),
}

def prod(steps, table):
    """Product of several steps, min with min and max with max."""
    lo = mid = hi = 1.0
    for s in steps:
        a, b, c = table[s]
        lo, mid, hi = lo * a, mid * b, hi * c
    return round(lo, 6), round(mid, 6), round(hi, 6)

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
ELEMENTS = ['Nd', 'Pr', 'Dy', 'Tb']

def tc_rows(table):
    rows = []
    def add(inflow, inkey, outflow, tlayer, tkey, v, process, tech, note,
            inlayer='component'):
        lo, mid, hi = v
        rows.append(dict(
            Input_FlowID=inflow, Input_layer=inlayer, Input_layer_key=inkey,
            Output_FlowID=outflow, TC_target_layer=tlayer, TC_target_key=tkey,
            value=mid, value_min=lo, value_max=hi,
            process=process, technology=tech, source=f'{note} [{SRC}]'))

    # 1-2  capture and motor removal, identical for every material
    upstream = prod(['capture', 'removal'], table)
    # ⚠️ KEYED AT PRODUCT, NOT COMPONENT. What reaches F_collected is the
    # vehicle; the coefficient names which COMPONENT of it moves on. Keying
    # the input at component instead left every group stranded at F_collected
    # with no coefficient to move it -- which the checker caught by name.
    for g in GROUPS:
        add('F_collected', 'BEV', 'F_motor', 'component', g, upstream,
            'motor_recovery', 'dismantling',
            'steps 1-2: EoL capture x motor removal', inlayer='product')
        add('F_collected', 'BEV', 'F_loss_upstream', 'component', g,
            (round(1 - upstream[2], 6), round(1 - upstream[1], 6),
             round(1 - upstream[0], 6)),
            'motor_recovery', 'dismantling', 'not captured or not removed',
            inlayer='product')

    # 3  pre-processing splits the motor into streams
    routes = [('magnet', 'F_magnet_rotor', 'pre_magnet', 'magnet_extraction'),
              ('copper', 'F_cu_stream', 'pre_cu', 'winding_separation'),
              ('aluminium', 'F_al_stream', 'pre_al', 'housing_recovery'),
              ('lamination', 'F_steel_stream', 'pre_steel', 'lamination_recovery'),
              ('steel', 'F_steel_stream', 'pre_steel', 'lamination_recovery')]
    # ⚠️ Input_layer_key NAMES THE PARENT OF TC_target_key. A row whose target
    # is a COMPONENT is therefore keyed at the PRODUCT, whatever flow it
    # leaves. Keying it at the component itself -- 'magnet' moving 'magnet' --
    # matched nothing and left all five stranded at F_motor.
    for g, out, step, process in routes:
        v = table[step]
        add('F_motor', 'BEV', out, 'component', g, v, process, 'disassembly',
            'step 3: dehousing, demagnetisation, stream separation',
            inlayer='product')
        add('F_motor', 'BEV', 'F_loss_preprocessing', 'component', g,
            (round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)),
            process, 'disassembly', 'not separated at pre-processing',
            inlayer='product')

    # 4a + 5  extraction and magnet pre-processing
    v = prod(['extract', 'magnet_prep'], table)
    add('F_magnet_rotor', 'BEV', 'F_magnet_feed', 'component', 'magnet', v,
        'magnet_extraction', 'disassembly',
        'steps 4a-5: extraction x decoat and mill', inlayer='product')
    add('F_magnet_rotor', 'BEV', 'F_loss_extraction', 'component', 'magnet',
        (round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)),
        'magnet_extraction', 'disassembly', 'magnet not liberated',
        inlayer='product')

    # 6b + 7 + 8  the long loop, element by element
    for el in ELEMENTS:
        v = prod([f'hyd_{el}', f'sx_{el}', f'oxide_{el}'], table)
        add('F_magnet_feed', 'magnet', f'F_{el.lower()}', 'element', el, v,
            'ree_recovery', 'hydrometallurgical',
            'steps 6b-8: leach x solvent extraction x oxide/metal')
        add('F_magnet_feed', 'magnet', 'F_loss_ree', 'element', el,
            (round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)),
            'ree_recovery', 'hydrometallurgical', 'lost in the long loop')
    # the magnet is mostly iron and boron: not tracked, not recovered
    add('F_magnet_feed', 'magnet', 'F_loss_ree', 'element', 'rest',
        (1.0, 1.0, 1.0), 'ree_recovery', 'hydrometallurgical',
        'Fe, B, Co and the rest of the magnet: not a recovery target here')

    # 9-11  the bulk metals leave as materials, not elements
    metals = [('F_cu_stream', 'copper', 'F_cu_recovered', 'cu_refine',
               'step 9: winding separation and refining'),
              ('F_al_stream', 'aluminium', 'F_al_recovered', 'al_recover',
               'step 10: housing to secondary aluminium'),
              ('F_steel_stream', 'lamination', 'F_steel_recovered',
               'steel_recover', 'step 11: laminations to ferrous scrap'),
              ('F_steel_stream', 'steel', 'F_steel_recovered', 'steel_recover',
               'step 11: shaft and gearbox steel to ferrous scrap')]
    # ⚠️ TARGETED AT THE MATERIAL LAYER, NOT THE ELEMENT LAYER. Copper,
    # aluminium and the two steels have NO element arrays upstream -- that was
    # the 2026-09-24 decision, they stay materials -- so their mass never
    # reaches the element layer and there is no 'rest' there to catch it. Its
    # deepest filled layer is the material placeholder, which carries the
    # group's own name. Aimed at 'element'/'rest' the coefficients matched
    # nothing and all three metals came out as zero recovered while the magnet
    # worked, because the magnet DOES have element children.
    for inflow, g, out, step, note in metals:
        v = table[step]
        process = out.replace('F_', '').replace('_recovered', '_recovery')
        add(inflow, g, out, 'material', g, v, process, 'metallurgical', note)
        add(inflow, g, 'F_loss_metals', 'material', g,
            (round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)),
            process, 'metallurgical', 'lost in separation and melting')
    return pd.DataFrame(rows)

processes = pd.DataFrame([
    ('F_collected', 'F_motor', 'motor_recovery', 'dismantling', 'component', 'intermediate'),
    ('F_collected', 'F_loss_upstream', 'motor_recovery', 'dismantling', 'component', 'loss'),
    ('F_motor', 'F_magnet_rotor', 'magnet_extraction', 'disassembly', 'component', 'intermediate'),
    ('F_motor', 'F_cu_stream', 'winding_separation', 'disassembly', 'component', 'intermediate'),
    ('F_motor', 'F_al_stream', 'housing_recovery', 'disassembly', 'component', 'intermediate'),
    ('F_motor', 'F_steel_stream', 'lamination_recovery', 'disassembly', 'component', 'intermediate'),
    ('F_motor', 'F_loss_preprocessing', 'magnet_extraction', 'disassembly', 'component', 'loss'),
    ('F_magnet_rotor', 'F_magnet_feed', 'magnet_extraction', 'disassembly', 'component', 'intermediate'),
    ('F_magnet_rotor', 'F_loss_extraction', 'magnet_extraction', 'disassembly', 'component', 'loss'),
    ('F_magnet_feed', 'F_nd', 'ree_recovery', 'hydrometallurgical', 'element', 'recovered'),
    ('F_magnet_feed', 'F_pr', 'ree_recovery', 'hydrometallurgical', 'element', 'recovered'),
    ('F_magnet_feed', 'F_dy', 'ree_recovery', 'hydrometallurgical', 'element', 'recovered'),
    ('F_magnet_feed', 'F_tb', 'ree_recovery', 'hydrometallurgical', 'element', 'recovered'),
    ('F_magnet_feed', 'F_loss_ree', 'ree_recovery', 'hydrometallurgical', 'element', 'loss'),
    ('F_cu_stream', 'F_cu_recovered', 'cu_recovery', 'metallurgical', 'element', 'recovered'),
    ('F_al_stream', 'F_al_recovered', 'al_recovery', 'metallurgical', 'element', 'recovered'),
    ('F_steel_stream', 'F_steel_recovered', 'steel_recovery', 'metallurgical', 'element', 'recovered'),
    ('F_cu_stream', 'F_loss_metals', 'cu_recovery', 'metallurgical', 'element', 'loss'),
    ('F_al_stream', 'F_loss_metals', 'al_recovery', 'metallurgical', 'element', 'loss'),
    ('F_steel_stream', 'F_loss_metals', 'steel_recovery', 'metallurgical', 'element', 'loss'),
], columns=['Input_FlowID', 'Output_FlowID', 'process', 'technology',
            'keyed_at', 'role'])

source = pd.DataFrame([
    ('upstream_dir', 'data/processed/traction_recovery_draws'),
    ('flow', 'collected'),
    ('product', 'BEV'),
    ('inflow_flow_id', 'F_collected'),
    ('child_layer', 'element'),
    ('group_marker', '__component__'),
    ('material_suffix', None),
    ('groups', None),
    ('draws', 200000),
    ('improvement_start', 2030),
    ('improvement_end', 2060),
], columns=['key', 'value'])

lists = pd.DataFrame({'keyed_at': ['component', 'material', 'element', None],
                      'role': ['recovered', 'loss', 'handoff', 'intermediate']})

path = 'data_folder/tractionmotor/input_data/case.xlsx'
with pd.ExcelWriter(path, engine='openpyxl') as w:
    source.to_excel(w, sheet_name='source', index=False)
    processes.to_excel(w, sheet_name='processes', index=False)
    lists.to_excel(w, sheet_name='_lists', index=False)
    tc_rows(S30).to_excel(w, sheet_name='TCs', index=False)
    tc_rows(S60).to_excel(w, sheet_name='TCs_improved', index=False)
print(f'{path}: {len(tc_rows(S30))} TC rows, {len(processes)} processes')
