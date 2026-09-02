# Handover

Current as of **2026-09-01**, commit `76ac8e3`. Rewritten from the ground up on
2026-08-21 and updated since; git has the older text.

**Read this first: what happened on 2026-09-01.** The upstream draw folder had
been rewritten on 08-31 and held **four runs at once**, because upstream writes
it file by file and never clears it — Motors' elements came to 1.81 of Motors.
`src/upstream.py` read the union of them without a word; it now refuses, naming
the widths (DEFECTS.md §3.10). The user emptied the folder and re-ran 04_02 the
same day, and it came back clean: one run, one draw count, no `_ppm` files.

Three things followed from that day, all built and all tested:

1. **Layer 3 is real.** `<element>__<material>__<group>` is read, so `esteel`
   and `magnet` sit at Layer 3 where a placeholder stood. The placeholder stays
   for what is not resolved, so an export without those files gives exactly the
   rows it always did. CASES.md has the three rules.
2. **A resource that cannot leave a flow is refused.** It used to lose its mass
   in silence — 5.9% of the electronics case, found by hand. DEFECTS.md §3.11.
3. **`make_skeleton` no longer deletes.** It dropped filled rows whose resource
   had left the composition while being documented as merging, and took 32 of
   them, every rare earth included. DEFECTS.md §3.12.

**The electronics case is `bev_electronics_wiring`, and it is the only one.**
Rebuilt from scratch on 2026-09-02 to the user's specification, after two
earlier attempts they had not agreed to. `bev_electronics` and
`bev_electronics_boards` were deleted the same day at their instruction; git has
both (`e8c2373`, `0e965f0`).

**Materials only. No element layer anywhere** -- zero Layer 4 rows in the
solution. Layer 3 is what a scrapyard sells:

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

**Both pipelines run end to end on real upstream data. All 117 checks pass.**

| | 04_02 electronics | 04_01 car composition |
|---|---|---|
| case folder | `data_folder/bev_electronics_wiring` | `data_folder/carcomposition_mockup` |
| covers | wiring and motors in BEVs | whole cars, five drivetrains |
| finest resolution | **material** — copper, alalloy, fealloy | **material** — calAHSS, battery |
| element layer | **none at all** | none |
| years | 2030–2050 | 2040 |
| draws | 200,000 | 50,000 |
| mass in | 640.8 kt (2050) | 13,863 kt (2040) |
| mass balance | 1.9e-16 | 4.7e-11 |
| recovered | 76.2% of collected (2050) | 82.8% of collected (2040) |
| coefficient rows | 24, of which 10 are chosen | 632 |

PCB and Sensors are exported by 04_02 and read by nothing. They are not in this
case's `groups`, and the case that covered them was deleted on 2026-09-02.

To verify, set `run.data_folder` and press Run on `99_check_all.py`: six test
suites on fixed fixtures (117 checks), then the pipeline and a mass balance.

**`run.data_folder` points at `bev_electronics_wiring`.** Its loss rows ARE
residual -- computed as `1 - what reached a pile` -- at the user's instruction on
2026-09-02, so that a person types a yield and nothing else. That reverses the
2026-08-28 decision below; simplicity won over having a measured range on both
sides of every pair.

Both case tables are **structurally finished**. `tools/tc_worklist.py` reports
all 26 groups in the electronics case as *measured on every row*, and 278 of 278
in the car composition one as correct as they stand, with no warnings on either.
Nothing in the tables needs converting, rearranging or repairing. What they need
is numbers — see §4.

### The one thing that matters most

**Every transfer coefficient in this project is a placeholder I invented.**
Not one is measured.

| case | rows | invented outright | derived or definitional |
|---|---|---|---|
| `bev_electronics` | 68 | 60 `PLACEHOLDER (Claude, not data)` | 8 routing decisions and the hulk transfer |
| `carcomposition_mockup` | 632 | 532 `MADE UP (Claude)` | 100 definitional hulk transfers |

**Neither table has a residual row left.** What remains beside the placeholders
states a definition (a hulk that was not dismantled goes to the shredder, at 1)
or a routing decision (a flow that does not apply here, at 0). A residual is
`parent − Σ known children`, so it is arithmetic on the invented numbers beside
it — which is why the headline above says every coefficient and means it. The
split is worth stating only because the `source` column distinguishes them, and
a reader comparing this table against the file should find them agreeing.

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

- **`child_layer`** — `element` (04_02: the child is Cu within Wiring, with a
  placeholder material between) or `material` (04_01: the child is calAHSS
  within elvBIW, at Layer 3, no Layer 4). Getting this wrong **does not fail**:
  it files materials where elements belong, every element-keyed coefficient
  matches nothing, and the run still balances while being wrong.
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

### What 04_02 has to change for the metals case

**It must write the material's own mass, and not go down to the elements** for
the metal domains. 04_01 already exports exactly this shape --
`calAHSS__elvBIW.npy` -- and this model reads it with `child_layer = material`
and no element layer at all. 04_02 writes elements instead, which is why Layer 3
here can only ever be a by-product of element names.

Four files, and they are the whole ask:

    copper__Wiring.npy      the harness
    copper__Motors.npy      the windings -- the motor copper IS wiring
    alalloy__Motors.npy
    fealloy__Motors.npy     steel + cast iron + the ferrite magnets, one stream

**The numbers are already there, and no approximation is involved.**
`RAWCLICVehicleElectronics/Composition/element_draws/motors_<segment>_elements.txt`
names every column of the fractions array, and each is either a bare element or
`<element>__<material>`:

    Cu  O__copper Ag__copper Pb__copper ... Mn__copper
    Fe__esteel Si__esteel C__esteel Mn__esteel Al__esteel P__esteel S__esteel
    Sr__magnet Fe__magnet O__magnet
    Fe__cfsteel C__cfsteel Mn__cfsteel P__cfsteel S__cfsteel
    Al__bulk  Plastic  Unspecified

and `motors_<segment>_esteel_elements.txt` names `Fe Si C Mn Al P S` -- the same
seven. So **every element of every alloy is in the main list**, and an alloy's
mass is the exact sum of its `__<material>` columns. Nothing is missing and
nothing has to be invented:

    copper   = Cu + every X__copper        (the bare `Cu` IS the copper metal,
                                            which is why no Cu__copper exists)
    alalloy  = every X__bulk
    fealloy  = every X__esteel + X__cfsteel + X__magnet

The change is in `code/04_02_BEVelectronics.py`, in the export block that calls
`_write_element_draws` -- 04_02's own figures and tables do not move.

**This will not work off the current export.** The 09-01 re-run resolved 24
elements and dropped `Fe` entirely, so summing today gives 0.06% of Motors
rather than the steel. `bev_electronics_elements` has to be empty (= all) when
it runs.

### Why the metals case is not built yet

Two attempts were made on 2026-09-01 and both were wrong, in the same way:
keying the recovery at the material layer while `child_layer` stayed `element`
leaves `Al`, `Mn` and `Sr` sitting underneath `bulk`, `cfsteel` and `magnet`.
The user's instruction is that there is no element layer there at all. There is
no way to that shape from an elemental export, so the case waits for the four
files. Nothing half-built was left behind -- `case.xlsx` was reverted.

The branch itself is **20 commits ahead of `main`** — the other 17 are earlier
work that had not been merged. Merging it brings all twenty, not three.

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

0. **The four new materials are filled in, and three of them do not matter.**
   `bulk/Al`, `cfsteel/Mn`, `esteel/Mn` and `magnet/Sr`, across refining and
   shredding, recovered and lost — placeholders written on 2026-09-01, each
   saying so in `source`. `filling_sheet.py` ranks `bulk/Al` **7th of 60** at
   0.74% of the spread and the other three at **0.00%**, because cfsteel is
   0.09% of Motors, esteel 0.05% and magnet 1.6%. So look up `bulk/Al` when
   convenient and leave the rest; measuring them would buy nothing.

   Two of the eight carry a judgement worth revisiting rather than a number
   worth measuring. `bulk/Al` at shredding was carried over unchanged from the
   `Motors_mixed/Al` row it replaces, so moving to a real material key changed
   no value — but a bulk aluminium part should separate better than aluminium
   dispersed through a motor. And `esteel/Mn` was given the same number as
   `cfsteel/Mn` deliberately: nothing points to a difference, so inventing one
   would be worse, yet laminated stator steel inside a copper winding plausibly
   does worse than a pressed housing.

1. **Replace the coefficients. This is the whole of what is left.** The user
   asked on 2026-08-26 to have the case ready for real use; the model side is
   finished and nothing else is in the way. For electronics,
   `tools/make_skeleton.py` writes the rows and **merges, deleting nothing**,
   so you can do it a domain at a time without losing what you filled in — a
   row whose resource has left the composition is kept as inert rather than
   dropped, which it was not until 2026-09-01 (DEFECTS.md §3.12). For car
   composition,
   `tools/make_carcomposition_tcs.py` generated the current invented table and
   **overwrites** — but it now refuses to, once any row's `source` says
   something it did not write. `--overwrite` forces a deliberate rebuild.

   **Start with [FILLING_IN.md](FILLING_IN.md)** — five steps, written for
   doing rather than studying — and with `tools/filling_sheet.py`, which ranks
   the rows still waiting for a number by **`spread_share`**: the fraction of
   the answer's variance each one accounts for, and so the fraction that
   disappears if it is measured exactly. That is what a measurement buys, and
   it is not the same as how closely a coefficient tracks the answer, which is
   reported beside it as `influence`.

   The difference decides what to do first. On the electronics case **3 rows of
   60** carry 80% of the spread (remeasured 2026-09-01), and two of those three
   are the same measurement — copper out of the shredder, seen from the
   recovered side and the loss side. The third is the fraction of wiring that
   is not dismantled. On car composition, **12 of 354** rather than the 88 the
   influence ranking suggested.

   Fill in `value`, `value_min` and `value_max`.

   **A caution that follows from having no residual rows.** 22 of the 26
   electronics groups have exactly two members, and with no residual the
   constraint leaves such a group ONE degree of freedom: both rows carry the
   same information. Two consequences, one harmless and one not.

   - Harmless: `filling_sheet.py` reports shares that sum past 100% — "measuring
     all 44 would remove 200% of the spread" — because each row is credited with
     the same variance. Read the ranking as an ordering, not as an accounting.
   - Not harmless: **the second range in each of those pairs is not a
     measurement.** It was written on 2026-08-28 by widening around the derived
     value when the residual rows were converted, and it says so in `source`.
     Until a real, independently measured range replaces it, the pair's width is
     something nobody measured. §5 has why arithmetic cannot detect this and
     only the `source` column can.

   So: when you measure one side of a pair, measure the other side
   independently or say plainly that you did not. `tools/tc_worklist.py` has
   blank columns for an independent number and its source.
2. **More years for 04_01**, if wanted — but check the memory arithmetic first:
   five drivetrains over five years is roughly 20,000 result rows, which at
   200,000 draws exceeds the 4 GB budget and would be refused.

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

**`F_separated_electronics` stays**, at the user's decision on 2026-08-28: it is
a real handoff to a separate recovery stream with its own coefficients, and it
carries 0 here only because nobody has measured it yet. It is not a candidate
for removal.

### Not in this repository

The upstream project was parked on 2026-08-26 — the user's words: stock and
flow is done for the moment — but **five commits landed there on 2026-08-31**
(§3), so it is being worked on again. These still need it and should not be
started without saying so first.

- **Empty `element_draws/<scenario>/` and re-run 04_02 once.** This is what
  unblocks the electronics case here, and it is the only thing that does. The
  folder is written file by file and never cleared, so it now holds four runs;
  emptying it first is what makes one run's export stand alone. Two things to
  settle while doing it:
  - The plain Motors elements sum to **3.7% more than the Motors domain mass**
    within their own run. That is a fact about the export, not about the mix,
    and nothing here can compute a share around it.
  - `Fe_ppm` restates `Fe` under a name whose level is invisible. `Fe__esteel`
    is read correctly now, because `__` says how deep the name goes; a single
    underscore says nothing, so `Fe_ppm` reads as an element and double-counts.
    Either stop exporting them or give them a `__` level.

  After the re-run, press Run on `tools/make_skeleton.py` for the electronics
  case. Layer 3 will hold real materials, so the TC table needs rows for them —
  it **merges**, so nothing already filled in is lost.
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
