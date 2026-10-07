"""
01_check_inputs.py
========================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

STEP 2 -- check that a dataset's numbers add up, before trusting a result.

    ./.venv/bin/python stages/01_check_inputs.py

Reports three things about the case named in `src/params_schema.py`:

  * COMPOSITION -- what each thing is made of should add up to 1. If it does
    not, the whole inflow is silently scaled up or down.
  * TRANSFER COEFFICIENTS -- how much of each resource goes where. A total
    above 1 creates mass out of nothing and is always an error. A total below 1
    means the missing mass leaves the system unrecorded.
  * STRUCTURE -- every transfer coefficient writing into one output flow has to
    describe the same layer, or deep rows end up larger than their own parents.

Nothing here changes any file. It only reports.

"""

import os
import sys

# Run under the project interpreter whatever was typed, and put the repo
# root on the path. Must come before any third-party import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if os.path.basename(os.path.dirname(os.path.abspath(__file__)))
                in ('tests', 'tools', 'stages')
                else os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv
ensure_venv()

import os
import sys


from src.mass_balance import report
from src.monte_carlo import MemoryBudgetExceeded
from src.params_schema import ParameterError, current
from src.sampling import SamplingError
from src.upstream import (UpstreamError, cases_to_run, load as refresh,
                          scenarios_to_run)
from src.validate_inputs import InputDataError, validate

# These four already say what is wrong and which file or setting to change.
# This is run by pressing Run in an editor, so a traceback on top of that text
# is noise in front of the answer, not a detail.
CLEAR = (InputDataError, UpstreamError, MemoryBudgetExceeded, SamplingError)


def main(argv=None) -> int:
    """
    Everything this needs is in `src/params_schema.py`.

    NO ARGUMENTS, AND NOT BY OVERSIGHT. This project is run by pressing Run on
    the numbered stages; a switch that only exists on a command line is a
    switch the person running this never sees. `run.data_folder` says which
    case and the case's own export says which scenarios, so there is nothing
    left to be told.
    """
    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    # A RUN THAT NAMES SEVERAL CASES CHECKS ALL OF THEM, the same way a case
    # set up as scenarios is checked as all of them. See upstream.cases_to_run.
    asked_for = params.run.scenario
    cases = cases_to_run(params)
    if len(cases) > 1:
        print(f'Cases     : '
              f'{", ".join(os.path.basename(c) for c in cases)}\n')

    worst = 0
    for case_position, folder in enumerate(cases):
        # PUT THE SCENARIO SETTING BACK FIRST. The loop below writes the
        # current scenario into it, so after the first case it no longer holds
        # what was configured -- it holds the last scenario that ran, and
        # `scenarios_to_run` reads a non-blank setting as "only this one".
        # Left out, a blank setting ran all four grades for the first case and
        # then silently ran only the last of them for every case after it.
        params.run.scenario = asked_for
        # Downstream reads run.data_folder, so point it at the current case --
        # the same move the scenario loop already makes below.
        params.run.data_folder = folder
        if len(cases) > 1:
            print(f'\n########## case {os.path.basename(folder)} '
                  f'({case_position + 1} of {len(cases)}) ##########')

        scenarios = scenarios_to_run(params, folder)
        if len(scenarios) > 1:
            print(f'Scenarios : {", ".join(scenarios)}\n')

        for position, scenario in enumerate(scenarios):
            params.run.scenario = scenario
            if len(scenarios) > 1:
                print(f'\n=== scenario {scenario}  ({position + 1} of '
                      f'{len(scenarios)}) ===')
            try:
                # Check the tables before totalling them. Without this a
                # freshly generated skeleton -- rows present, values blank --
                # reaches the arithmetic and comes back as a TypeError from
                # inside pandas, naming neither the file nor the row.
                tables = refresh(params, folder)
                validate(folder, tables)
                if not report(folder, tables):
                    worst = 1
            except CLEAR as error:
                print(error, file=sys.stderr)
                worst = 1
    return worst


if __name__ == '__main__':
    raise SystemExit(main())
