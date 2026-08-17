"""
00_parameters.py
================

Creates or refreshes `params.xlsx`, the parameter file every script reads, and
regenerates `documentation/PARAMETER_REFERENCE.md` from the same source.

    ./.venv/bin/python 00_parameters.py            # write params.xlsx
    ./.venv/bin/python 00_parameters.py --check    # validate it, change nothing
    ./.venv/bin/python 00_parameters.py --reset    # discard edits, back to defaults

Run it once to get the file. After that, edit `params.xlsx` in Excel or
Positron -- the scripts read it directly and nothing here needs running again
unless a new parameter is added to `src/params_schema.py`.

By default an existing file is preserved: its values are read, validated, and
written back, so refreshing to pick up a newly added parameter does not throw
away settings. `--reset` is the way to deliberately go back to the defaults.

This file is intentionally thin. Every parameter, its type, its default and its
documentation live in `src/params_schema.py`; reading and writing live in
`src/params_io.py`.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.params_io import PARAMS_FILE, ParameterError, load, reference, save
from src.params_schema import Params

REFERENCE_FILE = os.path.join('documentation', 'PARAMETER_REFERENCE.md')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    parser.add_argument('--check', action='store_true',
                        help='validate the existing file and report, writing nothing')
    parser.add_argument('--reset', action='store_true',
                        help='overwrite with the defaults, discarding any edits')
    parser.add_argument('-p', '--path', default=PARAMS_FILE,
                        help=f'parameter file to write (default: {PARAMS_FILE})')
    args = parser.parse_args(argv)

    if args.check:
        try:
            params = load(args.path, required=True)
        except ParameterError as error:
            print(error, file=sys.stderr)
            return 1
        print(f'{args.path} is valid.')
        for name, _, key, value in _rows(params):
            print(f'  {key:<28} {value}')
        return 0

    if args.reset or not os.path.exists(args.path):
        params = Params()
        action = 'reset to defaults' if args.reset else 'created'
    else:
        try:
            params = load(args.path)
        except ParameterError as error:
            print(error, file=sys.stderr)
            print('\nRun with --reset to discard the file and start from the defaults.',
                  file=sys.stderr)
            return 1
        action = 'refreshed, existing values kept'

    save(params, args.path)
    print(f'{args.path}: {action} ({len(_rows(params))} parameters)')

    os.makedirs(os.path.dirname(REFERENCE_FILE), exist_ok=True)
    with open(REFERENCE_FILE, 'w') as handle:
        handle.write(reference(params))
    print(f'{REFERENCE_FILE}: regenerated')
    return 0


def _rows(params: Params):
    from src.params_schema import flatten
    return flatten(params)


if __name__ == '__main__':
    raise SystemExit(main())
