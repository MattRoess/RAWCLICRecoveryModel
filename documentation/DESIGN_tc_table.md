# Design: building the TC table

**Status: proposal.** The real transfer coefficient table does not exist yet
(confirmed 2026-08-14 — nothing on this machine, and `basic_test` is mock
data). That is the good case: the constraints can be designed in rather than
retrofitted.

A worked example of everything below is in `data_folder/reference/template`. It runs
through the existing engines unchanged, and passes every check.

## 1. The principle: make sum-to-1 true by construction

"Everything sums to 1" cannot be *discovered* in a TC table. It has to be
*built* in, and there is exactly one thing that makes it possible:

> **Every process gets explicit loss flows.** A resource's coefficients then
> cover all its destinations — recovered *and* lost — and total exactly 1 by
> construction.

Without loss flows, the coefficients describe only the recovered fraction, the
rest vanishes unrecorded, and no sum-to-1 rule can be enforced without
inventing recovery. With them, mass balance becomes a property you can assert
on load and check on every Monte Carlo draw.

The contrast, from `01_check_inputs.py`:

| | `basic_test` (mock, no loss flows) | `template` (proposed schema) |
|---|---|---|
| Resources totalling exactly 1 | **0 of 24** | **10 of 10** |
| Range of totals | [0, 0.66] | [1, 1] |
| Unaccounted mass | 78% average, unrecorded | none |

## 2. Schema

Keep the three existing files and the columns the user guide already defines.
Add three things to `TCs.csv`:

| Column | Status | Purpose |
|---|---|---|
| `value` | existing | The **mode** of the triangular. Unchanged meaning for the deterministic model. |
| `value_min` | **new** | Lower bound of the triangular. |
| `value_max` | **new** | Upper bound of the triangular. |
| `process` | exists, currently discarded | Groups TCs for correlated sampling. |
| `technology` | exists, currently discarded | Finer grouping for correlated sampling. |

**This is backward compatible, and that is verified.** Both engines select only
the columns in `InputDataFormat.TCs_columns`, so the extra columns are ignored:
`data_folder/reference/template` solves correctly today with no code change. `value`
remains the deterministic point estimate, so the existing model keeps working
while the data is collected once.

`process` and `technology` are already in `basic_test`'s TC file and already
thrown away on load. They are the natural keys for common random numbers — two
coefficients governed by the same shredder should move together across draws
rather than independently.

## 3. The four rules a TC table must obey

`01_check_inputs.py` checks all four.

### R1 — Each resource's coefficients total exactly 1

The total is taken **per transferred resource, over the output flows it
reaches** — where a resource is the pair `(Input_layer_key, TC_target_key)`.
Not by input key, and not across different target keys; those group unrelated
things (MODEL_MECHANICS.md §4).

A total above 1 creates mass and is always an error. Below 1 means mass is
leaving unrecorded, which R1 exists to eliminate.

### R2 — Every TC writing into one output flow must target the same layer

This one is subtle and it bites hard. A TC targeting a **coarse** layer carries
the resource's entire subtree with it, producing rows at every depth. One
targeting a **fine** layer produces rows at that depth only. Route both into
the same output flow and the deep rows exceed their own parents.

Measured, using a single shared `F9_loss` fed by a component-level TC and two
element-level ones:

```
F9_loss / BEV / Harness / CuAlloy          = 30.00   (parent)
F9_loss / BEV / Harness / CuAlloy / Cu+Au  = 112.32  (children)
NESTING BROKEN by 82.32 Mg
```

The flow becomes uninterpretable: no aggregation over it is correct. Splitting
into one loss flow per process fixed it exactly (worst discrepancy 5.7e-14).

**Practical consequence: one loss flow per process, not one shared sink.** That
is also better practice independently — it makes losses auditable per process
rather than pooled into a single number.

Note that several *processes* may write into the same output flow without any
problem, so long as they target the same layer. In the template, refining and
shredding both feed `F6_refined` at the element layer, and nesting holds.

### R3 — `0 <= value_min <= value <= value_max <= 1`

Asymmetry is expected and is the point — the mode sits off-centre. In the
template, 16 of 22 rows are asymmetric.

### R4 — No resource routed to the same output flow twice

Two TC rows for one resource into one destination are resolved differently by
the two engines (DEFECTS.md §2.3). Until that semantic is settled, treat it as
an error rather than relying on either behaviour.

## 4. Which layer to put a TC on

Put it at the layer where the yield actually differs. This is the whole reason
the model exists:

- **Dismantling** separates *components* — a harness comes out whole or it
  doesn't. Key those TCs at the component layer. The element detail rides along
  automatically, because a coarse-layer TC scales the whole subtree.
- **Refining and shredding** have yields that differ per *element* — copper
  from a harness behaves nothing like gold on a board. Key those at the element
  layer.

Do not key a TC finer than the physics justifies: it multiplies the rows to
collect data for, without adding information.

## 5. Consequence for the Monte Carlo — this reverses an earlier finding

On `basic_test`, 22 of 24 resources reached a single destination, so the
simplex sampling machinery looked like a corner case
(DESIGN_monte_carlo.md §3).

**Building the table this way inverts that.** Every resource acquires at least
one loss destination, so every resource becomes a split set: 10 of 10 in the
template. The joint-constraint handling in DESIGN_monte_carlo.md §4 therefore
becomes the *core* of the sampling design, not an exception.

That is a real cost of the approach, and it is worth paying — mass balance you
can assert beats marginals you can sample independently. But it should be a
deliberate choice, not a surprise discovered during implementation.

It also settles which sampling scheme to use. With loss as an explicit
destination, **sample the recovery coefficients from their triangulars and
derive loss as `1 - Σ`** — option (b) in DESIGN_monte_carlo.md §4. Loss is
physically the residual and is the term with the weakest independent data, so
this is the correct causal direction and it leaves the coefficients you have
data for undistorted. A negative residual then means the sampled recovery
fractions exceeded 1, which is a data problem worth reporting rather than
silently clipping.

One consequence to be aware of: if loss is derived, then **the `value_min` and
`value_max` given for a loss row are not independent inputs** — they are
implied by the others. Keep them in the table as a cross-check (does the
derived distribution land inside the range an expert would have stated?), but
do not sample them.

## 6. Open, for whoever owns the method

1. Is the flow network settled — which processes exist, and what each one's
   output flows are? Everything else follows from that.
2. Are the triangular bounds elicited per technology, or per coefficient? This
   determines how much data collection R3 actually implies.
3. Should composition carry uncertainty too? It already sums to 1 exactly, so
   it is a genuine simplex and the same machinery would apply.
