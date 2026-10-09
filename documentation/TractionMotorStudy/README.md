# The traction motor recycling study

**The source for every traction motor coefficient in this project.** It lives
here, inside the repository, because it was twice lost from `~/Downloads`
between sessions and the model cannot be checked without it.

| file | what it is |
|---|---|
| `RAWCLIC_BEV_Motor_Recycling_Report_V1.md` | the review, EMPA / RAWCLIC, September 2026 |
| `RAWCLIC_BEV_Motor_Recycling_Report_V1.pdf` | the same, as delivered |
| `RAWCLIC_BEV_Motor_Recycling_TC_V1.xlsx` | the transfer coefficients, 2030 and 2060, both routes |

`../recycling_coefficients.csv` is the workbook flattened to one row per
(horizon, route, step, material), written by
`tools/extract_recycling_coefficients.py`. **It is a convenience, not the
source.** Where the two disagree, the workbook wins.

⚠️ **THE REPORT AND THE WORKBOOK DISAGREE ABOUT HOW MUCH IS KNOWN.** The
report's own finding 9 is *"No evidence-supported full-chain TC exists for 2030
or 2060"*, and its section 5.2 table is almost entirely `NR`. The workbook then
fills those cells with Min|Mode|Max anyway, labelled as scenario assumptions.
Anyone reading only the workbook will not notice its numbers are a
construction. **Every traction coefficient in this project is a scenario
assumption. None is a measurement.**

## What reads it

    tools/build_tractionmotor_case.py            THE case: both roads,
                                                 split at the review's step 2
    tools/extract_traction_tcs.py                the workbook -> the csv

Each builder types the coefficients it needs at the top of the file with the
sheet they came from, so the chain from this folder to a case is one file to
read.
