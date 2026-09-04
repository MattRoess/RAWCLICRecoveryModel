# Handover

Current as of **2026-09-02**. Rewritten from the ground up on 2026-08-21 and
updated since; git has the older text.

**What is left to do is in NEXT, immediately below: the coefficients, and
nothing else.** The rest of this document is why things are the way they are,
and section 6 is how to work with this user -- read that before doing anything.

**Then read this: what happened on 2026-09-01.** The upstream draw folder had
been rewritten on 08-31 and held **four runs at once**, because upstream writes
it file by file and never clears it — Motors' elements came to 1.81 of Motors.
`src/upstream.py` read the union of them without a word; it now refuses, naming
the widths (DEFECTS.md §3.10). The user emptied the folder and re-ran 04_02 the
same day, and it came back clean: one run, one draw count, no `_ppm` files.

Three things followed from that day, all built and all tested:

1. **Layer 3 is real.** `<element>__<material>__<group>` is read, so a material
   sits at Layer 3 where a placeholder stood. CASES.md has the three rules.
   Superseded on 2026-09-02 for the electronics cases: 04_02 now exports the
   ALLOYS themselves, and neither case has a placeholder at all.
2. **A resource that cannot leave a flow is refused.** It used to lose its mass
   in silence — 5.9% of the electronics case, found by hand. DEFECTS.md §3.11.
3. **`make_skeleton` no longer deletes.** It dropped filled rows whose resource
   had left the composition while being documented as merging, and took 32 of
   them, every rare earth included. DEFECTS.md §3.12.

## NEXT: THE NUMBERS. THE MODEL IS FINISHED.

**Both cases are built, both run end to end, and not one coefficient in either
of them is real.** 20 of the wiring case's 24 rows and 47 of the boards case's
52 say `PLACEHOLDER (Claude, not data)` in their `source` column. Everything
else -- the network, the layers, the sampling, the figures, the workbook -- is
correct arithmetic on invented numbers. §4 is how to replace them and in what
order, and `tools/filling_sheet.py` ranks them by what measuring each one would
actually buy. **Five rows carry 80% of the wiring case's spread. Three carry
80% of the boards case's.** That is the whole of what is left here.

**Nothing else is open.** The two things that were on this list at the start of
2026-09-02 -- the figures, and the boards structure -- are done, and what
follows says what they became so that neither is reopened by accident.

**Open, and small:**

- **04_01 has not been re-run.** `carcomposition_draws_years` is set to 11
  years, 2020-2070 step 5, and the export folder holds a PARTIAL result from a
  run that was aborted. `carcomposition_mockup` therefore still reports 2040
  only. The user runs that stage, not the assistant (§6).

### Done 2026-09-03: two kinds of repeated noise, and a spreadsheet hazard

A Monte Carlo run printed openpyxl's data-validation warning **nine times** and
the case's own warning block **four times**, interleaved with the output that
matters -- which is how people learn to scroll past warnings.

- openpyxl cannot round-trip the extension the workbook dropdowns use and says
  so on every open. Filtered at the three places `src/case_tables.py` opens a
  workbook, by that one message from that one library. Not a blanket filter:
  pandas and numpy warnings have twice been the first sign of a real defect here.
- `validate()` runs once per engine, and `03_run_monte_carlo.py` builds four.
  A warning is about the TABLE, so saying it again tells nobody anything.
  `src/validate_inputs.py` now says each one once per run.

Nine plus four became zero plus one.

**A SPREADSHEET TURNS A BLANK CELL INTO 0.** A definitional row -- the hulk
transfer, `rest` to loss -- carried blank bounds meaning "no range". Opening
`case.xlsx` and saving it wrote `0` into those cells, which reads as "the
minimum is zero" and, beside a value of 1, is an impossible triangle. The
validator refused and computed nothing, which is the system working; the cause
was not obvious from the message.

Every definitional row in all three cases now states `value_min = value_max =
value` explicitly. It means exactly what blank meant, and there is no empty cell
left for a spreadsheet to fill in. 4 repaired in wiring, 6 and 76 made explicit
in boards and car composition; boards verified byte-identical afterwards.

**Why those rows are 1 and cannot carry a range**: each is the only edge leaving
its flow. A one-member group has no freedom, so a range there is not uncertainty,
it is a leak. Uncertainty needs a second destination for the remainder.

### Built 2026-09-03: a case can improve over time

A case may carry a second coefficient table, `TCs_improved`, and an
`improvement_start` / `improvement_end` window in its `source` sheet. Before the
window the current numbers hold, across it every coefficient moves on a straight
line, after it the improved ones hold. CASES.md, *A case that improves over
time*, has the shape and the three properties it rests on.

**Almost nothing had to change.** Both engines already select coefficient rows
by year and the Monte Carlo already samples once per year, so a table with a
`Year` column simply works. The feature is one function that produces that
table, `src/case_tables.ramp`, plus two keys in the source sheet.

**Both electronics cases are seeded**, 2026-09-03: a `TCs_improved` sheet that
is an exact copy of `TCs`, and a 2030-2060 window. Each seeded row says in its
`source` that it is a copy and not an improvement. Neither case's numbers moved
-- checked row for row against the run before the sheets existed, worst
difference exactly 0 on both. `carcomposition_mockup` is seeded too, 632 rows,
at the user's instruction -- checked on the tables rather than through a run,
since its upstream export is waiting to be rebuilt: all 11 years equal the
current table exactly and all 3,894 groups close to 1. Its `TCs` sheet is
GENERATED, though, so `make_carcomposition_tcs.py` now reports whether a
rebuild has left the improved sheet out of step; the run refuses a mismatch
either way.

**One thing this makes true that the documentation already predicted.**
RUNNING.md says `convergence.png` and `sensitivity.png` pool the years, and that
"if that ever stops being true -- a case whose coefficients vary by year -- they
have to be split per year like the rest." An improving case is exactly that.
Neither figure is wrong for a case that does not improve, and no case improves
yet, but the first one that does needs them split. Related, and in the same
place: `solve_draws` keeps only the LAST year's coefficient draws for the
sensitivity figure (`all_tc_values[:] = tc_values`), which for a ramped case is
the improved end rather than a mixture. **Not yet done, and it is the first
thing to do when a real improvement table is filled in.**

### Done 2026-09-03: a case writes only the layers it reaches

All three cases are material-keyed, so `Layer 4` was empty in every row of every
one of them, and each wrote a dead column into its solution, its Monte Carlo
summary and two sheets of its workbook. `src/rest.drop_unused_layers` drops it
**at the moment of writing** -- the arithmetic reads the layers positionally and
never sees the change, and the wiring case's mass balance is the same 2.67e-16
it was.

Two things the fix had to get right, both pinned by tests:

- **The FRAME returned by an engine keeps every layer.**
  `03_run_monte_carlo.py` merges the deterministic answer onto the Monte Carlo
  one using all four, so dropping before returning breaks the join rather than
  tidying a file.
- **Only TRAILING layers go.** An empty layer with a filled one beneath it is a
  gap in the nesting, which `validate_inputs` refuses at input; dropping it here
  would quietly restate the nesting as something else.

`99_check_all.py` read the summary back and asked for all four columns, which
stopped it with a `KeyError` the first time a case was written this way. It now
takes the depth from the columns the file has. **Any consumer of a written file
has to do the same** -- the depth is a property of the case, not a constant.

### What the figures became, 2026-09-02

Every rule in [DECISIONS.md](DECISIONS.md) section *Figures* was written after a
figure was rejected, several of them more than once. Read it before touching any
of these.

| figure | what it is |
|---|---|
| `over_time.png` | the median per resource per year with the 95% band, deterministic run dashed |
| `pdf_<resource>.png` | the density, one panel per year, every other year |
| `pdf_all.png` | those panels on one page, resources x years, each panel its own axis |
| `spread.png` | how much and how sure on one log axis, with BOTH years on the rows whose certainty changed |
| `spread_last_year.png` | the same, last year only, at twice the width |
| `mode_vs_mean.png` | how far the single-value answer sits from the mean, in ONE year, with the drift across the others measured in the subtitle |
| `structure.png` | the network, each endpoint's ROLE, and every coefficient behind every arrow |

`distribution.png` and `flows_over_time.png` were deleted. The first summed an
absolute mass across years; the second was unreadable. `spread.png` and
`mode_vs_mean.png` had the same summing defect and were fixed rather than
deleted -- both now show one year and state, from a measurement, how much
another year would differ.

**Do not invent a figure.** Five replacements for a density figure were built
before somebody noticed `pdf_<resource>` already did the job.

### What the boards case became, 2026-09-02

The user's instruction: *the shredded road is not split -- nobody is interested
in it -- and the elements recovered by the specialist route are what the case is
for.* Three general-recycling flows and their six coefficients came out;
`F_shredded` is terminal with the role `handoff`. See *the boards case* in §1.

---

**Two cases, and neither has a placeholder layer any more.**
`bev_electronics_wiring` and `bev_electronics_boards`, rebuilt 2026-09-02 to the
user's specification after earlier attempts they had not agreed to. The older
`bev_electronics` was deleted (git has it at `e8c2373`).

| | Layer 2 | Layer 3 | Layer 4 |
|---|---|---|---|
| wiring | Wiring, Motors | copper, alalloy, fealloy, rest | none |
| boards | PCB, Sensors | Ag, Au, Cu, Nd, ... , rest | none |

The boards case carried `PCB_mixed` / `Sensors_mixed` until 2026-09-02 -- a
placeholder with no information in it, put there by an assistant who had set
`material_suffix` blank on the wiring case in the same session and did not apply
the same decision to this one. Removing it moved the elements up to Layer 3 and
the coefficients with them, `keyed_at` element to material, 46 rows, every
number unchanged. **Layer 3 there now holds element names**, which is the right
structure -- that route separates gold and palladium and there is nothing
between the board and them -- but the column is called `material`. If that ever
reads wrong, the fix is what the layers are NAMED, not where the numbers sit.

**The boards case, 2026-09-02: the shredded road is ONE flow.** It used to
split into `F_alalloy_general`, `F_fealloy_general` and `F_loss_general` --
three flows and six coefficients, every one of them a placeholder, describing
what becomes of a board nobody is asking about. The case exists to answer what
the specialist route gets back; the other road is there only to say how much
never reaches it.

    F_collected --> F_disassembled --> F_recovered_own   Ag Au Cu Ni Pd (PCB)
                |                  \-> F_loss_own        + 16 more (Sensors)
                \-> F_in_car ------> F_shredded          handoff, and that is all

`F_shredded` carries the role `handoff`: not recovered here, not lost, passed to
a process this case does not model. 8 processes became 5, 58 coefficient rows
became 52. Nothing else moved -- the disassembly split and every recovery
coefficient are the numbers they were. DECISIONS.md 12.

2070, kilograms -- the working unit -- from the deterministic run in
`output_data/solution_optimized_model.csv`:

| | collected | recovered | lost in the specialist route | handed to the shredder |
|---|---|---|---|---|
| Cu | 5,958,949 | 2,861,454 | 317,939 | 2,779,556 |
| Ni | 318,871 | 134,599 | 23,753 | 160,519 |
| Ag | 74,032 | 38,422 | 2,022 | 33,588 |
| Au | 14,534 | 8,153 | 429 | 5,951 |
| Pd | 7,437 | 4,239 | 223 | 2,975 |
| Nd | 19,353 | 290 | 5,516 | 13,547 |

The last column is the price of not disassembling, and the case now says it in
one number per element instead of three flows of invented detail. Nd is the
contrast worth keeping in view: 70% of it is never even offered to the
specialist route, and of the 30% that is, the coefficient recovers 5%.

**Materials only in the WIRING case. No element layer anywhere there** -- zero
Layer 4 rows in its solution. Layer 3 is what a scrapyard sells:

| | share of a motor |
|---|---|
| `fealloy` -- steel, cast iron AND the ferrite magnets | 67.5% |
| `copper` | 14.9% of Motors, 100% of Wiring |
| `alalloy` | 10.1% |
| `rest` -- plastics and the like, never recovered | 7.5% |

Whatever is alloyed into one of those stays in it. `Mn recovered` would claim a
manganese separation nobody performs, which is why 04_02 was changed to export
the alloys themselves (§3).

**Two roads, and they are the point of the case.** Some of the wiring and some
of the motors are DISASSEMBLED -- taken out whole with tools -- and go to their
own shredder and their own recycling process. The rest stays in the car, and the
car is crushed and torn apart by the general shredder. Nothing is lost by not
being disassembled; it simply travels the other road. The dedicated route gets
much more copper back, and that is the whole reason to disassemble.

Six recovered flows, kept apart so the two roads can be compared, and added
together in reporting rather than by a third flow that would double-count.
2050, tonnes:

| | own process | general | combined |
|---|---|---|---|
| copper | 130,842 | 129,357 | 260,199 |
| Al alloy | 24,650 | 3,383 | 28,033 |
| steel alloy | 171,353 | 28,647 | 200,000 |
| rubbish | 38,607 | 113,993 | 152,600 |

76.2% of collected mass recovered, closing to 1.9e-16.

**24 rows, of which 10 are numbers a person chose.** 10 more are computed --
what stays in the car, and what did not reach a pile -- and 4 are fixed at 1
because they state a definition. THERE IS NO ROW FOR A MATERIAL THAT DOES NOT
REACH A STREAM: an earlier version wrote the full material x destination matrix,
22 of its 46 rows were structural zeros, and reading `copper` on an
`F_recovered_al_alloy` row made it look as though copper were inside the alloy.
Do not reintroduce them; `tools/make_skeleton.py` still expands the full matrix,
so this table was written directly rather than generated.

**What changed on 2026-08-28 — the flow itself.** The user's modification, which
§4 had recorded as agreed in principle, is built. `F_loss_dismantling` was a
terminal loss, so a fraction of every component was destroyed by someone with a
screwdriver; dismantling sorts material, it does not destroy it. It was also
redundant with `F_collected -> F_shredded` — "not dismantled" IS "goes to the
shredder". Both edges are gone, replaced by one `F_not_dismantled` that flows on
to the shredder at 1.0. One fewer coefficient per component, and the one left is
answerable. §2 has the shape.

**No residual rows anywhere.** All 22 in `bev_electronics` and all 278 in
`carcomposition_mockup` are now measured in their own right, at the user's
instruction: a derived coefficient is not a measurement and they did not want
any. `bev_electronics_all_measured`, which existed only to contrast the two
schemes, went the same day. Both cases carry the corrected dismantling network,
and both generators write it -- `make_skeleton.py`'s template and
`make_carcomposition_tcs.py` -- so neither the loss edge nor a residual row can
come back through a rebuild.

**§5 is guarded, not just written down.** Its three fixable traps — a
`child_layer` that balances while being wrong, a residual that can be driven
negative, a range that restates its own group — now fail or warn in an ordinary
run. Six of the nine bullets there are conventions with nothing to fix.

**Dead code swept.** One unused function, nine unused imports, and four
hand-typed copies of the resource key, now defined once. Four settings that
looked unused are read through `getattr` and were left alone; §5 says which.

**No coefficient became a measurement on any of it.** What the model does with
numbers is finished; the numbers are not.

**Read [DECISIONS.md](DECISIONS.md) before touching anything.** It is the list
of what the user has settled, and it is short. Every item on it was decided
once and then broken by an assistant who found a tidier way -- which is how a
day gets spent on rework. Add to it the moment something is decided.

**Read [RUNNING.md](RUNNING.md) first if you just want to run something.** This
document is for picking the work back up.

---

## 1. Where things stand

**Three cases run end to end on real upstream data. All 118 checks pass.**

| | wiring | boards | car composition |
|---|---|---|---|
| case folder | `bev_electronics_wiring` | `bev_electronics_boards` | `carcomposition_mockup` |
| from | 04_02 | 04_02 | 04_01 |
| covers | wiring and motors in BEVs | boards and sensors in BEVs | whole cars, five drivetrains |
| finest resolution | **material** — copper, alalloy, fealloy | **element** — Ag, Au, Cu, Pd, Nd, ... | **material** — calAHSS, battery |
| element layer | none at all | Layer 3 IS the elements | none |
| years | 2020–2070, step 5 | 2020–2070, step 5 | 2040 |
| draws | 200,000 | 200,000 | 50,000 |
| mass in | 906.1 kt (2070) | 11.9 kt (2070) | 13,863 kt (2040) |
| mass balance | 0.0 | 1.6e-16 | 4.7e-11 |
| recovered | 76.5% of collected (2070) | 25.6%, with 49.9% handed on | 82.8% (2040) |
| coefficient rows | 24 | 52 | 632 |
| of those, invented | **20** | **47** | **556** |

The boards case's three-way split is the case: a quarter of the mass comes back
as named elements, a quarter is lost inside the specialist route, and **half
never reaches it at all** because the board stayed in the car. That last half is
`F_shredded`, a `handoff` -- what becomes of it is another model's question.

To verify, set `run.data_folder` and press Run on `99_check_all.py`: six test
suites on fixed fixtures (118 checks), then the pipeline and a mass balance.

**No `is_residual` anywhere, and there must not be** (DECISIONS.md 1). Every
coefficient is a value with its own range. The loss rows in both electronics
cases were nevertheless WRITTEN as `1 minus the yield beside them`, and each
says exactly that in its `source`:

    PLACEHOLDER (Claude, not data) -- NOT AN INDEPENDENT MEASUREMENT: it is
    1 minus what left in the stream, given its own range. Replace it with a
    number measured on this side.

That is the honest form of it -- a real row carrying a real range, and a
sentence saying nobody measured it -- as against a derived row, which hides the
same fact in machinery. §4 has what to do when one side of such a pair is
measured.

Both case tables are **structurally finished**. `tools/tc_worklist.py` reports
every group as measured on every row, with no warnings. Nothing in the tables
needs converting, rearranging or repairing. What they need is numbers — see §4.

### The one thing that matters most

**Every transfer coefficient in this project is a placeholder I invented.**
Not one is measured.

| case | rows | invented outright | definitional or stated |
|---|---|---|---|
| `bev_electronics_wiring` | 24 | 20 `PLACEHOLDER (Claude, not data)` | 2 hulk transfers at 1, 2 `rest` rows |
| `bev_electronics_boards` | 52 | 47 `PLACEHOLDER (Claude, not data)` | 2 hulk transfers, 2 `rest` rows, 1 boron |
| `carcomposition_mockup` | 632 | 556 `MADE UP (Claude)` | 76 definitional hulk transfers |

**No table has a residual row.** What remains beside the placeholders states a
definition (a hulk that was not dismantled goes to the shredder, at 1), routes
the unspecified `rest` to loss, or records a fact -- boron is not recovered,
because no process at this scale separates it. None of those is a measurement
either; they are simply not guesses. The split is worth stating only because
the `source` column distinguishes them, and a reader comparing this table
against the file should find them agreeing.

The `source` column says so on every row, and it is carried into the workbook's
Coefficients sheet. The uncertainty ranges are invented too, so **the 95%
intervals are the spread of guesses, not of observations.**

What *is* real: inflow mass and composition (from the upstream draws), every
name — elements, drivetrains, components, materials — and which (component,
material) pairs exist. The mass balance, closure to 1, layer nesting and Monte
Carlo machinery are checked and correct. They are correct arithmetic on
placeholders.

---

## 2. The architecture, in one page

**One model.** `src/` knows nothing about vehicles, electronics or panels. What
differs between studies is a **case**: a folder under `data_folder/` holding

```
input_data/
    case.xlsx
        source      where the numbers come from, and how they map to layers
        processes   the flow network
        TCs         the coefficients
```

Switching studies is changing `run.data_folder` in `src/params_schema.py`.
Nothing else changes — which is the point: a setting you have to edit to run the
other study is a setting somebody forgets, and then one stage's draws get read
with another stage's coefficients and no check anywhere notices.

Three things `source.csv` says that nothing could infer:

- **`child_layer`** — `material`, meaning the child sits at Layer 3 and there is
  no Layer 4, or `element`, meaning Layer 3 holds whatever material the file
  names resolve and the children go below it. **All three current cases are
  `material`**: `calAHSS` within `elvBIW`, `copper` within `Wiring`, and `Ag`
  within `PCB` -- the last of these an ELEMENT sitting in the layer the setting
  calls material, which is right, because the boards route really does separate
  gold from palladium and there is nothing between the board and them. If that
  ever reads wrong, the fix is what the layers are NAMED, not where the numbers
  sit. Getting this setting wrong **does not fail**: it files children at the
  wrong depth, every coefficient keyed at the other one matches nothing, and the
  run still balances while being wrong.
- **`product`** — one name, or several separated by `;`. 04_01's five
  drivetrains are one case, because they are one study: the same shredder and
  the same coefficient table, with only the dismantling rows keyed per
  drivetrain. Each product is its own whole — a component's share is a share of
  its own drivetrain, never of all five together.
- **`draws`** — 04_01 exported 50,000 and 04_02 exported 200,000. Running the
  coefficients at a width the inflow does not have is a mismatch nothing
  downstream reports.

Full detail in [CASES.md](CASES.md).

### No intermediate steps

The engines read the upstream `.npy` draws directly through `src/upstream.py`,
every run. There is no import step and no intermediate file: neither case has
an `inputs.csv` or a `composition.csv` on disk, and both run.

`01_import_upstream.py` used to write those two files so a case could be looked
at. It was **deleted on 2026-08-24** along with the `data.import_case` and
`data.import_year` settings that existed only to serve it. It had already been
deleted once, restored, and then left out of the pipeline, which is a fair sign
that its real job was answering "what will the model solve?" — a question the
`01_check_inputs.py` report and the figures now answer from the draws
themselves.

Four modules still *can* read those files, as a fallback when a caller has not
already passed the frames in: `src/validate_inputs.py`, `src/mass_balance.py`,
`src/plot_flows.py` and `tools/make_skeleton.py`. Each tries the upstream draws
first, so the fallback is unreachable in the normal pipeline. It is left in
place deliberately — it is what lets a hand-written case folder be solved
without any upstream at all, which is how `tests/test_generality.py` builds its
photovoltaic case.

### How a group is made to sum to 1

Everything one resource turns into must total exactly 1. Independent draws do
not, so something has to give, and which thing is the modelling choice.

| the group | what happens | set by |
|---|---|---|
| names an `is_residual` row | that row becomes `1 − the rest` on every draw | the table |
| does not, and every row has a range | **conditioned** — see below | `monte_carlo.sum_to_one` |
| does not, and you asked for `normalise` | the group is divided by its own sum | `monte_carlo.sum_to_one` |

**Conditioning** is the default. It keeps every row's own measurement: draw
them all, take the widest as determined by the rest so the group sums to 1
exactly, weight each draw by that row's own density at the value it was forced
to, and resample so the draws come out equally weighted. It was checked against
brute-force rejection — draw everything and keep only what sums to 1 — and
agrees to four decimals, at about 1% of a run's cost rather than 20×.

**Normalising** is kept for two things and no others: reproducing a result from
before conditioning existed, and getting a number out of a group whose ranges
contradict each other. It hides the contradiction rather than resolving it.

`tools/compare_sum_rules.py` solves a case under both and prints which elements
the choice actually moves. If a case has nothing that can differ, it says so
and stops after one solve rather than drawing two identical curves.

Two consequences worth knowing before you touch a table:

- **`chunk` and `memory_budget_gb` cannot change a result.** The coefficients
  are drawn at full width, once, before anything is evaluated in blocks —
  precisely so conditioning never sees a block boundary. Two machines with
  different memory settings agree exactly. What conditioning *does* give up is
  composing separately invoked runs of different widths; nothing in the
  pipeline does that.
- **`01_check_inputs.py` has a `SUM TO 1` section.** A group's modes sum to 1
  by construction, but its *means* need not — a triangular's mean is
  `(min + mode + max)/3`. Where they disagree the constraint has to move the
  answer away from what is written. It reports that per group as an offset in
  standard deviations. The electronics case sits at a median of 0.73, driven by
  the rare-earth rows, and that is the source of the "running at the modes is
  not the mean" line every Monte Carlo run prints.

---

## 3. What changed upstream, and what did not

Branch **`carcomposition-draw-export`** in `RAWCLICStockAndFlow`, pushed. Three
commits are this work:

| commit | what |
|---|---|
| `6250bb5` | 04_01 writes a year slice of its mass draws in the `.npy` layout this model reads. Off by default. |
| `00af52a` | A single-year period reads the per-year draws 03_02 already writes, instead of demanding a period histogram that does not exist. |
| `7d6c9dd` | Every drivetrain gets a single-year vehicle count, without re-running 03_02. |

Those three touch **only** `code/04_01_carcomposition.py`, and
`data/processed/bev_draws` (2.6 GB) was never rewritten.

**Five more commits landed there on 2026-08-31**, after this document recorded
the project as parked, and three of them change `04_02_BEVelectronics.py`:

| commit | what |
|---|---|
| `cbf8903` | 04_02 skips an element no domain resolves, instead of stopping |
| `57a06f4` | seeds the segment split with `crc32` rather than `hash`, and makes `bev_electronics_elements` default to **empty = every element the draws resolve** |
| `d93e8ed` | reports critical and strategic materials |

`57a06f4` is the one that matters here. The element list is now read from the
upstream models' own files, so the exported names include what those models
call things — `Fe__esteel`, `Al__bulk`, `Sr__magnet`, `Ag_ppm` — which are
decompositions and restatements of elements already exported, not new elements.
`rpartition('__')` reads `Fe__esteel__Motors` as an element named `Fe__esteel`,
so read together they triple-count iron.

**That, plus a folder never being cleared, is why electronics does not run.**

**The material-resolved names are now read** (2026-09-01). `Fe__esteel__Motors`
puts `esteel` at Layer 3 and `Fe` beneath it, where this case had a placeholder
and nothing else. The placeholder stays for what the export does not resolve,
so a folder without the new files produces exactly the rows it always did.
CASES.md, *What fills Layer 3 in the `element` shape*, has the three rules that
decide what the shares mean.

**It is not verified against the real data and cannot be** until the folder is
emptied and 04_02 re-run — the guard refuses to read it, which is the point.
It is verified on a synthetic fixture that resolves two materials in one group
and none in another, checked share by share against exact arithmetic, and
falsified two ways to confirm the checks bite.

`Fe_ppm` is a different problem and is **not** solved here. It is a
single-underscore name, so structurally it is simply an element called
`Fe_ppm`, sitting beside `Fe` and stating the same quantity again. Nothing in a
file name distinguishes a restatement from an element, and this model will not
guess from values. If a clean re-run still writes them, they double-count, and
the answer is upstream's: either stop exporting them or name them so their
level is visible.

**`03_02_adjustedflows.py` is still unmodified.**

### Upstream state at the end of 2026-09-02

| | setting | on disk |
|---|---|---|
| 04_02 | `bev_electronics_element_draws_years` = **all 51 years, 2020-2070** | **done** -- 5.88 GB, `(200000, 51)`, verified against the previous run to 3e-05 |
| 04_01 | `carcomposition_draws_years` = **11 years, 2020-2070 step 5** | **NOT re-run.** The folder holds a PARTIAL result from an aborted run -- one flow's worth of the 11 years. Do not trust it; the next run overwrites it. |

`monte_carlo.output_periods` is back to `[(1975, 2070)]` and must stay that way.
It is shared with stages 02, 03_01 and 03_02, and every entry is a reporting
window all of them compute. Putting single-year windows there to feed 04_01's
export was tried twice on 2026-09-02 -- once at 52 entries -- and rejected both
times. **04_01 derives its own export periods now** (`7b39946`), so a year that
should be EXPORTED goes in `carcomposition_draws_years` and nowhere else.
`(2040, 2040)` was removed from `output_periods` on the same day: it was the
original version of that same shortcut and no longer bought anything.

**04_01 costs about 1.2 minutes per period, and the period loop runs once per
flow -- there are two.** So 11 export years is ~29 minutes and every year is
~2 hours. Measured, not estimated. The user chose the step of 5 after watching
the every-year version reach 1h 50m.

### What 04_02 was changed to export, and why — **DONE 2026-09-02**

**It writes the material's own mass and does not go down to the elements**, for
the metal domains only. Four files, and they were the whole ask:

    copper__Wiring.npy      the harness
    copper__Motors.npy      the windings -- the motor copper IS wiring
    alalloy__Motors.npy
    fealloy__Motors.npy     steel + cast iron + the ferrite magnets, one stream

**No approximation was involved.**
`RAWCLICVehicleElectronics/Composition/element_draws/motors_<segment>_elements.txt`
names every column of the fractions array, and each is either a bare element or
`<element>__<material>`:

    Cu  O__copper Ag__copper Pb__copper ... Mn__copper
    Fe__esteel Si__esteel C__esteel Mn__esteel Al__esteel P__esteel S__esteel
    Sr__magnet Fe__magnet O__magnet
    Fe__cfsteel C__cfsteel Mn__cfsteel P__cfsteel S__cfsteel
    Al__bulk  Plastic  Unspecified

Every element of every alloy is in that list, so an alloy's mass is the exact
sum of its `__<material>` columns:

    copper   = Cu + every X__copper        (the bare `Cu` IS the copper metal,
                                            which is why no Cu__copper exists)
    alalloy  = every X__bulk
    fealloy  = every X__esteel + X__cfsteel + X__magnet

**Half of that change is stopping the old one.** `ALLOY_DOMAINS = ('Wiring',
'Motors')`, and the element export is skipped for a domain in that tuple --
otherwise the folder holds both shapes and `src/upstream.py` reads Cu twice,
once as an element and once inside `copper`. Adding the alloy files without
removing the element files was the first attempt and it was wrong.
`code/test_stage04_02_export.py` calls `element_flows` for real with `export`
set and asserts on **the file names produced**, which is the only thing that
catches this: five checks.

PCB and Sensors are NOT alloy domains, so they still export
`<element>__<group>` -- which is what the boards case reads, and why its
Layer 3 holds element names.

Verified against the previous 5-year run: worst relative difference **3.0e-05**,
Motors alloys 92.51-92.54% of the domain on every year,
`copper__Wiring` / domain exactly 100%, no negatives and no NaN.

### Why two earlier attempts at the metals case were wrong

Both, on 2026-09-01, in the same way: keying the recovery at the material layer
while `child_layer` stayed `element`, which leaves `Al`, `Mn` and `Sr` sitting
underneath `bulk`, `cfsteel` and `magnet`. The user's instruction is that there
is no element layer there at all -- *"NO NO NO Fe is the steel and cast iron
alloy and the magnets. No elements. Just the material."* There was no way to
that shape from an elemental export, which is what the four files above fixed.
Both attempts were reverted rather than left half-built.

### The one honest approximation

For a single year, real per-year vehicle-count draws exist **only for BEV** —
03_02's export is BEV-only. The other four drivetrains take:

- their **level** from `03_tracker_keyed`, which holds exact per-year counts for
  all five;
- their **shape** from that (drivetrain, segment)'s widest cumulative summary,
  rescaled to the level.

**Their mean is exact. Their spread is a floor**, because a cumulative total
averages year-to-year variation out, so its relative spread is narrower than any
single year's. The run prints which path each drivetrain took.

Removing it means widening 03_02's BEV-only export loop to every drivetrain —
about twenty lines. **Worth folding into the next 03_02 run, never worth a run
of its own.** A full 03_02 re-run is hours and rewrites the draws 04_02 depends
on.

### Getting more years

| you want | set there | then press Run on |
|---|---|---|
| another year of electronics | `materials.bev_electronics_element_draws_years` | `code/04_02_BEVelectronics.py` |
| another year of car composition | `materials.carcomposition_draws_years` **and** a matching single-year entry in `monte_carlo.output_periods` | `code/04_01_carcomposition.py` |

**Press Run on `code/00_parameters.py` there first.** Those stages read a saved
params artifact, not the source file, so an edit not followed by that has no
effect and the run still looks fine. This cost an hour before it was understood.

**04_01 needs single-year periods** because its draws are cumulative over a
period while this model's axis is years. Keep `(1975, 2070)` alongside — every
existing figure and saved table there is keyed on it.

---

## 4. What to do next, in order

1. **Replace the coefficients. This is the whole of what is left.** The model
   side is finished; nothing else is in the way. The rankings below were
   measured on 2026-09-02 against the cases as they now stand, with
   `tools/filling_sheet.py`.

   **Wiring — 20 waiting, and 5 carry 80% of the spread:**

   | # | share | coefficient | guess |
   |---|---|---|---|
   | 1 | 45.7% | `Wiring/copper  F_shredded -> F_cu_general` | 0.35 – **0.55** – 0.65 |
   | 2 | 45.7% | `Wiring/copper  F_shredded -> F_loss_general` | 0.315 – **0.45** – 0.56 |
   | 3 | 30.7% | `Motors/fealloy  F_disassembled -> F_fealloy_own` | 0.75 – **0.95** – 1 |
   | 4 | 30.7% | `Motors/fealloy  F_disassembled -> F_loss_own` | 0.035 – **0.05** – 0.24 |
   | 5 | 10.0% | `Wiring/copper  F_disassembled -> F_cu_own` | 0.75 – **0.95** – 1 |

   Rows 1 and 2 are ONE measurement seen from both sides, and so are 3 and 4.
   So the real list is three questions: **how much copper a general shredder
   yields from a harness**, **how much steel a dedicated motor process yields**,
   and **how much copper the dedicated process yields.** The remaining 15 rows
   are together worth 18%.

   **Boards — 47 waiting, and 3 carry 80%:**

   | # | share | coefficient | guess |
   |---|---|---|---|
   | 1 | 65.0% | `BEV/PCB  F_collected -> F_in_car` | 0.28 – **0.40** – 0.52 |
   | 2 | 65.0% | `BEV/PCB  F_collected -> F_disassembled` | 0.45 – **0.60** – 0.70 |
   | 3 | 30.4% | `PCB/Cu  F_disassembled -> F_loss_own` | 0.07 – **0.10** – 0.28 |

   Again 1 and 2 are one measurement: **what fraction of main boards is
   actually taken out of the car.** Nothing about gold or palladium appears
   until far down the list, because the recovery coefficients for those are
   tight (0.95, narrow) while the disassembly fraction is wide and sits
   upstream of everything. The other 44 rows are worth 20% between them.

   `tools/make_skeleton.py` writes the rows and **merges, deleting nothing** --
   a row whose resource has left the composition is kept and reported as inert
   rather than dropped, which it was not until 2026-09-01 (DEFECTS.md §3.12).
   For car composition, `tools/make_carcomposition_tcs.py` generated the current
   invented table and **overwrites**, but refuses once any row's `source` says
   something it did not write; `--overwrite` forces a deliberate rebuild.

   **Start with [FILLING_IN.md](FILLING_IN.md)** — five steps, written for
   doing rather than studying — and with `tools/filling_sheet.py`, which ranks
   the rows still waiting for a number by **`spread_share`**: the fraction of
   the answer's variance each one accounts for, and so the fraction that
   disappears if it is measured exactly. That is what a measurement buys, and
   it is not the same as how closely a coefficient tracks the answer, which is
   reported beside it as `influence`.

   The difference between the two decides the order. On car composition it is
   **12 rows of 354** rather than the 88 the influence ranking suggested.

   Fill in `value`, `value_min` and `value_max`.

   **A caution that follows from having no residual rows.** 10 of the wiring
   case's 14 sum-to-1 groups have exactly two members, and 24 of the boards
   case's 28. With no residual, the constraint leaves such a group ONE degree of
   freedom: both rows carry the same information. Two consequences, one harmless
   and one not.

   - Harmless: `filling_sheet.py` reports shares that sum past 100% —
     "measuring all 20 exactly would remove 198% of that spread" — because each
     row of a pair is credited with the same variance. Read the ranking as an
     ordering, not as an accounting. It is also why the tables above list the
     same measurement twice, at ranks 1 and 2.
   - Not harmless: **the second range in each pair is not a measurement.** It is
     `1 minus the row beside it`, widened, and it says so in `source`. Until a
     real, independently measured range replaces it, the pair's width is
     something nobody measured. §5 has why arithmetic cannot detect this and
     only the `source` column can.

   So: when you measure one side of a pair, measure the other side
   independently or say plainly that you did not. `tools/tc_worklist.py` has
   blank columns for an independent number and its source.
2. **More years for 04_01**, if wanted — but check the memory arithmetic first:
   five drivetrains over five years is roughly 20,000 result rows, which at
   200,000 draws is about 32 GB and would be refused even at the raised budget.
   `monte_carlo.memory_budget_gb` went 4.0 -> 8.0 on 2026-09-02 so the boards
   case could run (4.5 GB); it is a guard, not a model parameter, and no result
   number moves when it changes.

### Built 2026-08-28: the dismantling loss was not a loss, in either case

Raised by the user on 2026-08-27, argued through, built the next day.

Manual dismantling sorts material; it does not destroy it. A harness that is not
pulled out is still in the hulk, and the hulk goes to the shredder. So a terminal
`F_loss_dismantling` asserted a destruction that does not happen, and it wrote
the material off **and** denied it the chance to be recovered at shredding —
biasing recovery low. It was also redundant: `F_collected -> F_shredded` and
`F_collected -> F_loss_dismantling` named one event twice.

    F_collected --> F_dismantled              (pulled out)
                --> F_separated_electronics   (handed on)
                --> F_not_dismantled          (left in the car)
                            |
                            +--> F_shredded  = 1.0   definitional

Four edits: rename; `role` loss to intermediate; add the definitional transfer;
remove `F_collected -> F_shredded`. The two coefficients on the removed edges
became **one** — the fraction of harnesses not removed — which is a question
somebody can answer, where "how much is lost during dismantling" was not.

**Both cases.** `carcomposition_mockup` carried exactly the same defect --
`ELV_loss_dismantling` terminal, and `ELV_collected -> ELV_shredded` naming the
same event -- and was corrected the same way. Recovery there moved from 79.2% to
82.8% of collected mass, which is the material that used to be destroyed at
dismantling now reaching the shredder.

Both generators wrote the old network, so a rebuild would have resurrected it:
`make_skeleton.py`'s `DEFAULT_PROCESSES` and `make_carcomposition_tcs.py`'s row
builders. Both write the corrected one now, with the argument beside it, and
neither emits a residual row.

`F_separated_electronics` was that case's handoff to a separate recovery
stream. **The two cases that replaced it are that stream**, split in two because
they are two different processes: the boards and sensors go to a specialist
route that really does separate elements, the wiring and motors to shredders
that produce alloys. The handoff role survives in both -- `F_shredded` in the
boards case is one -- and the argument for keeping it is unchanged: a flow
handed to a process this case does not model is neither recovered nor lost.

### Not in this repository

The upstream project was parked on 2026-08-26 — the user's words: stock and
flow is done for the moment — but **five commits landed there on 2026-08-31**
(§3), so it is being worked on again. These still need it and should not be
started without saying so first.

- **DONE 2026-09-01/02: the folder was emptied and 04_02 re-run**, then changed
  to export the alloys and re-run again over all 51 years. It holds one run, one
  draw count, and no `_ppm` files. `src/upstream.py` refuses a mixed folder now
  rather than reading the union of it, so this cannot recur silently. What is
  still worth settling upstream, whenever 04_02 is next touched:
  - **`_ppm` names have no level.** None are being exported today. If they come
    back, `Fe_ppm` reads as an element and double-counts, because `__` is what
    says how deep a name goes and a single underscore says nothing. Give them a
    `__` level or leave them out.
  - The plain Motors elements sum to **3.7% more than the Motors domain mass**
    within their own run. It no longer affects either case -- both read the
    alloys, and the alloys sum to 92.5% of Motors -- but it is a fact about the
    export that nothing here can compute a share around.
- **Widen 03_02's per-year export** to all five drivetrains, next time it runs
  anyway. Removes the approximation in §3.
- **04_03 and 04_04.** Each needs its own year-sliced export upstream, then a
  case folder here. No code change unless its children sit at a layer that is
  neither element nor material — in which case `src/source.py` gains a third
  value, `src/upstream.py` a third branch, and `tests/test_generality.py` a
  third case *before* either.
- **Consolidating the draw files.** 04_01 reads 765 separate `.npy` files per
  run, each paying iCloud open overhead. Consolidating them into one array per
  product would cut minutes off a run, and touches a layout both repositories
  read.

### Settled, so that it is not reopened

- **The segment question for 04_01 — settled 2026-08-26: keep summing.** Not a
  trade-off: the model is exactly linear in the inflow, verified to 4.7e-17, so
  solving the summed inflow and summing per-segment solutions give the same
  number. Running per segment buys per-segment *reporting*, not accuracy. What
  it did surface is that A–F and JA–JF are a near-even 49.3 / 50.7 split, so a
  coefficient measured on one family carries about half of any real difference
  into the total — and that what `J` means is written down nowhere upstream.
  DESIGN_04_01_carcomposition.md §3 has the working.

---

## 5. Things that will bite you

- **Getting `child_layer` wrong does not fail** on its own. It balances and it
  plots. §2. **Guarded since 2026-08-28**: a process keyed at a layer the
  composition never fills is refused, naming `child_layer` as the likely cause.
  That is the observable symptom, and it is checkable where the setting alone
  is not — nothing in the source table knows what the upstream files contain.
- **An upstream draw folder is never cleared, so it is the union of every run
  that has written to it.** A file is replaced only when a later run happens to
  emit the same name; change the element list upstream and the old names stay.
  Reading them together divides one run's element by another run's total, and
  `array[:draws]` on a short array returns what there is without complaint.
  **Guarded since 2026-09-01**: every array in a folder, and every product
  folder in a case, must agree on the draw count. That catches a mixed folder;
  it cannot say which run was wanted. DEFECTS.md §3.10 — it had already
  happened, and only tripped because the mix came to 1.81 and `rest` refuses
  parts exceeding the whole.
- **A coarse TC scales the resource's whole subtree**; a fine one does not.
  All TCs writing into one output flow must target the same layer, or nesting
  breaks — measured at 82 Mg on a shared loss flow. `01_check_inputs.py` checks
  this.
- **`rest` is derived, not written.** Per parent per year, `parent − Σ known
  children`, and it defaults to *unrecovered*. That is what makes every recovery
  figure a **lower bound** rather than an estimate.
- **Sampled maxima must not sum past 1 per resource.** If they do, the residual
  goes negative on extreme draws and the model produces negative mass — which
  balances perfectly and is nonsense. It happened: 17 of 278 resources in the
  first 04_01 table, surfacing as a negative 2.5th percentile on `ELV_loss_ASR`.
  `make_carcomposition_tcs.py` caps them. **Refused at input since 2026-08-28**,
  before a run rather than after — but only for groups that HAVE a residual row.
  Where every row is measured, conditioning enforces the constraint by
  weighting, so the same arithmetic is fine and refusing it would wrongly reject
  a measured case -- the deleted `bev_electronics_all_measured` summed to 1.34
  out of `F_collected` and was correct, which is what the test now pins with a
  fixture instead.
- **A complementary pair is not a defect.** Two REAL measurements of one split
  -- 0.85 recovered and 0.15 lost -- look exactly like one measurement counted
  twice, and multiplying their densities is CORRECT in the first case: two
  observations should narrow the answer. Arithmetic cannot separate them, only
  the `source` column can. The run stopped warning about it on 2026-09-03
  (DECISIONS 30); `tools/tc_worklist.py` reports it, names the group and has
  columns for the answer.
- **Do not manufacture a second measurement.** Conditioning is worth having
  only where the extra range was measured *without going through* the rest of
  the group. Both shortcuts were tried and measured:
  - clearing `is_residual` and leaving the bounds blank leaves the group one
    degree of freedom and no slack — every draw comes out identical, recovery
    pinned at a single value across 100,000 draws. `src/sampling.py` **refuses
    this** now, but it silently destroyed the spread before it did.
  - filling in `1 − the rest of the group` counts one measurement twice: the
    target becomes `f(x)·f(x)` instead of `f(x)`, narrowing the answer by about
    a fifth for no reason. Not refused — it cannot be told from a real second
    opinion by arithmetic alone — but `tools/tc_worklist.py` flags it, and
    `reference/template`'s loss rows are exactly this, so any demonstration of
    conditioning on that fixture measures squaring.
- **A high effective sample size does not mean a second range was worth
  having.** Two ranges that restate each other agree perfectly and keep nearly
  all of it. Effective sample size says whether ranges are *consistent*, never
  whether they are *independent*. Only the `source` column says that.
- **Four settings are read through `getattr` and look unused to any search.**
  `data.product`, `data.inflow_flow_id`, `data.material_suffix` and
  `data.group_marker` appear zero times at their point of use, because
  `src/source.py` reaches them through its `FALLBACK` table. Deleting them in a
  dead-code sweep would break every case without a `source` table, silently, and
  a 2026-08-28 sweep came within one step of doing exactly that.
- **Memory is `result rows × draws × 8 bytes`**, checked before allocating.
  Chunking bounds the working memory but not the result, so the levers are
  `run.years` and the case's `draws`.
- **Totalling the `Value` column quadruple-counts.** A deeper row is a
  *sub-quantity* of its parent. Total at each flow's own shallowest depth.
- **Coefficient totals must be grouped by `TC_target_key` and summed over
  `Output_FlowID`.** The obvious grouping produces numbers that are not
  quantities. MODEL_MECHANICS.md §4.

---

## 6. How to work with this user

Read this before doing anything. Every item cost time to learn.

1. **No command line.** Everything runs by pressing Run in Positron, no
   arguments, case chosen in `src/params_schema.py`. Step by step: `00`, `01`,
   `02`, `03`, `99`.
2. **Ask before adding anything** — no new file, tool, wrapper or intermediate
   step. A question wants an answer, not a project. `RUN.py` was added unasked
   and deleted the same day.
3. **Never delete. Never overwrite with different data.** Separate cases by
   **folder**, not by filename prefix. "Bring the old one back" means restore it
   verbatim from git and change only what stops it running.
4. **Never re-run an upstream stage to test.** Read what is already on disk.
   Never 200,000 draws for a test.
5. **Never conda.** venv and a pinned `requirements.txt`.
6. **Verify it yourself before showing it.** Open the figure. Check the number.
   Do not make the user find the bug.
7. **It has to work generally.** Write the failing test first, then generalise —
   `tests/test_generality.py` builds a PV panel case sharing no name with a
   vehicle, and runs it through both `child_layer` shapes.
8. **Be exact about provenance.** Never imply a placeholder is data.
9. **Do not invent data to make a feature demonstrable.** On 2026-08-26 a
   placeholder range was written for one row so conditioning would have
   something to do. It happened to be the exact reflection of the row beside
   it, so the demonstration measured one measurement squared and reported a
   21% improvement that did not exist — shown to the user in a figure and a
   table before anyone noticed. If a feature has nothing to act on, say that;
   it is a finding, not a gap to be filled.
10. **Document in the same commit as the change, and mean every document.**
    This used to name only RUNNING.md and CASES.md, and the two that drifted
    were the ones it did not name. On 2026-08-26 a sweep found DEFECTS.md still
    listing the mass balance, the Monte Carlo and unit conversion as absent
    capabilities — three things built days earlier — the index still saying the
    real TC table "does not exist yet", and `monte_carlo.enabled` documented as
    "off by default" while its value was `True`. Nothing there was hard to fix;
    it was simply never struck off. Building a thing and striking it off the
    list of things not built are one task, not two.

Settled conventions: **95% interval** on every distribution figure. Plain
figure titles.

**Units — three are in play at once, and this document uses all three.** The
data folders are written in **Mg**, the upstream pipeline delivers **kt**, and
the arithmetic and every output file are in **kg** (`run.working_unit`). The
inflow is converted on load, from whatever the file declares to the working
unit, so nothing is converted by hand. Figures pick a display scale per figure
— which is why §1 reports 640.7 kt while the summary file holds 640,684,957.
A wrong unit is a silent factor of 1000, so `src/units.py` is worth reading
before touching any of it.

---

## 7. Environment

Python **3.14 + pandas 3.0.5**, pinned, in `.venv`. Never conda. Positron is the
editor; `.vscode/settings.json` is committed so `.venv` is selected
automatically, and `ipykernel` is in `requirements.txt` for the console. Every
entry script calls `src/bootstrap.ensure_venv()`, so it re-execs under the
project interpreter whatever it was started with.

The pins are load-bearing. pandas copy-on-write silently changed this model's
intermediate results, and three inherited breakages came from it —
`DataFrame._append` removal, a `SettingWithCopyWarning` import, and a
`fillna(inplace=True)` that became a silent no-op and blew an intermediate up by
300,000×.

Setup on a fresh machine: [SETUP.md](SETUP.md).

If `~/Documents` starts returning permission errors after a Claude update, the
app needs restarting. It is not a code problem.

The same thing happens to the **iCloud Drive path** and it looks worse than it
is. On 2026-08-26 the whole project tree stopped being listable mid-session:
`ls`, `git` and even `python` failed with *Operation not permitted* — `getcwd`
and directory enumeration denied while individual files still opened by path,
and it persisted outside the sandbox, so it was macOS rather than any tool.
Restarting the app cleared it. Nothing was lost and nothing needed repairing.

---

## 8. The rest of the documentation

| document | what is in it |
|---|---|
| [DECISIONS.md](DECISIONS.md) | **what the user has settled. Read it first, and add to it.** |
| [RUNNING.md](RUNNING.md) | what to press, in what order, and what comes out |
| [CASES.md](CASES.md) | how a case is configured and why |
| [MODEL_MECHANICS.md](MODEL_MECHANICS.md) | how a result is actually computed. The nesting rule. **Read before reading any number.** |
| [DEFECTS.md](DEFECTS.md) | every defect found, with a measurement and a reproduction |
| [DESIGN_tc_table.md](DESIGN_tc_table.md) | how to build a TC table so sum-to-1 holds by construction |
| [DESIGN_04_01_carcomposition.md](DESIGN_04_01_carcomposition.md) | the 04_01 design, plus what building it proved the estimate had wrong |
| [DESIGN_monte_carlo.md](DESIGN_monte_carlo.md) | the Monte Carlo design; built, see `src/monte_carlo.py` |
| [PARAMETER_REFERENCE.md](PARAMETER_REFERENCE.md) | every setting and what it does. Generated — edit `src/params_schema.py`, not this. |
| [FILLING_IN.md](FILLING_IN.md) | **how to open the workbook and put real numbers in it.** Five steps. Written to be followed, not studied. |

The tools, none of which is a numbered step and all of which read the case from
`run.data_folder` unless given a folder:

| tool | what it answers |
|---|---|
| `tools/filling_sheet.py` | which coefficients to measure first, by what measuring one would buy |
| `tools/tc_worklist.py` | per sum-to-1 group, whether a second measurement would buy anything — and the two ways of faking one |
| `tools/compare_sum_rules.py` | which elements the choice between conditioning and normalising actually moves |
| `tools/plot_structure.py` | the flow network on its own, without solving |
| `tools/make_skeleton.py` | the TC rows a case needs. Merges, so it is safe to re-run |
| `tools/make_carcomposition_tcs.py` | the 04_01 table. Overwrites, and refuses once a row has been edited |
| `tools/compare_engines.py` | the two engines against each other |

The input file format is specified in `../doc/User guide.docx` (Harmjan de
Vries, 21-11-2024), still accurate on the schema. It does not describe model
behaviour; MODEL_MECHANICS.md does.

---

## 2026-09-04 — the result array moved to disk, and the year step matters

**The 5-year grid was hiding a real feature.** Net copper into the BEV fleet
falls to a trough at 2054 (36.8 kt/yr) and rises to a peak at 2058
(47.4 kt/yr). Sampling only 2055 and 2060 — 42.1 and 45.1 — draws a straight
line across it, which reads as a plotting bug and is not one. The origin is a
wave in the INFLOW: it dips to a local minimum of 473.7 kt in 2053 and rises to
532.3 kt in 2059, while the outflow rises smoothly with no feature at all. That
wave is in `RAWCLICStockAndFlow`, not here; this repository only reads the
exported arrays. Verified by reading the `.npy` files directly: the figure
reproduces them to better than 0.4%, and inflow/outflow/collected at 2070
(585.1 / 593.4 / 521.8 kt) match the figure's 585 / 593 / 522.

**So finer year steps are needed, and the memory model had to change.** The
per-draw result is `rows x draws x 8 bytes` and grows with the year count: the
boards case at every year and 200,000 draws is 16.6 GB on a 17 GB machine. It
is now MEMORY-MAPPED to a file in the case's `output_data/` whenever it exceeds
`monte_carlo.memory_budget_gb`, rather than the run being refused. The solve
already fills it one year at a time, so only the pages being written stay
resident; `plan()` sizes a chunk instead of raising; `MonteCarloRun.close()`
deletes the file once the summary and figures are written, and
`03_run_monte_carlo.py` calls it. Nothing above that changed and no figure
knows. Wiring at every year (51 years, 200,000 draws) runs in 2:48.

**`04_combine_cases.py` now writes three figures**, all copper, both cases
added per draw:

| figure | what it shows |
|---|---|
| `copper_combined.png` | the account: entering and leaving the fleet, reaching a recycler, recovered, and — DASHED — the two losses, never collected and lost inside recycling. Recovery rate on the right axis. |
| `copper_with_the_bev.png` | what the fleet holds: solid = in the fleet (left axis), dashed = added per year (right axis), for total and each of wiring, motors, PCB, sensors |
| `copper_lost.png` | the same five, for what is lost and not recycled |

The figure language, agreed the hard way over several hours and not to be
changed without asking:

- **nothing is drawn on top of the lines** — no labels, no numbers, no legend
  box inside the panel;
- **the legend is one strip under the x-axis label**, names only, no numbers;
- **total first, then the streams alphabetically**; total is black and the
  heaviest line; the four streams have four fixed colours (blue, red, green,
  orange) that do not change between figures;
- **one dash pattern, one meaning** per figure, said once in the legend;
- **the same unit on both axes**, four intervals each so one set of gridlines
  serves both, and the two zeros on the same line;
- **no stacks, no fills, no log scales.** Small streams are small lines.

`figures.resources` is copper only. `rest` is excluded everywhere as waste
(DECISIONS 40).

**The tests.** All 127 pass, in about six seconds for the whole suite —
`test_monte_carlo.py` alone is two. The disk-backed result has its own test,
`test_a_result_on_disk_is_the_same_result`: the same run is solved twice, once
in memory and once forced onto disk by a budget of a nanogram, and the two must
agree to the last bit. It also checks the file is created, and deleted by
`close()`, and that calling `close()` twice is harmless. That test exists
because the failure mode here is not a crash — it is a memmap that is not
flushed, or a dtype that differs, giving plausible numbers nobody checks.

| file | tests | covers |
|---|---|---|
| `test_monte_carlo.py` | 10 | chunking, seeding, mass and nesting per draw, **the result on disk** |
| `test_sampling.py` | 40 | the triangular draws, the sum-to-1 rules, the streams |
| `test_regression.py` | 30 | the ramp, TCs_improved being checked, closure and range faults |
| `test_generality.py` | 26 | nothing case-specific leaking into `src/` |
| `test_rest.py` | 9 | the derived `rest` child |
| `test_units.py` | 12 | conversion and display scaling |

**The structure is built once, not once a year.** Profiling a 51-year solve
showed 73% of the time in `Structure.__init__` -- pandas joins producing index
arrays, fifty-one times, identically. The network does not change with the
year: only the inflow, the composition VALUES and the coefficient values do,
and all three arrive as arguments to `evaluate`. `_shape_of` hashes each year's
KEY columns, and a year whose shape matches one already built reuses it through
`Structure.for_values`, a shallow copy that swaps `composition_values` alone.
It is a cache keyed on shape, never an assumption: a case whose rows differ by
year gets its own structure for that year. **51 years at 20,000 draws went from
9.67 s to 1.68 s**, a 5.8x speed-up, with all 127 tests passing and the answer
unchanged.

**Still open:** the boards case at every year has not been run — it needs about
17 GB of free disk while it runs. `years` is set to `'2020-2070, 1'`.
