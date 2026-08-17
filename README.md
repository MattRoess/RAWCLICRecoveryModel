# Futuram Recovery Model

Computes material flows through a recovery system across four nested resource
layers — products contain components, components contain materials, materials
contain elements. Inflows are split by composition, then routed through
processes by transfer coefficients (TCs).

## Repository layout

- `src/` — the two model engines
- `data_folder/` — input data, one folder per case (`basic_test` is the mock reference case, `template` shows the proposed schema)
- `documentation/` — how the model works, known defects, and the Monte Carlo design
- `doc/User guide.docx` — input data format specification
- `params.xlsx` — **the parameter file**: which case, which engine, which figures. Every script reads it
- `00_parameters.py` — creates and validates `params.xlsx`, and regenerates the parameter reference
- `run_model.py` — entry point: solves a data folder and draws its figures
- `compare_engines.py` — runs both engines over a data folder and diffs them
- `check_mass_balance.py` — reports what a dataset's TCs and composition total to
- `plot_structure.py` — draws how the flows connect and the TCs behind each arrow
- `plot_flows.py` — draws mass-weighted Sankey diagrams, in total and per element

**Start at [documentation/README.md](documentation/README.md).** It indexes how
the model actually computes a result, every known defect with a reproduction,
and the open design questions.

There are two engines, which agree exactly on `basic_test`:

| | `RecoveryModelOptimized` | `RecoveryModelLA` |
|---|---|---|
| Method | Processes TCs one by one with dataframe joins, in topological order | Solves the whole system as sparse linear algebra |
| Feedback loops | Not supported (raises on cycles) | Supported |
| Scaling | Scales with the number of populated rows | Scales with the *product* of all layer cardinalities |

`RecoveryModelOptimized` is the default and is the faster of the two on
realistic problem sizes. `RecoveryModelLA` is useful as an independent check on
small cases.

## Setup

No conda. The project uses a plain virtual environment, pinned in
`requirements.txt` and built with Python 3.14. Full instructions for a fresh
machine, including Positron, are in [documentation/SETUP.md](documentation/SETUP.md).

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

In Positron, select `.venv` as the interpreter (it is picked up automatically
from `.vscode/settings.json`). Create the parameter file once, then run the
model — both from the project root:

```bash
./.venv/bin/python 00_parameters.py
```

```bash
./.venv/bin/python run_model.py
```

`00_parameters.py` writes `params.xlsx`, which is where the case, the engine
and every figure setting live. Edit it in Excel or Positron; the scripts read
it directly, so nothing needs re-running there and no Python needs editing.
`00_parameters.py --check` validates it and prints the values in force.

Versions are pinned deliberately. This model is sensitive to pandas behaviour
changes — copy-on-write and the removal of legacy APIs have both silently
altered its intermediate results in the past.

## Using the model

Add a new folder under `data_folder/` containing an `input_data/` sub-folder
with three CSV files:

- `inputs.csv` — the inflows per parent resource
- `composition.csv` — what each resource is made of
- `TCs.csv` — the transfer coefficients between flows

Then set `run.data_folder` in `params.xlsx` to your new folder and run
`run_model.py`. For a one-off run of a different case without touching the
parameter file, pass it as an argument instead:

```bash
./.venv/bin/python run_model.py data_folder/my_case
```

Results are written to an `output_data/` folder alongside your inputs, and the
figures to `figures/`. Run any script with `--list` to see the folders it can
find, or `--pick` to choose from a menu. The column definitions for all three
input files are in `doc/User guide.docx`; every parameter is documented in
[documentation/PARAMETER_REFERENCE.md](documentation/PARAMETER_REFERENCE.md).

Real input data is not tracked by git; only the `basic_test` mock case is.

## Known issues

The model reproduces its reference case exactly, but several behaviours are
either undocumented or differ between the two engines. Before relying on
results beyond `basic_test`, read these — each is documented with a
measurement and a one-command reproduction in
[documentation/DEFECTS.md](documentation/DEFECTS.md):

- **Composition `Stock/ID` is ignored by `RecoveryModelOptimized`.** It merges
  composition on the parent resource alone, so compositions defined for one
  flow are applied to every flow with the same parent. `RecoveryModelLA`
  honours it, as the user guide specifies.
- **The documented `P*` wildcard only works in `RecoveryModelLA`.**
  `RecoveryModelOptimized` treats it as a literal key, matches nothing, and
  silently emits no flow at all.
- **Overlapping TC specificity resolves differently.** Given both a
  product-level and a component-level TC for the same process, `LA` applies the
  more specific one and `Optimized` adds them together.
- **Bad input is not rejected — it is absorbed.** Nothing validates the input
  tables. An inflow naming a flow that appears in no TC adds 4000 Mg of phantom
  mass to `basic_test` under `RecoveryModelOptimized`, with no warning; the
  same input makes `RecoveryModelLA` die on an unreadable `TypeError`. A
  composition row that fills only `Layer 1` invents mass the same way.
- **Same-layer TCs discard `Input_layer_key` in `RecoveryModelOptimized`.**
  A component→component TC is read as "anything → that component", so the two
  engines disagree wherever a resource is routed within one layer.
- **There is no mass balance check.** A TC is a retention fraction for one
  resource into one destination flow, so the meaningful total is per resource
  over the output flows it reaches. Nothing verifies it. Run
  `check_mass_balance.py` to see it for any dataset: on `basic_test` the totals
  range [0, 0.66] and the unaccounted 78% has no residual flow — it simply
  leaves the system unrecorded.
- **Everything is deterministic.** The `DQS` and `CV` columns are declared in
  the input dtypes but are read by nothing.
