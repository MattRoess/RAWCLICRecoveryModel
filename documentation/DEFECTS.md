# Defects and engine divergences

Found 2026-08-14; §2.5–2.7, §3.7 and §3.8 added 2026-08-17, and all of §2
resolved the same day. Each item has a measurement and a reproduction.

**Everything in §2 is now closed** — fixed in an engine, or settled as a rule
the loader enforces. There is no longer an input on which the two engines
disagree. The entries are kept with their measurements because each is a shape
of mistake that can recur, and because the reasoning behind a rule matters more
than the rule. §3 is still open.

Reproduce any case with:

```bash
./.venv/bin/python tools/compare_engines.py data/reference/defect_cases/<case>
```

Every §2 item has a committed data folder. `basic_test`, for comparison, is
**180 rows** and a naive row total of **7514.4575** on both engines — that
total sums nested rows at every depth, so it is a comparison figure and not a
mass.

---

## 1. Fixed — the code did not run at all

All three were fixed in commit `ee3fc6b`. Recorded because each was silent or
misleading, and because the third one silently corrupted performance rather
than results.

### 1.1 `run_model.py` failed at import

`from pandas.errors import SettingWithCopyWarning` — removed in pandas 3. The
entry point raised `ImportError` before doing anything. `data_folder` also
pointed at `data/feb_2026_sensitivity`, which does not exist in the
repository.

### 1.2 `RecoveryModelLA` failed at construction

Used `DataFrame._append`, removed in pandas 3 (`AttributeError`). It was also
called in a row-by-row loop in two places, making frame construction quadratic.
Replaced with building each frame once from a list of rows.

### 1.3 Unmatched TCs were never zero-filled — 300,000x intermediate blow-up

`process_outflow["TC"].fillna(0, inplace=True)` is a **silent no-op** under
copy-on-write: it modifies a temporary column object and returns None, leaving
the real TC column as `NaN`.

`Value *= NaN` gives `NaN`, and `NaN != 0` is `True`, so the `Value != 0` filter
pruned nothing. Every one of the 16 layer-pair combinations survived as NaN
rows and fed into the next process. Measured on the 44-row `basic_test`:

```
process rows in=   44  out=     704   NaN=    676
process rows in=  704  out=   11264   NaN=  11250
process rows in=11264  out=  180224   NaN= 180212
process rows in=191376 out= 3062016   NaN=3062006
```

16x growth per process stage. The **final answer was still correct**, purely
because `groupby.sum()` skips NaN — which is why this was never noticed.

After the fix, the same last step produces **10 rows instead of 3,062,016**,
with identical results. On a larger synthetic case it is an 11x speedup and
turns the memory curve from explosive into flat.

> This is the clearest argument for the regression test proposed in HANDOVER.md:
> a defect this severe was invisible because the output stayed right.

---

## 2. The two engines implement different semantics

**This is the most important area.** The engines agree on `basic_test` only
because it exercises none of these cases. Do not treat their agreement as
general validation.

All seven were closed on 2026-08-17. §2.1, §2.2 and §2.4 were plain bugs.
§2.3 and §2.5 were unspecified semantics — neither engine's behaviour was
documented as correct, so each needed a decision first, and both decisions are
written down with the option not taken. §2.6 and §2.7 are refused at load.

### 2.1 Composition `Stock/ID` is ignored by the optimized engine — FIXED

**Reproduce:** `data/reference/defect_cases/composition_stock_id`

The user guide defines `Stock/ID` as "Stock/Flow ID for the flow the material
is contained in". `RecoveryModelLA` honours it.
`RecoveryModelOptimized` drops the column (`recovery_model_optimized.py:210`)
and merges composition on `Layer 1` alone, so **a composition defined for one
flow is applied to every flow sharing that parent**.

Two inflows, FA composed of C1 and FB composed of C2:

| Row | LA | Optimized |
|---|---|---|
| FA / P1 (product) | 100 | 100 |
| FA / P1 / C1 | 100 | 100 |
| FA / P1 / C2 | — | **100** |
| FB / P1 / C1 | — | **100** |
| FB / P1 / C2 | 100 | 100 |

The component layer of FA now sums to 200 against a product layer of 100. Mass
is invented, silently. The optimized engine is the one `stages/02_run_model.py` uses.

**Severity: high.** Any real dataset where two flows carry the same product with
different compositions was wrong, in the direction of overestimating recovery.

**FIXED 2026-08-17.** `create_initial_flows` now carries `Stock/ID` into the
join keys, renamed to `Stock/Flow ID`, at all three composition depths. The two
engines agree exactly on this case: largest difference **0.00e+00**, down from
100. `basic_test` is unmoved at 8.88e-16, so the fix changes only the datasets
that were wrong.

The companion check is in `src/validate_inputs.py`: an inflow whose (flow,
product) pair has no composition is now an error, because after this fix such a
row silently stops at product depth instead of being wrongly expanded.

### 2.2 The documented `P*` wildcard silently produces nothing — FIXED

**Reproduce:** `data/reference/defect_cases/wildcard_star`

The user guide documents an asterisk for "the same TC for all products in a
layer". `fill_star_values` implements it — in `RecoveryModelLA` only
(`recovery_model_LA.py:256`). The optimized engine treats `P*` as a literal
key, matches nothing, and **emits no output flow at all**:

| Row | LA | Optimized |
|---|---|---|
| F2 / P1 / C1 | 50 | **0 (absent)** |
| F2 / P2 / C1 | 50 | **0 (absent)** |

No error, no warning — an entire flow is missing from the results.

**Severity: high**, because it failed toward under-reporting with no signal, and
because the feature is documented so a user had every reason to use it.

**FIXED 2026-08-17.** `RecoveryModelOptimized.expand_wildcards`, called from
`read_input_data` once the layer names are normalised, turns any key containing
`*` into one row per resource at that layer. The engines agree exactly on this
case: **0.00e+00**, down from 50, with both now producing F2/P1/C1 = 50 and
F2/P2/C1 = 50.

The asterisk expands to *every* resource at the layer, so `P*` and `*` mean the
same thing — the layer column already says which set is meant. That is how
`RecoveryModelLA.fill_star_values` has always read it, and matching it is what
makes the two agree.

### 2.3 Overlapping TC rules — RESOLVED

**Reproduce:** `data/reference/defect_cases/overlapping_rules`

A TC row names what it is about on its input side. A row naming a product is
specific; a row naming only a component applies to that component in *every*
product, the specific one included. Write both and one material is described
twice:

```
row 2:  product   BEV      ->  component Harness   0.80
row 3:  component Harness  ->  component Harness   0.20
```

Both cover the harness inside a BEV. The table never said which governs, and
each engine guessed differently and silently.

20,000 t of BEVs at 4% harness and 100,000 t of hybrids at 3%, so 800 t of BEV
harness and 3,000 t of hybrid harness:

| | BEV harness | hybrid harness |
|---|---|---|
| LA, before | 160 t (used 0.20) | 600 t |
| optimized, before | **800 t** (added to 1.00) | 600 t |
| both, now | **640 t** (0.80 governs) | 600 t |

The optimized engine's 800 t is 800 of 800 — the entire harness recovered and
zero dismantling loss, purely because two rows existed. A third overlapping row
would have "recovered" more than went in.

**RESOLVED 2026-08-17: a row that names the parent beats a row that does not.**

Specificity is the number of layers a row pins down. A blank key, or one
containing `*`, pins nothing — those are the "applies to everything"
conventions the user guide already defines. Two rows pinning the same number of
layers and still overlapping are a real ambiguity and are refused, rather than
resolved by a tie-break nobody chose.

`src/tc_precedence.py` does this on the table, **before either engine sees it**,
and rewrites the general row as one row per product it still governs. So the
engines are handed identical explicit rows and cannot drift apart again — which
is why this fixed both at once rather than needing two changes.

#### It says what it did

The rule is only half of it. The other half is that nothing is silent:

```
TC RESOLUTION -- 1 place(s) where more than one rule applied
  Harness in BEV               row 2 governs (0.8), row 3 overridden (0.2)
  The rule: a row naming the parent beats a row that does not.

UNDER-SPECIFIED -- covered by a rule that names no parent
  Harness in HEV  -- 0.2 from row 3, which names no product
  Not a problem in itself, but a product added later inherits these silently.
```

The under-specified list matters as much as the overrides: it shows which
materials are running on a general rate rather than one of their own, so a
vehicle type added next year cannot quietly pick up a number nobody chose for
it.

#### Why not simply forbid the overlap

That was the first proposal, and `DESIGN_tc_table.md` R4 still records it. It
was rejected because the "applies to everything" row is a documented feature —
the `P*` wildcard of §2.2 — and because with a dozen vehicle types sharing one
rate, forbidding it means writing a dozen rows to say one thing. Reporting what
was applied gives the brevity without the silence.

### 2.4 Year, scenario and location matching differ — FIXED

**Reproduce:** `data/reference/defect_cases/scenario_prefix`

`RecoveryModelLA` selected rows by **substring**: `str(year_target) in
year_data`, and `.str.contains()` for scenario and additionalSpecification —
with regex still enabled, only `Location` passing `regex=False`.
`RecoveryModelOptimized` compared for equality, with explicit range handling.

Consequences: scenario `"BAU"` also selected `"BAU_high"`; year `"2020"` also
selected `"12020"`; a scenario name containing a regex metacharacter either
raised or matched something unintended.

One inflow in scenario `BAU`, and TC rows of 0.30 for `BAU` and 0.90 for
`BAU_high`:

| | result |
|---|---|
| optimized | 30 t — only the BAU row |
| LA, before | **90 t** — matched `BAU_high` as well |
| both, now | 30 t |

Not a wrong number so much as **a different scenario than the one asked for**,
with nothing said about it.

**FIXED 2026-08-17.** The selection rule moves to `src/selection.py` and both
engines use it: equality on scenario, location and additionalSpecification;
years equal or inside a `2020-2030` range, on either side. A column that exists
but is empty everywhere does not filter, which is how a table with no scenario
dimension is read against a request that names one.

The point of one shared module rather than two corrected copies: two copies of
a selection rule is exactly how these came apart. `is_year_match` and
`select_df_by_year_scenario_location` remain on both engines as thin
delegations, so existing callers are unaffected.

**Found while fixing this:** `src/tc_precedence.py`, added the same day for
§2.3, grouped rows without looking at the selector columns — so two TC rows for
*different scenarios* were reported as an unresolvable overlap. They are
alternatives, not a conflict. Corrected in the same commit; a
scenario-differentiated table would have been refused outright otherwise.

### 2.5 Same-layer TCs: each engine drops a different key — RESOLVED

**Reproduce:** `data/reference/defect_cases/same_layer_key`

For a transfer that stays within one layer, **neither engine reads both keys,
and they drop opposite ones**:

| | reads | ignores |
|---|---|---|
| `RecoveryModelLA` (`recovery_model_LA.py:297-299`) | `Input_layer_key` | `TC_target_key` |
| `RecoveryModelOptimized` (was `:320-322`) | `TC_target_key` | `Input_layer_key` |

In LA, when `Input_layer == TC_target_layer` the `if row['Input_layer']==layer`
branch wins and sets *both* the input and output key to `Input_layer_key`, so
the target is never consulted. The optimized engine did the mirror image: it
selected `TC_target_key` alone and merged on it, so it matched — and moved —
whichever resource the *target* named, not the one the TC was about.

They agreed only because **every same-layer TC written so far is an identity**:
4 of 4 in `basic_test`, 2 of 2 in `composition_stock_id`, 1 of 1 in
`tc_specificity`. Identity is the one case where dropping either key is
harmless.

The committed case is 100 Mg of P1, 60% C1 and 40% C2, with one TC reading
`F2 component C1 → F3 component C2`. Three implementations, three answers:

| | result |
|---|---|
| LA | `F3 / P1 / C1 = 60` — moves C1, keeps calling it C1 |
| optimized, before | `F3 / P1 / C2 = **40**` — moves C2, the wrong resource |
| a transformation reading | `F3 / P1 / C2 = 60` — moves C1, renames it C2 |

**RESOLVED 2026-08-17: a same-layer transfer carries a resource unchanged.**
A component does not become a different component, so the two keys must name
the same resource. Two changes follow:

- `src/validate_inputs.py` rejects a same-layer TC whose keys differ, naming
  the row and both keys. This is an error, not a warning: it is not a
  disagreement about a legal input, it is an input with no meaning.
- The optimized engine now matches on `Input_layer_key` rather than
  `TC_target_key`. With the loader enforcing identity the two are equal, so
  this changes no result — but matching on the input key is the direction that
  is *right* rather than accidentally equivalent, and it stops the old
  behaviour of silently moving the wrong resource if the rule is ever relaxed.

`basic_test` is unmoved at 8.88e-16.

#### If the transformation reading is wanted later

The rejected option — `C1 → C2` meaning "this component is reclassified as
that one" — is strictly more expressive, and a process that re-sorts or
re-grades material is a real thing. It was not chosen because nothing in the
current data needs it and neither engine can express it. To implement it:

1. **Loader** — drop the same-layer identity check in `validate_inputs.check`
   (the block marked `2.5`). Both keys become legal again.
2. **Optimized engine** — in `solve_process.process_outflow`, the same-layer
   branch keeps `TC_target_key` alongside `Input_layer_key`, merges on the
   input key, then rewrites the layer column to the target key for the rows
   that matched:

   ```python
   became = process_outflow["TC_target_key"]
   process_outflow[target_layer] = became.where(became.notna(),
                                                process_outflow[target_layer])
   ```

   This was written and measured; it produces the 60 in the table above.
3. **LA engine** — the harder half, and the reason this is not a small change.
   `create_tcs_matrix` must stop letting the `Input_layer` branch win: the
   matrix needs `Input_<layer> = Input_layer_key` and
   `Output_<layer> = TC_target_key`, so the transfer is off-diagonal within the
   layer rather than on it.
4. **Nesting** — decide what happens to the subtree. A component carries its
   materials and elements with it; if C1 becomes C2, do its children keep C1's
   composition or take C2's? Neither engine currently has an answer, and this
   is the question that makes the feature a method decision rather than a
   coding one.

Steps 1 and 2 alone would make the engines disagree again. All four are needed.

### 2.6 A composition row populating only Layer 1 invents mass

**Reproduce:** add a row to `basic_test/input_data/composition.csv` with
`Layer 1` filled, `Layer 2`–`Layer 4` empty, and `Value` 1.

`recovery_model_optimized.py:214` selects the product→component shares with
`Layer 3 == '' and Layer 4 == ''` — but never requires `Layer 2` to be
non-empty. A Layer-1-only row therefore passes the filter, gets merged on
`Layer 1`, and duplicates the product row at "component" depth with an empty
component key.

| | optimized | LA |
|---|---|---|
| baseline | 7514.4575 | 7514.4575 |
| with the added row | **8514.4575** | 7514.4575 |

Exactly +1000, the mass of `F1/P1`, created from a row that says nothing. The
LA engine is unaffected.

**Severity: medium.** Same family as §2.1 — a filter that under-constrains
which composition rows apply — and equally silent.

**Caught since 2026-08-17** by `src/validate_inputs.py`: a composition row with
a gap, or with only `Layer 1`, is an error naming the file and the row.

**FIXED 2026-08-26 — the filter itself.** The three filters tested only the
TAIL of a row (`Layer 3` and `Layer 4` empty) and never that the layers before
it were filled. They now select a row for depth *d* only if the first *d*
layers are filled **and** the rest are empty — contiguous from the left, which
is what "this resource sits inside that one" means.

Reproduced against `create_initial_flows` directly rather than through a case
folder, because the validator would stop the input long before the filter saw
it and the filter is what was under test. Before:

    Stock/Flow ID Layer 1 Layer 2 Layer 3 Layer 4  Value
               F1      P1                         1000.0
               F1      P1      C1                  600.0
               F1      P1      C2                  400.0
               F1      P1                         1000.0   <- from the empty row

Two rows at the shallowest depth totalling 2000 against an inflow of 1000.

**Counting filled layers is not enough, and the test for that caught a fix
that was itself wrong.** `Layer 1` and `Layer 3` filled with `Layer 2` empty
counts as two, so a depth-count filter read it as a product-to-component share
and produced `P1 / '' / M1` at full mass — a worse outcome than the original
defect, briefly introduced and caught by the second test before it was
committed. All four malformed shapes now produce output identical to the clean
table.

### 2.7 Unknown keys: LA crashes unreadably, optimized swallows them

**Reproduce:** add to `basic_test/input_data/inputs.csv` either (a) a row whose
`Substance_main_parent` appears in no composition row, or (b) a row whose
`Stock/Flow ID` appears in no TC row.

The LA engine encodes with `.replace(mapping)`
(`recovery_model_LA.py:188`, `:224`, `:307-312`). `replace` leaves an unmapped
value as the original **string**, which then reaches `ravel_multi_index`'s
`np.dot` alongside integers:

| case | LA |
|---|---|
| (a) unknown product | `TypeError: unsupported operand type(s) for +: 'int' and 'str'` |
| (b) unknown flow id | `TypeError: can only concatenate str (not "int") to str` |

Neither message names the column, the value, or the file. `.map()` yields NaN
for a miss and would allow a real diagnostic.

The optimized engine does not fail at all:

| case | optimized |
|---|---|
| (a) unknown product | 181 rows, 8514.4575 — **+1000** as an inert product row |
| (b) unknown flow id | 202 rows, 11514.4575 — **+4000** across 22 rows |

In (b) the orphan flow's mass enters the system, expands through the full
composition tree, and goes nowhere. No warning from either engine.

**Severity: high for the optimized engine**, which is the one `stages/02_run_model.py`
uses and the one that fails silently; medium for LA, where the failure is loud
but the message is useless.

**Caught since 2026-08-17.** Both engines refuse the input before reading it,
naming the file, the column and the value.

**LA HALF FIXED 2026-08-26.** All three encodings — the inflow vector, the
composition matrix and the transfer coefficients — use `.map()` and report
what did not map, through one `encode()` helper:

    InputDataError: data/reference/basic_test: the inflow table has
    1 value(s) in column 'product' that appear nowhere the model can place them:
        'NOT_A_PRODUCT'

    A key has to exist in the composition (for a resource) or in the transfer
    coefficients (for a flow) before it can be encoded. Check the spelling
    against those tables.

against the `TypeError: unsupported operand type(s) for +: 'int' and 'str'`
it used to raise. Worth fixing behind the guard because a guard can be
bypassed — by a caller handing tables over in memory rather than through the
file checks, or by a key that becomes unknown only after the table has been
rewritten — and the landing place should say something.

**The optimized half is still only guarded, not fixed.** Its merges drop or
keep unmatched rows silently; nothing in the engine itself objects. The
mitigation is `src/validate_inputs.py` refusing the input, plus the unaccounted
fraction reported by `stages/01_check_inputs.py`, which is where an orphan flow's mass
shows up. Making the engine refuse as well would duplicate the validator, so it
is left — recorded here rather than fixed, so the asymmetry is deliberate and
visible.

---

## 3. Absent capability and latent issues

Things the model was never built to do, plus latent issues affecting both
engines. Listed so they are not rediscovered.

**3.1 to 3.4 have since been built or fixed** and are kept, struck through, so
that a reader who remembers them can see what happened rather than wonder.
**3.5 to 3.8 were re-checked against the code on 2026-08-26 and are still
true**, with their line numbers corrected — they had drifted.

### 3.1 No mass balance check anywhere — **BUILT**

`src/mass_balance.py` reports it, `stages/01_check_inputs.py` prints it, and
`99_check_all.py` counts it as one of its ten checks. On `bev_electronics` the
worst relative residual across five years is 2.8e-16. Both failures named below
are checked: a total above 1 is reported as ERROR, and composition closure is
reported per depth.

The original text follows.

Nothing verifies that the TCs for a resource total to anything sensible, and
nothing records the shortfall.

The meaningful check is per transferred resource, totalled over the output
flows it reaches — see MODEL_MECHANICS.md §4 for why other groupings are not
quantities. `stages/01_check_inputs.py` computes it. On `basic_test`, totals range
[0, 0.66], none exceed 1, and the unaccounted fraction averages 0.78. That mass
has no residual or loss flow: it leaves the system unrecorded.

Two things a checker should catch that nothing currently does:

- **A total above 1**, which creates mass and is always an error.
- **Composition failing to close to 1**, which silently rescales the entire
  inflow expansion. In `basic_test` it closes exactly, at all three depths.

See DESIGN_monte_carlo.md §3 for how this bears on the sum-to-1 question.

### 3.2 No uncertainty of any kind — **BUILT**

`src/sampling.py` and `src/monte_carlo.py`, with 37 and 9 checks respectively.
A coefficient carries `value_min` and `value_max` as a triangular, groups are
made to sum to 1 by one of three rules (CASES.md, the TCs section), and
`stages/03_run_monte_carlo.py` produces percentiles, a sensitivity ranking and the
distribution figures. `DQS` and `CV` were never used and are not the mechanism.

The original text follows, including the line about this being the main body of
work ahead — which it was, and no longer is.

`DQS` and `CV` are declared in `InputDataFormat.dtypes` in both engines and are
read by nothing. Every value is a deterministic scalar. This is the main body
of work ahead.

### 3.3 Units are declared and ignored — **FIXED**

`src/units.py` converts every inflow into `run.working_unit` on load, from
whatever its own file declares, and `convert_inflows` is on the reading path
rather than a manual step. Three units are in play — data folders in Mg,
upstream in kt, arithmetic in kg — and a wrong one is a silent factor of 1000,
which is why this became a conversion rather than a warning.

The original text follows.

`inputs.csv` has a `Unit` column. It is not in `InputDataFormat.input_columns`
and is never read by either engine. The user guide states the model is
unit-agnostic and the user must keep units consistent by hand.

**Checked since 2026-08-17**, though still not *read*: the model continues to
multiply fractions without ever converting anything, which is exactly why the
unit is dangerous — a wrong one is wrong by a clean factor of 1000 and nothing
in the output looks unusual. `src/validate_inputs.py` now refuses a file that
mixes two units, names an unrecognised or ambiguous one ('ton' is 1000 kg in
one country and 907 in another), and warns when the declared unit differs from
`expected_unit` in `src/params_schema.py`.

Worth acting on: HANDOVER.md §7 records that the upstream `04_02` pipeline
delivers inflows **in kt**, while every data folder here is written in **Mg**.
That is the factor of 1000 this check exists to catch, and it will fire the
first time real upstream data arrives.

### 3.4 The solution's `Value` column is `object` dtype — **FIXED**

Checked in memory on 2026-08-26, not through the CSV, which re-infers and would
have hidden it: the optimized engine returns `Value` as `float64`. The
Monte Carlo work this was blocking has been built.

The original text follows.

`solve_models_and_write_to_output` seeds the result with
`pd.DataFrame(columns=[...])`, which creates an all-`object` frame, then
`pd.concat`s onto it. The `Value` column of the returned solution therefore
holds boxed Python floats rather than `float64`:

```
optimized: Value dtype = object
       LA: Value dtype = object
```

It survives the CSV round-trip unnoticed because `read_csv` re-infers the type,
so downstream consumers reading the file see floats. In memory it does not.

**Why it matters for the Monte Carlo work:** an object column defeats every
numpy fast path. Vectorising over draws requires a real `float64` array; this
must be fixed first or the restructuring will be silently slow. It is also why
naive byte-level comparison of two solutions fails — `.tobytes()` on an object
array hashes pointer addresses, which differ every run.

**Severity: low now, blocking later.** Trivial to fix (build from a list and
concatenate once, declaring the dtype).

### 3.5 The LA engine is not reproducible run to run — **FIXED 2026-08-26**

**FIXED 2026-08-26.** Both encodings are `sorted(set(...))`. Verified across
five hash seeds in separate processes: identical flow encoding
`F1..F8` and an identical SHA-256 of the solution's values, where before the
fix three seeds gave three orderings and two different hashes.
`tests/test_regression.py` runs the engine under two hash seeds in
subprocesses, because inside one process the set order is already fixed and no
test living there could see this.

The original text follows.

`recovery_model_LA.py:195` and `:199` build the encoding with
`list(set(...))`. Set iteration order for strings depends on Python's
per-process hash randomisation, so the integer encoding of flows and resources
changes between runs. That changes the ordering of the sparse system and hence
the floating-point accumulation order in `spsolve`.

Measured across 5 runs of `basic_test`:

```
168 of 180 rows identical, 12 differing
max absolute spread 1.78e-15   max relative spread 3.31e-16
```

About 1.5 ULP — numerically irrelevant here. But it means the LA engine's
output is **not byte-reproducible**, and on a larger or more
ill-conditioned system the accumulation-order sensitivity would be larger.

`RecoveryModelOptimized` is bit-identical across runs; only the LA engine is
affected.

**Severity: low, but fix before trusting LA as an exact oracle.** Sorting the
sets (`sorted(set(...))`) makes it deterministic at no cost.

### 3.6 Feedback loops are unsupported in the default engine

Still true on 2026-08-26: `recovery_model_optimized.py:427`.

`get_process_sequence_from_tcs` raises `ValueError` on cycles. Any closed-loop
recycling route must either use the LA engine or be modelled as a distinct
downstream flow. Worth knowing before designing the flow network.

### 3.7 `src/plot_flows.py` silently plots only the first case — **FIXED 2026-08-26**

**FIXED 2026-08-26, and it had started biting.** The note below said it did
not, because the fixtures had one combination each. The real electronics case
grew to five years, so every Sankey described **2030** while every other output
of the run was headlined 2050 — and nothing on the figure said so.

`replay` now takes `input_data[-1]`, the last of the selection, matching what
the rest of the output is headlined on, and `figure_for` prints which:

    2050 — one of 5 in this run. Element-depth rows only. ...

Narrow `run.years` to draw a different one. The fix is the figure naming its
own subject, not a better default: a diagram that says which year it is cannot
mislead whichever one it picks.

The original text follows.

`src/plot_flows.py:56` takes `model.input_data[0]`. With more than one year,
scenario, location or additionalSpecification, the figures describe that first
combination alone — and nothing in the title or subtitle says which.

`basic_test` and `template` each have one combination, so it does not bite
today. It will the moment real data arrives with several years, and it will
look like a plotting quirk rather than a selection.

**Severity: low now.** Either loop over `input_data` and label each figure, or
take the combination as an argument.

### 3.8 The LA engine mixes the two scipy sparse APIs — **FIXED 2026-08-26**

`HelperFunctions.create_sparse_matrix` built a legacy `coo_matrix(...).tocsr()`
— the `spmatrix` branch — while `solve_model` combined the result with
`eye_array`, from the sparse *array* API. The type hints throughout claimed
`csr_array`, which is not what came back:

    create_sparse_matrix   -> csr_matrix     sparray=False
    create_vector          -> csc_array      sparray=True

It worked on scipy 1.18. It mattered because the two APIs differ in operator
semantics — `*` is matrix multiplication for `spmatrix` and elementwise for
`sparray` — so the mix was a trap for anyone editing this later, and the hints
pointed the wrong way for anyone checking.

**FIXED:** `coo_array` throughout, so both builders return sparse arrays and
`coo_matrix` is no longer imported. Two hints were also wrong in a second way
and are corrected: `create_vector` and `create_inflows_vector` return a single
column, which is **CSC**, and both said CSR.

`tests/test_regression.py` asserts both builders return `scipy.sparse.sparray`,
and checks their shapes and placed values, so a return to the `spmatrix` branch
fails rather than merely working.

---

### 3.9 Every Sankey was labelled with the wrong unit — **FIXED 2026-08-26**

Found while fixing 3.7, and worse than it.

`plot_flows.draw` took the unit from the inputs table's own `Unit` column —
which is the unit the SOURCE declared, `kt` from upstream — while the engine
converts every inflow into `run.working_unit`, `kg`, on the way in. So the
numbers drawn were kilograms and the label said kilotonnes.

Reproduction, before the fix: aluminium in the electronics case printed as

    F_collected 887,760.1     subtitle: "mass in kt"

against a measured `887,760.09` **kg**, or 0.89 t. A factor of 10^6, on every
Sankey the project has ever drawn.

**FIXED:** `unit_drawn(params)` returns `run.working_unit`, and the inputs
table's `Unit` column is no longer consulted for labelling — it describes the
file, not the figure. `tests/test_generality.py` asserts the label matches the
working unit and, where they differ, is not the source unit.

**Why this one is worth the space.** A wrong unit is invisible: the number
looks reasonable and the reader supplies the meaning. It survived because the
two units differ by exactly the factor that makes a plausible number out of an
implausible one. Three units are in play in this project — data folders in Mg,
upstream in kt, arithmetic in kg — and nothing but the label tells them apart.

### 3.10 A draw folder holding two runs was read as one — **FIXED 2026-09-01**

Found by re-checking the pipeline, not by a test. It had already happened.

An upstream draw folder is written **file by file and never cleared**, so it is
the union of every run that has written to it. A file is replaced only when a
later run happens to emit the same name — change the element list upstream and
the old names stay, indefinitely.

`src/upstream.py` read whatever `*.npy` it found. `_one_product` means each
array over `array[:draws]`, and slicing 200,000 rows from a 20,000-row array
returns the 20,000 without complaint. So a share became one run's element over
another run's domain total, and the model solved it.

**Measured 2026-08-31**, on `element_draws/BAU/collected` after upstream's
`57a06f4` changed 04_02's element list and re-ran it:

| written | draws | what |
|---|---|---|
| 08-21 10:52 | 200,000 | 7 Motors elements, incl. `Nd`, `Dy`, `Pr`, `Tb` |
| 08-31 13:23 | **20,000** | 16 `*_ppm__Motors` |
| 08-31 13:56 | **20,000** | 20 plain `*__Motors`, incl. `Fe`, `Al`, `O` |
| 08-31 15:09–15:44 | 200,000 | material-resolved Motors (`Fe__esteel`, …), Wiring, PCB, Sensors, and the domain arrays |

Four runs in one folder. Iron was present three times over — `Fe__Motors`,
`Fe__{cfsteel,esteel,magnet,copper}__Motors` and `Fe_ppm__Motors` — because
`rpartition('__')` reads `Fe__esteel__Motors` as an element named `Fe__esteel`.
Motors' children summed to **1.81** of Motors.

**It surfaced only by luck.** `src/rest.py` refuses parts exceeding the whole,
so 1.81 stopped the run. A mix landing under 1 would have balanced, plotted and
been wrong — the §5-of-HANDOVER failure mode exactly.

**FIXED:** `upstream.one_run()`. Every array in one folder must hold the same
number of draws, and every product folder in one case must agree with the
others; anything else is refused, naming the widths, the counts and examples.
The draw count is the one property every array of a run shares and that two
runs have no reason to.

    ../RAWCLICStockAndFlow/data/processed/element_draws/BAU/collected holds
    arrays from more than one run.
        84 array(s) at 200,000 draws: Ag__PCB, Ag__Sensors, Ag__copper__Motors, ...
        36 array(s) at 20,000 draws: Ag__Motors, Ag_ppm__Motors, Al__Motors, ...

`tests/test_generality.py` covers both halves: a leftover file under a name the
current run does not write, and one product folder re-run alone.

**What the check does not do.** It says the folder mixes runs; it does not say
which run is wanted, and it cannot. Two things are still open and are upstream's
to settle — the plain Motors elements exceed the Motors domain mass by 3.7% even
within their own run, and `Nd`, `Dy`, `Pr` and `Tb`, the elements this case
exists for, are still the 21 August files. The folder has to be emptied and
04_02 re-run once before the electronics case reads again.

### 3.11 A resource with no way out of a flow lost its mass silently — **FIXED 2026-09-01**

Found by hand-totalling the terminal flows after the Layer 3 work, not by any
check.

A coefficient is keyed on the resource's parent — `Motors_mixed / Al`. When the
material layer became real, `Al` moved to `bulk`, so that row no longer reached
it. `Al`, and `Mn` and `Sr` with it, arrived at `F_dismantled` and
`F_shredded` and **stopped**. The run wrote a solution, drew its figures and
reported a recovery rate over less mass than entered.

Measured on `bev_electronics`, 2050:

| | kg |
|---|---|
| entered `F_collected` | 640,831,681 |
| left through the four terminal flows | 603,149,794 |
| **gone** | **37,681,887 — 5.9%** |

Per flow: `F_dismantled` kept 32.0 Mkg of the 365.5 it received, `F_shredded`
5.7 of 275.4. Every one of the four resources shows `0` in every onward flow.

**The check that existed was the same join read the other way.** Since
2026-08-17 a TC row naming a resource that does not exist has been reported —
as a *warning*, correctly, since an inert row costs nothing. Nothing looked for
a resource that no row names. That asymmetry is why five years of runs could
have lost mass without a word.

**FIXED:** `validate_inputs._check_nothing_strands`. For each flow that
something leaves, every resource at each layer the outgoing coefficients target
must be covered by one of them. An **error**, not a warning: the mass is not
questionable, it is gone.

    ERROR 4 resource(s) reach F_dismantled and no coefficient moves them on:
              bulk/Al, cfsteel/Mn, esteel/Mn, magnet/Sr

Which flows are terminal is read from the `processes` table — a flow is
terminal exactly when it is no process's input — so no flow name is written in
the code. **A case with no `processes` table is not checked**, since nothing
then says which flows ought to have an exit. Both real cases have one; the
reference fixtures predate the sheet, which is why the test for this lives in
`tests/test_generality.py`, whose synthetic case writes one.

### 3.12 `make_skeleton` deleted filled rows while documented as merging — **FIXED 2026-09-01**

`merge()` dropped any filled row whose resource was not in the composition, and
reported it as `dropped`. Both the module docstring and CASES.md called the
script safe to re-run.

A resource leaves the composition for two ordinary reasons, neither of which
says the row is wrong: **narrowing `groups` to work one component at a time** —
the workflow the script exists for, and the one its own docstring recommends —
and **an upstream export resolving fewer elements than the last one**.

Both happened at once on 2026-09-01. Upstream re-exported 24 elements instead
of 68, and the material layer moved `Al` out of the placeholder. One re-run
deleted **32 filled rows** from `bev_electronics` — every rare earth among them,
each with a hand-written provenance note. They were recovered from a copy taken
before the run; nothing in git would have helped, since `case.xlsx` is a binary
and the loss would have been a silent 52 → 36.

**FIXED:** a filled row is kept whatever happens — appended after the skeleton
and reported as *inert*. Only a blank stale row is removed, since it says
nothing. `src/validate_inputs.py` already reports a row that cannot fire, which
is the honest state: the row is not wrong, it is not currently reachable.

**Worth the space because the word was right and the behaviour was not.**
"Merges" was in the docstring, in CASES.md and in HANDOVER §4, and it was
trusted on all three counts. The code even carried a comment about not causing
"quiet loss" — attached to the handling of extra *columns*, three lines above
the rows being dropped.

### 3.13 The deterministic line was drawn unscaled — **FIXED 2026-09-02**

Spotted by the user in `distribution.png`: every histogram was a single spike at
zero, with a dashed line off at the right edge labelled `59,750,828.6` beside a
Monte Carlo mean of `57.1`.

`figure_distribution` picks each panel's unit from the Monte Carlo values and
scales them, but drew the deterministic total **raw**. That value arrives in the
working unit — kilograms — so the line landed 10^6 away, the axis stretched to
reach it, and the distribution collapsed into one bar.

    alalloy   Monte Carlo mean 57.1 kt   deterministic drawn at 59,750,828.6

**FIXED:** `point = point * scale`, one line. `figure_pdf` and
`figure_mode_vs_mean` draw the same value and both already scaled it; only this
one did not.

**Worth the space** because the figure did not look broken, it looked *decisive*
— a tight spike and a clear line — and it is the figure the whole Monte Carlo
exists to produce. Same family as §3.9: a unit that is never wrong by a little.

### 3.14 `SUM TO 1` printed `nan nan -> nan` rows — **FIXED 2026-09-02**

Spotted by the user in `stages/01_check_inputs.py` output. The section said *3 groups
beyond 0.5 sd* and then listed eight lines, five of them blank:

    3 group(s) beyond 0.5 sd -- ...
      BEV Wiring -> F_collected: independent sum averages 0.9333, -0.86 sd from 1
      Motors copper -> F_shredded: ...
      Wiring copper -> F_shredded: ...
      nan nan -> nan: independent sum averages nan, +nan sd from 1
      nan nan -> nan: ...

`worth_naming` holds only the groups over the threshold; `offset` covers all of
them. Reindexing the first onto the index of the second inserted a NaN row for
every group below the threshold, and `.head(8)` then took three real rows and
five of those.

**FIXED:** rank within `worth_naming`, using its own `offset` column.

**Why it survived so long.** Sorting every group by offset puts the ones over
the threshold first, so with eight or more of them `.head(8)` happened to take
the right eight. `carcomposition_mockup` has 65 and never showed it in weeks of
runs. It needed a case with **fewer than eight** — the 14-group wiring case —
before the sorted index ran on into groups that were not in the frame at all.

A reminder that a small case is not a weaker test than a large one; it is a
different one.

### 3.15 Per-resource Sankeys were silently missing — **FIXED 2026-09-02**

Asked for by the user: *"I want the sankey diagram also for the copper and each
of the alloys."* They were supposed to exist already — `RUNNING.md` listed
`<resource>.png`, one Sankey per resource — and `stages/02_run_model.py` drew only
`total.png`.

One line in `src/plot_flows.py`:

```python
elements += sorted({e for f in flows.values() for e in f['Layer 4'].unique() if e})
```

**A hard-coded `Layer 4`.** A case that resolves to MATERIALS leaves Layer 4
empty in every row, so the set came back empty and the loop drew the total and
stopped. No error and no warning — one figure where there should have been
several.

It affected every material-keyed case: `bev_electronics_wiring`, and
`carcomposition_mockup`, which has **never** had per-resource Sankeys in its
life.

**FIXED:** a `finest_layer` that reads the deepest layer the data actually
fills. `mass()` had the same assumption when selecting a resource's rows and was
fixed with it.

**`src/plot_monte_carlo.py` already had `finest_layer`, for this exact reason,
with a docstring warning that assuming Layer 4 gave 04_01 no per-resource
figures at all, silently.** The fix was applied there and not to its sibling. A
defect understood well enough to be documented, and left in place next door.

    F_collected 515,880 t of copper, 2070
      +- F_disassembled 192,420 -> F_cu_own      182,799   (95%)
      +- F_in_car       323,460 -> F_cu_general  177,903   (55%)

37% of the copper takes the dedicated road and yields more metal than the 63%
that goes through the shredder. That is the entire case for disassembling, and
no other figure shows it.

### 3.16 `mode_vs_mean` compared two masses no year has — **FIXED 2026-09-02**

The last figure that summed the year axis. `totals_by_flow_and_element(run)`
adds every year's draws together, and the deterministic side was summed to
match:

```python
point = float(rows['Value'].sum())          # every year of the point estimate
mean = float(values.mean())                 # mean of every year, added up
entries.append((..., 100.0 * (point - mean) / mean, point * scale, mean * scale))
```

`distribution.png` was deleted the same day for adding 2030's kilotonnes to
2070's. This did the same thing and **survived, because it divides one total by
the other** — and a ratio of two quantities that are wrong in the same direction
comes out looking right. The percentage was within a percentage point of the
truth. Nothing justified it.

What gave it away was the label written at the end of every bar: `1,247.9 vs
1,155.4 kt`, a mass belonging to no year, on a figure whose title said
*2020–2070, all 11 years summed*.

**FIXED:** the gap is computed per year, and the figure shows the LAST year.
Which year hardly matters here — but the figure says so with a measurement
instead of an assurance. `drift` is the largest distance any single gap travels
across every year in the run:

```
F_cu_own        · copper    2.0 -> 3.0    0.95 pp
F_disassembled  · copper   -2.7 -> -1.8   0.90 pp
F_loss_own      · copper  -48.0 -> -47.6  0.49 pp
30 rows, 2 of them moving more than 0.5 pp
```

0.9 percentage points, on a scale reaching −48%, and only copper moves at all —
the one material that is in both Wiring and Motors, so the blend between them
shifts as the two domains grow at different rates. Everything else is exactly
flat, because the coefficients do not vary by year and the gap is a ratio of two
quantities that both scale with the inflow.

The subtitle now carries that number, so a reader asking *"which year, and would
another one differ?"* gets both answers off the figure.

**`stages/03_run_monte_carlo.py` printed the wrong name in the same breath:**

```python
f'on {worst["Stock/Flow ID"]} {worst["Layer 4"] or worst["Layer 2"]}'
```

The same hard-coded `Layer 4` as §3.15. On a material-keyed case Layer 4 is
empty, so it fell through to Layer 2 and named the worst result
`F_loss_own Wiring` — the component — while the figure beside it said
`F_loss_own · copper`. Two outputs of one run disagreeing about which result was
worst. It now takes the deepest layer the row actually fills, and names the
year.

### 3.17 Every figure was built before any was written — **FIXED 2026-09-02**

`draw_all` built its list eagerly:

```python
figures = [('over_time', figure_over_time(...)), ...]
for stem, figure in figures:
    write(figure, ...); plt.close(figure)
```

The close was there and it was too late: the list comprehension had already
constructed all of them. On the wiring case that is 11 figures and nobody
noticed. On the boards case, with 20 resources, it is 27 — each holding its own
histogram of 200,000 draws — and matplotlib says so out loud at 20:

    RuntimeWarning: More than 20 figures have been opened.

**FIXED:** the list holds thunks, and each figure is built, written and closed
before the next one starts. The per-resource entries bind `resource` as a
default argument, since a bare closure over the loop variable would have drawn
the last resource 20 times.

### 3.18 The per-element Sankey announced a depth it did not have — **FIXED 2026-09-02**

    2070 -- one of 11 in this run. Element-depth rows only.

On `bev_electronics_wiring`, whose rows are MATERIALS: copper, alalloy,
fealloy at Layer 3, Layer 4 empty everywhere. `mass()` had been fixed to read
the deepest layer each frame fills (3.15) and was drawing the right rows; the
sentence under the title was still the one written when Layer 4 was assumed.
A caption that names the wrong layer is worse than none: it is checkable, and
it checks out false.

**FIXED:** the subtitle names the layer it actually drew -- `Layer 3 rows only
-- the deepest this case resolves` -- rather than asserting what is in it.
Which is also the honest wording for the boards case, where Layer 3 holds
element names while the column is called material.

### 3.19 The structure diagram never said what an endpoint WAS — **FIXED 2026-09-02**

Every box carried one line of meta -- `expressed at: material` -- and none said
whether the mass that lands there is recovered, lost, or handed to a process
the case does not model. So two boxes with no arrow leaving them looked
identical:

    F_recovered_own   expressed at: material      <- gold coming back
    F_shredded        expressed at: component     <- a board nobody follows

The `role` column has existed since the day it replaced guessing recovery from
the flow's NAME (CASES.md), it is what the whole boards restructure turned on,
and the one picture of the network did not carry it. `render` was never given
the processes table at all -- only the TCs, which do not hold a role.

**FIXED:** `draw` passes `flow_roles(case)` in, and each box states its role on
a third line, coloured: recovered here (green), lost (red), handed on, not
counted here (purple). `intermediate` is deliberately left off -- it says an
arrow leaves the box, which the arrow already says -- and a case with no
processes table keeps its two-line box. `tests/test_generality.py` renders a
four-flow case and asserts on the strings that reach the axes.

A local variable in that code was called `role` and held the TC target LAYER,
which is likely how the real role went unnoticed for as long as it did. It is
called `depth` now.

### 3.20 A new parameter section stopped `00_parameters.py` dead — **FIXED**

    KeyError: 'combine'

`combine` had been declared, given defaults, added to `SECTIONS`, validated,
documented in its own comment blocks and read by `05_combine_cases.py`. It
worked. The one thing it had not been added to was a dict written out by hand
inside `describe`:

```python
section = {'run': RunParams, 'data': DataParams,
           'monte_carlo': MonteCarloParams,
           'figures': FigureParams}[section_name]
```

So the FIRST stage of the pipeline -- the one whose whole job is to write the
settings out, and which every other stage reads the artifact of -- crashed on a
section every other stage was already using.

The caller had the section object in its hand:

```python
for section_name in params.SECTIONS:
    section = getattr(params, section_name)      # right here
    for f in fields(section):
        rows.append([..., describe(section_name, f.name), ...])
```

and threw it away to pass a string that had to be mapped back to a class.

**FIXED:** `describe` takes the section itself. There is no second list to keep
in step, so a section added to `SECTIONS` cannot fail this way again. A test
walks every field of every section through `flatten` and also refuses the
fallback text -- a section whose comments are not collected would otherwise
flatten silently, with `Setting in ...` where its explanation should be.
Confirmed the test fails against the old code before keeping it.

Side effect worth noting: `documentation/PARAMETER_REFERENCE.md` had never
carried the `combine` section, because the generator could not run. It does
now.

### 3.21 Every per-resource Sankey was drawn at twice the mass — **FIXED 2026-09-28**

    F_collected, copper, 2070:   drawn 141,089,503 kg      true 70,544,752 kg

Exactly 2x, on **every resource of every traction motor case** (copper,
aluminium, steel, lamination, magnet) and **all twelve components of the
battery**, in all three scenarios. Since the cases were built.

`resource_of` gives each row the value of its own deepest filled layer, which
is what lets one case mix depths (3.16). But a component named after the thing
it is made of answers the same name twice:

| Layer 2 | Layer 3 | `resource_of` | Value |
|---|---|---|---|
| `copper` | | copper | 70,544,752 |
| `copper` | `copper` | copper | 70,544,752 |

The child is the WHOLE of its parent, so the two rows carry the same mass by
construction, and `mass()` summed both — under a docstring reading *"Total mass
in a set of rows, without double counting the nesting"*. It handled the nesting
correctly for a flow's aggregate, where it takes the shallowest depth, and not
at all for a named resource.

Upstream names a component after its material as a matter of course, so this is
the normal case here and not a corner: `copper`/`copper`, `magnet`/`magnet`,
`batteryPackCables`/`batteryPackCables`. The electronics cases escaped because
theirs differ — `Wiring`/`copper`, `PCB`/`Ag`.

**WHAT IT DID NOT TOUCH.** The `Recovered` sheet, `over_time`, `recovery_rate`,
`spread`, `mode_vs_mean` and every `pdf_` figure read RECOVERED flows only, and
no recovered flow in any of the nine cases holds a resource at two depths —
checked, all of them. The damage is confined to the Sankeys, which is also why
it lasted: the Sankey is the one figure nobody reconciles against a table.

**HOW IT SURFACED.** By wiring `figure_for_draws` into 03 on 2026-09-28, at the
user's instruction. The Monte Carlo Sankey prints each node's mean, so for the
first time the picture carried numbers that could be checked against each
other — and `F_cu_stream` at 123.5 M kg with 61.8 M leaving it does not
balance. The deterministic Sankey had been drawing the same doubled masses for
weeks with nothing on it to contradict them.

**FIXED:** `shallowest_of` states the rule once -- match the resource, then keep
only the shallowest depth among the rows that matched -- and both `mass` and
`draws_for` go through it. `tests/test_generality.py` builds a frame with a
component named after its material and pins all three cases; it fails against
the old rule.

### 3.22 The Sankey subtitle ran off the page, and interval labels collided — **FIXED 2026-09-28**

Both are 3.21's figure seen at full size, and neither existed until a node
carried three lines.

The subtitle was one line of 12.5pt from x=20 on a 1180pt canvas: about 170
characters, and the Monte Carlo subtitle -- which has to say that the ribbon is
a MEAN and the interval is printed separately, because a ribbon cannot carry
one -- is longer than that and lost its last clause. Truncating the sentence
that explains what the figure cannot show is the worst possible place to
truncate.

A right margin of 150pt suited `name` over `value`. `[597,713,656.8 -
670,589,993.6]` at 9pt is about 155pt on its own, so every interval was cut in
half. And a gap of 16pt between nodes let two small ones print three lines each
straight through one another.

**FIXED:** the subtitle wraps at `SUBTITLE_CHARS` and the diagram starts below
however many lines it took; a figure carrying intervals is 1400x880 with a
300pt right margin and a 40pt gap. DECISIONS 17 -- a figure has to be readable
at the size it is drawn.

### 3.23 Copper had no account figure, in two places at once — **FIXED 2026-09-28**

The battery and the electronics cases draw four whole-account figures per
resource -- `account`, `losses`, `trapped`, `fate`. The traction motor cases
drew none of them, for any resource, and said nothing about it.

All four hang off `plot_monte_carlo.account()`, which needs three upstream
arrays per resource: `collected`, `outflow` and `inflow`. Two separate things
stopped it.

**One, the export had no `outflow`.**

    traction_recovery_draws/mix/     collected/  inflow/
    battery_recovery_draws/S1/       collected/  inflow/  outflow/
    element_draws/BAU/               collected/  inflow/  outflow/

`account()` returns None the moment `outflow` is missing, and `outflow -
collected` is the mass that left the fleet and never reached a recycler at all
-- the band those figures exist to draw. Nothing here can compute it: it is a
fleet quantity. Fixed upstream in `RAWCLICStockAndFlow/src/traction_export.py`,
which now composes it from the three destinations that partition the outflow.

**Two, `other_flow` could not address the resource.** It builds
`<resource>__<domain>.npy`:

| | copper's array | looked for |
|---|---|---|
| electronics | `Cu__PCB.npy`, an element in a component | `Cu__PCB.npy` ✓ |
| traction | `__component____copper.npy`, copper IS the component | `copper__copper.npy` ✗ |

04_03 exports copper, aluminium, lamination and steel as COMPONENTS, because
that is where the recycling routes act (decided 2026-09-24). So every traction
motor resource came back None from every flow -- `collected` included, before
`outflow` was ever reached.

**FIXED:** `Draws` keeps the case's `group_marker`, and `_other_path` falls
back to `<group_marker>__<domain>.npy` when the resource IS its domain. That is
the rule `Draws.mass` already applies one layer up: when the thing asked for is
the group, the group's array is the answer. A resource that simply is not
exported still comes back absent -- checked, so the fallback cannot answer a
missing name with a component's mass.

Verified on the real arrays: copper at 2070 now resolves to 70.47 kt collected
and 72.48 kt inflow, against 70.54 kt in the run's own banner. With a staged
`outflow` present, all four figures build.

⚠️ **The figures stay absent until 04_03 is re-run**, because the export on
disk is the old two-flow one. That run is the user's.

### 3.24 The same double count in the ACCOUNT, where it did worse — **FIXED 2026-09-28**

3.21 again, in `plot_monte_carlo`, found hours later and only because the
account figures could finally be drawn at all (3.23). In the Sankey the defect
doubled a number. Here it mixed two quantities that were wrong in DIFFERENT
ways:

| | rows | doubled? |
|---|---|---|
| `collected` | start flows, which hold the component row AND the material row | **yes** |
| `recovered` | recovered flows, which hold one depth | no |

and `lost = collected - recovered`. So copper, 2070, shredder route:

    collected  140.94 kt      true  70.47
    recovered   49.22 kt      true  49.22
    lost        91.73 kt      true  21.26

**Copper appeared to lose 91.7 kt of the 70.5 kt it had**, and the account
still closed to 0.00e+00 -- because closure is by construction: `uncollected`
is `outflow - collected` and the outflow was scaled by the same doubled ratio.
A figure that reconciles with itself and not with the model.

`recovery_rate` had it too, its denominator being the same start flows.

**FIXED:** `resource_key` now also marks `own_depth` -- the shallowest depth
among rows sharing (flow, year, resource) -- and `own(keys)` is ANDed into all
twelve row selections in the module that sum mass. Grouping on (flow, year,
resource) is what keeps it safe where a resource legitimately appears twice:
copper in Wiring and copper in Motors are two rows at the SAME depth in one
flow, and both are kept.

Checked against the model afterwards, copper 2070, shredder, `mix`:

    outflow      80.08     upstream array  80.16
    collected    70.47     upstream array  70.54
    recovered    49.22     Recovered sheet 49.12
    lost         21.26     = collected - recovered
    uncollected   9.61     = outflow - collected
    closure    0.00e+00

**THE LESSON, AND IT IS THE SECOND TIME TODAY.** Both of these survived because
the figure carrying them had nothing on it to contradict. The Sankey balanced
within itself; the account closed by construction. Neither was ever put beside
the `Recovered` sheet, which was right the whole time. A figure that can only
be checked against itself is not checked.

---

### 3.25 The traction motor carries no fleet uncertainty — **FIXED UPSTREAM 2026-09-30**, re-export pending

⚠️ **Every interval on the traction motor is about five times too narrow.**
Nothing in this repository is wrong; the export it reads is. Do not quote a
traction confidence interval until this is fixed.

**How it was found.** Matthias asked why the in-fleet band on `fleet_<r>.png`
was so tight when the others widen. The answer given first — that the stock
carries no transfer coefficient, so it only inherits the upstream's spread —
was true and beside the point. He then put it in one line: the inflow is
vehicle count times composition, the count alone has a CV of 12.1%, so the
product cannot have a CV of 2.5%. *A product of two uncertain things cannot be
more certain than either of them.*

**Measured**, copper at 2070, 200,000 draws:

| | CV | what varies |
|---|---|---|
| vehicle count, all segments | 12.10% | — |
| wiring copper inflow (`04_02`) | 14.61% | count × composition |
| traction copper inflow (`04_03`) | **2.53%** | composition only |

Separating the wiring figure in quadrature puts its composition spread near
8.2% against the traction motor's 2.53%, so the motor study IS about three
times better characterised — that part is real. The other 12.1 points are not
a characterisation difference at all: one export draws the fleet and the other
does not.

    should be   sqrt(12.10^2 + 2.53^2)  =  12.36%
    is                                      2.53%

**The mechanism.** `code/04_03_tractionmotors.py` in `RAWCLICStockAndFlow`
loads `tracker_keyed_BAU` — the tracker's point-estimate vehicle counts — and
`src/traction_draws.coefficients()` puts them in its deterministic matrix. Its
own docstring says so plainly:

> ⚠️ EVERYTHING DETERMINISTIC LIVES HERE AND NOTHING ELSE DOES. The vehicle
> count, the motor-type share, the voltage share and the year factor are all
> scalars; the only random thing in the product is the draw vector this
> multiplies.

`04_02` does the opposite: it loads `bev_draws/<scenario>/BEV_<segment>_<flow>.npy`,
which is *(draws, years), millions of vehicles*, and pairs draw *i* of the
fleet with draw *i* of the electronics. **The per-draw counts already exist, in
the same folder, written by the same 03_02 run. `04_03` simply does not read
them.**

**What it affects here.** Everything the traction study reports an interval
for: `account_<r>`, `losses_<r>`, `fleet_<r>`, the recovery rate, the Sankey's
95% labels, `spread`, `pdf_<r>`, and the traction share of every figure
`05_combine_cases.py` draws. Means and modes are unaffected — the point
estimate of the vehicle count is the one the tracker gives either way. **It is
only the spread that is wrong, and only in the direction of overconfidence.**

**It also makes 05 inconsistent.** When copper is added across the four cases,
the wiring contribution carries fleet uncertainty and the traction contribution
does not, so the combined band is too narrow by an amount that depends on the
mix and is stated nowhere.

**HOW MUCH IS MISSING, PER YEAR.** The count dominates in every year --
composition is 2.5-3.3% throughout, the count 7-21%:

| year | composition | count | combined | too narrow by |
|---|---|---|---|---|
| 2020 | 3.29% | 21.43% | 21.68% | 6.6x |
| 2030 | 2.85% | 11.86% | 12.20% | 4.3x |
| 2040 | 2.63% | 10.56% | 10.88% | 4.1x |
| 2050 | 2.52% | 6.94% | 7.38% | 2.9x |
| 2060 | 2.48% | 9.33% | 9.65% | 3.9x |
| 2070 | 2.47% | 12.23% | 12.48% | 5.0x |

Neodymium is the least bad case, its composition spread being larger to begin
with: 5.50% at 2070, combining to 13.41%.

**The correction.** Multiply each exported `(draws, years)` array elementwise by
`count_draw[draw, year] / count_mean[year]` for its flow. That ratio has mean
1, so no mean moves -- only the spread. It composes correctly with the
composition spread because the two are drawn independently.

⚠️ THE MEANS OF THE TWO ARTEFACTS DISAGREE BEFORE 2060 -- 83% on collected at
2035, converging to 0.08% by 2070 -- and that is a SEPARATE question. It does
not block this correction, because the ratio's mean is 1 whatever the two
means are. It is recorded here because it was found while looking at this, and
because `04_02` uses the draws while `04_03` uses the tracker, so the two
studies do not describe the same fleet before 2060.

**The fix is not in this repository.** `04_03` would have to multiply by the
`bev_draws` counts per draw instead of the tracker's scalars, the way `04_02`
already does, keeping draw *i* of the fleet with draw *i* of the motor. Whether
that alignment already holds there has not been checked.

### 3.26 A year in which a case has no mass at all stopped the Monte Carlo — **FIXED 2026-10-08**

`AttributeError: 'NoneType' object has no attribute 'mean'`, in
`Draws.mean_inflow`, on the first real run of the solid-state case.

Solid-state is exported for S3 with nothing before 2040: the arrays are zero, so
the composition table has no row for it in those years, so `upstream_values`
kept no component, so `Draws.inflow` had nothing to add up and returned `None`.
The code a line below already meant to treat a zero year as zero
(`scale = ... if average > 0 else 0.0`); it never got that far. Any case with a
leading run of empty years would have failed the same way -- a chemistry that
starts late, a product with no inflow yet.

It was not found by the stand-in export the five battery cases were first checked
on, because that had mass in every year. It was found by running each case on the
real export before the study was pressed (FAILURES 30).

**FIXED:** no component kept is a year with no mass, and `inflow` returns zeros.
Components that the composition names and the export has none of is a different
thing, a mismatch between two things that should agree, and is now an
`UpstreamError` that says so. Two tests in `tests/test_generality.py`; the first
reproduced the real traceback before the fix.

### 3.27 04_04 draws a different pack-size world on every run — **FIXED UPSTREAM 2026-10-09**, re-run pending

Found 2026-10-08 comparing the per-chemistry export with the old summed one. The
means agree to four decimals (new/old = 1.0000 on every array looked at), the
individual draws do not: the correlation between the two runs across draws is
0.06 for 2020 inflow, where the pack size dominates, and 0.97 for 2050, where
the vehicle count does. The vehicle counts (`bev_draws`) and the composition
files were not rewritten between the runs; the pack size and voltage are.

**Cause:** `RAWCLICStockAndFlow/src/battery_capacity.py:81` and
`src/battery_voltage.py:107` seed each segment's stream with
`abs(hash(segment))`. Python salts the hash of a `str` per process, so the seed is
different in every run. Shown directly: the same call with the same seed gives
`[33.7, 35.8, 34.1, ...]` kWh in one process and `[33.7, 29.9, 34.1, ...]` in the
next, and identical numbers in both with `PYTHONHASHSEED=0`. These are the last
two uses of `hash()` for a seed in the code; `battery_chemistry.py` and
`04_02` already use `zlib.crc32`, and the upstream handover of 2026-09-28 says
"crc32, never `hash`".

**What it costs:** nothing within a run -- the capacity and voltage are drawn once
per segment and shared by every chemistry and scenario, so one draw is one world
in everything the run wrote. What is lost is that two runs of 04_04 differ, so an
export cannot be reproduced, and this model's results shift a little with each
re-run.

**FIXED 2026-10-09:** `zlib.crc32(segment.encode())` in both places. Checked as a
failing test and then a passing one: the pack size, the voltage, every chemistry
share and a composition call, in four processes (two pinned hash salts, two random),
differ in 25 of 34 digests before and in none after. It changes the draws once and
for good, so it takes effect with the next run of 04_04 (six hours, his to run); the
export on disk is from the unfixed code.

### 3.28 Pack size and voltage are coupled, and so are other draws — **OPEN, upstream**

Found 2026-10-09 while fixing 3.27. `capacity_draws` and `voltage_draws` are called
with the same `seed=404` and both seed their stream with `[seed, segment]`, so they
are the same stream: the uniform that picks a segment's pack size is the one that
places the car in the 800 V adoption order. A small `u` is the smallest pack **and**
800 V. Segment A in 2050: the 25 kWh pack is 800 V in 100 % of its draws, the 30 kWh
pack in 63 %, the 35 kWh pack in 0.6 %; rank correlation between pack size and 800 V
-0.56 in A, -0.15 in C and JC, -0.09 in JF. Nothing in the design note relates them.

Three further streams are seeded with the bare `seed` and so share their uniforms:
the capacity growth rate and plateau year (`battery_capacity.py:65`), the voltage band
position (`battery_voltage.py:115`) and the composition's extrapolation factor
(`battery_composition.py:211`). Measured: growth rate against voltage band position,
rank correlation **+1.0000**.

Size, measured for the pack size and voltage only, on LFP per pack at 200,000 draws
against the same voltages shuffled across draws: mean cable copper up to +0.5 % and
terminal copper up to +1.0 % higher as drawn (segment A, 2050), within 0.5 % in C and
JC. The effect on the spread, and of the other couplings, was not measured.

**Not fixed, his decision:** give every stream its own tag in the seed list. It
changes the draws, so the time to do it is the same run of 04_04 as the 3.27 fix.

---

## 4. Code quality notes

The docstrings are reasonable throughout. What is missing is not docstrings but
any statement of *semantics* — §2.3 exists precisely because nobody wrote down
what overlapping TCs mean.

One comment is worth flagging, at `recovery_model_optimized.py:277`:

> `# This snippet is taken from chatgpt, i have no idea but it works`

That block implements wildcard/empty-key expansion and is load-bearing. It is
directly adjacent to defect 2.2. It needs to be understood and rewritten, not
preserved.

One dead line, at `recovery_model_optimized.py:211`:

```python
composition_df[['Layer 1','Layer 2','Layer 3','Layer 4']] = composition_df[['Layer 1','Layer 2','Layer 3','Layer 4']]
```

It assigns the four columns to themselves — a no-op. Worth noting rather than
just deleting: it sits one line below the `Stock/ID` drop that is defect §2.1,
and looks like the remains of something that was meant to happen there.

---

## 5. Input validation — what ties §2.5–2.7 together

All three, plus §2.1, were the same absence: **nothing validated the input
tables before they were used.**

**Built 2026-08-17** — `src/validate_inputs.py`, called from both engines'
constructors before a single row is joined. At that point a bad key can still
be reported with its file, its column and its value.

### Errors — the run stops

An input that cannot be read as meaning anything. Each one used to be silent:

| Check | Was |
|---|---|
| Every `Substance_main_parent` resolves in `composition.csv` (§2.7) | +1000 Mg of inert product, or an unreadable `TypeError` |
| Every `Stock/Flow ID` resolves in `TCs.csv` (§2.7) | +4000 Mg across 22 rows, going nowhere |
| No composition row skips a layer (§2.6) | +1000 Mg invented from a row saying nothing |
| Every TC key names a resource that exists | Unmatched TCs, silently zero |
| One mass unit per file, and a recognised one (§3.3) | Unread — a clean factor of 1000, invisible in the output |
| Shares and TCs are fractions in [0, 1] (§3.3) | 25 read as 25, not 0.25 — a 100-fold error |

### Warnings — the run continues

Inputs that are readable but that the two engines *disagree* about. These are
open method questions (§2.1, §2.3, §2.5), not mistakes, and the answer belongs
to whoever owns the method — so they are reported and the run proceeds. It is
also what keeps `data/reference/defect_cases/` runnable, since those folders are
built from exactly these patterns.

Each defect case now reports precisely its own defect and nothing else;
`basic_test` and `template` report nothing at all.
