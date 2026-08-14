# Futuram Recovery Model

Computes material flows through a recovery system across four nested resource
layers — products contain components, components contain materials, materials
contain elements. Inflows are split by composition, then routed through
processes by transfer coefficients (TCs).

## Repository layout

- `src/` — the two model engines
- `data_folder/` — input data, one folder per case (`basic_test` is the mock reference case)
- `doc/User guide.docx` — input data format specification
- `run_model.py` — entry point

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
`requirements.txt` and built with Python 3.14.

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

In Positron, select `.venv` as the interpreter (it is picked up automatically
from `.vscode/settings.json`). Run the model from the project root:

```bash
./.venv/bin/python run_model.py
```

Versions are pinned deliberately. This model is sensitive to pandas behaviour
changes — copy-on-write and the removal of legacy APIs have both silently
altered its intermediate results in the past.

## Using the model

Add a new folder under `data_folder/` containing an `input_data/` sub-folder
with three CSV files:

- `inputs.csv` — the inflows per parent resource
- `composition.csv` — what each resource is made of
- `TCs.csv` — the transfer coefficients between flows

Point `data_folder` in `run_model.py` at your new folder and run it. Results
are written to an `output_data/` folder alongside your inputs. The column
definitions for all three files are in `doc/User guide.docx`.

Real input data is not tracked by git; only the `basic_test` mock case is.

## Known issues

The model reproduces its reference case exactly, but several behaviours are
either undocumented or differ between the two engines. Before relying on
results beyond `basic_test`, read these:

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
- **There is no mass balance check.** Nothing verifies that the TCs leaving a
  flow sum to anything in particular. In `basic_test` they sum to between 0.06
  and 0.80, and the unaccounted mass has no residual flow — it simply leaves
  the system unrecorded.
- **Everything is deterministic.** The `DQS` and `CV` columns are declared in
  the input dtypes but are read by nothing.
