# Cases — one model, one case per upstream stage

Written 2026-08-21.

## The rule

**There is one model.** `src/` is shared by every case and knows nothing about
vehicles, electronics or panels. What differs between 04_01, 04_02 and whatever
04_03 and 04_04 turn out to be is only two things:

1. **the data preparation** — where the draws are, and what their layers mean;
2. **the parameters** — the flow network and the coefficients.

Both live in the case folder. Nothing in `src/params_schema.py` changes when
you switch, and that is deliberate: a setting you have to edit to run the other
study is a setting somebody forgets, and then one stage's draws get read with
another stage's coefficients and no check anywhere notices.

## A case folder

```
data_folder/<case>/input_data/
    source.csv      where the numbers come from, and how they map to layers
    processes.csv   the flow network
    TCs.csv         the coefficients
```

Running it is naming it:

```bash
./.venv/bin/python 01_check_inputs.py    data_folder/carcomposition_mockup
./.venv/bin/python 02_run_model.py       data_folder/carcomposition_mockup
./.venv/bin/python 03_run_monte_carlo.py data_folder/carcomposition_mockup
```

With no argument each uses `run.data_folder`, so the everyday case still runs
by typing nothing.

## source.csv

Two columns, `key` and `value`.

| key | example | what it is |
|---|---|---|
| `upstream_dir` | `data/processed/element_draws` | under `data.upstream_root` |
| `flow` | `{product}_collected` | which upstream folder(s) to read |
| `product` | `BEV;Diesel;Petrol` | Layer 1; one name or several |
| `inflow_flow_id` | `F_collected` | must match the first `Input_FlowID` in `processes.csv` |
| `child_layer` | `element` | `element` or `material` — see below |
| `group_marker` | `__domain__` | how a group's own mass is named upstream |
| `material_suffix` | `_mixed` | the placeholder material, where one is needed |
| `groups` | `Wiring;Motors` | blank means all of them |

A key that is **present** settles the matter, blank or not — blank `groups`
means every group. A key that is **absent** falls back to the matching `data.*`
setting, which is what lets an older case with no `source.csv` keep working.

## Several products in one case

04_01 covers five drivetrains, and they are **one study**: the same shredder,
the same coefficient table, and only the dismantling rows keyed per drivetrain —
a battery is pulled from a BEV, a catalytic converter from a Petrol, and both
rows live in the same file. So one case names all five:

```
product   BEV;Diesel;HEV;PHEV;Petrol
flow      {product}_collected
```

`{product}` is substituted per product, so the case reads `BEV_collected`,
`Diesel_collected` and so on — the folders 04_01's export writes.

**Each product is its own whole.** A component's share is a share of its own
drivetrain, never of all five together, and the inflow is one row per product
per year. Pooling them would still balance and still plot; every share would
just be wrong by the ratio of one drivetrain's mass to the fleet's. Nothing
downstream could catch that, which is why `tests/test_generality.py` checks the
shares rather than the total, and writes its two products a factor apart so
that reading one folder twice shows up as a wrong number.

Naming several products with a `flow` that has no `{product}` in it is refused
rather than run.

## Memory — the cost of a wide case

The Monte Carlo array is `result rows × draws × 8 bytes`, and result rows are
roughly nine times composition rows. So:

| case | composition rows | result rows | at 200,000 draws |
|---|---|---|---|
| 04_02 electronics, 2 groups, 5 years | 70 | 600 | 0.96 GB |
| 04_01, 5 drivetrains, 1 year | 605 | ~3,600 | 5.8 GB |
| 04_01, 5 drivetrains, 5 years | 3,025 | ~18,000 | 29 GB |

`monte_carlo.memory_budget_gb` is 4 GB and `plan()` refuses **before**
allocating, so an oversized run stops with an arithmetic explanation rather
than with the machine swapping. Chunking bounds the working memory, not the
result — the result array has to fit — so the two levers are `run.years` and
`data.draws`. One year at 50,000 draws fits.

Widening a case is therefore not free, and this is the argument for keeping
04_02's four electronics domains as separate cases rather than one.

## `child_layer` — the one that matters

Upstream files are all named `<child>__<parent>.npy`, but what the child *is*
differs by stage, and the filename cannot tell you:

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| `child_layer` | `element` | `material` |
| Layer 1 | BEV | drivetrain — BEV, Diesel, … |
| Layer 2 | domain — Wiring, Motors | component — elvBIW, elvBattery |
| Layer 3 | *placeholder, meaningless* | **material** — calAHSS, battery |
| Layer 4 | element — Cu, Nd | *unused* |

Getting this wrong does not fail. It silently files materials where elements
belong, and every coefficient keyed at the element layer then matches nothing —
the model still runs and still balances, and the answer is wrong. Hence a named
setting rather than a guess, and `tests/test_generality.py` runs one synthetic
fixture through **both** shapes to keep the material path honest.

## Adding 04_03 or 04_04

1. Upstream: a year-sliced `.npy` export, mirroring the one in
   `04_02_BEVelectronics.py`. Whole-run pickles are tens of GB; a year slice is
   under one.
2. Here: `mkdir data_folder/<case>/input_data`, write the three files, run it.

No code change, unless the new stage's children sit at a layer neither
`element` nor `material` describes — in which case `src/source.py` gains a
third value and `src/upstream.py` a third branch, and the test above gains a
third case before either of them is written.

## What is deliberately NOT per case

`data.upstream_root`, `data.draws`, `run.years`, `run.scenario`,
`run.working_unit`. Where the sibling repository is checked out, and how much of
it to read, are facts about this machine and this run — not about the study. A
case that pinned them would fight the next machine it was opened on.
