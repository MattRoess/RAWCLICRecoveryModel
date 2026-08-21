"""
src/upstream.py
===============

Read the inflow and the composition straight from the upstream draws.

THERE IS NO IMPORT STEP
-----------------------
There used to be one, and it was a mistake. The inflow and the composition are
not things anyone writes: they are the upstream pipeline's numbers, and a copy
of them sitting in a CSV is a copy that goes stale the moment upstream re-runs.

So every stage refreshes them from the source before it does anything. The only
file in a case folder that a person writes is `TCs.csv` -- the transfer
coefficients, which are genuinely yours -- plus `processes.csv`, the network
they hang on. `inputs.csv` and `composition.csv` are rewritten on every run and
are gitignored: read them to see what the model was handed, never edit them.

WHERE THE NUMBERS COME FROM
---------------------------
Stage 04_02 of RAWCLICStockAndFlow multiplies fleet draws (vehicles per year) by
electronics draws (grams per vehicle), draw by draw, and reports element mass in
kilotonnes. It keeps percentiles and drops the draws, so it also writes the raw
draws for the years named in its own settings:

    <upstream>/data/processed/element_draws/<scenario>/<flow>/
        years.npy                      the years exported
        __domain____<domain>.npy       (draws, years)  mass of the domain itself
        <element>__<domain>.npy        (draws, years)  that element within it

HOW IT MAPS ONTO THE FOUR LAYERS
---------------------------------
    Layer 1  product     BEV
    Layer 2  component   the electronics domain: Wiring, Motors, PCB, Sensors
    Layer 3  material    one placeholder per domain
    Layer 4  element     Cu, Nd, Au, ...

The material layer is a placeholder: upstream has no material resolution, going
straight from a domain to the elements in it. Inventing materials would be
inventing data, so each domain gets one material with a share of 1.0 and the
layer is carried for the model's sake. Nothing at the material layer is
informative here.

WHAT THE INFLOW IS
------------------
The **electronics** in the collected vehicles, not the vehicles. The steel,
glass and plastic of the car are not in this dataset, so a recovery rate
computed from it is a rate for electronics. Even within that, the tracked
elements are a minority -- the rest of each domain is picked up by
`src/rest.py` and treated as unrecovered.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

# What the item is called, how its files are named and what its placeholder
# material layer is called are all DATA, not code. They live in
# src/params_schema.py so that a different recovery item -- a panel, a battery,
# anything upstream exports in this layout -- is a settings change rather than
# an edit here. tests/test_generality.py solves a non-vehicle item to keep that
# true.

class UpstreamError(FileNotFoundError):
    """Raised when the upstream draws are missing or do not cover the request."""


def source_dir(params) -> str:
    """Where the draws for this scenario live."""
    return os.path.normpath(os.path.join(
        params.data.upstream_root, params.data.inflow_draws_dir,
        params.run.scenario or 'BAU'))


def is_upstream_case(params, folder: str) -> bool:
    """Whether this case folder is the one fed from upstream."""
    return os.path.normpath(folder) == os.path.normpath(
        os.path.join('data_folder', params.data.import_case))


def read_draws(folder: str, flow: str, group_marker: str = '__domain__'):
    """Every array upstream wrote for one flow, memory-mapped."""
    years_path = os.path.join(folder, 'years.npy')
    if not os.path.exists(years_path):
        raise UpstreamError(
            f'No upstream draws at {folder}.\n'
            f'Stage 04_02 of RAWCLICStockAndFlow writes them when\n'
            f'materials.bev_electronics_element_draws_years names at least one year.')

    years = np.load(years_path)
    flow_dir = os.path.join(folder, flow)
    if not os.path.isdir(flow_dir):
        raise UpstreamError(f'{flow_dir} does not exist. Found: '
                            f'{sorted(os.listdir(folder))}.')

    domain_mass, element_mass = {}, {}
    for path in sorted(glob.glob(os.path.join(flow_dir, '*.npy'))):
        stem = os.path.basename(path)[:-4]
        # Split on the LAST '__': the domain files are named '__domain____Motors',
        # which begins with the separator, so splitting from the front loses them.
        left, _, right = stem.rpartition('__')
        if left == group_marker:
            domain_mass[right] = np.load(path, mmap_mode='r')
        elif right != 'total':
            element_mass[(left, right)] = np.load(path, mmap_mode='r')

    if not domain_mass:
        raise UpstreamError(f'{flow_dir} holds no {group_marker}__*.npy arrays.')
    return years, domain_mass, element_mass


def wanted_years(available: np.ndarray, setting: str) -> list[int]:
    """
    Which of the exported years this run covers.

    Uses the same spelling as `run.years`: blank for all of them, '2040' for
    one, '2030-2050' for a range, '2030-2050,5' for every fifth. Asking for a
    year upstream did not export is an error naming what is there, rather than
    a silently shorter answer.
    """
    from src.selection import chosen_years

    frame = pd.DataFrame({'Year': [str(y) for y in available]})
    chosen = [int(y) for y in chosen_years(frame, setting or '')]
    if not chosen:
        raise UpstreamError(
            f'No year matches {setting!r}. Upstream exported {available.tolist()}.\n'
            f'Either change run.years, or add the year to\n'
            f'materials.bev_electronics_element_draws_years upstream and re-run 04_02.')
    return chosen


def build(years, domain_mass, element_mass, keep_years: list[int],
          draws: int, keep_groups: tuple[str, ...] = (),
          product: str = 'BEV', flow_id: str = 'F_collected',
          material_suffix: str = '_mixed'):
    """
    The inflow and composition tables, one set of rows per year.

    Means over draws. The model's arithmetic is linear in the inflow, so a
    deterministic run built on means is the honest central case; the spread is
    carried separately by the Monte Carlo.
    """
    domains = sorted(domain_mass)
    if keep_groups:
        unknown = sorted(set(keep_groups) - set(domains))
        if unknown:
            raise UpstreamError(f'groups names {unknown}; upstream has {domains}.')
        domains = [d for d in domains if d in keep_groups]

    inflow_rows, composition_rows, report = [], [], {}
    for year in keep_years:
        index = int(np.searchsorted(years, year))

        def mean_of(array):
            return float(np.asarray(array[:draws, index], dtype=np.float64).mean())

        totals = {d: mean_of(domain_mass[d]) for d in domains}
        totals = {d: v for d, v in totals.items() if v > 0}
        product_total = sum(totals.values())
        report[year] = totals

        inflow_rows.append({'Year': year, 'Stock/Flow ID': flow_id,
                            'Substance_main_parent': product,
                            'Value': product_total, 'Unit': 'kt'})

        for domain in sorted(totals):
            material = f'{domain}{material_suffix}'
            base = {'Year': year, 'Stock/ID': flow_id, 'Layer 1': product,
                    'Layer 2': domain}
            composition_rows.append({**base, 'Layer 3': '', 'Layer 4': '',
                                     'Value': totals[domain] / product_total,
                                     'parameterCode': 'c-p'})
            composition_rows.append({**base, 'Layer 3': material, 'Layer 4': '',
                                     'Value': 1.0, 'parameterCode': 'm-c'})
            for (element, in_domain), array in sorted(element_mass.items()):
                if in_domain != domain:
                    continue
                share = mean_of(array) / totals[domain]
                if share > 0:
                    composition_rows.append({**base, 'Layer 3': material,
                                             'Layer 4': element, 'Value': share,
                                             'parameterCode': 'e-m'})

    return pd.DataFrame(inflow_rows), pd.DataFrame(composition_rows), report


def load(params, folder: str, quiet: bool = False) -> dict | None:
    """
    The inflow and composition for this case, as frames. Nothing is written.

    Returns None for a case that is not upstream-backed: the reference cases
    are ordinary CSV folders and are read from disk as before.
    """
    if not is_upstream_case(params, folder):
        return None

    source = source_dir(params)
    years, domain_mass, element_mass = read_draws(
        source, params.data.upstream_flow, params.data.group_marker)
    keep_years = wanted_years(years, params.run.years)

    available = next(iter(domain_mass.values())).shape[0]
    draws = min(params.data.draws, available)

    inflow, composition, report = build(
        years, domain_mass, element_mass, keep_years, draws,
        tuple(params.data.groups), product=params.data.product,
        flow_id=params.data.inflow_flow_id,
        material_suffix=params.data.material_suffix)

    if not quiet:
        span = (f'{keep_years[0]}' if len(keep_years) == 1
                else f'{keep_years[0]}-{keep_years[-1]} ({len(keep_years)} years)')
        print(f'Upstream  : {os.path.relpath(source)}')
        print(f'            {params.data.upstream_flow}, {span}, {draws:,} draws, '
              f'domains {", ".join(params.data.groups) or "all"}')
        for year, totals in report.items():
            print(f'            {year}: {sum(totals.values()):,.4g} kt  '
                  + '  '.join(f'{d} {v:,.4g}' for d, v in sorted(totals.items())))

    return {'inputs': inflow, 'composition': composition}
