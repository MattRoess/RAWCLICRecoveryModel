# Running the studies

## 1. The short way: press Run on your study

Three studies go through this model. Each has its own file. Press Run on it and
it does stages 01, 02 and 03 over every case and every scenario that study
covers — nothing to edit, no arguments.

| press Run on | covers | passes |
|---|---|---|
| `02_electronics.py` | wiring + motors, boards + sensors | 2 |
| `03_tractionmotors.py` | four routes × four magnet grades | 16 |
| `04_batteries.py` | five cases, one per chemistry family — LFP, LMFP, NMC_high, sodium, solid-state — each in the scenarios its chemistry has (S1–S3, sodium S2–S3, solid-state S3), for the choice in `run.variants` | 12 |

⚠️ **The number is the UPSTREAM stage that feeds it, not a step in a sequence
here.** `04_02` in RAWCLICStockAndFlow exports the electronics, `04_03` the
traction motors, `04_04` the batteries. The three are alternatives: you press
one of them, never all three in order.

Each one runs the whole pipeline itself and stops at the first stage that
fails. The stages live in `stages/` now and are not what you press:

```
stages/01_check_inputs.py      the inputs, and what the constraint does to them
stages/02_run_model.py         the deterministic answer, the Sankeys, the network
stages/03_run_monte_carlo.py   the Monte Carlo, the workbook, the figures
```

They still run on their own if you want one of them alone — the study file is
a convenience, not a gate.

What each study covers — its case folders, its scenarios, the resources on its
figures — is `STUDIES` in `src/params_schema.py`, written once. Added
2026-09-28, because switching between the three meant editing that file between
runs: several edits to answer one question, and a run started with the previous
study's settings still in force looks exactly like a correct one.

**This is not a command-line switch by another name.** `02_run_model.main` says
why the stages take no arguments — *a switch that only exists on a command line
is a switch the person running this never sees*. A file you press Run on is as
visible as the setting it replaces, and it states the whole study in one place
instead of three settings you have to remember to change together.

## 1b. The long way: one case at a time

`run.data_folder` still decides, when no study is named. It reads one folder or
several separated by semicolons:

```python
data_folder: str = 'data/bev_electronics_wiring'
data_folder: str = 'data/bev_electronics_wiring; data/bev_electronics_boards'
```

**Each pass is still one case.** They are different studies — different
networks, different coefficients, different layers — and a result is reported
for one of them, never for both added together. Naming several runs each of
them in turn; it does not solve them as one.

## 1c. Which set of coefficients: `run.variants`

Added 2026-10-08. A case can hold several versions of some of its coefficients, and
**one setting picks them**, in `src/params_schema.py`:

```python
variants: str = 'tc_set=own; sodium_route=mechanical'
```

| name | choices | where it applies |
|---|---|---|
| `tc_set` | `own` (your numbers; the paper's REC where you have none), `BAU`, `REC` | the five battery cases |
| `sodium_route` | `mechanical` (the paper's), `mechanical_direct` (a placeholder share goes direct) | the sodium case |

To run another set, change the setting and press Run again. **Each choice has its own
output folder** after the scenario — `figures/battery_lfp/S1/own/`,
`figures/battery_sodium/S2/own_mechanical/`, and the same under `output_data/` — so a REC
run does not replace an `own` run. Cases that offer no choice (the electronics, the
traction motor) ignore the setting and have no such folder. A choice a case does not
offer, or a case that offers one the setting leaves out, is refused with a message.

**The battery cases need the upstream export written per chemistry**
(`data/processed/battery_recovery_draws_by_chemistry/`, one folder per chemistry). Until
RAWCLICStockAndFlow's `04_04_batteries.py` has been run since it changed, stage 01 stops
and says the export does not exist. What it does, the three sets and every number's
source: `BATTERY_ROUTES.md`.

## 2. Open each file in Positron and press Run, in order

No terminal, no arguments. Each one reads `run.data_folder` and does its part.

| step | file | what it does | writes |
|---|---|---|---|
| 0 | `00_parameters.py` | checks the settings make sense; regenerates `params.xlsx` and `PARAMETER_REFERENCE.md` | those two files |
| 1 | `stages/01_check_inputs.py` | reports the totals, closure, coefficient coverage, and — since 2026-08-26 — a `SUM TO 1` section saying where the constraint pulls the answer away from what is written | nothing |
| 2 | `stages/02_run_model.py` | the deterministic answer, the Sankeys, the structure diagram | `output_data/solution_*.csv`, `figures/<case>/` |
| 3 | `stages/03_run_monte_carlo.py` | the Monte Carlo, the workbook, the distribution figures | `output_data/*.csv`, `recovery_results.xlsx`, `figures/<case>/` |
| 9 | `99_check_all.py` | ten checks: six test suites, then the pipeline and mass balance | nothing |

A study file runs steps 1, 2 and 3 for you, and stops at the first one that
fails, because a later stage cannot mean anything if an earlier one refused.

**Steps 0 and 1 are optional.** `02` and `03` validate the inputs themselves and
refuse a broken table, so nothing silently uses bad numbers if you skip them.

**Steps 2 and 3 do not depend on each other.** `03` runs the deterministic solve
itself. Run `02` when you want the diagrams; run `03` when you want the numbers
and the uncertainty. Either can be run alone.

**To put real coefficients into a case**, see [FILLING_IN.md](FILLING_IN.md).

One more you can press when you want it:

| file | what it does |
|---|---|
| `tools/plot_structure.py` | the structure diagram on its own, without solving anything |
| `tools/compare_sum_rules.py` | solves the case twice, conditioning and normalising, and shows which elements the choice actually moves |
| `tools/tc_worklist.py` | per sum-to-1 group, whether a second measurement would buy anything -- and flags the two ways of faking one |
| `tools/filling_sheet.py` | the coefficients still waiting for a real number, ranked by how much of the answer's spread each one accounts for |

---

## What the two pipelines are

There is **one model**. The two pipelines are two **cases**: two folders under
`data/`, each with its own data and its own coefficients.

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| folder | `data/bev_electronics_wiring` | `data/carcomposition_mockup` |
| covers | wiring and motors in BEVs | whole cars, five drivetrains |
| finest resolution | **element** — Cu, Nd, Dy | **material** — calAHSS, battery |
| years | 2030–2050 | 2040 |
| draws | 200,000 | 50,000 |
| coefficients | yours, hand-filled | **invented**, generated |

Adding a third (04_03, 04_04) means a new folder and pointing `run.data_folder`
at it. No code changes. See [CASES.md](CASES.md).

---

## Where the results are

```
data/<case>/output_data/
    recovery_results.xlsx        <-- open this one
    monte_carlo_summary.csv      every result row, every percentile
    solution_optimized_model.csv the deterministic answer

figures/<case>/
    structure.png                the flow network, each endpoint's role, and
                                 every coefficient behind every arrow
    total.png                    the Sankey, all resources
    <resource>.png               one Sankey per resource
                                 -- 02 draws these from the point solve, then
                                 03 REDRAWS them from the draws, means with
                                 each node's 95% interval (DECISIONS 27)
    over_time.png                median per resource per year, with the 95% band
    account.png                  THE WHOLE ACCOUNT, ON ONE AXIS: entering and
                                 leaving the fleet, reaching a recycler,
                                 recovered, lost inside recycling, never
                                 collected, and each road -- all in the same
                                 unit so any two can be compared by the
                                 distance between them, with the recovery rate
                                 on the right axis
    trapped.png                  what the fleet holds, gives back and loses.
                                 Per year: entering, leaving, recovered and
                                 reusable, with recovery as a share of what the
                                 fleet BUYS on the right axis. Over time: the
                                 three stocks those build -- still driving,
                                 recovered to date, lost to date. Every year the
                                 upstream arrays hold, not just the solved ones
    losses.png                   WHY it did not come back -- one wedge per
                                 reason, as mass and as a share of the outflow
    recovery_rate.png            recovered as a SHARE of what came in, per year
    fate.png                     what becomes of it once it leaves the fleet:
                                 recovered / lost in recycling / never collected
    pdf_<resource>.png           the distribution, one panel per year
    pdf_all.png                  those panels on one page, resources x years
    spread.png                   how much and how sure, with both years on the
                                 rows whose certainty changed
    spread_last_year.png         the same, last year only -- twice the width
    mode_vs_mean.png             deterministic against the MC mean, last year
    convergence.png              is the draw count enough
    sensitivity.png              which coefficient drives the answer
```

**Six of them sit in the case's folder and the rest in `detail/`** --
`over_time`, `recovery_rate`, `account`, `losses`, `total`, `pdf_all`. That is
`ESSENTIAL` in `src/figure_style.py` (DECISIONS 30). Nothing stops being drawn;
what changes is that the folder you open answers the question and the rest is
one directory further in.

**A folder per case**, with the same names in both, so the two pipelines cannot
overwrite each other and their figures compare directly.

The first three come from `stages/02_run_model.py` and the rest from
`stages/03_run_monte_carlo.py`, so a folder holding only the Monte Carlo figures means
02 has not been run since the case was last renamed or created.

**No figure that reports a MASS sums the year axis any more.**
`mode_vs_mean.png` was the last one that did, fixed on 2026-09-02;
`distribution.png` was deleted for the same thing a few hours earlier
(DEFECTS.md 3.16). It now compares one year -- the last -- and its subtitle
carries the measured drift: the largest distance any one gap travels across
every year in the run, 0.9 percentage points on the wiring case, against gaps
that reach 48%. The gap hardly moves because it is a ratio of two quantities
that both scale with the inflow. See DECISIONS.md, *Figures*.

`convergence.png` and `sensitivity.png` DO still pool the years, and say so in
their titles. Neither reports a mass: one asks whether 200,000 draws is enough,
the other which coefficient drives the variance, and both answers are properties
of the coefficients rather than of a year's tonnage. Pooling gives them more
draws to answer with. If that ever stops being true -- a case whose coefficients
vary by year -- they have to be split per year like the rest.

### The workbook, sheet by sheet

| sheet | what it is |
|---|---|
| Overview | the settings this run used, and the standing caveats |
| **Recovered** | the headline: recovered mass per resource per year, with the 95% interval |
| By flow | where the mass ended up, totalled at each flow's own depth |
| **Mass balance** | what entered against what left. **Start here.** |
| Distribution | every result row and every percentile |
| Coefficients | the TC table as used, including the `source` column |
| Composition | what the model thinks each product is made of |

---

## Changing what a run covers

**`src/params_schema.py`, under `run.*`** — facts about the run, shared by every
case:

| `run.years` | runs |
|---|---|
| `''` | every year in the data |
| `'2040'` | that one year |
| `'2030-2050'` | that range |
| `'2030-2050,10'` | every 10th year of it |

**The `source` table** (a sheet of `case.xlsx`, or `source.csv`) — facts about the case: which
upstream export, which product(s), which layer the children sit at, how many
draws. One case cannot disturb another. See [CASES.md](CASES.md).

### Memory

The Monte Carlo array is `result rows × draws × 8 bytes`, and
`monte_carlo.memory_budget_gb` (4 GB) is checked **before** allocating, so an
oversized run stops with an explanation rather than the machine swapping.
Chunking bounds the working memory but not the result, so the two levers are
`run.years` and the case's `draws`.

| case | result rows | at its draw count |
|---|---|---|
| 04_02, 2 groups, 5 years | 600 | 0.96 GB at 200,000 |
| 04_01, 5 drivetrains, 1 year | 4,117 | 0.30 GB at 50,000 |
| 04_01, 5 drivetrains, 5 years | ~20,000 | would be refused at 200,000 |

---

## The coefficient tables

Two files in `tools/`. Both write that case's coefficient table from its own
own composition, so the table covers exactly what the case contains — no row
that can never fire, no resource left without coefficients.

| file | for | writes |
|---|---|---|
| `tools/make_skeleton.py` | 04_02 electronics | every row that needs a number, **blank**, for you to fill |
| `tools/make_carcomposition_tcs.py` | 04_01 car composition | the same rows **already filled with invented numbers** |

**`make_skeleton.py` merges.** Run it again whenever the case grows: what you
filled in is kept, new resources are added blank, rows whose resource no longer
exists are dropped. Nothing you typed is ever overwritten. That is what makes it
safe to work one domain at a time.

**`make_carcomposition_tcs.py` overwrites**, deliberately: everything in it is
marked `MADE UP (Claude)` in the `source` column, so there is nothing of yours
to protect. 278 resources is not fillable by hand.

It refuses to run once that stops being true: any row whose `source` it did not
write is treated as yours, and the run stops rather than replacing it. Use
`make_skeleton.py` to add rows without losing what is filled in, or
`--overwrite` to rebuild deliberately.

---

## Upstream — when you have to touch RAWCLICStockAndFlow

Normally never. This model reads draws that are already on disk.

You go upstream only to **add a year or a scenario**:

| you want | set there | then press Run on |
|---|---|---|
| another year of electronics | `materials.bev_electronics_element_draws_years` | `code/04_02_BEVelectronics.py` |
| another year of car composition | `materials.carcomposition_draws_years` **and** a matching single-year entry in `monte_carlo.output_periods` | `code/04_01_carcomposition.py` |

**Run `code/00_parameters.py` there first.** Those stages read a saved params
artifact, not the source file, so an edit not followed by that has no effect and
the run still looks fine.

**04_01 needs single-year periods**, because its draws are cumulative over a
period while this model's axis is years:

```python
output_periods = [(1975, 2070), (2040, 2040)]
```

Keep `(1975, 2070)` — every existing figure and saved table there is keyed on it.

### One honest limitation

For a single year, real per-year vehicle-count draws exist **only for BEV**. The
other four drivetrains take their exact per-year level from `03_tracker_keyed`
and their distribution *shape* from the cumulative summary. **Their mean is
exact; their spread is a floor**, because a cumulative total averages
year-to-year variation out. The run prints which path each drivetrain took.

Removing the approximation means widening 03_02's BEV-only export to every
drivetrain — worth doing the next time 03_02 runs anyway, not worth a run of its
own.

---

## Keeping this up to date

Two documents to maintain together:

- **RUNNING.md** (this one) — what to press, in what order, and what comes out.
- **[CASES.md](CASES.md)** — how a case is configured, and why it is built that way.

Anything that changes a file's job, a location, a setting's meaning, or what a
run produces belongs in one of them in the same commit as the change. The rest
of `documentation/` is reference, indexed in [README.md](README.md).
