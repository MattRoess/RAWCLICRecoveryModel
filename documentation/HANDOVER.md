# Handover

## 2026-10-08 — the battery is five cases, one per chemistry, and each has its own roads

**Built, tested, and every case checked on the real export. The study itself, `04_batteries.py`, has not
been run and is his; where things stand at the end of the day is the entry at the foot of this file.**
All of it is in `documentation/BATTERY_ROUTES.md`; the decisions are DECISIONS.md 42–52. The user asked on the day
whether the three main processes beside the pretreatment (hydrometallurgy, pyrometallurgy, direct
recycling) were in the model. Only hydrometallurgy was.

**What exists now**

- **Five cases**, `data/battery_lfp`, `_lmfp`, `_nmc_high`, `_sodium`, `_solid_state` — LFP and LMFP with
  hydrometallurgy and direct recycling, NMC_high with hydrometallurgy and pyrometallurgy, sodium with the
  paper's mechanical treatment (direct recycling prepared), solid-state with its cell handed on.
  `tools/build_battery_cases.py` wrote them from the paper, the report's Table 2 and `data/battery`, and
  refuses to overwrite one. `data/battery` is untouched and is no longer in `STUDIES['batteries']`.
- **Three sets of coefficients in each workbook**, `own` / `BAU` / `REC`, chosen by **`run.variants`**
  (`tc_set=own; sodium_route=mechanical`); a `variant` column in `TCs` and `TCs_improved`. Every choice has
  its own output folder, and stage 01 checks every version, not only the selected one.
- **`chemistries` in the source table**: a case reads and adds several upstream folders; an export folder
  no case names stops the run.
- **Handed-on mass** is neither recovered nor lost, and has its own line in the figures. The existing
  figures are byte-identical.
- **Upstream**, `RAWCLICStockAndFlow/code/04_04_batteries.py` now writes the recovery export per chemistry
  (`battery_recovery_draws_by_chemistry/`) and no longer sums it. **He ran it the same day**, about six
  hours, and the export checked out; the evening entry at the foot has the checks. See also its handover of
  the same date.
- Tests: all seven suites, 160 tests, pass. Documented: `BATTERY_ROUTES.md`, `DECISIONS.md`, `CASES.md`,
  `RUNNING.md`, `BATTERY_COEFFICIENTS.md` (two errors corrected), `BatteryStudy/README.md`.

**What to run, in order — the large runs are yours**

1. **Done, 2026-10-08:** in RAWCLICStockAndFlow `00_parameters.py`, then `04_04_batteries.py`.
   `data/processed/battery_recovery_draws_by_chemistry/` holds the 14 chemistry × scenario folders.
2. Here: press Run on `04_batteries.py`. Twelve passes. Stage 01 comes first and says what is wrong.
3. To see BAU or REC, change `run.variants` and press Run again; nothing is overwritten.

**What I got wrong on the way, and corrected** (the second and third in the same day they were said):
the REC lithium "dip to 0.50 in 2028" is the regulation's target, not a copy error; BAU does recover
manganese; and the deviations of the straight-line mapping were first computed on the target series
(`BATTERY_ROUTES.md` §4 has the right ones). Also a label: the casing, separator and unitemised mass was
first charged to the first road's process in the loss figure; it is `unresolved_material` now.

**Found in the user's own data, reported and not changed** (`BATTERY_ROUTES.md` §11): `data/battery` loses
its casing and separator silently (3.5 % of the cell stream, 2.1 % of what is collected, in S1); its S2 and
S3 are refused by its own input check; and its cathode rates are a blend of three chemistries, two of
them matching none.

**Decisions that are his, not taken**

- Put the five cases into `combine.cases` in place of `data/battery`? A case without the scenario stops
  05 (`BATTERY_ROUTES.md` §13).
- Add Fe, P, Mn, Na, C and Al to `figures.resources` of the batteries study (it has Cu, Ni, Co, Li).
- Retire `data/battery`, which nothing now needs but which still runs from the old export?
- The chemistry cases draw the same random numbers where a coefficient has the same name (correlation
  1.000); a `stream` key per case would make them independent. Left out as complicated.
- `own` borrows the paper's REC for the split between roads, pyrometallurgy, direct recycling and sodium;
  the 90 PLACEHOLDER rows of the 2030 table (20, 22, 20 and 28; `BATTERY_ROUTES.md` §4) and the dismantling
  of `batteryCellUnitemised` are his to confirm.

**Git.** This Mac's git had not been fetched since 2026-09-16 and held two stray refs from August,
`refs/heads/main 2` and `refs/remotes/origin/main 2`, that made `git fetch` fail with "bad object". The
reorganisation that `git status` showed as pending here was already on GitHub (`9ea56fe`, 2026-10-07), so
the battery work was committed and pushed (`96de773`) from a clean clone of GitHub's `main`. **Then, the same
day, git here was fixed, on his word:**

- the two stray refs were moved, not deleted, to `~/gitdirs/RAWCLICRecoveryModel.git/stray-refs-2026-10-08/`;
  they pointed at `e74504f` of 2026-08-14, which is on `main` anyway. `git fsck` is clean;
- the 52 commits that existed only on this Mac (09-17 to 09-25, 204 commits in all) are kept on the branch
  `local-history-2026-09-25`. All 45 files they touched are on GitHub, byte for byte in the 09-28 snapshot
  or changed again since; one, `tools/build_tractionmotor_shredder_case.py`, was removed on purpose in
  `e33d84c` of 09-29;
- `main` was moved to `origin/main` with `git reset --mixed`, which leaves the working folder alone. `git
  status` is empty and `main` equals `origin/main`.

RAWCLICStockAndFlow got the same: its two commits only on this Mac are kept on `local-history-2026-09-24`.
So the command in "The other Mini, whenever it is next opened" below has been done; its `--hard` form
would throw away uncommitted work, so use it only on a tree with none. **The rule stays: commit and push on
one Mac, pull on the other.**

## 2026-10-07 — the copyright notice and the licence

**52 of the 54 Python files carry `**Copyright notice:** Copyright © 2026 Empa, Matthias
Roesslein`** in the module docstring, after the title block, and **a new Python file must get it
too**. The two that do not are the engines this project received, `src/recovery_model_LA.py` and
`src/recovery_model_optimized.py`: 408 of 640 and 231 of 512 of their lines still come from the
first commit, "recovery model as received". The notice would claim code he did not write, so how
to mark them is his decision. Four of the 52 hold a few received lines as well and carry the
notice: `src/model_run.py` (7 of 77 lines), `src/selection.py` (18 of 235),
`tests/test_units.py` (3 of 222) and `tests/test_regression.py` (4 of 1,348).

`LICENSE` is CC BY 4.0, the official text. The README says what it does not cover: the two
engines, `data/reference/basic_test/` (byte for byte the received test case), `doc/User guide.docx`
(Harmjan de Vries) and the journal article in `documentation/BatteryStudy/`. A Creative Commons
licence cannot be withdrawn for copies already made. Checked before the push: the code is
identical outside the docstrings, and `99_check_all.py --code` passes in a sandbox clone (all seven
suites).

Found and not touched: `documentation/SETUP.md` still says the repository is private.

## GIT: DONE. `main` holds everything.

    origin/main   49195d6   2026-09-28   everything, both machines

Pushed on 2026-09-28. Nothing is left to run here and nothing is waiting on a
person. The temporary backup ref is deleted; `main` is the only ref.

### ⚠️ The other Mini, whenever it is next opened

It still has about twenty local commits from 09-17 to 09-25 -- the traction
motor work, `cb3f0ca` to `a4a2d5c` -- which were never pushed. **Their CONTENT
is in `49195d6` already**, because the working tree is the shared iCloud tree
and all of it was committed from this machine. What those twenty carry that
`main` does not is their MESSAGES, and nothing else.

So that machine is out of step with the remote, and one command fixes it:

    git fetch origin && git reset --hard origin/main

Safe: the working tree it resets to is byte for byte what is already on disk
there, because both machines share the same iCloud folder. Nothing is lost
except the twenty messages, and what they described is written up in the
09-24 and 09-25 entries at the foot of this file.

### Why it broke, so it is not repeated

`.git` was moved out of iCloud on 2026-09-22, because iCloud corrupted it. That
was done on the other Mini. What synced here was the one-line pointer file; the
directory it points at, `~/gitdirs/`, was never created on this machine, so
every git command here failed from 09-22 until 09-28. Restarting the editor
cannot fix it -- the directory was absent, not locked. It is attached now:

    ~/gitdirs/RAWCLICRecoveryModel.git   core.worktree -> the iCloud tree

**The rule, from RAWCLICStockAndFlow's handover:** *machines exchange work by
push and pull, not by iCloud. Commit and push on one Mac, pull on the other.*
Three weeks passed without that happening, which is how the two histories
drifted apart in the first place.

---

Current as of **2026-09-28**. Rewritten from the ground up on 2026-08-21 and
updated since; git has the older text. The newest entries are at the foot of
this file.

**READ THE 09-28 ENTRY AT THE FOOT FIRST.** The Sankey is drawn from the draws
now, and wiring it up exposed that every per-resource Sankey had been drawing
twice the real mass -- every traction motor case, every battery scenario, since
they were built. No table was affected. **Re-run 03 before trusting any figure
or workbook on disk**: they also predate the `Contributions` sheet.

**THEN READ THE 09-25 ENTRY, STARTING WITH THE DEFECT AT ITS HEAD.** Copper, aluminium and steel were being
solved correctly and then dropped before anything was reported -- the headline
table showed 0.56% of the recovered mass and 140 tests passed throughout. It is
fixed, but **every workbook and figure on disk predates the fix**, so re-run 03
before trusting any sheet you find there.

The four traction-motor cases -- the recycling work -- are the only cases here
whose coefficients come from a real source document rather than a placeholder.
They were finished on 09-24 and 09-25 and now all run from one press.

**IF YOU READ ONE THING ABOUT THE BATTERY, READ THE 09-17 ENTRY.** The battery case
went from unrunnable to running that day, the composition it is fed was
corrected at its source, and how a run is started changed: the parameter file
now says the case, the scenarios and the metals, and every numbered stage runs
the whole set.

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

**Added 2026-09-15: a third case, `data/battery`.** Fed by stage 04_04 of
RAWCLICStockAndFlow, which exports the mass of an element WITHIN a component for
this -- copper in a cable and copper in an electrode foil are 16.1 kg against
21.6 on a 60 kWh pack and go through different processes, so an element total
could not carry one coefficient right for both. The same holds for iron, which
is a steel frame on one route and LFP's iron phosphate cathode on the other.

The pack is dismantled two ways: the housing with the cables and terminals to a
shredder, the cells to their own liquid route.

**Updated 2026-09-17. It is now 17 processes, 18 flows, 87 TC rows, and all 87
are written.** The last 22 cells -- the 11 hydrometallurgy rates -- were
measured and entered by the user from his own research. The rest came from
precedent or from definition. **Nothing in this case is outstanding**; see the
09-16 and 09-17 entries at the foot of this file.

Its inflow arrives as `<upstream>/data/processed/battery_recovery_draws/`, 11
years 2020-2070, kilotonnes, summed over the chemistries. Two of those
chemistries have no described cell: sodium-ion's holds no CRM or SRM so its
absence costs this model nothing, while solid-state's holds lithium and there is
no coefficient to write for a composition that does not exist.

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
- `validate()` runs once per engine, and `stages/03_run_monte_carlo.py` builds four.
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
  `stages/03_run_monte_carlo.py` merges the deterministic answer onto the Monte Carlo
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
differs between studies is a **case**: a folder under `data/` holding

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
`stages/01_check_inputs.py` report and the figures now answer from the draws
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
- **`stages/01_check_inputs.py` has a `SUM TO 1` section.** A group's modes sum to 1
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
  breaks — measured at 82 Mg on a shared loss flow. `stages/01_check_inputs.py` checks
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
| `tools/compare_scenarios.py` | a case's scenarios side by side, after each has been run |

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
`stages/03_run_monte_carlo.py` calls it. Nothing above that changed and no figure
knows. Wiring at every year (51 years, 200,000 draws) runs in 2:48.

**`05_combine_cases.py` now writes three figures**, all copper, both cases
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

---

## 2026-09-16 — the battery case, filled where nobody had to choose

**65 of 87 coefficients are written. 11 hydrometallurgy rates are left, and
they are the user's.** He said so explicitly, twice. Do not fill them.

The principle behind the whole day: **a coefficient was written only where
there was no choice to make** — either another case had already answered it, or
the row had one destination and the value was forced. Everything that needed a
judgement was left empty and named.

### What was written, and on whose authority

| rows | what | where it came from |
|---|---|---|
| 36 | dismantling | **the user**: 0.95 / 0.98 / 1.00 to the proper branch, 0 to the other, 0.00 / 0.02 / 0.05 to waste |
| 19 | the shredder | **the electronics cases** — same shredder, same rates |
| 7 | `rest` → loss on the cell road | definitional, 1.0 |
| 3 | Si, cathode O, cathode Al → loss | one destination, so forced |
| 22 | **empty** | 11 hydromet groups: C, Li ×2, Ni, Co, Mn, Fe, P, Cu, Al ×2 |

### Three things that were not obvious

**Which branch a component takes was never a choice.** Each of the twelve
appears downstream in exactly one branch, so routing it to the other strands its
mass, which `validate_inputs` refuses: *"their mass stops there and disappears
from every total."* Five follow the housing — frame, module enclosures, thermal
conductor, cables, cell terminals — and seven follow the cells.

**The battery does not get the electronics pattern for imperfect dismantling,
and this is regulatory, not modelling.** Wiring and boards send what is missed
down the worse road: `stays_in_car` → `general_recycling`. **A battery pack must
come out of the car whole and no cell may enter a shredder**, so that road does
not exist here. What cannot be separated is waste at the dismantling step —
hence `F_loss_dismantling`, a third destination rather than a stray into the
other branch.

**Six element routes were missing and would have stranded mass.** The
composition names them: the anode is 47.7 kg of carbon and 5.9 kg of silicon at
80 kWh, and the cathode carries Al, O and P depending on chemistry. Two new
recovered flows were added — **`F_graphite`** and **`F_p`** — and
`currentCollectorAnode / Al` now reports to `F_al_cell`, because it is sodium's
aluminium anode collector. Si, cathode O and cathode Al are lost outright.

`F_p` takes a bare name like `F_li`, `F_ni`, `F_co`, `F_mn`. Only metals that
**also** come off the shredder carry the `_cell` suffix, so the two roads to the
same metal can be told apart.

### The improvement ramp now builds

The case declared `improvement_start 2030` / `improvement_end 2060` with no
`TCs_improved` table, so `case_tables.coefficients()` raised `ImprovementError`
— *"nothing says WHAT improves"* — and **no run could read a coefficient**. That
is fixed: 87 rows, same keys, same order. 435 rows across 2025/2030/2045/2060/2070.

The shredder improves, again from the electronics cases' own improved table:
Cu 0.60 → 0.85, Al 0.50 → 0.72, Fe 0.50 → 0.72. Definitional rows do not move.

> **Filling a hydromet rate means filling it TWICE** — a 2030 value in `TCs` and
> a 2060 value in `TCs_improved`. Both sheets carry all 87 rows.

### Two things left, and both are the user's

**Both were closed on 2026-09-17. Kept here because the reasoning still stands;
read the 09-17 entry for what they became.**

1. **The 11 hydrometallurgy rates.** No other case in this project uses
   hydrometallurgy, so there is no precedent to borrow. Lithium appears twice —
   from the cathode and from the electrolyte — and they need not be the same
   rate; electrolyte lithium is the harder one.
2. **The 2060 dismantling rate.** 95 / 98 / 100 is a 2030 number. `TCs_improved`
   currently **copies it across unchanged**, and every dismantling row's `source`
   column says so rather than hiding it. Every other case improves its
   disassembly: Motors 0.65 → 0.80, Wiring 0.90 → 0.96, PCB 0.85 → 0.95.

### Checking it

```bash
./.venv/bin/python tools/plot_structure.py data/battery
```

Draws the wiring with every coefficient beside its arrow, reads `TCs` and
nothing else, needs no result and solves nothing. It is the fastest way to see
what is still `nan`.

---

## 2026-09-17 — the two sheets had been swapped, and the case is now complete

**`TCs` and `TCs_improved` had their contents exchanged.** The working copy was
compared against 2040ccd row by row: the 2030 sheet carried the 2060 numbers and
the 2060 sheet the 2030 ones, across the 19 shredder rows and the `source`
column of all 36 dismantling rows. The case therefore got **worse** with time --
copper off the pack cables and cell terminals 0.85 in 2030 falling to 0.60 in
2060, aluminium and iron 0.72 falling to 0.50 -- while the electronics cases
those rates were borrowed from run 0.60 → 0.85 and 0.50 → 0.72. Seven recovered
rows fell across the ramp. None should.

**Nothing in the arithmetic complained, and nothing here would have.** Both
sheets still summed to 1 in all 45 groups, every value still sat inside its
bounds, every key still matched its partner in the same order. A swap of two
tables with the same shape is invisible to every check this repository owns.
What caught it was the `source` column: the 2030 sheet said *"the same shredder
in 2060"*. **There is still no assertion that a recovered flow cannot fall from
`TCs` to `TCs_improved`** -- that is the test this defect asks for, and it is
not written yet.

Corrected. Every value and every key in the case is now exactly what 2040ccd
holds, except the 22 cells the user entered.

**The 11 hydrometallurgy rates are in, and they are the user's own research.**
He entered them himself and said so: *"I did for this an independent research."*
The 09-16 instruction not to fill them is discharged. Both ends of the ramp:

| resource | 2030 | 2060 |
|---|---|---|
| cathode Li | 0.85 | 0.96 |
| electrolyte Li | 0.85 | 0.96 |
| cathode Ni | 0.95 | 0.99 |
| cathode Co | 0.95 | 0.99 |
| cathode Mn | 0.90 | 0.98 |
| cathode Fe | 0.80 | 0.94 |
| cathode P | 0.80 | 0.94 |
| anode graphite | 0.50 | 0.70 |
| anode collector Cu | 0.85 | 0.92 |
| anode collector Al | 0.72 | 0.85 |
| cathode collector Al | 0.72 | 0.85 |

Each of those 22 cells carries a `source` saying it is his own research and
naming the year it applies to. **Replace that wording with the actual reference
when there is one** -- it records who entered the number, not where it was
measured.

**The 2060 dismantling rate is decided: it does not improve.** The user,
2026-09-17: *"there will be never a 100% dismanteling."* 95 / 98 / 100 holds in
2060 as well, and all 36 dismantling rows in `TCs_improved` now say that is the
decision rather than *"no 2060 rate chosen yet"*. This case is the one that does
not follow Motors, Wiring and PCB in improving its disassembly, and the reason
is physical, not an omission.

**Lithium arrives on two roads and the model treats them as PARALLEL, not as
steps.** `cathodeActiveMaterial → F_li` and `batteryCellElectrolyte → F_li` are
two separate sum-to-1 groups: each routes its own component's lithium, and the
two add into the same recovered flow. Nothing in this model can express one
process feeding another -- a coefficient is always the fraction of THIS
component's element reaching THIS flow. So one measured whole-cell yield on both
rows is a correct reading, which is what the case now holds.

**How much the electrolyte rate can matter, measured.** On the S1 collected
draws, `Li__batteryCellElectrolyte` against `Li__cathodeActiveMaterial`, mean
over 200,000 draws: the electrolyte holds **3.6%** of the collected lithium and
the cathode 96.4%, steady across all 11 years (2070: 3.40 kt against 86.92 kt).
Taking the electrolyte rate to zero would move recovered lithium by 3.6%. If the
research number turns out to be a black-mass leach yield rather than a whole-cell
one, that is the size of the error it can cause.

**One claim in the 09-16 entry above was wrong.** It presents the 11
hydrometallurgy rates as empty in both sheets. At 2040ccd, 7 of the 11 already
carried a 2060 value in `TCs_improved` -- 0.85, 0.95, 0.95, 0.90, 0.85, 0.85,
0.72 -- every one of them still labelled `EMPTY -- to be provided. No value is
written`. Those are the values that landed in `TCs` when the sheets were
swapped. Nothing in this file says where they came from.

**Also repaired, and it predates the swap:** the 24 dismantling rows in `TCs`
carried `EMPTY -- to be provided. No value is written` while holding 0.98. They
now say what their 12 loss partners have always said -- *"assumed: 95/98/100%
dismantled, the rest cannot be separated"*. No `source` cell in either sheet is
blank now, and none claims to be empty while holding a number.

---

## 2026-09-17 — the battery runs, and the parameter file says how

Twenty-five commits. The case was unrunnable at the start of the day and had
never been solved once; it now runs all three scenarios at 200,000 draws and
joins the combined figures. What follows is in the order it was found, because
each thing was hidden behind the one before it.

### The two sheets had been swapped

`TCs` held the 2060 numbers and `TCs_improved` the 2030 ones, across the 19
shredder rows and the `source` column of all 36 dismantling rows. The case got
**worse** with time -- pack cable copper 0.85 in 2030 falling to 0.60 in 2060,
against 0.60 → 0.85 in the electronics cases it borrowed them from.

**Nothing in the arithmetic complained.** Both tables summed to 1 in all 45
groups, every value sat inside its bounds, every key matched in the same order.
A swap of two same-shaped tables is invisible to every check here. What gave it
away was the `source` column: the 2030 sheet said *"the same shredder in 2060"*.

`test_regression.py` now refuses a recovered flow that falls from `TCs` to
`TCs_improved`, with a second test on a swapped pair so weakening the first
cannot leave a suite that passes on four healthy cases. Only a **recovered**
flow can be asserted -- `F_in_car` legitimately falls, and less of it is the
improvement -- so the case's own `role` column decides.

### Three things refused the case, none of them its coefficients

1. **`years.npy` is not always at the scenario root.** 04_02 writes one per
   scenario for all three flows; 04_04 writes one inside each flow folder. The
   reader knew only the first layout and refused the battery before reading a
   single array, which is why it had never been run. Both layouts hold the same
   years -- all nine of the battery's are identical -- so the flow folder is
   tried first and the root second.
2. **The stranding check assumed every resource reaches every flow.** True of a
   case whose branches all carry the same components, false of a pack that
   sends the housing to a shredder and the cells to a liquid route. It asked
   for cable copper to have an exit from the cell road. `_what_reaches` follows
   the coefficients now, from the flows mass enters by, ON WHOLE COMPOSITION
   ROWS -- following it layer by layer makes the check silent instead, because
   an element moved by a component-keyed row never appears to have moved.
3. **The fraction check had no tolerance.** An upstream composition is computed,
   not typed. 1e-3 now, and the measurement is in the comment.

### The composition was wrong at its source, and was fixed there

The recovery model was refusing a negative `rest`. The cause was two defects in
`RAWCLICVehicleBattery`'s workbook, both of the same shape -- a share changed
without its siblings being reduced:

| | was | is |
|---|---|---|
| the two NMC anodes, C | 1.0123 of the anode | `C := c-p - Si` |
| `battLiMFP` cathode | Mn and Fe at 1.479x stoichiometry | the five rows partition `c-p` |

The LMFP one was found by asking why lithium looked short. It was not: oxygen
and phosphorus were short by the same 0.7395 while manganese and iron sat at
exactly twice it -- a full formula unit each instead of the half that
LiMn(0.5)Fe(0.5)PO4 carries, normalised back to 100% afterwards. **The lithium
override in `params_schema` was a patch on that symptom and has been removed**;
lithium arrives at 4.408% on its own. **LMFP manganese and iron demand falls by
about a third.**

**What is left over is float32 and nothing else.** The workbook's rows sum to
their component to 3.3e-16; what this model receives runs up to 2.3e-4 over,
because the chain interpolates between capacity anchors and stores float32. So
`rest.py` gained `OVERSHOOT_TOLERANCE = 1e-3`, separate from the 1e-9 that says
how far a parent may fall SHORT -- a different question deserving a different
number. The two defects above sit a factor of 50 above it and are still
refused, which is pinned by a test both ways.

⚠️ **BELOW ABOUT 5,000 DRAWS THAT TOLERANCE IS TRIPPED.** The overshoot is
sampling noise: 2.3e-4 at 200,000 draws, about 1.4e-3 at 2,000. A low-draw run
is refused on arithmetic, not on data. Scale the tolerance with the draw count
before loosening it; loosening costs the guard that caught 1.0115.

### Scenarios: the battery has three, and the run is one press

The battery is exported as S1, S2 and S3 and no single one of them is the
answer. Four things had to change for that to work:

- **The scenario was thrown away after picking a folder.** `upstream.load`
  stamps it on the frames now, so `run.scenario` is usable at all for an
  upstream case.
- **THE SCENARIO HAD TWO SOURCES OF TRUTH.** The stages set it on the params
  they walk; the engine built a `Params()` of its own and could not see it.
  Every construction passes it now -- `model_run`, `plot_flows` twice,
  `monte_carlo`, 03 twice -- AND every caller of `solve_draws`, which builds an
  engine too. That second list is where this bit twice: three of its five
  callers were wrong.
- **Results and figures are per scenario.** `output_data/<scenario>/` and
  `figures/<case>/<scenario>/`. Before, the third run overwrote the first.
- **A case may rename the run's scenario.** `scenario_alias` in its own
  `source.csv`: the electronics carry `*=BAU`, because 04_02 writes one folder
  while 04_04 writes three. Delete the line the day 04_02 exports scenarios.

**All four numbered stages now run every scenario the case has**, resolved once
in `upstream.scenarios_to_run`: `--scenario` wins, then `run.scenario`, then the
case's own export. One pass is still one scenario; this decides how many passes
a command makes, not what a pass does.

### The parameter file is the interface

The user runs by pressing Run in Positron. A setting that exists only on the
command line does not exist. So:

- `run.data_folder` is `data/battery`, the case being worked on.
- `combine.resources` replaced `combine.resource` + `combine.label`: a mapping
  of label to every spelling the data uses. Pressing Run on 04 draws **four
  metals across three scenarios**, twelve sets of figures, nothing typed.
- **04 was the only numbered stage without the `ensure_venv` bootstrap.** It
  worked for as long as it happened to be started with `./.venv/bin/python` and
  died on `import matplotlib` the first time Positron ran it. Pressing Run on
  04 had never been possible.

⚠️ **POSITRON KEEPS ONE PYTHON SESSION ALIVE.** After anything under `src/`
changes, restart it or the old modules are still in `sys.modules`. A whole
evening was lost to a failure that had already been fixed on disk.

### An element-keyed case propagates its draws

`Draws.propagates` was true only for the `material` shape, so the battery
broadcast a MEAN share across every draw and `account` returned `None` for it --
it sat in `combine.cases` contributing nothing to a figure that named three
cases. It propagates now WHEN THE EXPORT NAMES NO MATERIALS, which is the
battery: Layer 3 is a placeholder for the whole component, so the middle level
is an identity. An element-keyed case that DOES name materials still refuses;
that needs `_material_and_element_rows` reproduced per draw.

Measured: all 19 exported Layer-4 rows rebuild from the chained shares to
**2.7e-16**, and the battery contributes 380 kt of copper in 2070 against the
381 kt its own run reports.

### The figures

New: **`<metal>_recovered.png`**, the total and each stream, which is the only
figure that answers where a metal comes back from -- the question as soon as a
run holds more than one case. And **`tools/compare_scenarios.py`**, a case's
scenarios side by side.

**UNCERTAINTY COMES FROM THE DRAWS, NEVER FROM ADDING INTERVALS.** Percentiles
of the sum per draw, not the sum of two cases' percentiles; a ratio pooled per
draw, not a ratio of two medians. `compare_scenarios` SOLVES each scenario for
this reason -- a saved summary keeps percentiles and drops the draws, and there
is no way back. **It changes the answer**: pooled battery recovery went
49.4→64.1% to 59.1→77.0% and the scenario ordering flipped. Only nickel and
cobalt separate the scenarios; aluminium, iron and phosphorus overlap entirely.

`with_the_bev` and `lost` are **two stacked panels** now, not one panel with a
twin axis. One panel could not carry a band on both totals: the axes are tied
so their zeros align, so making room for one band rescales the other. Filled,
the two bands were the same grey and crossed; dashed, they read as more lines;
ruled to fit, the left axis doubled. Split, each has its own band and the dash
code is gone -- colour means stream and nothing else.

Also: ten stream colours, because four wrapped and put `wiring` and
`currentCollectorAnode` in the same green; a legend that wraps at five; and
`_short` splits camelCase and strips the metal BY SHAPE -- matching the literal
word `copper` meant every nickel legend read "nickel in wiring".

### Open

- **`tools/compare_scenarios.py` reads `figures.resources`**, not
  `combine.resources`. Two lists of metals, and they can drift.
- **The combine re-solves wiring and boards for every scenario**, and their
  alias makes those answers identical -- two thirds of the work in a
  three-scenario run. Not cached on purpose: a combine that quietly reused
  another scenario's solve would be the hardest kind of wrong to notice.
- **On a metal the battery dominates, the stream line hides under the total.**
  Nickel's `cathode active material` is the total, so its legend entry has no
  visible line. Drawing the total beneath the streams would fix it and cost the
  "total is the topmost line" convention.


---

## 2026-09-24 — the traction motor, and the first real coefficients

**Two cases, both running, and every coefficient traceable to a published
source.** That is new here: the electronics cases still say `PLACEHOLDER
(Claude, not data)`, and the battery's came from a paper read by hand. These
came from a document written for this purpose.

### What the source is

Two files, handed over today, in `~/Downloads/TractionMotor/`:

| | |
|---|---|
| `RAWCLIC_BEV_Motor_Recycling_Report_V1.md` | 959 lines, EMPA / RAWCLIC, September 2026 |
| `RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx` | 9 sheets, 2030 and 2060 × two routes |

⚠️ **The report and the workbook disagree about how much is known, and the
workbook is the one that looks like data.** The report's own finding 9 is *"No
evidence-supported full-chain TC exists for 2030 or 2060"* and its §5.2 table is
almost entirely `NR`. The workbook then fills those cells with Min|Mode|Max
anyway. It labels them as scenario assumptions, legitimately — but anyone
reading only the workbook will not notice that its numbers are a construction.
**Every coefficient in both cases is a scenario assumption. None is measured.**

### The two routes, and what actually separates them

The fork is at the magnet, not at the motor:

| 2030 | disassembly | shredder | |
|---|---|---|---|
| Nd, Pr, Dy, Tb | 0.41 | 0.016 | **26×** |
| Cu | 0.64 | 0.59 | 1.1× |
| Al | 0.66 | 0.61 | 1.1× |
| **electrical steel** | 0.60 | **0.72** | **0.8×** |

**Shredding is not the bad route.** It recovers copper and aluminium within
10% of disassembly and recovers *more* steel, because laminations report
cleanly to the ferrous fraction where careful dismantling loses some. What it
destroys is the magnet. By 2060 the magnet gap narrows from 26× to **2.4×**,
but only because the review's 2060 shredder is a different process —
controlled shredding after demagnetisation, inline magnetic separation, then
hydrometallurgy of the concentrate.

### The cases

| | |
|---|---|
| `data/tractionmotor` | Route A, selective disassembly. 39 TC rows, 20 processes |
| `data/tractionmotor_shredder` | Route B, shredding. 27 TC rows, 16 processes |

Both are **generated**, not hand-edited: `tools/build_tractionmotor_case.py`
and `tools/build_tractionmotor_shredder_case.py`. Re-running either rebuilds
its workbook from the coefficients written at the top of the script, so the
chain from source document to case is one file to read.

`TCs` is the review's **2030** column and `TCs_improved` its **2060** column,
so the report's two horizons became the improvement window rather than two more
cases.

**The check that matters:** both cases reproduce the review's own end-to-end
coefficients to rounding, for every material and both horizons, with nothing
fitted to make that happen. Disassembly 2030 Nd 0.406 against 0.41 and Cu 0.636
against 0.64; 2060 Nd 0.648 against 0.65. Shredder 2030 Cu 0.588 against 0.59;
2060 Nd 0.265 against 0.26.

### One deliberate departure from the workbook

Its 2030 shredder sheet gives the magnet chain as **0.02**, which is the *step*
value quoted as the chain: upstream capture and feed are not applied to it,
although they are applied to copper, aluminium and steel on that same sheet,
and although the 2060 sheet **does** apply them to the magnet. Applied
consistently the 2030 magnet chain is **0.0157**, and that is what the case
uses. Written at the top of the shredder builder.

### The upstream, which did not exist this morning

The recovery model reads `.npy` draw arrays. `04_03_tractionmotors.py` computed
a 200 000-long distribution for every flow and year and then discarded it,
writing only percentile CSVs. `RAWCLICStockAndFlow/src/traction_export.py` now
writes the draws:

```
data/processed/traction_recovery_draws/<grade>/<flow>/
    years.npy                        2020-2070, 11 years
    __component____<material>.npy    (200 000, 11) float32
    <element>__magnet.npy            Nd, Pr, Dy, Tb
```

72 arrays, 604 MB, four grade folders, two flows.

### Why grade is a scenario and route is a case

The scenario axis picks an **upstream folder and nothing else** —
`scenario_alias` "maps a NAME to a FOLDER". It cannot change a coefficient. So
treatment is a case and what-arrives is a scenario:

| what varies | mechanism |
|---|---|
| route | case folder |
| magnet grade | scenario / upstream folder |
| 2030 → 2060 | `TCs` → `TCs_improved` |

⚠️ **And SH/UH/EH is nothing like the battery's S1/S2/S3.** S1/S2/S3 change
*which elements exist* — an LFP pack has no nickel. The magnet grades change
**two numbers**: Nd and Pr are byte-identical in all three classes, because the
workbook's 0.29–0.32 didymium applies to every one. Only Dy, Tb and the iron
that compensates move.

| share of magnet | SH | UH | EH |
|---|---|---|---|
| Nd | 0.2559 | 0.2559 | 0.2559 |
| Pr | 0.0489 | 0.0489 | 0.0489 |
| Dy | 0.0551 | 0.0751 | 0.0900 |
| Tb | 0.0025 | 0.0050 | 0.0050 |

So the default is the **`mix`** folder, which draws the grade class per draw —
a fleet is a mixture, and averaging the three would build a magnet that exists
nowhere, since the SH and EH dysprosium ranges do not overlap. `SH`, `UH` and
`EH` are pinned and exist for exactly one question the user asked: *what if
only EH is feasible, because of China*. That is `run.scenario = 'EH'` and
nothing else changes.

**This rests on one assumption worth stating**: that no transfer coefficient
depends on concentration — that hydrometallurgy does not recover dysprosium
better from a 9% feed than a 5% feed. The documents report flat fractions per
element, so nothing there contradicts it, but it is an assumption.

### Four things that went wrong, and how each was caught

None was found by reading carefully. Each needed something to fail.

1. **`Input_layer_key` names the PARENT of `TC_target_key`.** A row moving a
   component is keyed at the *product*, whatever flow it leaves. Keyed at the
   component itself it matched nothing — the checker named all five groups
   stranded, by name.
2. **The metals target the MATERIAL layer, not the element layer.** Copper,
   aluminium and both steels have no element arrays upstream, so their mass
   never reaches the element layer and there is no `rest` there to catch it.
   Aimed at `element`/`rest` they came out as **zero recovered** while the
   magnet worked, because the magnet *does* have element children.
3. **One flow per stream, and separate loss flows.** A shared shredder flow let
   the magnet leave at the element layer while the metals left at the material
   layer; the checker found the magnet stranded at material depth. And one
   shared loss flow written at two layers breaks the nesting invariant.
4. ⚠️ **The export was in kilograms where the contract is kilotonnes, and
   NOTHING FAILED.** The traction total at 2050 read 9.43e8 against the
   battery's 4281. It was caught only by comparing magnitudes with the battery
   — 943 kt against 4281 kt is a ~100 kg motor against a ~400 kg pack, which is
   right. **A factor of a million that survived every structural check.** If
   another upstream is ever added here, compare its magnitude against the
   battery before trusting anything.

### Where to continue

`run.data_folder` is left at **`data/tractionmotor_shredder`** and
`run.scenario` at **`mix`**.

1. **Monte Carlo**, `stages/03_run_monte_carlo.py`, both cases, all four grade
   folders. The point of the whole chain and not yet run once.
2. **Combination figures**, `05_combine_cases.py` — the two routes on one
   panel is the comparison the user has been driving at all day.
3. **The second fork is still unmodelled.** Inside disassembly the review has
   short-loop hydrogen decrepitation (HD/HPMS) as an alternative to
   hydrometallurgy: it keeps the alloy intact, skips elemental separation
   entirely, and returns Dy and Tb *where they already are*. The workbook gives
   it no end-to-end coefficient, so neither does the case. It changes the
   **shape** of the recovered output, not only the amount.
4. Copper, aluminium and both steels **stay materials** — decided 2026-09-24.
   Not a gap.

---

## 2026-09-25 — all four cases from one run, and a reporting defect that hid 99% of the mass

Fifteen commits, `cb3f0ca` to `a4a2d5c`. The four cases were finished and run;
then a defect was found that had been silently dropping most of what the model
recovers, in every case, since the traction motor work began.

### READ THIS FIRST: copper, aluminium and steel were solved and never reported

The headline `Recovered` table and every per-resource figure showed **Dy, Nd,
Pr, Tb and nothing else** — about **0.56% of the recovered mass**. Copper alone
is nineteen times the whole rare-earth output by weight, and it has its own
four-panel figure upstream (`04_03_1_copper.png`, asked for on 2026-09-21).

Recovered mass in 2050, `tractionmotor`/`mix`, mean of the draws:

| | kt | was reported |
|---|---|---|
| steel (lamination 229.3 + steel 242.1) | 471.4 | no |
| aluminium | 136.5 | no |
| copper | 47.0 | no |
| Nd / Dy / Pr / Tb | 2.5 / 0.68 / 0.47 / 0.04 | yes |

**One assumption, in three files.** `finest_layer()` answers with a single
layer column for a whole case, and this case MIXES DEPTHS: the magnet resolves
to elements at Layer 4, while copper, aluminium, steel and lamination stop at
materials in Layer 3. Layer 4 wins because the rare earths fill it, and then
`summary[layer] != ''` deletes every metal row. `src/plot_flows.py` was explicit
about it, falling back to Layer 4 whenever flows disagreed — read as protecting
the *"no output flow is written at mixed layers"* check, but that check forbids
ONE FLOW mixing layers, not a case whose different flows sit at different
depths, which is exactly what this is.

Fixed in `5027967`: each row is asked for its own depth (`report.resource_of`,
`plot_monte_carlo.resource_key`, `plot_flows.resource_of`), the same rule the
mass balance already used. `figures.resources` also had to grow — before the
fix its five names matched nothing here so the figure code fell back to "all";
after it, the old list would have narrowed every figure to copper alone.

⚠️ **This was not found by testing.** 140 tests passed throughout. It was found
because the user asked where the copper figure was.

### All four cases run from one press

`run.data_folder` now reads several folders separated by semicolons, as
`groups` and `scenario_alias` already do. `src/upstream.cases_to_run` splits it
and stages 01, 02, 03 and 99 loop over it (`9283475`).

Each case **puts `run.scenario` back before it starts**. The scenario loop
writes into that field, so without the restore every case after the first
inherited the last scenario that ran — the first case did all four grades and
the other three silently did only `mix`. Found by running it.

### Contributions: what made up each total

`Recovered` says how much Nd came back, not from where. `Contributions`
(`7fb58bf`) gives one row per contributing flow with its own interval and its
share. Split case, 2050: **Nd is 64.5% long loop (1.664 kt) and 35.5% short
loop (0.917 kt)**. Shares are of MEANS, which add exactly; the intervals are
each flow's own and do NOT sum to the total's.

Intervals for a resource arriving by several flows now come from the **draws**.
Adding two flows' p50s is not the median of their sum. Measured on Nd in 2050:
the naive percentile sum puts p2.5 **5.4% low** and p97.5 **4.7% high**. Single
-flow groups are unaffected — both agree exactly.

### Figures

`a5cdda0`: every y axis in 04 is pinned to **kt** (`AXIS_UNIT`) and a rate axis
carries `/year`. It mixed Mt and kt, and half the panels labelled an annual
flow with a bare mass unit.

`752abcc`: `_one_panel` claimed "both panels share a scale, so a height in one
compares with a height in the other". They share the UNIT. Each panel is ruled
to its own data, so the heights do NOT compare. The claim went, the behaviour
stayed.

`a4a2d5c`: **`plot_flows.figure_for_draws`** — the Sankey from the draws
instead of one point solve. Ribbons are means (the only central value that
balances: means add), each node prints its 95% interval. **NOT WIRED INTO ANY
STAGE.** 02 still draws the deterministic ones. Decided jointly: it stays a
tool. Its limits are real and it does not remove them — one year out of eleven,
and a ribbon cannot carry a range (`F_loss_ree` is 277,622 with an interval of
150,737–436,888, a factor of 2.9, drawn as one fixed width).

### The standing rule, stated twice today

**Every figure must be Monte Carlo generated and show uncertainty ranges.** All
02 figures fail it — `replay()` re-runs the model on point values, so every
Sankey and `structure.png` is a single number with nothing behind it. 03's
figures pass (`spread`, `mode_vs_mean` and `sensitivity` carry no band because
uncertainty IS their subject). 04 bands the total only, by choice.

**Check the stock-and-flow for what is significant** before calling a case
reported. The upstream export says which resources exist; the upstream FIGURES
say which ones matter.

### Where to continue

`run.data_folder` is all four traction motor cases, `run.scenario` blank
(= all four grades). 01 and 02 verified over all 16 passes, exit 0. 03 was run
by the user at 15:00–15:18.

1. **Re-run 03.** Its summaries are from 15:18, BEFORE the mixed-depth fix, so
   every workbook on disk still has the four-rare-earth `Recovered` sheet and
   no `Contributions`. Nothing is wrong with the numbers in them; the sheets
   are just missing most of their rows.
2. **Audit 03's figures** for ranges, one by one. This was agreed as the next
   task and is not started.
3. **04 does not cover this work.** `combine.cases` is wiring + boards +
   battery; `combine.resources` is copper, nickel, cobalt, lithium. No traction
   motor case and no rare earth. Note that 04 ADDS cases — parts of one car —
   whereas the four traction motor cases are the same motors down competing
   routes, so they must be COMPARED, not summed. That figure does not exist.
4. **The schema figure still quotes the chain of modes** (0.406, 0.674, 0.265).
   That is not the mode of the result and not any percentile — the
   deterministic run sits 1.5% from the mean on the median flow and 19.1% out
   at worst. Restate from the draws or label it for what it is.
5. `scenarios_to_run`'s `named` parameter is a leftover from `--scenario`; no
   stage passes it. Documented as the override hook it is, not removed.

## 2026-09-28 — the Sankey is Monte Carlo now, and it was drawing double

Asked for in one line: *"yes wire it into 03, I want full MC"*.

### What was wired

`plot_flows.figure_for_draws` was written on 09-25 and called by nothing --
not a stage, not a tool, not a test. `plot_monte_carlo.draw_all` now calls it
for the total and for every resource `chosen` covers, in the LAST year, and
writes them under the names 02 uses. So a full pass (02 then 03) leaves one
Sankey per resource and it is the Monte Carlo one. DECISIONS 27.

Each node prints its mean and its 95% interval; the ribbon width is the mean,
because means add and the picture has to balance. Both limits -- a ribbon
cannot carry a range, and this is one year of eleven -- are on the figure.

⚠️ **`magnet.png` and `rest.png` stay deterministic.** 03 draws what
`figures.resources` names, and that list has no `magnet`; `rest` is excluded on
purpose (it is waste, not a material). Those two files keep whatever 02 wrote,
in a folder where everything else is Monte Carlo, and only the subtitle says
so. Add `'magnet'` to `figures.resources` to close half of it.

### What it exposed: every per-resource Sankey was drawn at 2x

    F_collected, copper, 2070:   drawn 141,089,503 kg      true 70,544,752 kg

Every resource of every traction motor case, and all twelve components of the
battery, in all three scenarios, since the cases were built. `resource_of`
gives a row the value of its own deepest filled layer, so a component `copper`
holding a material `copper` answers `copper` on both rows -- and the child is
the whole of its parent, so they carry the same mass. `mass()` added them, under
a docstring promising it did not.

**It did not reach any table.** The `Recovered` sheet and every recovered-flow
figure read flows where each resource sits at one depth -- checked across all
nine cases. Only the Sankeys were wrong, and the Sankey is the one figure
nobody reconciles against a table, which is why it survived.

**It surfaced because the Monte Carlo version prints numbers.** `F_cu_stream`
at 123.5 M kg with 61.8 M leaving it does not balance. The deterministic
Sankey had been drawing the same doubled masses for weeks with nothing on it to
contradict them. DEFECTS 3.21, and 3.22 for the caption that ran off the page
and the interval labels that collided.

### Copper's account figures, and why there were none

The battery and electronics cases draw `account`, `losses`, `trapped` and
`fate` per resource. The traction motor cases drew none of them, silently. All
four hang off `account()`, and two separate things stopped it -- the traction
export had no `outflow` folder, and `other_flow` could not address a resource
exported AS a component (`__component____copper.npy`, where it looked for
`copper__copper.npy`). Both are fixed: DEFECTS 3.23 here, and
`RAWCLICStockAndFlow` 2026-09-28 for the export.

**04_03 was re-run the same day** and the export is now three flows, 108
arrays, 950 MB, same nine array names in each, all `(200000, 11)`. Copper has
its account, losses, trapped and fate figures, the same four the battery and
the electronics cases have.

⚠️ **Drawing them found the double count a third time** -- `account()` read
copper's collected mass as 140.94 kt against a true 70.47, and because
`recovered` comes from flows holding ONE depth while `collected` comes from
flows holding two, copper appeared to lose 91.7 kt of the 70.5 it had. It
closed to 0.00e+00 the whole time, because closure is by construction.
DEFECTS 3.24. Fixed with `own()`, applied at all twelve row selections that sum
mass.

⚠️ **The collected share is a FIXED 0.88**, identical in every draw, year and
resource -- `sd 5.3e-08`. The battery's is drawn (`04_04_batteries.FLOWS`
notes 03_02 draws those shares); 04_03's is not. So "never collected" on these
figures is a flat 12% of the outflow with no band of its own, which the figure
draws honestly as a flat line. This is upstream open item 4.1d -- 04_03's
vehicle counts are deterministic -- showing up in a new place.

### Where to continue

Unchanged from the 09-25 list except that these figures now need the re-run
too:

0. **Re-run 04_03 upstream**, which now exports `outflow`. Until then copper
   has no account figure and neither does anything else.
1. **Re-run 03.** Still the first thing here. Every workbook on disk is missing its
   `Contributions` sheet -- the code writes eight sheets, the files hold seven
   -- and now every Sankey on disk is a doubled deterministic one.
2. **Audit 03's figures for ranges**, one by one. Not started. `account`,
   `trapped`, `losses` and `fate` return None for all four traction cases,
   because they need `run.upstream.propagates` and the traction export does not
   carry the inflow/outflow arrays. `routes` returns None correctly -- each
   case is one road, and the road comparison is `tools/compare_routes.py`.
3. **`compare_routes.py` covers the four rare earths only.** Copper, aluminium
   and steel differ by route too -- 0.64 against 0.59 for copper -- and are not
   compared anywhere.
4. The schema figure still quotes the chain of modes. Unchanged.

---


---

## 2026-09-28 (later) — three studies to press, and the stages out of the way

**The project root now shows what to run and nothing else:**

    00_parameters.py          the settings, checked, and the two files it writes
    02_electronics.py   \
    03_tractionmotors.py > the three studies -- press ONE of them
    04_batteries.py     /
    05_combine_cases.py       adds cases together; its own settings
    99_check_all.py           the suites, then the pipeline and a mass balance
    stages/                   01, 02, 03 -- run by the study files, not by you

⚠️ **The study numbers are the UPSTREAM stage that feeds each one** -- 04_02,
04_03, 04_04 -- not steps in a sequence here. The three are alternatives.

`combine_cases` was `04_` until 2026-09-28 and became `05_` the same day: on
the reading above its `04` claimed an upstream stage that does not feed it, and
it sat next to `04_batteries.py` meaning something else. Nothing feeds it -- it
adds cases this model has already solved.

The stages kept their numbered names inside `stages/`, so every mention of
`03_run_monte_carlo.py` in these documents still finds the file. They still run
on their own.



*"at the moment we are running in recovery electronics, battery and
tractionmotors using different parameters setting. This proves not efficient."*

| press Run on | covers | passes |
|---|---|---|
| `02_electronics.py` | wiring + motors, boards + sensors | 2 |
| `03_tractionmotors.py` | four routes x four magnet grades | 16 |
| `04_batteries.py` | the pack, S1 / S2 / S3 | 3 |

Each runs 01, 02 and 03 and stops at the first failure. What a study covers is
`STUDIES` in `src/params_schema.py` -- case folders, scenario, and the
resources its figures draw -- written once. `current()` reads the
`RECOVERY_STUDY` variable the wrapper sets; the stages import `current` BY NAME,
so patching the module would not reach them and an environment variable does.
`src/study.py` runs the stages as subprocesses, the way `99_check_all.py`
already does, so what runs is the stage itself and not an in-process imitation.

DECISIONS 28, and it does not reopen 23: a switch that exists only on a command
line is invisible, a file in the project root is not.

One thing the traction study fixes on the way past: `magnet` is now in its
figure resources, so 03 draws its Sankey from the draws. Left out, 03 skipped it
and 02's deterministic one stayed on disk looking current.

### ⚠️ A correction to the entry above

**The stages ignore arguments.** `02_run_model.main` says so and means it. So
`02_run_model.py data/tractionmotor_mixed` did NOT run that case -- it
ran the four in `run.data_folder`, which is why it printed
`tractionmotor_split`. The claim earlier today that 01 had validated
`tractionmotor_mixed` was wrong for the same reason: it validated the four
configured cases.

**Checked properly afterwards, and it does pass**: 99 TC rows, 45 processes,
structure OK, nothing stranded, every resource totalling 1, exit 0. Four
sum-to-1 groups sit 0.82 sd from 1 -- the shredder chain's four magnet fates,
imported unchanged -- which the checker itself reports as not an error.

`tractionmotor_mixed` is deliberately NOT in `STUDIES['tractionmotors']` yet.
Adding it is one name in that list, once the disassembly share is a number
somebody chose rather than the placeholder in
`tools/build_tractionmotor_mixed_case.py`.

---

## 2026-09-28 (evening) — READ THE FIRST SECTION BEFORE TOUCHING THE FLEET CASE

### ~~⚠️ 1. `tractionmotor_fleet` DOUBLE-COUNTS MOTOR REMOVAL~~ — **FIXED 2026-09-29**

> **Resolved.** The fork is now the review's step 2, in
> `tools/build_tractionmotor_case.py` — which is the ONLY traction builder
> left, and writes `data/tractionmotor`. There is no
> `DISASSEMBLY_SHARE` and no `tractionmotor_fleet` any more; the case that
> is the answer carries the plain name. `check_ratios.py` was wrong in the
> same way and now expects `disassembly + (1 - step 2) x shredder`.
> The account below is kept because it is the record of how it happened —
> see `documentation/FAILURES.md`.


The case is built and runs. Its numbers are wrong and I found it minutes before
stopping, by reading the user's own extracted study table.

**The study already contains the split.** `documentation/recycling_coefficients.csv`,
extracted from `RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx` on 09-25:

    2030  disassembly  step 1  EoL vehicle collection      0.70 | 0.80 | 0.90
    2030  disassembly  step 2  Motor removal from vehicle  0.85 | 0.93 | 0.98

**Step 2 IS the disassembly share.** It is in the review, with a range, per
horizon. I invented a coefficient `DISASSEMBLY_SHARE` and put it ABOVE a chain
that already applies capture x removal:

    disassembly road  =   d    x (0.80 capture x 0.93 removal)   <- removal twice
    shredder road     = (1-d)  x (0.80 capture x 0.98 feed)

**The correct structure adds nothing and uses the review's numbers:**

    F_collected --0.80 capture--> --0.93 removal--> removed   -> recovery chain
                                   \-0.07---------> not removed -> shredder chain

That is also DECISIONS 10 word for word: *nothing is lost by not being
disassembled, it simply travels the other road*. In the pure disassembly case
the 7% not removed goes to `F_loss_upstream` and is written off; in a fleet
case it must go to the shredder.

**THE FIX:** delete `DISASSEMBLY_SHARE` from
`tools/build_tractionmotor_fleet_case.py` and branch at step 2 instead. It
needs the two builders to expose their step-2 value rather than folding it into
`up = prod(['capture','removal'])`.

⚠️ **`figures/tractionmotor_fleet/` and its workbook are from the wrong
structure.** So is `agreement_with_the_review.png`: it compared the case
against `d x dis + (1-d) x shr` using the SAME invented `d`, so it agreed with
itself. Its worst gap of 1.9 pp means nothing until the structure is right.

Two values of `d` were used today, both wrong for the same reason: 0.20, my
placeholder, and then 0.95|0.98|1.00, the BATTERY case's own dismantling rate,
after *"why are only so few traction motors taken out. It will be the same as
for batteries."* The reasoning there is sound -- a hulk opened for the pack is
one the motor can come out of -- but the review's own step 2 is the number to
use, and it says 0.93.

### ⚠️ 2. THE STUDY DOCUMENTS ARE NOT IN THIS PROJECT, AND THE ORIGINALS ARE GONE

Asked for explicitly on 2026-09-28: the study belongs in a folder in the
project AND in `documentation/`. It was never done.

`~/Downloads/TractionMotor/` -- where the 09-24 entry says
`RAWCLIC_BEV_Motor_Recycling_Report_V1.md` and
`RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx` lived -- **no longer exists**. The
only survivor in this repository is the extraction:

    documentation/recycling_coefficients.csv    118 rows, 11 columns

Related but NOT the same documents, in a sibling repository:

    RAWCLICVehicleTractionMotor/documentation/TractionMotor/
        RAWCLIC_BEV_Motors_Comprehensive_Report_V1.md / .pdf
        RAWCLIC_BEV_Motors_Critical_Review_V1.md / .pdf
        RAWCLIC_BEV_Motors_Comprehensive_Data_V2.xlsx

**FIRST JOB NEXT SESSION:** find the two originals -- check the other Mini,
check the Trash -- and copy them into this project. Every traction coefficient
traces to them and right now nothing here holds them.

### 3. What was built today and is sound

- **Upstream `04_03` now exports `outflow`** (`traction_export.py`, composed
  from collected + export + unknown_whereabouts, which partition it). Re-run
  and verified: 108 arrays, 3 flows, 950 MB. Without it `account()` returned
  None and FOUR figures were silently never drawn.
- **`other_flow` can address a resource exported AS a component**
  (`__component____copper.npy`). Both were needed before copper could have an
  account at all. DEFECTS 3.23.
- **The same nesting double count, found in three places**: the Sankey
  (3.21), `account()` and every row selection in `plot_monte_carlo` that sums
  mass (3.24). `account` read copper's collected mass as 140.94 kt against
  70.47, and because `lost = collected - recovered` mixed a doubled quantity
  with an undoubled one, copper appeared to lose 91.7 kt of the 70.5 it had --
  closing to 0.00e+00 the whole time, because closure is by construction.
- **A road split now requires that some resource travel more than one road.**
  The shredder's first branch is four material streams, and reading them as
  roads drew `recovered, ndfeb stream` beside `recovered`, the same 0.3396 kt
  twice.
- **Three study files** -- `02_electronics.py`, `03_tractionmotors.py`,
  `04_batteries.py` -- and the stages moved to `stages/`. DECISIONS 28.
- **Figures**: six essential per case with the rest in `detail/`, one resource
  per figure for account/losses/fleet, `over_time` on a log axis, and titles
  and legends that state only what the figure can show. DECISIONS 30-35.
- **`tools/compare_routes.py`** gained `<resource>_recovered` and
  `<resource>_lost`, cumulative above and per year below, one line per route,
  no total.

### 4. What is uncommitted

`main` is at `47eb40a`, pushed. Not yet committed:

    M  src/figure_style.py            write() takes essential=
    M  src/params_schema.py           study points at tractionmotor_fleet
    M  tools/build_tractionmotor_case.py    write() guarded so it can be imported
    M  tools/compare_routes.py        the two new figures, wrapped subtitles
    D  tools/build_tractionmotor_mixed_case.py   replaced by the fleet builder
    D  data/tractionmotor_mixed/
    ?? data/tractionmotor_fleet/         ⚠️ wrong structure, see §1
    ?? tools/build_tractionmotor_fleet_case.py  ⚠️ wrong structure, see §1
    ?? tools/check_ratios.py                    ⚠️ checks against itself, see §1

Nothing here is lost; none of it is right yet.

### 5. Where to continue, in order

1. **Find the two study documents and put them in the project.** §2.
2. **Rebuild the fleet case from step 2 of the review.** §1. Then
   `check_ratios.py` becomes a real check rather than a mirror.
3. **The overview figure.** Asked for repeatedly and not delivered: it should
   carry the ratios READ FROM THE RUN, so they can be checked. It still
   hard-types `Nd 0.41 -> 0.65`, which is a chain of modes and not any
   percentile of the result.
4. DECISIONS.md still has three weeks of decisions that live only in this log.

---

## 2026-09-29 (evening) — HANDOVER

**Tree is clean. `main` is pushed. Nothing is half-done.**

    origin/main   f82f4da   21 commits today

### If you read one thing

Everything below is figures, naming and one modelling rule. **No result from
any run you did today is wrong.** Every defect fixed after your runs was in the
drawing code, so `recovery_results.xlsx` and `monte_carlo_summary.csv` from
those runs stand as they are.

### THE ONE THING WAITING ON A DECISION YOU ALREADY MADE

You said: **put the shortfall on the loss flow.** It is NOT implemented — you
asked for the handover a minute later and I stopped rather than leave it half
written.

What it is. `improvement_after_end = continue` extrapolates past 2060.
Measured with the model's own checker:

    bev_electronics_wiring   OK
    tractionmotor            OK        <- the only case set to it
    battery                  3 groups sum to 0.9900 at 2070
    bev_electronics_boards   3 rows, 4 groups, 0.9900 to 0.9933

The cause, exactly. In `F_cells cathodeActiveMaterial -> Ni` the review caps
recovery at 0.99 and the mode reaches it by 2060. One step further the mode
would be 0.9967, above its own maximum, so it is held at 0.99 — and the loss
row that should have taken the remainder was clipped to 0 in the same step. So
0.67% to 1% of the mass exists in 2065 and not in 2070, and stage 01 refuses
it.

The fix you chose: give the group's LOSS flow the shortfall, since it is the
only member not sitting at a bound. `src/rest.flow_roles(case)` says which
flow in a group is the loss. It goes in `_hold_at_the_bounds`
(`src/case_tables.py`), after the mode is held and before the group is set
back to 1 — and `ramp()` does not currently know the case, so it needs the
roles passed down from `coefficients()`.

Until then, battery and boards stay on `hold`, which is their default and is
defensible: those coefficients are genuinely finished by 2060.

### WHAT CHANGED TODAY

**The case is `data/tractionmotor`.** One case, one builder
(`tools/build_tractionmotor_case.py`), forking at the review's own step 2 —
motor removal, 0.85 | 0.93 | 0.98, ref 6,7,8,9. The invented
`DISASSEMBLY_SHARE` is gone, and so are the three other builders and
`compare_routes.py`. No `mix` folder: the case declares `scenario_alias =
*=mix`, so it has no scenario dimension and writes to the top of its folders.

**`data_folder` is now `data`.** 154 path references across 34 files. The
setting is still called `run.data_folder`.

**Extrapolation past 2060.** `improvement_after_end` in a case's source table,
`hold` (default) or `continue`. Traction is `continue`. A simple linear
extrapolation; a value that would pass 0 or 1 is set to it, a mode that would
pass its own min or max is set to that, and a group that then sums above 1 is
set back to 1. Nothing is scaled up to reach 1 — which is why the shortfall
above has nowhere to go yet.

**05 adds the traction case.** Four cases now, and the rare earths joined
`combine.resources`. It runs its own 200,000-draw Monte Carlo and does not read
03's output — percentiles cannot be added, so it re-solves and adds per draw.

**Figures.** Too many to list; see `documentation/FAILURES.md` entries 19–26,
which is the honest version. The ones that changed numbers on a picture:
the fleet stock was summed as if 5-yearly samples were annual and was ~5× low;
05 was silently dropping the traction motor's copper, 60 kt, about 9% of the
combined total.

### ⚠️ A BUG THAT NEVER REACHED A RESULT, BUT NEARLY DID

`case_tables.GROUP` was three columns where the model's sum-to-1 key
(`mass_balance.RESOURCE`) is five. Two groups differing only by their input key
read as one: the wiring case's `F_disassembled -> copper` totalled **2.0000**
and the battery's `F_cells -> rest` totalled **7.0000**, and the set-to-1 rule
would have divided them by two and by seven. It never fired because traction is
the only case on `continue` and its groups happen to be identified by three
columns. Fixed, and asserted equal to `RESOURCE` so the copy cannot drift.

### WHAT TO RE-RUN

Nothing is required. If you want the figures to match the code:

    02_electronics.py   03_tractionmotors.py   04_batteries.py   05_combine_cases.py

02/03/04 for the axis labels, the fleet stock, the structure and coefficients
pages; 05 for its four figures moving out of `detail/` and the `copper` stream
being renamed `tractionmotor`.

**There is still no way to redraw figures without re-solving.** Every one-word
axis fix today cost a full Monte Carlo re-run. Worth building: the run writes
what the figures need, a redraw reads it back.

### STILL OPEN, OLDER

- No source documents for electronics (20/24 and 47/52 `PLACEHOLDER`) or
  `carcomposition_mockup` (556 `MADE UP`).
- `DECISIONS.md` is missing three weeks of decisions that live only here.
- The schema's lower-left is empty — cosmetic, inherent to the layered layout.
- The other Mini: `git fetch origin && git reset --hard origin/main`.

---

## 2026-10-07 (evening) — HANDOVER

**Tree clean, both repos pushed. Continuing tomorrow on the other Mac.**

### ⚠️ FIRST, ON THE OTHER MAC

    git fetch origin && git reset --hard origin/main      # in BOTH repos

`RAWCLICStockAndFlow` especially: its git was **broken** — `.git` pointed at a
`~/gitdirs/` directory that did not exist, and `.git 2` was an empty iCloud
conflict copy. It had been unversioned since 22 September, so
`src/traction_export.py` had **never been committed**. Restored by cloning the
remote bare into the gitdir and pointing `core.worktree` back at the tree.
Check the other Mac has the same wiring before working there.

### WHAT IS WAITING TO BE RUN

Nothing is broken; these are out of date.

    02_electronics.py      03_tractionmotors.py      04_batteries.py
    05_combine_cases.py

`04_03_tractionmotors.py` upstream HAS been re-run (07-10, 08:55) and its
export is verified — the vehicle count is sampled now.

### WHERE THE DAY WENT

**1. The traction export did not sample the vehicle count.** Mass is
count x composition, and a product of two uncertain quantities cannot be more
certain than either; the count alone has a CV of 7–21% by year against the
composition's 2.5–3.3%. Every traction interval was 2.9x to 6.6x too narrow.

Fixed in `RAWCLICStockAndFlow` `8e4b4e3`, per segment, which is the resolution
`bev_draws` exists at. Verified against that project's own 22-September proof:
copper `inflow` 2060 band **9.7% -> 45.1%** (proof said 44.5%).

⚠️ **The medians moved too, and should**: `inflow` −0.5%, `collected` −6.9% at
2040. The tracker is one deterministic run at the point lifetime, so Jensen
makes its `collected` biased high by 2–6%. A first version held the means
fixed, preserving that bias — `FAILURES.md` 29.

⚠️ **It was all already proved on 22 September** in
`RAWCLICStockAndFlow/code/proof_0403_vehicle_draws.py` and that project's
HANDOVER, under a heading reading "THE BLOCKER IS RESOLVED". A day went into
rediscovering it. **Read the upstream handover before investigating upstream.**

**2. Extrapolation past 2060.** `improvement_after_end` = `hold` (default) or
`continue`; all four cases are `continue` now. Linear; a value passing 0 or 1
is set to it; a group summing above 1 is set back to 1; a shortfall goes to the
group's loss flow.

⚠️ The one that cost three failed runs: past the window a rising coefficient
reaches its own ceiling and the mode meets the max — the battery's cathode
nickel at `0.97 / 0.99 / 0.99`. That row is then the widest in its group, so
the sampler forces it to take `1 - the others`, which is 0.990001 to 0.999181,
all above its maximum: every draw weighs zero and the run stops. Rule: past
2060, where the mode has met the max and sits above 0.5, **keep the min and set
mode = max = 1**.

**3. Figures.** Shared units per figure type; crossing dots interpolated onto
the drawn line; the stock integrated over the year gaps (it had summed
5-yearly samples as annual, ~5x low); axes that use the panel; `structure.png`
and `structure_coefficients.png` as two top-level pages; `routes.png` removed;
the fleet share no longer capped at 100%.

### ⚠️ WHERE WORK STOPPED — THE BATTERY STUDY

Two new documents arrived today in `documentation/BatteryStudy/`:

    1-s2.0-S0956053X2600543X-main.pdf    Maisel et al., 15 pages
    1-s2.0-S0956053X2600543X-mmc1.xlsx   supplementary data, 25 sheets

Read and written up in **`documentation/BATTERY_COEFFICIENTS.md`**, extracted
by `tools/extract_battery_tcs.py` (reads and never writes the study):

- **Three process families** — mechanical 1,216 coefficients, hydro 630,
  thermal 496, plus preparation for reuse 404.
- **A family is not a route.** The five routes are chains of families.
  Mechanical is Route 3 *and* the pre-treatment inside 1, 2 and 4. **Direct
  recycling is Route 5 alone, LFP only** — it keeps the cathode compound rather
  than dissolving it. That was the question asked, and answered.
- Per-element min/median/max with data quality (1 best, 4 worst) and reference
  counts for Ni, Co, Li, Mn, Cu, Al, Fe, P, graphite, C.
- The mixture moves hard: Route 3 `0.799 -> 0.286`, Route 2 `0.100 -> 0.696`.
  Direct recycling stays near zero at **TRL 4**.

⚠️ **THE OPEN QUESTION, AND IT IS A MODELLING DECISION.** The wanted split is
**NMC low / middle / high, LFP, LMFP and two sodium**. The coefficients are
**chemistry-blind**: `NMC`, `LFP` and `LMFP` appear ZERO times in all 2,746
rows, and the paper states that as a limitation in its own words. Sodium IS
there (`SIB` 99 times, `battNaRechargeable` 200 rows).

So chemistry cannot come from these coefficients. It has to enter through
COMPOSITION — the same family coefficients applied to different element mixes —
with Route 5 the one exception defined per chemistry. **That decision has not
been taken.** It is the first thing to settle.

Still unread: the paper's Fig. 5, and the ten `LIB_Route* BAU/REC` sheets,
which hold route-level recovery with uncertainty per element.

### SMALLER THINGS

- `pypdf` was installed into this repo's `.venv` to read the paper. The venv's
  `pip` shebang still points at the old pre-iCloud path — use
  `./.venv/bin/python -m pip`.
- `documentation/DIALOG.md` holds the whole conversation, both sessions, 1,707
  turns, 2026-08-17 to 09-30. `FAILURES.md` is the register drawn from it:
  29 entries, eight patterns.

## 2026-10-08 (evening) — HANDOVER

**Both repositories pushed, git aligned on this Mac, tree clean. 04_04 has been run and its export checked.
The next step is his: press Run on `04_batteries.py`.**

### ⚠️ FIRST, ON THE OTHER MAC

    git fetch origin && git reset --hard origin/main      # in BOTH repos

Safe, because the working folder is the shared iCloud tree and everything in it is on GitHub now: after
the fetch, `git diff origin/main --stat` must print nothing. If it prints something, stop -- that is work
that was not pushed. (This Mac needed more than the one command; see "Git" in the entry above. If `git
fetch` fails there with "bad object", look for a stray ref in `refs/` whose name has a space and ` 2`.)

### WHAT IS WAITING TO BE RUN

    04_batteries.py       twelve passes, 200,000 draws, `run.variants` = own + mechanical
    02_electronics.py     03_tractionmotors.py     05_combine_cases.py     as out of date as before

I have not timed `04_batteries.py` at full width. At 300 draws, stage 03 of one case took 45 s, most of
it figures. Then change `run.variants` to `tc_set=BAU` and `tc_set=REC` (and, for sodium,
`sodium_route=mechanical_direct`) and press Run again; every choice has its own folder, after the
scenario, under `figures/<case>/` and `data/<case>/output_data/`.

### WHERE THE DAY WENT

**1. The battery is five cases.** LFP, LMFP, NMC_high, sodium, solid-state; each with its own roads, three
sets of coefficients, one setting. Everything about it is in `BATTERY_ROUTES.md`; the decisions are
DECISIONS 42–52, and 21 now says large runs are his.

**2. He ran 04_04, and the export is right.** The first of the three flows was exported at 14:11, the second
at 17:00, the third at 19:38, the summary files and figures by 19:41: **about six hours**, not the "an hour
or more" in the older notes. Checked, read-only:

- 14 chemistry × scenario folders, 9.4 GB: LFP, LMFP and NMC_high in S1–S3, the two sodium cells in S2–S3,
  solid-state in S3, each with `inflow`, `outflow` and `collected`. Every array is (200000, 11), float32,
  finite, none negative; no N or F; `batteryCellUnitemised` only in the sodium cells.
- **Against `battery_draws/` of the same run, draw by draw: 3.4e-7**, the worst relative difference,
  components and elements, in 21 of the 42 folder-flow pairs (all 14 `collected`, and seven of `inflow` and
  `outflow`); nothing missing, nothing extra. That is the check that counts: both were written by one run
  from the same arrays.
- Against the old summed export of 10-07 the means agree to four decimals (new/old = 1.0000) and the draws
  do not. That is not the export; it is point 4.

Collected mass in 2050, kt (the sum of the component totals):

| | LFP | LMFP | NMC_high | Na layered | Na Prussian white | solid-state |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 2,130 | 1,274 | 878 | | | |
| S2 | 2,034 | 1,266 | 419 | 335 | 719 | |
| S3 | 1,946 | 1,197 | 400 | 309 | 684 | 62 |

**3. Each case was run on the real export** before he pressed Run, one at a time at 300 draws: the input
check, the check of every version, and a Monte Carlo of every version in every scenario the case has.
Everything passed; the numbers are a check, not a result.

| case | scenarios | versions | all terminal flows / collected | |
|---|---|---|---:|---|
| `battery_lfp` | S1–S3 | own, BAU, REC | 100.01–100.03 % | |
| `battery_lmfp` | S1–S3 | own, BAU, REC | 100.24–100.25 % | 100.11–100.12 % at 5,000 draws |
| `battery_nmc_high` | S1–S3 | own, BAU, REC | 100.48–100.57 % | |
| `battery_sodium` | S2, S3 | 3 sets × 2 routes | 99.99 % | handed on 27–28 % (mechanical), 14 % (mechanical_direct) |
| `battery_solid_state` | S3 | — | 100.23 % | handed on 8.9 %; stages 02 and 03 ran in a sandbox |

The excess over 100 % is the composition files' own noise, not mass made by the model: at the full 200,000
draws the elements of a component add up to at most 0.03 % above the component (the enclosures, where iron
and aluminium are nearly all of it), and at a few hundred draws the noise is larger. It shrinks with the
draws. The stand-in export I had used before had that noise clipped out.

**⚠️ The real export found a crash the stand-in could not.** The solid-state pass stopped with
`'NoneType' object has no attribute 'mean'`: solid-state has nothing in S3 before 2040, so in those years
the composition has no row for it and nothing was kept to add up. Any case with a leading run of empty
years would have done the same, and it would have stopped his twelve passes at the last. **Fixed** in
`Draws.inflow` (a year with no mass is zero; components named that the export lacks is an error that says
so), with two tests, the first of which reproduced the real traceback. DEFECTS 3.26, FAILURES 30. Stages
02 and 03 then ran on solid-state in a sandbox, figures and workbook included; the zero years draw as
zero.

**4. Found upstream, not fixed: 04_04 draws a different pack-size world on every run.**
`RAWCLICStockAndFlow/src/battery_capacity.py:81` and `src/battery_voltage.py:107` seed each segment with
`abs(hash(segment))`, and Python salts the hash of a string per process. Shown directly: the same call with
the same seed gives `[33.7, 35.8, 34.1, ...]` kWh in one process and `[33.7, 29.9, 34.1, ...]` in the next,
and the same numbers in both with `PYTHONHASHSEED=0`. Within a run nothing is wrong -- one draw is one world
in everything the run wrote -- but two runs of 04_04 differ, so an export cannot be reproduced. The fix is
`zlib.crc32(segment.encode())` in both places, as `battery_chemistry.py` already does; it changes the
draws once and takes effect with the next run of 04_04, six hours. **Not made: it is his decision.**
DEFECTS 3.27.

**5. Git on this Mac was fixed**, on his word (the entry above has the details): two stray refs moved, not
deleted; 204 commits of old local history kept on `local-history-2026-09-25` and `local-history-2026-09-24`;
`main` equals `origin/main` in both repositories.

**6. The numbers in the documents were read back against the data** before anything was pushed. Eleven
statements in the first draft of `BATTERY_ROUTES.md` were wrong, and three wrong statements had already gone
to him in chat (FAILURES 31). The pushed document has none of them.

### OPEN — HIS

- **The `hash(segment)` fix** (point 4), and whether to re-run 04_04 after it.
- Put the five cases into `combine.cases` in place of `data/battery`? A case without the scenario stops 05:
  S1 has three of them, S2 four, S3 five (`BATTERY_ROUTES.md` §13).
- Add Fe, P, Mn, Na, C and Al to `figures.resources` of the batteries study; it draws Cu, Ni, Co and Li.
- Retire `data/battery`? It still runs, from the old summed export (`battery_recovery_draws/`, 2.8 GB), which
  nothing writes any more.
- The chemistry cases draw the same random numbers where a coefficient has the same name (correlation 1.000),
  so their sum in 05 is wider than independent cases would give. A `stream` key per case would fix it; it was
  left out as complicated.
- The 90 PLACEHOLDER rows (20, 22, 20 and 28; `BATTERY_ROUTES.md` §4), `own` borrowing the paper's REC where he
  has no numbers, and the dismantling of `batteryCellUnitemised`, which is an assumption.
- Two things on disk that are his to delete, and I have not: the old single-sodium `Na_ion*` files in
  `battery_draws/` (8.2 GB, not read any more), and the old summed export above once `data/battery` is gone.

### SMALLER THINGS

- Registers: DEFECTS 3.26 and 3.27, FAILURES 30 and 31, DECISIONS 42–52.
- The index of `documentation/README.md` lists `BATTERY_ROUTES.md`.
- Scratch from today is outside the repositories: about 100 MB of stand-in data in the system temp folder,
  and the check scripts in the session's scratchpad. None of it is needed.
