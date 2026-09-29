# The battery recycling study

**The source for `data/battery`.** It lives here, inside the repository,
for the same reason the traction motor study does: a document that only exists
in `~/Downloads` is a document the next session cannot check a coefficient
against.

| file | what it is |
|---|---|
| `Battery_Cell_Recycling_Report_LFP_LMFP_NMC.md` | **the study**, LFP / LMFP / NMC cell recycling |
| `Battery_Cell_Recycling_Report_LFP_LMFP_NMC.pdf` | the same, as delivered |
| `1-s2.0-S0956053X2600543X-main.pdf` | a journal article, *not* the study — see below |

⚠️ **THE JOURNAL ARTICLE IS NOT THE STUDY.** `1-s2.0-...` had been sitting
loose in `data/battery/` since the case was built, with nothing saying
what it was or which coefficient it supported. It was moved here on 2026-09-29
after being mistaken, by me, for the source document. It is a cited paper
beside the study, not the study.

## Where the battery coefficients actually come from

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

⚠️ **The composition is NOT here.** It arrives from upstream as
`battery_recovery_draws/`, written by `04_04_batteries.py` in
RAWCLICStockAndFlow, summed over the chemistries. Two chemistries have no
described cell: sodium-ion holds no CRM or SRM, and solid-state holds lithium
with no composition to attach a coefficient to.
