"""
04_plot_flows.py
================

STEP 4 -- draw HOW MUCH MASS GOES WHERE, as Sankey diagrams: one for the total
and, unless switched off, one per element.

    ./.venv/bin/python 04_plot_flows.py

The width of every ribbon is mass. This is the picture of a result, so it
re-solves the case to draw it -- which is also why step 1 draws these for you
and you rarely need to run this yourself.

    ./.venv/bin/python 04_plot_flows.py --pick       choose from a list
    ./.venv/bin/python 04_plot_flows.py <folder>     draw one case

The file formats written are set by `png`, `svg` and `pdf` in
`src/params_schema.py`, and `element_figures` turns the per-element figures on
and off.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.params_schema import ParameterError, current
from src.plot_flows import draw
from src.plot_structure import choose, find_cases


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Draw the Sankey diagrams of a result.')
    parser.add_argument('folder', nargs='?',
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

    draw(choose() if args.pick else args.folder, params)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
