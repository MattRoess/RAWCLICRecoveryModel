"""
03_tractionmotors.py -- the traction motor recycling study.

    Press Run. No arguments, nothing to edit.

Four cases -- long loop, short loop, shredder, split -- and four magnet
grades each, so sixteen passes. The grades are scenarios: `mix` draws the
grade per draw, `SH`, `UH` and `EH` pin it.

It runs every stage in order and stops at the first that fails. The stages
themselves live in `stages/`; they are not what you press any more.

What this study covers -- the case folders, the scenarios, the resources its
figures draw -- is `STUDIES['tractionmotors']` in `src/params_schema.py`, written in
one place so that a run cannot be started with another study's settings still
in force.

⚠️ THE NUMBER IS THE UPSTREAM STAGE THAT FEEDS THIS, not a step in a sequence
here. `04_03` in RAWCLICStockAndFlow exports what this reads. The three
studies are alternatives -- you press one of them, not all three in order.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv

ensure_venv()

from src.study import run_study

if __name__ == '__main__':
    raise SystemExit(run_study('tractionmotors'))
