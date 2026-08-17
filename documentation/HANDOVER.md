# Handover

State as of 2026-08-14. Everything below is either verified by running it or
flagged as a decision still to be taken.

## 1. Where things stand

The model works, in the narrow sense that both engines reproduce the committed
reference result exactly:

```bash
./.venv/bin/python compare_engines.py data_folder/basic_test
# 180 rows, largest engine difference 8.9e-16
```

The core algebra — nested layers, composition expansion, TC application,
topological process ordering — is sound, and two independent implementations
agreeing is real evidence for it.

It did not run when inherited. Three pandas-3 breakages were fixed
(DEFECTS.md §1). Beyond `basic_test`, **seven** divergences between the engines
remain open and change results (DEFECTS.md §2). Four of those — §2.1 and
§2.5–2.7 — are one absence: no input table is validated before use, so bad
input is silently absorbed rather than rejected (DEFECTS.md §5).

Nothing about uncertainty exists yet. That is the work ahead.

## 2. Environment — decisions and why

**No conda, on this or any machine.** Plain venv, pinned requirements.

| Decision | Value | Why |
|---|---|---|
| Python | 3.14.2 | Already installed; avoids a mid-project migration. |
| pandas | 3.0.5, pinned | See below — the pins are load-bearing. |
| Editor | Positron | `.vscode/settings.json` is committed, so `.venv` is auto-selected. `ipykernel` is in requirements for the console. |
| Repo | `MattRoess/RAWCLICRecoveryModel`, private | Empa research code; can be made public later. |

**Setting this up on another machine: see [SETUP.md](SETUP.md).** It covers
installing Python 3.14 without conda, building the venv, selecting the
interpreter in Positron, and the pyenv trap that bit us on the first machine.
Verified reproducible from a clean clone.

The version pins are not caution for its own sake. The pandas copy-on-write
change turned a `fillna` call into a silent no-op and inflated this model's
intermediates 300,000-fold **without changing its output** (DEFECTS.md §1.3).
Unpinned, that class of failure recurs invisibly. Do not relax the pins without
running the comparison above.

Python 3.13 + pandas 2.2 was the considered alternative — everything would have
run unmodified. Rejected because the code needed fixing either way, and
migrating mid-project is worse than fixing now. `environment.yml` was deleted;
it is recoverable from commit `cc82a0a` if ever needed.

## 3. Commits

| Commit | Contents |
|---|---|
| `cc82a0a` | The code exactly as inherited. Baseline for reviewing every later diff. |
| `ee3fc6b` | Environment setup and the three pandas-3 fixes. |
| `902b04c` | This documentation set, `compare_engines.py`, and the defect cases. |
| `9cbbe8d` | Corrected the TC mass-balance grouping; added `check_mass_balance.py`. |
| `f082c7b` | Positron terminal auto-activation. |
| `f719d5f` | TC table schema proposal and the `template` worked example. |
| `cf9b188` | `plot_flows.py` — mass-weighted Sankey figures. |

## 4. Open questions — these need answers, not code

These are method decisions. They are listed in DESIGN_monte_carlo.md §6 with
context; repeated here because they gate the work.

0. **What is the flow network?** Which processes exist, and what output flows
   each one has. The real TC table does not exist yet (confirmed 2026-08-14),
   so this is the gating question and it is entirely a method decision.
   DESIGN_tc_table.md proposes the schema and the four rules; the network
   itself is domain knowledge.
1. **Do losses get explicit flows?** Recommended yes — it is the only thing
   that makes "everything sums to 1" true rather than aspirational, and it
   turns mass balance into something assertable on every draw. The cost is
   real and should be accepted knowingly: every resource then becomes a split
   set, so the joint-constraint sampling in DESIGN_monte_carlo.md §4 becomes
   the core of the design rather than a corner case.
2. **How should overlapping TC specificity resolve?** The two engines disagree
   by a factor of two and the user guide is silent. This must be settled
   *before* element-layer TCs are layered over component-layer ones — which is
   precisely what the new requirements ask for, so this will be hit immediately.
3. **Which TCs are correlated?** `TCs.csv` already carries `process` and
   `technology` columns that the model reads and discards. They are the obvious
   grouping keys for common random numbers.
4. **Is composition uncertain too, or only the TCs?**
5. **Which rows need full per-draw traces**, versus summary statistics only?
   This sets the memory budget.

## 5. Recommended order of work

0. **Settle the TC table schema** (DESIGN_tc_table.md) and start collecting
   into it. This is the long pole — it is data collection, it gates the Monte
   Carlo entirely, and it can run in parallel with all the engineering below.
1. **Regression test pinning `basic_test`.** Cheap, and the justification is
   concrete: defect 1.3 was a 300,000x blow-up that stayed invisible for months
   *because the output remained correct*. Without a pinned test, the Monte
   Carlo restructuring can silently move the deterministic answer and nobody
   will know. Compare with a tolerance rather than exactly — the LA engine
   varies by ~1.5 ULP between runs (DEFECTS.md §3.5).
2. **Validate the input tables on load** (DEFECTS.md §5). One check catches
   §2.1, §2.6 and §2.7 at the point where the error can still name the file,
   the column and the value — instead of, respectively, inventing mass,
   inventing mass, and either an unreadable `TypeError` or +4000 Mg of silent
   phantom inflow. `check_mass_balance.py` already does work of this shape.
3. **Fix the engine divergences** (DEFECTS.md §2.1, §2.2, §2.5), and settle
   §2.3 with whoever owns the method. Write the resolved semantics down — their
   absence is why §2.3 exists at all. §2.5 lands on the element-over-component
   layering the new requirements ask for, so it will be hit early.
4. **Add the mass balance assertion on load**, once the table has loss flows.
   `check_mass_balance.py` already computes everything it needs; this is
   promoting a report into a hard failure.
5. **Then restructure for Monte Carlo** (DESIGN_monte_carlo.md §2): hoist the
   join structure out, carry `Value` as `(n_rows x n_draws)`, chunk over draws.

Steps 1 to 3 are ordinary engineering and can start today. Step 0 is the long
pole and is not engineering at all — it is a method decision followed by data
collection, and nothing in step 5 can be finished without it. Step 5 should not
start before step 1 exists.

## 6. Picking up on Monday

Do these in order and you are back to where today ended in about ten minutes.

1. **[SETUP.md](SETUP.md)** — Python 3.14, venv, Positron interpreter. Finish
   with the verification block; if `compare_engines.py` prints *Engines agree*,
   the environment is good.
2. **Look at `figures/template_structure.svg`** — one page showing every flow,
   every process, and every transfer coefficient behind each arrow. It is the
   fastest way back into how the model is wired.
3. **Read [MODEL_MECHANICS.md](MODEL_MECHANICS.md) §1 and §4.** The nesting
   rule and what a TC can meaningfully sum to. Both are counter-intuitive and
   both were got wrong at least once during this session.
4. **Then [DESIGN_tc_table.md](DESIGN_tc_table.md)**, which is where the work
   actually resumes.

### The one thing waiting on you, not on the code

**The flow network.** Which processes exist, and what output flows each has.
The real TC table does not exist yet, so nothing downstream can be finished
without it, and it is entirely domain knowledge. `data_folder/template` is a
worked example of the shape the answer takes — seven flows, three processes,
explicit loss flows — not a proposal about the content.

Everything else in §5 is engineering that can proceed in parallel.

### Known unfinished

- **The structure figure needs a second pass.** `plot_structure.py` was written
  at the end of the session in response to the note that the Sankey diagrams
  did not answer "how is this set up". It is a first cut. If it is still hard
  to follow, that is the figure to iterate on, not the Sankeys.
- No regression test exists yet. It is step 1 of §5 and should come before any
  Monte Carlo restructuring.

## 7. Upstream context

Inflows come from `04_02` in the separate pipeline: per-element inflow, outflow
and collected in kt, at 200,000 draws, resolved by domain.

Two things carried over from that work:

- Collection there is applied to **whole vehicles** — one rate, identical for
  every element by construction. Element-specific recovery yield is not
  modelled anywhere yet. That gap is exactly what this model is meant to fill.
- **Known-open defect:** `mc_composition`'s Sensors series is mode-based and
  understates sensor domain mass by ~1.73x. `04_02` works around it for
  elements, but **domain mass still carries the error**. If this model consumes
  domain-level mass rather than element-level, it inherits the bias.

Draw alignment matters: draw *i* of the upstream inflow must pair with draw *i*
of the TCs here, not an independent resample, or the uncertainties will not
compose correctly.
