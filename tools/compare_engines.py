"""
Run both engines over a data folder and print their results side by side.

The two engines agree on data_folder/reference/basic_test but not in general. This script
is how that was established and is how the cases in documentation/DEFECTS.md
are reproduced:

    ./.venv/bin/python tools/compare_engines.py data_folder/reference/defect_cases/tc_specificity

With no argument it runs data_folder/reference/basic_test, where the two agree exactly.
"""

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


import os
import sys

import numpy as np
import pandas as pd

from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

LAYER_NAMES = ['product', 'component', 'material', 'element']
KEYS = ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4']


def run(model_class, data_folder: str) -> pd.DataFrame:
    """Solve a data folder with one engine, returning an empty frame if it raises."""
    try:
        model = model_class(data_folder=data_folder, layer_names=LAYER_NAMES)
        return model.solve_models_and_write_to_output()
    except Exception as error:
        print(f"  {model_class.__name__} failed: {type(error).__name__}: {error}")
        return pd.DataFrame(columns=KEYS + ['Value'])


def compare(data_folder: str) -> pd.DataFrame:
    """Outer-join both engines' solutions so that disagreements are visible."""
    optimized = run(RecoveryModelOptimized, data_folder)
    linear_algebra = run(RecoveryModelLA, data_folder)

    merged = optimized.merge(
        linear_algebra, on=KEYS, how='outer', suffixes=('_optimized', '_LA')
    )
    merged = merged[KEYS + ['Value_optimized', 'Value_LA']].fillna({'Value_optimized': 0, 'Value_LA': 0})
    merged['difference'] = merged['Value_optimized'] - merged['Value_LA']
    return merged.sort_values(KEYS)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "data_folder/reference/basic_test"
    print(f"\n{folder}")
    result = compare(folder)
    print(result.to_string(index=False))

    largest_difference = np.abs(result['difference']).max()
    if largest_difference > 1e-9:
        print(f"\nENGINES DISAGREE: largest difference {largest_difference:g}")
    else:
        print(f"\nEngines agree (largest difference {largest_difference:.2e})")
