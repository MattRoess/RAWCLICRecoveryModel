"""
01_check_inputs.py
========================

STEP 2 -- check that a dataset's numbers add up, before trusting a result.

    ./.venv/bin/python 01_check_inputs.py

Reports three things about the case named in `src/params_schema.py`:

  * COMPOSITION -- what each thing is made of should add up to 1. If it does
    not, the whole inflow is silently scaled up or down.
  * TRANSFER COEFFICIENTS -- how much of each resource goes where. A total
    above 1 creates mass out of nothing and is always an error. A total below 1
    means the missing mass leaves the system unrecorded.
  * STRUCTURE -- every transfer coefficient writing into one output flow has to
    describe the same layer, or deep rows end up larger than their own parents.

Nothing here changes any file. It only reports.

    ./.venv/bin/python 01_check_inputs.py <folder>   check one case
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


from src.mass_balance import report
from src.monte_carlo import MemoryBudgetExceeded
from src.params_schema import ParameterError, current
from src.sampling import SamplingError
from src.upstream import UpstreamError, load as refresh
from src.plot_structure import choose, find_cases
from src.validate_inputs import InputDataError, validate

# These four already say what is wrong and which file or setting to change.
# This is run by pressing Run in an editor, so a traceback on top of that text
# is noise in front of the answer, not a detail.
CLEAR = (InputDataError, UpstreamError, MemoryBudgetExceeded, SamplingError)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check that a dataset's numbers add up.")
    parser.add_argument('folder', nargs='?',
                        help='check this case, instead of the one in the settings')
    parser.add_argument('--pick', action='store_true', help='choose the case from a list')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the cases that can be checked, then stop')
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
    try:
        # Check the tables before totalling them. Without this a freshly
        # generated skeleton -- rows present, values blank -- reaches the
        # arithmetic and comes back as a TypeError from inside pandas, naming
        # neither the file nor the row.
        tables = refresh(params, folder)
        validate(folder, tables)
        return 0 if report(folder, tables) else 1
    except CLEAR as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
