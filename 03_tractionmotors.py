"""
03_tractionmotors.py -- the traction motor recycling study.

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

    Press Run. No arguments, nothing to edit.

ONE CASE, ONE ANSWER: `data/tractionmotor`, grade `mix`.

The fleet runs BOTH roads at once and splits between them at the review's own
step 2, "Motor removal from vehicle" (0.85 | 0.93 | 0.98, ref 6,7,8,9). What is
removed is disassembled; what is not stays in the hulk and is shredded. Nobody
chooses the share and there is no dial to set.

This used to be four cases -- long loop, short loop, shredder, split -- times
four magnet grades, so sixteen passes and sixteen of every figure, and no
single answer to read. They were the extremes, not the fleet. One builder
writes the one case now: `tools/build_tractionmotor_case.py`.

`mix` draws the magnet grade per draw, which is what a fleet is. `SH`, `UH`
and `EH` pin it, for the one question they answer: what if only EH is feasible.
Set `run.scenario` in `STUDIES['tractionmotors']` to ask it.

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
