# Reading 04_01 (car composition) — what it would take

Investigated 2026-08-21 against the real upstream repository.

**BUILT 2026-08-21.** Everything below except the coefficients themselves is
now implemented; see the corrections at the end for the two places this
estimate was wrong. A made-up TC table on the real structure sits in
`data_folder/carcomposition_mockup/`, and how a case is configured is in
[CASES.md](CASES.md).

## Short answer

**About a day**, most of it upstream and one 04_01 run. Nothing here is hard;
there is one genuine generalisation needed in this project's reader, one
modelling decision that is yours, and one thing upstream that is already built
and simply switched off.

It is materially easier than 04_02 was, for three reasons: the draws are
already computed, the switch to persist them already exists, and the layer
mapping is a better fit than the electronics one.

## What 04_01 actually is

Stage 04 part 1 of RAWCLICStockAndFlow: vehicle counts from stage 03 multiplied
by component–material composition, giving material mass by year, flow,
drivetrain and material, with Monte Carlo uncertainty.

It has been run — `04_01_mass_by_year_BAU.pkl` and `04_01_scalar_mass_BAU.pkl`
are on disk, written 2026-08-21. Its own header says the rewrite is still in
progress, so treat its numbers as provisional.

Its output table is:

```
region  flow  drivetrain  segment  year  components  material
        vehicle_count  composition_value  mass
```

Scale, on the 2040 collected flow:

| | |
|---|---|
| drivetrains | 5 — BEV, Diesel, HEV, PHEV, Petrol |
| segments | 12 |
| components | 20 (`elvBIW`, `elvBattery`, `elvChassis`, …) |
| materials | 28 (`calAHSS`, `calAl_5xxx`, `battery`, `cableLike`, …) |
| (component, material) pairs present | 101 |
| (drivetrain, component, material) | 476 |
| years | 96, annual, 1975–2070 |

Collected mass in 2040: BEV 7.56 Mt, Petrol 2.83, Diesel 1.57, HEV 1.29,
PHEV 1.10. (Corrected: this said kt, a factor of 1,000 out. The measured export
gives BEV 7,067 kt for 2040, which is 3.44 M vehicles at about 2,050 kg each.)

## The layer mapping — better than electronics

04_01 fills three layers naturally, where 04_02 needed a placeholder:

| Layer | 04_02 electronics | **04_01 car composition** |
|---|---|---|
| 1 product | BEV | **drivetrain** — BEV, Diesel, … |
| 2 component | domain (Wiring, Motors…) | **component** — elvBIW, elvBattery… |
| 3 material | *placeholder, meaningless* | **material** — calAHSS, battery… |
| 4 element | element | *not available* |

So the material layer stops being a placeholder and becomes real. What is
missing instead is the element layer: 04_01 does not resolve materials into
elements. A recovery result from it is therefore per material, not per element —
which is the right granularity for steel, aluminium and plastics, and the wrong
one for the critical raw materials 04_02 covers. **The two are complementary,
not alternatives.**

## The four pieces of work

### 1. Upstream export — the biggest piece, but it already exists

04_01 computes per-draw mass arrays and already has a switch for keeping them:

```python
persist_mc_mass_draws: bool = False        # src/params_schema.py:1673
```

Its own comment explains why it is off:

> NOTHING IN THE PIPELINE READS THEM BACK … They were persisted for a consumer
> that was never built … be aware it is tens of GB per run at 200,000 draws.

**This project is that consumer.** But turning the flag on is not the answer —
tens of gigabytes of pickles is the same problem 04_02 had, and it has the same
solution: export a **year slice** in the `.npy` layout this project reads,
rather than the whole thing. One year of 476 combinations at 200,000 draws is
about 0.4 GB.

That is roughly forty lines in 04_01, mirroring `_write_element_draws` and the
export block already added there for 04_02, plus two settings for which years
and where. Half a day including one run.

### 2. One generalisation here — which layer the child sits at

`src/upstream.py` reads files named `<child>__<parent>.npy` and puts the child
at **Layer 4**, with a placeholder material at Layer 3. For 04_01 the child is a
material and belongs at **Layer 3**, with Layer 4 unused.

That is one new setting — `data.child_layer`, `'element'` or `'material'` —
and the branch that inserts the placeholder becoming conditional. Perhaps
twenty lines. `tests/test_generality.py` already covers the existing path; it
would gain a case for the other one.

### 3. Segment — SETTLED 2026-08-26: keep summing

04_01 carries 12 segments and this model has no layer for them. The question
was posed here as a trade-off between accuracy and twelve times the runs. It is
not one, and the reason is worth stating because it disposes of the question
rather than deferring it again.

**The model is exactly linear in the inflow.** Solving the whole inflow, against
solving 30% and 70% separately and adding, agrees to **4.7e-17** across every
row of the solution. So

    solve(sum over segments)  ==  sum over segments of solve(segment)

identically, provided the coefficients are the same for every segment. Running
per segment cannot make the total more accurate. It would cost twelve runs and
an upstream re-export — the current export sums segments before writing — to
arrive back at a number already in hand.

So the real question was never accuracy. It is two other questions:

1. **Do you want per-segment RESULTS** — "what share of recovery comes from
   large cars?" Running per segment is the only way to get that, and it is a
   reporting decision.
2. **Is the coefficient right for the actual mix?** This is the real exposure,
   and running per segment does not fix it unless per-segment coefficients
   exist to go with it.

#### The mix, and what it exposes

From `03_01_flowdriven.py:164`, matching what the draws themselves give:

| family | share of collected BEVs |
|---|---|
| A–F | 49.3% |
| JA–JF | 50.7% |

`JC` alone is 25.1%, the largest single segment. Because the split is nearly
even, a single coefficient measured on one family inherits about half of any
real difference between them:

| if the families differ by | bias on that coefficient |
|---|---|
| 5 points | 2.5% |
| 10 points | 5.1% |
| 20 points | 10.1% |

#### One thing nobody has written down

**What the `J` prefix means is not recorded anywhere upstream.** `SEGMENT_ORDER`
lists `A`–`F` then `JA`–`JF`; `segment_map` is described only as "Vehicle-segment
letter code -> composition dataset code"; and `00_parameters.py`,
`03_01_flowdriven.py` and `04_01_carcomposition.py` define it nowhere. The
standard EU scheme would make `J` sport-utility, but that is a guess and it is
half the fleet, so it decides which literature half the coefficients should come
from. Worth asking whoever built 03_01.

**Decision: sum over segments.** Revisit only if per-segment reporting is wanted,
or a segment-specific coefficient turns up. The third option in the original
list — segment as Layer 1, drivetrain folded into the flow — is not revisited:
it was only ever right if segment mattered more than drivetrain, and nothing
here suggests it does.

### 4. The TC table

Generated from the composition, as for the electronics case. Sizes, if the
network below is used:

| | rows |
|---|---|
| component-keyed — (drivetrain, component) × 3 destinations | 228 |
| material-keyed — (component, material) × 2 destinations × 2 processes | 404 |
| **total** | **632**, covering 278 resources |

Note what keeps this small: a material coefficient is keyed on
`(component, material)`, **not** on the drivetrain. The same steel in the same
body shell goes through the same shredder whatever drove the car, so one row
serves all five drivetrains. Only the dismantling rows are per drivetrain,
which is right — a battery is pulled from a BEV, a catalytic converter from a
Petrol.

## The made-up table

`data_folder/carcomposition_mockup/` holds a complete, self-consistent table on
the **real** component and material names, with **invented** coefficients. Every
one of its 278 resources sums to 1.

Network:

```
ELV_collected → ELV_dismantled        dismantling, component-keyed
              → ELV_shredded          (the residual: what stays in the hulk)
              → ELV_loss_dismantling  loss
ELV_dismantled → ELV_reused           reuse_sorting, material-keyed, recovered
               → ELV_loss_dismantled  loss
ELV_shredded   → ELV_ferrous          separation, material-keyed, recovered
               → ELV_loss_ASR         loss
```

The invented assumptions, all marked `MADE UP (Claude)` in the `source` column:

- batteries and catalytic converters are pulled at 0.95, powertrains 0.80,
  transmissions 0.70, wheels 0.60, drivelines 0.45, everything else 0.15 —
  accessibility and value, not measurement;
- `cal*` steels and aluminium separate well (0.85 dismantled, 0.90 shredded),
  battery material badly once shredded (0.10), cable-like material in between.

**It will not run yet** — it needs the export from piece 1 to supply the inflow
and composition. It exists to show the shape and to size the work.

## What is not covered

- **Elements.** 04_01 stops at material. Copper as `cableLike` is not copper as
  `Cu`, and the two cannot be added together.
- **The rewrite.** 04_01's header says it is still being rebuilt, and records a
  correction where a `direct=True` lookup was silently returning zero vehicles.
  Its numbers should be treated as provisional until its author says otherwise.
- **04_03 and 04_04** (traction motors, batteries) export nothing at all. Each
  would need its own export step, and possibly its own reader if the shape
  differs.

## Corrections, after building it

Two things above were wrong, and both changed the work.

### 04_01's draws are per PERIOD, not per year

This document assumed an annual axis to slice, as 04_02 has. It does not have
one. `combine_flow_and_composition_draws` returns one `(n_draws,)` array per
`(drivetrain, segment, component, material)` **cumulative over a period**, and
`monte_carlo.output_periods` defaults to a single entry covering 1975–2070.

So an annual axis is something you ask for:

```python
output_periods = [(y, y) for y in (2030, 2035, 2040, 2045, 2050)]
```

The export writes only single-year periods, and skips a multi-year one with a
note rather than filing it under a year label it does not mean.

### Five drivetrains are one case, not five

The estimate said "one generalisation — which layer the child sits at". There
were two. The other is that the recovery model had one product at Layer 1,
where 04_01 has five drivetrains, and they belong in one case: the same
coefficient table serves all of them, with only the dismantling rows keyed per
drivetrain. A case can now name several products and read one upstream folder
each — see [CASES.md](CASES.md).

The cost is memory, and it is not small: five drivetrains over 20 components
and 101 material pairs is 605 composition rows per year against the electronics
case's 70 for five, which is 29 GB at 200,000 draws over five years. The budget
guard refuses that before allocating. Years and draws are the levers.

### A single-year period did not need 03_02 re-run

`mc_stage03_02_summary` holds only cumulative distributions for the periods
03_02 itself was run with, so a single-year period appeared to require re-running
03_02 — hours of simulation, and it rewrites the 2.6 GB `bev_draws` the
electronics case depends on.

It did not. `data/processed/bev_draws/<scenario>/BEV_<segment>_collected.npy` is
already `(n_draws, n_years)` per-year vehicle counts, written by 03_02 for stage
04_02. 04_01 now reads those for a single-year period — the same quantity the
histogram bootstrap approximates, only exact. **03_02 is unmodified.**

Only BEV has such an export, so a single-year run covers BEV and skips the other
four as before. Widening 03_02's BEV-only filter is a one-line change for
whenever it next runs.

### The result, BEV 2040, 50,000 draws

7,067 kt collected. Mass balance closes to 7e-11. 5,599 kt recovered across 16
materials — 79.2% — with the `rest` convention making that a lower bound.

| material | mean kt | 95% interval | spread |
|---|---|---|---|
| battery | 1,014 | 841 – 1,180 | 33% |
| calmildSteel | 898 | 619 – 1,186 | 63% |
| calHSS | 733 | 507 – 966 | 63% |

Running every coefficient at its mode overstates the mean by a median 8.3%.

**These numbers are illustrations, not results** — the coefficients are invented.

### What is still open

- **The coefficients.** The mockup's numbers are invented and marked as such.
  Capping their maxima (below) fixed their arithmetic, not their truth.
- **The other four drivetrains**, which need 03_02's per-year export widened.

### The invented ranges were internally impossible

17 of 278 resources had `value_max` summing past 1 — e.g. a battery "up to 100%
dismantled" *and* "up to 18% lost", which forces the residual to −18%. The Monte
Carlo caught it as 153,135 negative residuals and a negative 2.5th percentile on
`ELV_loss_ASR`. Capped so each resource's maxima sum to at most 1, preserving the
modes and the relative widths; the affected rows say so in `source`.
