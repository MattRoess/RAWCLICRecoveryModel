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

## 3. "Everything sums to 1" is a data-model change, not a sampling change

**This is the most important point in this document.**

The current TCs do not sum to 1, and are not close. Per flow and input key in
`basic_test`, the outgoing TCs sum to: 0.41, 0.74, 0.71, 0.80, 0.60, 0.66,
0.77, 0.18, 0.06, 0.14, 0.19.

The shortfall is not routed anywhere — it has no loss or residual flow, and
simply stops existing (MODEL_MECHANICS.md §4).

So the constraint cannot be applied to the data as it stands. Normalising
F1/P1's TCs to sum to 1 would multiply that recovery route by 2.4x. **Enforcing
sum-to-1 on an incomplete set does not conserve mass, it invents recovery.**

The prerequisite is therefore a schema and data change:

> Every process must gain **explicit residual/loss output flows**, so that the
> set being constrained is complete — recovered fractions *plus* losses to
> slag, dust, landfill, export, and any unrecovered remainder.

That is a data collection task and a modelling decision before it is a coding
task. Once it exists, sum-to-1 becomes both enforceable and *checkable*, and a
mass balance assertion can be added as a hard validation on load.

Composition already satisfies this — it closes to 1.0 exactly at all three
depths — so the same machinery should cover both inputs.

## 4. Sampling asymmetric triangulars on a simplex

Sampling a single asymmetric triangular is easy and fully vectorisable by
inverse CDF. For parameters `a <= c <= b` (min, mode, max) and `U ~ Uniform(0,1)`:

```
F_c = (c - a) / (b - a)
x = a + sqrt(U * (b - a) * (c - a))              where U <  F_c
x = b - sqrt((1 - U) * (b - a) * (b - c))        where U >= F_c
```

The difficulty is the **joint** constraint: the k TCs leaving one (flow, key)
must sum to 1, but k independent triangulars do not. Three options, none free:

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

1. Whether losses/residuals get explicit flows (§3). Everything else depends
   on this.
2. Which TCs are correlated, keyed on `process` / `technology` (§5).
3. Whether composition is uncertain as well as TCs.
4. Which rows need full per-draw traces retained, versus summary statistics
   only — this sets the memory budget (§2).
5. How overlapping TC specificity should resolve (DEFECTS.md §2.3) — this is a
   method decision, and it must be settled before element-layer TCs are layered
   on top of component-layer ones, which is exactly what the requirements ask
   for.
