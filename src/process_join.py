"""
src/process_join.py
===================

Which transfer coefficient applies to which inflow row, for one process.

This is the join at the centre of the model, and it is here rather than inside
an engine for one reason: the deterministic solve and the Monte Carlo solve must
pair exactly the same rows with exactly the same coefficients. Two copies of
this logic would be two chances to diverge, and this project already has a
record of what that costs -- the two engines came apart on year and scenario
matching for precisely that reason (DEFECTS.md 2.4).

So the join is computed once, as *positions*: which row of the inflow, times
which row of the TC table. What multiplies those positions afterwards is the
caller's business. The deterministic engine multiplies two scalars; the Monte
Carlo multiplies two rows of draws. Same structure, different arithmetic.

WHAT A PROCESS DOES
-------------------
A process takes every row of its input flow and applies the coefficients
defined for it, one (input layer, target layer) pair at a time -- all sixteen
combinations, most of which match nothing.

Two cases, and they behave differently:

  * **Same layer** (component -> component). The resource is carried to another
    flow unchanged, so the join is on the input key alone. A component does not
    become a different component; the loader enforces that the two keys name the
    same resource (DEFECTS.md 2.5).

  * **Different layers** (product -> component). The join is on both keys at
    once, which is what makes a coefficient apply to "component C1 as found
    within product P1" rather than to C1 everywhere. A coarse-layer coefficient
    therefore scales the resource's whole subtree, which is what keeps the
    nesting invariant intact (MODEL_MECHANICS.md section 3).

An empty input key means "every resource at that layer", and is expanded here
against the resources the inflow actually contains.
"""
from __future__ import annotations

import pandas as pd

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# Position of the inflow row, and position of the TC row, that together produce
# an output row. Named with a leading underscore pair so they cannot collide
# with a layer or a flow column coming from the data.
INFLOW_POSITION = '__inflow'
TC_POSITION = '__tc'


def _expand_empty_keys(tcs_layer: pd.DataFrame, process_inflow: pd.DataFrame,
                       input_layer: str, target_layer: str) -> pd.DataFrame:
    """
    Turn an empty `Input_layer_key` into one row per resource present in the
    inflow at that layer.

    An empty key means the coefficient applies to every resource at its layer.
    Expanding against what the inflow actually holds -- rather than against
    every resource in the table -- keeps the result to rows that can exist.
    """
    if not tcs_layer['Input_layer_key'].eq('').any():
        return tcs_layer

    present = [key for key in process_inflow[input_layer].unique() if key != '']
    expanded = tcs_layer.copy()
    expanded['Input_layer_key'] = [
        present if key == '' else [key] for key in expanded['Input_layer_key']]
    expanded = expanded.explode('Input_layer_key')

    # An expansion can collide with a coefficient written out explicitly for the
    # same resource. The explicit one is the more specific statement and wins,
    # which is the same precedence rule applied to the table as a whole in
    # src/tc_precedence.py.
    explicit = set(tcs_layer.loc[tcs_layer['Input_layer_key'] != '', 'Input_layer_key'])
    was_empty = tcs_layer['Input_layer_key'].eq('')
    from_expansion = expanded.index.isin(tcs_layer.index[was_empty])
    keep = ~(from_expansion & expanded['Input_layer_key'].isin(explicit))
    return expanded[keep].reset_index(drop=True)


def process_pairs(process_tcs: pd.DataFrame, process_inflow: pd.DataFrame) -> pd.DataFrame:
    """
    Every (inflow row, coefficient row) pairing this process produces.

    Args:
        process_tcs: the coefficients for one (input flow, output flow), with a
            `TC_POSITION` column giving each row's position in the full TC table
        process_inflow: the contents of the input flow, with an `INFLOW_POSITION`
            column giving each row's position in the flows array. Layer columns
            only -- no 'Stock/Flow ID', which the caller has already selected on.

    Returns:
        One row per pairing: the four layer columns of the resulting resource,
        plus `INFLOW_POSITION` and `TC_POSITION`. Empty if nothing matches.

        Rows where no coefficient matched are absent rather than zero. That is
        the meaningful distinction: a missing coefficient is not a transfer of
        nothing, it is the absence of a route.
    """
    pairings = []

    for input_layer in LAYERS:
        for target_layer in LAYERS:
            selected = process_tcs[(process_tcs['Input_layer'] == input_layer)
                                   & (process_tcs['TC_target_layer'] == target_layer)]
            if selected.empty:
                continue

            if input_layer == target_layer:
                # Carried unchanged: join on the input key only. Joining on the
                # target key instead moved the wrong resource whenever the two
                # differed, silently (DEFECTS.md 2.5).
                tcs_layer = selected[['Input_layer_key', TC_POSITION]].rename(
                    columns={'Input_layer_key': input_layer})
                joined = process_inflow.merge(tcs_layer, on=[input_layer], how='inner')
            else:
                tcs_layer = selected[['Input_layer_key', 'TC_target_key', TC_POSITION]]
                tcs_layer = _expand_empty_keys(tcs_layer, process_inflow,
                                               input_layer, target_layer)
                tcs_layer = tcs_layer.rename(columns={'Input_layer_key': input_layer,
                                                      'TC_target_key': target_layer})
                joined = process_inflow.merge(tcs_layer, on=[input_layer, target_layer],
                                              how='inner')

            if len(joined):
                pairings.append(joined[LAYERS + [INFLOW_POSITION, TC_POSITION]])

    if not pairings:
        return pd.DataFrame(columns=LAYERS + [INFLOW_POSITION, TC_POSITION])
    return pd.concat(pairings, ignore_index=True)
