"""
Solve a data folder and write both the solution and the flow figures.

    ./.venv/bin/python run_model.py                          # pick from a list
    ./.venv/bin/python run_model.py data_folder/template
    ./.venv/bin/python run_model.py data_folder/template --engine LA
    ./.venv/bin/python run_model.py data_folder/template --structure
    ./.venv/bin/python run_model.py data_folder/template --no-figures

The data folder is an argument, never an edit to this file. With no argument
the discoverable cases are listed and one is chosen.

The solution goes to <folder>/output_data/, and the Sankey figures to
figures/ -- drawing them is part of a run rather than a separate step, so a
result and the picture of it cannot drift apart.
"""
import argparse
import warnings

import pandas as pd

import plot_flows
from plot_structure import choose, find_cases
from src.recovery_model_LA import RecoveryModelLA
from src.recovery_model_optimized import RecoveryModelOptimized

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("multi_sparse", False)
pd.set_option("display.float_format", "{:.2f}".format)

LAYER_NAMES = ['product', 'component', 'material', 'element']
ENGINES = {'optimized': RecoveryModelOptimized, 'LA': RecoveryModelLA}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n\n')[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target', nargs='?',
                        help='data folder to solve. Omit to choose from a list.')
    parser.add_argument('-e', '--engine', choices=sorted(ENGINES), default='optimized',
                        help='which engine to solve with (default: optimized). '
                             'The two disagree beyond basic_test -- see documentation/DEFECTS.md.')
    parser.add_argument('--no-figures', action='store_true',
                        help='solve only, skip the Sankey figures')
    parser.add_argument('--structure', action='store_true',
                        help='also draw the structure diagram (plot_structure.py)')
    parser.add_argument('-o', '--out', default='figures',
                        help='figure output directory (default: figures)')
    parser.add_argument('-f', '--formats', default='svg,png,pdf',
                        help='structure diagram formats (default: svg,png,pdf)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the data folders that can be solved, then exit')
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    if args.list:
        for case in find_cases():
            print(case)
        return

    folder = args.target or choose()

    model = ENGINES[args.engine](data_folder=folder, layer_names=LAYER_NAMES)
    solution = model.solve_models_and_write_to_output()
    print(f'\n{folder}  ({args.engine} engine)')
    print(solution.to_string(index=False))
    print(f'\n{len(solution)} rows written to {folder}/output_data/')

    if not args.no_figures:
        print()
        plot_flows.main(folder)

    if args.structure:
        # Imported here so that --no-figures runs never pay for matplotlib.
        import plot_structure
        tcs_path, case = plot_structure.resolve(folder)
        tcs = pd.read_csv(tcs_path, keep_default_na=False, na_values=[])
        figure = plot_structure.render(tcs, case)
        formats = [f.strip() for f in args.formats.split(',') if f.strip()]
        for path in plot_structure.write(figure, args.out, case, formats, dpi=200):
            print(f'  wrote {path}')


if __name__ == '__main__':
    main()
