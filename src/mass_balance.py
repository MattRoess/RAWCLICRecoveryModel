"""
Report what the transfer coefficients in a data folder actually sum to, and
check the structural rules a TC table has to obey.

A TC is applied by joining on BOTH layer columns, so the resource it transfers
is identified by the *pair* (Input_layer_key, TC_target_key) -- "component C1
within product P1" -- not by the input key alone. The only sum that means
anything is therefore: for one such resource, the total over all the output
flows it can reach.

    ./.venv/bin/python check_mass_balance.py data_folder/reference/template

Also checks composition closure, the single-target-layer rule (see
documentation/DESIGN_tc_table.md), and the optional value_min/value_max
uncertainty columns if they are present.
"""
import os

import pandas as pd

TOLERANCE = 1e-9

# A resource is identified by where it comes from and what it becomes.
# Output_FlowID is deliberately absent: that is the axis we sum over.
# THE key: everything transferred as a unit, split across the output flows it
# reaches. Grouping by anything else produces numbers that are not quantities
# (MODEL_MECHANICS.md section 4), which is why this is defined once and imported
# rather than retyped -- it had been written out five times.
RESOURCE = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
            'TC_target_layer', 'TC_target_key']


def check_transfer_coefficients(tcs: pd.DataFrame) -> pd.DataFrame:
    """Total each transferred resource's TCs over the output flows it reaches."""
    totals = tcs.groupby(RESOURCE).agg(
        total=('value', 'sum'),
        destinations=('Output_FlowID', 'nunique'),
        rows=('value', 'size'),
    ).reset_index()

    # More TC rows than destinations means one resource is routed to the same
    # output flow twice. The engines disagree about what that means, so flag it.
    totals['duplicated'] = totals['rows'] > totals['destinations']
    return totals


def check_single_target_layer(tcs: pd.DataFrame) -> pd.DataFrame:
    """
    Find output flows written by TCs that target different layers.

    A TC targeting a coarse layer carries the resource's whole subtree with it,
    producing rows at every depth. One targeting a fine layer produces rows at
    that depth only. Summing both into one flow makes deep rows exceed their
    own parents, which breaks the nesting invariant the entire model rests on.
    """
    per_flow = tcs.groupby('Output_FlowID')['TC_target_layer'].agg(['nunique', 'unique'])
    return per_flow[per_flow['nunique'] > 1]


def check_uncertainty(tcs: pd.DataFrame) -> pd.DataFrame | None:
    """Validate the optional triangular columns, returning offending rows."""
    if not {'value_min', 'value_max'}.issubset(tcs.columns):
        return None
    bad = tcs[(tcs['value_min'] > tcs['value']) | (tcs['value'] > tcs['value_max'])
              | (tcs['value_min'] < 0) | (tcs['value_max'] > 1)]
    return bad


def check_composition(composition: pd.DataFrame) -> pd.DataFrame:
    """Total each parent resource's composition shares, which must come to 1."""
    layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
    composition = composition.copy()
    composition['depth'] = (composition[layers] != '').sum(axis=1)

    results = []
    for depth in sorted(composition['depth'].unique()):
        # The parent is everything to the left of the layer being described --
        # including the year, scenario or location when the composition carries
        # them. Grouping without those adds every year's shares together, so a
        # five-year table reports totals of 5 and "DOES NOT CLOSE" for data that
        # closes perfectly. Same rule as src/rest.py, which derives the rests.
        from src.rest import _parent_columns
        parent = _parent_columns(depth, composition)
        totals = composition[composition['depth'] == depth].groupby(parent)['Value'].sum()
        results.append({'depth': depth, 'parents': len(totals),
                        'min': totals.min(), 'max': totals.max()})
    return pd.DataFrame(results)


def report(folder: str, tables: dict | None = None) -> bool:
    # Only TCs.csv is a file. The inflow and composition come from the upstream
    # draws in memory, so a case that has them handed over needs nothing on disk.
    from src import case_tables

    given = tables or {}
    missing = []
    if given.get('tcs') is None and not case_tables.exists(folder, 'TCs'):
        missing.append('transfer coefficients')
    if given.get('composition') is None and not os.path.exists(
            os.path.join(folder, 'input_data', 'composition.csv')):
        missing.append('composition.csv')
    if missing:
        print(f"\nNothing to check in '{folder}': missing {', '.join(missing)}")
        print(f"Expected them in {os.path.join(folder, 'input_data')}.")
        print("\nData folders that do have them:")
        for root, _, files in os.walk('data_folder'):
            if 'TCs.csv' in files or 'case.xlsx' in files:
                print(f"  {os.path.dirname(root)}")
        return False

    read = dict(keep_default_na=False, na_values=[])
    given = tables or {}
    tcs = given.get('tcs')
    if tcs is None:
        tcs = case_tables.read(folder, 'TCs')
    # Coerce the three bound columns once, here, rather than at each use. A row
    # derived as its group's residual carries no range of its own, so its bounds
    # are blank -- and a blank read as a string turns every later comparison and
    # subtraction into str arithmetic, which fails somewhere far from the cause.
    if {'value_min', 'value_max'}.issubset(tcs.columns):
        from src.sampling import numeric_bounds
        tcs = numeric_bounds(tcs)
    composition = given.get('composition')
    if composition is None:
        composition = pd.read_csv(f"{folder}/input_data/composition.csv", **read)
    # The engine derives a `rest` child for every parent whose known children
    # fall short, so closure has to be judged on the table the engine actually
    # solves. Reading the raw file reported "DOES NOT CLOSE" for exactly the
    # parents the rest rows complete -- the check disagreeing with the model.
    from src.rest import add_rest
    composition, rest_notes = add_rest(composition)
    print(f"\n{folder}")

    closure = check_composition(composition)
    print("\nCOMPOSITION -- shares within each parent, which must sum to 1")
    if rest_notes:
        print(f"  {len(rest_notes)} parent(s) incomplete; a `rest` child was derived:")
        for note in rest_notes:
            print(f"    {note}")
    for _, row in closure.iterrows():
        closes = abs(row['min'] - 1) < TOLERANCE and abs(row['max'] - 1) < TOLERANCE
        print(f"  depth {int(row['depth'])}: {int(row['parents']):5d} parents, "
              f"range [{row['min']:.6g}, {row['max']:.6g}]  {'OK' if closes else 'DOES NOT CLOSE'}")

    totals = check_transfer_coefficients(tcs)
    splits = totals[totals['destinations'] > 1]
    single = totals[totals['destinations'] == 1]
    closes = (totals['total'] - 1).abs() < TOLERANCE
    over = totals['total'] > 1 + TOLERANCE

    print("\nTRANSFER COEFFICIENTS -- per resource, totalled over its output flows")
    print(f"  {len(totals)} distinct resources transferred")
    print(f"    {len(single):5d} reach exactly one output flow")
    print(f"    {len(splits):5d} split across several output flows")
    print(f"    {int(closes.sum()):5d} total exactly 1  (mass conserved by construction)")
    print(f"    {int(over.sum()):5d} total ABOVE 1     (impossible -- creates mass)")
    print(f"  range of totals: [{totals['total'].min():.4g}, {totals['total'].max():.4g}]")

    if over.any():
        print("\n  ERROR -- these create mass:")
        for _, row in totals[over].iterrows():
            print(f"    {row['Input_FlowID']} / {row['Input_layer_key']} -> "
                  f"{row['TC_target_key']}: {row['total']:.4g}")

    unaccounted = 1 - totals['total']
    if (unaccounted.abs() > TOLERANCE).any():
        leaking = unaccounted[unaccounted.abs() > TOLERANCE]
        print(f"\n  {len(leaking)} resources do not total 1. Unaccounted fraction: "
              f"mean {leaking.mean():.3f}, max {leaking.max():.3f}")
        print("  That mass is not routed anywhere and leaves the system unrecorded.")
        print("  Adding explicit per-process loss flows is what closes this.")
    else:
        print("\n  All resources total exactly 1: mass is conserved by construction.")

    if totals['duplicated'].any():
        print(f"\n  WARNING: {int(totals['duplicated'].sum())} resources routed to the same output "
              f"flow more than once. The engines disagree here -- see documentation/DEFECTS.md 2.3.")

    mixed = check_single_target_layer(tcs)
    print("\nSTRUCTURE -- every TC writing into one output flow must target the same layer")
    if len(mixed):
        print(f"  ERROR: {len(mixed)} output flows are written at mixed layers.")
        print("  This breaks the nesting invariant: deep rows will exceed their own parents.")
        for flow, row in mixed.iterrows():
            print(f"    {flow}: {', '.join(sorted(row['unique']))}")
    else:
        print("  OK -- no output flow is written at mixed layers.")

    uncertainty = check_uncertainty(tcs)
    print("\nUNCERTAINTY -- optional value_min / value_max triangular columns")
    if uncertainty is None:
        print("  Not present. The table is deterministic; the Monte Carlo needs these.")
    elif len(uncertainty):
        print(f"  ERROR: {len(uncertainty)} rows violate 0 <= value_min <= value <= value_max <= 1")
        print(uncertainty.head(10).to_string(index=False))
    else:
        spread = tcs['value_max'] - tcs['value_min']
        skew = ((tcs['value_max'] - tcs['value']) - (tcs['value'] - tcs['value_min']))
        print(f"  OK -- {len(tcs)} rows, all with 0 <= min <= mode <= max <= 1")
        print(f"  width  : mean {spread.mean():.3f}, max {spread.max():.3f}")
        print(f"  skew   : {int((skew.abs() > TOLERANCE).sum())} of {len(tcs)} asymmetric "
              f"(mode off-centre), mean signed skew {skew.mean():+.3f}")

    # A blend the run cannot sample is a FAILED check, not a printed note.
    # Reporting it and returning True gave a green light from 01_check_inputs
    # and a crash from 03_run_monte_carlo on the same data -- the two disagreeing
    # about whether a case is runnable, which is worse than either verdict.
    ramp_ok = report_uncertainty_over_time(folder, given)
    report_sum_to_one(tcs)
    return ramp_ok


def _years_of(given: dict, folder: str) -> list[str] | None:
    """
    The years a case is solved at, from whichever of its sources exists.

    General on purpose: a case may arrive with its frames already in memory, or
    as csv files on disk, or -- for a case whose inflow comes from somewhere
    this check cannot see -- as nothing but an improvement window. The window is
    the last resort and is stepped by one year, so a blend that only goes bad
    part-way along is still caught.
    """
    inputs = given.get('inputs')
    if inputs is None:
        path = os.path.join(folder, 'input_data', 'inputs.csv')
        if os.path.exists(path):
            inputs = pd.read_csv(path, keep_default_na=False, na_values=[])
    if inputs is not None and 'Year' in inputs.columns:
        found = sorted({str(y).strip() for y in inputs['Year'] if str(y).strip()})
        if found:
            return found

    from src import source as source_table
    if not source_table.exists(folder):
        return None
    try:
        described = source_table.read(folder, None)
    except Exception:
        return None
    start, end = described.get('improvement_start'), described.get('improvement_end')
    if not str(start).strip() or not str(end).strip():
        return None
    return [str(y) for y in range(int(start), int(end) + 1)]


def report_uncertainty_over_time(folder: str, given: dict) -> bool:
    """
    Check `TCs_improved`, and every year the run will actually solve.

    `TCs_improved` was checked by nothing. Gold on the boards case was written
    min 0.995, mode 0.980, max 0.960 -- a min above its own max -- and this
    report said the case was clean because it only ever read `TCs`. The run
    then died halfway along the ramp, quoting three blended numbers that appear
    in neither sheet.

    THE FAULT IS ALWAYS IN A SHEET SOMEBODY TYPED, never in the blending. min,
    mode and max each interpolate linearly, so `mode_w - min_w` is a sum of two
    non-negative terms and the ordering survives any weight in [0, 1]: a ramped
    year can only be invalid if one of the two tables already was. (Pinned by
    `test_a_blend_of_two_valid_tables_is_always_valid`; the first version of
    this check was written on the opposite belief and told the reader the blend
    was at fault, which would have sent them looking in the wrong place.)

    So the years are checked because they are what the run samples and they
    name the point where it will stop -- but what is REPORTED is the sheet, the
    row, and the numbers as written, because that is the only place they can be
    corrected.
    """
    from src import case_tables
    if not case_tables.exists(folder, case_tables.IMPROVED):
        return True

    # The years this case will actually be solved at, so the report can name
    # the year the run would stop at. From the upstream frames when a run handed
    # them over, from inputs.csv when it did not, and from the improvement
    # window itself when a case has neither.
    years = _years_of(given, folder)
    try:
        ramped = case_tables.coefficients(folder, years)
    except Exception as error:                 # said plainly, not raised here
        print(f"\nIMPROVEMENT OVER TIME -- {case_tables.IMPROVED}")
        print(f"  ERROR: {error}")
        return False

    from src.sampling import numeric_bounds
    ramped = numeric_bounds(ramped)
    bad = check_uncertainty(ramped)
    span = f"{years[0]}-{years[-1]}" if years else 'every year'
    print(f"\nIMPROVEMENT OVER TIME -- the table the run samples, one per year")

    # CLOSURE, TOO. `TCs` closing to 1 says nothing about `TCs_improved`: on the
    # boards case copper out of F_ground summed to 1.035 there, so every year
    # from the window on created 3.5% of the copper it reported, and the only
    # thing that noticed was the mass balance at the very END of the pipeline --
    # after a full 200,000-draw run. Like the ordering check, a blend cannot
    # introduce this (a convex combination of two vectors summing to 1 sums to
    # 1), so the fault is in one of the sheets.
    open_groups = _closure_faults(folder, ramped, case_tables)

    if (bad is None or not len(bad)) and not open_groups:
        print(f"  OK -- {len(ramped)} rows across {span}, all with "
              f"0 <= min <= mode <= max <= 1, every resource totalling 1")
        return True

    identity = ['Input_FlowID', 'Input_layer_key', 'Output_FlowID', 'TC_target_key']
    if bad is not None and len(bad):
        print(f"  ERROR: {len(bad)} row(s) violate "
              f"0 <= value_min <= value <= value_max <= 1 in the table the run "
              f"samples.")
        print(f"  Correct it in whichever sheet below has min, mode and max out "
              f"of order -- the blending cannot introduce this, so one of them "
              f"already has it.")
    shown = (bad.drop_duplicates(subset=identity).head(10)
             if bad is not None and len(bad) else bad.head(0) if bad is not None
             else None)
    for _, row in (shown.iterrows() if shown is not None else ()):
        who = (f"{row['Input_FlowID']} {row['Input_layer_key']} -> "
               f"{row['Output_FlowID']} {row['TC_target_key']}")
        print(f"    {who}   first bad year {row.get('Year', '?')}")
        for sheet in (case_tables.TABLES[2], case_tables.IMPROVED):
            table = numeric_bounds(case_tables.read(folder, sheet))
            match = table
            for column in identity:
                match = match[match[column] == row[column]]
            if len(match):
                one = match.iloc[0]
                print(f"      {sheet:14} min {one['value_min']:<8.4g} "
                      f"mode {one['value']:<8.4g} max {one['value_max']:<8.4g}")

    for line in open_groups:
        print(line)
    return False


def _closure_faults(folder: str, ramped: pd.DataFrame, case_tables) -> list[str]:
    """
    Resources that do not total 1 in the ramped table, and which sheet does it.

    Returns the lines to print, empty when everything closes. Reported rather
    than raised so one run of the check shows every fault at once.
    """
    # PER YEAR. The ramped table holds one copy of every coefficient per year,
    # so totalling it whole gives 11, not 1 -- which faults every resource in
    # the case and says nothing. Each year has to close on its own.
    numeric = ramped.assign(
        **{'value': pd.to_numeric(ramped['value'], errors='coerce')})
    per_year = ([(year, block) for year, block in numeric.groupby('Year')]
                if 'Year' in numeric.columns else [(None, numeric)])
    faulted = []
    for year, block in per_year:
        totals = check_transfer_coefficients(block)
        bad_rows = totals[(totals['total'] - 1).abs() > TOLERANCE]
        if len(bad_rows):
            faulted.append((year, bad_rows))
    if not faulted:
        return []
    first_year, off = faulted[0]

    lines = [f"  ERROR: {len(off)} resource(s) do not total 1 in "
             f"{first_year or 'the table the run samples'}"
             f"{f' (and {len(faulted) - 1} further year(s))' if len(faulted) > 1 else ''}"
             f", so mass is created or destroyed."]
    per_sheet = {}
    for sheet in (case_tables.TABLES[2], case_tables.IMPROVED):
        table = case_tables.read(folder, sheet)
        table = table.assign(**{'value': pd.to_numeric(table['value'],
                                                       errors='coerce')})
        sheet_totals = check_transfer_coefficients(table)
        per_sheet[sheet] = sheet_totals.set_index(RESOURCE)['total']

    for _, row in off.drop_duplicates(subset=RESOURCE).head(10).iterrows():
        key = tuple(row[column] for column in RESOURCE)
        who = (f"{row['Input_FlowID']} {row['Input_layer_key']} -> "
               f"{row['TC_target_key']}")
        lines.append(f"    {who}")
        for sheet, sheet_totals in per_sheet.items():
            if key in sheet_totals.index:
                total = float(sheet_totals.loc[key])
                mark = 'OK' if abs(total - 1) <= TOLERANCE else 'FIX THIS SHEET'
                lines.append(f"      {sheet:14} totals {total:<8.6g} {mark}")
    return lines


# How far a group may sit from 1, in standard deviations of its own independent
# sum, before it is worth naming. Below this the constraint barely moves it.
OFFSET_TO_REPORT = 0.5


def report_sum_to_one(tcs: pd.DataFrame) -> None:
    """
    Say whether the measured ranges are compatible with summing to 1.

    A constrained group's modes sum to 1 by construction. Its means need not,
    because a triangular's mean is (min + mode + max) / 3 and an off-centre
    mode pulls the two apart. Where they disagree, enforcing the constraint
    has to move the answer away from the numbers in the sheet -- and that is
    the difference the Monte Carlo already reports as a gap between running at
    the modes and running the full distributions. This says which groups it
    comes from, before a run rather than after.
    """
    from src.sampling import group_consistency

    consistency = group_consistency(tcs)
    print("\nSUM TO 1 -- do the measured ranges agree with the constraint?")
    if not len(consistency):
        print("  No constrained groups: no group's modes sum to 1, so nothing "
              "is corrected.")
        return

    offset = consistency['offset'].abs()
    print(f"  {len(consistency)} constrained groups")
    print(f"  offset from 1, in standard deviations of the group's own sum: "
          f"median {offset.median():.2f}, max {offset.max():.2f}")

    worth_naming = consistency[offset > OFFSET_TO_REPORT]
    if not len(worth_naming):
        print("  All groups sit within half a standard deviation of 1. The "
              "ranges already\n  agree with the constraint, so enforcing it "
              "changes little.")
        return

    print(f"  {len(worth_naming)} group(s) beyond {OFFSET_TO_REPORT} sd -- "
          f"drawn independently these do NOT\n  average to 1, so the "
          f"constraint moves them away from the values written:")
    # RANKED WITHIN `worth_naming`, not against every group. Reindexing the
    # three rows above the threshold onto the index of all fourteen inserted a
    # NaN row for each of the eleven below it, and `.head(8)` then printed three
    # real lines and five `nan nan -> nan`.
    #
    # It only showed up on a small case. Sorting every group by offset puts the
    # ones over the threshold first, so with eight or more of them `.head(8)`
    # happened to take the right eight -- which is why 04_01, with 65 of them,
    # never revealed it in weeks of runs. Fewer than eight, and the sorted index
    # runs on into groups that are not in the frame at all.
    ranked = worth_naming.loc[worth_naming['offset'].abs()
                              .sort_values(ascending=False).index]
    for _, row in ranked.head(8).iterrows():
        print(f"    {row['Input_layer_key']} {row['TC_target_key']} -> "
              f"{row['Input_FlowID']}: independent sum averages "
              f"{row['sum_mean']:.4f}, {row['offset']:+.2f} sd from 1")
    if len(worth_naming) > 8:
        print(f"    ... and {len(worth_naming) - 8} more")
    print("  This is not an error. It is the reason a run at the modes and a "
          "run of the\n  full distributions give different answers.")

