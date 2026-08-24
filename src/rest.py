"""
src/rest.py
===========

Making the unspecified part of a composition explicit.

THE PROBLEM
-----------
Real composition data is incomplete, and incomplete in a particular way: you
often know how much copper is in a wire without knowing what the wire weighs,
or what its insulation weighs. So the shares of a parent do not add up to one.

Until this existed, the model simply accepted that. On `template` with the gold
rows removed, the laminate parent read 400 kg, its known children summed to
340, and **the missing 60 had no row at all**. Nothing was wrong with any
number on the page; the 60 was just absent. Anyone totalling the element rows
would get 340 and reasonably call it the laminate.

THE RULE
--------
    A parent is the sum of the children we know about, plus a rest.

So a `rest` child is derived for every parent whose known children fall short:

    rest = parent - sum(known children)

Written as a share, exactly as every other composition row is. Closure to one
then holds by construction at every layer, the same way explicit loss flows
make the transfer coefficients sum to one (DESIGN_tc_table.md section 1).

It is derived rather than declared on purpose. A rest that has to be written
into the file by hand is a rest that gets forgotten, and forgetting it is
invisible -- which is the failure this module exists to end.

WHY IT IS AT EVERY LAYER, NOT ONLY THE PRODUCT
-----------------------------------------------
One rest per product would be simpler to read, but it could not be given
recovery coefficients that mean anything: unspecified mass sitting in a
dismantled harness is separated quite differently from unspecified mass in a
shredded hulk. Deriving it per parent keeps the *location* of the unknown,
which is what makes it possible to say anything about its fate.

A component whose own mass is unknown gets no row at all -- there is nothing to
take a share of. Whatever is known about it attaches to the product, and the
product's rest is smaller by that much.

WHAT REST DOES NEXT
-------------------
Nothing, unless TCs.csv says so. Unspecified material is treated as unrecovered
by default, which makes every recovery figure a **lower bound** rather than an
estimate. That is the conservative reading and it is deliberately visible:
`rest` appears in the output and in the figures, so a total that is mostly
unspecified cannot be mistaken for a total that is mostly known.
"""
from __future__ import annotations

import pandas as pd

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# The name given to the derived child. Chosen to read as what it is in an
# output table. `validate_rest_name` refuses a dataset that already uses it for
# something real, rather than quietly merging the two.
REST = 'rest'

# How far a parent's shares may fall short of 1 before a rest is derived.
# Below this it is rounding in a hand-written table, not missing data.
TOLERANCE = 1e-9


class RestError(ValueError):
    """Raised when the known parts of a parent exceed the whole."""


# A composition may be given per year, scenario, location or specification.
# Those columns are part of what identifies a parent: the same component has a
# different element split in 2030 and in 2050, and grouping without them adds
# every year together, so a parent's shares sum to the number of years rather
# than to 1.
DIMENSIONS = ['Year', 'Scenario', 'Location', 'additionalSpecification']


def _parent_columns(depth: int, frame: pd.DataFrame) -> list[str]:
    """The columns identifying the parent of a row at this depth."""
    present = [column for column in DIMENSIONS if column in frame.columns]
    return present + ['Stock/ID'] + LAYERS[:depth - 1]


def validate_rest_name(composition: pd.DataFrame) -> None:
    """Refuse a table that already uses the reserved name for a real resource."""
    for layer in LAYERS:
        if layer in composition.columns and (composition[layer] == REST).any():
            raise RestError(
                f"composition.csv uses {REST!r} as a resource name in '{layer}'. "
                f"That name is reserved for the derived remainder "
                f"(src/rest.py). Rename the resource.")


def add_rest(composition: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Derive a `rest` child for every parent whose known children fall short of 1.

    Args:
        composition: the composition table, shares per row

    Returns:
        The table with rest rows appended, and one note per rest derived.

    Raises:
        RestError: if a parent's known children sum to more than 1, which says
            the parts exceed the whole and cannot be repaired by adding a rest.
    """
    validate_rest_name(composition)

    composition = composition.copy()
    composition['Value'] = composition['Value'].astype(float)
    depth = (composition[LAYERS] != '').sum(axis=1)

    added, notes = [], []
    for level in (2, 3, 4):
        at_level = composition[depth == level]
        if at_level.empty:
            continue

        parent = _parent_columns(level, composition)
        totals = at_level.groupby(parent, sort=False)['Value'].sum()

        for key, total in totals.items():
            key = key if isinstance(key, tuple) else (key,)

            if total > 1.0 + TOLERANCE:
                raise RestError(
                    f"composition.csv: the parts of {' / '.join(str(k) for k in key if k)} "
                    f"sum to {total:g}, which is more than the whole. A rest cannot be "
                    f"negative -- correct the shares.")

            if total >= 1.0 - TOLERANCE:
                continue                      # already complete; nothing unknown

            row = dict(zip(parent, key))
            # The rest sits at the layer its siblings sit at, and inherits the
            # parent path above it. Layers below stay empty: a remainder is not
            # decomposed, because by definition nothing is known about it.
            for layer in LAYERS:
                row.setdefault(layer, '')
            row[LAYERS[level - 1]] = REST
            row['Value'] = 1.0 - total
            added.append(row)
            notes.append(f"{' / '.join(str(k) for k in key if k)}: "
                         f"{total:.4g} known, rest {1.0 - total:.4g}")

    if not added:
        return composition, notes

    rest_rows = pd.DataFrame(added).reindex(columns=composition.columns, fill_value='')
    return pd.concat([composition, rest_rows], ignore_index=True), notes


def is_rest(frame: pd.DataFrame) -> pd.Series:
    """True for rows that are, or sit beneath, a derived remainder."""
    return (frame[LAYERS] == REST).any(axis=1)


def terminal_flows(tcs: pd.DataFrame) -> set[str]:
    """Flows that nothing transfers out of."""
    return set(tcs['Output_FlowID']) - set(tcs['Input_FlowID'])


def stranded(solution: pd.DataFrame, tcs: pd.DataFrame) -> pd.DataFrame:
    """
    Mass sitting in a flow that no coefficient moves onward.

    A coarse-layer coefficient carries a resource's whole subtree with it, so a
    `rest` row rides along through dismantling without needing coefficients of
    its own. It stops dead at the first process keyed finer than itself --
    refining and shredding are element-specific, and there is no element called
    `rest` -- and then simply sits in an intermediate flow.

    That is worse than being lost, because it is lost *invisibly*: a reader
    totalling the terminal flows never sees it. On `template` with the gold
    rows removed, 68.4 of 72 kg of rest strands this way.

    Whether a row moves is decided by `src/process_join.py` -- the same
    function the model itself uses -- rather than by inspecting flow names.
    Asking only whether a flow is intermediate is not enough: the rest in the
    collected flow sits in an intermediate flow too, and is transferred
    perfectly well.

    The honest fix is in the data, not here: `rest` is a resource like any
    other and a well-formed table gives it coefficients, exactly as
    DESIGN_tc_table.md section 3 requires of everything else. Generating those
    coefficients automatically would be wrong -- it would double-count the part
    a coarse coefficient already carries. So this reports instead.

    Args:
        solution: a solved frame, with 'Stock/Flow ID', the layers and 'Value'
        tcs: the coefficient table **as the model holds it**, with layers
            already named 'Layer 1'..'Layer 4'

    Returns:
        The stranded rows, most massive first.
    """
    import numpy as np

    from src.process_join import INFLOW_POSITION, TC_POSITION, process_pairs

    ends = terminal_flows(tcs)
    stuck = []

    for flow in sorted(set(tcs['Input_FlowID']) - ends):
        rows = solution[solution['Stock/Flow ID'] == flow].reset_index(drop=True)
        if rows.empty or not is_rest(rows).any():
            continue

        outgoing = tcs[tcs['Input_FlowID'] == flow].reset_index(drop=True)
        outgoing = outgoing.assign(**{TC_POSITION: np.arange(len(outgoing))})

        inflow = rows[LAYERS].copy()
        inflow[INFLOW_POSITION] = np.arange(len(rows))
        pairs = process_pairs(outgoing, inflow)
        moved = set(pairs[INFLOW_POSITION].tolist()) if len(pairs) else set()

        caught = rows[is_rest(rows) & ~rows.index.isin(moved)]
        if len(caught):
            stuck.append(caught)

    if not stuck:
        return solution.iloc[0:0]

    caught = pd.concat(stuck, ignore_index=True)
    caught['Value'] = pd.to_numeric(caught['Value'])
    # Deepest rows only: a rest row and its ancestors describe the same mass.
    depth = (caught[LAYERS] != '').sum(axis=1)
    caught = caught[depth == depth.max()]
    return caught.sort_values('Value', ascending=False)


# ----------------------------------------------------------------------
#  What each terminal flow means
# ----------------------------------------------------------------------

# Read from processes.csv rather than guessed from the flow's name. Guessing
# counted F_separated_electronics as recovered, because the string 'loss' does
# not appear in it -- and that flow is material handed to a SEPARATE recovery
# model, neither recovered here nor lost. It carried no mass at the time, so
# nothing was wrong yet; it would have silently inflated recovery the moment
# boards and sensors were included again.
ROLES = ('recovered', 'loss', 'handoff', 'intermediate')


def flow_roles(case: str) -> dict[str, str]:
    """
    {flow: role} from the case's processes.csv, empty when there is none.

    A flow with no role stated falls back to `is_loss`, and to 'recovered' when
    even that is absent -- so an older table keeps working, just less precisely.
    """
    from src import case_tables

    if not case_tables.exists(case, 'processes'):
        return {}

    processes = case_tables.read(case, 'processes')
    roles: dict[str, str] = {}
    for _, step in processes.iterrows():
        stated = str(step.get('role', '')).strip()
        if stated not in ROLES:
            stated = ('loss' if str(step.get('is_loss', '')).strip() in ('1', 'True', 'true')
                      else 'recovered')
        roles[step['Output_FlowID']] = stated
    return roles


def recovered_flows(case: str, tcs: pd.DataFrame) -> list[str]:
    """Terminal flows whose contents actually count as recovered."""
    roles = flow_roles(case)
    ends = terminal_flows(tcs)
    if not roles:
        return sorted(f for f in ends if 'loss' not in f.lower())
    return sorted(f for f in ends if roles.get(f, 'recovered') == 'recovered')
