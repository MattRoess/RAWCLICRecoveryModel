# The battery cases — one per chemistry, each with its own roads

Written 2026-10-08. The decisions behind it are DECISIONS.md 42–52.

**In one paragraph.** The battery is no longer one case with one blended set of
recovery rates. A recycler treats a lithium iron phosphate cell, a
nickel-manganese-cobalt cell and a sodium-ion cell differently, so there is a
case for each chemistry family, and each has the roads that apply to it:
hydrometallurgy, direct recycling, pyrometallurgy, mechanical treatment. Each
case holds **three sets of coefficients** (`own`, `BAU`, `REC`) in one workbook,
and one setting, `run.variants` in `src/params_schema.py`, picks which set runs.
Sodium has two ways of being treated, and the same setting picks between them.

**You press Run on `04_batteries.py`.** It runs the five cases, each in the
scenarios its chemistry exists in (12 passes), once for the choice in
`run.variants`. Nothing here needs a command line. **It needs the per-chemistry
export of the upstream stage (§12), which was written on 2026-10-08; without it
stage 01 says so and stops.**

| § | |
|---|---|
| 1 | the five cases |
| 2 | what each case does with a collected pack |
| 3 | the three sets, and how to choose |
| 4 | where every number comes from, and which are placeholders |
| 5 | independence, and the one place it is not |
| 6 | the sodium cells |
| 7 | time, and things that may surprise |
| 8 | a chemistry nobody has written a treatment for |
| 9 | what is not modelled, on purpose |
| 10 | what the paper's supplement does that you should know |
| 11 | findings about the existing case `data/battery` |
| 12 | the upstream export these cases read |
| 13 | combining the cases, and what the figures draw |
| 14 | changing or rebuilding a case; the checks and the tests |

---

## 1. The five cases

| case folder | upstream chemistry folder(s) it reads | roads of its cells | runs scenarios |
|---|---|---|---|
| `data/battery_lfp` | `LFP` | hydrometallurgy, **direct recycling** | S1, S2, S3 |
| `data/battery_lmfp` | `LMFP` | hydrometallurgy, **direct recycling** | S1, S2, S3 |
| `data/battery_nmc_high` | `NMC_high` | hydrometallurgy, **pyrometallurgy** | S1, S2, S3 |
| `data/battery_sodium` | `Na_ion_layered` + `Na_ion_prussian_white`, **added per draw** | **mechanical treatment** (the paper's); direct recycling is prepared | S2, S3 |
| `data/battery_solid_state` | `solid_state` | none: frame, enclosure, cables and thermal conductor only; the cell is **handed on** | S3 |

Rows in each workbook's `TCs` sheet (the same number in `TCs_improved`): 142, 150,
167, 151 and 38. Rows marked PLACEHOLDER: 20, 22, 20, 28 and 0 (§4).

`data/battery` — the one blended case — is **untouched**. It is no longer in the
study, it still runs if you name it in `run.data_folder`, and it reads the old
summed export (§12).

**Why NMC is `NMC_high` only.** The stock-and-flow model produces no medium or
low nickel grade. If one ever appears in the input, the run stops and says so (§8).

**Why LFP and LMFP are two cases.** The report gives them different rates
(Table 2), and the paper gives neither, so the case is where the difference lives.

**Why sodium is one case over two upstream folders.** Layered oxide and Prussian
white are treated the same way; a case is a treatment, not a composition.
`chemistries = Na_ion_layered; Na_ion_prussian_white` in its source table makes
the case read both and add them, array by array.

**Why solid-state is a case at all.** Nothing is known of its cell, so nothing is
claimed about it. Its pack parts are real and go through dismantling and the
shredder like everyone else's. Its cell, collectors included, goes to
`F_cells_handed`, a handoff, and is reported as "handed on, not counted here". It
is there so that the day its chemistry is described there is a case to write it
into.

---

## 2. What each case does with a collected pack

Every case starts with the user's own steps, copied from `data/battery`:

```
F_collected --dismantling--> F_pack_housing   (frame, enclosure, thermal conductor, cables, terminals)
                         \-> F_cells          (cathode, anode, electrolyte, separator, casing, collectors)
                         \-> F_loss_dismantling

F_pack_housing --general_recycling (shredder)--> F_fealloy_general, F_alalloy_general, F_cu_general
                                             \-> F_loss_general
```

The cells then split, by component, between the case's roads:

```
LFP, LMFP
F_cells --route_split--> F_cells_hydro  --cell_recycling--> F_li, F_fe_cell, F_p, F_mn (LMFP), F_graphite,
                     |                                      F_cu_cell, F_al_cell, F_loss_cell
                     \-> F_cells_direct --direct_recycling--> F_cathode_direct, F_graphite_direct,
                     |                                         F_cu_direct, F_al_direct, F_loss_direct
                     \-> F_loss_unresolved                   (casing, separator: §9)

NMC_high
F_cells --route_split--> F_cells_hydro  --cell_recycling--> F_li, F_ni, F_co, F_mn, F_graphite,
                     |                                      F_cu_cell, F_al_cell, F_loss_cell
                     \-> F_cells_pyro   --pyrometallurgy---> F_li_pyro, F_ni_pyro, F_co_pyro, F_mn_pyro,
                     |                                       F_cu_pyro, F_al_pyro, F_loss_pyro
                     \-> F_loss_unresolved

sodium
F_cells --route_split--> F_cells_mech   --mechanical_treatment--> F_black_mass (HANDED ON), F_al_mech,
                     |                                            F_loss_mech
                     \-> F_cells_direct --direct_recycling------> F_cathode_direct, F_graphite_direct,
                     |                                            F_al_direct, F_loss_direct
                     \-> F_loss_unresolved                       (casing, separator, unitemised)

solid-state
F_collected --dismantling--> F_pack_housing (as above), F_cells_handed (HANDED ON), F_loss_dismantling
```

A flow is in a case's `processes` sheet if any version of the case can put mass in
it, so a REC-only flow such as `F_mn_pyro` is there although the BAU set never
fills it. The sheet is read off the coefficient rows, so it cannot disagree with them.

`F_loss_unresolved` is made by a process called `unresolved_material`
(technology `not itemised upstream`). The loss figure names each wedge by the
process that makes the loss flow, and the structure figure labels each edge with
it, so the name is what the reader sees: "lost in unresolved material".

**Every road is one step.** The paper's routes are chains — pyrolysis, then
mechanical treatment, then hydrometallurgy, then slag treatment. What this model
needs of a chain is its overall recovery per element, which the paper states, so a
road is one process carrying that number. The chain stays in the paper.

**The pretreatment stays `dismantling`**, and the mechanical loss of each road
stays inside that road's coefficients. The report's Table 2 rates are net of
pretreatment; a separate mechanical multiplier ahead of them would count the same
loss twice.

**Oxygen is never counted** as recovered or handed on, in any road. Silicon, and
sodium and phosphorus in a sodium electrolyte, go the same way where no road
recovers them: to the road's loss flow.

---

## 3. The three sets, and how to choose

`TCs` and `TCs_improved` carry a column `variant`. Blank means *the row is the same
in every set*, and it is written once. Otherwise the cell names the version the row
belongs to:

```
tc_set=BAU                         used when tc_set is BAU
tc_set=own|REC                     used when tc_set is own or REC
sodium_route=mechanical_direct     used only for that sodium route
```

Several clauses are separated by `;` and a row is used only if **all** of them
match. **One setting chooses**, in `src/params_schema.py`:

```python
variants: str = 'tc_set=own; sodium_route=mechanical'
```

| `tc_set` | what runs |
|---|---|
| `own` | **your numbers.** The hydrometallurgical road is the report's Table 2, for the chemistry of the case; the shredder, the dismantling, the collectors, the graphite and the electrolyte lithium are your rows in `data/battery`. Where you have **no** number — the split between roads, pyrometallurgy, direct recycling, the sodium treatment — the **paper's REC** is used, and the `variant` cells say `own\|REC` so it can be seen and changed. |
| `BAU` | the paper's business-as-usual numbers, everywhere the paper has them. The dismantling and the shredder stay yours. |
| `REC` | the paper's recovery scenario — EU targets met on time — everywhere the paper has them. |

| `sodium_route` | what runs |
|---|---|
| `mechanical` | every sodium cell goes the mechanical way, as in the paper. **The default.** Its black mass is handed on. |
| `mechanical_direct` | a share of the sodium cells goes to direct recycling instead. **Prepared, not the paper's**: nothing has been published for it, so the share and the direct numbers are placeholders (§4). |

A case that offers none of these (the electronics, the traction motor) ignores the
setting. A case that offers a choice the setting does not make is **refused**,
naming what it offers; nothing is defaulted silently. A choice the case does not
offer is refused too.

**Where the results go.** The choice is part of the path, like the scenario, so a
REC run never replaces an `own` run:

```
figures/battery_lfp/S1/own/                    data/battery_lfp/output_data/S1/own/
figures/battery_sodium/S2/own_mechanical/      data/battery_sodium/output_data/S2/own_mechanical/
```

The folder reads in the order the setting is written. A case that offers no choice
has no such folder, so the paths of the other cases are what they were.

**Every version is checked, not only the selected one.** Stage 01 closes each
version's coefficients to 1 in every year it will be solved, and checks that nothing
strands, for every choice the case offers; it prints a `VERSIONS` section. A version
nobody has selected is read the day somebody does.

**What the sets differ by** — the hydrometallurgical road, mode at 2030, 2050 and
2060 (2050 is on the model's straight line between the two tables):

| case | resource | `own` (Table 2 / your rows) | `BAU` (paper) | `REC` (paper) |
|---|---|---|---|---|
| LFP | Li | 0.85 / 0.92 / 0.96 | 0.82 / 0.87 / 0.90 | 0.89 / 0.91 / 0.92 |
| LFP | Fe | 0.85 / 0.91 / 0.94 | **0** | 0.17 / 0.50 / 0.67 |
| LFP | P | 0.80 / 0.89 / 0.93 | **0** | 0.17 / 0.50 / 0.67 |
| LMFP | Li | 0.82 / 0.91 / 0.95 | 0.82 / 0.87 / 0.90 | 0.89 / 0.91 / 0.92 |
| LMFP | Mn | 0.80 / 0.89 / 0.93 | 0.83 / 0.88 / 0.91 | 0.17 / 0.50 / 0.67 |
| LMFP | Fe | 0.78 / 0.87 / 0.91 | **0** | 0.17 / 0.50 / 0.67 |
| LMFP | P | 0.75 / 0.85 / 0.90 | **0** | 0.17 / 0.50 / 0.67 |
| NMC | Li | 0.85 / 0.93 / 0.97 | 0.82 / 0.87 / 0.90 | 0.89 / 0.91 / 0.92 |
| NMC | Ni | 0.95 / 0.98 / 0.99 | 0.89 / 0.94 / 0.97 | 0.95 / 0.95 / 0.95 |
| NMC | Co | 0.95 / 0.98 / 0.99 | 0.80 / 0.93 / 1.00 | 0.95 / 0.95 / 0.95 |
| NMC | Mn | 0.90 / 0.95 / 0.98 | 0.83 / 0.88 / 0.91 | 0.17 / 0.50 / 0.67 |
| all three | graphite | 0.50 / 0.63 / 0.70 | 0.18 / 0.46 / 0.59 | 0.79 / 0.92 / 0.99 |
| all three | Cu foil | 0.85 / 0.90 / 0.92 | 0.90 flat | 0.95 flat |
| all three | Al foil | 0.72 / 0.81 / 0.85 | 0.84 flat | 0.95 flat |

Read from it: **the sets are a real switch** for iron, phosphorus, manganese and
graphite. In the paper's BAU hydrometallurgical route iron and phosphorus are not
recovered at all, and in REC they follow a slow series that reaches 0.50 in 2050;
your Table 2 has them at 0.85–0.94. **The paper's rates are the same for LFP, LMFP
and NMC**, because its coefficients carry no chemistry, while Table 2's differ.
**After 2050 the paper says nothing**, and the line goes on (§7).

---

## 4. Where every number comes from

Every row has a `source` cell. There are four kinds of source and a row never mixes
them:

| source | what it is | in the cell |
|---|---|---|
| **the user** | Table 2 of the report, and the user's own rows in `data/battery` | `the report, Table 2, NMC Co, 2030: min/mode/max 90%/95%/99%.` · `data/battery (the user): <their own text>` |
| **the paper** | Maisel et al., *Waste Management* 227 (2027) 115873, and its supplement `1-s2.0-S0956053X2600543X-mmc1.xlsx` | `Maisel et al. 2027 (Waste Management 227, 115873) supplement, LIB_Route2 BAU, Cobalt (CAM): estimated overall rate 0.81 in 2032 and 0.931 in 2050 (min 0.5184/0.5958, max 1/1); DERIVED: the straight line through them, read at 2030.` |
| **DERIVED** | arithmetic on the paper's numbers, stated in the row | as above |
| **PLACEHOLDER** | **(Claude, not data)** — a number nobody has; you replace it | `PLACEHOLDER (Claude, not data): …` |

### How the paper's numbers become the two tables

For each route and element the paper gives the **estimated overall recovery** (the
product of its step coefficients) at 2025, at 2032 and at 2050 — REC also at 2028 —
with a minimum and a maximum. The model has two tables, 2030 and 2060, and a
straight line between them. So each of minimum, mode and maximum is fitted by **the
straight line through the paper's 2032 and 2050 values, read off at 2030 and at
2060**, and held inside [0, 1]:

* **from 2032 to 2050 the model reproduces the paper**, because the paper itself
  runs straight between its anchor years (its annual series are linear between
  anchors, and the last value is held to 2050, its §2.6). The largest difference
  there is 0.4 points, in the BAU Route 3 rows for nickel, iron, manganese and
  phosphorus, where the paper's own estimate dips between 2025 and 2032;
* **2030 differs** where the paper bends before 2032: by 2.1 points on average over
  the 50 paper rows the cases use, and by at most 13.9 (REC Route 1 lithium, +13.9;
  REC Route 2 graphite, +13.8; BAU Route 1 lithium, +8.1). BAU Route 2 graphite
  shows −21 only because the paper's 2025 anchor for it, 0.85, is the share that
  reaches the black mass and not recovered graphite (§10); that anchor is not used;
* **after 2050 the paper says nothing**; the line goes on, with the user's
  `improvement_after_end = continue`, and is held at 0 and 1.

Putting the paper's 2050 value straight into the 2060 table instead would be off at
2050 by 2.6 points on average and by up to 11.7 (the iron, phosphorus and manganese
series of REC, which climb from 0.20 to 0.50). That is why it is not done.

The paper's **estimated** rates are used, not its target series (`BAU_targets`,
`REC_targets`). Those are what the regulation requires — lithium 50 % by 2027, 80 %
by 2031 — and the estimates are built to meet or exceed them. REC Route 2 lithium:
estimate 0.784 (2025), 0.874 (2028), 0.892 (2032), 0.912 (2050); the target in 2028
is 0.50.

### The route shares

The paper gives one mix for **all** lithium-ion batteries over five routes
(`Structural_Decomposition`). This model needs, for each case, what share of the
cells takes the second road:

* LFP, LMFP: direct recycling `= Route 5 / (Route 2 + Route 5)`
* NMC: pyrometallurgy `= (Route 1 + Route 4) / (Route 1 + Route 2 + Route 4)`

**Route 3 — mechanical only, black mass exported, 79.9 % of the mix in 2024 — is
left out**, because it is not one of the three main processes, and the shares are
renormalised over what is left.

| share of the cells | paper 2032 | paper 2050 | table 2030 | table 2060 |
|---|---:|---:|---:|---:|
| direct, LFP and LMFP, BAU | 0.19 % | 0.57 % | 0.15 % | 0.78 % |
| direct, LFP and LMFP, REC | 1.39 % | 8.32 % | 0.62 % | 12.16 % |
| pyro, NMC, BAU | 3.71 % | 1.97 % | 3.90 % | 1.01 % |
| pyro, NMC, REC | 2.30 % | 1.53 % | 2.38 % | 1.10 % |

`own` uses the REC shares. The paper gives the shares and **no range**; each share
carries ±50 % of itself as a placeholder, and the other road's row is its mirror
(1 − max, 1 − mode, 1 − min).

**Route 4** (pyrolysis, mechanical treatment, pyrometallurgy, hydrometallurgy)
shares the pyrometallurgical step, so its share is added to Route 1's, and the road
uses **Route 1's rates for all of it**. Route 4's own rates are close for lithium,
nickel, cobalt, copper and manganese — within a point at 2050 — and differ for the
aluminium foil (Route 1: 0 in BAU and 0.2 → 0.5 in REC; Route 4: 0.84 and 0.95).
They are not used: one road is one set of rates. Pyrometallurgy is 1–4 % of the NMC
cells, so the effect on a total is small.

### The placeholders

Each is named in its row's `source` cell; filter that column for `PLACEHOLDER`.

| where | what | the placeholder |
|---|---|---|
| every route split | the **range** on the share (the paper has none) | ±50 % of the share |
| sodium, `mechanical_direct` | the share of cells that go to direct recycling | 0.5, range 0.25–0.75 |
| sodium, direct road | every recovery number: the paper's direct route is LFP only | Route 5's lithium row (the regeneration rate of a cathode) for every cathode element of a sodium cell — Na, Fe, Mn, Ni, Cu, C; its graphite row for the anode carbon; its aluminium-foil row for both foils |
| LMFP, direct road | manganese: Route 5 has no row for it | Route 5's iron row |

Counted in the 2030 table, all versions together: LFP 20 rows (the ranges of its
splits), LMFP 22, NMC_high 20, sodium 28 (10 for the share, 18 for the direct road),
solid-state 0.

Four things look like placeholders and are not. **What a road does not recover** is
written once as "not recovered on this road, so all of it is lost" (DEFINITIONAL,
loss = 1): oxygen, silicon, graphite in pyrometallurgy, the electrolyte's lithium on
the direct road, sodium and phosphorus in a sodium electrolyte. **The unresolved
components** (§9) go to loss the same way. **`batteryCellUnitemised`**, new upstream
and without a row of yours, is dismantled with the cell components' numbers, and the
row says DERIVED: an assumption, yours to confirm. And **where a chemistry is not in
the paper — sodium — the closest paper row is used** and the row says so in words
("The paper names no row for Na in a cathode; the black-mass rate of its lithium row
is used").

### What is copied from the user's case, not recomputed

Dismantling (0.95 | 0.98 | 1.00, in both tables), the shredder rows for the pack
components, and — under `own` — the hydrometallurgy rows for the graphite, the
electrolyte lithium and the two collectors are copied from `data/battery` at build
time, with their own `source` text. A copy, not a link: editing `data/battery` later
does not move them.

The loss row that goes with a Table 2 recovery row is **the user's own** when
`data/battery` already has that same recovered row (lithium for LFP; lithium, nickel,
cobalt and manganese for NMC; phosphorus 2030 for LFP), and the **mirror**
`(1 − max, 1 − mode, 1 − min)` where it does not.

---

## 5. Independence, and the one place it is not

**Inside a group** — everything one resource turns into at one step — every row has a
range of its own. The rows are drawn **independently**, each on its own random
stream (measured on `data/battery`'s lithium pair with the real sampler: correlation
−0.006 before the constraint), and the group is then **conditioned** on adding up to 1
(`monte_carlo.sum_to_one = 'condition'`, `src/sampling.py`: the widest row is forced to
1 − the others, weighted by its own triangular density, and resampled). Afterwards a
two-row group is a mirror image of itself (−1.000): that is what "adds up to 100 %"
means, and it holds for every recovered/lost pair in the model, including yours. The
ranges are all used; conditioning narrows them (that lithium row's 95 % interval is
0.814–0.921 against 0.732–0.941 for its own triangular). The code refuses a group in
which only one row has a range.

So nothing is computed here as "1 minus the other". The route split's two rows each
carry a range of their own and are conditioned like every other pair.

**Between cases** it is **not** independent where the coefficient has the same name.
A coefficient's random stream is chosen by its identity — resource, from, to — and
not by its case. Two cases with the same coefficient draw the **same** random number
(measured: correlation 1.000, the arrays equal). So the lithium recovery of LFP and
of NMC move together in a draw, and the battery total, added per draw in
`05_combine_cases.py`, is wider than independent cases would give. **This is a known
simplification, left in on purpose**: a stream name per case would switch independence
on with one line in each source table, and was left out as complicated. The existing
cases are unaffected: no two of them share names.

The route split draws **per component**: each component's pair of rows is its own
coefficient with its own stream, so within one draw the cathode of a case can go one
way and its anode the other. A recycler routes a whole cell, so this is a
simplification too. The shares are small except for the sodium placeholder, so the
effect on a total is small; the expected value is unaffected.

---

## 6. The sodium cells

**`sodium_route = mechanical`** — as in the paper, which describes only mechanical
treatment for sodium-ion. The cell is shredded; the aluminium foils are recovered
(the paper's `Aluminium (CC)` row: 0.84 in BAU, 0.95 in REC); the **black mass** — the
cathode and anode material — is **handed on**: it leaves for processing elsewhere and
is counted neither as recovered nor as lost. That is what the paper's Route 3 does
with it: it is largely exported (the paper estimates 80–90 %). Its rates are the
paper's Route 3 rows: nickel, manganese and iron each their own; sodium, copper and
carbon in a cathode the lithium row (0.90 → 0.95 in BAU, 0.97 in REC); the anode
carbon the graphite row.

**`sodium_route = mechanical_direct`** — prepared for the day direct recycling of
sodium-ion cells is described. Half of the cells (range 0.25–0.75) take the direct
road, whose numbers are LFP's carried over. **Every number on this road is a
placeholder**, and the default does not use it.

Sodium has aluminium foils on **both** sides (no copper foil). Its cathodes carry
sodium, nickel, manganese, iron and copper (layered oxide) or iron, sodium and carbon
(Prussian white); the electrolyte carries sodium and phosphorus. Nitrogen and
fluorine are not exported by upstream (`battery_elements_not_of_interest`).

---

## 7. Time, and things that may surprise

**How the coefficients change over the years.** Every coefficient is flat at its
`TCs` value until 2030, runs on a straight line to its `TCs_improved` value in 2060,
and then continues on the same slope to 2070, held at 0 and 1 (your
`improvement_start`, `improvement_end` and `improvement_after_end = continue`). The
years 2020 and 2025 therefore use the 2030 numbers. One draw is one set of random
numbers in all years: a coefficient that is high in 2030 is high in 2060.

**Is the two-table structure enough?** For the hydrometallurgical road, yes. The 2050
column of Table 2 lies 0.3–1.7 points above the straight line between its own 2030 and
2060 values (mean 1.0), and the paper ends in 2050. A third table for 2050 would touch
`case_tables.ramp`, the validators, the tools and the workbook layout for that
difference, and is not recommended. The structure is kept (DECISIONS 27 and 28 of the
coefficient table, and 52).

**BAU passes REC for nickel from 2054 and for cobalt from 2053**, because BAU is still
climbing at 2050 and REC has stopped at its ceiling. This is the straight line going
on, not a finding.

**REC manganese is below BAU manganese** on the hydrometallurgical road (0.50 against
0.88 at 2050). That is how the paper's route sheets read: REC replaces manganese's
hydro rate with the series it gives iron, phosphorus and aluminium (0.114, 0.204,
0.504 in 2028, 2032, 2050). It is reproduced as stated and not corrected.

**The sets differ most where the paper is silent.** For anything the paper does not
regulate — iron, phosphorus, manganese, graphite — its numbers are what its authors
needed for their targets, not what a recycler achieves.

**Mass handed on is neither recovered nor lost.** "Lost inside recycling" is
`collected − recovered − handed on`, and handed-on mass has its own line in the
figures ("handed on, not counted here"). A case with no handoff flow has none and its
figures are what they were — checked byte for byte on the existing figures.

---

## 8. A chemistry nobody has written a treatment for

If the upstream export holds a chemistry folder that **no case names**, every run that
reads the export **stops** and says which:

```
<export> holds 1 chemistry folder(s) that no case treats: NMC_low.
Their mass would be left out of every total without a word. Each needs a treatment:
  1. copy the case of the nearest chemistry and give it that chemistry's coefficients,
  2. name the folder in its source table:  chemistries = NMC_low
  3. list the case in the study (`run.data_folder`, and `combine.cases` for the combined figures).
Cases looked at: … (the cases that name a chemistry, and which)
```

A chemistry named by **two** cases is refused as well ("so its mass would be counted
2 times. Name it in one."). A case that names a chemistry the export does not have is
a warning (a stale name, or an export not yet re-run). The check reads every case
folder beside the one being run, so running a single case still sees what the others
treat. It is `check_chemistries` in `src/upstream.py` and runs in stages 01, 02, 03
and in 05.

To add a chemistry: copy the nearest case folder, edit its `source` table
(`chemistries`), its `processes` and its coefficients, and add the folder to
`STUDIES['batteries']`.

---

## 9. Not modelled, on purpose

* **The cell casing and the separator** have no element upstream, so in the
  composition each is a leaf: no `rest` is derived under it, and a coefficient keyed at
  `rest` **never fires** — the component's whole mass would arrive at a road and stop,
  with no error and nothing in any total. In the new cases such a component leaves at
  the split, once, to `F_loss_unresolved`, and appears in no road at all; so does the
  sodium cells' `batteryCellUnitemised`. **The paper's casing coefficients cannot be
  used** for the same reason: they are per element and the casing has none.
* **Electrolyte.** Lithium in the electrolyte is given the cathode lithium row, as
  the user does in `data/battery`. On the direct road it is not recovered.
* **Graphite in pyrometallurgy** is not recovered (the paper: 0). **Silicon** never is.
* **Solid-state** cells are handed on whole, collectors included, until their
  chemistry is described. Its cathode and anode active material have no mass upstream
  (a zero there means "not described"), so stage 01 warns that their rows never fire:
  `2 component(s) in 6 row(s) are not in this case's composition, so those rows never
  fire: anodeActiveMaterial, cathodeActiveMaterial`. That warning is expected; the rows
  are there for the day they do.
  In S3 it has nothing before 2040, so those years are zero in its figures (a case with an
  empty year used to stop the Monte Carlo: DEFECTS 3.26).
* **Warnings that are expected** in the other cases: the `rest` rows of components
  that have no `rest` ("so those rows never fire: rest") and, in the version check,
  "improvement extrapolated past 2060; N coefficient(s) reached 0 or 1 and were held
  there from 2065".

---

## 10. What the paper's supplement does that you should know

Used as published, anomalies included. Found while reading it:

* **REC manganese below BAU manganese** in Route 2 (§7).
* **The REC sheets say "BAU Target"** in the header of their target blocks (2028,
  2032, 2050); they are REC's.
* **`LIB_Route5 …` sheets are headed "LIB Recycling Route 1"**; they are Route 5.
* **Graphite in BAU Route 2 in 2025** shows an estimated recovery of 0.85. That is the
  share that reaches the black mass, with the hydro step at zero; it is not recovered
  graphite. It does not matter here: only 2032 and 2050 are used.
* **Route 3 nickel, iron, manganese and phosphorus** dip from 0.8525 (2025) to 0.85
  (2032) in BAU, against the paper's statement that coefficients are non-decreasing.
* **REC Route 1 aluminium foil** carries the same 0.2 → 0.5 series as manganese, where
  Route 4 has 0.95.
* **A row with estimate 0 still prints a minimum and maximum** (0.72–1.0, the
  mechanical step's). Read as a point mass at zero.
* **A maximum above 1** (1.005) is clipped.
* **The paper's regulatory-target sheets are not its estimates** (§4).
* **The paper's direct route is LFP only, pilot scale (TRL 4)**, with the same numbers
  in BAU and REC (0.8874 → 0.8973 for lithium, iron, phosphorus and graphite; 1.0 for
  the foils, with ranges down to 0.57 and 0.80).
* **The paper's coefficients carry no chemistry**: "NMC", "LFP" and "LMFP" appear in
  none of its 2,746 coefficients.

---

## 11. Findings about the existing case, `data/battery` (the user's data — reported, not changed)

1. **The casing and the separator lose their mass silently** (§9). In the first
   scenario, S1, in 2070, the mean of 200 draws: the casing (83.4 kt) and the separator
   (41.2 kt) arrive at `F_cells` and stop, 3.5 % of the 3,597 kt that reach it. Of the
   5,687 kt collected, 2.1 % reach no terminal flow (97.9 % do). Stage 01 says, in a
   warning, that `rest` rows "never fire"; stage 03 prints `STRANDED UNSPECIFIED MASS`
   when mass stops in an intermediate flow. The fix is to leave them to the split, as the
   new cases do, or to key their loss rows at the material layer into a loss flow of
   their own.
2. **Scenarios S2 and S3 are refused** by the case's own input check: six resources
   arrive with no coefficient — sodium and phosphorus in the electrolyte; carbon, copper
   and sodium in the cathode; and `batteryCellUnitemised`. The new sodium case is where
   they belong.
3. **The cathode rates are a blend of chemistries.** Against Table 2: nickel and cobalt
   are NMC's exactly; manganese is NMC's (0.75 / 0.90 / 0.99 → 0.92 / 0.98 / 0.99);
   lithium is LFP's at both anchors and NMC's at 2030 only (2060: 0.85 / 0.96 / 0.99
   here, 0.88 / 0.97 / 0.99 for NMC); phosphorus at 2030 and iron at 2060 are LFP's
   exactly. **Two rows match neither chemistry**: iron in 2030 (0.58 / 0.80 / 0.96 here;
   LFP 0.60 / 0.85 / 0.98, LMFP 0.55 / 0.78 / 0.95) and phosphorus in 2060 (0.77 / 0.94 /
   0.99 here; LFP 0.78 / 0.93 / 0.99). For LMFP the blend is wrong throughout: manganese
   0.90 here against 0.80 in Table 2, iron 0.80 against 0.78, phosphorus 0.80 against
   0.75 (2030 modes). That blend is why there are separate cases.

---

## 12. The upstream export these cases read

```
data/processed/battery_recovery_draws_by_chemistry/<chemistry>/<scenario>/<flow>/
    years.npy
    __component____<component>.npy         (draws, 11 years)  kt
    <element>__<component>.npy             (draws, 11 years)  kt
```

written by `code/04_04_batteries.py` in RAWCLICStockAndFlow: one folder per
chemistry, the same files the summed export had, for the years 2020–2070 in steps of
five. A chemistry is written only for the scenarios it has a share in: S1 has no
sodium or solid-state folder, S2 no solid-state folder, so a full run leaves 14
chemistry × scenario folders.

It **replaces** the summed export `battery_recovery_draws/`, which only `data/battery`
read. Nothing writes the old folder any more; the old 2.8 GB folder stays on disk until
you delete it, and `data/battery` runs from it until then (its `upstream_dir` names
it).

**Status: run on 2026-10-08, and checked.** It took about six hours (not the "an hour or
more" of the older notes) and left 9.4 GB: exactly the 14 chemistry × scenario folders, each with
`inflow`, `outflow` and `collected`, every array (200000, 11), float32, finite, none negative, no N
or F, and `batteryCellUnitemised` only in the sodium cells. Against `battery_draws/` of the same
run the export agrees **draw by draw to 3.4e-7**, components and elements, in 21 of the 42
folder-flow pairs. Before the run, the old and the new export code had been run on the same small
synthetic inputs and compared (90 arrays, worst relative error 2e-7). The upstream
`documentation/HANDOVER.md` of 2026-10-08 has the details.

**Two runs of 04_04 did not give the same draws** (`hash(segment)` seeded the pack size and
voltage; DEFECTS 3.27), so the new export agrees with the old summed one of 10-07 in its means
(to four decimals) and not draw by draw. **Fixed in the code on 2026-10-09** (`zlib.crc32`); the
export on disk is from the unfixed code, and the fix shows with the next run of 04_04, which he
will do later. Pack size and voltage are also coupled draw by draw, and so are the capacity
growth and the voltage band (DEFECTS 3.28): not fixed, his decision, best made before that run.

If the export is not there, stage 01 says so:

```
The export ../RAWCLICStockAndFlow/data/processed/battery_recovery_draws_by_chemistry does not exist.
It is `upstream_dir` (data/processed/battery_recovery_draws_by_chemistry) in the source table of
…/data/battery_lfp, below the upstream root. The upstream stage that writes it has not been run
since the export became one folder per chemistry, or `upstream_dir` is wrong.
```

A chemistry folder that appears in the export and that no case names stops the run (§8).

---

## 13. Combining the cases, and what the figures draw

**`combine.cases` and the frozen copper figures are unchanged.** `05_combine_cases.py`
still combines the wiring, the boards, `data/battery` and the traction motor, and
`figures/combined/copper_combined.png` and `copper_streams.png` are as they were. To
put the five chemistry cases in instead of `data/battery`, list them in `combine.cases`;
05 adds them per draw, and the combined figures then go to a folder named after the
choice in `run.variants`, so they cannot replace the frozen ones. Two things to know
first:

* **A case that has no draws for the scenario stops 05.** Each scenario has its own
  set: S1 has LFP, LMFP and NMC_high; S2 those and sodium; S3 all five. Listing the
  sodium or the solid-state case for a scenario that lacks it raises "No upstream draws
  at …", naming the case. So list the cases the scenario has. A silent skip would also
  hide a mistyped scenario, so it was not built; say if you want it with a printed note.
* **The chemistry cases are fully correlated where they share a coefficient name** (§5).

**What the figures draw.** `figures.resources` for the batteries study is
`('Cu', 'Ni', 'Co', 'Li')`, so a case is drawn for those of them it has: LFP and LMFP
for copper and lithium, sodium for copper and nickel. Iron, phosphorus, manganese,
aluminium, carbon (graphite) and sodium are solved and are in the summary, but not
drawn; add them to `figures.resources` if you want their figures.

---

## 14. Changing or rebuilding a case; the checks and the tests

The workbooks are **input**, yours to edit — replace a placeholder, revise a number,
add a row. `tools/build_battery_cases.py` writes them once and **refuses to overwrite**
one that exists, so an edit is never lost; to rebuild one, move or remove its folder
yourself. It reads the paper, the report's Table 2 and `data/battery`, checks that every
version of every case closes to 1, and writes. The five workbooks in the repository are
exactly what it writes.

**To replace a placeholder:** change the numbers in the row of **both** sheets, `TCs`
and `TCs_improved`, in every version that has the row, and replace
`PLACEHOLDER (Claude, not data)` in the `source` cell by where the number comes from.
Keep the group closed: the rows of one resource at one step must add up to 1 at the
mode, and stage 01 refuses what does not.

* A row that belongs to one version carries a `variant`; a row that is the same
  everywhere has it blank. A coefficient that differs by version appears once per
  version, in both sheets; the two sheets must name the same coefficients.
* `tools/make_skeleton.py` **refuses** a sheet with a `variant` column: it matches rows
  by identity, and two versions of one coefficient share one.
* Checks: stage 01 (the case and all of its versions), `99_check_all.py` (the code).
  In the tests: `test_every_battery_case_closes_in_every_version`,
  `test_the_battery_cases_conserve_mass_in_every_version`,
  `test_a_component_with_no_elements_leaves_at_the_split_not_in_a_road`, and in
  `tests/test_generality.py` the tests of the chemistries and of handed-on mass.
* Verified here, outside the repository: all five cases in every version they offer
  ran end to end on a stand-in export built from the real composition files
  (validate, every-choice check, Monte Carlo at a few hundred draws), and the mass
  balance closed to exactly 100.00 % in every version -- **and on the real export**
  (2026-10-08), one case at a time at 300 draws. The real export reads 99.99 to 100.57 %,
  not 100.00 %: the composition files' own sampling noise, which a stand-in made without it
  did not have, and which shrinks with the draws (the elements of a component add up to at
  most 0.03 % above the component at 200,000). The real export also found what the stand-in
  could not: a year in which a case has no mass at all stopped the Monte Carlo
  (solid-state before 2040; DEFECTS 3.26, fixed).
