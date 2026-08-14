"""
Report what the transfer coefficients in a data folder actually sum to.

A TC is applied by joining on BOTH layer columns, so the resource it transfers
is identified by the *pair* (Input_layer_key, TC_target_key) -- "component C1
within product P1" -- not by the input key alone. The only sum that means
anything is therefore: for one such resource, the total over all the output
flows it can reach.

    ./.venv/bin/python check_mass_balance.py data_folder/basic_test

Composition is checked too: shares must sum to 1 within each parent, or the
inflow expansion silently creates or destroys mass.
"""
import os
import sys

import pandas as pd

TOLERANCE = 1e-9

# A resource is identified by where it comes from and what it becomes.
# Output_FlowID is deliberately absent: that is the axis we sum over.
RESOURCE = ['Input_FlowID', 'Input_layer', 'Input_layer_key', 'TC_target_layer', 'TC_target_key']


def check_transfer_coefficients(folder: str) -> pd.DataFrame:
    """Total each transferred resource's TCs over the output flows it reaches."""
    tcs = pd.read_csv(f"{folder}/input_data/TCs.csv", keep_default_na=False, na_values=[])
    totals = tcs.groupby(RESOURCE).agg(
        total=('value', 'sum'),
        destinations=('Output_FlowID', 'nunique'),
        rows=('value', 'size'),
    ).reset_index()

    # More TC rows than destinations means one resource is routed to the same
    # output flow twice. The engines disagree about what that means, so flag it.
    totals['duplicated'] = totals['rows'] > totals['destinations']
    return totals


def check_composition(folder: str) -> pd.DataFrame:
    """Total each parent resource's composition shares, which must come to 1."""
    composition = pd.read_csv(f"{folder}/input_data/composition.csv", keep_default_na=False, na_values=[])
    layers = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']
    composition['depth'] = (composition[layers] != '').sum(axis=1)

    results = []
    for depth in sorted(composition['depth'].unique()):
        # The parent is everything to the left of the layer being described.
        parent = ['Stock/ID'] + layers[:depth - 1]
        totals = composition[composition['depth'] == depth].groupby(parent)['Value'].sum()
        results.append(pd.DataFrame({'depth': depth, 'parent_groups': len(totals),
                                     'min': totals.min(), 'max': totals.max()}, index=[0]))
    return pd.concat(results, ignore_index=True)


def report(folder: str) -> None:
    missing = [name for name in ('TCs.csv', 'composition.csv')
               if not os.path.exists(os.path.join(folder, 'input_data', name))]
    if missing:
        print(f"\nNothing to check in '{folder}': missing {', '.join(missing)}")
        print(f"Expected them in {os.path.join(folder, 'input_data')}.")
        print("\nData folders that do have them:")
        for root, _, files in os.walk('data_folder'):
            if 'TCs.csv' in files:
                print(f"  {os.path.dirname(root)}")
        sys.exit(1)

    print(f"\n{folder}")

    composition = check_composition(folder)
    closes = ((composition['min'] - 1).abs() < TOLERANCE) & ((composition['max'] - 1).abs() < TOLERANCE)
    print("\nCOMPOSITION -- shares within each parent, which must sum to 1")
    for _, row in composition.iterrows():
        verdict = "OK" if closes[row.name] else "DOES NOT CLOSE"
        print(f"  depth {int(row['depth'])}: {int(row['parent_groups']):5d} parents, "
              f"range [{row['min']:.6g}, {row['max']:.6g}]  {verdict}")

    totals = check_transfer_coefficients(folder)
    splits = totals[totals['destinations'] > 1]
    single = totals[totals['destinations'] == 1]
    print("\nTRANSFER COEFFICIENTS -- per resource, totalled over its output flows")
    print(f"  {len(totals)} distinct resources transferred")
    print(f"    {len(single)} reach exactly one output flow  -> nothing to sum; each is a retention fraction")
    print(f"    {len(splits)} split across several output flows -> these are the ones a sum-to-1 rule would bind")

    if len(splits):
        print("\n  Resources that genuinely split:")
        for _, row in splits.iterrows():
            print(f"    {row['Input_FlowID']:>4} {row['Input_layer_key']:>4} -> {row['TC_target_key']:<4} "
                  f"across {row['destinations']} flows, total {row['total']:.4g}")

    out_of_range = totals[(totals['total'] < -TOLERANCE) | (totals['total'] > 1 + TOLERANCE)]
    print(f"\n  totalling exactly 1: {int((totals['total'] - 1).abs().lt(TOLERANCE).sum())} of {len(totals)}")
    print(f"  totalling above 1 (impossible -- creates mass): {len(out_of_range)}")
    print(f"  range of totals: [{totals['total'].min():.4g}, {totals['total'].max():.4g}]")

    if totals['duplicated'].any():
        print(f"\n  WARNING: {int(totals['duplicated'].sum())} resources routed to the same output flow "
              f"more than once. The two engines resolve this differently -- see documentation/DEFECTS.md 2.3.")

    unaccounted = 1 - totals['total']
    print(f"\n  Unaccounted fraction (1 - total), which currently goes nowhere:")
    print(f"    mean {unaccounted.mean():.3f}, min {unaccounted.min():.3f}, max {unaccounted.max():.3f}")
    print("  Nothing in the model records this. Adding explicit loss flows is what")
    print("  would make it visible, and a sum-to-1 rule checkable.")


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else "data_folder/basic_test")
