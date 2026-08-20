# Handover

State as of **2026-08-20**. Everything below is either verified by running it
or flagged as a decision still to be taken.

**Starting on the other Mac? Go straight to §7.**

## 1. Where things stand

The model works, and now works for the same reasons on both engines:

```bash
./.venv/bin/python tools/compare_engines.py data_folder/reference/basic_test
# 180 rows, largest engine difference 8.9e-16

./.venv/bin/python test_regression.py
# 16 of 16 passed
```

The core algebra — nested layers, composition expansion, TC application,
topological process ordering — is sound, and two independent implementations
agreeing is real evidence for it.

It did not run when inherited. Three pandas-3 breakages were fixed
(DEFECTS.md §1). Seven engine divergences were then found, and **all seven are
now closed** (DEFECTS.md §2): there is no input on which the two engines
disagree. Three were plain bugs; two were unspecified semantics that needed a
decision before any code could be right, and both decisions are written down
together with the option not taken; two are refused at load.

Bad input is no longer absorbed. `src/validate_inputs.py` runs before either
engine joins a row, and an unresolvable key, a composition row with a gap, a
mixed or unrecognised mass unit, or a share written as a percentage each stop
the run naming the file, the column and the value.

**The Monte Carlo exists as of 2026-08-20** and is checked against the
deterministic model: a table whose ranges have zero width reproduces the
deterministic answer exactly, mass is conserved on every draw, and a chunked
run matches an unchunked one value for value.

What it still lacks is real data. Coefficients are sampled from the ranges in
`TCs.csv`; inflows and composition are held at their stated values, because
the upstream per-draw arrays are not readable yet (§8).

```bash
./.venv/bin/python 04_run_monte_carlo.py
```

## 2. Environment — decisions and why

**No conda, on this or any machine.** Plain venv, pinned requirements.

| Decision | Value | Why |
|---|---|---|
| Python | 3.14.2, from python.org | Framework install at `/Library/Frameworks/Python.framework/Versions/3.14/` |
| pandas | 3.0.5, pinned | The pins are load-bearing — see below |
| matplotlib | 3.11.1, pinned | Added 2026-08-17; both figure scripts render through it |
| Editor | Positron | `.vscode/settings.json` is committed, so `.venv` is auto-selected |
| Repo | `MattRoess/RAWCLICRecoveryModel`, private | Empa research code; can be made public later |

**Setting up on another machine: [SETUP.md](SETUP.md).** It covers Python 3.14
without conda, the venv, the Positron interpreter, and two traps that have
actually bitten: a stored pyenv interpreter selection overriding
`python.defaultInterpreterPath`, and a venv broken by moving the project folder.

The version pins are not caution for its own sake. The pandas copy-on-write
change turned a `fillna` call into a silent no-op and inflated this model's
intermediates 300,000-fold **without changing its output** (DEFECTS.md §1.3).
Unpinned, that class of failure recurs invisibly.

**The venv is not relocatable.** It records its creation path in
`.venv/pyvenv.cfg` and hardcodes it into `bin/activate`, so moving the project
folder breaks it — and the symptom is misleading, because `./.venv/bin/python`
keeps working while the bare `python` name does not. SETUP.md §4 has the
diagnosis and the one-minute rebuild.

## 3. Commits

| Commit | Contents |
|---|---|
| `cc82a0a` | The code exactly as inherited. Baseline for reviewing every later diff. |
| `ee3fc6b` | Environment setup and the three pandas-3 fixes. |
| `902b04c` | The documentation set, `compare_engines.py`, and the defect cases. |
| `9cbbe8d` | Corrected the TC mass-balance grouping; added the mass balance check. |
| `f719d5f` | TC table schema proposal and the `template` worked example. |
| `cf9b188` | Mass-weighted Sankey figures. |
| `e74504f` | Structure diagrams and SETUP.md. |
| **2026-08-17** | |
| `eec3644` | Recorded why a moved venv breaks. |
| `5277377` | Four more engine divergences and two latent issues, from a full read. |
| `68a9408` | Figures through matplotlib; Sankeys drawn as part of a run. |
| `0799d6f` | Settings in code, `params.xlsx` generated; `plot_flows` on matplotlib. |
| `e3e0a81` | Numbered workflow, settings file, regression test. |
| `14ee1f4` | Every figure from step 1; `plot_structure` out of the workflow. |
| `8230b80` | Input validation, units included. |
| `5a83b37` | §2.1 and §2.2 fixed. |
| `3db7597` | §2.5 settled: a same-layer transfer carries, it does not transform. |
| `2363a1b` | §2.3 settled: overlapping rules resolve by specificity, and report. |
| `859b719` | §2.4 fixed: exact year and scenario matching, from one shared rule. |
| `c6faedc` | One scenario per run, each into its own output folder. |
| `1e7a64f` | Year selection, with a step. |

## 4. Open questions — these need answers, not code

0. **What is the flow network?** Which processes exist, and what output flows
   each one has. The real TC table does not exist yet, so this is the gating
   question and it is entirely domain knowledge. DESIGN_tc_table.md proposes
   the schema and the four rules; `data_folder/reference/template` shows the *shape* of
   an answer — seven flows, three processes, explicit loss flows — and is
   **not a proposal about the content**.
1. **Do losses get explicit flows?** Recommended yes — it is the only thing
   that makes "everything sums to 1" true rather than aspirational. The cost is
   real: every resource then becomes a split set, so the joint-constraint
   sampling in DESIGN_monte_carlo.md §4 becomes the core of the design rather
   than a corner case. One loss flow **per process**, not a shared sink — a
   shared sink was measured breaking the nesting by 82 t on a 30 t parent.
2. **Mg or kt?** Every data folder here is written in Mg; the upstream `04_02`
   reports in **kilotonnes**. That is a factor of 1000, and because the model
   only multiplies fractions, nothing in the output would look wrong.
   `expected_unit` in `src/params_schema.py` is set to `Mg` and the loader now
   warns on a mismatch — but which is correct is a data decision.
3. **Where does composition come from?** If it is generated the way BEV
   electronics was, it arrives as `(draws, years)` `.npy` arrays rather than a
   table, and the deterministic run should take the mean of those same arrays
   so the two cannot drift. Two pieces are domain knowledge: how grams per
   vehicle become shares within a parent, and how the electronics segment
   groups (AB/CD/EF) map onto products.
4. **Which TCs are correlated?** `TCs.csv` already carries `process` and
   `technology` columns that the model reads and discards. They are the obvious
   grouping keys for common random numbers.
5. **Which rows need full per-draw traces**, versus summary statistics only?
   This sets the memory budget.

Question 2 in the 2026-08-14 list — how overlapping TC specificity should
resolve — was **answered on 2026-08-17** and is now DEFECTS.md §2.3.

## 5. Recommended order of work

0. **Settle the TC table schema** (DESIGN_tc_table.md) and start collecting
   into it. The long pole: data collection, gating the Monte Carlo entirely,
   and able to run in parallel with all the engineering below.
1. ~~**Regression test pinning `basic_test`**~~ — **done**, `test_regression.py`,
   16 checks.
2. ~~**Validate the input tables on load**~~ — **done**, `src/validate_inputs.py`.
3. ~~**Fix the engine divergences**~~ — **done**, all seven (DEFECTS.md §2).
4. **Add the mass balance assertion on load**, once the table has loss flows.
   `02_check_inputs.py` already computes everything it needs; this is
   promoting a report into a hard failure. Blocked on question 1.
5. ~~**Restructure for Monte Carlo**~~ — **done 2026-08-20**. `src/sampling.py`
   draws the coefficients, `src/monte_carlo.py` solves every draw at once,
   `04_run_monte_carlo.py` runs it and `src/plot_monte_carlo.py` draws five
   figures. 24 + 7 checks in `test_sampling.py` and `test_monte_carlo.py`.
6. **Feed it the real inflow draws.** The engine already takes inflows as a
   `(rows, draws)` array — it is handed a repeated column today only because
   the upstream per-element arrays do not exist yet (§8). That is a change of
   input, not of engine.
7. **Decide whether composition is uncertain.** Same shape of change:
   `Structure.evaluate` already accepts `composition_values` as an array.

Step 5 is now unblocked on the engineering side: the deterministic answer is
pinned, the engines agree, and the semantics are written down. What it still
needs from step 0 is a real TC table to sample from.

## 6. Three things worth knowing before touching the Monte Carlo

- **Seed from `(draw index, TC identity)`**, not from a running generator.
  Comparing scenarios wants the same draw in each, so the difference reflects
  the scenario rather than noise. Seeding this way gives that across separate
  runs, and survives chunking, reordering and reruns.
- **A negative residual is a diagnostic, not a failure.** If sampled recovery
  fractions sum past 1, count and report those draws; do not silently clip
  (DESIGN_monte_carlo.md §4).
- **The year axes do not line up.** `bev_draws` is 96 years from 1975, the
  electronics composition draws are 51 from 2020. Align on year *value*, never
  on position — and read the real draws rather than re-deriving them, which is
  a mistake `04_02`'s own header records having made three times.

## 7. Picking up on the other Mac

The project folder syncs through iCloud, so the code is already there. Do these
in order.

**1. Let iCloud finish syncing** before anything else. A half-synced repo looks
like a corrupt one.

**2. Pull.** Some files were renamed on 2026-08-17 — `run_model.py`,
`plot_flows.py` and `check_mass_balance.py` moved into `src/`, and the numbered
stages replaced them. Any Positron tab open on an old path will point at
nothing.

```bash
git pull
```

**3. Reinstall the requirements.** matplotlib is new since that machine last
ran anything, and without it every figure fails.

```bash
./.venv/bin/pip install -r requirements.txt
```

If the venv there was built at a different path — for instance before the
project moved into iCloud — it will be broken in the way SETUP.md §4 describes.
Rebuild it:

```bash
rm -rf .venv && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

**4. Check the environment is right.**

```bash
./.venv/bin/python tools/compare_engines.py data_folder/reference/basic_test   # Engines agree, ~1e-15
./.venv/bin/python test_regression.py                          # 16 of 16 passed
```

If both pass, that machine is in the same state as this one.

**5. Run the model.**

```bash
./.venv/bin/python 03_run_model.py
```

That solves the case in the settings and writes every figure to `figures/`.

**6. To change anything, edit `src/params_schema.py`** — which case, which
years, which scenario, which engine, which figure formats. Every value has a
plain comment above it. Then:

```bash
./.venv/bin/python 00_parameters.py
```

which rewrites `params.xlsx` and PARAMETER_REFERENCE.md. **Both are reports.**
Editing either changes nothing; the settings file is the only input.

**7. Read yourself back in**, in this order:

- `figures/template_structure.png` from step 5 — every flow, every process, and
  the transfer coefficients behind each arrow on one page. The fastest way back
  into how the model is wired.
- [MODEL_MECHANICS.md](MODEL_MECHANICS.md) §1 and §4 — the nesting rule, and
  what a TC can meaningfully sum to. Both are counter-intuitive and both were
  got wrong at least once.
- [DEFECTS.md](DEFECTS.md) §2 — closed, but the reasoning behind §2.3 and §2.5
  is the part that matters, because those were decisions rather than fixes.
- [DESIGN_tc_table.md](DESIGN_tc_table.md) — where the work actually resumes.

### The one thing waiting on you, not on the code

**The flow network.** Which processes exist and what each produces. Everything
downstream is blocked on it, and it is entirely domain knowledge — no amount of
engineering here substitutes for it.

Give it as a plain list, and the TC table skeleton can be generated from it with
the coefficients left blank to fill in:

| From | To | Process | Keyed at which layer |
|---|---|---|---|
| collected | dismantled | dismantling | component |
| collected | loss_dismantling | dismantling | component |
| … | … | … | … |

Two rules constrain the answer, both from DESIGN_tc_table.md: one loss flow per
process rather than a shared sink, and each process keyed at the layer where
its yield actually differs — dismantling separates components, refining and
shredding differ per element.

### Known unfinished

- **No uncertainty of any kind.** `DQS` and `CV` are declared in the input
  dtypes and read by nothing. This is the main body of work.
- **The structure figure is a first cut.** If it is still hard to follow, that
  is the figure to iterate on, not the Sankeys.
- **`Value` is `object` dtype** in both engines' returned frames
  (DEFECTS.md §3.4). Harmless today, blocking for vectorisation — fix it before
  the Monte Carlo restructuring, not during.

## 8. Upstream context

Inflows come from `04_02` in the separate pipeline: per-element inflow, outflow
and collected, **in kt**, at 200,000 draws, resolved by domain. The real draws
are persisted as `(draws, years)` `.npy` arrays — `bev_draws/<scenario>/` —
and are meant to be read rather than re-derived.

### Where the path is set

`data.upstream_root` and `data.inflow_draws_dir` in `src/params_schema.py`,
joined with `run.scenario`. To see the resolved path and whether it is actually
there:

```bash
./.venv/bin/python 00_parameters.py --check
```

### Data availability, checked 2026-08-20 — this is the blocker

| What | Where | State |
|---|---|---|
| Electronics composition draws | `RAWCLICVehicleElectronics/Composition/draws` | **live**, 15 arrays, 584 MB |
| Element fraction draws | `RAWCLICVehicleElectronics/Composition/element_draws` | **live**, 24 arrays + labels, 316 MB |
| Fleet draws `bev_draws/BAU` | `RAWCLICStockAndFlow/data/processed` | **in the iCloud Trash**, 2.6 GB, 37 arrays |
| `04_02_*` outputs | `RAWCLICStockAndFlow/data/processed/intermediate` | **absent** — intermediate stops at `03_` |

The electronics half is intact. The fleet half — `BEV_<segment>_{inflow,outflow,
collected}.npy`, `(200000, 96)` float32, millions of vehicles — exists only in
`~/Library/Mobile Documents/.Trash/processed/bev_draws`. Recoverable, but the
Trash is not a storage location.

**And even with both halves restored, there is still nothing for this model to
read.** 04_02 multiplies them draw by draw and then persists only
`04_02_bev_electronics_summary.pkl` plus figures — the per-element, per-draw
arrays are computed and discarded. Its `OUTPUTS` header confirms it.

So the work is upstream first: 04_02 gains a step that writes the element-level
draws it already has in memory. Doing that multiplication here instead would
duplicate its segment splitting (`split_pair_by_tilt`) and its draw pairing, and
that pipeline's own header records three occasions where a stage rebuilt another
stage's numbers and diverged silently.

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
