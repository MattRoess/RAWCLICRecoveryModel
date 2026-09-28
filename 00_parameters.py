"""
00_parameters.py
================

Regenerates `params.xlsx` and `documentation/PARAMETER_REFERENCE.md` from the
values in `src/params_schema.py`.

    ./.venv/bin/python 00_parameters.py

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


import os
import sys


from src.params_io import PARAMS_FILE, reference, save
from src.params_schema import ParameterError, current, data_status, flatten

REFERENCE_FILE = os.path.join('documentation', 'PARAMETER_REFERENCE.md')


def main(argv=None) -> int:
    """
    Validate the settings, print them, and regenerate the register.

    NO ARGUMENTS, AND NOT BY OVERSIGHT. This project is run by pressing Run;
    a switch that only exists on a command line is a switch the person running
    this never sees.

    WHAT `--check` USED TO DO IS NOW ALWAYS DONE. It validated, printed the
    values in force and said whether the upstream draws were there, and wrote
    nothing. All of that is worth seeing on every run -- the settings are the
    thing this file exists to report -- so it is printed first and the register
    is written afterwards. Writing it is harmless: both outputs are generated
    and nothing reads them.
    """
    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    rows = flatten(params)

    print('src/params_schema.py is valid. Values in force:')
    for _, _, key, value in rows:
        print(f'  {key:<28} {value}')
    # A path that does not exist is not a settings error -- the deterministic
    # stages never open it -- but it is the single thing most worth knowing
    # before starting a Monte Carlo run, so this says so plainly.
    print(f'\nUpstream draws\n  {data_status(params)}\n')

    save(params, PARAMS_FILE)
    print(f'{PARAMS_FILE}: regenerated ({len(rows)} parameters)')

    os.makedirs(os.path.dirname(REFERENCE_FILE), exist_ok=True)
    with open(REFERENCE_FILE, 'w') as handle:
        handle.write(reference(params))
    print(f'{REFERENCE_FILE}: regenerated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
