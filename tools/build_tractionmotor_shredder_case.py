"""
Build the traction motor SHREDDER case from the RAWCLIC recycling workbook.

Route B of the review: the motor is shredded without magnet extraction. Two
stages only -- capture and shredder feed, then the shredder itself -- because
the review gives the magnet's fate as one end-to-end coefficient from shredder
feed to recovered rare earth, not as a chain of separable steps.

⚠️ ONE DEPARTURE FROM THE WORKBOOK, AND IT IS DELIBERATE. Its 2030 sheet gives
the shredder magnet chain as 0.02, which is the STEP value quoted as if it were
the chain -- upstream capture and feed are not applied to it, although they are
applied to copper (0.784 x 0.75 = 0.588, reported 0.59), to aluminium and to
steel, and although the 2060 sheet does apply them to the magnet
(0.882 x 0.30 = 0.265, reported 0.26). Applied consistently the 2030 magnet
chain is 0.784 x 0.02 = 0.0157. That is what this case uses: being consistent
with the workbook's own method matters more than matching one cell it rounded
differently.
"""
import pandas as pd

SRC = 'RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, TC_2030/2060_Shredder_Route'

# ⚠️ WHERE THE UNRECOVERED MAGNET PHYSICALLY GOES, added 2026-09-25 at
# Matthias's request: "going to steel then REE are lost".
#
# The workbook's 2030 sheet splits the shredded NdFeB across three fates --
# 0.35 to the ferrous fraction, 0.15 to non-ferrous, 0.40 to shredder residue
# -- and gives a fourth row, step 4, for what the ferrous stream yields once it
# reaches the steel melt: 0.0 | 0.01 | 0.03. Its own note says the rare earth
# reports to slag.
#
# THE FERROUS PATH IS MODELLED AND TERMINATES AS LOSS. Step 4's 0.01 is NOT
# taken as recovery: the material ends in the steel, and the rare earth in it
# is lost as rare earth. What the split buys is that the model can now say
# WHERE the magnet went -- into steel, into non-ferrous, into residue -- rather
# than reporting one undifferentiated loss. For a material-flow model that is
# the difference between "lost" and "lost into the steel scrap stream".
#
# ⚠️ THE 2060 SPLIT IS DERIVED, NOT GIVEN. That sheet states only recovery
# (0.30) and residue (0.25); it is silent on ferrous and non-ferrous. The
# remaining 0.45 is divided in 2030's own ferrous:non-ferrous ratio of 70:30.
# The ramp requires both tables to name the same coefficients, so a row cannot
# simply be absent for one horizon.
S30 = {'capture': (0.70, 0.80, 0.90), 'feed': (0.95, 0.98, 1.00),
       'magnet_ree': (0.00, 0.02, 0.05),
       'magnet_to_steel': (0.20, 0.35, 0.55),
       'magnet_to_nonferrous': (0.10, 0.15, 0.20),
       'magnet_to_asr': (0.30, 0.40, 0.50),
       'cu': (0.60, 0.75, 0.85), 'al': (0.65, 0.78, 0.88),
       'steel': (0.85, 0.92, 0.97)}
S60 = {'capture': (0.82, 0.90, 0.96), 'feed': (0.95, 0.98, 1.00),
       # controlled shredding after demagnetisation, inline magnetic
       # separation, then hydrometallurgy of the concentrate
       'magnet_ree': (0.15, 0.30, 0.50),
       # derived: the 0.45 the sheet leaves unassigned, split 70:30 as 2030
       'magnet_to_steel': (0.14, 0.315, 0.50),
       'magnet_to_nonferrous': (0.06, 0.135, 0.21),
       'magnet_to_asr': (0.15, 0.25, 0.40),
       'cu': (0.68, 0.80, 0.90), 'al': (0.72, 0.83, 0.92),
       'steel': (0.88, 0.94, 0.98)}

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
ELEMENTS = ['Nd', 'Pr', 'Dy', 'Tb']


def inverse(v):
    return round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)


def tc_rows(table):
    rows = []

    def add(inflow, inkey, inlayer, outflow, tlayer, tkey, v, process, note):
        lo, mid, hi = v
        rows.append(dict(
            Input_FlowID=inflow, Input_layer=inlayer, Input_layer_key=inkey,
            Output_FlowID=outflow, TC_target_layer=tlayer, TC_target_key=tkey,
            value=mid, value_min=lo, value_max=hi, process=process,
            technology='shredder', source=f'{note} [{SRC}]'))

    # ⚠️ ONE FLOW PER STREAM, NOT ONE SHARED SHREDDER FLOW. The first version
    # sent everything to a single F_shredder_feed and let the magnet leave at
    # the element layer while the metals left at the material layer. The
    # checker then evaluated the material layer for every resource at that flow
    # and found the magnet stranded there with no coefficient -- correctly, and
    # invisibly in the disassembly case only because its magnet flow had no
    # material-layer targets to trigger the check. Separate flows keep each
    # stream at one layer, and match the disassembly case's shape.
    up = (round(table['capture'][0] * table['feed'][0], 6),
          round(table['capture'][1] * table['feed'][1], 6),
          round(table['capture'][2] * table['feed'][2], 6))
    streams = [('magnet', 'F_ndfeb_stream'), ('copper', 'F_cu_stream'),
               ('aluminium', 'F_al_stream'), ('lamination', 'F_steel_stream'),
               ('steel', 'F_steel_stream')]
    for g, stream in streams:
        add('F_collected', 'BEV', 'product', stream, 'component', g, up,
            'motor_recovery',
            'steps 1-2: EoL capture x motor to shredder, then sorted')
        add('F_collected', 'BEV', 'product', 'F_loss_upstream', 'component', g,
            inverse(up), 'motor_recovery', 'not captured or not fed')

    # 3  the shredder's own coefficient. The review gives the magnet's fate as
    #    ONE end-to-end number from shredder feed to recovered rare earth, not
    #    as a separable chain, and the same number for all four elements --
    #    it reports "NdFeB to recovered REE", never per element.
    fates = [('F_nd_pr_dy_tb', table['magnet_ree'], 'ree_recovery',
              'step 3: NdFeB to recovered rare earth, end to end'),
             ('F_ree_in_steel', table['magnet_to_steel'], 'steel_melt',
              'step 3-4: to the ferrous fraction and into the steel melt. '
              'The rare earth reports to slag and is LOST as rare earth -- '
              "step 4's 0.01 recoverable is not taken"),
             ('F_ree_in_nonferrous', table['magnet_to_nonferrous'],
              'nonferrous_sorting',
              'step 3: fragments carried into the non-ferrous concentrate'),
             ('F_ree_in_asr', table['magnet_to_asr'], 'shredder_residue',
              'step 3: fines into automotive shredder residue')]
    # what the four fates leave unassigned closes the group
    assigned = [sum(f[1][i] for f in fates) for i in range(3)]
    remainder = (round(max(0.0, 1 - assigned[2]), 6),
                 round(max(0.0, 1 - assigned[1]), 6),
                 round(max(0.0, 1 - assigned[0]), 6))
    for element in ELEMENTS:
        for outflow, v, process, note in fates:
            target = (f'F_{element.lower()}' if outflow == 'F_nd_pr_dy_tb'
                      else outflow)
            add('F_ndfeb_stream', 'magnet', 'component', target, 'element',
                element, v, process, note)
        add('F_ndfeb_stream', 'magnet', 'component', 'F_loss_shredding',
            'element', element, remainder, 'ree_recovery',
            'the fates the sheet does not assign')
    add('F_ndfeb_stream', 'magnet', 'component', 'F_loss_shredding',
        'element', 'rest', (1.0, 1.0, 1.0), 'ree_recovery',
        'Fe, B, Co and the rest of the magnet: not a recovery target here')

    # the bulk metals, at the material layer -- they have no element arrays
    metals = [('F_cu_stream', 'copper', 'F_cu_recovered', 'cu', 'cu_recovery',
               'step 3: copper to the non-ferrous fraction'),
              ('F_al_stream', 'aluminium', 'F_al_recovered', 'al',
               'al_recovery', 'step 3: aluminium to the non-ferrous fraction'),
              ('F_steel_stream', 'lamination', 'F_steel_recovered', 'steel',
               'steel_recovery', 'step 3: laminations to the ferrous fraction'),
              ('F_steel_stream', 'steel', 'F_steel_recovered', 'steel',
               'steel_recovery', 'step 3: shaft and gearbox steel to ferrous')]
    for inflow, g, out, key, process, note in metals:
        v = table[key]
        add(inflow, g, 'component', out, 'material', g, v, process, note)
        # ⚠️ A SEPARATE LOSS FLOW FOR THE METALS. One shared F_loss_shredding
        # was written at the element layer by the magnet and at the material
        # layer by the metals, which breaks the nesting invariant -- deep rows
        # would exceed their own parents. The disassembly case already keeps
        # F_loss_ree and F_loss_metals apart for the same reason.
        add(inflow, g, 'component', 'F_loss_metals', 'material', g,
            inverse(v), process, 'lost to residue, mixing and melt')
    return pd.DataFrame(rows)


processes = pd.DataFrame([
    ('F_collected', 'F_ndfeb_stream', 'motor_recovery', 'shredder', 'component', 'intermediate'),
    ('F_collected', 'F_cu_stream', 'motor_recovery', 'shredder', 'component', 'intermediate'),
    ('F_collected', 'F_al_stream', 'motor_recovery', 'shredder', 'component', 'intermediate'),
    ('F_collected', 'F_steel_stream', 'motor_recovery', 'shredder', 'component', 'intermediate'),
    ('F_collected', 'F_loss_upstream', 'motor_recovery', 'shredder', 'component', 'loss'),
    ('F_ndfeb_stream', 'F_nd', 'ree_recovery', 'shredder', 'element', 'recovered'),
    ('F_ndfeb_stream', 'F_pr', 'ree_recovery', 'shredder', 'element', 'recovered'),
    ('F_ndfeb_stream', 'F_dy', 'ree_recovery', 'shredder', 'element', 'recovered'),
    ('F_ndfeb_stream', 'F_tb', 'ree_recovery', 'shredder', 'element', 'recovered'),
    ('F_ndfeb_stream', 'F_ree_in_steel', 'steel_melt', 'shredder', 'element', 'loss'),
    ('F_ndfeb_stream', 'F_ree_in_nonferrous', 'nonferrous_sorting', 'shredder', 'element', 'loss'),
    ('F_ndfeb_stream', 'F_ree_in_asr', 'shredder_residue', 'shredder', 'element', 'loss'),
    ('F_ndfeb_stream', 'F_loss_shredding', 'ree_recovery', 'shredder', 'element', 'loss'),
    ('F_cu_stream', 'F_cu_recovered', 'cu_recovery', 'shredder', 'element', 'recovered'),
    ('F_al_stream', 'F_al_recovered', 'al_recovery', 'shredder', 'element', 'recovered'),
    ('F_steel_stream', 'F_steel_recovered', 'steel_recovery', 'shredder', 'element', 'recovered'),
    ('F_cu_stream', 'F_loss_metals', 'cu_recovery', 'shredder', 'material', 'loss'),
    ('F_al_stream', 'F_loss_metals', 'al_recovery', 'shredder', 'material', 'loss'),
    ('F_steel_stream', 'F_loss_metals', 'steel_recovery', 'shredder', 'material', 'loss'),
], columns=['Input_FlowID', 'Output_FlowID', 'process', 'technology',
            'keyed_at', 'role'])

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

path = 'data_folder/tractionmotor_shredder/input_data/case.xlsx'


def write() -> None:
    """Write the case. Under a guard so the MIXED builder can IMPORT this one."""
    with pd.ExcelWriter(path, engine='openpyxl') as w:
        source.to_excel(w, sheet_name='source', index=False)
        processes.to_excel(w, sheet_name='processes', index=False)
        lists.to_excel(w, sheet_name='_lists', index=False)
        tc_rows(S30).to_excel(w, sheet_name='TCs', index=False)
        tc_rows(S60).to_excel(w, sheet_name='TCs_improved', index=False)
    print(f'{path}: {len(tc_rows(S30))} TC rows, {len(processes)} processes')


# ⚠️ GUARDED, so that importing this file does not rewrite the case. The mixed
# case is built by composing THIS chain with the disassembly one
# (`build_tractionmotor_mixed_case.py`), and a second copy of these
# coefficients is a second copy that drifts.
if __name__ == '__main__':
    write()
