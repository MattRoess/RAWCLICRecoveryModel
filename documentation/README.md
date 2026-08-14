# Documentation index

Written 2026-08-14, after a review of the inherited code. The point of these
documents is that the next working session starts from something written down
rather than from anyone's recollection.

| Document | What is in it |
|---|---|
| [SETUP.md](SETUP.md) | Getting running on a new machine: Python 3.14 without conda, the venv, and Positron. Start here on a fresh Mac. |
| [MODEL_MECHANICS.md](MODEL_MECHANICS.md) | How the model actually computes a result. The nesting rule, how composition and TCs are applied, what the two engines do differently by design. Read this first. |
| [DEFECTS.md](DEFECTS.md) | Every defect and engine divergence found, each with a measurement and a one-command reproduction. |
| [DESIGN_tc_table.md](DESIGN_tc_table.md) | How to build the TC table so that sum-to-1 holds by construction. Proposal, with a worked example in `data_folder/template`. The real table does not exist yet, so read this before collecting data. |
| [DESIGN_monte_carlo.md](DESIGN_monte_carlo.md) | The design problem for the Monte Carlo version: architecture, the compute budget, sampling asymmetric triangulars, and how to sample under the sum-to-1 constraint. Not yet built. |
| [HANDOVER.md](HANDOVER.md) | Current state, decisions taken and why, open questions, and the recommended order of work. |

The input file format is specified in `../doc/User guide.docx` (Harmjan de
Vries, 21-11-2024). That document is the authority on the input schema and is
still accurate. It does not describe model behaviour, which is what
MODEL_MECHANICS.md covers.

## Checking a dataset

What the transfer coefficients in a dataset actually total, and whether
composition closes to 1:

```bash
./.venv/bin/python check_mass_balance.py data_folder/basic_test
```

Read MODEL_MECHANICS.md §4 first — the grouping this uses is not the obvious
one, and the obvious one produces numbers that are not quantities.

## Seeing the flows

To understand **how the model is wired** — every flow, every process, and the
transfer coefficients behind each arrow, nothing scaled by mass:

```bash
./.venv/bin/python plot_structure.py data_folder/template
```

To see **how much mass goes where**, as a Sankey, in total and per element:

```bash
./.venv/bin/python plot_flows.py data_folder/template
```

Writes an SVG Sankey per case into `figures/` — one for total mass, one per
element. Totals are taken at each flow's own shallowest depth, so the nesting
described in MODEL_MECHANICS.md §1 is not double counted, and edge magnitudes
are recomputed by replaying the model's own process loop rather than inferred
from the solution file.

## Verifying the model still works

Both engines reproduce the committed reference result exactly:

```bash
./.venv/bin/python compare_engines.py data_folder/basic_test
```

Expected: 180 rows, largest engine difference on the order of 1e-15.

That last figure varies slightly between runs. This is expected and understood:
the LA engine's encoding order depends on Python's hash randomisation, which
changes the floating-point accumulation order in its sparse solve. See
DEFECTS.md §3.5. The optimized engine is bit-identical across runs.
