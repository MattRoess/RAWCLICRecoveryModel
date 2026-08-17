"""
Solve a data folder and write both the solution and the figures.

    ./.venv/bin/python run_model.py                        # the case in params.xlsx
    ./.venv/bin/python run_model.py data_folder/basic_test
    ./.venv/bin/python run_model.py --list

What is solved, with which engine, and which figures are drawn in which
formats all come from `params.xlsx`. Run `00_parameters.py` once to create it,
then edit it in Excel or Positron -- nothing here needs changing to run a
different case.

The optional folder argument overrides `run.data_folder` for one run, which is
the only override this script has: everything else belongs in the parameter
file.

The solution goes to <folder>/output_data/, and the figures to
`figures.out_dir` -- drawing them is part of a run rather than a separate step,
so a result and the picture of it cannot drift apart.
"""
import argparse
import os
import sys
import warnings

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plot_flows
import plot_structure
from src.params_io import ParameterError, load
from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("multi_sparse", False)
pd.set_option("display.float_format", "{:.2f}".format)

LAYER_NAMES = ['product', 'component', 'material', 'element']
ENGINES = {'optimized': RecoveryModelOptimized, 'LA': RecoveryModelLA}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('folder', nargs='?',
                        help='data folder to solve. Omit to use run.data_folder from params.xlsx.')
    parser.add_argument('--pick', action='store_true', help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the data folders that can be solved, then exit')
    parser.add_argument('-p', '--params', default=None,
                        help='parameter file (default: params.xlsx)')
    args = parser.parse_args(argv)

    if args.list:
        for case in plot_structure.find_cases():
            print(case)
        return

    params = load(args.params) if args.params else load()
    folder = args.folder or (plot_structure.choose() if args.pick else params.run.data_folder)

    model = ENGINES[params.run.engine](data_folder=folder, layer_names=LAYER_NAMES)
    solution = model.solve_models_and_write_to_output()
    print(f'\n{folder}  ({params.run.engine} engine)')
    print(solution.to_string(index=False))
    print(f'\n{len(solution)} rows written to {folder}/output_data/')

    if params.run.draw_flows:
        print()
        plot_flows.main(folder, params)

    if params.run.draw_structure:
        print()
        plot_structure.main(folder, params)


if __name__ == '__main__':
    try:
        main()
    except ParameterError as error:
        raise SystemExit(error)
