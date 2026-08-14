# Model mechanics

How the model computes a result. Reconstructed by reading the code and
verifying each claim against `data_folder/basic_test`; none of this was
previously written down. The input *schema* is documented in
`../doc/User guide.docx` — this document is about behaviour.

## 1. The data model: rows are nested, not parallel

Every row of both input and output is identified by a flow plus up to four
layer keys:

```
Stock/Flow ID, Layer 1, Layer 2, Layer 3, Layer 4, Value
        F1,        P1,      C1,      M1,      E1,  91.0
```

Layers are nested containers — element inside material inside component inside
product. A row's *depth* is how many layer columns are populated. The critical
consequence:

> **A deeper row is a sub-quantity of its shallower parent, not an addition to
> it.** `F1/P1/C1/M1` (130 t) is *part of* `F1/P1/C1` (250 t), which is *part
> of* `F1/P1` (1000 t).

So summing the `Value` column over a solution is meaningless — it counts the
same mass up to four times. Any aggregate must first select a single depth.
This is the single easiest way to misread the model's output.

Verified on `basic_test`: wherever a parent row exists, its children sum to it
exactly (worst discrepancy 5.7e-14 across 70 parent groups).

## 2. Flows are truncated at the layer their TC targets

An output flow only contains rows at or below the depth of the TC that created
it. In `basic_test`:

| Flow | Created by a TC targeting | Shallowest rows present |
|---|---|---|
| F1 (inflow) | — | product |
| F2, F3, F4, F6 | component | component |
| F5, F7 | material | material |
| F8 | element | element |

F8 has **only** element-depth rows — there is no aggregate row for it. So
"total mass in F8" is the sum over its element rows, whereas the same sum over
F2 would quadruple-count. Aggregation rules therefore differ per flow, which is
a trap for any reporting code written on top.

This is deliberate: once a product has been dismantled, it no longer exists as
a product. But it means the output is not uniform, and consumers must inspect
depth rather than assume it.

## 3. How a result is built

### Step 1 — expand the inflow by composition

`create_initial_flows` takes the inflows (given only at Layer 1) and multiplies
them out to all four depths using `composition.csv`, one depth at a time:
product → component → material → element. Each step multiplies the parent's
value by the composition share.

Composition shares must sum to 1 within each parent for mass to be conserved.
Nothing enforces this. In `basic_test` they do, exactly, at all three depths.

### Step 2 — order the processes

`get_process_sequence_from_tcs` builds a directed graph of
`Input_FlowID → Output_FlowID` and topologically sorts it, so each process can
be solved once, in order. **Cycles raise `ValueError`** — the optimized engine
cannot represent feedback loops or recycling back into an earlier flow.

### Step 3 — apply each process's TCs

For each process, `solve_process` loops over all 16 ordered pairs of
(input layer, target layer) and applies any TCs defined for that pair. The
mechanism is a dataframe join on the layer key(s), then a multiplication.

The important behaviour is what a TC at a *coarse* layer does to *fine* rows:

> A TC keyed on `Layer 1 → Layer 2` is joined on those two columns only, so it
> multiplies **every row matching that (product, component) pair — including
> all of its material and element descendants — by the same factor.**

This is what keeps the nesting invariant intact through the whole pipeline: a
subtree is scaled uniformly, so children still sum to their parent afterwards.
It is also why element-specific recovery cannot be expressed with a
component-level TC. Getting different yields for copper in a harness versus
gold on a board requires TCs keyed at the element layer.

### Step 4 — aggregate

Outflows from all 16 layer-pair combinations are concatenated and summed by
`groupby`. Rows with `Value == 0` are dropped, both mid-pipeline and in the
final output.

> **Note for the Monte Carlo work:** dropping zero rows means each draw would
> produce a *different set of rows*, which cannot be stacked into an array.
> See DESIGN_monte_carlo.md.

## 4. Mass is not conserved, and nothing checks it

The TCs leaving a flow are not required to sum to anything. In `basic_test`
they sum to:

| Flow / key | Sum of outgoing TCs |
|---|---|
| F1 / P1 | 0.41 |
| F1 / P2 | 0.74 |
| F2 / C1 | 0.71 |
| F2 / C2 | 0.80 |
| F3 / C2 | 0.60 |
| F3 / C3 | 0.66 |
| F4 / C2 | 0.77 |
| F5 / M1 | 0.18 |
| F5 / M2 | 0.06 |
| F7 / M1 | 0.14 |
| F7 / M2 | 0.19 |

The remainder is not routed to a loss or residual flow. It simply stops
existing, with no record and no warning. Composition, by contrast, closes to
1.0 exactly. The discipline exists on one input and not the other.

This matters directly for the planned "everything sums to 1" requirement —
see DESIGN_monte_carlo.md §3.

## 5. The two engines

Both produce identical results on `basic_test` (largest difference 8.9e-16)
but they are *not* two implementations of one specification. See DEFECTS.md
§2 for where they disagree.

### `RecoveryModelOptimized` (default)

Sequential dataframe joins, one process at a time, in topological order.
Cost scales with the number of *populated* rows.

### `RecoveryModelLA`

Encodes the entire system as one sparse linear system and solves
`(I − TC − Composition) x = inflows` — a Leontief-style inverse. Because it
inverts rather than walks the graph, it **supports feedback loops**, which the
optimized engine cannot.

Its cost is governed by the state space:

```
size = n_flows x (n_products+1) x (n_components+1) x (n_materials+1) x (n_elements+1)
```

This is a dense enumeration of every possible combination, whether populated or
not. Measured growth:

| products, components, materials, elements | LA state size | optimized | LA |
|---|---|---|---|
| 5, 8, 5, 12 | 21,168 | 0.09 s | 0.25 s |
| 6, 12, 8, 20 | 80,080 | 0.16 s | 1.12 s |
| 8, 20, 10, 30 | 290,304 | 0.49 s | 4.18 s |
| 10, 30, 15, 40 | 973,896 | 1.64 s | 17.92 s |

Both returned identical row counts at every size. The optimized engine is
11x faster at the largest and scaling far better, which is why it is the
basis for the Monte Carlo work. The LA engine's value is as an independent
oracle on small cases — that two people implemented this twice is an asset,
and `compare_engines.py` exists to exploit it.
