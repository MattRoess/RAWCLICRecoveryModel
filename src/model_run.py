"""
src/model_run.py
================

Solving a case and drawing its figures. The stage that calls this is
`01_run_model.py`; the logic lives here because a file whose name starts with
a digit cannot be imported by another file.

What is solved, with which engine, and which figures are drawn are all settings
in `src/params_schema.py`.
"""
from __future__ import annotations

import warnings

import pandas as pd

from src import plot_flows, plot_structure
from src.params_schema import Params
from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("multi_sparse", False)
pd.set_option("display.float_format", "{:.2f}".format)

LAYER_NAMES = ['product', 'component', 'material', 'element']
ENGINES = {'optimized': RecoveryModelOptimized, 'LA': RecoveryModelLA}


def solve_and_draw(folder: str, params: Params, show_table: bool = True) -> pd.DataFrame:
    """
    Solve one case, write the solution, and draw whatever the settings ask for.

    The figures are drawn here rather than in a separate step so that a result
    and the picture of it cannot drift apart.
    """
    model = ENGINES[params.run.engine](data_folder=folder, layer_names=LAYER_NAMES)
    solution = model.solve_models_and_write_to_output()

    print(f'\nCase   : {folder}')
    print(f'Engine : {params.run.engine}')
    if show_table:
        print()
        print(solution.to_string(index=False))
    print(f'\n{len(solution)} rows written to {folder}/output_data/')

    if params.run.draw_flows:
        print()
        plot_flows.draw(folder, params)

    if params.run.draw_structure:
        print()
        plot_structure.draw(folder, params)

    return solution
