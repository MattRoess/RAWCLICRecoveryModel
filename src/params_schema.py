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

    # ******************************************************************
    #  WHICH PIPELINE RUNS.  Set it here, then press Run on the stages in
    #  order: 00, 01, 02, 03 -- or 99 to run the checks and the pipeline.
    #
    #    'data_folder/bev_electronics'        04_02  electronics in BEVs,
    #                                                resolved to ELEMENTS
    #    'data_folder/carcomposition_mockup'  04_01  whole cars, five
    #                                                drivetrains, resolved
    #                                                to MATERIALS
    #
    #  ONE AT A TIME. They are different studies -- different networks,
    #  different coefficients, different layers -- and a result is reported
    #  for one of them, never for both together.
    #
    #  Nothing else changes when you switch: each case carries its own data
    #  and its own coefficients in its own folder.
    # ******************************************************************
    # A folder holding an `input_data/`, written from the project root.
    # `02_run_model.py --list` prints the folders that qualify.
    # SAFE TO CHANGE: yes -- this is the setting that changes on most runs.
    data_folder: str = 'data_folder/bev_electronics'

    # WHICH SCENARIO TO RUN.  Blank when the data has no scenario dimension,
    # which is the case for every data folder in this repository today.
    #
    # ONE RUN IS ONE SCENARIO, across all its years. Scenarios are independent
    # here -- this model is pure flow-through, with no stock carried between
    # runs -- so nothing is gained by solving several at once, and under the
    # Monte Carlo it costs: the memory budget is already the binding constraint
    # (DESIGN_monte_carlo.md section 2). Separate runs also means five
    # scenarios on five cores, and a failure that loses one rather than all.
    #
    # Comparing scenarios is ANALYSIS, done afterwards on the output files. The
    # model produces one scenario's numbers and stops there.
    #
    # If the data holds scenarios and this is left blank, the run stops and
    # lists what it found rather than guessing.
    # SAFE TO CHANGE: yes -- it must name a scenario present in inputs.csv.
    scenario: str = ''

    # WHICH YEARS TO RUN.  Blank means every year the data holds.
    #
    #     ''               every year in inputs.csv
    #     '2030'           that one year
    #     '2030-2050'      that range, both ends included, every year in it
    #     '2030-2050,10'   that range, every 10th year: 2030, 2040, 2050
    #     ',10'            every 10th year of the whole data
    #
    # Real inflow data is annual -- the upstream arrays run 1975 to 2070 -- so
    # a step is usually what you want rather than the full trajectory. It keeps
    # the shape of the curve while cutting its size. The step counts by year
    # value, not by row, so a gap in the data does not shift everything after
    # it.
    #
    # Several years in one run is normal, unlike scenarios which are one per
    # run. Years are independent here too, but a result usually wants the
    # trajectory rather than a point.
    #
    # It matters for the Monte Carlo: 200,000 draws x 96 years is the memory
    # problem in DESIGN_monte_carlo.md section 2, and the year axis is the most
    # direct lever on it.
    # SAFE TO CHANGE: yes -- it must match at least one year present in the data.
    years: str = '2030-2050'

    # WHICH OF THE TWO ENGINES SOLVES THE SYSTEM: 'optimized' or 'LA'.
    # SAFE TO CHANGE: yes, but read this first. The two engines disagree beyond
    # the basic_test case -- seven documented differences, several of which
    # change results silently (documentation/DEFECTS.md section 2). 'optimized'
    # is the default because it is what this project has always run, NOT
    # because it is the more correct of the two.
    engine: str = 'optimized'

    # THE MASS UNIT THIS PROJECT WORKS IN.
    # Every inflow is converted into this on load, from whatever its own file
    # declares in the 'Unit' column, and every number the model writes is in it.
    #
    # This used to be a check rather than a conversion: a file in another unit
    # was reported and left alone, and converting it was a manual step. That is
    # a poor arrangement when three units are genuinely in play -- the data
    # folders here are written in Mg, the upstream pipeline delivers kt, and
    # results are wanted in kg -- because the manual step can be forgotten and
    # forgetting it is invisible. The model multiplies fractions, so a factor
    # of 1000 leaves every ratio in the output looking perfectly reasonable.
    #
    # Data files are NOT edited to match this. They keep saying what they are;
    # this says what the answer should be in.
    #
    # Worth knowing: no single unit suits both ends of this model. A year's
    # collected fleet is around 500 kt and the gold in it is a few tonnes --
    # 500,000,000 kg against 3,000 kg. Figures therefore choose their own
    # display unit per panel (src/units.py, scale_for); this setting governs
    # the arithmetic and the output files.
    # SAFE TO CHANGE: yes. Any unit in MASS_UNITS in src/units.py.
    working_unit: str = 'kg'

    # ALSO DRAW THE STRUCTURE DIAGRAM WHEN THE MODEL RUNS.
    # The structure diagram shows how the flows connect and the transfer
    # coefficients behind each arrow. It is not a picture of a result -- it
    # only changes when the TC table changes -- so it is a switch rather than
    # something that always happens.
    # The Sankey figures are not a switch: they are drawn on every run,
    # because they ARE the result and should never be out of step with it.
    # SAFE TO CHANGE: yes. Set to False to skip the structure diagram; you can
    # still draw it any time with:  ./.venv/bin/python tools/plot_structure.py
    draw_structure: bool = True


@dataclass
class DataParams:
    """
    Where the upstream Monte Carlo draws are read from.

    MOST OF THIS IS A DEFAULT, NOT THE ANSWER.
    ------------------------------------------
    There is one recovery case per upstream stage -- 04_01 car composition,
    04_02 electronics, 04_03 and 04_04 to come -- and each reads a different
    export with a different shape. So every setting below marked BY CASE is
    really the case's business, and a case states it in its own file:

        data_folder/<case>/input_data/source.csv

    Running the other one is then naming it, with nothing here touched:

        ./.venv/bin/python 02_run_model.py data_folder/carcomposition_mockup
        ./.venv/bin/python 03_run_monte_carlo.py data_folder/bev_electronics

    The values here are what a case gets if it says nothing. Keeping them is
    what lets an older case with no source.csv keep working; relying on them
    for a new one is how one stage's draws end up read with another stage's
    coefficients, which is exactly the mistake nothing else would catch.
    See src/source.py.

    `upstream_root` and `draws` are NOT by case: where the sibling repository
    is checked out, and how much of it to read, are properties of this machine
    and this run, not of the study.
    """

    # WHERE THE UPSTREAM PROJECT IS, as a path from this project's root.
    # The two repositories sit side by side, so the default works on any machine
    # that has both checked out, without hard-coding a home directory. Written
    # relative rather than absolute deliberately: the absolute path differs
    # between the two Macs this project is worked on, and did so again when the
    # folder moved into iCloud.
    # SAFE TO CHANGE: yes -- it must point at the RAWCLICStockAndFlow checkout.
    upstream_root: str = '../RAWCLICStockAndFlow'

    # BY CASE (`upstream_dir` in source.csv).
    # WHERE THE PER-CHILD INFLOW DRAWS ARE, under `upstream_root`.
    # One `.npy` per child per flow, each of shape (draws, years), in kt.
    # The scenario named in `run.scenario` is appended to this path.
    #
    # These are written by a year-sliced export step in the upstream stage --
    # built for 04_02, to be mirrored for the others. Recomputing them here
    # would mean duplicating that stage's segment splitting and draw pairing,
    # and that pipeline's own header records three separate occasions where a
    # stage reconstructed another stage's numbers and diverged silently.
    # Read the real draws; do not re-derive them.
    # SAFE TO CHANGE: yes -- but prefer saying it in the case's source.csv.
    inflow_draws_dir: str = 'data/processed/element_draws'

    # HOW MANY OF THE DRAWS TO USE.  The upstream arrays hold 200,000.
    # Lower this while developing: the memory arithmetic in
    # DESIGN_monte_carlo.md section 2 is unforgiving at full width, and a few
    # thousand draws is enough to see whether the machinery is correct. Raise it
    # for a result that will be reported.
    # Draws are taken from the front of the array, never sampled at random, so
    # that a run at 5,000 is a strict prefix of a run at 200,000 and the two can
    # be compared directly.
    # SAFE TO CHANGE: yes. A whole number above zero, at most what the arrays hold.
    draws: int = 200_000

    # BY CASE (`flow` in source.csv).
    # WHICH UPSTREAM FLOW IS THE INFLOW TO RECOVERY.
    # Upstream reports three: what entered the fleet, what left it, and what was
    # collected for recycling. Recovery starts from what was collected -- the
    # other two are the fleet's own story and are not handed to a recycler.
    # SAFE TO CHANGE: yes. One of 'collected', 'outflow', 'inflow'.
    upstream_flow: str = 'collected'

    # BY CASE (`product` in source.csv).
    # WHAT THE PRODUCT IS CALLED, at Layer 1.
    # Whatever the upstream item is: 'BEV', 'PVPanel', 'Battery'. It is the
    # parent every composition share is a share OF, and it appears in the
    # output rows, so it should read as the thing being recycled.
    # SAFE TO CHANGE: yes -- it is a label, and nothing matches on it.
    product: str = 'BEV'

    # BY CASE (`inflow_flow_id` in source.csv).
    # WHAT THE INFLOW FLOW IS CALLED.
    # The flow the upstream mass arrives in, and therefore the one the first
    # process reads from. It must match the Input_FlowID of the first row in
    # processes.csv.
    # SAFE TO CHANGE: yes, together with processes.csv.
    inflow_flow_id: str = 'F_collected'

    # BY CASE (`material_suffix` in source.csv). Used only where the upstream
    # child is an ELEMENT; a case whose children are already materials leaves
    # it blank and gets no placeholder. See `child_layer` in src/source.py.
    # WHAT THE PLACEHOLDER MATERIAL LAYER IS CALLED, appended to the group name.
    # Upstream has no material resolution -- it goes straight from a group to
    # the elements in it -- so each group gets exactly one material named after
    # it. The layer is carried for the model's sake and means nothing.
    # SAFE TO CHANGE: yes -- it is a label.
    material_suffix: str = '_mixed'

    # BY CASE (`group_marker` in source.csv).
    # HOW THE UPSTREAM FILES NAME A GROUP'S OWN MASS.
    # Files are `<child>__<parent>.npy`, and the group's own mass is written as
    # `<group_marker>__<group>.npy`. Only change it if the upstream export
    # changes its naming.
    # SAFE TO CHANGE: yes, together with the upstream export.
    group_marker: str = '__domain__'

    # BY CASE (`groups` in source.csv, semicolon-separated).
    # WHICH GROUPS TO IMPORT.  Empty means all of them.
    #
    # Narrowing this is the honest way to start: every domain kept is a set of
    # element yields somebody has to supply, and a study of wiring and motors
    # that is properly sourced is worth more than one covering everything on
    # guesses.
    #
    # The shares are recomputed over whatever is kept, so a restricted run is a
    # self-contained study of those domains rather than a full one with holes in
    # it. What it is NOT is a recovery rate for vehicle electronics as a whole --
    # the domains left out are simply not in the answer.
    # SAFE TO CHANGE: yes. Names must match upstream: Wiring, Motors, PCB, Sensors.
    groups: tuple[str, ...] = ('Wiring', 'Motors')


@dataclass
class MonteCarloParams:
    """How the Monte Carlo is run."""

    # RUN THE MONTE CARLO AT ALL.
    # On, because both cases carry value_min and value_max and the spread is
    # the point of running them. A case whose TC table has neither column has
    # nothing to sample -- every draw would return the same number -- and
    # stage 03 says so plainly rather than producing a flat histogram, so
    # leaving this on costs nothing even then.
    #
    # (This comment used to read "off by default" while the value was True.
    # Found by the documentation sweep on 2026-08-26.)
    # SAFE TO CHANGE: yes.
    enabled: bool = True

    # THE SEED.  Shifts every coefficient's stream together.
    # Draw i of a given coefficient is fixed by its identity and this seed, not
    # by a running generator, so it is the same number however the run is
    # chunked and whatever order the table is in. That is what lets two
    # scenarios be compared: the same draw index means the same underlying
    # randomness in both, so the difference between them is the scenario rather
    # than noise. Change it only for a genuinely independent repeat.
    # SAFE TO CHANGE: yes, but a different seed means results that cannot be
    # compared draw by draw with earlier ones.
    seed: int = 0

    # HOW MANY DRAWS TO HOLD IN MEMORY AT ONCE.
    # The whole result is rows x draws x 8 bytes; at full width that is larger
    # than any machine here has. Draws are therefore processed in blocks and
    # reduced as they go. Lower this if a run runs out of memory; raise it for
    # a little more speed on a small case.
    # SAFE TO CHANGE: yes. It changes nothing about the answer -- a chunked run
    # reproduces an unchunked one exactly, which test_monte_carlo.py checks.
    chunk: int = 0

    # HOW MUCH MEMORY THE RUN MAY USE, in gigabytes.
    #
    # The result is rows x draws x 8 bytes and cannot be avoided if exact
    # percentiles are wanted, so this is what decides whether a run is possible
    # at all. Everything else -- the sampled coefficients, the working values,
    # the sorting scratch -- is transient and is bounded by the chunk, which is
    # sized from this budget rather than guessed.
    #
    # A run whose result alone exceeds the budget stops BEFORE allocating
    # anything, and says which lever to pull: fewer draws, fewer years, fewer
    # domains. That is the point -- the alternative is the machine swapping for
    # ten minutes and then the process being killed with no explanation.
    #
    # Raise it if the machine has the memory. 4 GB suits a 16 GB laptop with
    # something else open.
    # SAFE TO CHANGE: yes. A number above zero.
    memory_budget_gb: float = 4.0

    # HOW A GROUP WITH NO `is_residual` ROW IS MADE TO SUM TO 1.
    #
    #     'normalise'   divide the group by its own sum. Always works, needs
    #                   nothing added to the table, and shifts every marginal
    #                   off the triangular it was drawn from.
    #     'condition'   keep every row's own measurement: draw them all, take
    #                   the widest as determined by the rest, weight each draw
    #                   by that row's own density at the value it was forced to,
    #                   and resample. This is what "sum to 1" means
    #                   probabilistically -- the product of the measured
    #                   densities, restricted to the draws that do sum to 1.
    #
    # Use 'condition' when every row carries a measured range and you want all
    # of them used. It also makes a contradiction visible: ranges that cannot
    # all be true collapse the effective sample size, which stage 03 reports,
    # instead of being silently absorbed.
    #
    # Groups that DO name a residual row are unaffected. That row has no
    # measurement of its own -- its bounds must be blank -- so there is nothing
    # to condition on, and for a two-row group the residual rule is exact.
    #
    # SAFE TO CHANGE: yes, but it changes the numbers for any group where every
    # row has a range. It is not a tuning knob; it is a modelling choice.
    #
    # 'normalise' is kept for two reasons and no others: reproducing a result
    # computed before conditioning existed, and getting a number out of a group
    # whose ranges contradict each other, which conditioning refuses. Note what
    # the second one means -- normalising a contradictory group does not
    # resolve the contradiction, it hides it.
    sum_to_one: str = 'condition'


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
    data: DataParams = field(default_factory=DataParams)
    monte_carlo: MonteCarloParams = field(default_factory=MonteCarloParams)
    figures: FigureParams = field(default_factory=FigureParams)

    SECTIONS = ('run', 'data', 'monte_carlo', 'figures')

    def validate(self) -> list[str]:
        """Return a list of plain-language problems. Empty means all is well."""
        issues: list[str] = []

        if self.run.engine not in ENGINES:
            issues.append(f"engine is {self.run.engine!r}, but must be one of "
                          f"{', '.join(repr(e) for e in ENGINES)}")

        from src.sampling import SUM_RULES
        if self.monte_carlo.sum_to_one not in SUM_RULES:
            issues.append(f"sum_to_one is {self.monte_carlo.sum_to_one!r}, but must "
                          f"be one of {', '.join(repr(r) for r in SUM_RULES)}")

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

        from src.units import AMBIGUOUS_UNITS, MASS_UNITS
        if self.run.working_unit not in MASS_UNITS:
            known = ', '.join(sorted(MASS_UNITS))
            extra = (' It names more than one quantity depending on where it is written.'
                     if self.run.working_unit in AMBIGUOUS_UNITS else '')
            issues.append(f'working_unit is {self.run.working_unit!r}, which is not a '
                          f'mass unit this project recognises.{extra} Known: {known}')

        if not isinstance(self.data.draws, int) or isinstance(self.data.draws, bool) \
                or self.data.draws <= 0:
            issues.append(f'draws is {self.data.draws!r}, but must be a whole number '
                          f'above zero, such as 200000')

        if not isinstance(self.monte_carlo.chunk, int) or self.monte_carlo.chunk < 0:
            issues.append(f'chunk is {self.monte_carlo.chunk!r}, but must be a whole '
                          f'number -- 0 to size it from the memory budget')

        if not isinstance(self.monte_carlo.memory_budget_gb, (int, float)) \
                or self.monte_carlo.memory_budget_gb <= 0:
            issues.append(f'memory_budget_gb is {self.monte_carlo.memory_budget_gb!r}, '
                          f'but must be a number above zero, such as 4.0')

        # Deliberately NOT checked here: whether the draw directories exist.
        # current() runs at the start of every stage, including the ones that
        # never touch the upstream draws, and a missing folder must not stop a
        # deterministic run. `00_parameters.py --check` reports it instead.

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
    section = {'run': RunParams, 'data': DataParams,
               'monte_carlo': MonteCarloParams,
               'figures': FigureParams}[section_name]
    return _FIELD_COMMENTS.get((section.__name__, name), '') or \
        f"Setting in section '{section_name}'."


def draws_path(params: Params) -> str:
    """
    The folder the per-element inflow draws are read from, scenario included.

    Assembled in one place so that every stage resolves it identically, and so
    that `00_parameters.py --check` reports the same path a run would open.
    """
    import os
    # 'BAU' when no scenario is set, matching src/upstream.source_dir. Two
    # spellings of the same path is how a status report ends up describing a
    # folder the model never opens.
    return os.path.normpath(os.path.join(
        params.data.upstream_root, params.data.inflow_draws_dir,
        params.run.scenario or 'BAU'))


def data_status(params: Params) -> str:
    """One plain-language line on whether the upstream draws are actually there."""
    import glob
    import os

    path = draws_path(params)
    if not os.path.isdir(path):
        return (f'{path}\n'
                f'      NOT FOUND. The Monte Carlo has nothing to read. See the comment\n'
                f'      above inflow_draws_dir in src/params_schema.py -- these arrays are\n'
                f'      written by stage 04_02 upstream, which does not persist them yet.')

    # The arrays sit one level down, under the flow: <scenario>/<flow>/*.npy.
    arrays = glob.glob(os.path.join(path, '*', '*.npy'))
    if not arrays:
        return f'{path}\n      found, but holds no .npy arrays.'

    import numpy as np
    years_path = os.path.join(path, 'years.npy')
    years = np.load(years_path).tolist() if os.path.exists(years_path) else '?'
    flows = sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))
    return (f'{path}\n      {len(arrays)} arrays, years {years}, '
            f'flows {", ".join(flows)}')


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
