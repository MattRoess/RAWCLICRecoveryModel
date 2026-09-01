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


def source_dir(params, folder: str = '') -> str:
    """Where the draws for this case's scenario live."""
    from src import source as source_module
    upstream_dir = (source_module.read(folder, params)['upstream_dir'] if folder
                    else params.data.inflow_draws_dir)
    return os.path.normpath(os.path.join(
        params.data.upstream_root, upstream_dir, params.run.scenario or 'BAU'))


def is_upstream_case(params, folder: str) -> bool:
    """
    Whether this case is fed from upstream.

    A case says so by carrying a source.csv. That replaces matching a setting
    against the folder name: with one recovery model per upstream stage, the
    setting could only ever name one of them, so running another meant editing
    it -- and forgetting to is how one stage's draws meet another's
    coefficients without anything complaining.
    """
    from src import source as source_module
    return source_module.exists(folder)


def read_draws(folder: str, flow: str, group_marker: str = '__domain__'):
    """Every array upstream wrote for one flow, memory-mapped."""
    years_path = os.path.join(folder, 'years.npy')
    if not os.path.exists(years_path):
        raise UpstreamError(
            f'No upstream draws at {folder}.\n'
            f'That path is upstream_root + this case\'s `upstream_dir` + the\n'
            f'scenario. Check `upstream_dir` in the case\'s input_data/source.csv,\n'
            f'and that the matching stage of RAWCLICStockAndFlow has run its\n'
            f'year-sliced draw export -- each stage has its own switch naming\n'
            f'which years to write.')

    years = np.load(years_path)
    flow_dir = os.path.join(folder, flow)
    if not os.path.isdir(flow_dir):
        raise UpstreamError(f'{flow_dir} does not exist. Found: '
                            f'{sorted(os.listdir(folder))}.')

    domain_mass, element_mass, widths = {}, {}, {}
    for path in sorted(glob.glob(os.path.join(flow_dir, '*.npy'))):
        stem = os.path.basename(path)[:-4]
        # Split on the LAST '__': the domain files are named '__domain____Motors',
        # which begins with the separator, so splitting from the front loses them.
        left, _, right = stem.rpartition('__')
        if left == group_marker:
            array = domain_mass[right] = np.load(path, mmap_mode='r')
        elif right != 'total':
            array = element_mass[(left, right)] = np.load(path, mmap_mode='r')
        else:
            continue
        widths.setdefault(array.shape[0], []).append(stem)

    if not domain_mass:
        raise UpstreamError(f'{flow_dir} holds no {group_marker}__*.npy arrays.')
    one_run(flow_dir, widths)
    return years, domain_mass, element_mass


def one_run(flow_dir: str, widths: dict[int, list[str]]) -> None:
    """
    Refuse a folder whose arrays do not all hold the same number of draws.

    Raises:
        UpstreamError: naming how many arrays sit at each width, and some of
            them, so the odd family is identifiable without listing the folder.

    WHY THIS IS NOT PARANOIA
    ------------------------
    A folder is written file by file and never cleared, so it is the UNION of
    every run that has ever written to it. A file is replaced only when a later
    run happens to emit the same name -- change the element list upstream and
    the old names are left behind rather than removed. Nothing upstream reports
    that, because from there each run wrote exactly what it meant to.

    Downstream it is not visible either. `_one_product` means each array over
    `array[:draws]`, and slicing 200,000 rows from a 20,000-row array returns
    the 20,000 without complaint -- so a share becomes one run's element over
    another run's domain total, and the model solves it.

    It happened on 2026-08-31: `element_draws/BAU/collected` held four runs at
    once, and Motors' elements summed to 1.81 of Motors. That surfaced only
    because `src/rest.py` refuses parts exceeding the whole. A mix that stayed
    under 1 would have balanced, plotted and been wrong. Hence a check on the
    draw count, which is the one property every array in a run shares and no
    two runs need to.
    """
    if len(widths) < 2:
        return

    lines = []
    for draws in sorted(widths, reverse=True):
        names = sorted(widths[draws])
        shown = ', '.join(names[:4]) + (', ...' if len(names) > 4 else '')
        lines.append(f'  {len(names):4d} array(s) at {draws:,} draws: {shown}')

    raise UpstreamError(
        f'{flow_dir} holds arrays from more than one run.\n'
        + '\n'.join(lines) + '\n'
        f'A folder is written file by file and never cleared, so a name a later\n'
        f'run does not write is left behind instead of replaced. Read together,\n'
        f'one run\'s element is divided by another run\'s total and the shares are\n'
        f'meaningless -- while still summing, balancing and plotting.\n'
        f'Empty the folder and re-run the upstream stage that writes it.')


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


def build(years, per_product: dict, keep_years: list[int],
          draws: int, keep_groups: tuple[str, ...] = (),
          flow_id: str = 'F_collected',
          material_suffix: str = '_mixed', child_layer: str = 'element'):
    """
    The inflow and composition tables, one set of rows per product per year.

    `per_product` maps a Layer 1 name to that product's (domain_mass,
    element_mass) arrays. One product is the ordinary case; 04_01's five
    drivetrains are one case with five, because they are one study -- the same
    shredder and the same coefficient table, with only the dismantling rows
    keyed per drivetrain.

    EACH PRODUCT IS ITS OWN WHOLE. The component share is `component / that
    product's total`, never `component / all five together`, and the inflow is
    one row per product. Pooling them would still balance and still plot, and
    every share would be wrong by the ratio of one drivetrain's mass to the
    fleet's -- which is why the total is computed inside the product loop and
    not before it.

    Means over draws. The model's arithmetic is linear in the inflow, so a
    deterministic run built on means is the honest central case; the spread is
    carried separately by the Monte Carlo.

    `child_layer` says what the upstream child actually is, which differs by
    stage and cannot be guessed from the files (src/source.py):

        'element'   Cu within Wiring, from 04_02. The group's children are
                    elements, so a placeholder material is inserted between
                    them -- upstream has no material resolution there.

        'material'  calAHSS within elvBIW, from 04_01. The group's children
                    ARE materials, so they sit at Layer 3 and there is no
                    placeholder and no element layer.
    """
    inflow_rows, composition_rows, report = [], [], {}
    for product, (domain_mass, element_mass) in per_product.items():
        _one_product(product, domain_mass, element_mass, years, keep_years, draws,
                     keep_groups, flow_id, material_suffix, child_layer,
                     inflow_rows, composition_rows, report)

    return pd.DataFrame(inflow_rows), pd.DataFrame(composition_rows), report



def _one_product(product, domain_mass, element_mass, years, keep_years, draws,
                 keep_groups, flow_id, material_suffix, child_layer,
                 inflow_rows, composition_rows, report) -> None:
    """One product's rows, appended in place. See `build` for the reasoning."""
    domains = sorted(domain_mass)
    if keep_groups:
        unknown = sorted(set(keep_groups) - set(domains))
        if unknown:
            raise UpstreamError(
                f'groups names {unknown}; upstream has {domains} for {product}.')
        domains = [d for d in domains if d in keep_groups]

    for year in keep_years:
        index = int(np.searchsorted(years, year))

        def mean_of(array):
            return float(np.asarray(array[:draws, index], dtype=np.float64).mean())

        totals = {d: mean_of(domain_mass[d]) for d in domains}
        totals = {d: v for d, v in totals.items() if v > 0}
        product_total = sum(totals.values())
        report.setdefault(year, {})[product] = totals

        inflow_rows.append({'Year': year, 'Stock/Flow ID': flow_id,
                            'Substance_main_parent': product,
                            'Value': product_total, 'Unit': 'kt'})

        for domain in sorted(totals):
            base = {'Year': year, 'Stock/ID': flow_id, 'Layer 1': product,
                    'Layer 2': domain}
            composition_rows.append({**base, 'Layer 3': '', 'Layer 4': '',
                                     'Value': totals[domain] / product_total,
                                     'parameterCode': 'c-p'})

            if child_layer == 'element':
                # A placeholder material, whole, so the children have something
                # to be a share of. It carries no information.
                material = f'{domain}{material_suffix}'
                composition_rows.append({**base, 'Layer 3': material, 'Layer 4': '',
                                         'Value': 1.0, 'parameterCode': 'm-c'})

            for (child, in_domain), array in sorted(element_mass.items()):
                if in_domain != domain:
                    continue
                share = mean_of(array) / totals[domain]
                if share <= 0:
                    continue
                if child_layer == 'element':
                    composition_rows.append({**base, 'Layer 3': material,
                                             'Layer 4': child, 'Value': share,
                                             'parameterCode': 'e-m'})
                else:
                    composition_rows.append({**base, 'Layer 3': child, 'Layer 4': '',
                                             'Value': share, 'parameterCode': 'm-c'})


def load(params, folder: str, quiet: bool = False) -> dict | None:
    """
    The inflow and composition for this case, as frames. Nothing is written.

    Returns None for a case that is not upstream-backed: the reference cases
    are ordinary CSV folders and are read from disk as before.
    """
    if not is_upstream_case(params, folder):
        return None

    from src import source as source_module
    described = source_module.read(folder, params)

    source = source_dir(params, folder)

    # One folder per product. The arrays are memory-mapped, so holding all five
    # drivetrains open at once costs file handles, not memory -- what grows is
    # the number of ROWS, and through them the Monte Carlo's array.
    per_product, years = {}, None
    for product in described['products']:
        years, domain_mass, element_mass = read_draws(
            source, source_module.flow_for(described, product),
            described['group_marker'])
        per_product[product] = (domain_mass, element_mass)

    keep_years = wanted_years(years, params.run.years)

    # `read_draws` has already refused any single folder that mixes runs, so
    # one array per product settles that product's width. The products still
    # have to agree with each other: 04_01's five drivetrains are five folders,
    # and re-running one of them alone leaves the others at the old width --
    # the same mix as within a folder, one level up.
    per_product_width, by_width = {}, {}
    for product, (domains, _) in per_product.items():
        width = per_product_width[product] = next(iter(domains.values())).shape[0]
        by_width.setdefault(width, []).append(
            f'{product} in {source_module.flow_for(described, product)}/')
    one_run(source, by_width)

    available = per_product_width[described['products'][0]]
    draws = min(described['draws'], available)

    inflow, composition, report = build(
        years, per_product, keep_years, draws,
        described['groups'],
        flow_id=described['inflow_flow_id'],
        material_suffix=described['material_suffix'],
        child_layer=described['child_layer'])

    if not quiet:
        span = (f'{keep_years[0]}' if len(keep_years) == 1
                else f'{keep_years[0]}-{keep_years[-1]} ({len(keep_years)} years)')
        print(f'Upstream  : {os.path.relpath(source)}')
        print(f'            {source_module.describe(described)}')
        print(f'            {span}, {draws:,} draws')
        one = len(described['products']) == 1
        for year, by_product in report.items():
            whole = sum(v for totals in by_product.values() for v in totals.values())
            print(f'            {year}: {whole:,.4g} kt', end='' if one else '\n')
            for product, totals in sorted(by_product.items()):
                label = '' if one else f'              {product:<10s}'
                print(f'{label}  '
                      + '  '.join(f'{d} {v:,.4g}' for d, v in sorted(totals.items())))

    return {'inputs': inflow, 'composition': composition}
