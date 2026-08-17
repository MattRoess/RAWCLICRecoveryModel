"""
src/params_schema.py
====================

Every parameter this project has, in one typed place.

WHY THIS LIVES HERE AND NOT IN 00_parameters.py
-----------------------------------------------
Same reason as the stock-flow model: a file that is run directly is module
`__main__`, so any class defined in it is recorded as `__main__.Params` and
cannot be resolved from a different script. Defining the schema in a module
that is only ever imported keeps the classes addressable as
`src.params_schema.Params` from everywhere.

HOW IT DIFFERS FROM THE STOCK-FLOW MODEL
----------------------------------------
There, `params.xlsx` is written but never read: the dataclass defaults are the
only real source of truth, so changing a setting means editing Python. Here the
spreadsheet is **read back** -- `load()` applies every row over the defaults
below -- so the file is the control surface and the code does not have to be
touched to change a case, a format or a resolution.

The defaults in this file are therefore the fallback, not the setting. If
`params.xlsx` is missing the model still runs on these.

Access is by attribute -- `params.run.data_folder`, `params.figures.formats` --
and by dotted key when coming from the spreadsheet: `run.data_folder`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

FORMATS = ('svg', 'png', 'pdf')
THEMES = ('light', 'dark')
ENGINES = ('optimized', 'LA')


@dataclass
class RunParams:
    """What to solve, and with which engine."""

    data_folder: str = 'data_folder/template'
    """
    The case to run. A folder holding an `input_data/` with the three CSVs.

    SAFE TO CHANGE: yes -- this is the setting that changes on most runs.
    Anything under `data_folder/` works; the path is relative to the project
    root. `run_model.py --list` prints the folders that qualify.
    """

    engine: str = 'optimized'
    """
    Which of the two engines solves the system: 'optimized' or 'LA'.

    SAFE TO CHANGE: yes, but know that the two disagree beyond `basic_test` --
    seven documented divergences, some of which silently change results. See
    documentation/DEFECTS.md §2. 'optimized' is the default because it is what
    the project has always run; it is not the more correct of the two.
    """

    draw_flows: bool = True
    """Draw the Sankey figures as part of a run. SAFE TO CHANGE: yes."""

    draw_structure: bool = False
    """
    Also draw the structure diagram on every run.

    Off by default because the structure changes only when the TC table does,
    while the Sankeys change with every result. SAFE TO CHANGE: yes.
    """


@dataclass
class FigureParams:
    """How every figure is rendered. Applies to both plot scripts."""

    formats: list[str] = field(default_factory=lambda: ['png'])
    """
    Which file formats to write, from 'svg', 'png' and 'pdf'.

    PNG only by default. SVG and PDF are off unless this list asks for them --
    add them here and nothing else changes, because one drawing produces every
    format and they cannot disagree.

    Written as a JSON list in the spreadsheet. To turn all three on:
    ["svg", "png", "pdf"]. A plain comma-separated list is also accepted, so
    svg, png, pdf typed straight into the cell works too.

    SAFE TO CHANGE: yes. PNG for anything that will not take a vector, SVG for
    the web and for editing, PDF for documents and printing.
    """

    out_dir: str = 'figures'
    """Where figures are written, relative to the project root. SAFE TO CHANGE: yes."""

    dpi: int = 200
    """
    Raster resolution for PNG, in dots per inch. Ignored by SVG and PDF, which
    are vector formats and have no resolution.

    200 is roughly print quality at the figure's natural size. 96 gives a
    smaller file for screen use; 300 is heavier than most documents need.

    SAFE TO CHANGE: yes. Must be above zero.
    """

    theme: str = 'light'
    """
    Colour scheme baked into the output: 'light' or 'dark'.

    The figures used to carry a `prefers-color-scheme` rule and switch by
    themselves. A PNG or PDF cannot, so the choice is made at render time.

    SAFE TO CHANGE: yes.
    """

    element_figures: bool = True
    """
    Whether plot_flows draws one Sankey per element in addition to the total.

    SAFE TO CHANGE: yes. With many elements this is one file per element per
    format, which multiplies quickly -- turn it off to get the total only.
    """


@dataclass
class Params:
    """The whole parameter set. One instance is built by 00_parameters.py."""

    run: RunParams = field(default_factory=RunParams)
    figures: FigureParams = field(default_factory=FigureParams)

    # -- sections, in the order they appear in the spreadsheet
    SECTIONS = ('run', 'figures')

    def validate(self) -> list[str]:
        """Return a list of human-readable problems. Empty means valid."""
        issues: list[str] = []

        if self.run.engine not in ENGINES:
            issues.append(f"run.engine is {self.run.engine!r}, expected one of {', '.join(ENGINES)}")

        if not self.figures.formats:
            issues.append('figures.formats is empty -- no figure would be written')
        unknown = [f for f in self.figures.formats if f not in FORMATS]
        if unknown:
            issues.append(f"figures.formats contains {', '.join(map(repr, unknown))}; "
                          f"allowed: {', '.join(FORMATS)}")

        if self.figures.theme not in THEMES:
            issues.append(f"figures.theme is {self.figures.theme!r}, expected one of {', '.join(THEMES)}")

        if self.figures.dpi <= 0:
            issues.append(f'figures.dpi is {self.figures.dpi}, must be above zero')

        if not self.run.data_folder:
            issues.append('run.data_folder is empty')

        return issues

    # ------------------------------------------------------------------
    # Dotted-key access, which is how the spreadsheet addresses a field
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        section, _, name = key.partition('.')
        return getattr(getattr(self, section), name)

    def set(self, key: str, raw: Any) -> None:
        """
        Apply one spreadsheet cell, coercing it to the field's declared type.

        The spreadsheet has no types -- everything arrives as text or as
        whatever openpyxl inferred -- so the dataclass annotation decides how
        to read it. An unparseable cell raises rather than silently keeping
        the default, because a typo that leaves the old value in place is the
        kind of thing nobody notices.
        """
        section_name, _, name = key.partition('.')
        if section_name not in self.SECTIONS:
            raise KeyError(f'unknown parameter section {section_name!r} in key {key!r}')
        section = getattr(self, section_name)
        declared = {f.name: f.type for f in fields(section)}
        if name not in declared:
            raise KeyError(f'unknown parameter {key!r}')
        setattr(section, name, _coerce(raw, declared[name], key))


def _coerce(raw: Any, annotation: Any, key: str) -> Any:
    """Turn one spreadsheet cell into the type the dataclass declares."""
    text = str(raw).strip() if raw is not None else ''
    annotation = str(annotation)

    if annotation.startswith('list'):
        if isinstance(raw, (list, tuple)):
            return list(raw)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Tolerate a bare comma-separated list, which is what a person
            # types into a spreadsheet cell when not thinking about JSON.
            parsed = [part.strip() for part in text.split(',') if part.strip()]
        if not isinstance(parsed, list):
            raise ValueError(f'{key}: expected a list, got {text!r}')
        return [str(item).strip() for item in parsed]

    if annotation.startswith('bool'):
        if isinstance(raw, bool):
            return raw
        if text.lower() in ('true', 'yes', '1'):
            return True
        if text.lower() in ('false', 'no', '0'):
            return False
        raise ValueError(f'{key}: expected true or false, got {text!r}')

    if annotation.startswith('int'):
        try:
            return int(float(text))
        except ValueError:
            raise ValueError(f'{key}: expected a whole number, got {text!r}') from None

    if annotation.startswith('float'):
        try:
            return float(text)
        except ValueError:
            raise ValueError(f'{key}: expected a number, got {text!r}') from None

    return text


# ----------------------------------------------------------------------
# Flattening, shared by the spreadsheet writer and the reference generator
# ----------------------------------------------------------------------

def describe(section_name: str, name: str) -> str:
    """The field's own docstring, collapsed to one line for the register."""
    section = {'run': RunParams, 'figures': FigureParams}[section_name]
    doc = _FIELD_DOCS.get((section.__name__, name), '')
    return ' '.join(doc.split()) or f"Parameter in section '{section_name}'."


def flatten(params: Params) -> list[list[Any]]:
    """[name, description, key, value] per parameter, in declaration order."""
    rows: list[list[Any]] = []
    for section_name in params.SECTIONS:
        section = getattr(params, section_name)
        for f in fields(section):
            value = getattr(section, f.name)
            rows.append([
                f.name,
                describe(section_name, f.name),
                f'{section_name}.{f.name}',
                json.dumps(value) if isinstance(value, (list, tuple)) else value,
            ])
    return rows


def _collect_field_docs() -> dict[tuple[str, str], str]:
    """
    Field docstrings are not kept by Python at runtime, so they are read back
    out of this module's own source. Keeping the documentation next to the
    field beats maintaining a parallel dict of descriptions that drifts.
    """
    import ast
    import inspect

    docs: dict[tuple[str, str], str] = {}
    tree = ast.parse(inspect.getsource(__import__(__name__, fromlist=['_'])))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        previous = None
        for statement in node.body:
            if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str) and previous is not None):
                docs[(node.name, previous)] = statement.value.value
            previous = (statement.target.id if isinstance(statement, ast.AnnAssign)
                        and isinstance(statement.target, ast.Name) else None)
    return docs


_FIELD_DOCS = _collect_field_docs()


def is_section(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)
