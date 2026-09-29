"""
Build the traction motor case. This is the only traction builder.

    ./.venv/bin/python tools/build_tractionmotor_case.py
    -> data_folder/tractionmotor/input_data/case.xlsx

ONE CASE, ONE ANSWER. A fleet of end-of-life BEVs does not go one way. Some
motors are taken out of the vehicle and disassembled; the rest stay in the hulk
and go through the shredder with it. This case runs BOTH roads at once and
splits between them at the review's own step 2, so there is one number to read
and not four cases to reconcile.

THE FORK IS STEP 2, AND NOBODY CHOSE IT
---------------------------------------
`RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx`, both disassembly sheets:

    step 1  EoL vehicle collection      0.70 | 0.80 | 0.90   ref 37,38
    step 2  Motor removal from vehicle  0.85 | 0.93 | 0.98   ref 6,7,8,9

    F_collected --step 1--> F_captured --step 2--------> F_removed   disassembly
                \\                                  \\
                 \\-> F_uncollected                  \\-(1 - step 2)-> F_shredded

**What is not removed is shredded, not lost.** DECISIONS 10: nothing is lost by
not being disassembled, it simply travels the other road. The consequence is
worth saying out loud, because it surprises people: **the fleet recovers MORE
than pure disassembly does.** A pure disassembly case writes the unremoved 7%
off as a loss; the fleet sends it to a shredder that gets some of it back.

WHAT USED TO BE HERE, AND WHY IT IS NOT
---------------------------------------
Four separate builders wrote four separate cases -- long loop, short loop,
shredder, split -- each sending 100% of the motors one way. That is four of
every figure and no single answer, and three of the four folders were not even
on disk any more while their builders sat here looking current.

The fleet builder that replaced them then invented a coefficient,
`DISASSEMBLY_SHARE`, and put it ABOVE chains that already applied
capture x removal -- so removal was counted twice on the disassembly road. Two
values were tried and both were a second copy of a step the review already
gives. The check meant to catch it blended at the same invented share the case
was built from, so it compared the case against itself and agreed to within
1.9 pp. There is no share in this file: step 2 IS the share.

The pure routes are still reachable from here -- pin `removal` to (1,1,1) for
disassembly only, or to (0,0,0) for shredder only -- so nothing was lost by
deleting three builders. `git log` has them if the exact files are ever wanted.

NOT HERE ON PURPOSE: the short loop. The workbook gives HD/HPMS no 2030
coefficient at all and calls it "pilot to early commercial". A route with no
coefficient for the near horizon cannot be blended into a fleet; putting it in
would mean inventing the number the review declined to give.

EVERY FLOW SAYS WHICH ROAD IT IS ON. The two chains share nine flow names, and
merging on them would pour the disassembled copper and the shredded copper into
one flow and give the pair a single yield. So every flow below the fork carries
`_dis` or `_shr`. That is also what lets `routes()` find two roads and report
how much came back on each.

⚠️ EVERY COEFFICIENT BELOW IS A SCENARIO ASSUMPTION, NOT A MEASUREMENT. The
review's own section 5.2 table is almost entirely `NR`; the workbook fills the
cells anyway and labels them assumptions. See
`documentation/TractionMotorStudy/README.md`.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

SRC_DIS = ('RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, '
           'TC_2030/2060_Disassembly_Route')
SRC_SHR = ('RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx, '
           'TC_2030/2060_Shredder_Route')

GROUPS = ['magnet', 'copper', 'aluminium', 'lamination', 'steel']
ELEMENTS = ['Nd', 'Pr', 'Dy', 'Tb']
COLUMNS = ['Input_FlowID', 'Output_FlowID', 'process', 'technology',
           'keyed_at', 'role']

# ---- the disassembly chain, as the recycling workbook states it -----------
# step: (min, mode, max) for 2030 and for 2060
DIS30 = {
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
DIS60 = {
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

# ---- the shredder chain ---------------------------------------------------
# ⚠️ ONE DEPARTURE FROM THE WORKBOOK, AND IT IS DELIBERATE. Its 2030 sheet
# gives the shredder magnet chain as 0.02, which is the STEP value quoted as if
# it were the chain -- upstream capture and feed are not applied to it, although
# they are applied to copper (0.784 x 0.75 = 0.588, reported 0.59), to aluminium
# and to steel, and although the 2060 sheet does apply them to the magnet
# (0.882 x 0.30 = 0.265, reported 0.26). Applied consistently the 2030 magnet
# chain is 0.784 x 0.02 = 0.0157. That is what this case uses: being consistent
# with the workbook's own method matters more than matching one cell it rounded
# differently.
#
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
SHR30 = {'feed': (0.95, 0.98, 1.00),
         'magnet_ree': (0.00, 0.02, 0.05),
         'magnet_to_steel': (0.20, 0.35, 0.55),
         'magnet_to_nonferrous': (0.10, 0.15, 0.20),
         'magnet_to_asr': (0.30, 0.40, 0.50),
         'cu': (0.60, 0.75, 0.85), 'al': (0.65, 0.78, 0.88),
         'steel': (0.85, 0.92, 0.97)}
SHR60 = {'feed': (0.95, 0.98, 1.00),
         # controlled shredding after demagnetisation, inline magnetic
         # separation, then hydrometallurgy of the concentrate
         'magnet_ree': (0.15, 0.30, 0.50),
         # derived: the 0.45 the sheet leaves unassigned, split 70:30 as 2030
         'magnet_to_steel': (0.14, 0.315, 0.50),
         'magnet_to_nonferrous': (0.06, 0.135, 0.21),
         'magnet_to_asr': (0.15, 0.25, 0.40),
         'cu': (0.68, 0.80, 0.90), 'al': (0.72, 0.83, 0.92),
         'steel': (0.88, 0.94, 0.98)}


def prod(steps, table):
    """Product of several steps, min with min and max with max."""
    lo = mid = hi = 1.0
    for s in steps:
        a, b, c = table[s]
        lo, mid, hi = lo * a, mid * b, hi * c
    return round(lo, 6), round(mid, 6), round(hi, 6)


def inverse(v):
    """What the step does NOT move on. The two always sum to 1."""
    return round(1 - v[2], 6), round(1 - v[1], 6), round(1 - v[0], 6)


# ======================================================================
#  Steps 1 and 2: the trunk every motor travels, and the fork at its end
# ======================================================================

def head(table, horizon: str) -> pd.DataFrame:
    """
    Collection, motor removal, and the split removal makes.

    This is the ONLY place steps 1 and 2 appear. Both chains below start at
    their own first process, never at `F_collected`, so no coefficient here is
    applied a second time further down.
    """
    rows = []

    def add(inflow, outflow, value, process, note):
        for group in GROUPS:
            rows.append(dict(
                Input_FlowID=inflow, Input_layer='product',
                Input_layer_key='BEV', Output_FlowID=outflow,
                TC_target_layer='component', TC_target_key=group,
                value=value[1], value_min=value[0], value_max=value[2],
                process=process, technology='dismantling',
                source=f'{note} [{SRC_DIS}]'))

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


HEAD_PROCESSES = pd.DataFrame([
    ('F_collected', 'F_captured', 'collection', 'dismantling', 'component', 'intermediate'),
    ('F_collected', 'F_uncollected', 'collection', 'dismantling', 'component', 'loss'),
    ('F_captured', 'F_removed', 'motor_removal', 'dismantling', 'component', 'intermediate'),
    ('F_captured', 'F_shredded', 'motor_removal', 'dismantling', 'component', 'intermediate'),
    ('F_shredded', 'F_ndfeb_stream_shr', 'shredder_feed', 'shredder', 'component', 'intermediate'),
    ('F_shredded', 'F_cu_stream_shr', 'shredder_feed', 'shredder', 'component', 'intermediate'),
    ('F_shredded', 'F_al_stream_shr', 'shredder_feed', 'shredder', 'component', 'intermediate'),
    ('F_shredded', 'F_steel_stream_shr', 'shredder_feed', 'shredder', 'component', 'intermediate'),
    ('F_shredded', 'F_loss_unfed_shr', 'shredder_feed', 'shredder', 'component', 'loss'),
], columns=COLUMNS)


# ======================================================================
#  Road A: the motor is taken out and taken apart
# ======================================================================

def disassembly_rows(table):
    """Steps 3 onwards. Steps 1-2 are in `head`, never here."""
    rows = []
    def add(inflow, inkey, outflow, tlayer, tkey, v, process, tech, note,
            inlayer='component'):
        lo, mid, hi = v
        rows.append(dict(
            Input_FlowID=inflow, Input_layer=inlayer, Input_layer_key=inkey,
            Output_FlowID=outflow, TC_target_layer=tlayer, TC_target_key=tkey,
            value=mid, value_min=lo, value_max=hi,
            process=process, technology=tech, source=f'{note} [{SRC_DIS}]'))

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
            inverse(v), process, 'disassembly',
            'not separated at pre-processing', inlayer='product')

    # 4a + 5  extraction and magnet pre-processing
    v = prod(['extract', 'magnet_prep'], table)
    add('F_magnet_rotor', 'BEV', 'F_magnet_feed', 'component', 'magnet', v,
        'magnet_extraction', 'disassembly',
        'steps 4a-5: extraction x decoat and mill', inlayer='product')
    add('F_magnet_rotor', 'BEV', 'F_loss_extraction', 'component', 'magnet',
        inverse(v), 'magnet_extraction', 'disassembly', 'magnet not liberated',
        inlayer='product')

    # 6b + 7 + 8  the long loop, element by element
    for el in ELEMENTS:
        v = prod([f'hyd_{el}', f'sx_{el}', f'oxide_{el}'], table)
        add('F_magnet_feed', 'magnet', f'F_{el.lower()}', 'element', el, v,
            'ree_recovery', 'hydrometallurgical',
            'steps 6b-8: leach x solvent extraction x oxide/metal')
        add('F_magnet_feed', 'magnet', 'F_loss_ree', 'element', el,
            inverse(v), 'ree_recovery', 'hydrometallurgical',
            'lost in the long loop')
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
        add(inflow, g, 'F_loss_metals', 'material', g, inverse(v),
            process, 'metallurgical', 'lost in separation and melting')
    return pd.DataFrame(rows)


DIS_PROCESSES = pd.DataFrame([
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
], columns=COLUMNS)


# ======================================================================
#  Road B: the motor stays in the hulk and is shredded with it
# ======================================================================

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
                source=f'{note} [{SRC_SHR}]'))
    return pd.DataFrame(rows)


def shredder_rows(table):
    """Step 3 onwards. Capture is in `head`, the feed in `feed`."""
    rows = []

    def add(inflow, inkey, inlayer, outflow, tlayer, tkey, v, process, note):
        lo, mid, hi = v
        rows.append(dict(
            Input_FlowID=inflow, Input_layer=inlayer, Input_layer_key=inkey,
            Output_FlowID=outflow, TC_target_layer=tlayer, TC_target_key=tkey,
            value=mid, value_min=lo, value_max=hi, process=process,
            technology='shredder', source=f'{note} [{SRC_SHR}]'))

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
        # would exceed their own parents. The disassembly chain already keeps
        # F_loss_ree and F_loss_metals apart for the same reason.
        add(inflow, g, 'component', 'F_loss_metals', 'material', g,
            inverse(v), process, 'lost to residue, mixing and melt')
    return pd.DataFrame(rows)


SHR_PROCESSES = pd.DataFrame([
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
], columns=COLUMNS)


# ======================================================================
#  Putting the two roads in one network
# ======================================================================

def road(name: str, suffix: str, entry: dict) -> str:
    """Put a flow on one road. The head's own flows keep their names."""
    return entry.get(name, f'{name}_{suffix}')


def rename(frame: pd.DataFrame, suffix: str, entry: dict) -> pd.DataFrame:
    out = frame.copy()
    for column in ('Input_FlowID', 'Output_FlowID'):
        out[column] = [road(str(v), suffix, entry) for v in out[column]]
    return out


# The disassembly chain calls its first flow `F_motor`; the head calls the same
# thing `F_removed`, because that is what step 2 produces. One name, chosen in
# one place.
DIS_ENTRY = {'F_motor': 'F_removed'}


def tcs_for(horizon: str) -> pd.DataFrame:
    dis = DIS30 if horizon == '2030' else DIS60
    shr = SHR30 if horizon == '2030' else SHR60
    return pd.concat([
        head(dis, horizon),
        rename(disassembly_rows(dis), 'dis', DIS_ENTRY),
        feed(shr, horizon),
        rename(shredder_rows(shr), 'shr', {}),
    ], ignore_index=True)


def processes_for() -> pd.DataFrame:
    return pd.concat([HEAD_PROCESSES,
                      rename(DIS_PROCESSES, 'dis', DIS_ENTRY),
                      rename(SHR_PROCESSES, 'shr', {})],
                     ignore_index=True)[COLUMNS]


SOURCE = pd.DataFrame([
    ('upstream_dir', 'data/processed/traction_recovery_draws'),
    ('flow', 'collected'), ('product', 'BEV'),
    ('inflow_flow_id', 'F_collected'), ('child_layer', 'element'),
    ('group_marker', '__component__'), ('material_suffix', None),
    ('groups', None), ('draws', 200000),
    ('improvement_start', 2030), ('improvement_end', 2060),
    # ⚠️ FLAT UNTIL 2030, THEN IT NEVER GOES FLAT AGAIN. `improvement_start`
    # holds the 2030 table until 2030 -- nothing improves before the year the
    # study says improvement begins. `continue` then carries the 2030-2060
    # rate of change past 2060 instead of stopping dead there: 2060 is the year
    # the review happens to publish a second table, not the year recycling
    # stops getting better. Asked for on 2026-09-29.
    #
    # Over this horizon that is one extra third of a ramp (2070 is weight
    # 1.33). Stage 01 checks every solved year stays inside [0, 1].
    ('improvement_after_end', 'continue'),
    # ⚠️ SO 05 CAN ADD THIS CASE. `05_combine_cases.py` runs over the
    # BATTERY's scenarios, S1/S2/S3, and asks every case for each of them in
    # turn. This case has one export, `mix` -- the magnet grade drawn per draw
    # -- and a rare earth does not depend on a cathode chemistry, so every
    # name maps to it. The electronics cases have carried the same declaration
    # as `*=BAU` since 2026-09-17; without it, adding this case to `combine`
    # fails looking for a folder called S1.
    ('scenario_alias', '*=mix'),
], columns=['key', 'value'])

LISTS = pd.DataFrame({'keyed_at': ['component', 'material', 'element', None],
                      'role': ['recovered', 'loss', 'handoff', 'intermediate']})

FOLDER = 'data_folder/tractionmotor'


def main() -> int:
    os.makedirs(f'{FOLDER}/input_data', exist_ok=True)
    tcs, processes = tcs_for('2030'), processes_for()

    path = f'{FOLDER}/input_data/case.xlsx'
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        SOURCE.to_excel(writer, sheet_name='source', index=False)
        processes.to_excel(writer, sheet_name='processes', index=False)
        LISTS.to_excel(writer, sheet_name='_lists', index=False)
        tcs.to_excel(writer, sheet_name='TCs', index=False)
        tcs_for('2060').to_excel(writer, sheet_name='TCs_improved', index=False)

    for horizon, table in (('2030', DIS30), ('2060', DIS60)):
        low, mode, high = table['removal']
        print(f'  {horizon}: step 2 removal {mode} [{low}-{high}] '
              f'-> disassembly;  {round(1 - mode, 2)} -> shredder')
    print(f'{path}: {len(tcs)} TC rows, {len(processes)} processes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
