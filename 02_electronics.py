"""
02_electronics.py -- the electronics recycling study.

    Press Run. No arguments, nothing to edit.

Two cases: the wiring and motors, resolved as materials, and the boards
and sensors, resolved as elements. Neither has a scenario dimension, so
one pass each.

It runs every stage in order and stops at the first that fails. The stages
themselves live in `stages/`; they are not what you press any more.

What this study covers -- the case folders, the scenarios, the resources its
figures draw -- is `STUDIES['electronics']` in `src/params_schema.py`, written in
one place so that a run cannot be started with another study's settings still
in force.

⚠️ THE NUMBER IS THE UPSTREAM STAGE THAT FEEDS THIS, not a step in a sequence
here. `04_02` in RAWCLICStockAndFlow exports what this reads. The three
studies are alternatives -- you press one of them, not all three in order.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.bootstrap import ensure_venv

ensure_venv()

from src.study import run_study

if __name__ == '__main__':
    raise SystemExit(run_study('electronics'))
