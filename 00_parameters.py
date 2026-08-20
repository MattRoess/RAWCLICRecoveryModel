"""
00_parameters.py
================

Regenerates `params.xlsx` and `documentation/PARAMETER_REFERENCE.md` from the
values in `src/params_schema.py`.

    ./.venv/bin/python 00_parameters.py            # regenerate both
    ./.venv/bin/python 00_parameters.py --check    # validate, write nothing

**To change a parameter, edit `src/params_schema.py`**, then run this to
refresh the register. The spreadsheet and the Markdown reference are outputs:
editing either of them changes nothing, because nothing reads them.

This file is intentionally thin. Every parameter, its value and its
documentation live in `src/params_schema.py`; the writing lives in
`src/params_io.py`.
"""

from __future__ import annotations

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


from src.params_io import PARAMS_FILE, reference, save
from src.params_schema import ParameterError, current, data_status, flatten

REFERENCE_FILE = os.path.join('documentation', 'PARAMETER_REFERENCE.md')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    parser.add_argument('--check', action='store_true',
                        help='validate the values and print them, writing nothing')
    parser.add_argument('-p', '--path', default=PARAMS_FILE,
                        help=f'register to write (default: {PARAMS_FILE})')
    args = parser.parse_args(argv)

    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    rows = flatten(params)

    if args.check:
        print('src/params_schema.py is valid. Values in force:')
        for _, _, key, value in rows:
            print(f'  {key:<28} {value}')
        # A path that does not exist is not a settings error -- the deterministic
        # stages never open it -- but it is the single thing most worth knowing
        # before starting a Monte Carlo run, so --check says so plainly.
        print(f'\nUpstream draws\n  {data_status(params)}')
        return 0

    save(params, args.path)
    print(f'{args.path}: regenerated ({len(rows)} parameters)')

    os.makedirs(os.path.dirname(REFERENCE_FILE), exist_ok=True)
    with open(REFERENCE_FILE, 'w') as handle:
        handle.write(reference(params))
    print(f'{REFERENCE_FILE}: regenerated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
