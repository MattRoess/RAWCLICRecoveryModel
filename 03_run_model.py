"""
03_run_model.py
===============

STEP 1 -- solve the model and draw its figures.

    ./.venv/bin/python 03_run_model.py

This is the one you run. It reads the settings in `src/params_schema.py`,
solves the case named there, writes the answer next to the input data, and
draws the figures.

    ./.venv/bin/python 03_run_model.py --list     which cases are available
    ./.venv/bin/python 03_run_model.py --pick     choose one from a list
    ./.venv/bin/python 03_run_model.py <folder>   run one case just this once

The answer goes to <case folder>/output_data/. The figures go to figures/.

To change which case runs every time, or which figures are drawn, edit
`src/params_schema.py` -- not this file.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.model_run import solve_and_draw
from src.params_schema import ParameterError, current
from src.upstream import UpstreamError, load as refresh
from src.plot_structure import choose, find_cases


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Solve the model and draw its figures.')
    parser.add_argument('folder', nargs='?',
                        help='run this case just this once, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true',
                        help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases that can be run, then stop')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='do not print the full result table')
    args = parser.parse_args(argv)

    if args.list:
        print('Cases available:')
        for case in find_cases():
            print(f'  {case}')
        return 0

    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    folder = args.folder or (choose() if args.pick else params.run.data_folder)
    if not os.path.isdir(folder):
        print(f"There is no case folder called '{folder}'.\n"
              f"Check run.data_folder in src/params_schema.py, or run with --list "
              f"to see what is available.", file=sys.stderr)
        return 1

    solve_and_draw(folder, params, show_table=not args.quiet)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
