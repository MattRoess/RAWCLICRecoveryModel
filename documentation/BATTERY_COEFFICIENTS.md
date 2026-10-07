# Battery transfer coefficients, by process family

**Source.** Maisel, Tippner, Mainuddin, Yamamoto & Iattoni, *"Quantifying
transfer coefficients in battery recycling routes for material flow analysis:
current state and future scenarios"* —
`documentation/BatteryStudy/1-s2.0-S0956053X2600543X-main.pdf` and its
supplementary workbook `…-mmc1.xlsx`, sheet `TC_data_Python`.

**Extracted by** `tools/extract_battery_tcs.py`, which reads and never writes
the study. Re-run it after any change to the workbook.

**2,746 coefficients.** Every one carries a value, an uncertainty, a
data-quality score, a year, a scenario and a reference. Nothing in this
document is typed by hand; it is all read from the sheet.

---

## 1. Three families, and why a family is not a route

| family | coefficients | targets | what is in it |
|---|---:|---:|---|
| mechanical | 1,216 | 36 | breaking and separating, fragmentation |
| hydro | 630 | 17 | leaching & solvent extraction, calcination, re-lithiation, Zn-electrowinning |
| thermal | 496 | 27 | pyrolysis, Waelz kiln, rotary furnace, vacuum distillation, pyrometallurgy |
| preparation | 404 | 4 | inspection, pack/module/cell disassembly — upstream of all three |

The paper's five **routes** are chains of these families:

```
Route 1   pyrolysis (opt) + mechanical + pyrometallurgy + hydrometallurgy
Route 2   pyrolysis (opt) + mechanical + hydrometallurgy
Route 3   mechanical ONLY
Route 4   pyrolysis (opt) + mechanical + pyrometallurgy + hydrometallurgy
Route 5   DIRECT recycling, LFP only — re-lithiation and graphite regeneration
```

⚠️ **Mechanical is not direct recycling.** Mechanical is Route 3 *and* the
pre-treatment inside Routes 1, 2 and 4. Direct recycling is Route 5 alone: it
preserves and restores the cathode and anode active material rather than
dissolving it back to elements. `processID` gives a family's position in the
chain.

### The route mixture, and how it moves

From `Structural_Decomposition` in the workbook:

| route | OBS 2024 | BAU 2050 | REC 2050 |
|---|---:|---:|---:|
| 1 | 0.041 | 0.006 | 0.006 |
| 2 | 0.100 | **0.696** | **0.851** |
| 3 | **0.799** | 0.286 | 0.118 |
| 4 | 0.059 | 0.008 | 0.008 |
| 5 | 0.001 | 0.004 | 0.012 |

Mechanical-only collapses; hydrometallurgy takes over. Direct recycling stays
near zero — it is at **TRL 4** against pyrometallurgy's **TRL 9**. The authors
warn the shares are built from announced capacity and therefore *"inherently
favour mature technologies"*, so direct recycling *"may be underestimated"* and
the distribution is *"plausible but uncertain"*.

---

## 2. The coefficients, per element and family

`min`, `median` and `max` are the span the study reports for that element in
that family **across its processes, years and scenarios** — not an uncertainty
range on one number. Each individual coefficient's own uncertainty is in
`battery_transfer_coefficients.csv`. **Data quality is 1 best, 4 worst.**

### Cathode metals

| element | family | coefficients | min | median | max | data quality | refs |
|---|---|---|---:|---:|---:|---|---:|
| `Ni` | mechanical | 54 | 0.030 | 0.500 | 0.970 | 1.0–4.0 | 3 |
| `Ni` | thermal | 70 | 0.010 | 0.990 | 1.000 | 1.0–2.5 | 2 |
| `Ni` | hydro | 102 | 0.010 | 0.912 | 1.000 | 1.0–4.0 | 2 |
| `Co` | mechanical | 54 | 0.030 | 0.500 | 0.970 | 1.0–4.0 | 3 |
| `Co` | thermal | 70 | 0.010 | 0.940 | 1.000 | 1.0–4.0 | 2 |
| `Co` | hydro | 102 | 0.010 | 0.794 | 1.000 | 1.0–4.0 | 2 |
| `Li` | mechanical | 66 | 0.013 | 0.500 | 0.987 | 1.0–4.0 | 5 |
| `Li` | thermal | 39 | 1.000 | 1.000 | 1.000 | 1.0–2.5 | 2 |
| `Li` | hydro | 84 | 0.000 | 0.500 | 1.000 | 1.0–4.0 | 4 |
| `Mn` | mechanical | 58 | 0.010 | 0.500 | 0.990 | 1.0–4.0 | 5 |
| `Mn` | thermal | 35 | 0.040 | 1.000 | 1.000 | 1.0–2.5 | 3 |
| `Mn` | hydro | 49 | 0.000 | 0.800 | 1.000 | 2.5–4.0 | 2 |

### Current collectors, casing and LFP phosphorus

| element | family | coefficients | min | median | max | data quality | refs |
|---|---|---|---:|---:|---:|---|---:|
| `Cu` | mechanical | 60 | 0.050 | 0.896 | 1.000 | 1.0–4.0 | 4 |
| `Cu` | thermal | 44 | 0.030 | 0.928 | 1.000 | 1.0–4.0 | 2 |
| `Cu` | hydro | 54 | 0.020 | 0.970 | 1.000 | 1.0–4.0 | 2 |
| `Al` | mechanical | 126 | 0.020 | 0.837 | 1.000 | 1.0–4.0 | 4 |
| `Al` | thermal | 39 | 1.000 | 1.000 | 1.000 | 1.0–2.5 | 2 |
| `Al` | hydro | 39 | 0.100 | 1.000 | 1.000 | 2.5–4.0 | 1 |
| `Fe` | mechanical | 132 | 0.013 | 0.500 | 0.987 | 1.0–4.0 | 5 |
| `Fe` | thermal | 70 | 0.355 | 0.645 | 1.000 | 1.0–2.5 | 2 |
| `Fe` | hydro | 81 | 0.040 | 0.960 | 1.000 | 1.0–4.0 | 4 |
| `P` | mechanical | 66 | 0.013 | 0.500 | 0.987 | 1.0–4.0 | 5 |
| `P` | thermal | 31 | 1.000 | 1.000 | 1.000 | 1.0–2.5 | 2 |
| `P` | hydro | 54 | 0.090 | 0.880 | 1.000 | 2.0–4.0 | 3 |

### Anode and the rest

| element | family | coefficients | min | median | max | data quality | refs |
|---|---|---|---:|---:|---:|---|---:|
| `graphite4` | mechanical | 48 | 0.013 | 0.500 | 0.987 | 1.0–4.0 | 5 |
| `graphite4` | thermal | 4 | 1.000 | 1.000 | 1.000 | 2.5–2.5 | 1 |
| `graphite4` | hydro | 26 | 0.000 | 0.350 | 0.950 | 2.0–4.0 | 3 |
| `C` | mechanical | 18 | 0.030 | 0.500 | 0.970 | 1.0–2.5 | 2 |
| `C` | thermal | 4 | 1.000 | 1.000 | 1.000 | 2.5–2.5 | 1 |
| `O` | mechanical | 66 | 0.013 | 0.500 | 0.987 | 1.0–4.0 | 5 |
| `O` | thermal | 8 | 1.000 | 1.000 | 1.000 | 2.5–2.5 | 1 |
| `O` | hydro | 12 | 0.090 | 0.500 | 0.910 | 2.0–3.5 | 2 |

**Reading these.** Thermal recovers Ni and Co almost completely (median 0.990
and 0.940) and destroys nothing of them, but sends Li, Al, P, graphite and C
to a **median of exactly 1.000** — those are transfers into slag or off-gas,
not recovery. Mechanical sits at a median of 0.500 for most elements, which is
the study's own placeholder where a split is not measured. Hydro is where Li
actually varies: 0.000 to 1.000, median 0.500, across 84 coefficients and 4
references.

---

## 3. Every process, by family


**preparation**

| process | level | coefficients |
|---|---|---:|
| EV battery inspection | ProcessLvl1 | 396 |
| EV battery pack/module/cell disassembling | ProcessLvl1 | 8 |

**mechanical**

| process | level | coefficients |
|---|---|---:|
| Breaking and separating | ProcessLvl1 | 1100 |
| LIB Recycling Routes | ProcessLvl1 | 96 |
| Mechanical processing | ProcessLvl1 | 20 |

**thermal**

| process | level | coefficients |
|---|---|---:|
| Thermal recovery processes | ProcessLvl3 | 290 |
| Pyrolisis | ProcessLvl2 | 144 |
| Pyrometallurgical process | ProcessLvl1 | 20 |
| Vacuum Distillation | ProcessLvl1 | 16 |
| Waelz kiln process | ProcessLvl1 | 16 |
| Thermal recovery (rotary furnance) | ProcessLvl1 | 10 |

**hydro**

| process | level | coefficients |
|---|---|---:|
| Hydrometallurgy (Leaching/SolventExtraction/Priciptation&Crystallization) | ProcessLvl3 | 537 |
| Re-lithiation | ProcessLvl1 | 48 |
| Hydrometallurgical processes | ProcessLvl1 | 25 |
| Calcination | ProcessLvl1 | 12 |
| Zn-electrowinning | ProcessLvl1 | 8 |

---

## 4. Provenance

### Data quality (1 best, 4 worst)

| score | coefficients | share |
|---:|---:|---:|
| 1.0 | 690 | 25.1% |
| 1.5 | 86 | 3.1% |
| 2.0 | 224 | 8.2% |
| 2.5 | 708 | 25.8% |
| 3.0 | 246 | 9.0% |
| 3.5 | 419 | 15.3% |
| 4.0 | 373 | 13.6% |

### Uncertainty as reported

| uncertainty | coefficients | share |
|---|---:|---:|
| ±15% | 950 | 34.6% |
| ±20% | 797 | 29.0% |
| ±5% | 690 | 25.1% |
| ±10% | 309 | 11.3% |

### Scenarios

| factor | coefficients |
|---|---:|
| REC | 1042 |
| BAU | 776 |
| OBS | 440 |
| BAU/REC/CIR | 210 |
| OBS/BAU/REC/CIR | 146 |
| CIR | 132 |

### Most-used references

| reference | coefficients |
|---|---:|
| Assumption, no reference | 955 |
| Various references and assumptions | 500 |
| [Hämmer and Wambach, 2024] | 481 |
| [Vaccari et al., 2024] | 448 |
| Losses calculated from reference value [Vaccari et al. 2024] | 146 |
| Losses calculated from reference value | 60 |
| [Roy et al. 2024] | 47 |
| [Lu et al. 2022] | 35 |
| [Rombach et al., 2016] | 20 |
| [Nowak et al. 2015] | 14 |
| [Wu et al., 2017] | 8 |
| [Salehi et al., 2023] | 8 |

---

## 5. ⚠️ What this data CANNOT do

**It is chemistry-blind.** In the paper's own words:

> the TCs for LIB recycling are defined for a generic LIB input stream
> **without differentiation by cathode chemistry**, except for direct recycling
> (Route 5) explicitly designed for LFP batteries. This represents an important
> limitation, since different cathode chemistries can yield systematically
> different recovery pathways.

Searched across all 2,746 rows: **`NMC`, `LFP` and `LMFP` appear zero
times.** Sodium does appear — `SIB` 99 times, and `battNaRechargeable` on 200
rows.

So the split wanted for this project — **NMC low / middle / high, LFP, LMFP,
and two sodium chemistries** — cannot come from these coefficients. Recovery
performance here is per ELEMENT. A chemistry split has to enter through
COMPOSITION: the same family coefficients applied to different element mixes,
with Route 5 the single exception that is defined per chemistry.

That is a modelling decision, not a gap to paper over, and it has not been
taken.

**Other limits worth stating.**

- `valueUpperLimit` is empty on every row; `valueLowerLimit` on all but 96. The
  uncertainty is carried as a percentage, not as a min/max pair, so a
  triangular range for this model has to be derived from `value` and
  `uncertainty%` rather than read.
- `valueType` is `singleValue` for all 2,746 rows.
- `TRL`, `Capacity`, `uncertaintyType` and `notes` are empty throughout.
- The 404 `preparation for reuse` coefficients reach only 4 targets, so reuse
  is coarse compared with the recycling families.
