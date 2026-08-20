"""
01_make_skeleton.py
===================

Write a TCs.csv with every row that needs a number, and no numbers in it.

    ./.venv/bin/python 01_make_skeleton.py data_folder/bev_electronics

The flow network is domain knowledge and this script does not invent it. It
reads a small, editable list of processes and expands it against the resources
the composition actually contains:

    <case>/input_data/processes.csv     you edit this -- seven lines, not 140
    <case>/input_data/composition.csv   supplies the resources
        |
        v
    <case>/input_data/TCs.csv           one row per coefficient, values blank

Run it again whenever the case grows. It **merges**: every value already filled
in is kept, rows for new resources are added blank, and rows whose resource no
longer exists are dropped. So the intended way to work is one component at a
time --

    import_domains = ('Wiring',)             one domain, eight rows, run it
    import_domains = ('Wiring', 'Motors')    re-import, re-run this, fill the new rows
    import_domains = ()                      all of them

-- rather than facing the whole table at once. Nothing you have filled in is
ever overwritten by this script.

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

WHY `rest` GETS ROWS TOO, AND WHY THEY COME FILLED IN
-----------------------------------------------------
Most of the mass is unspecified: on the real 2040 collected flow, 71% of the
motors, 57% of the sensors and 25% of the boards. Left without coefficients it
rides through the coarse processes and then strands in an intermediate flow,
where totalling the terminal flows never sees it (src/rest.py).

Unspecified material is glass, plastics and the like, and those genuinely are
lost -- so the rest rows are written as 1.0 into the process's loss flow and 0
into every other destination. That is a decision, not a default that happened:
it makes every recovery figure a **lower bound**, which is the honest reading
when you do not know what the material is.

The range is zero width, because this is not an uncertain coefficient. It is a
statement that unspecified material is not recovered. If you learn otherwise
for a particular process -- steel and aluminium in a shredded hulk are recovered
-- change those rows and give them a real range.

WHAT TO FILL IN
---------------
`value` is the mode, `value_min` and `value_max` the ends of the triangular
range. Bounds outside [0, 1] are pulled to the boundary; a range of zero width
is a coefficient you are certain about.

For each resource, the values across its destinations should sum to 1 -- that
is what makes mass balance checkable rather than aspirational. Check it with:

    ./.venv/bin/python 02_check_inputs.py <case>
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

import pandas as pd


from src.rest import REST, add_rest

COLUMNS = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
           'Output_FlowID', 'TC_target_layer', 'TC_target_key',
           'value', 'value_min', 'value_max', 'is_residual',
           'process', 'technology', 'source']

# `source` and `is_residual` are read by nothing in the loader -- extra columns
# are dropped -- except is_residual, which the sampler uses. They are here
# because a coefficient table without provenance is a table nobody can audit:
# six months on, "0.85" and "0.85 [Smith 2023]" and "0.85 (guessed)" are
# indistinguishable, and only one of them should survive review.

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

    # How many loss destinations each flow has. `rest` is only filled in
    # automatically where there is exactly one: with none there is nowhere to
    # send it, and with several the split is a judgement this script cannot make.
    loss_destinations: dict[str, int] = {}
    for _, step in processes.iterrows():
        flag = str(step.get('is_loss', '')).strip() in ('1', 'True', 'true')
        loss_destinations[step['Input_FlowID']] = \
            loss_destinations.get(step['Input_FlowID'], 0) + int(flag)

    for flow, count in sorted(loss_destinations.items()):
        if count != 1:
            print(f'  NOTE: {flow} has {count} loss destinations, so its `rest` rows '
                  f'are left blank for you to split.')

    # Straight from the upstream draws; there is no composition.csv on disk.
    from src.params_schema import current
    params = current()
    tables = refresh(params, case, quiet=True)
    if tables is None:
        composition = pd.read_csv(os.path.join(input_dir, 'composition.csv'),
                                  keep_default_na=False, na_values=[])
    else:
        composition = tables['composition']
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

        is_loss = str(step.get('is_loss', '')).strip() in ('1', 'True', 'true')

        for parent_key, target_key in resources_at(composition, keyed_at):
            # Unspecified material is treated as unrecovered: all of it to the
            # loss flow, none of it anywhere else, with no spread. See the
            # module docstring for why this is filled in rather than left blank.
            fills_in = target_key == REST and loss_destinations[step['Input_FlowID']] == 1
            value = (1.0 if is_loss else 0.0) if fills_in else ''

            rows.append({
                'Input_FlowID': step['Input_FlowID'],
                'Input_layer': INPUT_LAYER_FOR[keyed_at],
                'Input_layer_key': parent_key,
                'Output_FlowID': step['Output_FlowID'],
                'TC_target_layer': keyed_at,
                'TC_target_key': target_key,
                'value': value, 'value_min': value, 'value_max': value,
                'is_residual': '',
                'process': step.get('process', ''),
                'technology': step.get('technology', ''),
                'source': ('decision: unspecified material is not recovered'
                           if fills_in else ''),
            })

    return pd.DataFrame(rows, columns=COLUMNS)


KEY = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
       'Output_FlowID', 'TC_target_layer', 'TC_target_key']


def merge(existing: pd.DataFrame, skeleton: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Keep what is filled in, add what is new, drop what no longer exists.

    This is what makes growing a case one component at a time possible. A value
    someone has entered is never overwritten -- not even by the `rest` rows this
    script fills in itself, because they might have been deliberately changed.

    Returns the merged table and a count of what happened to it.
    """
    filled = existing[existing['value'].astype(str).str.strip() != ''] \
        if 'value' in existing.columns else existing.iloc[0:0]
    known = filled.set_index(KEY) if len(filled) else None

    merged, kept, added = [], 0, 0
    for _, row in skeleton.iterrows():
        key = tuple(row[column] for column in KEY)
        if known is not None and key in known.index:
            merged.append(known.loc[key].to_dict() | dict(zip(KEY, key)))
            kept += 1
        else:
            merged.append(row.to_dict())
            added += int(str(row['value']).strip() == '')

    dropped = len(filled) - kept
    return (pd.DataFrame(merged, columns=skeleton.columns),
            {'kept': kept, 'added': added, 'dropped': dropped})


def main(case: str) -> int:
    path = os.path.join(case, 'input_data', 'TCs.csv')
    skeleton = build(case)

    change = {'kept': 0, 'added': int((skeleton['value'].astype(str).str.strip() == '').sum()),
              'dropped': 0}
    if os.path.exists(path):
        existing = pd.read_csv(path, keep_default_na=False, na_values=[], dtype=str)
        skeleton, change = merge(existing, skeleton)

    skeleton.to_csv(path, index=False)

    blank = skeleton['value'].astype(str).str.strip() == ''
    print(f'\n{path}: {len(skeleton)} rows')
    if change['kept']:
        print(f'  {change["kept"]:4d} kept -- already filled in, untouched')
    if change['dropped']:
        print(f'  {change["dropped"]:4d} dropped -- their resource is no longer in the composition')
    print(f'  {int(blank.sum()):4d} still to fill in')
    for keyed_at, group in skeleton[blank].groupby('TC_target_layer', sort=False):
        print(f'       {len(group):4d} keyed at {keyed_at}')

    if not blank.any():
        print('\n  Nothing left to fill. Run it:')
        print('    ./.venv/bin/python 03_run_model.py')
        print('    ./.venv/bin/python 04_run_monte_carlo.py')
        return 0

    resources = skeleton[blank].groupby(
        ['Input_FlowID', 'Input_layer_key', 'TC_target_key']).ngroups
    print(f'\n  {resources} resources still need values, each of whose coefficients')
    print('  should sum to 1 across its destinations. Check with:')
    print(f'    ./.venv/bin/python 02_check_inputs.py {case}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else 'data_folder/bev_electronics'))
