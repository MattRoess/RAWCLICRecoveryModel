"""
plot_structure.py
=================

Draw HOW THE MODEL IS WIRED: one page showing every flow, every process, and
the transfer coefficients behind each arrow.

    ./.venv/bin/python tools/plot_structure.py

NOT a numbered step. `02_run_model.py` already draws this whenever
`draw_structure` is True, which it is by default. This file is here for when
you want the diagram on its own -- looking at a TC table you are still
building, or redrawing after editing one -- without solving anything.

That is also why it is the one figure that needs no result: it reads TCs.csv
and nothing else. Nothing on it is scaled by mass. It answers "how is this set
up", not "how much goes where".

    ./.venv/bin/python tools/plot_structure.py --pick       choose from a list
    ./.venv/bin/python tools/plot_structure.py <folder>     draw one case
    ./.venv/bin/python tools/plot_structure.py <TCs.csv>    draw any TC file

The file formats written are set by `png`, `svg` and `pdf` in
`src/params_schema.py`.
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

import argparse
import os
import sys


from src.params_schema import ParameterError, current
from src.plot_structure import choose, draw, find_cases


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Draw how the flows connect.')
    parser.add_argument('target', nargs='?',
                        help='draw this case, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true', help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases that can be drawn, then stop')
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

    draw(choose() if args.pick else args.target, params)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
