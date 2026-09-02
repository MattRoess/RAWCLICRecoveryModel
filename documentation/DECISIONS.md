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

12. **A board left in the car is not followed.** It goes to the general
    shredder and the boards case stops there -- ONE handoff flow, not a split
    into aluminium, iron and trash.

    Nobody is asking what a shredded board becomes. The question that case
    exists to answer is what the specialist route gets back, and the shredded
    road is there only to say how much never reaches it. Splitting it cost
    three flows and six coefficients that nobody would read, and each one was
    a placeholder.

    `handoff` is the role for it: not recovered here, not lost, passed to a
    process this case does not model. The wiring case DOES split its general
    road, because there the alloys coming off the general shredder are the
    answer rather than the leftovers.

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
