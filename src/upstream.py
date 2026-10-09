"""
src/upstream.py
===============

**Copyright notice:** Copyright © 2026 Empa, Matthias Roesslein

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


def source_dir(params, folder: str = '', chemistry: str = '') -> str:
    """
    Where the draws for this case's scenario live.

    A case may rename the run's scenario to the folder its own upstream stage
    wrote -- `scenario_alias` in its source.csv, see src/source.py. Without one
    the run's name is the folder's name, which is how every case worked before
    2026-09-17 and how they all work again once upstream agrees on the names.

    `chemistry` adds the level an export written per chemistry has between the
    export and the scenario: `<upstream_dir>/<chemistry>/<scenario>`.
    """
    from src import source as source_module
    described = source_module.read(folder, params) if folder else {}
    upstream_dir = (described['upstream_dir'] if folder
                    else params.data.inflow_draws_dir)

    scenario = params.run.scenario or 'BAU'
    alias = described.get('scenario_alias') or {}
    if alias:
        scenario = alias.get(params.run.scenario, alias.get('*', scenario))

    return os.path.normpath(os.path.join(
        params.data.upstream_root, upstream_dir, *([chemistry] if chemistry else []),
        scenario))


def source_dirs(params, folder: str) -> list[str]:
    """
    Every folder this case's draws for the run's scenario are read from.

    One for an ordinary case. For a case that names `chemistries` (src/source.py)
    one per chemistry that HAS the scenario: sodium is exported for S2 and S3 and
    not for S1, and a chemistry absent from a scenario is simply not there, which
    is different from a chemistry whose folder is missing altogether -- that is
    reported by `check_chemistries`.
    """
    from src import source as source_module
    described = source_module.read(folder, params)
    if not described['chemistries']:
        return [source_dir(params, folder)]

    # THE EXPORT ITSELF IS NOT THERE: a different fault from a scenario it lacks, and the
    # first one anybody meets -- a case that reads an export written per chemistry cannot
    # run until the upstream stage has written it, and "none of the chemistries has the
    # scenario" would send the reader looking at the wrong setting.
    root = os.path.normpath(os.path.join(params.data.upstream_root, described['upstream_dir']))
    if not os.path.isdir(root):
        raise UpstreamError(
            f'The export {root} does not exist.\n'
            f'It is `upstream_dir` ({described["upstream_dir"]}) in the source table of '
            f'{folder}, below the upstream root. The upstream stage that writes it has not been '
            f'run since the export became one folder per chemistry, or `upstream_dir` is wrong.')

    found = [path for path in (source_dir(params, folder, chemistry)
                               for chemistry in described['chemistries'])
             if os.path.isdir(path)]
    if not found:
        wanted = ', '.join(source_dir(params, folder, chemistry)
                           for chemistry in described['chemistries'])
        raise UpstreamError(
            f'No upstream draws at {wanted}.\n'
            f'None of the chemistries {", ".join(described["chemistries"])} that '
            f'{folder} names has the scenario {params.run.scenario or "BAU"!r}. '
            f'`chemistries` in its source table says which folders it reads; '
            f'`run.scenario` says which scenario.')
    return found


def scenarios_available(params, folder: str) -> list[str]:
    """
    Every scenario this case's upstream export holds, in name order.

    Empty when the case has no scenario dimension to speak of: not an upstream
    case, no export directory, or a `scenario_alias` sending every name to one
    folder -- which is how the electronics declare that their draws are one set
    however they are asked for.
    """
    if not is_upstream_case(params, folder):
        return []
    from src import source as source_module

    described = source_module.read(folder, params)
    if described.get('scenario_alias'):
        return []

    root = os.path.normpath(os.path.join(params.data.upstream_root,
                                         described['upstream_dir']))
    if not os.path.isdir(root):
        return []
    # An export written per chemistry has the scenarios one level down, inside
    # each chemistry the case names; the case runs every scenario ANY of them has.
    roots = ([os.path.join(root, chemistry) for chemistry in described['chemistries']]
             if described['chemistries'] else [root])
    return sorted({name for base in roots if os.path.isdir(base)
                   for name in os.listdir(base)
                   if not name.startswith('.')
                   and os.path.isdir(os.path.join(base, name))})


def offers_scenario(params, folder: str) -> bool:
    """
    Whether this case can be solved for `params.run.scenario`.

    A case with no scenario dimension -- the electronics, whose draws are one set
    however they are asked for, or a case that is not fed from upstream -- answers
    every scenario. A case that HAS scenarios answers only the ones it has, and
    asking for none answers any.

    Added 2026-10-09 for `05_combine_cases.py`. The battery is five cases, and
    sodium has no S1 while solid-state has neither S1 nor S2, so an S1 pass that
    reached sodium was refused and took the whole run with it. Now the case is
    left out of that pass, with a line saying so, as a case that cannot carry the
    metal already was.
    """
    scenario = (params.run.scenario or '').strip()
    if not scenario:
        return True
    available = scenarios_available(params, folder)
    return not available or scenario in available


def cases_to_run(params) -> list[str]:
    """
    Which cases a stage covers. Every numbered stage asks this.

    A RUN THAT NAMES SEVERAL CASES DOES ALL OF THEM. `run.data_folder` reads
    one folder or several separated by semicolons, exactly as `groups` and
    `scenario_alias` do in a case's own source table:

        data_folder = 'data/battery'
        data_folder = 'data/bev_electronics_wiring; data/bev_electronics_boards'

    Asked for 2026-09-25: four traction motor cases had to be run by editing
    the setting between each one, which is four edits and four presses to
    answer one question. Scenarios already worked this way -- "a case set up as
    scenarios runs as all of them" -- and there was no reason cases did not.

    ⚠️ ONE PASS IS STILL ONE CASE. Nothing here solves two at once. The stage
    sets `run.data_folder` to the current one inside its loop, the same way it
    already sets `run.scenario`, so everything downstream sees a single case
    and needs no change.
    """
    raw = (params.run.data_folder or '').strip()
    return [part.strip() for part in raw.split(';') if part.strip()]


def scenarios_to_run(params, folder: str, named=None) -> list[str]:
    """
    Which scenarios a stage covers. Every numbered stage asks this.

    A CASE THAT IS SET UP AS SCENARIOS RUNS AS ALL OF THEM. The battery is
    exported as S1, S2 and S3 and no single one of them is the answer, so
    pressing Run on 01, 02, 03 or 04 does the whole set. `run.scenario` narrows
    it to one; a case with no scenario dimension gives one pass with the setting
    as it stands, exactly as before.

    `named` is what `--scenario` used to fill. The stages take no arguments now
    and none of them passes it -- it is left here as the override hook, not as
    something any run uses.

    One pass is still one scenario. Nothing here solves two at once -- that is
    deliberate and DESIGN_monte_carlo.md section 2 says why. This decides how
    many passes a command makes, not what a pass does.
    """
    if named:
        return list(named)
    if (params.run.scenario or '').strip():
        return [params.run.scenario]
    return scenarios_available(params, folder) or ['']


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
    # WHERE years.npy SITS DEPENDS ON THE STAGE THAT WROTE IT. 04_02 writes one
    # at the scenario root for all three flows; 04_04 writes one inside each
    # flow folder beside the arrays it describes. Both are the same 11 or 51
    # years -- checked on the battery export 2026-09-17, all nine identical --
    # so this looks beside the arrays first and falls back to the root. Reading
    # only the root is why the battery case could never be run.
    years_path = os.path.join(folder, flow, 'years.npy')
    if not os.path.exists(years_path):
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
        if stem == 'years':
            continue                   # the 04_04 layout keeps it beside the arrays
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


def sum_draws(parts: list[tuple], labels: list[str]):
    """
    Several chemistries' draws added array by array: the mix a recycler receives.

    `parts` are the `(years, domain_mass, element_mass)` that `read_draws` gave
    for each chemistry. A file one chemistry has and another lacks counts as
    zero in the other -- LFP has no nickel, sodium has no cobalt -- so the sum
    holds every name any of them has. One chemistry is returned as it came, still
    memory-mapped: only a real sum is read into memory, and only the arrays that
    need adding.

    Refused if they disagree about the YEARS or the NUMBER OF DRAWS. Draw i has
    to be the same world in every chemistry or the sum is not a fleet; the
    check is the one `one_run` makes inside a folder, one level up.
    """
    if len(parts) == 1:
        return parts[0]

    years = parts[0][0]
    for (other, _, _), label in zip(parts[1:], labels[1:]):
        if not np.array_equal(years, other):
            raise UpstreamError(
                f'{labels[0]} exports the years {years.tolist()} and {label} '
                f'exports {np.asarray(other).tolist()}.\nThey cannot be added '
                f'year by year. Re-run the upstream stage so that both agree.')

    widths: dict[int, list[str]] = {}
    for (_, domains, _), label in zip(parts, labels):
        widths.setdefault(next(iter(domains.values())).shape[0], []).append(label)
    one_run(labels[0], widths)

    domain_mass: dict = {}
    element_mass: dict = {}
    for (_, domains, elements), label in zip(parts, labels):
        for total, found in ((domain_mass, domains), (element_mass, elements)):
            for key, array in found.items():
                total[key] = total[key] + array if key in total else array
    return years, domain_mass, element_mass


def _claims(params, folder: str, upstream_dir: str) -> dict[str, list[str]]:
    """
    {chemistry: [cases that name it]} among the case folders beside this one.

    ALL the cases in the project that read this export, not only the ones in
    the current run: a run may name a single case, and the others still treat
    their chemistries. Read from each case's source table directly -- one
    unreadable folder must not stop the check of the rest.
    """
    from src import case_tables

    parent = os.path.dirname(os.path.normpath(folder)) or '.'
    wanted = os.path.normpath(upstream_dir)
    claims: dict[str, list[str]] = {}
    for name in sorted(os.listdir(parent)):
        candidate = os.path.join(parent, name)
        if not os.path.isdir(candidate):
            continue
        try:
            if not case_tables.exists(candidate, 'source'):
                continue
            frame = case_tables.read(candidate, 'source')
        except Exception:
            continue
        stated = {str(k).strip(): str(v).strip()
                  for k, v in zip(frame.get('key', []), frame.get('value', []))}
        here = os.path.normpath(stated.get('upstream_dir', params.data.inflow_draws_dir))
        if here != wanted:
            continue
        for chemistry in (c.strip() for c in stated.get('chemistries', '').split(';')):
            if chemistry:
                claims.setdefault(chemistry, []).append(candidate)
    return claims


def check_chemistries(params, folder: str, described: dict, quiet: bool = False) -> None:
    """
    Refuse an export that holds a chemistry no case treats, or treats twice.

    ⚠️ THE EXPORT DOES NOT SAY WHAT TO DO WITH A CHEMISTRY; A CASE DOES. If a new
    grade turns up upstream (an NMC with less nickel, say), nothing in the
    recovery model has a road for it: its mass would enter no total, and every
    figure would balance, plot and be short by exactly that much. So a chemistry
    folder that no case claims STOPS the run and is named, together with what
    to do. The treatment has to be written -- by whoever knows how that
    chemistry is recycled -- before a number is reported.

    Added 2026-10-08, asked for in so many words: *"if one of the two shows up in
    future inputs, the user is warned and the respective treatment has to be
    there."*

    Also refused: a chemistry claimed by two cases, which would be counted twice.
    Only a warning: a case naming a chemistry the export does not have, which is
    what a stale name or an export not yet re-run looks like.
    """
    root = os.path.normpath(os.path.join(params.data.upstream_root,
                                         described['upstream_dir']))
    present = sorted(name for name in os.listdir(root)
                     if not name.startswith('.')
                     and os.path.isdir(os.path.join(root, name))) \
        if os.path.isdir(root) else []
    claims = _claims(params, folder, described['upstream_dir'])

    unclaimed = [name for name in present if name not in claims]
    twice = {name: cases for name, cases in claims.items() if len(cases) > 1}
    if unclaimed or twice:
        lines = []
        if unclaimed:
            lines.append(
                f'{root} holds {len(unclaimed)} chemistry folder(s) that no case '
                f'treats: {", ".join(unclaimed)}.\n'
                f'Their mass would be left out of every total without a word. '
                f'Each needs a treatment:\n'
                f'  1. copy the case of the nearest chemistry and give it that '
                f'chemistry\'s coefficients,\n'
                f'  2. name the folder in its source table:  chemistries = '
                f'{unclaimed[0]}\n'
                f'  3. list the case in the study (`run.data_folder`, and '
                f'`combine.cases` for the combined figures).')
        for name, cases in sorted(twice.items()):
            lines.append(
                f'chemistry {name} is named by {len(cases)} cases '
                f'({", ".join(cases)}), so its mass would be counted '
                f'{len(cases)} times. Name it in one.')
        lines.append('Cases looked at: ' + (
            '; '.join(f'{", ".join(cases)} ({name})' for name, cases in sorted(claims.items()))
            or 'none'))
        raise UpstreamError('\n'.join(lines))

    if not quiet:
        absent = [name for name in described['chemistries'] if name not in present]
        for name in absent:
            print(f'WARNING   : {folder} names the chemistry {name}, but {root} '
                  f'has no such folder -- stale name, or an export not yet re-run.')


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

    Means over draws, for the DETERMINISTIC answer: the arithmetic is linear in
    the inflow, so a run built on means is the honest central case.

    The spread is carried separately, by `Draws` below -- which until
    2026-09-03 it was not. This docstring claimed it was while `solve_draws`
    broadcast the mean across every draw, so every interval in the project was
    coefficient uncertainty only and too narrow by the inflow's own spread.

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

    # A case that treats chemistries is checked against the whole export FIRST:
    # a chemistry no case claims has to stop the run before anything is read.
    if described['chemistries']:
        check_chemistries(params, folder, described, quiet)

    sources = source_dirs(params, folder)
    source = sources[0]

    # One folder per product. The arrays are memory-mapped, so holding all five
    # drivetrains open at once costs file handles, not memory -- what grows is
    # the number of ROWS, and through them the Monte Carlo's array.
    #
    # A case that names several chemistries reads each one's folder and ADDS
    # them (`sum_draws`); one chemistry, or none, is returned as it was read.
    per_product, years = {}, None
    for product in described['products']:
        flow = source_module.flow_for(described, product)
        years, domain_mass, element_mass = sum_draws(
            [read_draws(path, flow, described['group_marker']) for path in sources],
            [os.path.relpath(path) for path in sources])
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

    # THE SCENARIO IS PART OF THE DATA, NOT JUST PART OF THE PATH. It used to
    # choose the folder the draws were read from and was then thrown away, so
    # the frames this builds had no Scenario column -- and `chosen_scenario`
    # refuses a run whose setting names a scenario the data does not carry.
    # `run.scenario` was therefore unusable for every upstream case, which in
    # turn meant the per-scenario output folder (`output_path`) and the
    # per-scenario figure folder could never fire and three scenarios wrote
    # over each other. The battery is the first case with more than one.
    scenario = (params.run.scenario or '').strip()
    if scenario:
        inflow['Scenario'] = scenario
        composition['Scenario'] = scenario

    if not quiet:
        span = (f'{keep_years[0]}' if len(keep_years) == 1
                else f'{keep_years[0]}-{keep_years[-1]} ({len(keep_years)} years)')
        if len(sources) > 1:
            print(f'Upstream  : {os.path.relpath(os.path.dirname(os.path.dirname(source)))}'
                  f'/{{{", ".join(os.path.basename(os.path.dirname(s)) for s in sources)}}}'
                  f'/{os.path.basename(source)}   (added per draw)')
        else:
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

    return {'inputs': inflow, 'composition': composition,
            'draws': Draws(per_product, years, described['child_layer'],
                           described['inflow_flow_id'], draws, source=source,
                           group_marker=described['group_marker'],
                           sources=tuple(sources))}


class Draws:
    """
    The upstream arrays, kept so the Monte Carlo can use the DRAWS themselves.

    WHY THIS EXISTS. `build` above reduces every array to its mean, and until
    2026-09-03 that mean was all the model ever saw: `solve_draws` broadcast one
    number across every draw, so every interval in every figure was coefficient
    uncertainty ONLY. The inflow spread is not small beside it -- copper
    collected in 2070 is 516 kt with a 95% interval of 388 to 670 -- so leaving
    it out made every published interval too narrow.

    Held rather than expanded: one year of one case at 200,000 draws is 100 MB,
    and every year of the car-composition case at once would be 10 GB. The
    arrays are memory-mapped and a block of draws for one year is cut from them
    on demand, inside the loop that already walks blocks.

    ONLY THE `material` SHAPE. All three cases are material-keyed, and there the
    parent's mass and the child's are each one exported array. The `element`
    shape resolves Layer 3 out of overlapping exports -- an element's total and
    the parts of it inside named materials -- and reproducing that per draw
    means reproducing `_material_and_element_rows` exactly. Until a case needs
    it, that shape keeps the old behaviour and `propagates` says so, rather
    than a second implementation drifting from the first.
    """

    def __init__(self, per_product, years, child_layer, flow_id, draws,
                 source: str = '', group_marker: str = '__domain__',
                 sources: tuple[str, ...] = ()):
        self.source = source
        # Every folder the arrays came from. One, unless the case adds several
        # chemistries; `other_flow` reads another flow from each of them.
        self.sources = tuple(sources) or ((source,) if source else ())
        self.per_product = per_product
        self.years = years
        self.child_layer = child_layer
        self.flow_id = flow_id
        self.draws = draws
        # How the export spells "the group itself" -- `__domain__` for 04_02,
        # `__component__` for 04_03. Needed by `other_flow`, which has to build
        # a file name for a flow it did not load.
        self.group_marker = group_marker
        self._means: dict[tuple, float] = {}

    @property
    def resolves_materials(self) -> bool:
        """Whether any exported array names a material as well as an element."""
        return any(len(child) > 1
                   for _, elements in self.per_product.values()
                   for child, _ in elements)

    @property
    def propagates(self) -> bool:
        """
        Whether this case's shares can be reproduced per draw.

        The `material` shape always can: the parent's mass and the child's are
        each one exported array.

        The `element` shape can too, 2026-09-17, AS LONG AS THE EXPORT NAMES NO
        MATERIALS. Layer 3 is then a placeholder for the whole component -- the
        battery's is its component's own name, the synthetic panel's carries
        `material_suffix` -- so the middle level is an identity and the elements
        hang off the component directly. Nothing has to be resolved out of
        overlapping exports and `_material_and_element_rows` is not reproduced.

        AN ELEMENT-KEYED CASE THAT DOES NAME MATERIALS STILL CANNOT. There the
        placeholder is the part of the component NOT inside a named material --
        an element's total minus the parts of it that were resolved -- and
        getting that right per draw means reproducing that function exactly.
        The first case that needs it should do that, not this property.
        """
        if self.child_layer == 'material':
            return True
        return self.child_layer == 'element' and not self.resolves_materials

    def _at(self, array, year, start, stop) -> np.ndarray:
        index = int(np.searchsorted(self.years, int(year)))
        return np.asarray(array[start:stop, index], dtype=np.float64)

    def inflow(self, product: str, year, domains, start: int, stop: int) -> np.ndarray:
        """
        That product's collected mass, per draw, in the ARRAYS' unit.

        OVER THE DOMAINS THE CASE ACTUALLY KEEPS, which the caller takes from
        the composition frame. The export folder holds every domain 04_02
        wrote -- Wiring, Motors, PCB and Sensors -- while a case keeps the ones
        its `groups` setting names. Summing all four made the whole 1.3% too
        big, so every component share came out too small and the two no longer
        summed to 1.
        """
        domain_mass, _ = self.per_product[product]

        # NO DOMAIN KEPT IS A YEAR WITH NO MASS, not a failure. The caller reads the
        # domains off the composition table, and the table has no row for a product in
        # a year in which the export holds nothing of it -- a chemistry that starts
        # late, solid-state in S3 before 2040. That year is zero, and what was here
        # returned None, which stopped the Monte Carlo at `.mean()` on the first
        # real export that had one (2026-10-08).
        if not len(domains):
            return np.zeros(stop - start)

        total = None
        for domain in domains:
            array = domain_mass.get(domain)
            if array is None:
                continue
            piece = self._at(array, year, start, stop)
            total = piece if total is None else total + piece

        # DOMAINS NAMED AND NONE OF THEM IN THE EXPORT is the other way to arrive with
        # nothing, and it is a different thing: the table and the arrays are meant to
        # list the same components. Said in words, not left to fail further on.
        if total is None:
            raise UpstreamError(
                f'The composition names {", ".join(str(d) for d in domains)} for {product} '
                f'in {year}, and the export holds an array for none of them. The table '
                f'and the arrays should list the same components.')
        return total

    def mean_inflow(self, product: str, year, domains) -> float:
        """
        The same total over every draw -- what `build` wrote into the table.

        Used to put the draws into the table's unit. The arrays are kilotonnes
        and the model works in kilograms (`run.working_unit`), a factor of a
        million, and the conversion happens on load where these arrays cannot
        see it. Scaling by `stated / this` needs no unit knowledge at all and
        makes the mean of the draws equal the number the deterministic run uses,
        by construction rather than by coincidence.
        """
        key = (product, str(year), tuple(domains))
        if key not in self._means:
            self._means[key] = float(
                self.inflow(product, year, domains, 0, self.draws).mean())
        return self._means[key]

    def other_flow(self, flow: str, resource: str, domains, year,
                   start: int, stop: int) -> np.ndarray | None:
        """
        One resource's mass in ANOTHER of the upstream flows, per draw.

        The export writes `inflow`, `outflow` and `collected` side by side, all
        with the same file names. The model solves only the flow its case names
        -- what reaches a recycler -- but `inflow` and `outflow` answer what
        entered and left the fleet, and outflow minus collected is the part
        nobody collected at all. Read here FOR REPORTING; nothing about the
        solve changes.

        In the arrays' own unit. The caller scales, the same way it does for the
        inflow, because only the caller knows what the table was written in.
        """
        if not self.sources:
            return None
        total = None
        for domain in domains:
            for base in self.sources:
                path = self._other_path(flow, resource, domain, base)
                if path is None:
                    continue
                piece = self._at(np.load(path, mmap_mode='r'), year, start, stop)
                total = piece if total is None else total + piece
        return total

    def _other_path(self, flow: str, resource: str, domain: str,
                    base: str | None = None) -> str | None:
        """
        The file holding one resource's mass in `flow`, or None.

        `<resource>__<domain>.npy` is the usual spelling: an element inside a
        component, `Cu__PCB.npy`.

        ⚠️ A RESOURCE CAN BE THE COMPONENT ITSELF, and then there is no such
        file. 04_03 exports copper, aluminium, lamination and steel as
        COMPONENTS -- that is where the recycling routes act, decided
        2026-09-24 -- so copper's array is `__component____copper.npy` and
        `copper__copper.npy` was never written. Asked the old way, every
        traction motor resource came back None from every flow, and with it the
        whole-account figures: no account, no losses, no trapped, no fate,
        drawn for the battery and the electronics but not here.

        Falling back to the group's own array is the same rule `mass` applies
        one layer up (`if not layer3: domain_mass.get(layer2)`): when the thing
        asked for IS the group, the group's array is the answer.
        """
        base = self.source if base is None else base
        named = os.path.join(base, flow, f'{resource}__{domain}.npy')
        if os.path.exists(named):
            return named
        if resource != domain:
            return None
        whole = os.path.join(base, flow,
                             f'{self.group_marker}__{domain}.npy')
        return whole if os.path.exists(whole) else None

    def mass(self, product: str, year, layer2: str, layer3: str,
             start: int, stop: int, layer4: str = '') -> np.ndarray | None:
        """
        One composition row's own mass per draw, or None if it is not exported.

        Three levels, because an element-keyed case has three: the component,
        the material inside it, and the element inside that. A material-keyed
        case fills only the first two and `layer4` stays blank, which is the
        call this had before and the same two lookups it did.
        """
        domain_mass, element_mass = self.per_product[product]
        if not layer3:
            array = domain_mass.get(layer2)
            return None if array is None else self._at(array, year, start, stop)

        if not layer4:
            array = element_mass.get(((layer3,), layer2))
            if array is not None:
                return self._at(array, year, start, stop)
            # A PLACEHOLDER MATERIAL IS NOT EXPORTED, because it is not a
            # material -- it is the part of the component upstream did not
            # resolve into one. `propagates` only allows the element shape when
            # nothing was resolved, so here it is the whole component.
            if self.child_layer == 'element':
                array = domain_mass.get(layer2)
                return None if array is None else self._at(array, year, start, stop)
            return None

        array = element_mass.get(((layer4,), layer2))
        return None if array is None else self._at(array, year, start, stop)
