# FAILURES

**What Claude got wrong on this project, when, how it was caught, and what now
stops it recurring.**

Asked for by Matthias on 2026-09-29: *"I also want a history of all your
failures."*

This is not `DEFECTS.md`. That file is the model's defect register — some of
its entries are inherited, some are ordinary bugs found by tests working as
intended. **This file is only the failures that were mine**, including the ones
that cost days, and especially the ones a human had to find because no check I
wrote would ever have found them.

Read the **Patterns** section at the end first. The individual failures are
instances of seven recurring shapes, and the shapes are more useful than the
list.

---

## The register

| # | Date | Failure | Found by | Cost |
|---|------|---------|----------|------|
| 1 | 09-02 | `mode_vs_mean` summed the year axis | Matthias | a figure that compared two masses no year has |
| 2 | 09-02 | Every figure built before any was written | me | matplotlib warnings; 27 figures open at once |
| 3 | 09-02 | Sankey subtitle claimed a depth it did not have | me | a material case labelled "element-depth rows only" |
| 4 | 09-07 | `describe()` took a name it had to map back to a class | Matthias | `00_parameters.py` died with `KeyError: 'combine'` |
| 5 | 09-28 | Upstream export had no `outflow` | Matthias | four figures silently not drawn, for weeks |
| 6 | 09-28 | `other_flow` could not address a component-level resource | Matthias | copper had no account figure |
| 7 | 09-28 | The nesting double count, in three places | Matthias | copper reported at 140.94 kt collected; truth 70.47 |
| 8 | 09-28 | False roads — and my first fix still passed | me, late | four material streams read as four competing roads |
| 9 | 09-28 | Claims on figures that the figure cannot support | Matthias | "many of the statements are absolutely wrong" |
| 10 | 09-28 | Made a branch, against a stated rule | Matthias | "you are again not following this rule" |
| 11 | 09-29 | Published a coefficient table I had not checked | Matthias | "126 coefficients" — 41 were headings, not coefficients |
| 12 | 09-29 | Named the wrong PDF as the battery study | Matthias | "This document is also not the one I provided. I am mad!!" |
| 13 | 09-29 | Invented `DISASSEMBLY_SHARE`; double-counted removal | me, hours late | the fleet case's numbers were wrong all day |
| 14 | 09-29 | Wrote a check that compared the case against itself | me | 1.9 pp "agreement" that meant nothing |
| 15 | 09-29 | **Never re-rendered the figures** | Matthias | days spent judging images up to three weeks old |
| 16 | 09-29 | Renamed figures without clearing the old ones | Matthias | `trapped.png` read as current 11 days after it died |
| 17 | 09-25→29 | Built four cases when one was wanted | Matthias | four of every figure; "I want one clear answer" |
| 18 | 09-29 | Started a 450-line refactor when a 4-line rename was needed | Matthias | "you are costing me so much time and money" |
| 19 | 09-29 | 05 silently dropped the traction motor's copper | me, by accident | 60 kt, ~9% of the combined total, reported as a skip |
| 20 | 09-29 | The fleet stock summed 5-yearly samples as annual | Matthias | every traction and battery stock ~5x too low |
| 21 | 09-29 | The shared unit judged unconverted numbers | Matthias | a 265 kt axis labelled kg, with `1e8` in the corner |
| 22 | 09-29 | Threshold dots drawn off the curve; peak label a sample late | Matthias | "points in green which do not align with the curve" |
| 23 | 09-29 | Five axes said a bare `mass (kt)` for per-year flows | Matthias | total or per year, unstated, differing by 50x |
| 24 | 09-29 | A cache inserted into the wrong function | Matthias's run | every 03 run crashed on `UnboundLocalError` |
| 25 | 09-29 | 05's own figures buried in `detail/`, one stream named `copper` | Matthias | "what is the copper, and why is it in the details folder" |
| 26 | 09-29 | Warned about a problem in 05 that did not exist | me | sent him into a run braced for an axis bug that was fixed in September |
| 27 | 09-30 | Defended a band as correct that was five times too narrow | Matthias | every traction interval overconfident, and I argued it was fine |
| 28 | 09-30 | Answered a question about spread by measuring means, then said stop | Matthias | would have halted the real fix and started a wrong investigation |
| 29 | 09-30 | Rediscovered a defect already proved, then preserved the bias it named | me / the record | a day spent re-deriving 22 September, and a first fix that kept a known 2-6% bias |

---

## 1. `mode_vs_mean` summed the year axis — 09-02

Compared a mode-run total against a mean-run total after summing over every
year, producing two masses that correspond to no year in the data. Fixed to be
per-year, with the measured drift stated in the subtitle.

The same figure's console line named the worst row `Wiring` — a component — on
a case whose resources live at Layer 3, by hard-coding `Layer 4 or Layer 2`. It
now names the deepest filled layer and the year, so the printed line and the
figure cannot disagree.

Register: `DEFECTS.md` 3.16.

## 2. Every figure built before any was written — 09-02

`draw_all` built the whole list eagerly, so all 27 of the boards case's figures
were open simultaneously, each holding a histogram of 200,000 draws.
Matplotlib warns at 20. Fixed with thunks: built one at a time, written, closed.

Register: `DEFECTS.md` 3.17.

## 3. The Sankey announced a depth it did not have — 09-02

Subtitle read "Element-depth rows only" on cases that resolve materials. It now
names the layer actually drawn.

Register: `DEFECTS.md` 3.18.

## 4. `describe()` took a name, not the section — 09-07

Adding a parameter section stopped `00_parameters.py` dead with
`KeyError: 'combine'`, because `describe()` mapped a string back to a class
through a dict that the new section was not in. It takes the section object
now, so a new section cannot be missing from anything.

Register: `DEFECTS.md` 3.20.

## 5. The upstream export had no `outflow` — 09-28

`src/traction_export.py` wrote `collected` and `inflow` and stopped. The
recovery model's `account()` needs `outflow` to compute the mass that left the
fleet and never reached a recycler. Without it `account()` returned `None` and
**four figures — account, losses, trapped, fate — were silently not drawn**.

Silently is the word that matters. Nothing failed. The stage printed success.
The figures were simply absent, and stayed absent for weeks, until Matthias
asked where copper's account was.

Fixed by composing `outflow` from the tracker's three destinations
(`collected`, `export`, `unknown_whereabouts`), with `_parts_of()` raising
rather than composing a partial sum — an outflow quietly too small means
"never collected" too small, which flatters collection without anything
failing.

Register: `DEFECTS.md` 3.23.

## 6. `other_flow` could not address a component-level resource — 09-28

The second half of the same missing figure. Fixed with a fallback to
`<group_marker>__<domain>.npy`.

Register: `DEFECTS.md` 3.23.

## 7. The nesting double count, in three places — 09-28

The layers are nested: an element row is part of its material row. A component
named after its own material — `copper` inside `copper` — answers the same
resource twice with the same mass. Summing both doubles it.

Measured, for copper in the wiring case:

| | reported | truth |
|---|---|---|
| collected | 140.94 kt | 70.47 kt |
| lost | 91.73 kt | 21.26 kt |

Three separate code paths had it: the Sankey (`mass()`, `draws_for()`), the
`account()` function, and twelve row selections in `plot_monte_carlo`. Fixed
with `shallowest_of()` and `own()` / `own_depth`.

**Why no check caught it:** the Sankey balanced against itself, and the account
closed by construction. Both were internally consistent and both were twice the
truth. Neither was ever put beside the `Recovered` sheet, which had been right
the whole time.

Register: `DEFECTS.md` 3.21, 3.24.

## 8. False roads, and a fix that still passed — 09-28

`routes()` read the shredder case's four material streams — copper, aluminium,
NdFeB, steel — as four competing roads. The account figure then drew
`recovered, ndfeb stream` for dysprosium at 0.3396 kt beside `recovered` at
0.3396 kt: one number, twice, under two names.

The first fix was worse than no fix. I tested whether the branches carried
overlapping resources — correct idea — but included `F_loss_upstream` in the
test. That flow carries **every** resource by construction, so it overlapped
with all of them and the four streams were read as roads again. The fix passed
and changed nothing.

Corrected to test only the branches that recovered material actually descends
from.

## 9. Claims on figures that the figure cannot support — 09-28

I wrote statements onto figures — about what a number meant, what it implied —
that a reader could not verify from anything drawn. On the Dy figure Matthias's
verdict was: *"Many of the statements in the figure are absolutely wrong!!! It
is very very very bad work"*, and then: *"what you write which can not be seen
in the figures as no place there. Move it to other figure once for all."*

Every unverifiable number and claim was stripped from titles and legends. A
figure now states only what is drawn on it.

This one is not a bug. It is a habit: writing the conclusion I believed instead
of the one the picture supports.

## 10. Made a branch, against a stated rule — 09-28

The rule had been given: commit to `main`, push, pull on the other Mac. I made
a branch anyway. *"Keep always in mind how github updated. This is a rule you
are again not following!"* Moved back to `main`.

## 11. Published a coefficient table I had not checked — 09-29

`tools/extract_traction_tcs.py` produced what I reported as "126 coefficients,
71 of them unreferenced". **41 of the 126 were chain-summary headings, not
coefficients.** The real figures are 85 steps, 31 of them unreferenced.

Matthias found it. His question was the right one: *"Why have you not told
me?"* The answer: because I pushed the table before checking it. Fixed by
splitting steps from chain totals into two files.

## 12. Named the wrong PDF as the battery study — 09-29

Labelled `1-s2.0-S0956053X2600543X-main.pdf` as the battery study in the
project documentation. It is a paper, not his study. *"This document is also
not the one I provided for the batteries. I am mad!!"* The real study was
copied in from `iCloud/Empa/RAWCLIC/` and the paper relabelled as what it is.

I asserted a document's identity without opening it to check.

## 13. `DISASSEMBLY_SHARE` — removal counted twice — 09-29

The fleet case needed a split between the disassembly road and the shredder
road. **The review already contained it**, as step 2, "Motor removal from
vehicle", 0.85 | 0.93 | 0.98, with references 6,7,8,9.

I invented a coefficient instead and put it above chains that already applied
`capture x removal`:

    disassembly road  =   d    x (0.80 capture x 0.93 removal)   <- removal twice
    shredder road     = (1-d)  x (0.80 capture x 0.98 feed)

Two values were tried — 0.20, then the battery case's 0.95|0.98|1.00 — and both
were a second copy of a step the source already gave. A whole day's traction
numbers were wrong.

The correct structure invents nothing:

    F_collected --step 1--> F_captured --step 2--------> F_removed   disassembly
                \                                  \
                 \-> F_uncollected                  \-(1-step 2)--> F_shredded

Fixed 09-29 in `tools/build_tractionmotor_case.py`.

**The failure underneath:** Matthias had said *"damn I told you to use my
numbers from the study!!"* and, earlier, *"You know what figures I have for
copper in electronics and also with batteries. So why do you need to ask, I
want the same."* The number existed, in a document in the project, and I made
one up.

## 14. A check that compared the case against itself — 09-29

`tools/check_ratios.py` was written to verify the fleet case against the
review's published end-to-end coefficients. It blended them as
`d x dis + (1-d) x shr` — **using the same invented `d` the case was built
from**. So it compared the case against a number derived from the case. It
reported agreement within 1.9 pp and would have reported agreement for any
value of `d`.

It was also wrong on the arithmetic. The review's disassembly coefficient
already contains step 2, so that road contributes the published number in full,
not a share of it; the shredder road is fed only by what step 2 leaves behind.
The expectation is `disassembly + (1 - step 2) x shredder` — which means **the
fleet recovers more than pure disassembly**, because pure disassembly writes
the unremoved 7% off while the fleet sends it to a shredder.

Both fixed 09-29.

## 15. Never re-rendered the figures — 09-29 *(the expensive one)*

For four days I fixed figures by editing code and reading what it would draw. I
never once looked at the images on disk beside it.

Matthias spent those days opening figures and finding every fault he had
already reported still there. *"I have looked at many of the figures. Most of
them have all the items which I criticised yesterday. I am so pissed."* Then:
*"We have to go through all of them. What a nightmare."*

They were all still there because **nothing had re-drawn them.**

| folder | newest figure |
|---|---|
| `figures/carcomposition_mockup/` | 2026-09-03 |
| `figures/bev_electronics_wiring/` | 2026-09-04 |
| `figures/bev_electronics_boards/` | 2026-09-17 |
| `figures/battery/S1–S3/` | 2026-09-18 |
| `figures/combined/S1–S3/` | 2026-09-25 |

Newest PNG anywhere: **2026-09-25 16:03.** Every figure fix from 09-26 to 09-29
had never been rendered once. He was judging work up to three weeks older than
the code, and I let him, because I was verifying in the source instead of in
the output.

**There is no code fix for this one.** The rule is: a figure change is not done
until the figure has been looked at.

## 16. A renamed figure does not disappear — it becomes a lie — 09-29

`trapped.png` was split into one file per resource, `fleet_<resource>.png`, and
the shaded band on it — *the gap: what the fleet absorbs* — was removed on
09-28 after *"only what is recycled can be used again. also the grey area is
shit."*

Nothing deleted the old file. Eleven days later `figures/battery/S1/trapped.png`
was still in the folder: a six-resource poster, the band still on it, dated like
everything around it, indistinguishable from current work. Matthias opened it
and read it as this model's answer. It was not — no code in the project draws
it. Same for `account.png` and `losses.png`, in five folders.

Fixed by `figure_style.sweep()`: each stage records which figures it wrote, and
clears its own leftovers on the next run. 02 cannot delete 03's work. Files
written before the manifest existed are reported, never deleted.

## 17. Four cases when one was wanted — 09-25 to 09-29

I built four traction cases — long loop, short loop, shredder, split — each
sending 100% of motors one way. A fleet is none of those. It also meant four of
every figure and nothing to read as the answer.

*"I want one clear answer that one understands, not 100% for four different
cases. We discussed this."* And: *"Your current solution is absolutely not
practical and overshoots the target."*

One case now. One builder: `tools/build_tractionmotor_case.py`. The pure routes
stay reachable by pinning `removal` to 1 or 0.

## 18. A refactor when a rename was needed — 09-29

Asked to make the case simply `tractionmotor`, I began merging four builders
into one file — while he was blocked and waiting to run. *"You are costing me
so much time and money."*

The rename was four lines. I did the four lines, committed, pushed, and he ran.
The consolidation was right, but it was not what unblocked him, and I chose it
without asking which came first.

---

## 19. 05 silently dropped the traction motor's copper — 09-29

Four helpers in `05_combine_cases.py` picked *the deepest layer with anything
in it* and compared every resource against that one column. On the traction
case that column is Layer 4 — Nd, Pr, Dy, Tb — while copper, aluminium, steel
and lamination stop at Layer 2/3 and are blank there. So `named_in` returned
`None` and the run printed

    data/tractionmotor: none of copper, Cu in this case -- skipped

which reads like a case that simply has no copper. It has **60.0 kt** recovered
in 2070, against the wiring case's 497 and the battery's 381 — about 9% of the
combined total, missing, and reported as a normal skip.

`src/plot_monte_carlo.resource_key` had fixed exactly this for the figures on
2026-09-25. This file never picked it up.

**Found while measuring runtime for an unrelated speedup.** No check would
have caught it: a skipped case is a thing 05 prints on purpose.

## 20. The fleet stock summed 5-yearly samples as annual — 09-29

`figure_trapped` asserted in its own docstring that *"the upstream export is
annual and all of it is read"* and used `np.cumsum`. True of the electronics
(51 years, step 1); **false of the battery and the traction motor** (11 years,
step 5). Measured on a flat 10 kt/year flow over 2020–2070:

| | total by 2070 |
|---|---|
| `cumsum`, what it did | 110 kt |
| trapezoid, correct | 500 kt |
| truth, 10 × 50 years | 500 kt |

Every traction and battery stock was about a fifth of the truth.
`05_combine_cases._accumulate` has integrated over the year gaps since it was
written. Found from the question *"is it not per year?"*

## 21. The shared unit judged unconverted numbers — 09-29

Fixing the axis units (entry 23) I added `_shared_unit`, which took a list of
dicts and a key to pull numbers out with. For the stocks it pulled them
straight from `fleet_flows` — whose arrays are the **upstream's**, in the
upstream's unit, because the conversion happens afterwards inside
`figure_trapped`. A 265 kt stock was judged as the number 265 against a unit of
kg; 265 kg does not reach a tonne; the axis came out in kilograms with `1e8`
stuck in the corner. *"What the hell kg."*

It takes values now, not a dict and a key, so a caller that has not converted
cannot pass the wrong thing by accident.

## 22. Dots drawn off the curve, and a label a sample late — 09-29

The crossings on `fleet_<r>.png` were drawn at the threshold VALUE and the
first SAMPLED year at or past it. The model solves every fifth year, so
copper's share climbs 9% → 18% between 2035 and 2040, stepping over 10%: the
dot went at (2040, 10) while the line at 2040 is at 18. *"I have points in
green which do not align with the curve. Why?"*

The panel above had the same fault and nobody had reported it: *"2055: the
stock peaks"* sat one sample past the peak of a curve that plainly peaked at
2050, because 2055 is the first year with a negative net flow.

One mistake twice: **labelling from the underlying condition rather than from
the curve that is drawn.**

## 23. Five axes said a bare `mass (kt)` — 09-29

`over_time`, `fate`, `account`, `losses` and `convergence` all draw per-year
flows and all labelled the axis `mass (kt)`, leaving the reader to decide
whether a point was that year's flow or everything up to it — quantities that
differ by a factor of fifty over this horizon. *"Either it is total mass of
copper or mass / year."*

## 24. A cache inserted into the wrong function — 09-29

Anchored on

    source = getattr(run, 'upstream', None)

which appears in both `figure_fate` and `account`. The edit took the first
match, so the cache's head landed in `figure_fate` — which has no `resource` to
key on — while its writes landed in `account`, where `store` was then
undefined. **Every 03 run crashed.**

I had checked that the module imported and that the 143 fixture checks passed.
Neither touches `figure_fate`: it needs upstream draws the fixtures do not
have. He found it by running it.

## 25. 05's own figures in `detail/`, and a stream called `copper` — 09-29

All four of 05's writes omitted `essential=True`, so the entire output of the
stage was filed under `detail/` — in a folder that contains nothing else to be
separated from.

And on the copper figure, one line in the legend was labelled `copper`. Streams
are named by their case's Layer 2 — `wiring`, `pcb`, `sensors` — and the
traction case's components ARE the materials, so its copper component is called
copper. *"What is the copper?"*

## 26. Warned about a problem that did not exist — 09-29

Before he ran 05 I warned that copper would come out in Mt and terbium in t,
reasoning from `scale_for`. **05 does not call `scale_for`.** It has pinned
every axis to `AXIS_UNIT = 'kt'` since 2026-09-25, after he asked for exactly
that. Three lines in the file, none of which I read before warning him.

Not a defect in the code — a defect in what I told him, which sent him into a
run braced for a bug that had been fixed three weeks earlier.


## 27. I defended a band that was five times too narrow — 09-30

He asked why the in-fleet band on `fleet_<r>.png` was so small at the end when
every other range widens, and whether the Monte Carlo had been done properly.

I measured, and answered that it was correct: the fleet stock is
`inflow - outflow`, both read straight from upstream, so it carries no transfer
coefficient and only inherits the upstream's own spread of ±4.9%. I showed the
correlation of 0.991 between inflow and outflow and called the narrow band
arithmetically right. I then went one step further and told him the *upstream*
was the confident one, and that this caveat applied to every case equally.

**All of that was wrong, and he found it in one sentence:** the inflow is
vehicle count times composition, the count alone has a CV of 12.1%, so the
product cannot have a CV of 2.5%. A product of two uncertain things cannot be
more certain than either of them.

`04_03` in `RAWCLICStockAndFlow` uses the tracker's point-estimate vehicle
counts; `04_02` uses the per-draw counts in `bev_draws/`, which sit in the same
folder and are written by the same run. So every traction interval is about
five times too narrow — `sqrt(12.10² + 2.53²) = 12.36%` against 2.53% — and
the caveat I said applied everywhere applied to exactly one of the two exports.

See `DEFECTS.md` 3.25.

**Why this one is worth its own entry.** I did measure before answering, which
is the habit the rest of this file exists to enforce. Measuring was not enough:
I measured the thing I was asked about and stopped, instead of asking what the
number had to be consistent with. A band that is too narrow looks like nothing
at all — no check fails, no figure misdraws, the interval is simply a lie about
precision. *Verifying a number against itself is the first pattern in this
file, and I did it again while quoting statistics at him.*


## 28. I measured means to answer a question about spread — 09-30

Having established that the traction export omits the fleet count's
uncertainty, I proposed a correction and called its first step: *check that the
tracker's counts equal the mean of `bev_draws`.* I ran it, found they disagree
badly before 2060 — 83% at 2035 on collected — and reported:

> **Step 1 says: not well-posed. Do not proceed to step 2 yet.**

**That recommendation was wrong and it was the expensive kind of wrong.** The
correction injects spread by multiplying by `count_draw / count_mean`, a ratio
whose mean is 1. The means can disagree by any factor at all and it changes
nothing about whether the CV can be injected. I had invented a precondition,
failed it, and told him to stop work on a real defect and go investigate
something unrelated in another stage.

He stopped it in one line: *"We talk about CV and not the means."*

The useful measurement took two minutes once the question was the right one:
the count CV runs 7% to 21% by year against a composition CV of 2.5%, so the
traction intervals are 2.9x to 6.6x too narrow depending on the year.

**The pattern.** #27 was answering the question asked and stopping too early.
This is worse: substituting a question I could measure for the one that was
asked, and then giving a confident instruction based on the substitute. The
mean disagreement may well be a real problem -- it is now on the record as a
separate one -- but it was not an answer to anything being asked, and dressing
it as a blocking result cost a step of the actual work.

*Before reporting a check as blocking, state what it would have to show to
block, and confirm that is the thing being measured.*


## 29. I rediscovered a solved problem, then got it wrong in the way the record warned about — 09-30

Everything in entries 27 and 28 — the traction export not sampling the vehicle
count, the measurement of how narrow the intervals are, the proposed fix, even
the decision to leave the cohort mix deterministic — **was already done in
`RAWCLICStockAndFlow` on 2026-09-22.** There is a committed script,
`code/proof_0403_vehicle_draws.py`, that names the exact line
(`src/traction_draws.py:222`), states the proposed formula, and measures the
effect. The finding is written up in that project's `HANDOVER.md` under a
heading reading **"THE BLOCKER IS RESOLVED"**.

I never looked. A day went into re-deriving it, and I wrote Matthias a
specification for a decision he had already taken and recorded.

**Then I got the substance wrong in the precise way that record warns about.**
My implementation divided by the draws' own mean so that no mean would move,
and my specification stated "means must not move" as an acceptance criterion.
The 22 September analysis had already established the opposite:

> Outflow is a nonlinear function of the drawn lifetime, so
> `E[outflow(λ)] ≠ outflow(E[λ])`. The tracker is one deterministic run at the
> point lifetime and therefore CANNOT equal the Monte Carlo mean. The draws are
> the correct quantity; the tracker's collected is biased high by 2–6%.

So "no mean moves" is not the safe choice. It preserves a measured bias and
presents the result as an uncertainty fix. Corrected: the drawn count replaces
the tracker's, and the medians fall — `inflow` 0.5%, `collected` 6.9% at 2040.

**What this costs beyond the day.** In entry 28 I reported the tracker/draws
disagreement as a blocker and was told it was not the question. It genuinely
was a blocker once — the 22 September handover opens with it as one — and had
been resolved the same day, with a cause. I had the disagreement in front of me
and no idea it had been diagnosed, because I was measuring instead of reading.

*Two repositories, one model. Before investigating anything upstream, read the
upstream handover.*


## 30. I said the battery cases ran end to end, on a stand-in that had mass in every year — 10-08

I built five cases and checked them on a stand-in export made from the real
composition files, and reported that every case ran in every version with the mass
balance at exactly 100.00 %. It was true of the stand-in. The stand-in had mass in
every year; the real export has years in which solid-state has none (S3, before
2040), and on the real export that pass stopped with `'NoneType' object has no
attribute 'mean'` (DEFECTS 3.26). The 100.00 % was also a product of the
stand-in: I had clipped the composition files' own noise out of it, and the real
export reads between 99.99 and 100.57 % at a few hundred draws.

It would have stopped his twelve-pass run at its last pass, hours in. It did not,
because I ran each case on the real export, one at a time at a few hundred draws,
after his 04_04 finished and before he pressed Run. Five commands, about fifteen
seconds each.

*A stand-in has the shapes you thought of. "Ran end to end" is a statement about
the thing it ran on; say what that was, and run the real one before he does.*

## 31. I typed numbers into the document that says where its numbers come from — 10-08

`BATTERY_ROUTES.md` exists to say where every number comes from. Its first draft
had numbers I had not looked up: a deviation of "up to 14 points" that I had
measured on the paper's target series and not on the estimates the model uses
(11.7); "Route 4's rates are taken to be Route 1's; they agree at the targets"
(they differ, the aluminium foil most); "3.5 % of everything collected" (3.5 % of
the cell stream, 2.1 % of what is collected); handed-on mass "not subtracted from
lost" (it is: lost is collected less recovered less handed on); "combine S2 and S3
with all five" (solid-state has no S2); and a loss flow labelled with the first
road's process, so that the loss figure would have charged hydrometallurgy with
mass that never reached it. Three wrong statements had already gone to him in chat:
the REC lithium "copy error" (it is the regulation's target), that BAU never
recovers manganese (it does), and the deviation figures, measured on the targets
(the first item above).

I caught them, before anything was pushed, by reading every number in the
document back against the workbooks, the paper's sheets and the code. None of that
needed him.

*A number in a document is read from the data when it is written, not remembered
from the day it was found.*


## Patterns

Thirty-one failures, eight shapes. The shapes repeat; the instances do not matter
much.

**1. Verified against itself.** #7, #8, #14, #27. A Sankey that balances, an account
that closes by construction, a check that blends at the number it is checking.
All three were internally consistent and all three were wrong. *A figure or a
check that can only be tested against itself is not tested.* Every check must
compare against something produced by a different path — the `Recovered` sheet,
the review's published values, the upstream arrays.

**2. Verified in the source, not in the output.** #15, #16, #11, #12, #30, #31. I read
code and concluded the output was right; I wrote a table and pushed it before
reading it; I named a document without opening it. This is the single most
expensive pattern in the list — it cost more days than every other entry
combined. *Open the artefact. The file on disk, the rendered image, the actual
PDF.*

**3. Silent absence.** #5, #6. Nothing failed, nothing warned, four figures
were simply not there for weeks. *A stage that cannot draw something must say
so; returning `None` quietly is a bug even when the code is correct.*

**4. Invented what the source already had.** #13. The coefficient was in his
workbook, with a range and four references. I made one up. *When a number is
needed, look for it in the study before deriving it, and say which cell it came
from.*

**5. Renamed without clearing.** #16, and the reason `tractionmotor_fleet` was
confusing at all. An old name that still resolves — a file, a folder, a case —
is worse than a missing one, because it looks current. *A rename is not done
until the old thing is gone or marked.*

**6. Fixed in one file, left broken in the other.** #19, #20, #22, #23, and
the axis ruling the same day. `resource_key` solved mixed-depth resources for
the figures and 05 never picked it up. `_accumulate` integrated over year gaps
and `figure_trapped` never picked it up. `_tight_step` used the full panel and
the shared `_round_step` never picked it up. Every one was solved correctly
somewhere in this repository while the other caller stayed wrong for weeks.
*When a fix is worth making, find every caller of the thing it fixes — the
second one is where the defect survives.*

**7. Measured instead of reading.** #29. A committed proof script, a handover
section headed "THE BLOCKER IS RESOLVED", and a decision with a date on it — all
sitting in the sibling repository while I re-derived them from the arrays. The
project's own record is faster than any measurement and it carries the reasons,
which measurements do not. *Read the handover of the repository you are about to
investigate, before you investigate it.*

**8. Widened the scope past the ask.** #17, #18, and the hundreds of figures.
Four cases when one was wanted; a refactor when a rename was wanted; every
resource drawn when he had said twice it was the magnet, its elements, and
copper. *Do what was asked, at the size it was asked.*

---

## What these cost him, in his own words

> "I have always to check and then fight with you so bad!! I hate that I have
> to do this."

> "I will now control everything."

> "I do not trust you anymore!!"

Every one of those followed a failure in this register. Entries #7, #11, #13
and #15 are the ones that earned them: in each case the work looked finished,
reported success, and was wrong, and he found it rather than any check of mine.

---

## The record this is drawn from

`DIALOG.md` holds the whole conversation, both sessions merged in time order,
2026-08-17 to 2026-09-30 — 1,707 turns, 497 of them Matthias's. Every entry
above can be read back to the exchange it came from, in his words rather than
my summary of them. Kept in the repository at his instruction on 2026-09-30:
*"I want documentation of all your failures."*

---

*Kept current. A new failure gets an entry on the day it is found, not at the
next handover. If an entry here is ever fixed, the fix is named in it — an
entry with no fix named is still open.*
