"""
tools/make_carcomposition_tcs.py
================================

Generate the ARTIFICIAL transfer-coefficient table for the 04_01 car-composition
case, from the composition that stage actually exported.

    ./.venv/bin/python tools/make_carcomposition_tcs.py data_folder/carcomposition_mockup

WHAT IS REAL AND WHAT IS NOT
----------------------------
REAL: every drivetrain, component and material name, and which (component,
material) pairs exist. Those come from 04_01's own export, so the table covers
exactly what the case contains -- no row that can never fire, and no resource
left without coefficients.

MADE UP: every number. They are marked `MADE UP (Claude)` in the `source`
column and are an illustration of the table's SHAPE. Replace them with measured
values before any result is reported.

WHY GENERATED RATHER THAN WRITTEN
---------------------------------
A hand-written table goes stale the moment the export gains a material, and the
failure is silent -- the resource simply has no coefficients and its mass stops.
Generating it from the composition means the two cannot drift apart, and it is
the only way a table covering five drivetrains and ~480 resources stays correct.

IT REFUSES TO OVERWRITE YOUR WORK
---------------------------------
This regenerates the WHOLE table; it does not merge. That is right while every
number is invented and wrong the moment one is not, and from inside the script
the two look identical. So the `source` column decides: every row written here
says `MADE UP (Claude) ...` or `derived: ...`, and a table holding a row that
says anything else is left alone. `--overwrite` forces it. To add rows for
resources the export has gained without losing what is filled in, use
tools/make_skeleton.py, which merges.

CLOSURE HOLDS BY CONSTRUCTION
-----------------------------
Each resource gets one residual row carrying whatever the named rows do not, so
its coefficients sum to 1 exactly. The sampled maxima are then capped so they
cannot sum past 1 either -- without that, an extreme draw drives the residual
negative and the model produces negative mass (see the ELV_loss_ASR case in
documentation/DESIGN_04_01_carcomposition.md).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bootstrap import ensure_venv
ensure_venv()

import pandas as pd

from src.params_schema import current
from src.upstream import load as refresh

MADE_UP = 'MADE UP (Claude) -- not data, illustration of shape only'

COLUMNS = ['Input_FlowID', 'Input_layer', 'Input_layer_key', 'Output_FlowID',
           'TC_target_layer', 'TC_target_key', 'value', 'value_min', 'value_max',
           'is_residual', 'process', 'technology', 'source']

# How readily a component comes off the car before shredding. Accessibility and
# value, not measurement: a battery is worth pulling, a trim panel is not.
DISMANTLING = {
    'elvBattery': 0.95, 'elvCatalyticConverters': 0.95,
    'elvPowertrain': 0.80, 'elvTransmission': 0.70, 'elvWheels': 0.60,
    'elvDriveline': 0.45, 'elvPowerElectronics': 0.60,
}
DISMANTLING_DEFAULT = 0.15

# How well a material separates, once it is in that stream. Steels and aluminium
# separate well; battery material does not survive shredding; cable-like
# material is in between.
def yields(material: str) -> tuple[float, float]:
    """(dismantled reuse yield, shredded separation yield) for one material."""
    if material.startswith('cal'):
        return 0.85, 0.90
    if material == 'battery':
        return 0.90, 0.10
    if 'able' in material or 'Cable' in material:      # cableLike, generatorCable
        return 0.80, 0.55
    return 0.60, 0.35


def component_rows(product: str, component: str) -> list[dict]:
    """Dismantling: what is pulled, what is lost doing it, what stays in the hulk."""
    pulled = DISMANTLING.get(component, DISMANTLING_DEFAULT)
    lost = 0.03
    base = dict(Input_FlowID='ELV_collected', Input_layer='product',
                Input_layer_key=product, TC_target_layer='component',
                TC_target_key=component, process='dismantling', technology='manual')
    return [
        {**base, 'Output_FlowID': 'ELV_dismantled', 'value': pulled,
         'value_min': max(0.0, pulled - 0.15), 'value_max': min(1.0, pulled + 0.15),
         'is_residual': '', 'source': f'{MADE_UP}: {component} out of a {product}'},
        {**base, 'Output_FlowID': 'ELV_loss_dismantling', 'value': lost,
         'value_min': 0.0, 'value_max': 0.15, 'is_residual': '',
         'source': f'{MADE_UP}: {component} lost while dismantling a {product}'},
        {**base, 'Output_FlowID': 'ELV_shredded', 'value': round(1 - pulled - lost, 6),
         'value_min': '', 'value_max': '', 'is_residual': '1',
         'source': 'derived: what is neither pulled nor lost stays in the hulk'},
    ]


def material_rows(component: str, material: str) -> list[dict]:
    """Two separations, one per stream, each with its own loss."""
    reuse, ferrous = yields(material)
    rows = []
    for flow, recovered_flow, loss_flow, keep, process, technology in (
            ('ELV_dismantled', 'ELV_reused', 'ELV_loss_dismantled', reuse,
             'reuse_sorting', 'manual'),
            ('ELV_shredded', 'ELV_ferrous', 'ELV_loss_ASR', ferrous,
             'separation', 'magnetic')):
        base = dict(Input_FlowID=flow, Input_layer='component',
                    Input_layer_key=component, TC_target_layer='material',
                    TC_target_key=material, process=process, technology=technology)
        rows += [
            {**base, 'Output_FlowID': recovered_flow, 'value': keep,
             'value_min': max(0.0, keep - 0.20), 'value_max': min(1.0, keep + 0.10),
             'is_residual': '', 'source': f'{MADE_UP}: {material} in {process}'},
            {**base, 'Output_FlowID': loss_flow, 'value': round(1 - keep, 6),
             'value_min': '', 'value_max': '', 'is_residual': '1',
             'source': 'derived: what is not recovered is lost'},
        ]
    return rows


from src.mass_balance import RESOURCE


def cap_maxima(tcs: pd.DataFrame) -> int:
    """
    Stop a resource's sampled maxima summing past 1.

    Every non-residual coefficient of one resource can be drawn high at once, and
    then the residual is 1 minus something greater than 1 -- negative mass, which
    balances perfectly and is nonsense. Modes and relative widths are preserved;
    only the headroom above the modes is shared out.
    """
    residual = tcs['is_residual'].astype(str).str.strip() == '1'
    changed = 0
    for _, index in tcs.groupby(RESOURCE).groups.items():
        free = index[~residual.loc[index] & (tcs.loc[index, 'value_max'] != '')]
        if not len(free):
            continue
        v = pd.to_numeric(tcs.loc[free, 'value'])
        m = pd.to_numeric(tcs.loc[free, 'value_max'])
        if m.sum() <= 1.0 + 1e-12:
            continue
        headroom, spread = 1.0 - v.sum(), m.sum() - v.sum()
        factor = 0.0 if spread <= 0 else max(0.0, min(1.0, headroom / spread))
        tcs.loc[free, 'value_max'] = (v + (m - v) * factor).round(6)
        changed += len(free)
    return changed


def build(composition: pd.DataFrame) -> pd.DataFrame:
    """One table covering every resource in the composition, and nothing else."""
    products = sorted(set(composition['Layer 1']))
    pairs = composition[composition['Layer 3'] != ''][['Layer 2', 'Layer 3']]

    rows = []
    for product in products:
        own = composition[composition['Layer 1'] == product]
        for component in sorted(set(own['Layer 2'])):
            rows += component_rows(product, component)

    # A material coefficient is keyed on (component, material), NOT on the
    # drivetrain: the same steel in the same body shell meets the same shredder
    # whatever drove the car. Only dismantling is per drivetrain, which is right
    # -- a battery is pulled from a BEV, a catalytic converter from a Petrol.
    for component, material in sorted(set(map(tuple, pairs.to_numpy()))):
        rows += material_rows(component, material)

    tcs = pd.DataFrame(rows, columns=COLUMNS)
    capped = cap_maxima(tcs)
    print(f'  capped value_max on {capped} row(s) so no resource can sum past 1')
    return tcs


def hand_written(existing) -> "pd.DataFrame":
    """
    The rows somebody has edited: any whose `source` this tool did not write.

    Every row it generates is marked either `MADE UP (Claude) ...` or
    `derived: ...`. A row saying anything else came from a person, and is the
    thing that must not be destroyed.
    """
    source = existing['source'].astype(str).str.strip() \
        if 'source' in existing.columns else None
    if source is None:
        # No source column at all means the table was not written by this tool.
        return existing
    generated = source.str.startswith(MADE_UP) | source.str.startswith('derived:')
    return existing[~generated]


def refuse_if_edited(folder: str, overwrite: bool) -> None:
    """
    Stop before overwriting a table somebody has put real numbers into.

    This tool OVERWRITES -- it does not merge, unlike make_skeleton -- because
    it generates the whole table from the composition. That is right while every
    number is a placeholder and wrong the moment one is not, and the difference
    is invisible from inside the script: a real coefficient looks exactly like
    an invented one. So the `source` column decides, and a table holding any row
    this tool did not write is left alone.

    The alternative was a warning in the handover, which is a poor guard: it is
    read once, months before the run that would destroy the work.
    """
    from src import case_tables

    if overwrite or not case_tables.exists(folder, 'TCs'):
        return

    edited = hand_written(case_tables.read(folder, 'TCs'))
    if edited.empty:
        return

    lines = []
    for _, row in edited.head(5).iterrows():
        lines.append(f"    {row.get('Input_FlowID', '?')} -> "
                     f"{row.get('Output_FlowID', '?')}  "
                     f"{row.get('TC_target_key', '?')}  "
                     f"value={row.get('value', '?')}  "
                     f"source={str(row.get('source', ''))[:60]}")
    more = f'\n    ... and {len(edited) - 5} more' if len(edited) > 5 else ''

    raise SystemExit(
        f"\nRefusing to overwrite {case_tables.where(folder, 'TCs')[1]}.\n\n"
        f"{len(edited)} of its rows were not written by this tool -- somebody has\n"
        f"edited them. This script regenerates the WHOLE table and does not merge,\n"
        f"so running it would replace those numbers with invented ones.\n\n"
        + '\n'.join(lines) + more + "\n\n"
        f"If the table really should be thrown away and rebuilt, say so:\n"
        f"    ./.venv/bin/python tools/make_carcomposition_tcs.py {folder} --overwrite\n"
        f"To add rows for resources the export has gained WITHOUT losing what is\n"
        f"filled in, use tools/make_skeleton.py, which merges.")


def main() -> int:
    arguments = [a for a in sys.argv[1:] if not a.startswith('--')]
    overwrite = '--overwrite' in sys.argv[1:]
    folder = arguments[0] if arguments else current().run.data_folder

    # Before anything is generated: this tool replaces the table wholesale.
    refuse_if_edited(folder, overwrite)

    params = current()
    composition = refresh(params, folder, quiet=True)['composition']

    tcs = build(composition)
    # Written wherever this case keeps its coefficients -- the TCs sheet of
    # case.xlsx, or TCs.csv for a case still on files. Same writer as
    # make_skeleton, so both tools leave the workbook in the same shape.
    from src import case_tables
    from tools.make_skeleton import WIDTHS

    where = case_tables.where(folder, 'TCs')
    if where is not None and where[0] == 'xlsx':
        path = case_tables.write_sheet(folder, 'TCs', tcs, widths=WIDTHS)
    else:
        path = case_tables.csv_path(folder, 'TCs')
        tcs.to_csv(path, index=False)

    resources = len(tcs.groupby(RESOURCE))
    print(f'{path}: {len(tcs):,} rows covering {resources:,} resources')
    print(f'  {composition["Layer 1"].nunique()} products, '
          f'{composition["Layer 2"].nunique()} components, '
          f'{composition[composition["Layer 3"] != ""]["Layer 3"].nunique()} materials')
    print('  EVERY NUMBER IS INVENTED -- see the source column.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
