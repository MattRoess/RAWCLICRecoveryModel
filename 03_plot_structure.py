"""
03_plot_structure.py
====================

STEP 3 -- draw HOW THE MODEL IS WIRED: one page showing every flow, every
process, and the transfer coefficients behind each arrow.

    ./.venv/bin/python 03_plot_structure.py

Nothing on this diagram is scaled by mass. It answers "how is this set up",
not "how much goes where" -- for that, see step 4.

This is also drawn automatically by step 1 if `draw_structure` is set to True
in `src/params_schema.py`.

    ./.venv/bin/python 03_plot_structure.py --pick       choose from a list
    ./.venv/bin/python 03_plot_structure.py <folder>     draw one case

The file formats written are set by `png`, `svg` and `pdf` in
`src/params_schema.py`.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
