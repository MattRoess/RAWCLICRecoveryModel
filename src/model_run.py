"""
src/model_run.py
================

Solving a case and drawing its figures. The stage that calls this is
`04_run_model.py`; the logic lives here because a file whose name starts with
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
    Solve one case, write the solution, and draw its figures.

    The Sankeys are drawn unconditionally: they are the picture of this result,
    and a run that produced a number without the matching picture is how the
    two drift apart. The structure diagram is a switch, because it describes
    the TC table rather than the result and only changes when that table does.
    """
    model = ENGINES[params.run.engine](data_folder=folder, layer_names=LAYER_NAMES)
    solution = model.solve_models_and_write_to_output()

    print(f'\nCase   : {folder}')
    print(f'Engine : {params.run.engine}')
    if show_table:
        print()
        print(solution.to_string(index=False))
    print(f'\n{len(solution)} rows written to {folder}/output_data/')

    print()
    plot_flows.draw(folder, params)

    if params.run.draw_structure:
        print()
        plot_structure.draw(folder, params)

    return solution
