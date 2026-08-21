# Recovery model — BEV electronics

Computes what is recovered from end-of-life vehicle electronics, with full
uncertainty. Inflow and composition come straight from the upstream
stock-and-flow model; transfer coefficients are the part you write.

## Running it

```bash
./.venv/bin/python 99_check_all.py          # the code AND your case
./.venv/bin/python 99_check_all.py --code   # the code only
```

Two separate questions, answered separately:

- **The code** — the five test suites. They run entirely against the fixed
  fixtures in `data_folder/reference/`, so **nothing you do to `TCs.csv` can
  make them fail.** Use `--code` while a coefficient table is half-written.
- **Your case** — the pipeline and mass balance on your data. A failure there
  names your table, not the model.

Neither asserts any particular coefficient value: mass balance holds for any
well-formed table, because it is a property of the coefficients summing to 1,
not of what they sum from. Change every number in `TCs.csv` and every check
here is still meaningful.

The individual stages, in order:

| | |
|---|---|
| `00_parameters.py` | Regenerate `params.xlsx` from the settings. `--check` prints them. |
| `01_check_inputs.py` | Validate the tables and report what they total to. |
| `02_run_model.py` | Solve, and draw the Sankeys and the structure diagram. |
| `03_run_monte_carlo.py` | Solve over many draws; write the summary, the workbook and the MC figures. |

`tools/make_skeleton.py` is **not** a stage. It writes the TC rows that need a
number, from `processes.csv`, and is run when the network changes — not on
every run.

## Not specific to vehicles

The item being modelled is data, not code. `data.product`,
`data.inflow_flow_id`, `data.groups`, `data.material_suffix` and
`data.group_marker` are settings, so a different recovery item — a panel, a
battery, anything upstream exports in the `<child>__<parent>.npy` layout — is a
settings change.

`tests/test_generality.py` proves it rather than asserting it: it builds a
photovoltaic-panel dataset sharing no name with the vehicle case, and puts it
through the same code — read, derive `rest`, solve, close mass balance, run the
Monte Carlo. If someone re-specialises the code, that suite fails.

Any interpreter works — each script re-executes itself under `.venv`.

## Where the numbers come from

**There is no import step.** The inflow and composition are read from the
upstream draws in memory, on every run, and nothing is written in between:

```
RAWCLICStockAndFlow/data/processed/element_draws/<scenario>/<flow>/*.npy
        |   read directly, per src/upstream.py
        v
    the model
```

A case folder therefore holds only what a person writes:

```
data_folder/bev_electronics/input_data/
    processes.csv    the flow network -- seven lines
    TCs.csv          the transfer coefficients
```

The upstream stage only exports the years named in its own settings
(`materials.bev_electronics_element_draws_years`). Within those, `run.years`
selects: blank for all, `'2040'`, `'2030-2050'`, or `'2030-2050,5'`.

## Settings

Everything is in **`src/params_schema.py`**, each value with a comment saying
what it does. Edit there, then run `00_parameters.py`. `params.xlsx` and
`documentation/PARAMETER_REFERENCE.md` are reports — editing them changes
nothing.

The ones that change most: `data_folder`, `years`, `data.groups`
(which electronics domains to include), `data.draws`, `working_unit`.

## Growing the case one component at a time

`tools/make_skeleton.py` **merges**: values already filled in are kept, rows for
new resources are added blank, rows whose resource no longer exists are dropped.
So the intended way to work is:

```python
groups = ('Wiring',)              # one domain, eight rows
groups = ('Wiring', 'Motors')     # re-run the skeleton, fill the new rows
groups = ()                       # all of them
```

## Layout

```
00..04, 99      the stages, in the order you run them
src/            the model
tests/          five suites, 68 checks
tools/          compare_engines.py, plot_structure.py
data_folder/    bev_electronics (the real case), reference/ (test fixtures)
documentation/  start at documentation/README.md
```

## Two things that are easy to misread

**Rows are nested.** A row at element depth is *part of* its material row, not
an addition to it, so summing the `Value` column counts the same mass up to four
times. Any aggregate must pick one depth first.

**Most of the mass is unspecified.** On the real data, 71% of the motors is not
in any tracked element. `src/rest.py` derives a `rest` child for it and treats
it as unrecovered, which makes every recovery figure a **lower bound**.

## Setup

No conda. See [documentation/SETUP.md](documentation/SETUP.md).

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```
