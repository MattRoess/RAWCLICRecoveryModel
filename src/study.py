"""
src/study.py
============

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

Run one study's stages, from the file you pressed Run on.

WHY A FILE PER STUDY RATHER THAN A SETTING. Three studies go through this model
-- electronics, traction motors, batteries -- and each needs a different
`run.data_folder` and a different set of resources on its figures. Switching
meant editing `src/params_schema.py` between runs: several edits to answer one
question, the edit most easily made in a hurry, and a run started with the
previous study's settings looks exactly like a correct one.

Asked for on 2026-09-28: *"This proves not efficient."*

WHY SUBPROCESSES. The stages import `current` BY NAME
(`from src.params_schema import current`), so replacing it on the module here
would not reach them. An environment variable does, whatever they import.
`99_check_all.py` already runs the stages this way for the same reason: what
runs is the stage itself, exactly as pressing Run on it would, and not an
in-process imitation of it.

WHY THE OUTPUT IS NOT CAPTURED. Asked for in the same breath: *"I want to see
that things are moving."* A sixteen-pass study is half an hour, and a silent
half hour is indistinguishable from a hung one. The stages keep the terminal,
and this file adds only a header and a footer around each so the stream reads
as progress rather than as one long log.

WHAT IT DOES NOT DO. It does not run 04. Combining cases is a separate question
with its own settings (`combine.cases`), and a study that silently also
recombined would be doing two things under one press.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# In order, and stopping at the first failure: 02 cannot mean anything if the
# inputs were refused, and 03 cannot if the deterministic solve did not run.
#
# THE NUMBERS ARE THE ORDER AND NOTHING ELSE. They are not what anyone presses
# any more -- these live in `stages/` and the three `run_*.py` files in the
# project root are the way in.
STAGES = (
    ('stages/01_check_inputs.py', 'Checking the inputs', ()),
    ('stages/02_run_model.py', 'The deterministic answer, and the diagrams', ()),
    ('stages/03_run_monte_carlo.py',
     'The Monte Carlo, the workbook and the figures', ()),
)

RULE = '=' * 72


def _clock(seconds: float) -> str:
    return f'{int(seconds) // 60}m {int(seconds) % 60:02d}s'


def run_study(name: str, stages=STAGES) -> int:
    """Run the stages for one study. Returns an exit code, 0 for success."""
    from src.params_schema import STUDY_VARIABLE, STUDIES, StudyError, current

    if name not in STUDIES:
        print(f'{name!r} is not a study. src/params_schema.py defines '
              f'{", ".join(sorted(STUDIES))}.', file=sys.stderr)
        return 1

    os.environ[STUDY_VARIABLE] = name
    try:
        params = current()
    except StudyError as error:
        print(error, file=sys.stderr)
        return 1
    environment = dict(os.environ)

    # Read back through `current()`, so the header states what the stages will
    # actually see rather than what this file believes it set.
    cases = [c.strip() for c in params.run.data_folder.split(';') if c.strip()]
    scenario = params.run.scenario or 'every one the case exports'

    print(RULE)
    print(f'STUDY  {name}')
    print(RULE)
    for case in cases:
        print(f'  case       {case}')
    print(f'  scenarios  {scenario}')
    print(f'  resources  {", ".join(params.figures.resources)}')
    print(f'  stages     {len(stages)}, in order, stopping at the first failure')
    print(RULE)

    began = time.time()
    for number, (script, title, args) in enumerate(stages, start=1):
        print(f'\n{RULE}\n[{number}/{len(stages)}]  {title}\n{RULE}', flush=True)
        started = time.time()
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, *script.split('/')), *args],
            cwd=ROOT, env=environment)
        took = _clock(time.time() - started)
        if result.returncode != 0:
            print(f'\n{RULE}')
            print(f'[{number}/{len(stages)}]  {title} FAILED after {took}.')
            print(f'  Nothing after it was run: it could not have meant '
                  f'anything.\n  The stage is {script}.')
            print(RULE, file=sys.stderr)
            return result.returncode
        print(f'\n[{number}/{len(stages)}]  done in {took}')

    print(f'\n{RULE}')
    print(f'STUDY  {name}  --  all {len(stages)} stages, {_clock(time.time() - began)}')
    print(RULE)
    return 0
