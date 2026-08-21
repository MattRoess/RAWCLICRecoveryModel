"""
src/monte_carlo.py
==================

Solving the flow network for many draws at once.

THE IDEA
--------
`solve_model` in the deterministic engine is a chain of joins, multiplications
and group-sums. Across Monte Carlo draws the *joins never change* -- the flow
network, the layer keys and which coefficient applies to which row are all
fixed by the input tables. Only the numbers move.

So the structure is computed once and the arithmetic is done on arrays:

    deterministic:   value  = inflow_value * coefficient          (two scalars)
    Monte Carlo:     values = inflow_values * coefficient_values  (two rows of draws)

Every row of the result carries `(draws,)` numbers instead of one. The joins
themselves come from `src/process_join.py`, the same function the deterministic
engine calls, so the two cannot pair rows differently.

WHY NOT A LOOP OVER DRAWS
-------------------------
Measured: `solve_model` takes 0.5 s on a mid-sized case, so 200,000 sequential
draws is 29 hours for one scenario. The arithmetic here is the same total
number of multiplications, but done as a few thousand large array operations
instead of a few million small ones.

MEMORY
------
`n_rows x n_draws x 8 bytes` is the whole story. 734,000 rows at 200,000 draws
is 1.17 TB, so draws are processed in chunks and reduced as they go -- see
`run_chunked`. Chunking is safe because draw i is the same number in every
chunk (`src/sampling.py`, SEEDING).

WHAT IS AND IS NOT UNCERTAIN HERE
---------------------------------
Transfer coefficients are drawn. Inflows and composition are held at their
stated values, because the tables have no ranges for them yet: composition
arrives as a single share per row, and the real per-draw inflows are the
upstream arrays this project cannot read yet (HANDOVER.md section 8). Both are
already arrays in the arithmetic below, so supplying draws for them later is a
change of input, not of engine.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.process_join import INFLOW_POSITION, LAYERS, TC_POSITION, process_pairs
from src.recovery_model_optimized import RecoveryModelOptimized

KEY_COLUMNS = ['Stock/Flow ID'] + LAYERS

BYTES_PER_VALUE = 8          # float64

# Everything that is not the result array or the chunk: the interpreter, numpy,
# pandas, scipy, matplotlib, the figures while they are being drawn, and the
# workbook. MEASURED rather than guessed -- two runs of the same case at
# different chunk sizes give both constants:
#
#   chunk  20,000 -> 2.75 GB peak
#   chunk 159,027 -> 3.46 GB peak      600 rows, 200,000 draws, result 0.96 GB
#
# The difference over the change in chunk gives the transient factor (~1.0 x
# rows x chunk x 8), and either point then gives the fixed part.
OVERHEAD_GB = 1.8
TRANSIENT_FACTOR = 1.0


class MemoryBudgetExceeded(MemoryError):
    """Raised before allocating, when the result would not fit the budget."""


def plan(total_rows: int, draws: int, budget_gb: float,
         chunk: int = 0) -> tuple[int, str]:
    """
    Decide the chunk size, and refuse a run that cannot fit.

    The result array is rows x draws x 8 bytes and is unavoidable if exact
    percentiles are wanted. Everything else is transient and is what the chunk
    bounds, so the chunk is sized from whatever budget is left over rather than
    guessed at a round number.

    Raises before anything is allocated. A run that cannot fit should say so in
    a second, not after ten minutes of swapping.
    """
    result_gb = total_rows * draws * BYTES_PER_VALUE / 1e9
    floor_gb = result_gb + OVERHEAD_GB

    if floor_gb > budget_gb:
        halved = result_gb / 2 + OVERHEAD_GB
        raise MemoryBudgetExceeded(
            f'This run needs about {floor_gb:.1f} GB and the budget is '
            f'{budget_gb:.1f} GB.\n'
            f'  {result_gb:.2f} GB  the result: {total_rows:,} rows x {draws:,} draws\n'
            f'  {OVERHEAD_GB:.2f} GB  the libraries and the figures\n\n'
            f'Nothing has been allocated. Pull one of these in '
            f'src/params_schema.py:\n'
            f'  data.draws                 halving it -> about {halved:.1f} GB\n'
            f'  run.years                  fewer years, proportionally fewer rows\n'
            f'  data.groups        fewer domains, fewer rows\n'
            f'  monte_carlo.memory_budget_gb  raise it if the machine has the memory')

    if chunk:
        return chunk, f'{chunk:,} draws per chunk (set by hand)'

    # Whatever the budget has left over goes to the chunk. Never more than the
    # draw count, and never so small that per-chunk overhead dominates.
    spare_gb = budget_gb - floor_gb
    per_draw = max(1, total_rows * BYTES_PER_VALUE) * TRANSIENT_FACTOR
    sized = int(min(draws, max(1_000, spare_gb * 1e9 / per_draw)))
    return sized, (f'{sized:,} draws per chunk, {floor_gb:.1f} of '
                   f'{budget_gb:.1f} GB budget')



class Structure:
    """
    The shape of one solve: which rows exist, and what produces each of them.

    Built once from the input tables, then evaluated as often as wanted with
    different coefficient values. Holding the two apart is the whole reason the
    Monte Carlo is affordable.
    """

    def __init__(self, inflows_df: pd.DataFrame, composition_df: pd.DataFrame,
                 tcs_df: pd.DataFrame):
        self.tcs = tcs_df.reset_index(drop=True)
        self.inflows = inflows_df.reset_index(drop=True)

        # Step 1 -- the inflow expanded through composition, as index pairs.
        self.keys, self.initial = self._initial_structure(composition_df)

        # Step 2 -- each process in turn. Every step says which existing rows it
        # reads, which coefficients it multiplies them by, and where the results
        # land in the growing table.
        self.steps: list[dict] = []
        self._process_structure()

        # Step 3 -- where each row of the working table lands in the final,
        # grouped result.
        self.result_keys, self.group_of_row = self._grouping()

    # ------------------------------------------------------------------
    #  Building the structure
    # ------------------------------------------------------------------

    def _initial_structure(self, composition_df: pd.DataFrame):
        """
        The inflow rows, and the composition cascade that expands them.

        Mirrors `RecoveryModelOptimized.create_initial_flows` exactly, including
        that composition is joined per flow -- 'Stock/ID' names the flow the
        material sits in, and dropping it applied one flow's composition to
        every flow carrying the same parent (DEFECTS.md 2.1).
        """
        inflow_keys = pd.DataFrame({
            'Stock/Flow ID': self.inflows['Stock/Flow ID'],
            'Layer 1': self.inflows['Substance_main_parent'],
            'Layer 2': '', 'Layer 3': '', 'Layer 4': '',
        })

        composition = composition_df.reset_index(drop=True).rename(
            columns={'Stock/ID': 'Stock/Flow ID'})
        composition = composition.assign(__comp=np.arange(len(composition)))

        keys = inflow_keys.copy()
        # Rows produced directly by the inflow: no composition factor.
        cascade = [{'kind': 'inflow', 'inflow_row': np.arange(len(inflow_keys))}]

        depth_filters = [
            (composition['Layer 3'] == '') & (composition['Layer 4'] == ''),
            (composition['Layer 3'] != '') & (composition['Layer 4'] == ''),
            (composition['Layer 3'] != '') & (composition['Layer 4'] != ''),
        ]
        join_on = [['Stock/Flow ID', 'Layer 1'],
                   ['Stock/Flow ID', 'Layer 1', 'Layer 2'],
                   ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3']]

        # Each depth expands the rows produced by the depth above it.
        parent_start, parent_stop = 0, len(inflow_keys)
        for depth, (mask, on) in enumerate(zip(depth_filters, join_on)):
            level = composition[mask]
            if level.empty:
                cascade.append({'kind': 'composition', 'parent': np.array([], dtype=int),
                                'factor': np.array([], dtype=int)})
                continue

            parents = keys.iloc[parent_start:parent_stop].copy()
            parents['__parent'] = np.arange(parent_start, parent_stop)
            merged = level.merge(parents[on + ['__parent']], on=on, how='inner')

            produced = merged[['Stock/Flow ID'] + LAYERS].reset_index(drop=True)
            keys = pd.concat([keys, produced], ignore_index=True)
            cascade.append({'kind': 'composition',
                            'parent': merged['__parent'].to_numpy(),
                            'factor': merged['__comp'].to_numpy()})
            parent_start, parent_stop = parent_stop, len(keys)

        self.composition_values = composition['Value'].to_numpy(dtype=float)
        return keys, cascade

    def _process_structure(self) -> None:
        """
        Each process, in an order that lets them be solved one at a time.

        The order and the cycle refusal come from the deterministic engine, so
        a network it cannot solve is not silently solvable here.
        """
        tcs = self.tcs.assign(**{TC_POSITION: np.arange(len(self.tcs))})
        sequence = RecoveryModelOptimized.get_process_sequence_from_tcs(self.tcs)

        for _, step in sequence.iterrows():
            source, target = step['Input_FlowID'], step['Output_FlowID']

            is_source = (self.keys['Stock/Flow ID'] == source).to_numpy()
            source_rows = np.flatnonzero(is_source)
            if source_rows.size == 0:
                continue

            inflow = self.keys.iloc[source_rows][LAYERS].reset_index(drop=True)
            inflow[INFLOW_POSITION] = np.arange(len(source_rows))

            process_tcs = tcs[(tcs['Input_FlowID'] == source)
                              & (tcs['Output_FlowID'] == target)]
            pairs = process_pairs(process_tcs, inflow)
            if pairs.empty:
                continue

            produced = pairs[LAYERS].copy()
            produced.insert(0, 'Stock/Flow ID', target)
            first_new_row = len(self.keys)
            self.keys = pd.concat([self.keys, produced], ignore_index=True)

            self.steps.append({
                # Positions in the working values array that this step reads ...
                'reads': source_rows[pairs[INFLOW_POSITION].to_numpy()],
                # ... the coefficient each of those is multiplied by ...
                'coefficient': pairs[TC_POSITION].to_numpy(),
                # ... and where each product is written.
                'writes': np.arange(first_new_row, len(self.keys)),
            })

    def _grouping(self):
        """
        Where each working row lands in the final result.

        The deterministic engine finishes with a groupby-sum over the key
        columns; the same collapse is done here with an index, so it costs one
        scatter-add per chunk instead of a pandas group operation per draw.
        """
        codes, uniques = pd.MultiIndex.from_frame(self.keys[KEY_COLUMNS]).factorize()
        result_keys = pd.DataFrame(list(uniques), columns=KEY_COLUMNS)
        return result_keys, np.asarray(codes)

    # ------------------------------------------------------------------
    #  Evaluating it
    # ------------------------------------------------------------------

    def evaluate(self, inflow_values: np.ndarray, tc_values: np.ndarray,
                 composition_values: np.ndarray | None = None,
                 out: np.ndarray | None = None) -> np.ndarray:
        """
        Solve for a block of draws.

        Args:
            inflow_values: (n_inflow_rows, n_draws)
            tc_values:     (n_coefficients, n_draws)
            composition_values: (n_composition_rows, n_draws), or None to use
                the single share stated in the table for every draw

        Returns:
            (n_result_rows, n_draws), aligned with `self.result_keys`.
        """
        draws = inflow_values.shape[1]
        if composition_values is None:
            composition_values = np.broadcast_to(
                self.composition_values[:, None], (len(self.composition_values), draws))

        values = np.zeros((len(self.keys), draws), dtype=np.float64)

        # Step 1 -- inflows, then the composition cascade.
        written = 0
        for stage in self.initial:
            if stage['kind'] == 'inflow':
                count = len(stage['inflow_row'])
                values[written:written + count] = inflow_values[stage['inflow_row']]
                written += count
            else:
                count = len(stage['parent'])
                if count:
                    values[written:written + count] = (
                        values[stage['parent']] * composition_values[stage['factor']])
                written += count

        # Step 2 -- the processes, in order.
        for step in self.steps:
            values[step['writes']] = values[step['reads']] * tc_values[step['coefficient']]

        # Step 3 -- collapse duplicate keys, straight into the caller's array
        # when one is given. Returning a fresh array and letting the caller copy
        # it meant a second full-size allocation for nothing.
        if out is None:
            result = np.zeros((len(self.result_keys), draws), dtype=np.float64)
        else:
            result = out
            result[:] = 0.0
        np.add.at(result, self.group_of_row, values)
        return result


@dataclass
class MonteCarloRun:
    """
    Everything one Monte Carlo run produced.

    The sampled coefficients are kept, not just the results. Sensitivity
    analysis needs to correlate an output against the coefficient draws that
    produced it, and re-drawing them afterwards would answer a different
    question than the one the results came from.
    """

    keys: pd.DataFrame          # Year + the five key columns, one row per result row
    values: np.ndarray          # (n_rows, draws)
    report: dict                # what the sampler clamped and constrained
    tcs: pd.DataFrame           # the coefficient table actually sampled
    tc_values: np.ndarray       # (n_coefficients, draws), as drawn
    case: str = ''              # the folder it was solved from

    @property
    def draws(self) -> int:
        return self.values.shape[1]


def solve_draws(data_folder: str, layer_names: list[str], draws: int,
                start: int = 0, seed: int = 0, scenario: str | None = None,
                years: str | None = None, tables: dict | None = None,
                chunk: int | None = None, budget_gb: float = 1e9,
                quiet: bool = True) -> MonteCarloRun:
    """
    Run the model over `draws` draws, for every year in the selection.

    Draws are processed in blocks of `chunk`, so the transient arrays -- the
    sampled coefficients, the working values, the group-sum scratch -- are
    bounded by the chunk rather than by the full draw count. Only the result
    itself is held at full width.

    Chunking cannot change the answer: draw i is fixed by its own stream and its
    index, not by what was drawn before it, so a chunked run reproduces an
    unchunked one value for value (test_monte_carlo.py checks exactly that).
    """
    from src.sampling import sample

    model = RecoveryModelOptimized(data_folder=data_folder, layer_names=layer_names,
                                   scenario=scenario, years=years, tables=tables)

    # Preallocated once and filled per year. Collecting per-year blocks and
    # stacking them at the end held every block AND the stacked copy live at the
    # same time -- two full-size arrays for no reason.
    key_frames, report = [], {}
    sampled_tcs, sampled_values = None, None

    structures = []
    for entry in model.input_data:
        structures.append((entry, Structure(entry['inflows_df'],
                                            entry['composition_df'],
                                            entry['tcs_df'])))
    total_rows = sum(len(s.result_keys) for _, s in structures)
    block, how = plan(total_rows, draws, budget_gb, chunk or 0)
    if not quiet:
        print(f'Memory    : {total_rows * draws * BYTES_PER_VALUE / 1e9:.2f} GB result, '
              f'{how}')
    values = np.zeros((total_rows, draws), dtype=np.float64)

    block, how = plan(total_rows, draws, budget_gb, chunk or 0)
    n_coefficients = len(structures[0][0]['tcs_df']) if structures else 0
    all_tc_values = np.zeros((n_coefficients, draws), dtype=np.float64)
    for offset in range(0, draws, block):
        width = min(block, draws - offset)
        written = 0
        for entry, structure in structures:
            rows = len(structure.result_keys)
            target = values[written:written + rows, offset:offset + width]

            tc_values, report = sample(entry['tcs_df'], draws=width,
                                       start=start + offset, seed=seed)
            inflow_values = np.broadcast_to(
                entry['inflows_df']['Value'].to_numpy(dtype=float)[:, None],
                (len(entry['inflows_df']), width))

            structure.evaluate(inflow_values, tc_values, out=target)
            written += rows

            # The coefficients are kept at full width: the sensitivity figure
            # correlates them against the results, so they have to line up draw
            # for draw with what is stored above.
            all_tc_values[:, offset:offset + width] = tc_values
            sampled_tcs = entry['tcs_df']

    for entry, structure in structures:
        keys = structure.result_keys.copy()
        keys.insert(0, 'Year', entry['Year'])
        key_frames.append(keys)
    sampled_values = all_tc_values

    if not key_frames:
        raise ValueError(f'{data_folder} produced no years to solve.')

    return MonteCarloRun(keys=pd.concat(key_frames, ignore_index=True),
                         values=values, report=report,
                         tcs=sampled_tcs, tc_values=sampled_values,
                         case=data_folder)
