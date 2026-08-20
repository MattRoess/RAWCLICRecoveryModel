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
it means. That is now only DEFECTS.md 2.3, an unspecified semantic whose answer
belongs to whoever owns the method -- not a mistake, and the answer belongs to whoever owns the method -- so they are
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


# The unit table and the conversion itself live in src/units.py, so that the
# check here and the conversion done on load cannot disagree about what a
# unit means.
from src.units import AMBIGUOUS_UNITS, MASS_UNITS


def _check_units(inputs: pd.DataFrame) -> list[Problem]:
    """
    The unit of the inflow data.

    The model multiplies fractions and never reads the unit, which is precisely
    why an unreadable one is dangerous: every number downstream would be wrong
    by a clean factor of 1000 and nothing about the output would look unusual.

    The unit no longer has to *match* the project's -- the loader converts it.
    What this checks is that it can be converted at all: exactly one unit per
    file, recognised, and not one of the ambiguous names.
    """
    from src.params_schema import Params
    expected = Params().run.working_unit
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
    # A unit that differs from the working one is NOT a problem any more. The
    # loader converts it (src/units.py), so a file in kt and a project working
    # in kg are a normal combination rather than a mistake to report. What is
    # still refused is a unit that cannot be converted safely: unknown,
    # ambiguous, or more than one in the same file.

    return problems


def _check_coefficients_present(tcs: pd.DataFrame) -> list[Problem]:
    """
    Every transfer coefficient has to be a number.

    A skeleton written by 02_make_skeleton.py has the rows and no values, which
    is the point -- but it must be said plainly. Left to reach the arithmetic, a
    blank value is read as the empty string and surfaces as
    "unsupported operand type(s) for -: 'str' and 'int'" from somewhere deep in
    pandas, naming neither the file nor the row.
    """
    if 'value' not in tcs.columns:
        return [Problem('ERROR', '-', "TCs.csv has no 'value' column.")]

    blank = tcs['value'].astype(str).str.strip() == ''
    if not blank.any():
        return []

    total = int(blank.sum())
    first = tcs[blank].iloc[0]
    return [Problem(
        'ERROR', '-',
        f"TCs.csv: {total} of {len(tcs)} rows have no value. The first is row "
        f"{int(blank.idxmax()) + 2}: {first['Input_FlowID']} "
        f"{first['Input_layer_key']} -> {first['Output_FlowID']} "
        f"{first['TC_target_key']}.\n"
        f"    This is what a freshly generated skeleton looks like. Fill in "
        f"value, and value_min/value_max if the coefficient is uncertain.")]


def check(folder: str) -> list[Problem]:
    """Every problem with a case folder's three tables. Empty means clean."""
    inputs, composition, tcs = _load(folder)

    # The engine derives a `rest` child for every parent whose known children
    # fall short (src/rest.py), so `rest` is a legitimate key in TCs.csv -- and
    # it has to be, because unspecified material is most of the mass. Checking
    # against the raw composition refused it as an unknown element, which is
    # the loader disagreeing with itself about what exists.
    from src.rest import add_rest
    try:
        composition_with_rest, _ = add_rest(composition)
    except Exception:
        # A composition too broken to derive a rest from will be reported by the
        # checks below on its own terms; do not fail here with a worse message.
        composition_with_rest = composition
    known = _known_keys(composition_with_rest)
    problems: list[Problem] = []

    # Before anything else: a table with no numbers in it cannot be checked for
    # anything else, and every later check would fail confusingly.
    blank = _check_coefficients_present(tcs)
    if blank:
        return blank

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

    # ---- 2.5  a same-layer TC carries a resource, it does not transform it --
    # Decided 2026-08-17: a transfer within one layer moves a resource to
    # another flow unchanged. A component does not become a different
    # component, so the two keys have to name the same resource.
    #
    # This is enforced here rather than handled in the engines because neither
    # engine can express a transformation: RecoveryModelLA reads only
    # Input_layer_key and ignores the target, the optimized engine used to read
    # only TC_target_key and ignored the input. They agreed solely because every
    # same-layer TC written so far is an identity. DEFECTS.md §2.5 records what
    # implementing the transformation reading would take, if it is ever wanted.
    same_layer = tcs[tcs['Input_layer'] == tcs['TC_target_layer']]
    for index, row in same_layer.iterrows():
        source_key, target_key = row['Input_layer_key'], row['TC_target_key']
        if source_key and target_key and source_key == target_key:
            continue
        problems.append(Problem(
            'ERROR', '2.5',
            f"TCs.csv row {index + 2}: {row['Input_FlowID']} -> {row['Output_FlowID']} "
            f"stays within the {row['Input_layer']} layer but reads "
            f"{source_key or '(blank)'!r} -> {target_key or '(blank)'!r}. A transfer "
            f"within one layer moves a resource unchanged, so both keys must name "
            f"the same resource. Write {target_key or source_key!r} on both sides, "
            f"or target a deeper layer if the resource really does become "
            f"something else."))

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
