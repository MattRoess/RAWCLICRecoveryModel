"""
src/validate_inputs.py
======================

Check the three input tables before the model uses them.

WHY THIS EXISTS
---------------
Four of the seven engine divergences in documentation/DEFECTS.md are the same
absence: nothing looked at the input tables before they were used. What each
engine did instead:

  - An inflow naming a flow that appears in no TC added 4000 Mg of phantom mass
    to basic_test under the optimized engine, silently, and killed the LA
    engine with `TypeError: can only concatenate str (not "int") to str`
    (DEFECTS.md 2.7).
  - A composition row filling only Layer 1 invented exactly the mass of its own
    product, again silently (2.6).
  - A composition defined for one flow was applied to every flow sharing its
    parent (2.1) -- since fixed in the engine itself, so what remains here is
    the check that every inflow's (flow, product) pair actually has a
    composition to expand into.

Every one of those is visible in the CSVs before a single row is joined, and at
that point the message can still name the file, the column and the value. That
is what this module does.

ERRORS AND WARNINGS
-------------------
An ERROR means the input cannot be read as meaning anything: a key that names
nothing, a row with a hole in it. The run stops.

A WARNING means the input is readable but the two engines disagree about what
it means. Those are open method questions (DEFECTS.md 2.3 and 2.5), not
mistakes, and the answer belongs to whoever owns the method -- so they are
reported and the run continues. The defect-case folders are built from exactly
these patterns and must stay runnable, which is the other reason they do not
stop anything.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

LAYERS = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']

# The user guide's layer names, in depth order, as they appear in TCs.csv.
LAYER_NAMES = ['product', 'component', 'material', 'element']

READ = dict(keep_default_na=False, na_values=[])


class InputDataError(ValueError):
    """Raised when an input table cannot be read as meaning anything."""


@dataclass
class Problem:
    severity: str        # 'ERROR' or 'WARNING'
    defect: str          # the DEFECTS.md section this prevents
    message: str

    def __str__(self) -> str:
        return f'  {self.severity:<7} [{self.defect}] {self.message}'


def _load(folder: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = os.path.join(folder, 'input_data')
    missing = [name for name in ('inputs.csv', 'composition.csv', 'TCs.csv')
               if not os.path.exists(os.path.join(path, name))]
    if missing:
        raise InputDataError(
            f"{path} is missing {', '.join(missing)}.\n"
            f"A case folder needs all three: inputs.csv, composition.csv, TCs.csv.")
    return (pd.read_csv(os.path.join(path, 'inputs.csv'), **READ),
            pd.read_csv(os.path.join(path, 'composition.csv'), **READ),
            pd.read_csv(os.path.join(path, 'TCs.csv'), **READ))


def _known_keys(composition: pd.DataFrame) -> dict[str, set[str]]:
    """Every resource name that exists at each layer, from the composition."""
    return {name: {value for value in composition[column].unique() if value}
            for name, column in zip(LAYER_NAMES, LAYERS)}


# Mass units the inflow file may declare, with what each one is in kilograms.
# The model never converts -- it multiplies fractions and is unit-agnostic --
# so this table exists to name the unit and to state the size of the mistake
# when the wrong one turns up.
MASS_UNITS = {
    'mg': 1e-6, 'g': 1e-3, 'kg': 1.0,
    't': 1e3, 'tonne': 1e3, 'tonnes': 1e3, 'Mg': 1e3,     # 1 Mg = 1 tonne
    'kt': 1e6, 'Gg': 1e6,                                  # 1 kt = 1 Gg
    'Mt': 1e9, 'Tg': 1e9,
    'Gt': 1e12,
}

# Units that name more than one quantity. 'ton' is 1000 kg in one country and
# 907 or 1016 in others, which is a 10% error that looks like a rounding
# difference rather than a unit mistake.
AMBIGUOUS_UNITS = {'ton', 'tons', 'T', 'MT', 'KT'}


def _check_units(inputs: pd.DataFrame) -> list[Problem]:
    """
    The unit of the inflow data.

    The model multiplies fractions and never reads the unit, which is precisely
    why a wrong one is dangerous: every number downstream is wrong by a clean
    factor of 1000 and nothing about the output looks unusual.
    """
    from src.params_schema import Params
    expected = Params().run.expected_unit
    problems: list[Problem] = []

    if 'Unit' not in inputs.columns:
        return [Problem('ERROR', '3.3',
                        f"inputs.csv has no 'Unit' column, so there is nothing saying "
                        f"what its numbers are. Add one, reading {expected!r} "
                        f"on every row.")]

    declared = sorted({str(unit).strip() for unit in inputs['Unit'] if str(unit).strip()})

    if not declared:
        return [Problem('ERROR', '3.3',
                        f"inputs.csv, column 'Unit': every row is blank. Fill it in "
                        f"with {expected!r}.")]

    if len(declared) > 1:
        sizes = []
        for unit in declared:
            factor = MASS_UNITS.get(unit)
            sizes.append(f'{unit} ({factor:g} kg)' if factor else f'{unit} (unknown)')
        problems.append(Problem(
            'ERROR', '3.3',
            f"inputs.csv, column 'Unit': the file mixes {', '.join(sizes)}. The model "
            f"adds these numbers together without converting them, so one unit per "
            f"file is the only safe arrangement."))
        return problems

    unit = declared[0]

    if unit in AMBIGUOUS_UNITS:
        problems.append(Problem(
            'ERROR', '3.3',
            f"inputs.csv, column 'Unit': {unit!r} names more than one quantity "
            f"depending on where it is written. Use an unambiguous one -- "
            f"{expected!r} for this project, or kg, kt, Mt."))
    elif unit not in MASS_UNITS:
        problems.append(Problem(
            'ERROR', '3.3',
            f"inputs.csv, column 'Unit': {unit!r} is not a mass unit this project "
            f"recognises. Known: {', '.join(sorted(MASS_UNITS))}."))
    elif unit != expected:
        factor = MASS_UNITS[unit] / MASS_UNITS[expected]
        problems.append(Problem(
            'WARNING', '3.3',
            f"inputs.csv is in {unit!r} but this project expects {expected!r} "
            f"(expected_unit in src/params_schema.py). That is a factor of {factor:g}. "
            f"Nothing here converts it -- either convert the data, or change the "
            f"setting if {unit!r} is genuinely what the project now works in."))

    return problems


def check(folder: str) -> list[Problem]:
    """Every problem with a case folder's three tables. Empty means clean."""
    inputs, composition, tcs = _load(folder)
    known = _known_keys(composition)
    problems: list[Problem] = []

    # ---- 2.7  every key in inputs.csv has to name something -----------------
    # Checked as a (flow, product) PAIR, because composition is defined per flow
    # via 'Stock/ID'. A product that exists in the file but not for this flow no
    # longer expands into components at all -- the mass stops at product depth
    # and quietly never reaches the layers the whole model is about.
    products = known['product']
    if 'Stock/ID' in composition.columns:
        defined = set(zip(composition['Stock/ID'], composition['Layer 1']))
        for flow, product in sorted(set(zip(inputs['Stock/Flow ID'],
                                            inputs['Substance_main_parent']))):
            if (flow, product) in defined:
                continue
            if product not in products:
                problems.append(Problem(
                    'ERROR', '2.7',
                    f"inputs.csv: {product!r} appears in no composition.csv row. "
                    f"Known products: {', '.join(sorted(products)) or 'none'}."))
            else:
                elsewhere = sorted({s for s, p in defined if p == product})
                problems.append(Problem(
                    'ERROR', '2.7',
                    f"inputs.csv: flow {flow!r} carries {product!r}, but composition.csv "
                    f"defines that product only for {', '.join(map(repr, elsewhere))}. "
                    f"Composition is per flow ('Stock/ID'), so this inflow would never "
                    f"be split into components."))
    else:
        for value in sorted(set(inputs['Substance_main_parent']) - products):
            problems.append(Problem(
                'ERROR', '2.7',
                f"inputs.csv, column 'Substance_main_parent': {value!r} appears in no "
                f"composition.csv row. Known products: {', '.join(sorted(products)) or 'none'}."))

    tc_flows = set(tcs['Input_FlowID'])
    for value in sorted(set(inputs['Stock/Flow ID']) - tc_flows):
        problems.append(Problem(
            'ERROR', '2.7',
            f"inputs.csv, column 'Stock/Flow ID': {value!r} appears in no TCs.csv "
            f"'Input_FlowID', so its mass would enter the system and go nowhere."))

    # ---- 2.6  a composition row must not have a hole in it -----------------
    depth = (composition[LAYERS] != '').sum(axis=1)
    filled_to = composition[LAYERS].apply(
        lambda row: max((i + 1 for i, value in enumerate(row) if value), default=0), axis=1)
    for index, row in composition[(depth != filled_to) | (depth < 2)].iterrows():
        written = ' / '.join(value or '-' for value in row[LAYERS])
        problems.append(Problem(
            'ERROR', '2.6',
            f'composition.csv row {index + 2}: {written}. A composition row has to '
            f'describe a resource inside its parent, so it needs at least Layer 1 and '
            f'Layer 2 filled and no gaps between them.'))

    # ---- TC keys and layer names have to name something --------------------
    for column, layer_column in (('Input_layer_key', 'Input_layer'),
                                 ('TC_target_key', 'TC_target_layer')):
        for index, row in tcs.iterrows():
            key, layer = row[column], row[layer_column]
            if not key or '*' in str(key):        # blank means 'all', * is the wildcard
                continue
            if layer not in known:
                problems.append(Problem(
                    'ERROR', '-',
                    f"TCs.csv row {index + 2}, column '{layer_column}': {layer!r} is not "
                    f"a layer name. Expected one of {', '.join(LAYER_NAMES)}."))
                continue
            if key not in known[layer]:
                problems.append(Problem(
                    'ERROR', '-',
                    f"TCs.csv row {index + 2}, column '{column}': {key!r} is not a "
                    f"{layer} in composition.csv. Known: "
                    f"{', '.join(sorted(known[layer])) or 'none'}."))

    # ---- 3.3  units ---------------------------------------------------------
    problems += _check_units(inputs)

    # ---- 3.3  shares and transfer coefficients are fractions, not percents --
    # The classic unit mistake in a table like this is writing 50 where 0.5 was
    # meant. Nothing downstream can tell the difference: the model just
    # multiplies, so a percentage inflates the answer a hundredfold in silence.
    columns = [('composition.csv', composition, 'Value'), ('TCs.csv', tcs, 'value')]
    # The optional triangular columns are fractions too, and are the ones the
    # Monte Carlo will sample from, so a range reaching outside [0, 1] would
    # draw impossible transfer coefficients on some fraction of the draws.
    columns += [('TCs.csv', tcs, name) for name in ('value_min', 'value_max')
                if name in tcs.columns]

    for name, frame, column in columns:
        numeric = pd.to_numeric(frame[column], errors='coerce')
        for index, value in numeric[(numeric > 1) | (numeric < 0)].items():
            hint = ' -- looks like a percentage where a fraction was meant' \
                if 1 < value <= 100 else ''
            problems.append(Problem(
                'ERROR', '3.3',
                f"{name} row {index + 2}, column '{column}': {value:g}. A share has to "
                f"be a fraction between 0 and 1{hint}."))

    # A triangular needs min <= mode <= max, or the inverse-CDF sampling in
    # DESIGN_monte_carlo.md §4 has no distribution to invert.
    if {'value_min', 'value_max'}.issubset(tcs.columns):
        low = pd.to_numeric(tcs['value_min'], errors='coerce')
        mode = pd.to_numeric(tcs['value'], errors='coerce')
        high = pd.to_numeric(tcs['value_max'], errors='coerce')
        for index in tcs.index[(low > mode) | (mode > high)]:
            problems.append(Problem(
                'ERROR', '3.3',
                f"TCs.csv row {index + 2}: value_min {low[index]:g}, value "
                f"{mode[index]:g}, value_max {high[index]:g}. A triangular range needs "
                f"value_min <= value <= value_max."))

    # ---- 2.3 / 2.5  two TCs competing for one destination ------------------
    # A TC identifies its resource by BOTH keys -- "component C1 within product
    # P1" -- so two TCs reaching the same target key from different input keys
    # are different resources and perfectly normal. What is not normal is two
    # TCs that describe the *same* resource reaching the same destination.
    for (source, target, layer, key), group in tcs.groupby(
            ['Input_FlowID', 'Output_FlowID', 'TC_target_layer', 'TC_target_key']):
        input_layers = set(group['Input_layer'])
        pairs = list(zip(group['Input_layer'], group['Input_layer_key']))

        if len(input_layers) > 1:
            problems.append(Problem(
                'WARNING', '2.3',
                f"TCs.csv: {source} -> {target} sets {layer} {key!r} from more than one "
                f"layer ({', '.join(sorted(input_layers))}). The optimized engine adds "
                f"the two together, the LA engine keeps only the more specific one -- "
                f"a factor of two between them, on an input the user guide does not "
                f"call illegal."))
        elif len(pairs) > len(set(pairs)):
            problems.append(Problem(
                'WARNING', '2.5',
                f"TCs.csv: {source} -> {target} has the same transfer coefficient "
                f"written more than once for {layer} {key!r}. The optimized engine adds "
                f"the duplicates together."))
        elif layer in input_layers and len(set(group['Input_layer_key'])) > 1:
            others = ', '.join(sorted(set(group['Input_layer_key'])))
            problems.append(Problem(
                'WARNING', '2.5',
                f"TCs.csv: {source} -> {target} reaches {layer} {key!r} from several "
                f"keys within that same layer ({others}). The optimized engine discards "
                f"'Input_layer_key' on a same-layer transfer, so it cannot tell them "
                f"apart and multiplies the rows instead."))

    return problems


def report(folder: str, problems: list[Problem]) -> None:
    """Print the warnings, and raise on the errors."""
    warnings = [p for p in problems if p.severity == 'WARNING']
    errors = [p for p in problems if p.severity == 'ERROR']

    if warnings:
        print(f'\n{len(warnings)} warning(s) about {folder}:')
        for problem in warnings:
            print(problem)
        print('  These are open method questions, not mistakes -- see '
              'documentation/DEFECTS.md. The run continues.')

    if errors:
        raise InputDataError(
            f'{len(errors)} problem(s) with the input tables in {folder}:\n\n'
            + '\n'.join(str(problem) for problem in errors)
            + '\n\nNothing was computed. Correct the input files and run again.')


def validate(folder: str) -> None:
    """Check a case folder, printing warnings and raising on errors."""
    report(folder, check(folder))
