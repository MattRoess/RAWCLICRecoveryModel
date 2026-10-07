"""
src/model_run.py
================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

Solving a case and drawing its figures. The stage that calls this is
`stages/02_run_model.py`; the logic lives here because a file whose name starts with
a digit cannot be imported by another file.

What is solved, with which engine, and which figures are drawn are all settings
in `src/params_schema.py`.
"""
from __future__ import annotations

import warnings

import pandas as pd

from src import plot_flows, plot_structure
from src.params_schema import Params
from src.upstream import load as load_upstream
import os

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
    # The inflow and composition come straight from the upstream draws, in
    # memory. Nothing is written between there and here: a copy on disk is a
    # second version of the truth, and it goes stale the moment upstream re-runs.
    tables = load_upstream(params, folder)

    # THE SCENARIO IS PASSED, NOT LOOKED UP. The engine's fallback builds a
    # Params() of its own, which cannot see one set on the params this was
    # handed -- and a stage that walks the scenarios sets it there. Left to the
    # fallback, every scenario after the first was refused for naming a
    # scenario its own data did not carry, which is the same second source of
    # truth that 03 and plot_flows were fixed for.
    model = ENGINES[params.run.engine](data_folder=folder, layer_names=LAYER_NAMES,
                                       tables=tables,
                                       scenario=params.run.scenario)
    solution = model.solve_models_and_write_to_output()

    print(f'\nCase   : {folder}')
    print(f'Engine : {params.run.engine}')
    if show_table:
        print()
        print(solution.to_string(index=False))
    # WHERE IT ACTUALLY WENT. `output_path` appends the scenario, so this said
    # output_data/ while the file landed in output_data/S1/ -- a line that
    # sends a reader to the wrong folder is worse than no line.
    print(f'\n{len(solution)} rows written to '
          f'{os.path.dirname(model.output_path("solution.csv"))}/')

    print()
    plot_flows.draw(folder, params, tables)

    if params.run.draw_structure:
        print()
        plot_structure.draw(folder, params)

    return solution
