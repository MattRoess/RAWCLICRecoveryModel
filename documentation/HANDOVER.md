# Handover

Current as of **2026-08-26**, commit `71653e2`. Rewritten from the ground up on
2026-08-21 and updated since; git has the older text.

**What changed on 2026-08-26.** The case workbooks gained dropdowns and a
marked header row, `is_loss` was dropped in favour of `role`, and the sum-to-1
machinery was finished: a third rule, a check that says where the constraint
pulls, a guard, and two tools. §2 has the rules, §5 the two traps. No
coefficient changed.

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
suites on fixed fixtures (95 checks), then the pipeline and a mass balance.

Both case tables are **structurally finished**. `tools/tc_worklist.py` reports
22 of 24 groups in the electronics case and 278 of 278 in the car composition
one as *correct as they stand*, with no warnings on either. Nothing in the
tables needs converting, rearranging or repairing. What they need is numbers —
see §4.

### The one thing that matters most

**Every transfer coefficient in this project is a placeholder I invented.**
Not one is measured.

| case | rows | invented outright | derived from those |
|---|---|---|---|
| `bev_electronics` | 52 | 24 `PLACEHOLDER (Claude, not data)` | 28 residuals and routing decisions |
| `carcomposition_mockup` | 632 | 354 `MADE UP (Claude)` | 278 residuals |

**The derived rows are not measurements either.** A residual is
`parent − Σ known children`, so it is arithmetic on the invented numbers beside
it — which is why the headline above says every coefficient and means it. The
split is worth stating only because the `source` column distinguishes them, and
a reader comparing this table against the file should find them agreeing.

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
    case.xlsx
        source      where the numbers come from, and how they map to layers
        processes   the flow network
        TCs         the coefficients
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
every run. There is no import step and no intermediate file: neither case has
an `inputs.csv` or a `composition.csv` on disk, and both run.

`01_import_upstream.py` used to write those two files so a case could be looked
at. It was **deleted on 2026-08-24** along with the `data.import_case` and
`data.import_year` settings that existed only to serve it. It had already been
deleted once, restored, and then left out of the pipeline, which is a fair sign
that its real job was answering "what will the model solve?" — a question the
`01_check_inputs.py` report and the figures now answer from the draws
themselves.

Four modules still *can* read those files, as a fallback when a caller has not
already passed the frames in: `src/validate_inputs.py`, `src/mass_balance.py`,
`src/plot_flows.py` and `tools/make_skeleton.py`. Each tries the upstream draws
first, so the fallback is unreachable in the normal pipeline. It is left in
place deliberately — it is what lets a hand-written case folder be solved
without any upstream at all, which is how `tests/test_generality.py` builds its
photovoltaic case.

### How a group is made to sum to 1

Everything one resource turns into must total exactly 1. Independent draws do
not, so something has to give, and which thing is the modelling choice.

| the group | what happens | set by |
|---|---|---|
| names an `is_residual` row | that row becomes `1 − the rest` on every draw | the table |
| does not, and every row has a range | **conditioned** — see below | `monte_carlo.sum_to_one` |
| does not, and you asked for `normalise` | the group is divided by its own sum | `monte_carlo.sum_to_one` |

**Conditioning** is the default. It keeps every row's own measurement: draw
them all, take the widest as determined by the rest so the group sums to 1
exactly, weight each draw by that row's own density at the value it was forced
to, and resample so the draws come out equally weighted. It was checked against
brute-force rejection — draw everything and keep only what sums to 1 — and
agrees to four decimals, at about 1% of a run's cost rather than 20×.

**Normalising** is kept for two things and no others: reproducing a result from
before conditioning existed, and getting a number out of a group whose ranges
contradict each other. It hides the contradiction rather than resolving it.

`tools/compare_sum_rules.py` solves a case under both and prints which elements
the choice actually moves. If a case has nothing that can differ, it says so
and stops after one solve rather than drawing two identical curves.

Two consequences worth knowing before you touch a table:

- **`chunk` and `memory_budget_gb` cannot change a result.** The coefficients
  are drawn at full width, once, before anything is evaluated in blocks —
  precisely so conditioning never sees a block boundary. Two machines with
  different memory settings agree exactly. What conditioning *does* give up is
  composing separately invoked runs of different widths; nothing in the
  pipeline does that.
- **`01_check_inputs.py` has a `SUM TO 1` section.** A group's modes sum to 1
  by construction, but its *means* need not — a triangular's mean is
  `(min + mode + max)/3`. Where they disagree the constraint has to move the
  answer away from what is written. It reports that per group as an offset in
  standard deviations. The electronics case sits at a median of 0.73, driven by
  the rare-earth rows, and that is the source of the "running at the modes is
  not the mean" line every Monte Carlo run prints.

---

## 3. What changed upstream, and what did not

Branch **`carcomposition-draw-export`** in `RAWCLICStockAndFlow`, pushed. Three
commits are this work:

| commit | what |
|---|---|
| `6250bb5` | 04_01 writes a year slice of its mass draws in the `.npy` layout this model reads. Off by default. |
| `00af52a` | A single-year period reads the per-year draws 03_02 already writes, instead of demanding a period histogram that does not exist. |
| `7d6c9dd` | Every drivetrain gets a single-year vehicle count, without re-running 03_02. |

Those three touch **only** `code/04_01_carcomposition.py`.
**`03_02_adjustedflows.py` and `04_02_BEVelectronics.py` are unmodified**, and
`data/processed/bev_draws` (2.6 GB) was never rewritten.

The branch itself is **20 commits ahead of `main`** — the other 17 are earlier
work that had not been merged. Merging it brings all twenty, not three.

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

1. **Replace the coefficients. This is the whole of what is left.** The user
   asked on 2026-08-26 to have the case ready for real use; the model side is
   finished and nothing else is in the way. For electronics,
   `tools/make_skeleton.py` writes the rows and **merges**, so you can do it a
   domain at a time without losing what you filled in. For car composition,
   `tools/make_carcomposition_tcs.py` generated the current invented table and
   **overwrites** — but it now refuses to, once any row's `source` says
   something it did not write. `--overwrite` forces a deliberate rebuild.

   **Start with `tools/filling_sheet.py`**, which ranks the rows still waiting
   for a number by how much each one actually moves total recovered mass —
   Spearman, one Monte Carlo run, the same measure the sensitivity figure uses.
   On the electronics case **4 of the 24 carry 80% of the influence**, so the
   first afternoon of literature work is four rows rather than twenty-four.

   Fill in `value`, `value_min`, `value_max` and — this is the part that is
   easy to get wrong — **leave `is_residual` alone unless you have a second,
   independent measurement for that group.** One measurement per group is
   already handled exactly by the residual rule. §5 has the two ways of
   pretending otherwise, both of which look like progress and are not.
   `tools/tc_worklist.py` says which group is which and has blank columns for
   an independent number and its source.
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
- **Do not manufacture a second measurement.** Conditioning is worth having
  only where the extra range was measured *without going through* the rest of
  the group. Both shortcuts were tried and measured:
  - clearing `is_residual` and leaving the bounds blank leaves the group one
    degree of freedom and no slack — every draw comes out identical, recovery
    pinned at a single value across 100,000 draws. `src/sampling.py` **refuses
    this** now, but it silently destroyed the spread before it did.
  - filling in `1 − the rest of the group` counts one measurement twice: the
    target becomes `f(x)·f(x)` instead of `f(x)`, narrowing the answer by about
    a fifth for no reason. Not refused — it cannot be told from a real second
    opinion by arithmetic alone — but `tools/tc_worklist.py` flags it, and
    `reference/template`'s loss rows are exactly this, so any demonstration of
    conditioning on that fixture measures squaring.
- **A high effective sample size does not mean a second range was worth
  having.** Two ranges that restate each other agree perfectly and keep nearly
  all of it. Effective sample size says whether ranges are *consistent*, never
  whether they are *independent*. Only the `source` column says that.
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
9. **Do not invent data to make a feature demonstrable.** On 2026-08-26 a
   placeholder range was written for one row so conditioning would have
   something to do. It happened to be the exact reflection of the row beside
   it, so the demonstration measured one measurement squared and reported a
   21% improvement that did not exist — shown to the user in a figure and a
   table before anyone noticed. If a feature has nothing to act on, say that;
   it is a finding, not a gap to be filled.
10. **Document in the same commit as the change, and mean every document.**
    This used to name only RUNNING.md and CASES.md, and the two that drifted
    were the ones it did not name. On 2026-08-26 a sweep found DEFECTS.md still
    listing the mass balance, the Monte Carlo and unit conversion as absent
    capabilities — three things built days earlier — the index still saying the
    real TC table "does not exist yet", and `monte_carlo.enabled` documented as
    "off by default" while its value was `True`. Nothing there was hard to fix;
    it was simply never struck off. Building a thing and striking it off the
    list of things not built are one task, not two.

Settled conventions: **95% interval** on every distribution figure. Plain
figure titles.

**Units — three are in play at once, and this document uses all three.** The
data folders are written in **Mg**, the upstream pipeline delivers **kt**, and
the arithmetic and every output file are in **kg** (`run.working_unit`). The
inflow is converted on load, from whatever the file declares to the working
unit, so nothing is converted by hand. Figures pick a display scale per figure
— which is why §1 reports 640.7 kt while the summary file holds 640,684,957.
A wrong unit is a silent factor of 1000, so `src/units.py` is worth reading
before touching any of it.

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

The same thing happens to the **iCloud Drive path** and it looks worse than it
is. On 2026-08-26 the whole project tree stopped being listable mid-session:
`ls`, `git` and even `python` failed with *Operation not permitted* — `getcwd`
and directory enumeration denied while individual files still opened by path,
and it persisted outside the sandbox, so it was macOS rather than any tool.
Restarting the app cleared it. Nothing was lost and nothing needed repairing.

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
