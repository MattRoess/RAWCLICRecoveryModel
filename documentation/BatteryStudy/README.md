# The battery recycling study

**The source for `data/battery`, and — with the journal article beside it — for the
five battery cases that replace it** (`data/battery_lfp`, `_lmfp`, `_nmc_high`,
`_sodium`, `_solid_state`; see `documentation/BATTERY_ROUTES.md`). It lives here,
inside the repository, for the same reason the traction motor study does: a document
that only exists in `~/Downloads` is a document the next session cannot check a
coefficient against.

| file | what it is |
|---|---|
| `Battery_Cell_Recycling_Report_LFP_LMFP_NMC.md` | **the study**, LFP / LMFP / NMC cell recycling. Its Table 2 is the hydrometallurgical road of the `own` set |
| `Battery_Cell_Recycling_Report_LFP_LMFP_NMC.pdf` | the same, as delivered |
| `1-s2.0-S0956053X2600543X-main.pdf` | the journal article, Maisel et al., *Waste Management* 227 (2027) 115873 (open access, CC BY 4.0). **The source of the paper's numbers** in the five battery cases: the BAU and REC sets, the pyrometallurgical, direct and sodium roads, and the route shares |
| `1-s2.0-S0956053X2600543X-mmc1.xlsx` | its supplementary workbook. `tools/build_battery_cases.py` reads the route sheets `LIB_Route1 … 5 BAU\|REC` and `Structural_Decomposition` from it |

⚠️ **THE JOURNAL ARTICLE IS NOT THE SOURCE OF `data/battery`.** `1-s2.0-...` had been
sitting loose in `data/battery/` since the case was built, with nothing saying what it
was or which coefficient it supported. It was moved here on 2026-09-29 after being
mistaken, by me, for the source document of that case; it is not. Since 2026-10-08 it
*is* the source of the paper-derived rows of the five new cases, and each of those
rows says so in its `source` column.

## Where the battery coefficients actually come from

### `data/battery`

The case has 87 TC rows and all 87 are written. They have three different
provenances and the `source` column on each row says which:

- **The eleven hydrometallurgy rates were measured and entered by the user**
  from his own research, 2026-09-17. They are the only measurements in this
  model that are not upstream inflow data.
- **The rest come from precedent or from definition** -- a hulk that is not
  dismantled goes to the shredder at 1, unspecified material is not recovered.
- **`dismantling` is 0.95 | 0.98 | 1.00**, the user's own number, and the
  reason the traction motor fleet case was briefly set to the same rate before
  the review's own step 2 was found to give it.

Its cathode rates are a blend of three chemistries, and its casing and separator lose
their mass without a word: `BATTERY_ROUTES.md` §11.

### The five battery cases

`own` is the user's numbers: Table 2 of the report for the hydrometallurgical road, per
chemistry, and the user's own rows in `data/battery`. `BAU` and `REC` are the paper's.
Where the user has no number — the split between roads, pyrometallurgy, direct
recycling, the sodium treatment — `own` borrows the paper's REC, and the `variant` cells
say so. Anything nobody has is `PLACEHOLDER (Claude, not data)`. All of it, row by row,
is in `BATTERY_ROUTES.md` §4.

⚠️ **The composition is NOT here.** It arrives from upstream, written by
`04_04_batteries.py` in RAWCLICStockAndFlow. For `data/battery` that is
`battery_recovery_draws/`, summed over the chemistries. For the five new cases it is
`battery_recovery_draws_by_chemistry/<chemistry>/…`, one folder per chemistry, which
replaces the summed export (`BATTERY_ROUTES.md` §12). Solid-state holds no described
cell: its packaging is real, its cell is handed on.
