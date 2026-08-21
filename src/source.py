"""
src/source.py
=============

What a case is, and where its numbers come from — declared by the case itself.

WHY THIS EXISTS
---------------
There is one recovery model per upstream stage: 04_01 gives components and
materials for a whole car, 04_02 gives electronics domains and their elements,
and 04_03 and 04_04 will each give something else again. They are different
studies with different networks, different coefficients and different layers.

Switching between them must not mean editing settings. A setting that has to be
changed to run the other case is a setting somebody forgets, and then a run
silently reads one stage's draws with another stage's coefficients.

So every case carries its own `source.csv`:

    data_folder/<case>/input_data/
        source.csv      where the numbers come from, and how they map to layers
        processes.csv   the flow network
        TCs.csv         the coefficients

and running it is naming it:

    ./.venv/bin/python 02_run_model.py data_folder/car_composition
    ./.venv/bin/python 02_run_model.py data_folder/bev_electronics

Nothing in `src/params_schema.py` changes between those two.

WHAT source.csv SAYS
--------------------
Two columns, `key` and `value`. Everything is optional; anything absent falls
back to the matching `data.*` setting, so an older case with no source.csv
keeps working exactly as before.

    key               example                        what it is
    ----------------- ------------------------------ ------------------------
    upstream_dir      data/processed/element_draws   under upstream_root
    product           BEV                            Layer 1
    inflow_flow_id    F_collected                    the flow the mass arrives in
    child_layer       element                        'element' or 'material'
    group_marker      __domain__                     how a group's own mass is named
    material_suffix   _mixed                         placeholder material, when needed
    groups            Wiring;Motors                  blank means all of them
    flow              collected                      which upstream flow to read

CHILD LAYER — THE ONE THAT MATTERS
----------------------------------
Upstream files are `<child>__<parent>.npy`, but what the child *is* differs by
stage:

    04_02   the child is an ELEMENT      Cu within Wiring
            -> Layer 2 group, Layer 3 a placeholder material, Layer 4 element

    04_01   the child is a MATERIAL      calAHSS within elvBIW
            -> Layer 2 component, Layer 3 material, Layer 4 unused

Getting this wrong does not fail — it silently puts materials where elements
belong, and every coefficient keyed at the element layer then matches nothing.
Hence a named setting rather than a guess.
"""
from __future__ import annotations

import os

import pandas as pd

FILENAME = 'source.csv'

# 'element' puts the child at Layer 4 with a placeholder material above it;
# 'material' puts it at Layer 3 and leaves Layer 4 empty.
CHILD_LAYERS = ('element', 'material')

# Every key a case may set, and which `data.*` setting it falls back to.
FALLBACK = {
    'upstream_dir': 'inflow_draws_dir',
    'product': 'product',
    'inflow_flow_id': 'inflow_flow_id',
    'child_layer': None,               # defaults to 'element', the 04_02 shape
    'group_marker': 'group_marker',
    'material_suffix': 'material_suffix',
    'groups': 'groups',
    'flow': 'upstream_flow',
}


class SourceError(ValueError):
    """Raised when a case's source.csv does not make sense."""


def path_for(case: str) -> str:
    return os.path.join(case, 'input_data', FILENAME)


def exists(case: str) -> bool:
    """Whether this case declares where its numbers come from."""
    return os.path.exists(path_for(case))


def read(case: str, params) -> dict:
    """
    The case's source description, with anything unstated taken from settings.

    Returns a plain dict rather than a dataclass: it is a small bag of strings
    read from a two-column CSV, and giving it a type would suggest it is
    validated more than it is.
    """
    described: dict[str, str] = {}
    if exists(case):
        frame = pd.read_csv(path_for(case), keep_default_na=False, na_values=[])
        missing = {'key', 'value'} - set(frame.columns)
        if missing:
            raise SourceError(
                f"{path_for(case)} needs columns 'key' and 'value'; "
                f"missing {', '.join(sorted(missing))}.")
        unknown = sorted(set(frame['key']) - set(FALLBACK))
        if unknown:
            raise SourceError(
                f"{path_for(case)} sets {unknown}, which mean nothing here.\n"
                f"Known keys: {', '.join(sorted(FALLBACK))}.")
        described = {str(k).strip(): str(v).strip()
                     for k, v in zip(frame['key'], frame['value'])}

    # A key that is PRESENT settles the matter, blank or not. Blank is a real
    # answer -- `groups` blank means every group, `material_suffix` blank means
    # no placeholder is wanted -- and treating it as "unstated" would quietly
    # substitute the other case's setting, which is the exact failure this file
    # exists to prevent. Only a key that is absent falls back.
    out = {}
    for key, fallback in FALLBACK.items():
        if key in described:
            out[key] = described[key]
        elif fallback is not None:
            out[key] = getattr(params.data, fallback)
        else:
            out[key] = 'element'

    # `groups` is a list either way: 'Wiring;Motors' from a file, a tuple from
    # settings. Semicolon-separated because a comma would need quoting in CSV.
    if isinstance(out['groups'], str):
        out['groups'] = tuple(g.strip() for g in out['groups'].split(';') if g.strip())
    else:
        out['groups'] = tuple(out['groups'])

    # Absent means the 04_02 shape; present-but-blank means somebody meant to
    # say something and did not, so say so rather than picking for them.
    if out['child_layer'] not in CHILD_LAYERS:
        raise SourceError(
            f"{path_for(case)}: child_layer is {out['child_layer']!r}, "
            f"but must be one of {', '.join(CHILD_LAYERS)}.\n"
            f"  element   the upstream child is an element within a group (04_02)\n"
            f"  material  the upstream child is a material within a component (04_01)")

    return out


def describe(source: dict) -> str:
    """One line naming what this case reads, for a run to print."""
    return (f"{source['product']} / {source['flow']} / child at the "
            f"{source['child_layer']} layer"
            + (f" / groups {', '.join(source['groups'])}" if source['groups'] else ''))
