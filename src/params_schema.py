"""
src/params_schema.py
====================

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

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
import os
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
    #    'data/bev_electronics_wiring'  04_02  the wiring and the
    #                                                motors, as MATERIALS:
    #                                                copper, alalloy, fealloy
    #    'data/bev_electronics_boards'  04_02  the boards and the
    #                                                sensors, as ELEMENTS:
    #                                                Au, Ag, Pd, Cu, Nd
    #    'data/carcomposition_mockup'   04_01  whole cars, five
    #                                                drivetrains, as MATERIALS
    #    'data/battery'                 04_04  the pack, as ELEMENTS
    #                                                within COMPONENTS
    #    'data/tractionmotor'           04_03  the fleet: motors
    #                                                removed and disassembled,
    #                                                the rest shredded in the
    #                                                hulk, split at the
    #                                                review's step 2
    #
    #  SEVERAL AT ONCE, SEPARATED BY SEMICOLONS. Naming more than one runs
    #  every one of them, in the order written, exactly as a case set up with
    #  scenarios runs all of its scenarios:
    #
    #      data_folder = 'data/bev_electronics_wiring; '
    #                    'data/bev_electronics_boards'
    #
    #  STILL ONE STUDY PER CASE. They are different networks with different
    #  coefficients and different layers, so each one is solved, written and
    #  reported on its own. Several in one run saves the four edits and four
    #  presses it used to take -- it does not combine them into one answer.
    #
    #  THIS IS THE ONLY PLACE THAT SAYS WHICH. Every stage falls back to it,
    #  and the folder argument the numbered scripts take is an override for a
    #  one-off run, not a second place to keep the answer. Leaving it pointing
    #  at a case that is not the one being worked on is how a run of the boards
    #  gets mistaken for a run of the battery -- pressing Run passes no
    #  argument, so the setting is what decides.
    #
    #  Nothing else changes when you switch: each case carries its own data
    #  and its own coefficients in its own folder.
    # ******************************************************************
    # One folder holding an `input_data/`, written from the project root, or
    # several separated by semicolons.
    # SAFE TO CHANGE: yes -- this is the setting that changes on most runs.
    data_folder: str = 'data/tractionmotor'

    # WHICH SCENARIO TO RUN.  Blank runs every scenario the case declares.
    #
    # LEFT BLANK ON PURPOSE. A scenario is a property of the CASE, not of the
    # settings: the reference cases carry no Scenario column at all, so naming
    # one here makes `chosen_scenario` refuse them -- 26 tests, tried. Blank
    # lets each case answer for itself, which is why `run.data_folder` alone
    # does not decide a run.
    #
    # BLANK MEANS ALL OF THEM, one pass each, in the order the case lists them:
    # the battery as S1, S2 and S3, the traction motor cases as EH, SH, UH and
    # mix. Naming one here narrows the run to that one.
    # See `src/upstream.scenarios_to_run`.
    #
    # 2026-09-25, CORRECTED. This used to say the battery was run with
    # `--scenario S1` on the command line, and that a blank setting stopped the
    # run and listed what it found rather than guessing. Neither is true any
    # more: the numbered stages take no arguments at all, and blank has meant
    # "all of them" since `scenarios_to_run` arrived.
    #
    # ONE PASS IS STILL ONE SCENARIO, across all its years. Scenarios are
    # independent here -- this model is pure flow-through, with no stock carried
    # between runs -- and solving several in one pass would cost: the memory
    # budget is already the binding constraint (DESIGN_monte_carlo.md
    # section 2). All of them from one press is a LOOP over passes, not one
    # larger solve.
    #
    # THE CASE LOOP PUTS THIS BACK between cases. The scenario loop writes the
    # current scenario into this field, so a run naming several cases restores
    # whatever is set here before each one. Without that, every case after the
    # first inherited the last scenario that ran and silently did only that one.
    #
    # Comparing scenarios is ANALYSIS, done afterwards on the output files. The
    # model produces each scenario's numbers and stops there.
    # SAFE TO CHANGE: yes -- it must name a scenario the case's own data has.
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
    #
    # 2026-09-17: STEP 5, NOT 1, AND THE BATTERY IS WHY. Its upstream export
    # (`battery_recovery_draws`) holds 11 years, 2020-2070 step 5, while the
    # electronics export holds all 51. `05_combine_cases.py` refuses cases
    # whose spans differ -- they are added year by year -- so every case that
    # is combined has to run on the grid the battery has. Step 1 is still
    # correct for a case run on its own; it cannot be combined with the
    # battery until upstream exports the battery at every year.
    years: str = '2020-2070, 5'

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

        data/<case>/input_data/source.csv

    Running the other one is then naming it, with nothing here touched:

        ./.venv/bin/python stages/02_run_model.py data/carcomposition_mockup
        ./.venv/bin/python stages/03_run_monte_carlo.py data/bev_electronics_wiring

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
    # It holds what the upstream file names do NOT resolve into a material. A
    # file named <element>__<material>__<group> puts its material at Layer 3 in
    # its own right; where there is no such file the element's material is
    # unknown, and the placeholder is where it sits. An export with none of them
    # gives one placeholder per group holding the whole of it, which is what
    # every case read before 2026-08-31. See CASES.md, `child_layer`.
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
    # something else open; 8 suits the 32 GB machine this is developed on, and
    # is what the boards case needs -- 1,661 rows x 200,000 draws is 2.7 GB of
    # result and about 4.5 GB in all, which 4 refused.
    # SAFE TO CHANGE: yes. A number above zero.
    memory_budget_gb: float = 8.0

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

    # WHICH RESOURCES THE FIGURES COVER.  Empty means every one the case
    # resolves. Name a few to focus: ('copper',) draws only copper on
    # fate.png, account_<r>.png, fleet_<r>.png and the per-resource
    # densities.
    #
    # It narrows what is DRAWN and never what is solved. Every resource stays
    # in recovery_results.xlsx and monte_carlo_summary.csv whatever this says,
    # so nothing is lost by focusing -- which is the point: the boards case
    # resolves twenty-odd elements and a reader usually wants two.
    # SAFE TO CHANGE: yes. A name that no case has is ignored rather than
    # silently producing an empty figure.
    #
    # 2026-09-17: nickel, cobalt and lithium joined copper when the battery
    # case arrived. Both spellings of copper are listed because the cases do
    # not agree on it -- wiring resolves MATERIALS and calls it `copper`,
    # boards and the battery resolve ELEMENTS and call it `Cu`. The other
    # three are elements everywhere, so one spelling each.
    #
    # 2026-09-25: the rare earths and the other motor materials joined it. Until
    # the mixed-depth fix this list matched nothing in the traction motor case
    # -- it resolves copper at the MATERIAL layer and the figures only looked at
    # the element layer -- so `chosen` fell back to "everything it can see",
    # which was the four rare earths and nothing else. With the fix 'copper'
    # matches, and a list of five would have narrowed the figures to copper
    # alone and dropped the rare earths. Both belong in this study, so both are
    # named.
    resources: tuple[str, ...] = ('copper', 'Cu', 'Ni', 'Co', 'Li',
                                  'Nd', 'Pr', 'Dy', 'Tb',
                                  'aluminium', 'steel', 'lamination')

    def enabled(self) -> list[str]:
        """The formats switched on above, in a fixed order. Not a setting."""
        return [name for name in FORMATS if getattr(self, name)]


@dataclass
class CombineParams:
    """
    Several cases added together, for 05_combine_cases.py.

    ONE METAL ACROSS SEVERAL STREAMS. Each case stays its own case -- separate
    folder, separate coefficients, separate run, and nothing here merges them
    (DECISIONS 20). This is reporting: the copper the wiring case recovers plus
    the copper the boards case recovers is the copper the electronics recover,
    added the way DECISIONS 11 adds the two roads.

    Adding is done PER DRAW, not by adding percentiles. Every case reads the
    same upstream draws with the same seed, so draw i is one world across all
    of them, and the interval of the sum is the interval of a sum rather than
    the sum of two intervals -- which would be wider than any world.
    """

    # WHICH CASES ARE ADDED. Any number; battery packs and drivetrains join by
    # being listed here once they have a case folder of their own.
    # SAFE TO CHANGE: yes. A folder that does not exist is named and refused.
    cases: tuple[str, ...] = ('data/bev_electronics_wiring',
                              'data/bev_electronics_boards',
                              'data/battery',
                              'data/tractionmotor')

    # ******************************************************************
    #  WHICH METALS ARE DRAWN.  Every one of them, every time 04 is run:
    #  four metals x three scenarios is twelve sets of figures from one
    #  press of Run. Add a metal by adding a line.
    #
    #      'how a reader says it': ('every spelling the data uses',)
    #
    #  THE SPELLINGS ARE A LIST BECAUSE THE CASES DISAGREE. Wiring resolves
    #  MATERIALS and calls it `copper`; boards and the battery resolve
    #  ELEMENTS and call it `Cu`. They are the same metal and this is the
    #  only place that says so -- every spelling is looked for in every
    #  case, and whichever one that case has is the one used. Nickel,
    #  cobalt and lithium are elements everywhere, so one spelling each.
    #
    #  The label is what the figures are titled and named with, so
    #  `nickel` gives nickel_combined.png and the rest of its set.
    #
    #  SAFE TO CHANGE: yes. A case with none of a metal's spellings is
    #  reported as contributing nothing rather than silently counting zero.
    # ******************************************************************
    #
    #  THE RARE EARTHS JOINED ON 2026-09-29, when the traction motor case
    #  did. They were left out while there were FOUR traction cases, because
    #  those were competing routes for the same motors and adding them would
    #  have counted one fleet four times. There is one traction case now --
    #  both roads inside it, split at the review's step 2 -- so it adds like
    #  any other part of the car.
    #
    #  Nd and Dy are in the BOARDS case too, as sensor and actuator magnets.
    #  That is not a double count: a sensor magnet and a traction magnet are
    #  different components of the same vehicle, which is the same reason
    #  wiring copper and board copper are added.
    resources: dict[str, tuple[str, ...]] = field(default_factory=lambda: {
        'copper':       ('copper', 'Cu'),
        'nickel':       ('Ni',),
        'cobalt':       ('Co',),
        'lithium':      ('Li',),
        'neodymium':    ('Nd',),
        'praseodymium': ('Pr',),
        'dysprosium':   ('Dy',),
        'terbium':      ('Tb',),
    })

    # What the combined streams are called together, for the title.
    # Updated 2026-09-17 when the battery joined `cases`: the figures were
    # still titled 'BEV electronics' while drawing the battery's components
    # alongside them.
    # SAFE TO CHANGE: yes.
    whole: str = 'BEV electronics, battery and traction motor'

    # WHERE THE COMBINED FIGURE GOES. Not any one case's folder: it belongs to
    # none of them.
    # SAFE TO CHANGE: yes.
    out_dir: str = 'figures/combined'


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
    combine: CombineParams = field(default_factory=CombineParams)

    SECTIONS = ('run', 'data', 'monte_carlo', 'figures', 'combine')

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

        # SEVERAL FOLDERS SEPARATED BY SEMICOLONS IS ONE VALID VALUE. Split
        # it the same way `src/upstream.cases_to_run` does, and say which of
        # them is wrong rather than quoting the whole line back.
        folders = [part.strip() for part in self.run.data_folder.split(';')
                   if part.strip()]
        if not folders:
            issues.append('data is empty -- it needs the name of a case folder')

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


# ----------------------------------------------------------------------
#  Studies: three recycling questions, each run by pressing Run on its own file
# ----------------------------------------------------------------------
#
# ⚠️ THE SETTINGS ABOVE ARE THE DEFAULT, NOT THE ONLY ANSWER. Three studies run
# through this model -- electronics, traction motors, batteries -- and each
# wants a different `data_folder` and a different set of resources on its
# figures. Switching between them meant editing this file, every time, which is
# four edits to answer one question and the wrong edit to make in a hurry.
#
# A study is now named, once, here, and chosen by pressing Run on its wrapper:
#
#     02_electronics.py      -> STUDIES['electronics']
#     03_tractionmotors.py   -> STUDIES['tractionmotors']
#     04_batteries.py        -> STUDIES['batteries']
#
# The wrapper sets `RECOVERY_STUDY` and runs 01, 02 and 03. `current()` reads
# it, so EVERY stage honours it however it imported `current` -- which matters,
# because they import the name directly and patching this module would not
# reach them.
#
# This does not reintroduce a command-line switch (02_run_model.main says why
# there is none). A switch nobody sees is the problem; a file you press Run on
# is as visible as the setting it replaces, and it says in one place what the
# whole study is.
#
# The numbering follows the UPSTREAM stage that feeds each study: 04_02 exports
# the electronics, 04_03 the traction motors, 04_04 the batteries.
STUDY_VARIABLE = 'RECOVERY_STUDY'

STUDIES: dict[str, dict] = {
    'electronics': {
        'run.data_folder': ('data/bev_electronics_wiring; '
                            'data/bev_electronics_boards'),
        'run.scenario': '',
        'figures.resources': ('copper', 'alalloy', 'fealloy',
                              'Ag', 'Au', 'Pd', 'Cu', 'Ni'),
    },
    'tractionmotors': {
        # ⚠️ ONE CASE, ONE ANSWER. `data/tractionmotor` runs BOTH
        # roads at once: motors that are removed are disassembled, motors that
        # are not stay in the hulk and are shredded with it. There used to be
        # four cases, each sending 100% of the motors one way, which meant four
        # of every figure and no single answer to read.
        #
        # THE MIXTURE IS NOT A DIAL. The split is the review's own step 2,
        # "Motor removal from vehicle", 0.85 | 0.93 | 0.98 at 2030. Nobody
        # chose it. An earlier version had an invented share above a chain that
        # already applied step 2, which counted removal twice.
        #
        # The pure routes are still reachable: pin `removal` in
        # `tools/build_tractionmotor_case.py` to (1,1,1) for disassembly only
        # or (0,0,0) for shredder only, and rebuild.
        'run.data_folder': 'data/tractionmotor',
        # ⚠️ NO SCENARIO, AND SO NO SCENARIO FOLDER. This used to say `mix`,
        # which put every output one level deeper -- `figures/tractionmotor/
        # mix/`, `output_data/mix/` -- a folder with exactly one thing in it
        # that had to be opened before anything could be read. Said on
        # 2026-09-29: *"why is there a folder tractionmotor/mix. NO MIX."*
        #
        # THE GRADE IS STILL `mix`. The case's own source table carries
        # `scenario_alias = *=mix`, so whatever scenario name is asked for, the
        # draws read are `traction_recovery_draws/mix` -- the magnet grade
        # drawn per draw, which is what a fleet is. Blank here means the case
        # has no scenario DIMENSION, one pass, output at the top of its folder.
        # That is exactly how the electronics cases work, with `*=BAU`.
        #
        # Running all four grades would be four times the folders and four
        # times the figures for one narrow question, and Nd and Pr are
        # BYTE-IDENTICAL across SH, UH and EH -- the workbook's didymium range
        # applies to all three -- so only Dy and Tb differ at all. To ask the
        # pinned-grade question (what if only EH is feasible, because of
        # China), change the alias in `tools/build_tractionmotor_case.py` to
        # `*=EH` and rebuild.
        'run.scenario': '',
        # ⚠️ THE MAGNET, ITS ELEMENTS, AND COPPER. Those are what this study is
        # about, said more than once and finally written down as DECISIONS 29.
        # Naming all nine resources here weighted aluminium, steel and
        # lamination the same as neodymium, which is not the question: the
        # bulk metals come back either way, and what the route decides is the
        # magnet and the copper.
        #
        # The bulk metals are NOT gone. `spread`, `spread_last_year`,
        # `mode_vs_mean` and the whole-case Sankey read every resource whatever
        # this says, so they still carry all nine -- which is the handful of
        # figures about the rest that was asked for.
        'figures.resources': ('magnet', 'Nd', 'Pr', 'Dy', 'Tb', 'copper'),
    },
    'batteries': {
        'run.data_folder': 'data/battery',
        'run.scenario': '',          # blank: S1, S2 and S3
        'figures.resources': ('Cu', 'Ni', 'Co', 'Li'),
    },
}


class StudyError(ValueError):
    """Raised when a study is named that this file does not define."""


def apply_study(params: Params, name: str) -> Params:
    """
    Put one study's settings onto `params`. Named so it can be tested.

    Every key must already exist. A study that sets a name nothing reads is a
    study that silently does not take effect, which is the failure this whole
    mechanism exists to remove.
    """
    if name not in STUDIES:
        raise StudyError(
            f'{name!r} is not a study. This file defines '
            f'{", ".join(sorted(STUDIES))}.')
    for key, value in STUDIES[name].items():
        section_name, _, field_name = key.partition('.')
        section = getattr(params, section_name, None)
        if section is None or not hasattr(section, field_name):
            raise StudyError(
                f"study {name!r} sets {key!r}, which is not a setting. "
                f"Nothing would read it.")
        setattr(section, field_name, value)
    return params


def current() -> Params:
    """
    The settings above, checked -- with a study applied if one was named.

    Every stage calls this rather than building Params itself, so a mistaken
    edit is reported once and clearly at the start of a run, naming the setting
    and what it should have been.
    """
    params = Params()
    chosen = os.environ.get(STUDY_VARIABLE, '').strip()
    if chosen:
        params = apply_study(params, chosen)
    issues = params.validate()
    if issues:
        raise ParameterError(
            'There is a problem with the settings in src/params_schema.py:\n\n'
            + '\n'.join(f'  - {issue}' for issue in issues)
            + '\n\nOpen that file, correct the value, and run again.')
    return params


def describe(section, name: str) -> str:
    """
    The comment block written above the setting, as one line.

    TAKES THE SECTION ITSELF, not its name. It used to look the class up in a
    dict written out by hand -- run, data, monte_carlo, figures -- and adding
    `combine` to SECTIONS without adding it there made `00_parameters.py` die
    on `KeyError: 'combine'`, after the section had been declared, defaulted,
    validated and used everywhere else. The list a person has to remember to
    add to twice is the list that gets added to once.
    """
    section_type = section if isinstance(section, type) else type(section)
    return _FIELD_COMMENTS.get((section_type.__name__, name), '') or \
        f'Setting in {section_type.__name__}.'


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
                describe(section, f.name),
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
