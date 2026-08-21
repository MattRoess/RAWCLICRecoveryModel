# Handover

Current as of **2026-08-21**, commit `a4879c2`. Rewritten from the ground up on
that date; the previous version described the state before the Monte Carlo was
fed real data and is superseded. Git has it if you want the old text.

**Read [RUNNING.md](RUNNING.md) first if you just want to run something.** This
document is for picking the work back up.

---

## 1. Where things stand

**Two pipelines run end to end on real upstream data. All ten checks pass.**

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| case folder | `data_folder/bev_electronics` | `data_folder/carcomposition_mockup` |
| covers | wiring and motors in BEVs | whole cars, five drivetrains |
| finest resolution | **element** — Cu, Nd, Dy | **material** — calAHSS, battery |
| years | 2030–2050 | 2040 |
| draws | 200,000 | 50,000 |
| mass in | 640.7 kt (2050) | 13,863 kt (2040) |
| mass balance | 2.8e-16 | 4.4e-11 |
| result rows | 600 | 4,117 |

To verify, set `run.data_folder` and press Run on `99_check_all.py`: six test
suites on fixed fixtures, then the pipeline and a mass balance.

### The one thing that matters most

**Every transfer coefficient in this project is a placeholder I invented.**
Not one is measured.

| case | rows | provenance |
|---|---|---|
| `bev_electronics` | 52 | 26 `PLACEHOLDER (Claude, not data)`, 26 derived residuals and routing decisions |
| `carcomposition_mockup` | 632 | all `MADE UP (Claude)` |

The `source` column says so on every row, and it is carried into the workbook's
Coefficients sheet. The uncertainty ranges are invented too, so **the 95%
intervals are the spread of guesses, not of observations.**

What *is* real: inflow mass and composition (from the upstream draws), every
name — elements, drivetrains, components, materials — and which (component,
material) pairs exist. The mass balance, closure to 1, layer nesting and Monte
Carlo machinery are checked and correct. They are correct arithmetic on
placeholders.

---

## 2. The architecture, in one page

**One model.** `src/` knows nothing about vehicles, electronics or panels. What
differs between studies is a **case**: a folder under `data_folder/` holding

```
input_data/
    source.csv      where the numbers come from, and how they map to layers
    processes.csv   the flow network
    TCs.csv         the coefficients
```

Switching studies is changing `run.data_folder` in `src/params_schema.py`.
Nothing else changes — which is the point: a setting you have to edit to run the
other study is a setting somebody forgets, and then one stage's draws get read
with another stage's coefficients and no check anywhere notices.

Three things `source.csv` says that nothing could infer:

- **`child_layer`** — `element` (04_02: the child is Cu within Wiring, with a
  placeholder material between) or `material` (04_01: the child is calAHSS
  within elvBIW, at Layer 3, no Layer 4). Getting this wrong **does not fail**:
  it files materials where elements belong, every element-keyed coefficient
  matches nothing, and the run still balances while being wrong.
- **`product`** — one name, or several separated by `;`. 04_01's five
  drivetrains are one case, because they are one study: the same shredder and
  the same coefficient table, with only the dismantling rows keyed per
  drivetrain. Each product is its own whole — a component's share is a share of
  its own drivetrain, never of all five together.
- **`draws`** — 04_01 exported 50,000 and 04_02 exported 200,000. Running the
  coefficients at a width the inflow does not have is a mismatch nothing
  downstream reports.

Full detail in [CASES.md](CASES.md).

### No intermediate steps

The engines read the upstream `.npy` draws directly through `src/upstream.py`,
every run. `01_import_upstream.py` writes `inputs.csv` and `composition.csv` so
you can *look* at a case — **nothing reads them.** Delete them and the results
are identical. (`bev_electronics` has them on disk; `carcomposition_mockup` does
not. Both run the same.)

---

## 3. What changed upstream, and what did not

Branch **`carcomposition-draw-export`** in `RAWCLICStockAndFlow`, pushed, three
commits:

| commit | what |
|---|---|
| `6250bb5` | 04_01 writes a year slice of its mass draws in the `.npy` layout this model reads. Off by default. |
| `00af52a` | A single-year period reads the per-year draws 03_02 already writes, instead of demanding a period histogram that does not exist. |
| `7d6c9dd` | Every drivetrain gets a single-year vehicle count, without re-running 03_02. |

**`03_02_adjustedflows.py` and `04_02_BEVelectronics.py` are unmodified**, and
`data/processed/bev_draws` (2.6 GB) was never rewritten.

### The one honest approximation

For a single year, real per-year vehicle-count draws exist **only for BEV** —
03_02's export is BEV-only. The other four drivetrains take:

- their **level** from `03_tracker_keyed`, which holds exact per-year counts for
  all five;
- their **shape** from that (drivetrain, segment)'s widest cumulative summary,
  rescaled to the level.

**Their mean is exact. Their spread is a floor**, because a cumulative total
averages year-to-year variation out, so its relative spread is narrower than any
single year's. The run prints which path each drivetrain took.

Removing it means widening 03_02's BEV-only export loop to every drivetrain —
about twenty lines. **Worth folding into the next 03_02 run, never worth a run
of its own.** A full 03_02 re-run is hours and rewrites the draws 04_02 depends
on.

### Getting more years

| you want | set there | then press Run on |
|---|---|---|
| another year of electronics | `materials.bev_electronics_element_draws_years` | `code/04_02_BEVelectronics.py` |
| another year of car composition | `materials.carcomposition_draws_years` **and** a matching single-year entry in `monte_carlo.output_periods` | `code/04_01_carcomposition.py` |

**Press Run on `code/00_parameters.py` there first.** Those stages read a saved
params artifact, not the source file, so an edit not followed by that has no
effect and the run still looks fine. This cost an hour before it was understood.

**04_01 needs single-year periods** because its draws are cumulative over a
period while this model's axis is years. Keep `(1975, 2070)` alongside — every
existing figure and saved table there is keyed on it.

---

## 4. What to do next, in order

1. **Replace the coefficients.** This is the only thing standing between the
   model and a result. Everything else works. For electronics,
   `tools/make_skeleton.py` writes the rows and **merges**, so you can do it a
   domain at a time without losing what you filled in. For car composition,
   `tools/make_carcomposition_tcs.py` generated the current invented table and
   **overwrites** — once you start putting real numbers in, stop running it.
2. **Decide the segment question for 04_01.** Twelve segments are currently
   summed, on the assumption that recovery does not depend on car size. If it
   does, the alternative is a run per segment, not a new layer.
3. **Widen 03_02's per-year export** to all five drivetrains, next time it runs
   anyway. Removes the approximation in §3.
4. **More years for 04_01**, if wanted — but check the memory arithmetic first:
   five drivetrains over five years is roughly 20,000 result rows, which at
   200,000 draws exceeds the 4 GB budget and would be refused.
5. **04_03 and 04_04.** Each needs its own year-sliced export upstream, then a
   case folder here. No code change unless its children sit at a layer that is
   neither element nor material — in which case `src/source.py` gains a third
   value, `src/upstream.py` a third branch, and `tests/test_generality.py` a
   third case *before* either.

---

## 5. Things that will bite you

- **Getting `child_layer` wrong does not fail.** It balances and it plots. §2.
- **A coarse TC scales the resource's whole subtree**; a fine one does not.
  All TCs writing into one output flow must target the same layer, or nesting
  breaks — measured at 82 Mg on a shared loss flow. `01_check_inputs.py` checks
  this.
- **`rest` is derived, not written.** Per parent per year, `parent − Σ known
  children`, and it defaults to *unrecovered*. That is what makes every recovery
  figure a **lower bound** rather than an estimate.
- **Sampled maxima must not sum past 1 per resource.** If they do, the residual
  goes negative on extreme draws and the model produces negative mass — which
  balances perfectly and is nonsense. It happened: 17 of 278 resources in the
  first 04_01 table, surfacing as a negative 2.5th percentile on `ELV_loss_ASR`.
  `make_carcomposition_tcs.py` caps them; a hand-edited table can reintroduce it,
  and the Monte Carlo will report it as `NEGATIVE RESIDUALS`.
- **Memory is `result rows × draws × 8 bytes`**, checked before allocating.
  Chunking bounds the working memory but not the result, so the levers are
  `run.years` and the case's `draws`.
- **Totalling the `Value` column quadruple-counts.** A deeper row is a
  *sub-quantity* of its parent. Total at each flow's own shallowest depth.
- **Coefficient totals must be grouped by `TC_target_key` and summed over
  `Output_FlowID`.** The obvious grouping produces numbers that are not
  quantities. MODEL_MECHANICS.md §4.

---

## 6. How to work with this user

Read this before doing anything. Every item cost time to learn.

1. **No command line.** Everything runs by pressing Run in Positron, no
   arguments, case chosen in `src/params_schema.py`. Step by step: `00`, `01`,
   `02`, `03`, `99`.
2. **Ask before adding anything** — no new file, tool, wrapper or intermediate
   step. A question wants an answer, not a project. `RUN.py` was added unasked
   and deleted the same day.
3. **Never delete. Never overwrite with different data.** Separate cases by
   **folder**, not by filename prefix. "Bring the old one back" means restore it
   verbatim from git and change only what stops it running.
4. **Never re-run an upstream stage to test.** Read what is already on disk.
   Never 200,000 draws for a test.
5. **Never conda.** venv and a pinned `requirements.txt`.
6. **Verify it yourself before showing it.** Open the figure. Check the number.
   Do not make the user find the bug.
7. **It has to work generally.** Write the failing test first, then generalise —
   `tests/test_generality.py` builds a PV panel case sharing no name with a
   vehicle, and runs it through both `child_layer` shapes.
8. **Be exact about provenance.** Never imply a placeholder is data.
9. **Keep [RUNNING.md](RUNNING.md) and [CASES.md](CASES.md) current in the same
   commit** as any change to what a file does or what a run produces.

Settled conventions: **kg**, not Mg. **95% interval** on every distribution
figure. Plain figure titles.

---

## 7. Environment

Python **3.14 + pandas 3.0.5**, pinned, in `.venv`. Never conda. Positron is the
editor; `.vscode/settings.json` is committed so `.venv` is selected
automatically, and `ipykernel` is in `requirements.txt` for the console. Every
entry script calls `src/bootstrap.ensure_venv()`, so it re-execs under the
project interpreter whatever it was started with.

The pins are load-bearing. pandas copy-on-write silently changed this model's
intermediate results, and three inherited breakages came from it —
`DataFrame._append` removal, a `SettingWithCopyWarning` import, and a
`fillna(inplace=True)` that became a silent no-op and blew an intermediate up by
300,000×.

Setup on a fresh machine: [SETUP.md](SETUP.md).

If `~/Documents` starts returning permission errors after a Claude update, the
app needs restarting. It is not a code problem.

---

## 8. The rest of the documentation

| document | what is in it |
|---|---|
| [RUNNING.md](RUNNING.md) | what to press, in what order, and what comes out |
| [CASES.md](CASES.md) | how a case is configured and why |
| [MODEL_MECHANICS.md](MODEL_MECHANICS.md) | how a result is actually computed. The nesting rule. **Read before reading any number.** |
| [DEFECTS.md](DEFECTS.md) | every defect found, with a measurement and a reproduction |
| [DESIGN_tc_table.md](DESIGN_tc_table.md) | how to build a TC table so sum-to-1 holds by construction |
| [DESIGN_04_01_carcomposition.md](DESIGN_04_01_carcomposition.md) | the 04_01 design, plus what building it proved the estimate had wrong |
| [DESIGN_monte_carlo.md](DESIGN_monte_carlo.md) | the Monte Carlo design; built, see `src/monte_carlo.py` |
| [PARAMETER_REFERENCE.md](PARAMETER_REFERENCE.md) | every setting and what it does. Generated — edit `src/params_schema.py`, not this. |

The input file format is specified in `../doc/User guide.docx` (Harmjan de
Vries, 21-11-2024), still accurate on the schema. It does not describe model
behaviour; MODEL_MECHANICS.md does.
