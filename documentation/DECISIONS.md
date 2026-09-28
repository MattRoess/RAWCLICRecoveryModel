# Decisions

**Read this before touching anything. These are settled.**

They are not preferences to weigh against tidiness, brevity, or what a tool
happens to generate. Where one of them looks wrong, say so **once, before
building** — and then do it the way it says here. Reopening a settled decision
by quietly building something else is how a whole day gets spent on rework.

This list exists because the user remembers what they decided and the assistant
does not. **Add to it the moment something is decided.** A decision that only
lives in a chat message is a decision that will be broken.

---

## The coefficient table

1. **No `is_residual`. Ever.** Every coefficient is a value with its own range.
   Nothing is derived as `1 − the rest`. This was decided, then broken twice
   because a derived row makes a table shorter — which is not a reason.

2. **No row that cannot carry mass.** If a material never reports to a stream,
   there is no row for it. A table you have to read to discover that a row says
   nothing is a table that misleads: `copper` on an `F_recovered_al_alloy` row
   read as though copper were inside the aluminium alloy, and it took 22 dead
   rows out of 46 to hide that.

   `tools/make_skeleton.py` expands the full material × destination matrix, so
   for these cases the table is **written directly, not generated**.

3. **Never invent a number without marking it.** `source` says
   `PLACEHOLDER (Claude, not data)` on every value nobody measured, and a
   derived or definitional value says which it is. Never imply a placeholder is
   data.

4. **A number that restates another is not a second measurement** and its
   `source` must say so.

27. **An improving case carries two complete tables, not a diff.**
    `TCs_improved` repeats every coefficient `TCs` has. Decided 2026-09-03
    against listing only what changes: an implicit "unchanged" is invisible,
    and a full copy can be read side by side. The cost is that a value edited
    in one sheet and not the other becomes an unintended improvement, which is
    why the two are matched by identity and any mismatch is refused.

28. **One improvement window for the whole case**, `improvement_start` and
    `improvement_end` in the `source` sheet. Not per coefficient: a scenario
    should be sayable in a sentence -- "the programme runs 2030 to 2060".

29. **A draw is one world across the years.** The same coefficient must draw
    the same uniform in every year, so an improvement is one ramped belief
    rather than a fresh guess per year. This is why `_stream_key` excludes the
    year, and it must stay excluded.

30. **A warning in a run means something is WRONG.** Not "worth thinking
    about", not "a question somebody should answer" -- wrong. Decided
    2026-09-03 after the run warned about a complementary pair of coefficients
    that may be two perfectly good measurements. A warning that fires on a
    correct table teaches its reader to scroll past warnings, which costs more
    than it saves. Advisory findings go in a tool the reader opens on purpose:
    `tools/tc_worklist.py` for measurement questions, `tools/filling_sheet.py`
    for what to measure next.

## The layers

5. **The metal route is materials only. No element layer under an alloy.**
   What a shredder produces is a stream a recycler sells: copper, an aluminium
   alloy, an iron alloy. Whatever is alloyed in stays in. `Mn recovered` claims
   a manganese separation nobody performs.

6. **`fealloy` is steel, cast iron AND the ferrite magnets** — one stream.
   Ferrite is ferrimagnetic, so a magnet leaves the separator inside the ferrous
   fraction as an impurity in the steel. Not a magnet product, and its strontium
   is not recovered as strontium.

7. **Elements only where a process really separates them.** The specialist
   board and sensor route grinds and then runs one process per element, so gold,
   silver and palladium come back as themselves. That is the only place an
   element layer belongs.

8. **The motor copper is wiring.** Windings are copper, and belong in the copper
   stream.

## The network

9. **Each case keeps its own `processes` sheet.** Separate, not shared. Do not
   introduce a common network file.

10. **Two roads, and they are the point:**

    - **Disassembly** — parts are taken out **whole, with tools**. They go to
      their **own** shredder and their **own** recycling process.
    - **Not disassembled** — the part **stays in the car**, and the car goes to
      the **general** shredder.

    **Nothing is lost by not being disassembled.** It simply travels the other
    road. There is no loss flow at disassembly.

11. **Report the two roads apart, and also combined.** Combined is the two added
    together in reporting — never a third flow, which would count the same metal
    twice.

12. **A board left in the car IS followed, and only copper comes back off it.**
    Reversed 2026-09-04 by the user, who had asked the opposite earlier. The
    general shredder returns copper -- it survives crushing as sortable pieces
    and the separators find it -- and everything else on that road is lost:
    a trace element ground into mixed shredder residue is separated by nobody.

    So `F_shredded` is no longer a `handoff`. It ends in `F_cu_general`
    (recovered) and `F_loss_general` (loss), which is the shape the wiring case
    already had. Both cases now follow both roads to the end, and neither hands
    anything on.

    What the earlier version said, and why it was wrong to keep: splitting the
    shredded road into aluminium, iron and trash would have cost three flows
    and six placeholder coefficients nobody would read. Copper alone costs one
    flow and one number, and it is the one that carries mass.

38. **Grinding and element recovery are two steps, not one arrow.** The
    specialist route ran `F_disassembled -> F_recovered_own` under a
    technology called `grinding_then_element` -- the name itself said it was
    two things. It is now `F_disassembled -> F_ground` (grinding, definitional:
    everything taken out whole is ground) and then `F_ground -> F_recovered_own
    / F_loss_own`, where the individual elements are separated one process at
    a time. Decided 2026-09-04. DECISIONS 7 said elements belong only where a
    process really separates them; this makes that process visible.

39. **A column of the structure diagram is ordered by its parents, not by the
    alphabet.** Sorting each column by name put the two ends of one road above
    the two ends of the other, so every arrow crossed every other and the
    picture said the roads mix when they do not. Each road now travels straight
    across the page.

## Figures

13. **Never rescale to make things look comparable.** An early version of the
    density figure divided every curve by its own median so the three alloys
    would overlay. It made copper's uncertainty — about ten times aluminium
    alloy's in kilotonnes — look identical to it. *"This is how to lie with
    statistics"*, and correctly. Absolute values, on axes that say what they
    are; where scales differ, give each panel its own axis and state its
    numbers on it.

14. **A figure is per year, never summed across years.** Adding 2030's 10 kt to
    2050's 254 kt gives a quantity nobody has a use for, dominated by the last
    year. This holds for a ratio too: `mode_vs_mean` divided one such total by
    another and looked right, because both halves were wrong the same way.

    Where one year has to stand for the others, **measure how much the others
    differ and print that number on the figure.** Do not assert it.

15. **Say which years a figure covers**, on the figure.

16. **The deterministic run belongs on every distribution figure.** The gap
    between it and the spread around it is the reason to draw the distribution
    at all.

17. **A figure has to be readable at the size it is drawn.** A shape you have
    to squint at is a shape nobody checks.

18. **Do not invent a figure that already exists.** `pdf_<resource>` already
    drew the per-year densities; five replacements were built before that was
    noticed. Look at what is there first.

31. **A rate divides by ITS OWN inflow.** Recovered copper over TOTAL collected
    mass is a composition figure wearing a recovery figure's label: on the
    wiring case it fell 57% to 44% while copper's actual recovery held at
    77-78%, because copper's share of the inflow dropped as motors grew against
    harnesses. The first version of `recovery_rate.png` made exactly that
    mistake and the user caught it. Only the all-resources line divides by the
    whole, which is the one case where that IS the question.

32. **The inflow draws are propagated.** Decided 2026-09-03. The Monte Carlo
    pairs upstream draw i with coefficient draw i -- the same independent
    pairing 04_01 uses upstream -- so an interval carries the fleet's
    uncertainty as well as the coefficients'. It did not until that date, and
    the intervals were too narrow: copper collected in 2070 is 516 kt spanning
    388-670, against coefficient ranges that are narrower than that.

    The shares are per draw too. Inflow per draw with a mean share would scale
    copper by the fleet's variation while fixing copper's share OF that fleet,
    which is neither the mean answer nor the draw's.

33. **A figure names things in the modeller's words, never in the model's.**
    `routes.png` titled its panels `F_disassembled` -- an internal flow id
    standing where a reader expects the name of a thing, and misleading because
    a flow is a place in the network while the road is the PROCESS that happens
    there. Routes are named from the `process` column: `own recycling`,
    `general recycling`. Decided 2026-09-03, after the user had to point it out.

34. **A road is a side of the SPLIT, and the sides are named as a decision and
    its negation.** `disassembled` and `not disassembled` -- not
    `own recycling` / `general recycling`, which name where the material ends
    up and so read as two independent roads a part could choose between. It
    cannot: taken out of the car, it is not in the car any more. Decided
    2026-09-04, after two wrong namings in a row.

35. **The two roads are anti-correlated and the figure has to show it.** Two
    95% bands side by side invite reading both at their upper edge at once,
    which no draw can do. The split -- one road's share, formed per draw -- is
    drawn as well, and its narrow band IS the correlation.

36. **A rate is formed inside the draw, numerator AND denominator.** Since the
    inflow draws are propagated (32), dividing a draw's recovered mass by the
    MEAN inflow hands the fleet's whole spread to a number the fleet cannot
    move: copper's 2020 recovery band came out at 142%, which is not a wide
    estimate but an impossible one.

37. **One question, one set of axes.** The copper account was three files, then
    one file of four panels, and both were the same mistake: the moment two
    quantities sit on different axes, comparing them means reading one,
    remembering a number, and looking at the other. Everything that is a mass
    in the same unit goes on the SAME axis, and then every comparison is a
    distance on the page. Decided 2026-09-04 -- *"Only if things are directly
    comparable, then one can understand the topic"*. The one exception is a
    quantity in another unit: the recovery rate is a per cent, so it is on a
    right-hand axis, drawn heavier, and says on its own axis what it is.

40. **`rest` is waste and is not a resource.** It is the part of a parent
    nobody itemised, derived by `src/rest.py` so composition closes to 1 --
    fibreglass, resin, plastics, solder on a board. No coefficient sends it to
    a recovered flow. It is out of the figures and out of the denominator of
    the total recovery rate: on the boards case it is 45% of the collected
    mass, which put a fixed ceiling of 55% on that line and made a real
    improvement read as flat, 46.5 to 51.9%. Against the recoverable inflow the
    same improvement is 84.1 to 94.8%. Decided 2026-09-04 -- *"the rest has to
    be excluded as it is waste"*.

41. **Cases are added for the reader, never merged.** `05_combine_cases.py`
    adds one metal across several case folders -- copper from the wiring and
    from the boards is the copper BEV electronics returns. Each case stays its
    own study (20): its own folder, network, coefficients and run. The addition
    is reporting, the same way the two roads are reported apart and also
    combined (11).

    **Per draw, never per percentile.** Every case reads the same upstream
    draws with the same seed, so draw i is one world in all of them. Adding
    percentiles would assume every stream hits its own 97.5th at once, which is
    wider than any world can be.

    A separate stage because the list will grow: battery packs and drivetrains
    join by getting a case folder and being named in `combine.cases`.

## Words

19. **Disassembly** is taking a part out whole, with tools, on purpose.
    **Shredding** is **crushing and tearing** — not cutting. A shredder is
    hammers, not blades. This is not pedantry: crushing and tearing is *why*
    brittle things shatter into unrecoverable dust while tough things survive as
    sortable pieces, and it is where the numbers come from.

## Working

20. **Never delete, and never overwrite with different data.** Separate cases by
    **folder**. "Bring the old one back" means restore it verbatim from git.

21. **Never re-run an upstream stage to test.** Read what is on disk. Never
    200,000 draws for a test.

22. **Never conda.** venv and a pinned `requirements.txt`.

23. **No command line.** Everything runs by pressing Run in Positron, with the
    case chosen in `src/params_schema.py`.

24. **Verify it before showing it.** Open the figure, check the number. Do not
    hand over work for the user to find the bug in — and do not check a change
    in isolation when the question is what the whole thing produces.

25. **Ask before adding anything.** No new file, tool, wrapper or intermediate
    step that was not asked for. A question wants an answer, not a project.

26. **Document in the same commit as the change**, and add any new decision
    here.

27. **Every figure is Monte Carlo and shows its uncertainty.** Stated twice on
    2026-09-25 and settled on 2026-09-28 -- *"yes wire it into 03, I want full
    MC"*. The Sankey was the last figure drawn from a single point solve, and
    the flow picture is exactly where a reader goes to find out where the
    copper went.

    A Sankey cannot carry a range in a ribbon, so it draws the MEAN -- the only
    central value that balances, because means add -- and prints each node's
    95% interval under it. It is also one year out of eleven. Both limits are
    said on the figure rather than left for the reader to discover.

    03 writes the Sankeys under the same names 02 uses, so a case folder holds
    ONE per resource. Run 02 alone and the point-solve versions come back; the
    subtitle is what tells them apart.

28. **A study is a file you press Run on, not a setting you edit.**
    `02_electronics.py`, `03_tractionmotors.py`, `04_batteries.py`. **The
    number is the UPSTREAM stage that feeds it** -- 04_02, 04_03, 04_04 in
    RAWCLICStockAndFlow -- and not a step in a sequence here. The three are
    alternatives; one gets pressed, never all three in order.

    The pipeline stages moved to `stages/` the same day. The project root
    shows what to run and nothing else.
    Decided 2026-09-28 -- *"we are running electronics, battery and
    tractionmotors using different parameters setting. This proves not
    efficient."*

    Each names its cases, its scenarios and its figure resources in `STUDIES`
    in `src/params_schema.py`, in one place, so a run cannot be started with
    the last study's settings still in force. The numbers follow the UPSTREAM
    stage that feeds each one.

    This does not reopen decision 23. A switch that exists only on a command
    line is invisible; a file in the project root is not.

29. **The traction motor study is about the MAGNET, ITS ELEMENTS, AND COPPER.**
    Said more than once before it was written down here, which is why it is
    here: *"I told you that I am interested in magnets, its elements and
    copper... You should know this already!"* (2026-09-28).

    Nd, Pr, Dy and Tb, the magnet they sit in, and copper. Those get the
    per-resource figures -- the densities, the account, the losses, what is
    trapped, the Sankey.

    **Aluminium, steel and lamination are not dropped, they are not the
    question.** They come back either way; the review's own numbers say the
    shredder recovers MORE steel than careful dismantling, 0.72 against 0.60.
    What the route decides is the magnet and the copper. The bulk metals stay
    on the whole-case figures -- `spread`, `mode_vs_mean`, the total Sankey --
    which read every resource regardless of the setting.

    `over_time` did NOT honour this until 2026-09-28: it drew every resource in
    the data, nine lines on the traction study, and I said otherwise before
    checking. *"I am not interested in al, steel but REE and copper."* It
    honours it now.

    `figures.resources` is where this lives, per study, in `STUDIES`.

30. **Six figures in the folder, the rest in `detail/`.** A traction motor run
    wrote 512 figures -- 16 folders of 32 -- and finding the answer meant
    knowing which filename to look for. *"I want to be able to see what is
    essential and not diluted by hundreds of other figures"* (2026-09-28).

    | | |
    |---|---|
    | `over_time` | what comes back per year, with its 95% band |
    | `recovery_rate` | the share of what was collected |
    | `account_<resource>` | in, out, recovered, lost, never collected |
    | `losses_<resource>` | why it does not come back, and how much of each reason |
    | `total` | the Sankey: where the mass went |
    | `pdf_all` | every resource's distribution on one page |

    **ONE RESOURCE PER FIGURE for the account and the losses.** Six in a grid
    came out 9,833 pixels wide, and the losses version 19,166 -- unreadable at
    any size a screen shows. *"Have them in individual figures, so one can see
    them"* (2026-09-28).

    **Nothing stops being drawn.** `src/figure_style.ESSENTIAL` names these;
    every other stem lands in `detail/` beside them, so a new figure is detail
    until somebody decides otherwise.

31. **A study runs the scenarios that answer its question, not all of them.**
    The traction study is `mix` only. Nd and Pr are byte-identical across SH,
    UH and EH -- the workbook's didymium range covers all three -- so the
    pinned grades move Dy and Tb and nothing else, while costing four times the
    folders. `mix` draws the grade per draw, which is what a fleet is. Pin one
    for the question it answers: *what if only EH is feasible.*

32. **02 and 03 draw the same resources.** 02 drew a Sankey for every resource
    in the data while 03 drew only those in `figures.resources`, so 02's
    point-solve pictures stayed on disk beside 03's Monte Carlo ones,
    indistinguishable but for their subtitles. Both read the setting now.

33. **A title on a figure about years states the SHAPE, not one year.** The
    account panels read *"Dy in 2070: 2 kt left the fleet, 1 reached a
    recycler, 0 came back"* -- a snapshot on a figure whose whole subject is
    eleven years of trajectory. *"I am not interested in 2070, but about the
    general shape over the years"* (2026-09-28).

    Two ends is the smallest honest summary of a shape:
    `Dy 2020-2070: 2.83 t -> 1.58 kt leaving the fleet, 2 -> 24% of it
    recovered`.

34. **Every printed number carries its own unit** -- `src.units.readable`.
    The same titles rounded to whole kilotonnes on a shared scale, so
    dysprosium read `0 came back` while the curve under it plainly rose, and
    the legend said `recovered 0 kt in 2070` on a line that had grown all
    century. A number a reader can see is wrong is worse than no number.

35. **A panel title says what the panel is; the figure header says what it
    found.** The losses summary written as a panel title was wider than its
    panel and ran through the title of the one beside it.
