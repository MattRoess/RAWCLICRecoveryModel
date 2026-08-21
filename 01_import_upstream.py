"""
import_upstream.py
==================

Turn the upstream per-element draws into a case folder this model can solve.

    ./.venv/bin/python import_upstream.py

Run it when the upstream data changes, not on every model run. It writes a data
folder under `data_folder/`, which `04_run_model.py` and `05_run_monte_carlo.py`
then read like any other case.

WHERE THE DATA COMES FROM
-------------------------
Stage 04_02 of RAWCLICStockAndFlow multiplies fleet draws (vehicles per year) by
electronics draws (grams per vehicle), draw by draw, and reports element mass in
kilotonnes. It keeps percentiles and drops the draws, because holding every year
would be 60 GB -- so it now also writes the draws for a few named years, which
is what this reads. See `data.*` in `src/params_schema.py` for the path.

    <upstream>/data/processed/element_draws/<scenario>/<flow>/
        years.npy                      the years exported
        __domain____<domain>.npy       (draws, years)  mass of the domain itself
        <element>__<domain>.npy        (draws, years)  that element within it
        <element>__total.npy           (draws, years)  that element, all domains

HOW IT MAPS ONTO THE FOUR LAYERS
---------------------------------
    Layer 1  product     BEV
    Layer 2  component   the electronics domain: Wiring, Motors, PCB, Sensors
    Layer 3  material    one placeholder per domain
    Layer 4  element     Cu, Nd, Au, ...

The material layer is a placeholder because the upstream data has no material
resolution -- it goes straight from a domain to the elements in it. Inventing
materials would be inventing data, so each domain gets exactly one material with
a share of 1.0, and the layer is carried for the model's sake rather than
meaning anything. That is worth knowing when reading a result: nothing at the
material layer is informative here.

WHAT THE INFLOW IS
------------------
The **electronics** in the collected vehicles, not the vehicles. Upstream tracks
wiring, motors, boards and sensors; the steel, glass and plastic of the car are
not in this dataset at all. So the product total here is the electronics mass,
and a recovery rate computed from it is a rate for electronics.

The elements that *are* tracked are a minority even of that -- copper is most of
a harness, but a board is mostly laminate and solder that no one has itemised.
The rest of each domain is picked up automatically by `src/rest.py` and treated
as unrecovered, which is why the recovery figures are a lower bound.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.params_schema import ParameterError, current

DOMAIN_MARKER = '__domain__'
# One placeholder material per domain. Named after the domain so a result row
# reads sensibly rather than showing a bare 'material'.
MATERIAL_SUFFIX = '_mixed'
PRODUCT = 'BEV'


def read_draws(folder: str, flow: str):
    """
    Every array upstream wrote for one flow.

    Returns (years, domain_mass, element_mass) where the two dictionaries are
    keyed by domain and by (element, domain), each holding (draws, years).
    """
    import glob

    years = np.load(os.path.join(folder, 'years.npy'))
    flow_dir = os.path.join(folder, flow)
    if not os.path.isdir(flow_dir):
        raise FileNotFoundError(
            f'{flow_dir} does not exist. Upstream writes one folder per flow; '
            f'found {sorted(os.listdir(folder))}.')

    domain_mass, element_mass = {}, {}
    for path in sorted(glob.glob(os.path.join(flow_dir, '*.npy'))):
        stem = os.path.basename(path)[:-4]
        # Split on the LAST '__', not the first. The domain-mass files are named
        # '__domain____Motors', which begins with the separator, so partitioning
        # from the front returns an empty name and loses them silently.
        left, _, right = stem.rpartition('__')
        if left == DOMAIN_MARKER:
            domain_mass[right] = np.load(path, mmap_mode='r')
        elif right != 'total':
            element_mass[(left, right)] = np.load(path, mmap_mode='r')

    if not domain_mass:
        raise FileNotFoundError(
            f'{flow_dir} holds no {DOMAIN_MARKER}__*.npy arrays. Upstream needs '
            f'to be re-run with the domain mass export.')
    return years, domain_mass, element_mass


def build_tables(years, domain_mass, element_mass, year: int, draws: int,
                 keep_domains: tuple[str, ...] = ()):
    """
    The three input tables, from the mean over draws.

    The mean rather than the median, because the model's arithmetic is linear in
    the inflow: the mean of the products is the product of the means for this
    step, so a deterministic run built on means is the honest central case. The
    spread is not lost -- it is carried separately for the Monte Carlo.
    """
    index = int(np.searchsorted(years, year))
    if index >= len(years) or years[index] != year:
        raise ValueError(f'{year} is not in the exported years {years.tolist()}. '
                         f'Set bev_electronics_element_draws_years upstream and '
                         f're-run 04_02.')

    def mean_of(array):
        return float(np.asarray(array[:draws, index], dtype=np.float64).mean())

    domains = sorted(domain_mass)
    if keep_domains:
        unknown = sorted(set(keep_domains) - set(domains))
        if unknown:
            raise ValueError(f'import_domains names {unknown}, which upstream did '
                             f'not write. It has {domains}.')
        domains = [d for d in domains if d in keep_domains]

    domain_totals = {domain: mean_of(domain_mass[domain]) for domain in domains}
    domains = [d for d in domains if domain_totals[d] > 0]
    product_total = sum(domain_totals[d] for d in domains)

    inputs = pd.DataFrame([{
        'Year': year, 'Stock/Flow ID': 'F_collected',
        'Substance_main_parent': PRODUCT, 'Value': product_total, 'Unit': 'kt',
    }])

    rows = []
    for domain in domains:
        material = f'{domain}{MATERIAL_SUFFIX}'
        rows.append({'Stock/ID': 'F_collected', 'Layer 1': PRODUCT, 'Layer 2': domain,
                     'Layer 3': '', 'Layer 4': '',
                     'Value': domain_totals[domain] / product_total,
                     'parameterCode': 'c-p'})
        # The material layer carries no information here; one per domain, whole.
        rows.append({'Stock/ID': 'F_collected', 'Layer 1': PRODUCT, 'Layer 2': domain,
                     'Layer 3': material, 'Layer 4': '', 'Value': 1.0,
                     'parameterCode': 'm-c'})

        for (element, in_domain), array in sorted(element_mass.items()):
            if in_domain != domain:
                continue
            share = mean_of(array) / domain_totals[domain]
            if share <= 0:
                continue
            rows.append({'Stock/ID': 'F_collected', 'Layer 1': PRODUCT,
                         'Layer 2': domain, 'Layer 3': material, 'Layer 4': element,
                         'Value': share, 'parameterCode': 'e-m'})

    return inputs, pd.DataFrame(rows), domain_totals, product_total


def main() -> int:
    try:
        params = current()
    except ParameterError as error:
        print(error, file=sys.stderr)
        return 1

    upstream = os.path.normpath(os.path.join(
        params.data.upstream_root, params.data.inflow_draws_dir,
        params.run.scenario or 'BAU'))
    flow = params.data.upstream_flow
    year = params.data.import_year
    draws = params.data.draws

    print(f'Reading   : {upstream}')
    print(f'Flow      : {flow}   Year: {year}   Draws: {draws:,}')

    years, domain_mass, element_mass = read_draws(upstream, flow)
    available = next(iter(domain_mass.values())).shape[0]
    if draws > available:
        print(f'  NOTE: only {available:,} draws upstream; using all of them.')
        draws = available

    keep = tuple(params.data.groups)
    if keep:
        print(f'Domains   : {", ".join(keep)}  (a restricted study, not all electronics)')

    inputs, composition, domain_totals, product_total = build_tables(
        years, domain_mass, element_mass, year, draws, keep_domains=keep)

    folder = os.path.join('data_folder', params.data.import_case)
    os.makedirs(os.path.join(folder, 'input_data'), exist_ok=True)
    inputs.to_csv(os.path.join(folder, 'input_data', 'inputs.csv'), index=False)
    composition.to_csv(os.path.join(folder, 'input_data', 'composition.csv'), index=False)

    print(f'\n{folder}/input_data/')
    print(f'  inputs.csv       1 row, {product_total:,.4g} kt of BEV electronics')
    print(f'  composition.csv  {len(composition)} rows')
    print(f'\n  domain mass ({flow}, {year}), kt:')
    for domain, mass in sorted(domain_totals.items(), key=lambda kv: -kv[1]):
        tracked = composition[(composition['Layer 2'] == domain)
                              & (composition['parameterCode'] == 'e-m')]['Value'].sum()
        print(f'    {domain:<10} {mass:>12,.4g}   {tracked:>6.1%} of it in tracked elements')

    tcs = os.path.join(folder, 'input_data', 'TCs.csv')
    if not os.path.exists(tcs):
        print(f'\n  {tcs} does not exist yet. The flow network and its transfer')
        print(f'  coefficients are domain knowledge -- see')
        print(f'  documentation/DESIGN_tc_table.md. Nothing can be solved without it.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
