# Design: Monte Carlo recovery model

**Status: not built.** This is the design problem as understood on 2026-08-14,
with the measurements that constrain it. Written so the design decisions are
made deliberately rather than discovered halfway through an implementation.

## 1. Requirements

- Uncertainty on transfer coefficients, expressed as **asymmetric triangular**
  ranges (min, mode, max — with the mode off-centre).
- TCs resolved at the **component and element** layers, so that recovery yield
  can differ per element rather than being one rate per vehicle.
- Every set of transfer coefficients **must sum to 1**.
- Monte Carlo, at the same draw count as the upstream pipeline (200,000).

## 2. Architecture: vectorise over draws, do not loop

### The budget rules out a loop

Measured on a mid-sized synthetic case (10 products, 30 components,
15 materials, 40 elements → 734,110 result rows):

```
read_input_data   0.063 s   (structure — depends only on the input files)
solve_model       0.525 s   (numbers — depends on the sampled values)
```

200,000 sequential draws of `solve_model` = **29.2 hours**, for a single
year/scenario/location cell. A naive `for draw in range(200_000)` loop is not
viable.

### What makes vectorisation possible

Every operation in `solve_model` is a join, an elementwise multiply, or a
groupby-sum. Crucially, **the graph topology and all join keys are identical
across draws** — only the numbers change. So:

> Compute the join structure **once**. Carry `Value` as an
> `(n_rows x n_draws)` array instead of a scalar. Replace each merge with a
> precomputed integer index, each multiply with a broadcast, each groupby-sum
> with `np.add.at` or a sparse matrix product.

This is a restructuring of `RecoveryModelOptimized`, not a rewrite of the
method. Use `RecoveryModelOptimized` as the base: it is 11x faster than the LA
engine at realistic sizes and scales with populated rows rather than with the
product of layer cardinalities (see MODEL_MECHANICS.md §5).

### Memory forces chunking over draws

`734,110 rows x 200,000 draws x 8 bytes = 1.17 TB`. Even a 10,000-row
reporting set is 16 GB at full draw width.

Process draws in blocks (a few thousand at a time) and **reduce within each
block** — accumulate mean, variance and the quantiles you need, keeping full
per-draw traces only for a named, small subset of reporting rows. Do not
materialise the full array.

### Three things in the current code that will break vectorisation

1. **Zero-row dropping.** `Value != 0` is applied both mid-pipeline
   (`recovery_model_optimized.py:298`) and to the final output (`:172`). Each
   draw would produce a *different set of rows*, which cannot be stacked. The
   row index must be established once, from the structure, and held fixed —
   with zeros kept as zeros.

2. **Quadratic concatenation.** `full_solution = pd.concat([full_solution,
   solution])` inside the year/scenario/location loop (`:166`). Fine for four
   cells, quadratic for four cells x 200,000 draws. Collect into a list and
   concatenate once, or write per-chunk.

3. **`Value` is `object` dtype, not `float64`** (DEFECTS.md §3.4). An object
   column of boxed Python floats defeats every numpy fast path, so it must be
   fixed before any vectorisation work or the restructuring will be silently
   slow. The same root cause — seeding a frame with
   `pd.DataFrame(columns=[...])` — produces both this and problem 2.

## 3. How much does "everything sums to 1" actually constrain?

Less than it first appears. Establishing this properly changes the design.

### What can sum to anything

A TC is a **retention fraction for one resource into one destination flow**
(MODEL_MECHANICS.md §4). The only meaningful total is: one resource, summed
over the output flows it reaches. Summing by input key, or across different
target keys, adds unrelated resources together and produces a number that is
not a quantity.

### What that total looks like in practice

From `02_check_mass_balance.py` on `basic_test`:

| | count |
|---|---|
| Distinct resources transferred | 24 |
| Reaching exactly **one** output flow | **22** |
| Genuinely **splitting** across several | **2** |
| Totalling exactly 1 | 0 |
| Totalling above 1 (would create mass) | 0 |

So a sum-to-1 rule has almost nothing to bind on here. 22 of the 24 resources
have a single destination, where the coefficient is just a retention fraction
and the only constraint is `0 <= TC <= 1`. The two genuine splits total 0.08
and 0.66 — both well under 1, the rest being loss.

### What this means for the design

**The simplex problem is the exception, not the rule.** Most TCs can be sampled
as independent triangulars on [0, 1] with no normalisation, no marginal
distortion, and no joint machinery at all. Only split sets need special
handling, and only where a resource reaches more than one output flow.

This is a significant simplification over treating every process as a simplex.

**But it is an empirical question about your data, not a settled fact.**
`basic_test` is mock data with a mostly linear flow network. A real recovery
network is full of separation steps — a shredder splitting into ferrous,
non-ferrous and ASR — where one input resource genuinely does divide between
several output flows. In that data, split sets could be the majority.

> **Run `02_check_mass_balance.py` against the real TC table before designing the
> constraint handling.** The ratio of split sets to single-destination sets
> determines how much of §4 you actually need.

**Update, 2026-08-14: the real TC table does not exist yet.** So this is a
design choice, not a measurement. If it is built as DESIGN_tc_table.md
proposes — with explicit per-process loss flows, so mass balance holds by
construction — then *every* resource becomes a split set and §4 becomes the
core of the sampling design rather than a corner case. That is the deliberate
trade: mass balance you can assert, in exchange for a joint constraint
everywhere.

### Where splits do exist, sum-to-1 still needs loss flows

For a split set, enforcing "sums to 1" is only correct if the set is complete.
In `basic_test` the two splits total 0.08 and 0.66; normalising them as they
stand would inflate those routes by 12x and 1.5x. **Enforcing sum-to-1 on an
incomplete set does not conserve mass, it invents recovery.**

So where the constraint is to be applied, the prerequisite is still a data
change: those processes need **explicit residual/loss output flows**, so that
the set being constrained is complete — recovered fractions *plus* losses to
slag, dust, landfill, export and unrecovered remainder.

The weaker constraint applies everywhere and is worth enforcing immediately,
independent of any of the above:

> **A resource's total over its output flows must never exceed 1.** Above 1
> creates mass. It holds for singletons and split sets alike, it needs no new
> data, and it should be a hard validation on load and a per-draw check in the
> Monte Carlo.

Composition already closes to 1.0 exactly at all three depths, so if it is
sampled too it is a genuine simplex — and there the machinery in §4 does apply.

## 4. Sampling asymmetric triangulars on a simplex

Sampling a single asymmetric triangular is easy and fully vectorisable by
inverse CDF. For parameters `a <= c <= b` (min, mode, max) and `U ~ Uniform(0,1)`:

```
F_c = (c - a) / (b - a)
x = a + sqrt(U * (b - a) * (c - a))              where U <  F_c
x = b - sqrt((1 - U) * (b - a) * (b - c))        where U >= F_c
```

**For a single-destination resource that is the whole job** — sample the
triangular, done. No joint constraint exists, because there is no set to
constrain. Per §3 that covers 22 of 24 resources in `basic_test`.

The rest of this section applies only to **split sets**, where one resource
reaches several output flows and those k coefficients must sum to 1. Sampling
k independent triangulars does not give a sum of 1. Three options, none free:

| Approach | Constraint | Marginals | Problem |
|---|---|---|---|
| **(a) Normalise** — sample k, divide by their sum | exact | distorted | Every marginal shifts off its specified mode. Distortion grows with the spread of the sum and with k. |
| **(b) Residual** — sample k−1, set the last to `1 − Σ` | exact | k−1 exact | The residual can go negative, and which one is the residual is an arbitrary choice that changes results. |
| **(c) Dirichlet** — fit a Dirichlet or generalised Dirichlet to the modes | exact, native | replaced | Marginals become Beta. You have discarded the triangular you were asked to use. |

**Recommendation: (b), once §3 is done — and it stops being a hack.**

If every process has an explicit loss flow, then loss is *physically* the
residual: it is whatever was not recovered, and it is precisely the term for
which independent data is weakest. Sampling the recovery TCs from their
triangulars and deriving loss as `1 − Σ` is then the correct causal direction,
and it leaves the marginals of the coefficients you actually have data for
undistorted.

A negative residual then becomes a **diagnostic, not a failure**: it means the
sampled recovery fractions sum to more than 1, which is physically impossible
and indicates the input ranges are wrong. Count and report those draws; do not
silently clip them.

Where a set genuinely has no natural residual, fall back to (a) — and **report
the realised marginals against the specified triangular** (mean, mode, 2.5/97.5
percentiles) so the distortion is visible and documented rather than hidden.

## 5. What should vary together

Independent sampling of every TC is almost certainly wrong, and this needs an
explicit decision.

`TCs.csv` already carries **`process` and `technology` columns that the model
reads and discards** — they are not in `InputDataFormat.TCs_columns`, so they
are dropped on load. These are the natural grouping keys for correlated
sampling: two TCs governed by the same shredding technology should move
together across draws, via common random numbers per technology group.

Also to decide:

- **Composition uncertainty.** Is composition uncertain too, or fixed? If
  uncertain, it needs the same simplex treatment (it already sums to 1).
- **Draw alignment with upstream.** Inflows arrive from `04_02` as 200,000
  draws. Draw *i* of the inflow must be used with draw *i* of the TCs — a
  shared draw index, not independent resampling — or the uncertainty will not
  compose correctly.

## 6. Open decisions

These need answers before implementation, in roughly this order:

0. **How many resources in the real TC table actually split?** Run
   `02_check_mass_balance.py` against it. This is a five-minute empirical question
   and it determines how much of §4 is needed at all — in `basic_test` the
   answer is 2 of 24, which would make the simplex machinery a corner case
   rather than the core of the design.
1. Whether losses/residuals get explicit flows, for those sets that do split
   (§3). Everything about the constraint depends on this.
2. Which TCs are correlated, keyed on `process` / `technology` (§5).
3. Whether composition is uncertain as well as TCs.
4. Which rows need full per-draw traces retained, versus summary statistics
   only — this sets the memory budget (§2).
5. How overlapping TC specificity should resolve (DEFECTS.md §2.3) — this is a
   method decision, and it must be settled before element-layer TCs are layered
   on top of component-layer ones, which is exactly what the requirements ask
   for.
