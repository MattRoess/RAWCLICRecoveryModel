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
