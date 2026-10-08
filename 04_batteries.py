"""
04_batteries.py -- the battery recycling study.

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

    Press Run. No arguments, nothing to edit.

Five cases, one per chemistry family -- LFP, LMFP, NMC_high, sodium and
solid-state -- each in the scenarios its chemistry exists in: S1, S2 and S3, sodium
S2 and S3, solid-state S3. Twelve passes. No single scenario is the answer, which is
why all of them run.

WHICH COEFFICIENTS: each case holds three sets, `own`, `BAU` and `REC`, and sodium two
routes. `run.variants` in `src/params_schema.py` picks one, and every choice has its own
output folder. documentation/BATTERY_ROUTES.md says what each case does and where every
number comes from. The cases need the per-chemistry export that `04_04` upstream writes;
until it has been run, stage 01 says the export does not exist.

It runs every stage in order and stops at the first that fails. The stages
themselves live in `stages/`; they are not what you press any more.

What this study covers -- the case folders, the scenarios, the resources its
figures draw -- is `STUDIES['batteries']` in `src/params_schema.py`, written in
one place so that a run cannot be started with another study's settings still
in force.

⚠️ THE NUMBER IS THE UPSTREAM STAGE THAT FEEDS THIS, not a step in a sequence
here. `04_04` in RAWCLICStockAndFlow exports what this reads. The three
studies are alternatives -- you press one of them, not all three in order.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv

ensure_venv()

from src.study import run_study

if __name__ == '__main__':
    raise SystemExit(run_study('batteries'))
