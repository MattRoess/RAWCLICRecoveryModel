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


def _load(folder: str, tables: dict | None = None
          ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the three tables, or take the ones already in memory."""
    if tables is not None:
        # The inflow and composition come straight from the upstream draws and
        # are never written to disk; only TCs.csv is a file anyone keeps.
        from src import case_tables
        tcs = tables.get('tcs')
        if tcs is None:
            if not case_tables.exists(folder, 'TCs'):
                raise InputDataError(
                    f"{folder} has no transfer coefficients.\nThey are the one "
                    f"table you write; run tools/make_skeleton.py to generate it.")
            tcs = case_tables.read(folder, 'TCs')
        return tables['inputs'], tables['composition'], tcs

    return _load_from_disk(folder)


def _load_from_disk(folder: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from src import case_tables

    path = os.path.join(folder, 'input_data')
    # inputs and composition are only ever files for a hand-built case with no
    # upstream -- the fixtures, and test_generality's panel. TCs may be a sheet.
    missing = [name for name in ('inputs.csv', 'composition.csv')
               if not os.path.exists(os.path.join(path, name))]
    if not case_tables.exists(folder, 'TCs'):
        missing.append('TCs')
    if missing:
        raise InputDataError(
            f"{path} is missing {', '.join(missing)}.\n"
            f"A case folder needs inputs.csv, composition.csv, and transfer "
            f"coefficients as either TCs.csv or a TCs sheet in case.xlsx.")
    return (pd.read_csv(os.path.join(path, 'inputs.csv'), **READ),
            pd.read_csv(os.path.join(path, 'composition.csv'), **READ),
            case_tables.read(folder, 'TCs'))


def _known_keys(composition: pd.DataFrame) -> dict[str, set[str]]:
    """Every resource name that exists at each layer, from the composition."""
    return {name: {value for value in composition[column].unique() if value}
            for name, column in zip(LAYER_NAMES, LAYERS)}


def _check_nothing_strands(processes: pd.DataFrame | None,
                           composition: pd.DataFrame,
                           tcs: pd.DataFrame) -> list[Problem]:
    """
    Every resource entering a flow that something leaves must have a
    coefficient to leave it by. Otherwise its mass stops there and vanishes.

    A flow nothing leaves is terminal and exempt -- recovered, lost, handed
    off. Which flows those are is read from the `processes` table, never
    listed here: a flow is terminal exactly when it is no process's input.

    WHY THIS IS AN ERROR AND NOT A WARNING
    --------------------------------------
    The mass does not go somewhere questionable. It is gone, the totals no
    longer add up, and nothing else notices -- the run writes a solution, draws
    its figures and reports a recovery rate computed from less mass than
    entered. On 2026-09-01 that was 5.9% of the electronics case, found by
    totalling the terminal flows by hand.

    The opposite direction has been checked since 2026-08-17: a TC row naming a
    resource that does not exist. That one is a warning, correctly -- an inert
    row costs nothing. This one is the same join read the other way round, and
    it costs the answer.

    THE MATCHING RULE IS THE ENGINE'S
    ---------------------------------
    A row covers a resource when its target key names the resource and its
    input key names the resource's parent -- or is blank or a wildcard, which
    both mean "whatever the parent is". That is the same precedence the engine
    applies (DEFECTS.md 2.3), stated once here for coverage rather than for
    which row wins.
    """
    if processes is None or 'Input_FlowID' not in tcs.columns:
        return []

    flows_with_an_exit = {str(flow).strip() for flow in processes['Input_FlowID']}
    depth_of = {name: depth for depth, name in enumerate(LAYER_NAMES)}

    problems = []
    for flow in sorted(flows_with_an_exit):
        leaving = tcs[tcs['Input_FlowID'].astype(str).str.strip() == flow]
        if not len(leaving):
            continue                       # named as an input by no coefficient

        for layer in sorted({str(value).strip()
                             for value in leaving['TC_target_layer']}):
            if layer not in depth_of:
                continue                   # already reported as an unknown layer
            depth = depth_of[layer]
            covered, anywhere = set(), set()
            for _, row in leaving[leaving['TC_target_layer'].astype(str)
                                  .str.strip() == layer].iterrows():
                target, parent = str(row['TC_target_key']), str(row['Input_layer_key'])
                if not parent or '*' in parent:
                    anywhere.add(target)
                else:
                    covered.add((parent, target))

            # The resources this layer defines: rows whose deepest filled layer
            # is this one. A deeper row is a sub-quantity of one of them and is
            # carried along by whatever moves its parent.
            at_depth = composition[LAYERS[depth]] != ''
            for deeper in LAYERS[depth + 1:]:
                at_depth &= composition[deeper] == ''

            here = {(str(row[LAYERS[depth - 1]]) if depth else '',
                     str(row[LAYERS[depth]]))
                    for _, row in composition[at_depth].iterrows()}
            stranded = sorted((parent, child) for parent, child in here
                              if child not in anywhere
                              and (parent, child) not in covered)

            if not stranded:
                continue
            named = ', '.join(f'{parent}/{child}' if parent else child
                              for parent, child in stranded[:8])
            more = f' ... and {len(stranded) - 8} more' if len(stranded) > 8 else ''
            problems.append(Problem(
                'ERROR', '-',
                f'{len(stranded)} resource(s) reach {flow} and no coefficient '
                f'moves them on:\n'
                f'          {named}{more}\n'
                f'          Their mass stops there and disappears from every '
                f'total. {flow} is not\n'
                f'          terminal -- the processes table gives it an exit -- '
                f'so each of these\n'
                f'          needs a row in TCs, even if the value is 0. '
                f'tools/make_skeleton.py writes them.'))
    return problems


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

    A skeleton written by tools/make_skeleton.py has the rows and no values, which
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



from src.mass_balance import RESOURCE


def _numeric(tcs: pd.DataFrame):
    """value, value_min, value_max as floats, bounds falling back to the mode."""
    mode = pd.to_numeric(tcs['value'], errors='coerce')
    low = pd.to_numeric(tcs.get('value_min'), errors='coerce') if 'value_min' in tcs else mode
    high = pd.to_numeric(tcs.get('value_max'), errors='coerce') if 'value_max' in tcs else mode
    return low.fillna(mode), mode, high.fillna(mode)


def _is_residual(tcs: pd.DataFrame):
    from src.sampling import RESIDUAL_COLUMN
    if RESIDUAL_COLUMN not in tcs.columns:
        return pd.Series(False, index=tcs.index)
    return tcs[RESIDUAL_COLUMN].astype(str).str.strip().isin(('1', '1.0', 'True', 'true'))


def _check_keyed_layers(processes: pd.DataFrame,
                        composition: pd.DataFrame) -> list[Problem]:
    """
    Every layer a process is keyed at must actually hold resources.

    THIS IS THE `child_layer` GUARD. Declaring the wrong one does not fail
    anywhere else: the reader files 04_01's materials at Layer 4 under an
    invented placeholder, every element-keyed coefficient then matches nothing,
    and the run still balances and still plots. The mass is right and the
    answer is wrong.

    It cannot be checked from `source.csv` alone -- nothing there knows what the
    upstream files contain. It CAN be checked here: a process keyed at a layer
    the composition never fills can never fire, so either the process names the
    wrong layer or the case declares the wrong `child_layer`.
    """
    if processes is None or 'keyed_at' not in processes.columns:
        return []

    problems = []
    for layer in sorted({str(value).strip() for value in processes['keyed_at']
                         if str(value).strip()}):
        if layer not in LAYER_NAMES:
            continue                      # named elsewhere as an unknown layer
        column = LAYERS[LAYER_NAMES.index(layer)]
        if (composition[column] != '').any():
            continue
        filled = [name for name, col in zip(LAYER_NAMES, LAYERS)
                  if (composition[col] != '').any()]
        rows = int((processes['keyed_at'].astype(str).str.strip() == layer).sum())
        problems.append(Problem(
            'ERROR', '-',
            f"processes: {rows} process(es) are keyed at the {layer} layer, but "
            f"nothing in this case's composition sits there, so not one of their "
            f"coefficients can ever fire.\n"
            f"          The composition fills: {', '.join(filled) or 'nothing'}.\n"
            f"          Either those processes name the wrong layer, or the case "
            f"declares the wrong `child_layer` in its source table -- which does "
            f"not fail on its own, and leaves a run that balances while being wrong."))
    return problems


def _check_residual_headroom(tcs: pd.DataFrame) -> list[Problem]:
    """
    A residual row must not be able to go negative.

    A residual is `1 - the others`, so if the others can all be drawn high at
    once and sum past 1, the residual goes NEGATIVE -- negative mass, which
    balances perfectly and is nonsense. It happened: 17 of 278 resources in the
    first 04_01 table, surfacing only afterwards as a negative 2.5th percentile.

    ONLY FOR GROUPS THAT HAVE A RESIDUAL ROW. Where every row is measured the
    constraint is enforced by conditioning, which handles maxima summing past 1
    by weighting -- so the same arithmetic is perfectly fine there, and
    refusing it would wrongly reject a conditioned case.
    """
    if not {'value_min', 'value_max'}.issubset(tcs.columns):
        return []

    low, mode, high = _numeric(tcs)
    residual = _is_residual(tcs)
    problems = []
    for name, rows in tcs.groupby(RESOURCE, dropna=False).groups.items():
        rows = pd.Index(rows)
        if not residual[rows].any():
            continue
        others = rows[~residual[rows]]
        total = float(high[others].sum())
        if total <= 1.0 + 1e-9:
            continue
        worst = 1.0 - total
        problems.append(Problem(
            'ERROR', '-',
            f"TCs: the coefficients of {name[4]!r} out of {name[0]} can sum to "
            f"{total:.4g} at their maxima, but one of them is derived as the "
            f"residual.\n"
            f"          On a draw near those maxima the residual becomes "
            f"{worst:+.4g} -- negative mass, which still balances.\n"
            f"          Lower the maxima so they sum to at most 1, or measure "
            f"the residual row too so the group is conditioned instead."))
    return problems


def _check_reflected(tcs: pd.DataFrame) -> list[Problem]:
    """
    A range that merely restates what the rest of its group already implies.

    Writing `1 - the rest of the group` into a row looks like a second
    measurement and is not: it counts the first one twice, so the target
    becomes f(x)*f(x) rather than f(x) and the answer narrows by about a fifth
    for no reason. Arithmetic cannot tell it from a genuine second opinion --
    only the `source` column can -- so this is a warning, not a refusal.
    """
    if not {'value_min', 'value_max'}.issubset(tcs.columns):
        return []
    import numpy as np
    from src.sampling import SAME_AS_IMPLIED, implied

    low, mode, high = _numeric(tcs)
    residual = _is_residual(tcs)
    problems = []
    for name, rows in tcs.groupby(RESOURCE, dropna=False).groups.items():
        rows = pd.Index(rows)
        if residual[rows].any() or abs(float(mode[rows].sum()) - 1.0) > 1e-9:
            continue                       # derived on purpose, or unconstrained
        l, m, h = low[rows].to_numpy(), mode[rows].to_numpy(), high[rows].to_numpy()
        free = np.flatnonzero(h - l > 0)
        if len(free) < 2:
            continue                       # handled by src/sampling.py itself
        for position in free:
            others = np.setdiff1d(np.arange(len(rows)), position)
            want = implied(l, m, h, others)
            got = (l[position], m[position], h[position])
            if all(abs(a - b) <= SAME_AS_IMPLIED for a, b in zip(want, got)):
                flow = tcs.loc[rows[position], 'Output_FlowID']
                problems.append(Problem(
                    'WARNING', '-',
                    f"TCs: {name[4]!r} -> {flow} states the range its own group "
                    f"already implies ({want[0]:.3g}, {want[1]:.3g}, {want[2]:.3g}).\n"
                    f"          That is one measurement counted twice, not a second "
                    f"opinion: the target becomes f(x)*f(x) and the answer narrows "
                    f"by roughly a fifth.\n"
                    f"          If it was not measured independently, mark it "
                    f"`is_residual` instead -- which says plainly that it is derived."))
                break
    return problems


def check(folder: str, tables: dict | None = None) -> list[Problem]:
    """Every problem with a case's three tables. Empty means clean."""
    inputs, composition, tcs = _load(folder, tables)

    # The engine derives a `rest` child for every parent whose known children
    # fall short (src/rest.py), so `rest` is a legitimate key in TCs.csv -- and
    # it has to be, because unspecified material is most of the mass. Checking
    # against the raw composition refused it as an unknown element, which is
    # the loader disagreeing with itself about what exists.
    # A share written as 25 rather than 0.25 is the classic mistake here, and it
    # has to be diagnosed BEFORE the rest is derived: 25 exceeds the whole, so
    # add_rest refuses first and reports "the parts sum to more than the whole",
    # which is true but says nothing about the actual error.
    out_of_range = pd.to_numeric(composition['Value'], errors='coerce')
    if ((out_of_range > 1) | (out_of_range < 0)).any():
        composition_with_rest = composition
    else:
        from src.rest import RestError, add_rest
        try:
            composition_with_rest, _ = add_rest(composition)
        except RestError as error:
            # Swallowing this hid a real bug once: a composition given per year
            # was grouped without the year, its shares summed to the number of
            # years, add_rest refused, and the only symptom was `rest` being
            # reported as an unknown element. Say what actually happened.
            raise InputDataError(f'The composition cannot be completed:\n\n  {error}')

    known = _known_keys(composition_with_rest)
    problems: list[Problem] = []

    # Before anything else: a table with no numbers in it cannot be checked for
    # anything else, and every later check would fail confusingly.
    blank = _check_coefficients_present(tcs)
    if blank:
        return blank

    # The three traps that used to be documented and unguarded: a `child_layer`
    # that balances while being wrong, a residual that can go negative, and a
    # range that restates its own group. HANDOVER.md section 5.
    from src import case_tables
    processes = (case_tables.read(folder, 'processes')
                 if case_tables.exists(folder, 'processes') else None)
    problems += _check_keyed_layers(processes, composition_with_rest)
    problems += _check_nothing_strands(processes, composition_with_rest, tcs)
    problems += _check_residual_headroom(tcs)
    problems += _check_reflected(tcs)

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
    #
    # An unmatched key is NOT automatically an error. One coefficient table is
    # meant to serve several runs of the same study -- 04_01's table carries all
    # five drivetrains, and a run covering BEV leaves four fifths of its
    # product-keyed rows matching nothing. Those rows are inert: they are never
    # looked up, and nothing they could affect exists.
    #
    # What IS an error is a table where NOTHING at a layer matches, because then
    # it is not this case's table at all -- a typo, or the wrong folder. So the
    # keys are collected first and judged together, which also turns 342 lines
    # of the same complaint into one line naming the four drivetrains.
    unmatched: dict[tuple[str, str], dict[str, list[int]]] = {}
    matched: dict[tuple[str, str], set[str]] = {}
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
                unmatched.setdefault((column, layer), {}).setdefault(key, []).append(index + 2)
            else:
                matched.setdefault((column, layer), set()).add(key)

    for (column, layer), keys in sorted(unmatched.items()):
        rows = sum(len(where) for where in keys.values())
        named = ', '.join(sorted(keys))
        if matched.get((column, layer)):
            problems.append(Problem(
                'WARNING', '-',
                f"TCs.csv, column '{column}': {len(keys)} {layer}(s) in "
                f"{rows} row(s) are not in this case's composition, so those rows "
                f"never fire: {named}.\n"
                f"          Expected when one coefficient table serves several runs. "
                f"If one of those is a typo, it is inert and silent -- check it."))
        else:
            problems.append(Problem(
                'ERROR', '-',
                f"TCs.csv, column '{column}': NO {layer} matches this case's "
                f"composition, so not one of these {rows} row(s) can ever fire.\n"
                f"          TCs.csv names: {named}\n"
                f"          composition has: "
                f"{', '.join(sorted(known[layer])) or 'none'}"))

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


def validate(folder: str, tables: dict | None = None) -> None:
    """Check a case, printing warnings and raising on errors."""
    report(folder, check(folder, tables))
