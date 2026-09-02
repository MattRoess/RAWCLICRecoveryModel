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
        years.npy                              the years exported
        __domain____<group>.npy                (draws, years)  the group itself
        <element>__<group>.npy                 (draws, years)  an element in it
        <element>__<material>__<group>.npy     (draws, years)  and in a material

HOW IT MAPS ONTO THE FOUR LAYERS
---------------------------------
    Layer 1  product     BEV
    Layer 2  component   the electronics domain: Wiring, Motors, PCB, Sensors
    Layer 3  material    what the file names resolve, and a placeholder for
                         whatever they do not
    Layer 4  element     Cu, Nd, Au, ...

**No name here is written in this file.** The segments of a file name run
finest first and end with the group, so depth alone says which layer a name
belongs at; which elements and which materials exist is read from the files,
and how they map onto layers from the case's own source table. That is what
lets one model serve a vehicle, a panel and a battery -- and it is checked by
`tests/test_generality.py`, which solves an item sharing no name with any of
them.

Layer 3 used to be a placeholder and nothing else, because upstream exported
only `<element>__<group>`. Since 2026-08-31 it also exports the material an
element sits in, and that is real resolution where this model had a stand-in.
The placeholder is still written for what is not resolved, so a folder without
the new files produces exactly the rows it always did.

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


# How far an element's material-resolved parts may exceed the element's own
# exported total before that is a disagreement rather than arithmetic noise.
# Two arrays written by one run, meaned over the same draws, agree to about
# 1e-4 relative; a real double-count is orders of magnitude bigger.
PARTS_TOLERANCE = 1e-3


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
            # The segments before the group run FINEST FIRST: 'Fe__Motors' is
            # the element Fe, 'Fe__esteel__Motors' is Fe within electrical
            # steel. Which is which is not decided here -- this only records
            # how deep the name goes, and `_one_product` maps depth onto
            # layers. Nothing in this file knows an element or a material by
            # name; both are read from the file names and the case's
            # source table.
            child = tuple(left.split('__'))
            if len(child) > 2:
                raise UpstreamError(
                    f'{stem}.npy in {flow_dir} names {len(child)} levels below '
                    f'the group.\nThis model has two: a material and an element '
                    f'within it. A file named\n<element>__<material>__<group> is '
                    f'read; anything deeper has nowhere to go.')
            array = element_mass[(child, right)] = np.load(path, mmap_mode='r')
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
    one, '2030-2050' for a range, '2030-2050,5' for every fifth.

    IT SAYS WHAT IT COULD NOT GIVE YOU. `chosen_years` selects FROM the years
    that exist, so a request for years upstream never exported can only come
    back shorter -- and it used to come back shorter in silence. Asking for
    2020-2070 every fifth year returned 2030 to 2050, five years of the eleven
    requested, with nothing but a line of ordinary run output to say so. This
    docstring claimed the opposite, that a missing year was an error; it was
    not, and that was the misleading part.

    Now the request is expanded on its own terms first and compared against what
    is there, so the caller can report the difference. Still not an error: a
    range is the natural way to say "everything in this window", and refusing it
    because the window is wider than the data would make the setting unusable.
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


def years_not_exported(available: np.ndarray, setting: str) -> list[int]:
    """
    Years `setting` asks for that upstream did not export.

    The request is expanded against a span wide enough to hold any year anyone
    would write, rather than against the data, so it reflects what was ASKED
    rather than what could be answered. The parser is the same one, so the two
    cannot drift on what '2020-2070, 5' means.
    """
    from src.selection import chosen_years

    if not str(setting or '').strip():
        return []                      # blank means "whatever is there"
    span = pd.DataFrame({'Year': [str(y) for y in range(1900, 2201)]})
    try:
        asked = {int(y) for y in chosen_years(span, setting)}
    except Exception:
        return []                      # an unparseable setting is reported elsewhere
    return sorted(asked - set(int(y) for y in available))


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
                    elements, and Layer 3 holds whatever material the file
                    names resolve, plus a placeholder for what they do not.
                    See `_material_and_element_rows`.

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

            here = {child: mean_of(array)
                    for (child, in_domain), array in sorted(element_mass.items())
                    if in_domain == domain}
            here = {child: mass for child, mass in here.items() if mass > 0}

            if child_layer == 'element':
                composition_rows.extend(
                    _material_and_element_rows(base, domain, totals[domain],
                                               here, material_suffix))
            else:
                for child, mass in here.items():
                    if len(child) > 1:
                        raise UpstreamError(
                            f"{'__'.join(child)}__{domain}.npy names a material "
                            f"and something inside it,\nbut this case reads its "
                            f"children AS materials (`child_layer` is 'material' "
                            f"in its\nsource table), so there is no layer below "
                            f"for the inner name to sit at.")
                    composition_rows.append({**base, 'Layer 3': child[0],
                                             'Layer 4': '',
                                             'Value': mass / totals[domain],
                                             'parameterCode': 'm-c'})


def _material_and_element_rows(base, domain: str, domain_total: float,
                               here: dict[tuple[str, ...], float],
                               material_suffix: str) -> list[dict]:
    """
    One domain's Layer 3 and Layer 4 rows, from the arrays exported for it.

    Args:
        base: the Year / flow / Layer 1 / Layer 2 columns, already filled.
        domain: the Layer 2 name, for error messages.
        domain_total: the domain's own mass, which Layer 3 is a share of.
        here: mass per exported child of this domain, keyed by the path from
            the file name -- `('Cu',)` for an element whose material upstream
            does not resolve, `('Fe', 'esteel')` for one it does.
        material_suffix: what to call the material that holds the rest.

    Returns:
        The rows, Layer 3 before its own Layer 4 children.

    Raises:
        UpstreamError: if an element's resolved parts exceed the element's own
            exported total, or if the resolved materials leave no room for
            elements exported outside them. Both mean the arrays disagree with
            each other, which no share can be computed around.

    WHAT SITS AT LAYER 3
    --------------------
    Whatever the file names resolve, and a placeholder for the rest. Upstream
    used to export only `<element>__<group>`, so every element's material was
    unknown and Layer 3 could only be one placeholder holding the whole domain.
    Since 2026-08-31 it also exports `<element>__<material>__<group>`, and that
    IS the material layer -- real resolution where this model had a stand-in.

    Both arrive in the same folder, and an element can be in both: `Fe__Motors`
    is all the iron, `Fe__esteel__Motors` the part of it in electrical steel.
    So the aggregate is the element's TOTAL, not a sibling of its parts, and
    adding both would count the resolved part twice.

    Hence: each resolved material holds what was exported for it, and the
    placeholder holds `total - what the materials account for`, per element.
    An element upstream resolves fully leaves nothing there; one it does not
    resolve at all is entirely there, exactly as before.

    THIS GENERALISES THE OLD SHAPE RATHER THAN REPLACING IT
    -------------------------------------------------------
    With no `<element>__<material>__<group>` files the placeholder comes out at
    1.0 of the domain and every element is a share of it -- the same rows, to
    the bit, as before this function existed. `tests/test_generality.py` pins
    that: the same fixture read with and without the material files agrees on
    every share it had before.

    WHAT IS DELIBERATELY NOT DONE
    -----------------------------
    A material's own mass is not exported, so it is the sum of the elements
    exported for it -- which makes those elements sum to exactly 1 within it,
    with no remainder. The mass of that material which upstream does not
    resolve into elements is therefore not inside it; it stays in the domain
    and reaches the placeholder, or `src/rest.py`, as unresolved. Attributing
    it to the material would mean inventing how much of it there is.
    """
    resolved: dict[str, dict[str, float]] = {}
    aggregate: dict[str, float] = {}
    for child, mass in here.items():
        if len(child) == 1:
            aggregate[child[0]] = mass
        else:
            element, material = child
            resolved.setdefault(material, {})[element] = mass

    placed: dict[str, float] = {}
    for parts in resolved.values():
        for element, mass in parts.items():
            placed[element] = placed.get(element, 0.0) + mass

    # What is left of each element once its resolved materials have taken
    # their share. Negative means the parts claim more than the whole.
    loose: dict[str, float] = {}
    for element, mass in sorted(aggregate.items()):
        left = mass - placed.get(element, 0.0)
        if left < -PARTS_TOLERANCE * mass:
            raise UpstreamError(
                f'{element} in {domain}: the materials it is resolved into hold '
                f'{placed[element]:,.6g},\nwhich is more than the '
                f'{mass:,.6g} exported for {element} itself. One of the two is\n'
                f'from a different run, or the resolution counts something twice.')
        if left > 0:
            loose[element] = left

    material_total = {material: sum(parts.values())
                      for material, parts in resolved.items()}
    outside = domain_total - sum(material_total.values())

    rows = []
    for material in sorted(material_total):
        rows.append({**base, 'Layer 3': material, 'Layer 4': '',
                     'Value': material_total[material] / domain_total,
                     'parameterCode': 'm-c'})
        for element, mass in sorted(resolved[material].items()):
            rows.append({**base, 'Layer 3': material, 'Layer 4': element,
                         'Value': mass / material_total[material],
                         'parameterCode': 'e-m'})

    # The placeholder is emitted when it has something to hold, and when
    # nothing was resolved at all -- which is the old shape, and where it comes
    # out at 1.0. When the materials cover the domain and every element sits in
    # one, it is not emitted and Layer 3 is entirely real.
    if not loose and material_total:
        return rows

    if loose and outside <= 0:
        raise UpstreamError(
            f'{domain}: its resolved materials already account for the whole '
            f'domain mass,\nyet {len(loose)} element(s) are exported outside '
            f'them ({", ".join(sorted(loose))}).\nThere is no room left for '
            f'them, so the arrays disagree about how big {domain} is.')

    material = f'{domain}{material_suffix}'
    rows.append({**base, 'Layer 3': material, 'Layer 4': '',
                 'Value': max(outside, 0.0) / domain_total,
                 'parameterCode': 'm-c'})
    for element, mass in sorted(loose.items()):
        rows.append({**base, 'Layer 3': material, 'Layer 4': element,
                     'Value': mass / outside, 'parameterCode': 'e-m'})
    return rows


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
        # SAY WHAT WAS ASKED FOR AND NOT DELIVERED. `run.years` selects from the
        # years upstream exported, so a wider request comes back quietly shorter.
        missing = years_not_exported(years, params.run.years)
        if missing:
            print(f'            run.years asks for {len(missing) + len(keep_years)} '
                  f'years; upstream exported {len(keep_years)} of them.')
            shown = ', '.join(str(y) for y in missing[:8])
            if len(missing) > 8:
                shown += f', ... and {len(missing) - 8} more'
            print(f'            NOT IN THIS RUN: {shown}')
            print(f'            To get them, add them to '
                  f'materials.bev_electronics_element_draws_years')
            print(f'            upstream and re-run that stage.')
        one = len(described['products']) == 1
        for year, by_product in report.items():
            whole = sum(v for totals in by_product.values() for v in totals.values())
            print(f'            {year}: {whole:,.4g} kt', end='' if one else '\n')
            for product, totals in sorted(by_product.items()):
                label = '' if one else f'              {product:<10s}'
                print(f'{label}  '
                      + '  '.join(f'{d} {v:,.4g}' for d, v in sorted(totals.items())))

    return {'inputs': inflow, 'composition': composition}
