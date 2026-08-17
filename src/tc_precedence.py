"""
src/tc_precedence.py
====================

Resolve transfer coefficients that describe the same material twice, and say
what was resolved.

THE SITUATION
-------------
A TC row names what it is about on its input side. A row that names a product
is specific; a row that names only a component applies to that component in
*every* product, the specific one included. Write both and one material is
covered twice:

    row 4:  product   BEV      -> component Harness   0.80
    row 7:  component Harness  -> component Harness   0.20

Both cover the harness inside a BEV. The table never says which governs, and
until now each engine guessed differently and silently: the LA engine applied
0.20, the optimized engine added them to 1.00 and reported perfect recovery
(DEFECTS.md 2.3).

THE RULE
--------
**A row that names the parent beats a row that does not.** Row 4 governs the
BEV's harness; row 7 governs every other product's harness. That is what the
two rows look like they mean, and it is now written down rather than left to
whichever engine happens to run.

Specificity is counted as the number of layers a row pins down. A blank key, or
one containing '*', pins nothing -- those are the "applies to everything"
conventions the user guide already defines. Two rows that pin the same number
of layers and still overlap are a genuine ambiguity: those are reported as an
error rather than resolved by a tie-break nobody chose.

WHY IT RUNS BEFORE THE ENGINES
------------------------------
Resolving here, on the table, rather than inside each engine's join logic means
the two engines cannot drift apart again: they are handed the same explicit,
non-overlapping rows. It also makes the report possible, because the decision
is taken in one place where it can be recorded.

WHAT IT DOES NOT DO
-------------------
A TC row can pin at most two layers -- one on the input side, one on the
target. Where an override cannot be written back in that shape, this reports a
conflict rather than inventing a representation the format cannot express.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
LAYER_NAMES = ['product', 'component', 'material', 'element']
LAYER_OF = dict(zip(LAYER_NAMES, LAYERS))


@dataclass
class Decision:
    """One place where more than one rule applied, and what was done."""
    flow: str
    target: str
    material: str
    winner: int          # spreadsheet row number
    winner_value: float
    loser: int
    loser_value: float

    def __str__(self) -> str:
        return (f'  {self.material:<28} row {self.winner} governs '
                f'({self.winner_value:g}), row {self.loser} overridden '
                f'({self.loser_value:g})')


@dataclass
class Conflict:
    """Two rules of equal specificity covering one material. Not resolvable."""
    message: str

    def __str__(self) -> str:
        return f'  {self.message}'


def specificity(row: pd.Series) -> int:
    """
    How many layers a row pins down.

    A blank key, or one containing '*', means "everything at this layer" and
    pins nothing -- both are conventions the user guide already defines.
    """
    pinned = set()
    for layer_column, key_column in (('Input_layer', 'Input_layer_key'),
                                     ('TC_target_layer', 'TC_target_key')):
        key = str(row[key_column]).strip()
        if key and '*' not in key:
            pinned.add(row[layer_column])
    return len(pinned)


def _parents_of(composition: pd.DataFrame, layer: str, key: str) -> list[str]:
    """Every product whose composition contains `key` at `layer`."""
    column = LAYER_OF.get(layer)
    if column is None or column == 'Layer 1':
        return []
    return sorted({product for product, value
                   in zip(composition['Layer 1'], composition[column])
                   if value == key and product})


def resolve(tcs: pd.DataFrame, composition: pd.DataFrame):
    """
    Return (resolved_tcs, decisions, conflicts).

    `resolved_tcs` holds explicit, non-overlapping rows. Where a general rule
    was overridden for one product, it is rewritten as one row per product it
    still governs, so nothing downstream has to know the precedence rule.
    """
    tcs = tcs.copy()
    tcs['_row'] = tcs.index + 2          # spreadsheet row number, for the report
    decisions: list[Decision] = []
    conflicts: list[Conflict] = []
    keep: list[pd.DataFrame] = []

    grouped = tcs.groupby(['Input_FlowID', 'Output_FlowID',
                           'TC_target_layer', 'TC_target_key'], sort=False)

    for (source, target, target_layer, target_key), group in grouped:
        if len(group) == 1:
            keep.append(group)
            continue

        scores = group.apply(specificity, axis=1)
        best = scores.max()
        winners = group[scores == best]
        losers = group[scores < best]

        if len(winners) > 1 and losers.empty:
            # Equally specific rows covering one destination. If they differ
            # only in their input key they are separate resources and fine;
            # otherwise nobody has said which governs.
            if winners['Input_layer_key'].nunique() == len(winners):
                keep.append(group)
                continue
            rows = ', '.join(str(r) for r in winners['_row'])
            conflicts.append(Conflict(
                f'{source} -> {target}: rows {rows} all describe {target_layer} '
                f'{target_key!r} with equal specificity, so none of them takes '
                f'precedence. Give each row a different parent, or delete all '
                f'but one.'))
            continue

        # A more specific row exists. Narrow every less specific one to the
        # products it still governs.
        claimed = {key for key in winners['Input_layer_key'] if key}
        keep.append(winners)

        for _, loser in losers.iterrows():
            parents = _parents_of(composition, target_layer, target_key)
            remaining = [p for p in parents if p not in claimed]

            if not parents:
                conflicts.append(Conflict(
                    f'{source} -> {target}: row {loser["_row"]} is overridden for '
                    f'{target_key!r} but cannot be narrowed, because that '
                    f'{target_layer} appears in no composition row. State the rate '
                    f'per product explicitly.'))
                continue

            for _, winner in winners.iterrows():
                product = winner['Input_layer_key']
                decisions.append(Decision(
                    flow=f'{source} -> {target}',
                    target=target_key,
                    material=f'{target_key} in {product}',
                    winner=winner['_row'], winner_value=winner['value'],
                    loser=loser['_row'], loser_value=loser['value']))

            if not remaining:
                continue        # fully overridden; the row simply disappears

            narrowed = pd.concat([loser.to_frame().T] * len(remaining), ignore_index=True)
            narrowed['Input_layer'] = 'product'
            narrowed['Input_layer_key'] = remaining
            keep.append(narrowed)

    resolved = pd.concat(keep, ignore_index=True) if keep else tcs.iloc[0:0]
    return resolved.drop(columns=['_row'], errors='ignore'), decisions, conflicts


def underspecified(tcs: pd.DataFrame, composition: pd.DataFrame) -> list[str]:
    """
    Materials running on a rule that does not name their parent.

    Not a problem in itself -- it is the documented way to give one rate to
    everything -- but it is worth seeing, because a product added later will
    silently inherit it.
    """
    lines = []
    for row in tcs.itertuples():
        key = str(row.Input_layer_key).strip()
        if key and '*' not in key:
            continue
        parents = _parents_of(composition, row.TC_target_layer, row.TC_target_key)
        if not parents:
            continue
        lines.append(f'  {row.TC_target_key} in {", ".join(parents)}'
                     f'  -- {row.value:g} from row {row.Index + 2}, '
                     f'which names no product')
    return lines


def report(decisions: list[Decision], conflicts: list[Conflict],
           under: list[str]) -> None:
    """Print what was resolved and what is running on a general rule."""
    if decisions:
        print(f'\nTC RESOLUTION -- {len(decisions)} place(s) where more than '
              f'one rule applied')
        for decision in decisions:
            print(decision)
        print('  The rule: a row naming the parent beats a row that does not.')

    if under:
        print('\nUNDER-SPECIFIED -- covered by a rule that names no parent')
        for line in under:
            print(line)
        print('  Not a problem in itself, but a product added later inherits '
              'these silently.')


def apply_precedence(tcs: pd.DataFrame, composition: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve overlapping rules, say what was done, and hand back explicit rows.

    This is what both engines call. Anything that cannot be resolved is raised
    rather than guessed -- the whole point is that no result should depend on
    which engine happened to run.
    """
    from src.validate_inputs import InputDataError

    resolved, decisions, conflicts = resolve(tcs, composition)

    if conflicts:
        raise InputDataError(
            f'{len(conflicts)} unresolvable overlap(s) in TCs.csv:\n\n'
            + '\n'.join(str(conflict) for conflict in conflicts)
            + '\n\nNothing was computed.')

    report(decisions, conflicts, underspecified(resolved, composition))
    return resolved
