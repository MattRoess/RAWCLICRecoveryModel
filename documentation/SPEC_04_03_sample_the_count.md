# Specification — `04_03` must sample the vehicle count

**For `RAWCLICStockAndFlow`, not this repository.** Written here because this is
where the defect was found and measured; see `DEFECTS.md` 3.25 and
`FAILURES.md` 27–28.

**Status: IMPLEMENTED 2026-09-30**, `RAWCLICStockAndFlow` commit `8e4b4e3`.
Stage `04_03` has not been re-run, so the arrays on disk are still the old ones.

⚠️ **AND IT WAS ALREADY KNOWN.** This was proved in that repository on
2026-09-22 — `code/proof_0403_vehicle_draws.py`, with the finding written up in
its `documentation/HANDOVER.md`. This specification rediscovered it. Read that
handover first; it is the primary record and it settles things this document
originally got wrong.

---

## 1. The defect, in one line

`04_03` multiplies a **deterministic** vehicle count by a sampled composition,
so the exported draws carry composition uncertainty only. The Monte Carlo is
incomplete, not merely imprecise.

`src/traction_draws.py`, `coefficients()`:

```python
vehicles = float(amount) * 1e6                       # scalar, off the tracker
row[slot] += vehicles * share * scale_cache[scale_key]
```

There is no draw index on `amount` anywhere in that function, and
`data/processed/bev_draws/` is never opened by that stage. `04_02` does open
it, for the same fleet, and pairs draw *i* of the fleet with draw *i* of the
electronics.

**The arithmetic that proves it.** Mass = count × composition. If the count
alone has a CV of 12.1%, the product cannot have a CV of 2.5%. A product of two
uncertain quantities cannot be more certain than either of them.

## 2. How wrong it is

Measured on the real export, `traction_recovery_draws/mix/collected`, copper,
200,000 draws, against the count CV from `bev_draws/BAU`:

| year | composition (has) | count (missing) | combined (should be) | too narrow by |
|---|---|---|---|---|
| 2020 | 3.29% | 21.43% | 21.68% | 6.6× |
| 2025 | 3.13% | 13.73% | 14.08% | 4.5× |
| 2030 | 2.85% | 11.86% | 12.20% | 4.3× |
| 2035 | 2.72% | 11.82% | 12.13% | 4.5× |
| 2040 | 2.63% | 10.56% | 10.88% | 4.1× |
| 2045 | 2.57% | 8.57% | 8.95% | 3.5× |
| 2050 | 2.52% | 6.94% | 7.38% | 2.9× |
| 2055 | 2.49% | 7.25% | 7.67% | 3.1× |
| 2060 | 2.48% | 9.33% | 9.65% | 3.9× |
| 2065 | 2.47% | 11.36% | 11.63% | 4.7× |
| 2070 | 2.47% | 12.23% | 12.48% | 5.0× |

The count dominates in every single year. Neodymium is the least bad case
because its own composition spread is larger — 5.50% at 2070, combining to
13.41% — and even there the count is the bigger term.

**The spread is wrong, and the means are too.** ⚠️ This document originally
said means were unaffected and must not move. That was wrong, and it had
already been settled here on 2026-09-22:

> Outflow is a nonlinear function of the drawn lifetime, so
> `E[outflow(λ)] ≠ outflow(E[λ])`. The tracker is one deterministic run at the
> point lifetime and therefore CANNOT equal the Monte Carlo mean. The draws are
> the correct quantity; the tracker's collected is **biased high by 2–6%**.

So the drawn count REPLACES the tracker's, and the medians move: `inflow`
−0.5%, `collected` −6.9% at 2040 and −2.7% at 2060. Holding the means fixed
would preserve a measured bias and call it an uncertainty fix.

## 3. What must NOT be done

**Do not rescale the finished export** by a total-count ratio
`count_draw / count_mean`. It injects the right aggregate spread through the
wrong mix: segments carry different motors, so scaling every segment by one
number is a different distribution from sampling each segment's own count.
This was proposed and rejected — correctly — on 2026-09-30.

**Do not treat the means disagreeing as a blocker.** The tracker and
`bev_draws` disagree on `collected` before 2060 (83% at 2035, 0.08% by 2070).
That is a real and separate problem, recorded in `DEFECTS.md` 3.25. It has no
bearing on this change.

## 4. The resolutions available

```
TRACKER   counts at (region, drive, flow, scrap_year, cohort_year, segment)
          5 region/drive keys · 12 segments · 60 cohorts (2011–2070) · deterministic

BEV_DRAWS (draws, years) per (segment, flow)
          12 segments (A–F, JA–JF) · 3 flows · 96 years (1975–2070)
          no region, no drive train, no cohort
```

Sampling must therefore happen **per segment and year**, which is the
resolution at which the count distribution exists.

## 5. The change

The sum in `coefficients()` already factorises by segment, so sampling the
count does not destroy the matrix product — it splits it into twelve:

```
result[row, draw] = Σ_segment  count[segment, flow, scrap_year, draw]
                               × Σ_files  share(cohort) · scale(cohort, voltage)
                                          · composition[file, segment, draw]
```

The inner sum is exactly what `coefficients()` builds today **with `vehicles`
removed**; the outer factor is that segment's `bev_draws` column for that flow
and scrap year.

Concretely:

1. `coefficients()` stops multiplying by `vehicles` and returns its matrix
   **per segment** — `{segment: (rows × files)}` — rather than one
   `(rows × columns)` block. `share` and `scale` stay where they are; they are
   genuinely deterministic.
2. `traction_export.export()` replaces `matrix @ draw_matrix(...)` with a sum
   over segments of `count_vector[segment] * (matrix[segment] @ draw_sub[segment])`,
   where `count_vector` is `bev_draws/<scenario>/BEV_<segment>_<flow>.npy`
   restricted to the exported years.
3. Same for `_draw_matrix_mixed`, the `mix` grade path.
4. Chunk over draws as the stage already does; twelve segment products of
   `(rows × files) @ (files × draws)` is the same order of work as one
   `(rows × columns) @ (columns × draws)`.

## 6. The residual assumption, which must be written into the code

The tracker splits each segment-year across 60 cohorts. `bev_draws` has no
cohort dimension. So **the cohort split stays deterministic** and the drawn
count scales that whole breakdown proportionally.

This is not a modelling preference — there is no cohort-level distribution on
disk to sample. Its consequence is that cohort composition is treated as known
while the segment total is not, and anyone quoting an interval should know it.
Put it in the docstring of whatever does the scaling, not in a commit message.

## 7. Two things to check while implementing

- **Draw alignment.** `04_02` states draw *i* of the fleet is draw *i* of the
  electronics. `04_03` has never opened `bev_draws`, so nothing guarantees its
  composition draws share that ordering. Either way the injected CV is right;
  the pairing only decides whether the correlation between count and
  composition is meaningful or arbitrary. Find out which, and say so.
- **Which ratio each flow takes.** The CVs differ sharply early: at 2020
  `inflow` is 0.83% and `collected` 21.43%. Each exported flow must take its
  own flow's counts, not `collected`'s for all three.

## 8. How to know it worked

1. **The medians must move, by the amounts the Jensen bias predicts:** `inflow`
   −0.3 to −0.7%, `collected` −2 to −7%. A mean that does NOT move means the
   ratio was taken against the draws' own mean instead of the tracker's, which
   preserves the bias.
2. **The 95% band must land on the 22-September proof.** Copper `inflow` 2060
   9.7% → 45.1% (proof: 44.5%); copper `collected` 2060 9.7% → 37.1% (proof:
   37.2%); magnet `inflow` 2060 11.9% → 45.5% (proof: 44.7%). **Measured, and
   it does.**
3. **Composed flows too.** The tracker has no `outflow` row, so it needs the
   sum of its parts as a denominator or a third of the arrays keep a
   deterministic count silently.
4. Then re-export, and in `RAWCLICRecoveryModel` re-run `03_tractionmotors.py`
   and `05_combine_cases.py`. Every traction interval widens; no mean should
   move by more than Monte Carlo noise.

## 9. EVERYTHING ELSE THAT IS STILL A SCALAR

⚠️ **Fixing the count does not make this stage a complete Monte Carlo.** It is
the largest missing term, not the only one. After §5 the following are still
point values, each of them a quantity nobody actually knows exactly:

| input | where | what it is | has a distribution? |
|---|---|---|---|
| motor-type share | `traction.type_shares(params, group, year)` | which share of a cohort is PMSM / IM / EESM / axial flux | no — a parameter |
| voltage-class share | `traction.voltage_shares(params, group, year)` | 400 V vs 800 V split | no — a parameter |
| the two combined | `traction.joint_shares()` | product of the above | no, **and it assumes independence**, which its own docstring flags as an assumption that may be wrong |
| year × voltage factor | `DrawLibrary.scale(file, year, voltage)` | design improvement over time, per file | no — a lookup table, explicitly "the deterministic year x voltage factor" |
| torque per segment | `composition['torque_nm'].first()` | one torque stands for a whole size class | no — a single value per segment, and `.first()` silently discards any disagreement within the group |
| cohort split | the tracker | how a segment-year's vehicles divide across 60 cohorts | no, and §6 |

**Two of these are more than missing spread.**

`joint_shares` multiplies two shares as independent and says so:

> ⚠️ TREATED AS INDEPENDENT, AND THAT IS AN ASSUMPTION. Nothing says an 800 V
> car is more or less likely to be axial flux, so the two are multiplied — but
> they plausibly correlate, since both follow the premium end of the market.

If they correlate, the joint distribution is wrong in shape, not only in width,
and no amount of sampling the marginals fixes that.

`segment_torque` takes `.first()` of a group. If a segment's composition rows
disagree on torque, one value wins silently and the rest are discarded. That
should be checked before it is sampled — a spread cannot be put on a number
whose central value was chosen by row order.

**So "all of it must be Monte Carlo" means, in order of size:**

1. the vehicle count — §5, measured at 3–7× the reported spread;
2. the torque per segment — check `.first()` first, then a distribution;
3. the motor-type and voltage shares, jointly, with their correlation
   addressed rather than assumed away;
4. the year × voltage scale factor;
5. the cohort split, which needs a distribution to exist upstream before it
   can be sampled at all.

**None of 2–5 is quantified.** Unlike the count, there is no distribution on
disk to measure them against, so this specification cannot say how much they
are worth — only that the intervals after §5 will still be too narrow by an
unknown amount, and that reporting them as complete would repeat the error
this document exists for.

## 10. What is wrong downstream until this is done

Every interval the traction study reports: `account_<r>`, `losses_<r>`,
`fleet_<r>`, the recovery rate, the Sankey's 95% labels, `spread`,
`pdf_<r>`, and the traction share of every figure `05_combine_cases.py` draws.

And `05` is internally inconsistent: it adds a wiring contribution that carries
fleet uncertainty to a traction contribution that does not, so the combined
band is too narrow by an amount that depends on the mix and is stated nowhere.
