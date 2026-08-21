# Running the two pipelines

The short version. Everything here is a command you can paste.

There is **one model**. The two pipelines are two **cases** — two folders under
`data_folder/`, each with its own data and its own coefficients. Switching
between them is naming the folder. **Nothing in `src/params_schema.py` changes.**

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| case folder | `data_folder/bev_electronics` | `data_folder/carcomposition_mockup` |
| what it covers | wiring and motors in BEVs | whole cars, five drivetrains |
| finest resolution | **element** — Cu, Nd, Dy | **material** — calAHSS, battery |
| years | 2030–2050 | 2040 |
| draws | 200,000 | 50,000 |
| coefficients | yours, hand-filled | **invented**, generated |

---

## Before anything

```bash
./.venv/bin/python 00_parameters.py --check
```

Prints every setting in force and whether the upstream draws are reachable. If
this fails, nothing else will work. `00_parameters.py` with no argument
regenerates `params.xlsx` and `documentation/PARAMETER_REFERENCE.md`.

---

## Pipeline 1 — BEV electronics (04_02)

```bash
./.venv/bin/python 01_check_inputs.py data_folder/bev_electronics
```

```bash
./.venv/bin/python 02_run_model.py data_folder/bev_electronics
```

```bash
./.venv/bin/python 03_run_monte_carlo.py data_folder/bev_electronics
```

## Pipeline 2 — car composition (04_01)

```bash
./.venv/bin/python 01_check_inputs.py data_folder/carcomposition_mockup
```

```bash
./.venv/bin/python 02_run_model.py data_folder/carcomposition_mockup
```

```bash
./.venv/bin/python 03_run_monte_carlo.py data_folder/carcomposition_mockup
```

**With no folder argument, each uses `run.data_folder`** — so the everyday case
runs by typing nothing.

---

## What each step does

| step | reads | writes |
|---|---|---|
| `01_check_inputs.py` | the case's three input files | nothing — it reports |
| `02_run_model.py` | the same | `output_data/solution_*.csv`, Sankeys |
| `03_run_monte_carlo.py` | the same | `output_data/monte_carlo_summary.csv`, `recovery_results.xlsx`, the MC figures |

**01 does not have to be run first.** 02 and 03 validate the inputs themselves
and refuse a broken table. 01 exists so you can look at the totals without
solving anything.

**Neither 02 nor 03 depends on the other.** 03 runs the deterministic solve
itself, so you can go straight to it.

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

**A folder per case**, so the two pipelines cannot overwrite each other. If you
still see loose `mc_*.png` and `bev_electronics_*.png` files directly in
`figures/`, those are leftovers from before that change and can be deleted.

### The workbook, sheet by sheet

| sheet | what it is |
|---|---|
| Overview | the settings this run used, and the standing caveats |
| **Recovered** | the headline: recovered mass per resource per year, with the 95% interval |
| By flow | where the mass ended up, totalled at each flow's own depth |
| Mass balance | what entered against what left. **Check this first.** |
| Distribution | every result row and every percentile |
| Coefficients | the TC table as used, including the `source` column |
| Composition | what the model thinks each product is made of |

---

## Changing what a run covers

**Years, scenario, engine, working unit** — `src/params_schema.py`, `run.*`.
These are facts about the run, shared by every case.

| `run.years` | runs |
|---|---|
| `''` | every year in the data |
| `'2040'` | that one year |
| `'2030-2050'` | that range |
| `'2030-2050,10'` | every 10th year of it |

**Everything else about a case is in the case** —
`data_folder/<case>/input_data/source.csv`: which upstream export, which
product(s), which layer the children sit at, how many draws. See
[CASES.md](CASES.md).

### Memory

The Monte Carlo array is `result rows × draws × 8 bytes`, and
`monte_carlo.memory_budget_gb` (4 GB) is checked **before** allocating. Chunking
bounds the working memory but not the result, so the two levers are `run.years`
and the case's `draws`.

| case | result rows | at its draw count |
|---|---|---|
| 04_02, 2 groups, 5 years | 600 | 0.96 GB |
| 04_01, 5 drivetrains, 1 year | 4,117 | 0.30 GB at 50,000 |
| 04_01, 5 drivetrains, 5 years | ~20,000 | would be refused at 200,000 |

---

## The coefficient tables

Both tools write `<case>/input_data/TCs.csv` from that case's own composition,
so the table covers exactly what the case contains — no row that can never fire,
no resource left without coefficients.

```bash
./.venv/bin/python tools/make_skeleton.py data_folder/bev_electronics
```

Writes every row that needs a number, **blank**. It **merges**: re-run it any
time and what you filled in is kept, new resources are added blank, and rows
whose resource no longer exists are dropped. Nothing you typed is overwritten.

```bash
./.venv/bin/python tools/make_carcomposition_tcs.py data_folder/carcomposition_mockup
```

Writes the same rows **already filled with invented numbers**, because 278
resources is not fillable by hand. It **overwrites** — everything in it is
marked `MADE UP (Claude)` in the `source` column, so there is nothing of yours
to protect. Once you start putting measured numbers in, stop running it.

---

## Seeing a case before solving it

```bash
./.venv/bin/python 01_import_upstream.py data_folder/bev_electronics
```

Writes `inputs.csv` and `composition.csv` into the case, so you can open the
numbers the model will solve. **Nothing reads them.** Every run takes its
numbers from the upstream draws through `src/upstream.py`; delete these files
and the results are identical.

---

## Upstream — when you have to touch RAWCLICStockAndFlow

Normally never. The recovery model reads the draws that are already on disk.

You need to go upstream only to **add a year or a scenario**:

| you want | run there |
|---|---|
| another year of electronics | `materials.bev_electronics_element_draws_years`, then `04_02_BEVelectronics.py` |
| another year of car composition | `materials.carcomposition_draws_years` **and** a matching single-year entry in `monte_carlo.output_periods`, then `04_01_carcomposition.py` |

Both need `code/00_parameters.py` run first — the stages read a saved params
artifact, not the source file, so an edit that is not followed by that command
has no effect and the run looks fine.

**04_01 needs single-year periods** because its draws are cumulative over a
period, while the recovery model's axis is years:

```python
output_periods = [(1975, 2070), (2040, 2040)]
```

Keep `(1975, 2070)` — every existing figure and saved table is keyed on it.

### One honest limitation

For a single year, real per-year vehicle-count draws exist **only for BEV**.
The other four drivetrains take their exact per-year level from
`03_tracker_keyed` and their distribution shape from the cumulative summary.
**Their mean is exact; their spread is a floor**, because a cumulative total
averages year-to-year variation out. The run prints which path each drivetrain
took. Removing the approximation means widening 03_02's BEV-only export to
every drivetrain — worth doing next time 03_02 runs anyway, not worth a run of
its own.

---

## Checking nothing is broken

```bash
./.venv/bin/python 99_check_all.py
```

Runs six test suites against fixed fixtures — independent of your `TCs.csv`,
which changes often — then the whole pipeline on the live case and a mass
balance. Ten checks.

```bash
./.venv/bin/python 99_check_all.py --code
```

The suites only. This one passes even with `TCs.csv` deleted, which is the
point: it tests the code, not your table.

---

## Keeping this up to date

This document and [CASES.md](CASES.md) are the pair to maintain:

- **RUNNING.md** (this one) — what to type, and what comes out.
- **[CASES.md](CASES.md)** — how a case is configured, and why it is built that
  way.

Anything that changes a command, a file location, a setting's meaning, or what a
run produces belongs in one of them in the same commit as the change. The rest
of `documentation/` is reference and is indexed in [README.md](README.md).
