# Defects and engine divergences

Found 2026-08-14; §2.5–2.7, §3.7 and §3.8 added 2026-08-17. Each item has a
measurement and a reproduction. Items in §1 are **fixed**; items in §2 and §3
are **open** and change results.

Reproduce any divergence with:

```bash
./.venv/bin/python compare_engines.py data_folder/defect_cases/<case>
```

The cases in §2.1–2.3 have committed data folders. The ones added on
2026-08-17 do not yet: each states the edit to `data_folder/basic_test` that
exposes it. Its unmodified baseline, for comparison, is **180 rows** and a
naive row total of **7514.4575** on both engines. That total sums nested rows
at every depth, so it is a comparison figure and not a mass.

---

## 1. Fixed — the code did not run at all

All three were fixed in commit `ee3fc6b`. Recorded because each was silent or
misleading, and because the third one silently corrupted performance rather
than results.

### 1.1 `run_model.py` failed at import

`from pandas.errors import SettingWithCopyWarning` — removed in pandas 3. The
entry point raised `ImportError` before doing anything. `data_folder` also
pointed at `data_folder/feb_2026_sensitivity`, which does not exist in the
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

§2.1 and §2.2 were **fixed 2026-08-17** and are kept here with their
measurements, because each is a shape of mistake that can recur. §2.3–§2.7
remain open.

### 2.1 Composition `Stock/ID` is ignored by the optimized engine — FIXED

**Reproduce:** `data_folder/defect_cases/composition_stock_id`

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
is invented, silently. The optimized engine is the one `01_run_model.py` uses.

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

**Reproduce:** `data_folder/defect_cases/wildcard_star`

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

**Reproduce:** `data_folder/defect_cases/overlapping_rules`

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

### 2.4 Year, scenario and location matching differ

`RecoveryModelLA` matches by substring: `str(year_target) in year_data`, and
`.str.contains()` for scenario and additionalSpecification — with regex still
enabled (only `Location` passes `regex=False`).

Consequences: scenario `"BAU"` also matches `"BAU_high"`; a scenario name
containing a regex metacharacter raises or mismatches; year `"2020"` matches
`"12020"`. `RecoveryModelOptimized` uses equality plus explicit range handling
(`HelperFunctions.is_year_match`), which is the sane behaviour.

**Severity: medium** — silent cross-contamination between scenarios, but only
with the LA engine and only with scenario names that are prefixes of others.

### 2.5 Same-layer TCs: each engine drops a different key — RESOLVED

**Reproduce:** `data_folder/defect_cases/same_layer_key`

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
a gap, or with only `Layer 1`, is now an error naming the file and the row. The
underlying filter at `recovery_model_optimized.py:214` is still wrong; it can
just no longer be reached.

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

**Severity: high for the optimized engine**, which is the one `01_run_model.py`
uses and the one that fails silently; medium for LA, where the failure is loud
but the message is useless.

**Caught since 2026-08-17.** Both engines now refuse the input before reading
it, naming the file, the column and the value. The `.replace()` encoding in the
LA engine is unchanged — it is simply no longer reachable with an unknown key.
Using `.map()` there is still the better fix and is not done.

---

## 3. Open — absent capability and latent issues

Things the model was never built to do, plus two latent issues that affect both
engines equally. Listed so they are not rediscovered.

### 3.1 No mass balance check anywhere

Nothing verifies that the TCs for a resource total to anything sensible, and
nothing records the shortfall.

The meaningful check is per transferred resource, totalled over the output
flows it reaches — see MODEL_MECHANICS.md §4 for why other groupings are not
quantities. `02_check_mass_balance.py` computes it. On `basic_test`, totals range
[0, 0.66], none exceed 1, and the unaccounted fraction averages 0.78. That mass
has no residual or loss flow: it leaves the system unrecorded.

Two things a checker should catch that nothing currently does:

- **A total above 1**, which creates mass and is always an error.
- **Composition failing to close to 1**, which silently rescales the entire
  inflow expansion. In `basic_test` it closes exactly, at all three depths.

See DESIGN_monte_carlo.md §3 for how this bears on the sum-to-1 question.

### 3.2 No uncertainty of any kind

`DQS` and `CV` are declared in `InputDataFormat.dtypes` in both engines and are
read by nothing. Every value is a deterministic scalar. This is the main body
of work ahead.

### 3.3 Units are declared and ignored

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

### 3.4 The solution's `Value` column is `object` dtype, in both engines

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

### 3.5 The LA engine is not reproducible run to run

`recovery_model_LA.py:125` and `:129` build the encoding with
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

`get_process_sequence_from_tcs` raises `ValueError` on cycles. Any closed-loop
recycling route must either use the LA engine or be modelled as a distinct
downstream flow. Worth knowing before designing the flow network.

### 3.7 `src/plot_flows.py` silently plots only the first case

`src/plot_flows.py:51` takes `model.input_data[0]`. With more than one year,
scenario, location or additionalSpecification, the figures describe that first
combination alone — and nothing in the title or subtitle says which.

`basic_test` and `template` each have one combination, so it does not bite
today. It will the moment real data arrives with several years, and it will
look like a plotting quirk rather than a selection.

**Severity: low now.** Either loop over `input_data` and label each figure, or
take the combination as an argument.

### 3.8 The LA engine mixes the two scipy sparse APIs

`HelperFunctions.create_sparse_matrix` builds a legacy `coo_matrix(...).tocsr()`
— the `spmatrix` branch — while `solve_model` combines the result with
`eye_array`, from the newer sparse *array* API. The type hints throughout claim
`csr_array`, which is not what is returned.

It works on scipy 1.18. But `spmatrix` is the branch scipy is moving away from,
and the two APIs differ in operator semantics (notably `*`), so the mix is a
trap for anyone editing this code later.

**Severity: low, but fix before the Monte Carlo work** rather than during it —
that restructuring will touch exactly these lines.

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
also what keeps `data_folder/defect_cases/` runnable, since those folders are
built from exactly these patterns.

Each defect case now reports precisely its own defect and nothing else;
`basic_test` and `template` report nothing at all.
