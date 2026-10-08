"""
02_run_model.py
===============

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

STEP 1 -- solve the model and draw its figures.

    ./.venv/bin/python stages/02_run_model.py

This is the one you run. It reads the settings in `src/params_schema.py`,
solves the case named there, writes the answer next to the input data, and
draws the figures.


The answer goes to <case folder>/output_data/. The figures go to figures/.

To change which case runs every time, or which figures are drawn, edit
`src/params_schema.py` -- not this file.
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


from src.model_run import solve_and_draw
from src.monte_carlo import MemoryBudgetExceeded
from src.params_schema import ParameterError, current
from src.case_tables import VariantError
from src.sampling import SamplingError
from src.upstream import UpstreamError, cases_to_run, scenarios_to_run
from src.validate_inputs import InputDataError

# These four already say what is wrong and which file or setting to change.
# This is run by pressing Run in an editor, so a traceback on top of that text
# is noise in front of the answer, not a detail.
CLEAR = (InputDataError, UpstreamError, MemoryBudgetExceeded, SamplingError,
         VariantError)


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

    # A RUN THAT NAMES SEVERAL CASES SOLVES ALL OF THEM, the same way a case
    # set up as scenarios is solved as all of them. See upstream.cases_to_run.
    asked_for = params.run.scenario
    cases = cases_to_run(params)
    for folder in cases:
        if not os.path.isdir(folder):
            print(f"There is no case folder called '{folder}'.\n"
                  f"Correct run.data_folder in src/params_schema.py.",
                  file=sys.stderr)
            return 1
    if len(cases) > 1:
        print(f'Cases     : {", ".join(os.path.basename(c) for c in cases)}')

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
            print(f'Scenarios : {", ".join(scenarios)}')

        for position, scenario in enumerate(scenarios):
            params.run.scenario = scenario
            if len(scenarios) > 1:
                print(f'\n=== scenario {scenario}  ({position + 1} of '
                      f'{len(scenarios)}) ===')
            try:
                solve_and_draw(folder, params, show_table=True)
            except CLEAR as error:
                print(error, file=sys.stderr)
                print(f'{scenario} failed; {len(scenarios) - position - 1} '
                      f'scenario(s) not attempted.', file=sys.stderr)
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
