# Filling in the coefficients

How to open the case workbook and start putting real numbers in it.

Everything else in this project works. The coefficients are the last thing
missing, and they are the one thing no tool can produce — they come from
measurements and literature.

---

## 1. Where the workbook is

Each case has one Excel file:

```
data_folder/bev_electronics_wiring/input_data/case.xlsx
data_folder/carcomposition_mockup/input_data/case.xlsx
```

Double-click it. It has three sheets:

| sheet | what it holds | do you edit it? |
|---|---|---|
| `source` | where the case's data comes from | rarely |
| `processes` | the flow network — what turns into what | when the system changes |
| **`TCs`** | **the transfer coefficients** | **this one** |

The header row is bold on a blue fill, and several columns have dropdowns, so
you pick a value rather than typing one.

---

## 2. Which rows to do first

Do **not** work down the sheet from the top. Most rows barely affect the
answer. Run this first:

```
./.venv/bin/python tools/filling_sheet.py
```

It solves the case once and prints the rows still holding a guess, hardest
first:

```
24 coefficients still waiting for a real number
the first 2 carry 80% of the spread in total recovered mass

  #  share    cum   infl  coefficient                                    guess
  1  72.5%  73.1%  0.849  Wiring_mixed/Cu F_shredded -> F_recovered_shredder  0.35-0.55-0.75
  2  22.2%  95.5%  0.454  BEV/Wiring F_collected -> F_dismantled              0.15-0.3-0.5
```

**`share`** is the fraction of the answer's uncertainty that one row accounts
for — what you would remove by measuring it exactly. In the electronics case
**two rows carry 80% of it**; in the car composition case, twelve.

The full list, with blank columns for the number and its citation, is written
to `output_data/filling_sheet.csv`. Use it as a reading list. **Type the
numbers into `case.xlsx`, not into that file** — it is rewritten every run.

---

## 3. What to type

For each row you have a source for, fill three cells in the `TCs` sheet:

| column | what it means |
|---|---|
| `value` | the most likely value — the **mode**, not the average |
| `value_min` | the lowest plausible value |
| `value_max` | the highest plausible value |

They make a triangular distribution. `value` may sit anywhere between the two;
it does not have to be in the middle, and usually is not.

Also replace the `source` cell. It currently says `PLACEHOLDER (Claude, not
data)` or `MADE UP (Claude)`. Put the citation there — author, year, table.
**That column is how anyone tells a measurement from a guess**, including you
in six months.

### Leave `is_residual` alone

A row marked `is_residual` is **calculated**, not measured. It is whatever is
left after the other rows in its group, so the group totals 1.

Those rows have `value_min` and `value_max` blank on purpose, and the run will
**refuse** to start if you fill them in. That is deliberate — a range typed
there used to be silently thrown away.

Only clear the `is_residual` mark if you have a genuinely **independent**
measurement for that row: someone measured the loss without working it out from
the recovery figure. If you clear it and fill in the range the constraint
already implies, you are counting one measurement twice and the answer comes
out falsely narrow.

`tools/tc_worklist.py` says which groups are which, and warns if this happens.

---

## 4. Check it, then run it

```
./.venv/bin/python 01_check_inputs.py
```

Reports the totals, whether each group closes to 1, and a `SUM TO 1` section
saying where the constraint is pulling the answer away from what you typed.
Run it **before** a full run — it takes a second, and it catches the mistakes
that would otherwise take twenty minutes to discover.

Then:

```
./.venv/bin/python 03_run_monte_carlo.py
```

The numbers, the distributions and the figures.

---

## 5. If a case has no `TCs` sheet yet

Only for a **new** case. The two that exist already have theirs.

```
./.venv/bin/python tools/make_skeleton.py data_folder/<your case>
```

It writes one row for every coefficient the case needs, with the identifying
columns filled and the values blank.

**It merges, and it deletes nothing.** Run it again after the upstream data
gains a resource and it adds the new rows without touching anything you have
filled in. So you can do a case in stages.

If the upstream data *loses* a resource — a re-export resolving fewer elements,
or a row moving to a different material — the coefficient you wrote for it is
**kept**, moved to the end of the sheet and reported as *inert*.
`01_check_inputs.py` then says it does not currently fire. Your number is never
thrown away because the data moved under it.

**Close Excel first.** It writes the workbook by replacing the file, and Excel
holding it open is the one thing that stops that working.

---

## The short version

1. `tools/filling_sheet.py` — which rows matter
2. Open `case.xlsx`, `TCs` sheet — fill `value`, `value_min`, `value_max`, and the citation in `source`
3. Don't touch `is_residual`
4. `01_check_inputs.py` — check
5. `03_run_monte_carlo.py` — run

For the reasoning behind any of it, see [CASES.md](CASES.md).
