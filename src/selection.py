"""
src/selection.py
================

Choosing the rows that belong to one year, scenario, location and
additionalSpecification.

WHY THIS IS ITS OWN MODULE
--------------------------
Both engines did this, separately, and did it differently -- DEFECTS.md 2.4.
The optimized engine compared for equality. The LA engine used substring
matching:

    str(year_target) in year_data
    df['Scenario'].str.contains(scenario)          # regex still enabled

so scenario 'BAU' also selected 'BAU_high', year '2020' also selected '12020',
and a scenario name containing a regex metacharacter either raised or matched
something unintended. On a table holding several scenarios, the LA engine
quietly mixed them.

One implementation, used by both, is the fix. Two copies of a selection rule
is how they came apart in the first place.

THE RULE
--------
Exact equality on scenario, location and additionalSpecification. Years are
equal, or fall inside a range written as '2020-2030' -- on either side, since
either the data or the request may be the range.

A column that exists but is empty everywhere does not filter at all: that is
how a table with no scenario dimension is read against a request that names
one.
"""
from __future__ import annotations

import pandas as pd

SELECTORS = ('Year', 'Scenario', 'Location', 'additionalSpecification')


def is_year_match(year_data, year_target) -> bool:
    """
    True when a row's year matches the year being solved.

    Equality, plus ranges written as '2020-2030' on either side. Note this is
    string equality: '2020' does not match '12020', which substring matching
    got wrong.
    """
    year_target = str(year_target)
    year_data = str(year_data)
    if year_data == year_target:
        return True

    if '-' in year_data:
        start, end = map(int, year_data.split('-'))
        if start <= int(year_target) <= end:
            return True

    if '-' in year_target:
        start, end = map(int, year_target.split('-'))
        if start <= int(year_data) <= end:
            return True

    return False


def scenarios_in(frame: pd.DataFrame) -> list[str]:
    """The distinct scenario names a table declares, ignoring blanks."""
    if 'Scenario' not in frame.columns:
        return []
    return sorted({str(value).strip() for value in frame['Scenario']
                   if str(value).strip()})


def chosen_scenario(inflows: pd.DataFrame, setting: str) -> str | None:
    """
    The one scenario this run solves, or None when there is no scenario
    dimension at all.

    One run is one scenario. Where the data holds several and the setting names
    none, that is refused rather than guessed: running all of them silently is
    what produced output files that overwrote each other.
    """
    from src.validate_inputs import InputDataError

    available = scenarios_in(inflows)
    setting = (setting or '').strip()

    if not available:
        if setting:
            raise InputDataError(
                f"scenario is set to {setting!r} in src/params_schema.py, but "
                f"inputs.csv has no Scenario column. Clear the setting, or add "
                f"the column.")
        return None

    if not setting:
        raise InputDataError(
            f"inputs.csv declares {len(available)} scenario(s): "
            f"{', '.join(available)}.\n"
            f"One run is one scenario. Set `scenario` in src/params_schema.py "
            f"to the one you want, and run the others separately -- comparing "
            f"them is analysis done afterwards on the output files.")

    if setting not in available:
        raise InputDataError(
            f"scenario is set to {setting!r} in src/params_schema.py, but "
            f"inputs.csv declares only: {', '.join(available)}. A name that "
            f"matches nothing would solve an empty system and report it as a "
            f"result.")

    return setting


def years_in(frame: pd.DataFrame) -> list[str]:
    """The distinct years a table declares, ignoring blanks, in order."""
    if 'Year' not in frame.columns:
        return []
    found = {str(value).strip() for value in frame['Year'] if str(value).strip()}

    def order(value: str):
        # '2020' sorts numerically; '2020-2030' sorts by its start.
        head = value.split('-')[0]
        return (0, int(head)) if head.isdigit() else (1, value)

    return sorted(found, key=order)


def chosen_years(inflows: pd.DataFrame, setting: str) -> list:
    """
    The years this run solves.

    Four forms, since real inflow data is annual and usually more years than
    anyone wants to look at:

        ''               every year in the data
        '2030'           that one year
        '2030-2050'      every year in that range, both ends included
        '2030-2050,10'   every 10th year of that range: 2030, 2040, 2050
        ',10'            every 10th year of the whole data

    The step counts from the first selected year, so ',10' on 2020-2070 gives
    2020, 2030 ... 2070 rather than an offset series. Years the data does not
    have are skipped rather than invented -- the step selects from what is
    there.

    Unlike the scenario, several years in one run is normal: they are
    independent, but a result usually wants the trajectory. Narrowing matters
    for the Monte Carlo, where 200,000 draws x 96 years is the memory problem
    in DESIGN_monte_carlo.md section 2 -- and a step is the form that keeps the
    shape of the trajectory while cutting its size.
    """
    from src.validate_inputs import InputDataError

    available = years_in(inflows)
    setting = str(setting or '').strip()

    if not available:
        if setting:
            raise InputDataError(
                f"years is set to {setting!r} in src/params_schema.py, but "
                f"inputs.csv has no Year column. Clear the setting, or add the "
                f"column.")
        return [None]

    span, _, step_text = setting.partition(',')
    span, step_text = span.strip(), step_text.strip()

    step = 1
    if step_text:
        if not step_text.isdigit() or int(step_text) < 1:
            raise InputDataError(
                f"years is set to {setting!r} in src/params_schema.py, but "
                f"{step_text!r} is not a step. Write a whole number above zero, "
                f"as in '2030-2050,10' or ',10'.")
        step = int(step_text)

    matched = available if not span else [
        year for year in available if is_year_match(year, span)]

    if not matched:
        raise InputDataError(
            f"years is set to {setting!r} in src/params_schema.py, but "
            f"inputs.csv has no year matching {span!r}. Available: "
            f"{available[0]} to {available[-1]} ({len(available)} years).\n"
            f"Write a single year such as '2030', a range such as '2030-2050', "
            f"or a range with a step such as '2030-2050,10'.")

    if step == 1:
        return matched

    # Step by year value rather than by position, so a gap in the data does not
    # shift everything after it.
    first = int(str(matched[0]).split('-')[0])
    stepped = [year for year in matched
               if str(year).split('-')[0].isdigit()
               and (int(str(year).split('-')[0]) - first) % step == 0]

    if not stepped:
        raise InputDataError(
            f"years is set to {setting!r} in src/params_schema.py, but a step "
            f"of {step} starting at {first} selects none of the years present.")

    return stepped


def _active(frame: pd.DataFrame, column: str) -> bool:
    """Whether a column exists and actually holds values worth filtering on."""
    return column in frame.columns and frame[column].dropna().astype(bool).any()


def select(frame: pd.DataFrame, year=None, scenario=None, location=None,
           additional_specification=None, *, drop: bool = True) -> pd.DataFrame:
    """
    The rows of `frame` belonging to one combination.

    Args:
        drop: remove the selector columns afterwards. The optimized engine
            wants them gone; pass False to keep them.
    """
    everything = pd.Series(True, index=frame.index)

    matches = everything
    if _active(frame, 'Year') and year:
        matches &= frame['Year'].apply(lambda value: is_year_match(value, year))
    if _active(frame, 'Scenario') and scenario:
        matches &= frame['Scenario'] == scenario
    if _active(frame, 'Location') and location:
        matches &= frame['Location'] == location
    if _active(frame, 'additionalSpecification') and additional_specification:
        matches &= frame['additionalSpecification'] == additional_specification

    selected = frame.loc[matches]
    return selected.drop(columns=list(SELECTORS), errors='ignore') if drop else selected
