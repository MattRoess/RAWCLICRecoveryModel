# Documentation index

Written 2026-08-14, after a review of the inherited code. The point of these
documents is that the next working session starts from something written down
rather than from anyone's recollection.

| Document | What is in it |
|---|---|
| **[RUNNING.md](RUNNING.md)** | **Start here.** Set the case in `src/params_schema.py`, then press Run on each numbered file in turn. What each step does, what comes out, where it lands, and the only two reasons to touch the upstream project. |
| [SETUP.md](SETUP.md) | Getting running on a new machine: Python 3.14 without conda, the venv, and Positron. Start here on a fresh Mac. |
| [MODEL_MECHANICS.md](MODEL_MECHANICS.md) | How the model actually computes a result. The nesting rule, how composition and TCs are applied, what the two engines do differently by design. Read this first. |
| [DEFECTS.md](DEFECTS.md) | Every defect and engine divergence found, each with a measurement and a one-command reproduction. |
| [DESIGN_tc_table.md](DESIGN_tc_table.md) | How to build the TC table so that sum-to-1 holds by construction. Proposal, with a worked example in `data_folder/reference/template`. The real table does not exist yet, so read this before collecting data. |
| [DESIGN_04_01_carcomposition.md](DESIGN_04_01_carcomposition.md) | What it would take to read stage 04_01 (car composition) as well as 04_02. Effort estimate, layer mapping, and a made-up TC table on the real component and material names. |
| [DESIGN_monte_carlo.md](DESIGN_monte_carlo.md) | The design problem for the Monte Carlo version: architecture, the compute budget, sampling asymmetric triangulars, and how to sample under the sum-to-1 constraint. **Built 2026-08-20** — see `src/monte_carlo.py`. |
| [HANDOVER.md](HANDOVER.md) | Picking the work back up: where both pipelines stand, what is real and what is a placeholder, what changed upstream and what did not, what to do next, what will bite you, and how to work with this user. |
| [CASES.md](CASES.md) | One model, one case per upstream stage. The three tables a case carries, what `source` says, how to fill the coefficients in, and how to add 04_03 or 04_04 without touching the settings. |
| [PARAMETER_REFERENCE.md](PARAMETER_REFERENCE.md) | Every setting, its current value, and what changing it does. Generated from `src/params_schema.py` — do not edit by hand; edit the settings file. |

The input file format is specified in `../doc/User guide.docx` (Harmjan de
Vries, 21-11-2024). That document is the authority on the input schema and is
still accurate. It does not describe model behaviour, which is what
MODEL_MECHANICS.md covers.

## Everything is a file you press Run on

Nothing in this project needs a terminal, and nothing takes an argument.
`00_parameters.py`, `01_check_inputs.py`, `02_run_model.py`,
`03_run_monte_carlo.py`, `99_check_all.py`, `tools/plot_structure.py` and
`tools/compare_sum_rules.py`, `tools/tc_worklist.py` and
`tools/filling_sheet.py` each do
one step, and each reads `run.data_folder` from `src/params_schema.py` -- which
is where you choose the pipeline. Step by step, in that order. See
[RUNNING.md](RUNNING.md).

Read MODEL_MECHANICS.md section 4 before reading a coefficient total -- the
grouping it uses is not the obvious one, and the obvious one produces numbers
that are not quantities.

## Seeing the flows

**How the model is wired** -- every flow, every process, and the transfer
coefficients behind each arrow, nothing scaled by mass -- is
`tools/plot_structure.py`, and `run.draw_structure` decides whether an ordinary
run draws it too.

**How much mass goes where** is the Sankeys, and they are drawn by every run, so
there is nothing separate to press. That is deliberate: a Sankey is a picture of
a RESULT, so a run that produced numbers without the matching picture is exactly
how the two drift apart. The structure diagram is different -- it describes the
TC table rather than a result, and changes only when that table changes.

Both render through matplotlib, so every requested format comes from one drawing
and they cannot disagree. Which formats, which resolution, which palette are
settings in `src/params_schema.py` (`figures.*`), not flags.

Figures land in `figures/<case>/`, one folder per case, with the same names in
each so the two pipelines compare directly.

## Years and scenarios

**Years**: `years` in `src/params_schema.py`.

| setting | runs |
|---|---|
| `''` | every year in the data |
| `'2040'` | that one year |
| `'2030-2050'` | that range, every year in it |
| `'2030-2050,10'` | that range, every 10th year |
| `',10'` | every 10th year of the whole data |

Real inflow data is annual — the upstream arrays run 1975 to 2070 — so a step
is usually what you want: it keeps the shape of the trajectory while cutting
its size. The step counts by year value rather than by row, so a gap in the
data does not shift everything after it.

Several years in one run is normal, unlike scenarios which are one per run.
It matters under the Monte Carlo: 200,000 draws × 96 years is the memory
problem in DESIGN_monte_carlo.md §2, and the year axis is the most direct lever
on it.

## Scenarios

**One run is one scenario, across all its years.** Set `scenario` in
`src/params_schema.py` and run; run the others separately. Each writes to its
own folder, `output_data/<scenario>/`, so results accumulate rather than
overwrite.

Scenarios are declared by the data, not by a list: the distinct values in
`inputs.csv`'s optional `Scenario` column are the scenarios that exist. If that
column is absent — as it is in every case folder here today — there is no
scenario dimension and the setting stays blank. If it is present and the
setting is blank, the run stops and lists what it found rather than guessing.

**Comparing scenarios is analysis, not modelling.** The model produces one
scenario's numbers and stops. Reading several `output_data/<scenario>/` folders
and putting them side by side is a separate step, deliberately kept outside the
model so it does not grow a reporting layer.

Why not solve them together: they are independent — this model is pure
flow-through with no stock carried between runs — so nothing is shared but the
time spent reading three CSVs. Under the Monte Carlo it actively costs, since
memory is already the binding constraint (DESIGN_monte_carlo.md §2). Separate
runs also means several scenarios on several cores, and a failure that loses
one rather than all of them.

## Verifying the model still works

Both engines reproduce the committed reference result exactly:

```bash
./.venv/bin/python tools/compare_engines.py data_folder/reference/basic_test
```

Expected: 180 rows, largest engine difference on the order of 1e-15.

That last figure varies slightly between runs. This is expected and understood:
the LA engine's encoding order depends on Python's hash randomisation, which
changes the floating-point accumulation order in its sparse solve. See
DEFECTS.md §3.5. The optimized engine is bit-identical across runs.
