# Running the two pipelines

## 1. Choose the pipeline, in `src/params_schema.py`

At the top of the file, `run.data_folder`:

```python
data_folder: str = 'data_folder/bev_electronics'          # 04_02, elements
# data_folder: str = 'data_folder/carcomposition_mockup'  # 04_01, materials
```

**One at a time.** They are different studies — different networks, different
coefficients, different layers — and a result is reported for one of them, never
for both together. To run the other, change this line and go through the steps
again.

## 2. Open each file in Positron and press Run, in order

No terminal, no arguments. Each one reads `run.data_folder` and does its part.

| step | file | what it does | writes |
|---|---|---|---|
| 0 | `00_parameters.py` | checks the settings make sense; regenerates `params.xlsx` and `PARAMETER_REFERENCE.md` | those two files |
| 1 | `01_check_inputs.py` | reports the totals, closure, coefficient coverage, and — since 2026-08-26 — a `SUM TO 1` section saying where the constraint pulls the answer away from what is written | nothing |
| 2 | `02_run_model.py` | the deterministic answer, the Sankeys, the structure diagram | `output_data/solution_*.csv`, `figures/<case>/` |
| 3 | `03_run_monte_carlo.py` | the Monte Carlo, the workbook, the distribution figures | `output_data/*.csv`, `recovery_results.xlsx`, `figures/<case>/` |
| 9 | `99_check_all.py` | ten checks: six test suites, then the pipeline and mass balance | nothing |

**Steps 0 and 1 are optional.** `02` and `03` validate the inputs themselves and
refuse a broken table, so nothing silently uses bad numbers if you skip them.

**Steps 2 and 3 do not depend on each other.** `03` runs the deterministic solve
itself. Run `02` when you want the diagrams; run `03` when you want the numbers
and the uncertainty. Either can be run alone.

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
`data_folder/`, each with its own data and its own coefficients.

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| folder | `data_folder/bev_electronics` | `data_folder/carcomposition_mockup` |
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
data_folder/<case>/output_data/
    recovery_results.xlsx        <-- open this one
    monte_carlo_summary.csv      every result row, every percentile
    solution_optimized_model.csv the deterministic answer

figures/<case>/
    structure.png                the flow network and its coefficients
    total.png                    the Sankey, all resources
    <resource>.png               one Sankey per resource
    distribution.png             recovered mass across draws
    pdf_<resource>.png           the distribution, one panel per year
    spread.png                   the 30 widest intervals
    mode_vs_mean.png             deterministic against the MC mean
    convergence.png              is the draw count enough
    sensitivity.png              which coefficient drives the answer
```

**A folder per case**, with the same names in both, so the two pipelines cannot
overwrite each other and their figures compare directly.

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
