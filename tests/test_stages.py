"""
Every name a stage calls exists.

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

    ./.venv/bin/python tests/test_stages.py

WHY THIS EXISTS
---------------
2026-09-18: removing a command-line flag meant removing the function that
parsed it, and the cut ran from that function to the next one -- taking
`figure_recovered`, which sat between them, with it. `05_combine_cases.py`
solved all three cases and then died on a NameError at the last figure.

The suite was green the whole time. Nothing in it touches 04's figures, so 138
passing said nothing at all about the file that had just been edited. That is
the gap this closes: a stage that calls a name nothing defines is a stage that
dies part way through a run, after the expensive part.

STATIC, NOT IMPORTED. These files call `ensure_venv()` at import, which
re-execs the interpreter, and 04 draws figures. Parsing them says what is
wanted without running anything -- so this is also safe to run while a stage
is running.

WHAT IT CANNOT SEE. A name bound anywhere in the module counts as defined,
wherever it is used, so this does not check scope. It catches the thing that
actually happens: a function deleted, renamed or never written, still called.
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

import ast
import builtins
import glob
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The numbered stages, plus the tools, which are run the same way.
STAGES = sorted(glob.glob(os.path.join(ROOT, '[0-9][0-9]_*.py'))
                + glob.glob(os.path.join(ROOT, 'tools', '*.py')))

# EMPTY, AND IT SHOULD STAY EMPTY. It held `trapped` for one commit, called by
# a `figure_streams` that had been defined and never called since 29c6035;
# that function was deleted on 2026-09-18 and the exemption went with it.
# Do not add a name here to make a failure go away -- the failure is the point.
DEAD: set[str] = set()


def _bound(tree: ast.Module) -> set[str]:
    """Every name the module binds, at any depth."""
    names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                for group in (args.posonlyargs, args.args, args.kwonlyargs):
                    names.update(a.arg for a in group)
                for one in (args.vararg, args.kwarg):
                    if one:
                        names.add(one.arg)
        elif isinstance(node, ast.Lambda):
            args = node.args
            for group in (args.posonlyargs, args.args, args.kwonlyargs):
                names.update(a.arg for a in group)
            for one in (args.vararg, args.kwarg):
                if one:
                    names.add(one.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name.split('.')[0]) for a in node.names)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def _called(tree: ast.Module) -> set[str]:
    """Every plain name that is called, `f(...)` rather than `a.f(...)`."""
    return {node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def test_no_stage_calls_a_name_that_does_not_exist() -> None:
    """The check that would have caught figure_recovered the moment it went."""
    checked, faults = 0, []
    for path in STAGES:
        tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
        missing = sorted(_called(tree) - _bound(tree) - DEAD)
        checked += 1
        if missing:
            faults.append(f'{os.path.relpath(path, ROOT)}: {", ".join(missing)}')

    assert checked >= 6, f'only {checked} stages found; the glob stopped matching'
    assert not faults, (
        'these call a name nothing defines, imports or binds -- a run reaches '
        'them and dies:\n  ' + '\n  '.join(faults))


def _read(tree: ast.Module) -> set[str]:
    """Every plain name that is READ, `x` rather than `a.x`."""
    return {node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}


def test_no_module_reads_a_name_that_does_not_exist() -> None:
    """
    The same check for every name that is READ, not only the ones that are called,
    over the stages, the tools, the stage scripts and `src/`.

    2026-10-09: `tools/compare_engines.py` read `data` where its argument is
    `data_folder`, left over from a rename (7357043). Nothing was called wrong --
    `run(...)` exists -- so the check above passed for weeks while the tool died on
    its first line with a NameError, and five documents told people to run it.
    """
    paths = sorted(STAGES + glob.glob(os.path.join(ROOT, 'stages', '*.py'))
                   + glob.glob(os.path.join(ROOT, 'src', '*.py')))
    faults = []
    for path in paths:
        tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
        missing = sorted(_read(tree) - _bound(tree) - {'__file__', '__name__', '__doc__'})
        if missing:
            faults.append(f'{os.path.relpath(path, ROOT)}: {", ".join(missing)}')

    assert len(paths) >= 30, f'only {len(paths)} files found; the globs stopped matching'
    assert not faults, (
        'these read a name nothing defines, imports or binds -- the first run '
        'that reaches them dies:\n  ' + '\n  '.join(faults))


def test_the_combine_still_has_every_figure_it_draws() -> None:
    """
    Named outright, because this is the one that was lost.

    A stage may lose a function to an edit that takes a neighbouring one with
    it, and the generic check above only sees that if something still calls it.
    These four are the point of the file.
    """
    path = os.path.join(ROOT, '05_combine_cases.py')
    tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
    defined = {n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    for name in ('figure_combined', 'figure_with_the_bev', 'figure_lost',
                 'figure_recovered', 'combine_one', 'main'):
        assert name in defined, f'05_combine_cases has lost {name}'


def test_the_monte_carlo_stage_closes_its_run_even_when_it_stops() -> None:
    """
    A memory-mapped result is a file as large as the run -- 16.6 GB for the boards
    case -- and only `MonteCarloRun.close()` deletes it. A stage that calls it
    on the way out of a run that finished, and not otherwise, leaves the whole
    result behind whenever the run fails or is stopped. Two of them sat in the
    boards case's output folder from September to October 2026.

    STATIC, like the rest of this file, because the stage cannot be run here.
    The behaviour itself is `test_monte_carlo.py`'s, in
    `test_a_run_that_stops_midway_leaves_no_file_behind`.
    """
    path = os.path.join(ROOT, 'stages', '03_run_monte_carlo.py')
    tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
    run_case = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'run_case')

    solves = [node for node in ast.walk(run_case)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == 'solve_draws']
    assert solves, 'run_case no longer calls solve_draws, so this test is out of date'

    closed_in_finally = any(
        isinstance(node, ast.Try)
        and any(isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == 'close'
                for statement in node.finalbody for inner in ast.walk(statement))
        for node in ast.walk(run_case))
    assert closed_in_finally, (
        'run_case does not close the run in a `finally`: a run that fails or is '
        'stopped leaves its memory-mapped result in the case\'s output folder')


def main() -> int:
    tests = [value for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as error:
            failures += 1
            print(f'FAIL  {test.__name__}\n      {error}\n')
        except Exception:
            failures += 1
            print(f'ERROR {test.__name__}')
            traceback.print_exc()
        else:
            print(f'ok    {test.__name__}')

    print(f'\n{len(tests) - failures} of {len(tests)} passed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
