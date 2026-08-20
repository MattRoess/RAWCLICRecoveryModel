"""
make_tc_skeleton.py
===================

Write a TCs.csv with every row that needs a number, and no numbers in it.

    ./.venv/bin/python make_tc_skeleton.py data_folder/bev_electronics

The flow network is domain knowledge and this script does not invent it. It
reads a small, editable list of processes and expands it against the resources
the composition actually contains:

    <case>/input_data/processes.csv     you edit this -- seven lines, not 140
    <case>/input_data/composition.csv   supplies the resources
        |
        v
    <case>/input_data/TCs.csv           one row per coefficient, values blank

Edit the process list and run this again. It refuses to overwrite a TCs.csv
that already has values in it, so a table you have started filling in cannot be
destroyed by a stray run.

WHAT A PROCESS LINE SAYS
------------------------
    Input_FlowID,Output_FlowID,process,technology,keyed_at,is_loss

`keyed_at` is the layer whose yield actually differs, and it decides which rows
get written (MODEL_MECHANICS.md section 3):

    component   dismantling separates whole components -- a harness comes out
                or it does not. One row per (product, component). The element
                detail rides along, because a coarse coefficient scales the
                resource's whole subtree.

    element     refining and shredding have yields that differ per element --
                copper from a harness behaves nothing like gold from a board.
                One row per (material, element).

Do not key a process finer than the physics justifies. It multiplies the rows
you have to fill in without adding information.

WHY `rest` GETS ROWS TOO
------------------------
Most of the mass is unspecified: on the real 2040 collected flow, 71% of the
motors, 57% of the sensors and 25% of the boards. Left without coefficients it
rides through the coarse processes and then strands in an intermediate flow,
where totalling the terminal flows never sees it (src/rest.py).

Glass and plastics genuinely are lost, so 1.0 into the loss flow is usually the
right answer -- but it should be written down rather than assumed.

WHAT TO FILL IN
---------------
`value` is the mode, `value_min` and `value_max` the ends of the triangular
range. Bounds outside [0, 1] are pulled to the boundary; a range of zero width
is a coefficient you are certain about.

For each resource, the values across its destinations should sum to 1 -- that
is what makes mass balance checkable rather than aspirational. Check it with:

    ./.venv/bin/python 02_check_mass_balance.py <case>
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rest import add_rest

COLUMNS = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
           'Output_FlowID', 'TC_target_layer', 'TC_target_key',
           'value', 'value_min', 'value_max', 'process', 'technology']

# The layer a coefficient reads FROM, given the layer it targets. A component
# coefficient is keyed on the product it sits in, an element coefficient on its
# material -- which is what makes it "copper as found in a harness" rather than
# copper everywhere.
INPUT_LAYER_FOR = {'component': 'product', 'material': 'component',
                   'element': 'material'}

LAYER_COLUMN = {'product': 'Layer 1', 'component': 'Layer 2',
                'material': 'Layer 3', 'element': 'Layer 4'}

# A starting point, not a proposal about your system. Seven lines: three ways
# out of the collected flow, then one recovery and one loss per treatment.
DEFAULT_PROCESSES = """\
Input_FlowID,Output_FlowID,process,technology,keyed_at,is_loss
F_collected,F_dismantled,dismantling,manual,component,0
F_collected,F_shredded,dismantling,manual,component,0
F_collected,F_loss_dismantling,dismantling,manual,component,1
F_dismantled,F_refined,refining,pyro,element,0
F_dismantled,F_loss_refining,refining,pyro,element,1
F_shredded,F_recovered_shredder,shredding,hammer_mill,element,0
F_shredded,F_loss_shredding,shredding,hammer_mill,element,1
"""


def resources_at(composition: pd.DataFrame, keyed_at: str) -> list[tuple[str, str]]:
    """
    Every (parent key, target key) pair a process at this layer must cover.

    Taken from the composition rather than from a list, so a resource that
    exists in the data cannot be left without a coefficient by oversight.
    """
    target = LAYER_COLUMN[keyed_at]
    parent = LAYER_COLUMN[INPUT_LAYER_FOR[keyed_at]]
    rows = composition[(composition[target] != '') & (composition[parent] != '')]

    # Rows deeper than the target layer describe something else and would
    # duplicate the pair.
    deeper = [column for layer, column in LAYER_COLUMN.items()
              if list(LAYER_COLUMN).index(layer) > list(LAYER_COLUMN).index(keyed_at)]
    for column in deeper:
        rows = rows[rows[column] == '']

    return sorted({(row[parent], row[target]) for _, row in rows.iterrows()})


def build(case: str) -> pd.DataFrame:
    """Expand the process list against the resources in the composition."""
    input_dir = os.path.join(case, 'input_data')

    processes_path = os.path.join(input_dir, 'processes.csv')
    if not os.path.exists(processes_path):
        with open(processes_path, 'w') as handle:
            handle.write(DEFAULT_PROCESSES)
        print(f'{processes_path}: written as a starting point. EDIT IT -- it is a')
        print('  placeholder network, not a description of your system.')

    processes = pd.read_csv(processes_path, keep_default_na=False, na_values=[])

    composition = pd.read_csv(os.path.join(input_dir, 'composition.csv'),
                              keep_default_na=False, na_values=[])
    # rest is a resource like any other and needs coefficients like any other.
    composition, _ = add_rest(composition)

    rows = []
    for _, step in processes.iterrows():
        keyed_at = str(step['keyed_at']).strip()
        if keyed_at not in INPUT_LAYER_FOR:
            raise ValueError(
                f"processes.csv: keyed_at={keyed_at!r} for "
                f"{step['Input_FlowID']} -> {step['Output_FlowID']}. "
                f"Must be one of {', '.join(INPUT_LAYER_FOR)}.")

        for parent_key, target_key in resources_at(composition, keyed_at):
            rows.append({
                'Input_FlowID': step['Input_FlowID'],
                'Input_layer': INPUT_LAYER_FOR[keyed_at],
                'Input_layer_key': parent_key,
                'Output_FlowID': step['Output_FlowID'],
                'TC_target_layer': keyed_at,
                'TC_target_key': target_key,
                'value': '', 'value_min': '', 'value_max': '',
                'process': step.get('process', ''),
                'technology': step.get('technology', ''),
            })

    return pd.DataFrame(rows, columns=COLUMNS)


def main(case: str) -> int:
    path = os.path.join(case, 'input_data', 'TCs.csv')

    if os.path.exists(path):
        existing = pd.read_csv(path, keep_default_na=False, na_values=[])
        filled = (existing['value'].astype(str).str.strip() != '').sum() \
            if 'value' in existing.columns else 0
        if filled:
            print(f'{path} already has {filled} filled-in values. Not overwriting.',
                  file=sys.stderr)
            print('Delete it first if you really mean to start again.', file=sys.stderr)
            return 1

    skeleton = build(case)
    skeleton.to_csv(path, index=False)

    print(f'\n{path}: {len(skeleton)} rows to fill in')
    for keyed_at, group in skeleton.groupby('TC_target_layer', sort=False):
        print(f'  {len(group):4d} keyed at {keyed_at}')

    # The number that actually has to sum to 1 is per resource, over the output
    # flows it reaches -- not per row (MODEL_MECHANICS.md section 4).
    resources = skeleton.groupby(
        ['Input_FlowID', 'Input_layer_key', 'TC_target_key']).ngroups
    print(f'\n  {resources} distinct resources, each of whose coefficients')
    print('  should sum to 1 across its destinations.')
    print(f'\n  Edit {os.path.join(case, "input_data", "processes.csv")} and run this')
    print('  again to change the network. Then fill in value, value_min and')
    print('  value_max, and check with:')
    print(f'    ./.venv/bin/python 02_check_mass_balance.py {case}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else 'data_folder/bev_electronics'))
