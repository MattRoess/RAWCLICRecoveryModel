"""
src/case_tables.py
==================

Where a case's three tables live, and how to read them.

WHY A WORKBOOK
--------------
`source`, `processes` and `TCs` describe one case and are edited together, by a
person, by hand. Three separate CSVs make that harder than it needs to be: no
dropdown to stop a flow name being mistyped, no room for a note beside a
number, and three files to keep consistent with each other.

So a case may carry a single `input_data/case.xlsx` with one sheet per table.
The workbook is the input -- there is no export step and no second copy, because
two copies of one table, one generated from the other, is exactly the drift this
project keeps finding.

CSV IS STILL READ
-----------------
A case with `source.csv`, `processes.csv` and `TCs.csv` works unchanged. The
reference fixtures under `data_folder/reference/` are CSV and stay that way:
every test suite runs on them, and converting the thing that proves the code
works would be a poor trade for tidiness.

A case may not have both for the same table. Two files of the same name with
different contents is precisely the situation where someone edits one and the
model reads the other.

EMPTY CELLS
-----------
A CSV read with `keep_default_na=False` gives `''` for a blank. Excel gives
`NaN`. The model reads `''` as "this layer is not populated" -- the whole
nesting rule depends on it -- so blanks are normalised here rather than in
every caller.
"""
from __future__ import annotations

import contextlib
import os
import warnings

import numpy as np
import pandas as pd

WORKBOOK = 'case.xlsx'

# Sheet name and CSV name are the same word, so a case reads the same either way.
TABLES = ('source', 'processes', 'TCs', 'TCs_improved')

# The coefficients an improved case ends at. Optional: a case without it does
# not change over time, which is every case built before 2026-09-03.
IMPROVED = 'TCs_improved'


@contextlib.contextmanager
def _quiet_workbook():
    """
    Open a workbook without openpyxl's data-validation warning.

    The case workbooks carry dropdowns on `source` and `processes` (added
    2026-08-26 so the vocabulary is offered rather than remembered). openpyxl
    cannot round-trip the extension those use and says so on EVERY open -- nine
    times in one Monte Carlo run, interleaved with the output that matters.

    Narrow on purpose: this filters that one message from that one library. A
    blanket filter here would also hide the pandas and numpy warnings that have
    twice been the first sign of a real defect in this project.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', category=UserWarning, module='openpyxl',
            message='Data Validation extension is not supported.*')
        yield

# What identifies one coefficient, so the two tables can be lined up row for
# row. Not src.mass_balance.RESOURCE: that leaves out Output_FlowID, because a
# resource is the thing split ACROSS the flows. Here a ROW is being matched.
COEFFICIENT = ['Input_FlowID', 'Input_layer', 'Input_layer_key',
               'Output_FlowID', 'TC_target_layer', 'TC_target_key']

# The three numbers that ramp. Everything else -- process, technology,
# is_residual -- is taken from the current table, because a coefficient that
# changed those would be a different coefficient rather than an improved one.
RAMPED = ['value_min', 'value', 'value_max']


class ImprovementError(ValueError):
    """Raised when a case's two coefficient tables do not describe one case."""


def _weight(year: int, start: int, end: int, after: str = 'hold') -> float:
    """
    How far along the improvement this year sits. 0 at `start`, 1 at `end`.

    FLAT BEFORE `start`, ALWAYS. Nothing improves before the year the case
    says improvement begins, so the weight is 0 there and the current table
    stands. `improvement_start` is the parameter that sets it, per case, in the
    source table.

    AFTER `end`, TWO ANSWERS, and the case picks:

        hold      the weight stops at 1 -- the improved table applies from
                  `end` onwards, unchanged
        continue  the weight keeps rising at the same rate, so 2070 is a third
                  of a ramp beyond a 2030-2060 window and the line does not go
                  flat at a year chosen for having a table

    ⚠️ `continue` EXTRAPOLATES, so a coefficient can in principle leave [0, 1]
    far enough out. Nothing here clamps it, on purpose: stage 01 checks every
    year the run will solve for `0 <= min <= mode <= max <= 1` and names the
    row that breaks it. A clamp would quietly bend one coefficient and leave
    its group summing to something other than 1, which is worse than being
    told the window is too short for the horizon.

    Sum-to-1 survives either way. Each year is `a + (b - a) * w`, and summing
    that over a group gives `1 + (1 - 1) * w = 1` for ANY weight -- the
    property does not need w to be between 0 and 1.
    """
    if year <= start:
        return 0.0
    if year >= end and after != 'continue':
        return 1.0
    return (year - start) / (end - start)


def ramp(current, improved, start: int, end: int, years,
         after: str = 'hold') -> "pd.DataFrame":
    """
    One coefficient table per year, on a straight line from current to improved.

    Before `start` the current numbers hold; between `start` and `end` each of
    value_min, value and value_max moves linearly; after `end` the case's
    `improvement_after_end` decides whether the improved numbers hold or the
    same rate of change carries on. See `_weight`. The result
    carries a `Year` column, which is all the rest of the model needs: both
    engines already select their rows by year
    (`select_df_by_year_scenario_location`), so nothing downstream changes.

    ONE DRAW STAYS ONE WORLD. A coefficient's random stream is keyed on which
    resource moves from where to where and NOT on the year
    (`src/sampling._stream_key`), so every year of one coefficient draws the
    same uniform. Draw 7 is therefore the same optimism about that process in
    2030 and in 2060, ramped -- not two unrelated guesses. Independent draws per
    year would invent a year-to-year wobble nobody measured.

    SUM-TO-1 SURVIVES BY CONSTRUCTION. Each year is `a + (b - a) * w` over two
    tables whose groups each sum to 1, and that sums to `1 + (1 - 1) * w = 1`
    whatever the weight -- so it holds for `continue` past the end of the
    window as well as inside it. Nothing has to be renormalised, and the groups
    are formed within a year, never across them.
    """
    missing = [column for column in COEFFICIENT if column not in current.columns]
    if missing:
        raise ImprovementError(f'the coefficient table has no {missing} column(s).')

    current = current.reset_index(drop=True)
    improved = improved.reset_index(drop=True)

    left = current[COEFFICIENT].astype(str).agg('|'.join, axis=1)
    right = improved[COEFFICIENT].astype(str).agg('|'.join, axis=1)
    only_current = sorted(set(left) - set(right))
    only_improved = sorted(set(right) - set(left))
    if only_current or only_improved:
        raise ImprovementError(
            f'{IMPROVED} must name exactly the coefficients {TABLES[2]} names.\n'
            + (f'  missing from {IMPROVED}: {len(only_current)}, first '
               f'{only_current[0]}\n' if only_current else '')
            + (f'  not in {TABLES[2]}: {len(only_improved)}, first '
               f'{only_improved[0]}\n' if only_improved else '')
            + '  Every coefficient appears in both, so that one edited in one\n'
              '  and not the other cannot become an unintended improvement.')

    for name, keys in ((TABLES[2], left), (IMPROVED, right)):
        repeated = keys[keys.duplicated()].unique()
        if len(repeated):
            raise ImprovementError(
                f'{name} names the same coefficient more than once, so the two '
                f'tables cannot be lined up row for row: {repeated[0]}')

    # Line the improved rows up with the current ones by identity, not by
    # position: the two sheets are edited by hand and a row moved in one of
    # them would otherwise ramp a coefficient towards a different coefficient.
    improved = improved.set_index(right).loc[left].reset_index(drop=True)

    numbers = {column: (pd.to_numeric(current[column], errors='coerce'),
                        pd.to_numeric(improved[column], errors='coerce'))
               for column in RAMPED
               if column in current.columns and column in improved.columns}
    group = (current[[c for c in GROUP if c in current.columns]]
             .astype(str).agg('|'.join, axis=1)
             if any(c in current.columns for c in GROUP) else None)

    blocks, held = [], {}
    for year in years:
        block = current.copy()
        weight = _weight(int(year), start, end, after)
        for column, (a, b) in numbers.items():
            # A SIMPLE LINEAR EXTRAPOLATION. Nothing caps the weight.
            mixed = a + (b - a) * weight
            # A blank bound is a definitional row with no range. Blank in either
            # table stays blank rather than becoming a number out of nowhere.
            block[column] = mixed.where(a.notna() & b.notna(), current[column])
        if weight > 1:
            block, capped = _hold_at_the_bounds(block, group, numbers)
            if capped:
                held[int(year)] = capped
        block['Year'] = str(year)
        blocks.append(block)
    if held:
        first = min(held)
        names = sorted({n for rows in held.values() for n in rows})
        print(f'  improvement extrapolated past {end}; '
              f'{len(names)} coefficient(s) reached 0 or 1 and were held '
              f'there from {first}; any group then summing above 1 was '
              f'set back to 1:')
        for name in names[:6]:
            print(f'    {name}')
        if len(names) > 6:
            print(f'    ... and {len(names) - 6} more')
    return pd.concat(blocks, ignore_index=True)


# The columns that make one sum-to-1 group: every coefficient moving the same
# resource out of the same flow. Stage 01 totals on exactly these.
GROUP = ['Input_FlowID', 'TC_target_layer', 'TC_target_key']


def _hold_at_the_bounds(block, group, numbers):
    """
    Past the window, a share that would leave [0, 1] is held at the bound.

    ⚠️ THE RULE, SET BY MATTHIAS ON 2026-09-29: *"if it is larger 1 then set it
    to 1 and document."* The same at the other end -- a share that would go
    negative is held at 0. A transfer coefficient is a share of what enters a
    flow; there is no such thing as 119% of it, or -3%.

    AND A GROUP THAT WOULD SUM ABOVE 1 IS SET TO 1. *"If it is larger than 1
    then set it to 1 and document."* A group of transfer coefficients is the
    whole of what leaves a flow, so its sum IS 1 -- 1.0267 of the magnet is not
    a pessimistic number, it is more magnet than there is.

    The group is divided by its own sum, and only when that sum is above 1.
    A group still summing to 1 or below is left exactly as the extrapolation
    put it; nothing is scaled up to reach 1.

    Returns the block and the names of the coefficients that were held, so the
    run can say so out loud rather than doing it silently.
    """
    columns = [c for c in ('value_min', 'value', 'value_max') if c in block.columns]
    if not columns:
        return block, []

    before = {c: pd.to_numeric(block[c], errors='coerce') for c in columns}
    after_clip = {c: v.clip(lower=0.0, upper=1.0) for c, v in before.items()}
    moved = np.zeros(len(block), dtype=bool)
    for c in columns:
        moved |= (before[c] - after_clip[c]).abs().gt(1e-12).fillna(False).to_numpy()

    for c in columns:
        block[c] = after_clip[c].where(before[c].notna(), block[c])

    # Set a group that now sums above 1 back to 1.
    if group is not None and 'value' in columns:
        mode = pd.to_numeric(block['value'], errors='coerce')
        total = mode.groupby(group).transform('sum')
        over = total.gt(1.0 + 1e-12)
        block['value'] = (mode / total).where(over & mode.notna(), block['value'])
        moved |= over.fillna(False).to_numpy()

    names = []
    if moved.any():
        have = [c for c in ('Input_FlowID', 'Output_FlowID', 'TC_target_key')
                if c in block.columns]
        if have:
            names = sorted(block.loc[moved, have].astype(str)
                           .agg(' -> '.join, axis=1).unique())
    return block, names


def coefficients(case: str, years, params=None) -> "pd.DataFrame":
    """
    The coefficient table this run should use: ramped if the case improves.

    A case with no TCs_improved sheet and no window gets exactly what it always
    got, unchanged and with no Year column.
    """
    from src import source as source_module

    current = read(case, 'TCs')
    has_improved = exists(case, IMPROVED)
    if params is None:
        from src.params_schema import current as settings
        params = settings()
    described = source_module.read(case, params)
    start, end = described.get('improvement_start'), described.get('improvement_end')

    if not has_improved and start is None:
        return current
    if has_improved and start is None:
        raise ImprovementError(
            f'{case} has a {IMPROVED} table but no improvement_start and '
            f'improvement_end in its source table, so nothing says WHEN it '
            f'improves.')
    if start is not None and not has_improved:
        raise ImprovementError(
            f'{case} sets improvement_start {start} and improvement_end {end} '
            f'but has no {IMPROVED} table, so nothing says WHAT improves.')

    return ramp(current, read(case, IMPROVED), start, end, years,
                described.get('improvement_after_end') or 'hold')


CSV_OPTIONS = dict(keep_default_na=False, na_values=[])


class CaseTableError(ValueError):
    """Raised when a case's tables cannot be located, or are offered twice."""


def workbook_path(case: str) -> str:
    return os.path.join(case, 'input_data', WORKBOOK)


def csv_path(case: str, table: str) -> str:
    return os.path.join(case, 'input_data', f'{table}.csv')



def _sheet_names(path: str) -> list[str]:
    from openpyxl import load_workbook
    with _quiet_workbook():
        book = load_workbook(path, read_only=True)
    try:
        return list(book.sheetnames)
    finally:
        book.close()


def where(case: str, table: str) -> tuple[str, str] | None:
    """
    ('xlsx', path) or ('csv', path) for one table, or None if it has neither.

    Raises when both exist: that is not a preference to resolve silently.
    """
    if table not in TABLES:
        raise CaseTableError(f'{table!r} is not one of {", ".join(TABLES)}')

    book, delimited = workbook_path(case), csv_path(case, table)
    in_book = os.path.exists(book) and table in _sheet_names(book)
    in_csv = os.path.exists(delimited)

    if in_book and in_csv:
        raise CaseTableError(
            f"{case} holds {table} twice: sheet '{table}' in {WORKBOOK}, and "
            f"{table}.csv beside it. Keep one -- otherwise the model reads a "
            f"table that may not be the one being edited.")

    if in_book:
        return ('xlsx', book)
    if in_csv:
        return ('csv', delimited)
    return None


def exists(case: str, table: str) -> bool:
    return where(case, table) is not None


def read(case: str, table: str, dtype=None) -> pd.DataFrame:
    """One of a case's tables, from whichever format it is kept in."""
    found = where(case, table)
    if found is None:
        raise CaseTableError(
            f'{case} has no {table}: expected sheet {table!r} in '
            f'{workbook_path(case)}, or {csv_path(case, table)}.')

    kind, path = found
    if kind == 'csv':
        return pd.read_csv(path, dtype=dtype, **CSV_OPTIONS)

    with _quiet_workbook():
        frame = pd.read_excel(path, sheet_name=table, dtype=dtype)
    return normalise(frame)


def _as_text(value) -> str:
    """One cell as the CSV reader would have produced it."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    if isinstance(value, bool):
        return '1' if value else ''
    if isinstance(value, float) and value.is_integer():
        # Excel stores every number as a float, so a column of 1s arrives as
        # 1.0. Written back out as '1.0' it stops matching the '1' that
        # is_residual is tested against, and residual rows go unrecognised.
        return str(int(value))
    return str(value).strip()


def normalise(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Make a sheet read like the CSV it replaces.

    The CSV reader runs with `keep_default_na=False`, so a column holding any
    blank comes back as strings -- '' and '1' -- while a fully populated
    numeric column comes back numeric. Excel has no empty string: a blank is
    NaN, which makes the whole column float64, and '1' becomes 1.0.

    That difference is not cosmetic. `is_residual` is tested with
    `str(value).strip() in ('1', 'True', 'true')`; against 1.0 that is '1.0',
    which matches nothing, and the Monte Carlo then refuses a group whose
    residual rows it can no longer identify. So columns containing a blank are
    converted to text here, and fully numeric columns are left numeric --
    exactly what reading the CSV produced.
    """
    frame = frame.copy()
    # A wholly empty trailing row is what Excel leaves behind after a delete.
    frame = frame.dropna(how='all')

    for column in frame.columns:
        has_blank = frame[column].isna().any()
        if frame[column].dtype == object or has_blank:
            frame[column] = frame[column].map(_as_text)

    return frame.reset_index(drop=True)


def describe(case: str) -> str:
    """Which file backs each table, for a run to report."""
    parts = []
    for table in TABLES:
        found = where(case, table)
        parts.append(f'{table}={found[0] if found else "missing"}')
    return ', '.join(parts)


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

# Allowed values live on their own hidden sheet and the dropdowns point at
# ranges on it. An inline list -- formula1='"a,b,c"' -- is capped at 255
# characters, which a real element list passes without warning: Excel then
# drops the validation silently and the dropdown simply is not there.
LISTS_SHEET = '_lists'

# Row 1 of every sheet is column names, not data. Freezing it keeps it on
# screen; colouring it is what makes it read as a heading on the first look,
# before anyone has scrolled far enough for the freeze to show.
HEADER_FILL = 'D9E1F2'



def style_header(sheet) -> None:
    """Bold on a fill across row 1, so the column names look like column names."""
    from openpyxl.styles import Font, PatternFill

    fill = PatternFill('solid', start_color=HEADER_FILL, end_color=HEADER_FILL)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = fill


def write_sheet(case: str, table: str, frame: pd.DataFrame, *,
                dropdowns: dict[str, list[str]] | None = None,
                widths: dict[str, int] | None = None) -> str:
    """
    Replace one sheet of a case's workbook, leaving the others alone.

    Written to a temp file beside the target and renamed, for the reason in
    tools/make_skeleton.py: a half-written table looks like a smaller table,
    and this one is read back and merged.
    """
    import tempfile

    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    path = workbook_path(case)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        with _quiet_workbook():
            book = load_workbook(path)
        position = book.sheetnames.index(table) if table in book.sheetnames else None
        if position is not None:
            del book[table]
        sheet = book.create_sheet(table, index=position)
    else:
        book = Workbook()
        book.remove(book.active)
        sheet = book.create_sheet(table)

    sheet.append(list(frame.columns))
    for row in frame.itertuples(index=False):
        sheet.append(['' if value is None else value for value in row])

    sheet.freeze_panes = 'A2'
    style_header(sheet)
    for index, column in enumerate(frame.columns, start=1):
        letter = get_column_letter(index)
        sheet.column_dimensions[letter].width = (widths or {}).get(column, 18)

    held = [None]  # the hidden sheet, made only if something actually needs it

    def offer(name: str, allowed, target: str) -> None:
        """
        Constrain `target` -- any A1 range on this sheet -- to `allowed`.

        The values are written to a column of a hidden sheet and referred to by
        range, not listed inline in the rule: Excel truncates an inline list at
        255 characters without saying so, and the TC key lists go well past it.
        """
        if held[0] is None:
            held[0] = book[LISTS_SHEET] if LISTS_SHEET in book.sheetnames \
                else book.create_sheet(LISTS_SHEET)
            held[0].sheet_state = 'hidden'
        lists = held[0]

        # Reuse the column this name already has. Writing a sheet twice used to
        # append a fresh copy of every list, so _lists grew by seven columns per
        # write and the abandoned copies stayed behind, still holding whatever
        # the keys were at the time.
        headers = {}
        for index in range(1, lists.max_column + 1):
            header = lists.cell(row=1, column=index).value
            if header is not None:
                headers[header] = index
        column = headers.get(name) or (max(headers.values()) + 1 if headers else 1)

        # Clear first: a list that got shorter would otherwise keep its tail.
        for line in range(2, lists.max_row + 1):
            lists.cell(row=line, column=column, value=None)
        lists.cell(row=1, column=column, value=name)
        for line, value in enumerate(allowed, start=2):
            lists.cell(row=line, column=column, value=value)

        letter = get_column_letter(column)
        rule = DataValidation(
            type='list',
            formula1=f"={LISTS_SHEET}!${letter}$2:${letter}${len(allowed) + 1}",
            allow_blank=True, showDropDown=False)
        # showDropDown=False is Excel's spelling for "do show the arrow";
        # setting it True hides the control while still enforcing the list.
        rule.error = 'Not one of the values this case declares.'
        rule.errorTitle = 'Unknown value'
        sheet.add_data_validation(rule)
        rule.add(target)

    def offer_column(name: str, allowed) -> None:
        """Constrain a whole column, header row excepted."""
        letter = get_column_letter(list(frame.columns).index(name) + 1)
        offer(name, allowed, f'{letter}2:{letter}{max(len(frame) + 1, 2)}')

    covered = set()
    for column, allowed in sorted((dropdowns or {}).items()):
        if column not in frame.columns or not allowed:
            continue
        offer_column(column, allowed)
        covered.add(column)

    # `source` is a key/value sheet, so a fixed vocabulary constrains ONE cell
    # rather than a column: the value beside `child_layer` is element or
    # material, while the value beside `product` is anything at all.
    #
    # Applied here rather than passed in by the caller because nothing writes
    # this sheet today -- a parameter nobody passes is a parameter nobody
    # remembers, and the dropdown has to come back on a sheet rewritten later
    # by someone who never read this file.
    if table == 'processes':
        from src.rest import VOCABULARY as PROCESS_VOCABULARY

        for column, allowed in sorted(PROCESS_VOCABULARY.items()):
            if column in frame.columns and column not in covered:
                offer_column(column, allowed)

    if table == 'source' and {'key', 'value'} <= set(frame.columns):
        from src.source import VOCABULARY

        keys = [str(key).strip() for key in frame['key']]
        value_column = get_column_letter(list(frame.columns).index('value') + 1)
        for key, allowed in sorted(VOCABULARY.items()):
            if key in keys:
                line = keys.index(key) + 2  # +1 for the header, +1 to 1-based
                offer(key, allowed, f'{value_column}{line}')

    handle = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(path), prefix='.case-', suffix='.tmp', delete=False)
    handle.close()
    try:
        book.save(handle.name)
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
    return path
