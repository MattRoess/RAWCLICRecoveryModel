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
    case.xlsx       one workbook, three sheets
        source      where the numbers come from, and how they map to layers
        processes   the flow network
        TCs         the coefficients

A case may keep the three as separate CSVs instead -- `source.csv`,
`processes.csv`, `TCs.csv` -- and the reference fixtures do. Not both for the
same table: two files of one name with different contents is how someone edits
one while the model reads the other.
```

Running it is naming it:

```bash
./.venv/bin/python 01_check_inputs.py    data_folder/carcomposition_mockup
./.venv/bin/python 02_run_model.py       data_folder/carcomposition_mockup
./.venv/bin/python 03_run_monte_carlo.py data_folder/carcomposition_mockup
```

With no argument each uses `run.data_folder`, so the everyday case still runs
by typing nothing.

## Running either one — the whole thing

Switching between 04_01 and 04_02 is naming the folder. **Nothing in
`src/params_schema.py` changes.**

### 04_02 — BEV electronics

```bash
./.venv/bin/python 01_check_inputs.py    data_folder/bev_electronics
./.venv/bin/python 02_run_model.py       data_folder/bev_electronics
./.venv/bin/python 03_run_monte_carlo.py data_folder/bev_electronics
```

### 04_01 — car composition

```bash
./.venv/bin/python 01_check_inputs.py    data_folder/carcomposition_mockup
./.venv/bin/python 02_run_model.py       data_folder/carcomposition_mockup
./.venv/bin/python 03_run_monte_carlo.py data_folder/carcomposition_mockup
```

With no folder argument each uses `run.data_folder`, so the everyday case runs
by typing nothing.

Everything lands in `<case>/output_data/` — `recovery_results.xlsx` is the one
to open — and figures in `figures/`, named after the case.

## Filling in the coefficients

The coefficient table is the one thing in a case a person writes by hand, and
it is the largest — 52 rows for the electronics case, 632 for car composition.
So it is kept in a workbook rather than a CSV, and the generator writes into
that workbook rather than beside it.

**You never type a flow name, a layer or a resource key.** `make_skeleton.py`
writes every row that needs a number, with all six identifying columns already
filled, and puts a dropdown on each of them. The lists come from the case
itself: flow names from `processes`, resource keys from what the upstream draws
actually contain. A name that cannot be chosen cannot be mistyped, which
removes the one class of input error the loader can only catch after the fact.

What you fill in is `value`, and `value_min` / `value_max` beside it, while you
are still thinking about the range. The `source` column is there as you work,
so provenance gets written down rather than reconstructed later.

**Add your own columns if they help.** A `notes` column recording where a
number came from survives regeneration — the merge carries through any column
the generator does not know about, rather than dropping it.

**The dropdown lists live on a hidden `_lists` sheet.** They are ranges rather
than typed-in lists because Excel silently discards an inline list over 255
characters: a real element list passes that without a warning, and the dropdown
would simply not be there.

### Growing a case one domain at a time

`make_skeleton.py` **merges**. A value already filled in is never overwritten —
not even by the `rest` rows the script fills in itself, since those may have
been changed deliberately. So the intended way to work is to narrow `groups`,
run it, fill the handful of rows that appear, widen, and run it again.

### Seeing what changed

`git diff` on a workbook says nothing. Every run therefore writes
`output_data/<case>/TCs_used.csv`, which is tracked: plain text, and the table
*after* rest-derivation, precedence and wildcard expansion. So it shows what was
applied rather than what was typed, and a result that moves can be traced to the
coefficient that moved with it.

## The two TC tools

Both write that case's coefficients -- the `TCs` sheet, or `TCs.csv` for a
case kept as files -- from its own composition, so the
table covers exactly what the case contains: no row that can never fire, and no
resource left without coefficients.

| case | tool | what it writes |
|---|---|---|
| 04_02 electronics | `tools/make_skeleton.py` | every row that needs a number, **blank**, for you to fill in |
| 04_01 car composition | `tools/make_carcomposition_tcs.py` | the same rows **already filled with invented numbers** |

```bash
./.venv/bin/python tools/make_skeleton.py data_folder/bev_electronics
```

```bash
./.venv/bin/python tools/make_carcomposition_tcs.py data_folder/carcomposition_mockup
```

**`make_skeleton.py` merges.** Re-run it whenever the case grows: values you
have already filled in are kept, rows for new resources are added blank, and
rows whose resource no longer exists are dropped. Nothing you typed is ever
overwritten. That is what makes it safe to work one domain at a time — narrow
`groups` in `source`, run it, fill the handful of rows, widen, repeat.

**`make_carcomposition_tcs.py` overwrites**, deliberately: everything it writes
is invented and marked `MADE UP (Claude)` in the `source` column, so there is
nothing of yours to protect. 278 resources is not fillable by hand.

**It refuses once it is not true.** Before generating anything it reads the
existing table and looks at the `source` column: every row it wrote says either
`MADE UP (Claude) ...` or `derived: ...`, so a row saying anything else came
from a person. Find one and the run stops, names the rows, and points at
`make_skeleton.py`, which merges. `--overwrite` forces it, for when the table
really should be thrown away and rebuilt.

That check replaced a sentence telling you to stop running it — a poor guard,
read once, months before the run that would have destroyed the work.

## The `source` table

Two columns, `key` and `value`. Nine keys, and **every one of them differs
between the two cases** — which is the point: this sheet is the only place the
two studies differ, so everything that makes them different has to be in it.

**Both cases spell out all nine.** Neither leans on a `data.*` setting for any
of them, so either sheet works as a template: copy it, change the values, and
you have never had to know which keys have defaults. The fallback described at
the end of this section still exists, but nothing shipped here uses it.

| key | electronics (04_02) | car composition (04_01) | what it decides |
|---|---|---|---|
| `upstream_dir` | `data/processed/element_draws` | `data/processed/carcomposition_draws` | which export to read, under `data.upstream_root` |
| `product` | `BEV` | `BEV;Diesel;HEV;PHEV;Petrol` | Layer 1. One name or several |
| `flow` | `collected` | `{product}_collected` | the upstream folder. `{product}` is substituted, so 04_01 reads five |
| `inflow_flow_id` | `F_collected` | `ELV_collected` | the flow the inflow enters as |
| `child_layer` | `element` | `material` | **the one that matters** — see below |
| `group_marker` | `__domain__` | `__component__` | the separator in the upstream `.npy` filenames |
| `material_suffix` | `_mixed` | *(blank)* | the placeholder material, where one is needed |
| `groups` | `Wiring;Motors` | *(blank)* | which groups to include; blank means all |
| `draws` | `200000` | `50000` | how wide this case's arrays are |

### What each one accepts

| key | allowed | refused on load? |
|---|---|---|
| `child_layer` | `element` or `material`, nothing else | **yes** |
| `draws` | a whole number above zero | **yes** |
| `product` | one name, or several separated by `;` | **yes** — blank is refused |
| `flow` | a folder name; must contain `{product}` when `product` names more than one | **yes** |
| `upstream_dir` | any path under `data.upstream_root` | no — fails when the folder is not found |
| `inflow_flow_id` | any flow id, but it must match the first `Input_FlowID` in `processes` | no |
| `group_marker` | any string | no — **a wrong one silently matches no files** |
| `material_suffix` | any string, or blank | no |
| `groups` | `;`-separated, blank for all | no |

Four of the nine are checked when the case loads. The rest fail later, or not
at all: `group_marker` is the one to be careful with, because getting it wrong
finds nothing rather than finding the wrong thing.

`child_layer` is a **dropdown** in the sheet — click the cell beside it and
Excel offers `element` and `material`. That is not extra safety, since a wrong
value is refused on load anyway; it is so the sheet says what the choices are,
which a rejection message only does after a run has failed. Any key with a
fixed set of values gets this automatically: the set lives in `VOCABULARY` in
`src/source.py`, and the dropdown is reapplied whenever the sheet is written,
so it cannot be lost by a rewrite.

### Present, blank, and absent are three different answers

A key that is **present settles the matter even when blank** — blank `groups`
means *every* group, blank `material_suffix` means *no* placeholder is wanted.
Only an **absent** key falls back to the matching `data.*` setting, which is
what lets an older case with no `source` table keep working. `child_layer`
absent defaults to `element`, the 04_02 shape.

So deleting a row and emptying a row do different things, and only deleting it
means "use the default".

The simplest way to never think about this again is the one both cases now
follow: **write all nine keys down**. Then present-or-absent never arises, and
a blank cell means what it looks like it means. `draws` used to be absent from
the electronics case, inheriting 200,000 from `data.draws` — which happened to
be right, but only by luck: as `src/source.py` puts it, how wide a case's
arrays are is a fact about the case, not about the machine, and one shared
setting can only ever be right for one of two cases.

## The `processes` table

One row per arrow in the flow network: this input flow becomes that output
flow, by this process. Seven columns.

| column | what it decides |
|---|---|
| `Input_FlowID` | the flow going in |
| `Output_FlowID` | the flow coming out |
| `process` | what happens — dismantling, shredding, refining. Labelling only |
| `technology` | how it happens — manual, hammer_mill, pyro. Labelling only |
| `keyed_at` | the layer this step's coefficients are written at — `component`, `material` or `element` |
| `role` | what the output flow **means** when recovery is totalled |

`process` and `technology` are descriptive: they name the step for figures and
for reading, and nothing computes from them.

### `role` — what a flow counts as

Four values, and only one of them is counted as recovery:

| role | counted as recovered? | meaning |
|---|---|---|
| `recovered` | **yes** | an endpoint material comes back from |
| `loss` | no | mass leaving the system |
| `handoff` | no | an endpoint, but handed to a **different** model — recovered elsewhere, not here |
| `intermediate` | no | not an endpoint; feeds the next process |

The one that earns its keep is `handoff`. The role used to be guessed from the
flow's *name*, and that guess counted `F_separated_electronics` as recovered
because the string `loss` does not appear in it. That flow is material handed
to a separate recovery model. It carried no mass at the time, so nothing looked
wrong — and it would have inflated the recovery figure, silently, the moment
boards and sensors were included again. `role` exists so the meaning is stated
rather than read out of the spelling.

`intermediate` marks a flow that is consumed further on. Those are excluded
from the total anyway, by not being terminal, so the value is a statement of
intent rather than something the sum depends on.

Both `role` and `keyed_at` are **dropdowns** in the sheet — click the cell and
Excel offers the legal values. The vocabularies live in `VOCABULARY` in
`src/rest.py`, and are reapplied whenever the sheet is written, so they cannot
be lost by a rewrite. `make_skeleton.py` derives each layer's parent from the
same list rather than keeping its own, so the layers it accepts and the layers
the sheet offers cannot drift apart.

### There is no default, on purpose

A row whose `role` is blank, misspelled, or missing stops the run and names the
step. It is not guessed.

That is a deliberate reversal. The table used to carry a second column,
`is_loss`, answering the same question with one bit, and `role` fell back to it
— then to `recovered` when neither was readable. So `recoverd` for `recovered`
did not fail; it added that flow's mass to the recovery figure and said
nothing. A column that exists to stop mass being counted by accident cannot
have a default that counts mass by accident.

`is_loss` was removed in the same change. It was exactly `role == 'loss'`, so
it carried no information of its own — only the chance of contradicting the
column beside it. `tools/make_skeleton.py`, which counts each flow's loss
destinations to decide whether a `rest` row can be filled in with 1.0
automatically, now counts them from `role`.

One thing that count gets right for free: a `handoff` is **not** a loss.
Material going to another model has left this system without being lost by it,
so it does not become somewhere the unspecified remainder can be sent.

## The `TCs` table — `value`, `value_min`, `value_max`, `is_residual`

`value` is the coefficient; `value_min` and `value_max` make it a triangular
distribution for the Monte Carlo. `is_residual` marks the one row per group
that is **derived rather than measured**.

### What a group is, and why one row is derived

A group is everything one resource turns into: aluminium as found in motors,
leaving `F_dismantled`, across every destination it reaches. It must sum to
**exactly 1** — the aluminium goes somewhere, all of it.

Independent draws do not sum to 1. Something has to give, and `is_residual`
says which row. On every draw that row is computed as `1 − (the rest of its
group)`.

**A residual row's `value_min` and `value_max` must be blank**, and a range
written there is now refused rather than ignored. It used to be read and
discarded silently, which is worse: nothing said your measurement had been
dropped.

### The derived row is still a distribution

This is the part that surprises people. The residual is not a fixed number —
it inherits its spread from the rows it is derived against:

| row | written | sampled p5 | p95 |
|---|---|---|---|
| `Motors_mixed Al → F_loss_refining` | 0.90 | 0.7533 | 0.9455 |
| `BEV Wiring → F_shredded` | 0.65 | 0.4995 | 0.7427 |

For a group with exactly **two** destinations there is no freedom at all:
`x₂ = 1 − x₁` identically, so the derived distribution is the measured one
reflected, and nothing is lost. Checked over 200,000 draws, the largest
difference between the derived row and `1 − the measured row` was `0.0`.

Twenty-two of the electronics case's twenty-four groups are of this kind.

### When there is no residual: two rules, and you choose

A group with no row marked is settled by `monte_carlo.sum_to_one`:

| setting | what it does | what it costs |
|---|---|---|
| `normalise` *(default)* | divide the group by its own sum | every marginal shifts off the triangular it was drawn from, by an amount nothing reports |
| `condition` | keep every row's own measurement | draws become slightly correlated — which the constraint makes unavoidable |

**`condition` is the one to use once every row carries a range.** It is what
sum-to-1 means probabilistically: the product of the measured densities,
restricted to the draws that do sum to 1. In practice — draw every row from
its own range; take the widest as determined by the rest, so the group sums to
1 exactly; weight each draw by that row's own density at the value it was
forced to take; resample so the draws come out equally weighted again.

Which row is taken as determined does not change the answer — the target is
the same product either way — so there is none of the arbitrariness that
choosing an `is_residual` row involves.

It was checked against brute force: drawing every row from its own range and
keeping only the draws that sum to 1 gives the same distribution, and that
test is in `tests/test_sampling.py`. Rejection is simply far slower — it
throws away 95% of the draws to get there.

On the electronics case, giving the loss row of one group its own measurement:

| | p5 | p50 | p95 |
|---|---|---|---|
| `F_refined`, residual rule (loss measurement unused) | 0.0537 | 0.1326 | 0.2470 |
| `F_refined`, **conditioned** | 0.0647 | 0.1223 | 0.2177 |

The conditioned answer is **narrower**, because two measurements constrain the
value more than one does. That is the point, and it is also the warning: your
reported spreads will be tighter than the ranges you typed, and correctly so.

### The effective sample size

Conditioning reports how much of the sample survived the weighting. Ranges
that agree keep most of it — 89% in the example above. Ranges that cannot all
be true collapse it, and stage 03 says so rather than absorbing the
contradiction quietly. That is the property neither `normalise` nor the
residual rule has.

### The `SUM TO 1` section of `01_check_inputs.py`

A constrained group's modes sum to 1 by construction. Its **means need not**: a
triangular's mean is `(min + mode + max) / 3`, so a range whose mode sits
off-centre has a mean away from its mode. Where the two disagree, enforcing the
constraint has to move the answer away from what is written in the sheet.

`01_check_inputs.py` reports that gap per group, as `offset` — how many
standard deviations of the group's own independent sum separate 1 from where
that sum actually lands:

```
SUM TO 1 -- do the measured ranges agree with the constraint?
  24 constrained groups
  offset from 1, in standard deviations of the group's own sum: median 0.73, max 1.02
  14 group(s) beyond 0.5 sd -- drawn independently these do NOT
  average to 1, so the constraint moves them away from the values written:
    Motors_mixed Nd -> F_dismantled: independent sum averages 1.1333, +1.02 sd from 1
```

**This is not an error.** It is the reason a run at the modes and a run of the
full distributions give different answers — the same difference
`03_run_monte_carlo.py` reports at the end of every run. Near zero means the
ranges already agree with the constraint and enforcing it changes little.
Large means the measured distributions and sum-to-1 pull in different
directions, and whatever rule is applied has to override something.

The electronics case sits at a median of 0.73 sd, driven by the rare-earth
rows, whose ranges run far above their modes.

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
