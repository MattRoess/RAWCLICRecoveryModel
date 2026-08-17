"""
src/params_schema.py
====================

**This is the file you edit to change a setting.**

Every value the model uses is written below, with a plain-language comment
above it saying what it does and whether it is safe to change. Change a value,
save the file, and the next run uses it.

Then run:

    ./.venv/bin/python 00_parameters.py

which rewrites `params.xlsx` and `documentation/PARAMETER_REFERENCE.md` so that
the written record matches what is actually set. Both of those are reports:
editing them changes nothing, because nothing reads them.

Same arrangement as the stock-flow model -- parameters in code, Excel generated.

WHY THIS IS A MODULE AND NOT PART OF 00_parameters.py
-----------------------------------------------------
A file that is run directly is module `__main__`, so a class defined in it is
recorded as `__main__.Params` and cannot be resolved from any other script.
Defining these here, in a module that is only ever imported, keeps them
addressable as `src.params_schema.Params` from every stage.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields

FORMATS = ('svg', 'png', 'pdf')
THEMES = ('light', 'dark')
ENGINES = ('optimized', 'LA')


class ParameterError(ValueError):
    """Raised when the values below do not make sense together."""


# ======================================================================
#  THE SETTINGS.  Everything you would want to change is in this block.
#  Edit the value to the right of the '=' sign. Nothing else.
# ======================================================================

@dataclass
class RunParams:
    """What gets solved, and with which engine."""

    # WHICH CASE THE MODEL RUNS.
    # A folder holding an `input_data/` with the three CSV files: inputs.csv,
    # composition.csv and TCs.csv. The path is written from the project root.
    # SAFE TO CHANGE: yes -- this is the setting that changes on most runs.
    # To see which folders qualify, run:  ./.venv/bin/python 01_run_model.py --list
    data_folder: str = 'data_folder/template'

    # WHICH OF THE TWO ENGINES SOLVES THE SYSTEM: 'optimized' or 'LA'.
    # SAFE TO CHANGE: yes, but read this first. The two engines disagree beyond
    # the basic_test case -- seven documented differences, several of which
    # change results silently (documentation/DEFECTS.md section 2). 'optimized'
    # is the default because it is what this project has always run, NOT
    # because it is the more correct of the two.
    engine: str = 'optimized'

    # DRAW THE SANKEY FIGURES AS PART OF A RUN.
    # These show how much mass goes where, in total and per element.
    # SAFE TO CHANGE: yes. Set to False to solve without drawing anything.
    draw_flows: bool = True

    # ALSO DRAW THE STRUCTURE DIAGRAM ON EVERY RUN.
    # This shows how the flows connect and the transfer coefficients behind
    # each arrow. Off by default because the structure only changes when the TC
    # table changes, while the Sankeys change with every result.
    # SAFE TO CHANGE: yes.
    draw_structure: bool = False


@dataclass
class FigureParams:
    """How the figures are written. Applies to both kinds of figure."""

    # WRITE PNG FILES.  On.
    # The picture format -- use it for slides, email, and anything that will
    # not accept a vector file.
    # SAFE TO CHANGE: yes.
    png: bool = True

    # WRITE SVG FILES.  Off -- set to True to also get them.
    # A vector format: it stays sharp at any size, and can be opened and edited
    # afterwards in Illustrator or Inkscape. Also the format for web pages.
    # SAFE TO CHANGE: yes.
    svg: bool = False

    # WRITE PDF FILES.  Off -- set to True to also get them.
    # A vector format with the text kept as real, searchable text. This is the
    # one for reports, papers and printing.
    # SAFE TO CHANGE: yes.
    pdf: bool = False

    # WHERE THE FIGURES ARE WRITTEN, as a folder name from the project root.
    # The folder is created if it does not exist.
    # SAFE TO CHANGE: yes.
    out_dir: str = 'figures'

    # RESOLUTION OF THE PNG FILES, in dots per inch.
    # Ignored by SVG and PDF, which are vector formats and have no resolution.
    # 200 is roughly print quality at the figure's natural size; 96 gives a
    # smaller file for screen use; 300 is heavier than most documents need.
    # SAFE TO CHANGE: yes. Must be a whole number above zero.
    dpi: int = 200

    # COLOUR SCHEME: 'light' or 'dark'.
    # The figures used to follow the reader's system setting automatically. A
    # PNG or PDF cannot do that, so the choice is made when they are drawn.
    # SAFE TO CHANGE: yes.
    theme: str = 'light'

    # DRAW ONE SANKEY PER ELEMENT, in addition to the total.
    # SAFE TO CHANGE: yes. With many elements this is one file per element per
    # format, which multiplies quickly -- set to False for the total only.
    element_figures: bool = True

    def enabled(self) -> list[str]:
        """The formats switched on above, in a fixed order. Not a setting."""
        return [name for name in FORMATS if getattr(self, name)]


# ======================================================================
#  Below here is machinery. Nothing to edit.
# ======================================================================

@dataclass
class Params:
    """The whole parameter set."""

    run: RunParams = field(default_factory=RunParams)
    figures: FigureParams = field(default_factory=FigureParams)

    SECTIONS = ('run', 'figures')

    def validate(self) -> list[str]:
        """Return a list of plain-language problems. Empty means all is well."""
        issues: list[str] = []

        if self.run.engine not in ENGINES:
            issues.append(f"engine is {self.run.engine!r}, but must be one of "
                          f"{', '.join(repr(e) for e in ENGINES)}")

        if not self.figures.enabled():
            issues.append('png, svg and pdf are all False, so no figure would be '
                          'written. Set at least one of them to True.')

        if self.figures.theme not in THEMES:
            issues.append(f"theme is {self.figures.theme!r}, but must be one of "
                          f"{', '.join(repr(t) for t in THEMES)}")

        if not isinstance(self.figures.dpi, int) or isinstance(self.figures.dpi, bool) \
                or self.figures.dpi <= 0:
            issues.append(f'dpi is {self.figures.dpi!r}, but must be a whole number '
                          f'above zero, such as 200')

        if not self.run.data_folder:
            issues.append('data_folder is empty -- it needs the name of a case folder')

        return issues


def current() -> Params:
    """
    The settings above, checked.

    Every stage calls this rather than building Params itself, so a mistaken
    edit is reported once and clearly at the start of a run, naming the setting
    and what it should have been.
    """
    params = Params()
    issues = params.validate()
    if issues:
        raise ParameterError(
            'There is a problem with the settings in src/params_schema.py:\n\n'
            + '\n'.join(f'  - {issue}' for issue in issues)
            + '\n\nOpen that file, correct the value, and run again.')
    return params


def describe(section_name: str, name: str) -> str:
    """The comment block written above the setting, as one line."""
    section = {'run': RunParams, 'figures': FigureParams}[section_name]
    return _FIELD_COMMENTS.get((section.__name__, name), '') or \
        f"Setting in section '{section_name}'."


def flatten(params: Params) -> list[list]:
    """[name, description, key, value] per setting, in the order written above."""
    rows: list[list] = []
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


def _collect_field_comments() -> dict[tuple[str, str], str]:
    """
    Read the comment block sitting above each setting, out of this file's own
    source.

    Comments are discarded by Python at import time, so they have to be read
    back from the source to appear in params.xlsx. Doing it this way means the
    explanation a reader sees next to the value is the same text that reaches
    the spreadsheet -- there is no second copy to fall out of date.
    """
    import ast
    import inspect

    source = inspect.getsource(__import__(__name__, fromlist=['_']))
    lines = source.splitlines()
    comments: dict[tuple[str, str], str] = {}

    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if not (isinstance(statement, ast.AnnAssign)
                    and isinstance(statement.target, ast.Name)):
                continue
            block = []
            index = statement.lineno - 2          # the line above the setting
            while index >= 0 and lines[index].strip().startswith('#'):
                block.insert(0, lines[index].strip().lstrip('#').strip())
                index -= 1
            if block:
                comments[(node.name, statement.target.id)] = ' '.join(block)
    return comments


_FIELD_COMMENTS = _collect_field_comments()
