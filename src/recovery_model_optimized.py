# -*- coding: utf-8 -*-
"""

@Author: Adrien Perello / Harmjan de Vries
@Date: 24.03.2024
"""
# %%
import numpy as np
import pandas as pd
import os
from typing import List
from dataclasses import dataclass
import networkx as nx
from itertools import product

from src.process_join import (INFLOW_POSITION, LAYERS, TC_POSITION, process_pairs)
from src.rest import REST, add_rest
from src.selection import chosen_scenario, chosen_years, is_year_match as _is_year_match, select
from src.tc_precedence import apply_precedence
from src.validate_inputs import validate

# Definition of file/folder names within the overarching data directory
OUTPUT_DATA_FOLDER_NAME = "output_data"
INPUT_DATA_FOLDER_NAME = "input_data"

TCS_FILENAME = "TCs.csv"
INPUTS_FILENAME = "inputs.csv"
COMPOSITION_FILENAME = "composition.csv"
SOLUTION_FILENAME = "solution_optimized_model.csv"


@dataclass
class InputDataFormat:
    """
    Dataclass defining mandatory columns for each input table
    """
    input_columns = ['Stock/Flow ID','Substance_main_parent','Value']
    TCs_columns = ['Input_FlowID','Input_layer','Input_layer_key','Output_FlowID','TC_target_layer','TC_target_key','value']
    composition_columns = ['Stock/ID','Layer 1','Layer 2','Layer 3','Layer 4', 'Value']

    optional_columns = ['Location','Year','Scenario','additionalSpecification']

    # Carried through to the Monte Carlo when present, ignored otherwise, so a
    # table with ranges and one without both load. See documentation/
    # DESIGN_tc_table.md section 2 and src/sampling.py.
    uncertainty_columns = ['value_min', 'value_max', 'is_residual',
                           'process', 'technology']

    dtypes = {
            'Stock/Flow ID': str,
            'Substance_main_parent': str,
            'Value': float,
            'Input_FlowID': str,
            'Input_layer': str,
            'Input_layer_key': str,
            'Output_FlowID': str,
            'TC_target_layer': str,
            'TC_target_key': str,
            'value': float,
            'Stock/ID': str,
            'Layer 1': str,
            'Layer 2': str,
            'Layer 3': str,
            'Layer 4': str,
            'Location': str,
            'Year': str,
            'Scenario': str,
            'additionalSpecification':str,
            'DQS': float,
            'CV': float,
        }


class RecoveryModelOptimized:
    """Class representing the optimized recovery model, which processes TCs one-by one using dataframe operations"""
    def __init__(self, data_folder: str, layer_names: List[str],
                 scenario: str | None = None, years: str | None = None,
                 working_unit: str | None = None):
        """
        Initialize the System class.
         - Defines and creates folder structure
         - Reads input data into a set of inflows, compositions and TCs dataframes for every year, scenario, location and 
         additionalSpecification
        Args:
            data_folder: directory containing input and output data for this model
        """
        # Set data folder and create structure if needed
        self.layer_names = layer_names
        self.data_folder = data_folder
        # None means "use the scenario setting"; a string overrides it for one
        # call, which is what the tests and a one-off run need.
        self._scenario_override = scenario
        self._years_override = years
        # Likewise for the unit. The regression test pins the inherited
        # reference, which is written in the unit that data declares, so it
        # solves in that unit rather than in whatever the project currently
        # works in -- otherwise changing working_unit would look like the
        # algebra had changed.
        self._unit_override = working_unit

        # Check the input tables before anything is joined. At this point a bad
        # key can still be reported with its file, column and value; a few lines
        # later it is either silent phantom mass or an unreadable TypeError.
        # See src/validate_inputs.py and documentation/DEFECTS.md section 5.
        validate(data_folder)

        if not os.path.exists(os.path.join(self.data_folder, OUTPUT_DATA_FOLDER_NAME)):
            os.makedirs(os.path.join(self.data_folder, OUTPUT_DATA_FOLDER_NAME))

        # Read excel files
        self.input_data = self.read_input_data()

    def read_input_data(self) -> dict:
        """
        Read inflows, composition and TCs files for every year and stores them in the correct dataframe format

        Returns:
            A dictionary with the input inflows, compositions and TCs dataframes for each year, scenario, location and 
            additionalSpecification
        """
        # Load the input files
        inflows_df = pd.read_csv(
            os.path.join(self.data_folder, INPUT_DATA_FOLDER_NAME, INPUTS_FILENAME),
            dtype=InputDataFormat.dtypes,
            keep_default_na=False,
            na_values=[]
        )
        # The inflow is re-expressed in the unit this project works in
        # (working_unit in src/params_schema.py). Composition and TCs are
        # fractions and carry no unit. Done here, before anything is joined, so
        # that every number after this point is in one unit -- the model
        # multiplies fractions and would otherwise never notice.
        from src.params_schema import Params
        from src.units import convert_inflows
        wanted_unit = (self._unit_override if self._unit_override is not None
                       else Params().run.working_unit)
        inflows_df, self.unit_note = convert_inflows(inflows_df, wanted_unit)
        self.working_unit = wanted_unit

        composition_df = pd.read_csv(
            os.path.join(self.data_folder, INPUT_DATA_FOLDER_NAME, COMPOSITION_FILENAME),
            dtype=InputDataFormat.dtypes,
            keep_default_na=False,
            na_values=[]
        )
        tcs_df = pd.read_csv(
            os.path.join(self.data_folder, INPUT_DATA_FOLDER_NAME, TCS_FILENAME),     
            dtype=InputDataFormat.dtypes,
            keep_default_na=False,
            na_values=[]
        )

        # Real composition data is incomplete: the copper in a wire is often
        # known when the wire's own weight is not. A parent is therefore the sum
        # of its known children plus a derived `rest`, so that closure to 1 holds
        # at every layer and the unspecified part is visible rather than absent.
        # Without this the shortfall simply had no row (src/rest.py).
        composition_df, self.rest_notes = add_rest(composition_df)
        # Where two TCs describe the same material, the row naming the parent
        # governs and the other is narrowed to the products it still covers.
        # Done here, on the table, so that both engines are handed the same
        # explicit rows and cannot drift apart again (DEFECTS.md 2.3).
        tcs_df = apply_precedence(tcs_df, composition_df)

        # Replace the wording of 'product', 'component', etc... with a consistent wording within the model: 'Layer 1', 'Layer 2', etc...
        layer_names_replace = {item: f"Layer {i+1}" for i, item in enumerate(self.layer_names)}
        tcs_df["Input_layer"] = tcs_df["Input_layer"].replace(layer_names_replace)
        tcs_df["TC_target_layer"] = tcs_df["TC_target_layer"].replace(layer_names_replace)

        # The user guide documents an asterisk for "the same TC for all products
        # in a layer". RecoveryModelLA implements it; this engine used to read
        # 'P*' as a literal key, match nothing, and emit no output flow at all --
        # no error and no warning, so an entire flow simply went missing from
        # the results (DEFECTS.md 2.2).
        tcs_df = self.expand_wildcards(tcs_df, composition_df)


        # What this run covers. inputs.csv is the defining basis for which
        # years, scenarios, locations and additionalSpecifications exist; the
        # settings then narrow that down.
        from src.params_schema import Params

        # Blank means every year in the file; a single year or a '2030-2050'
        # range narrows it (src/params_schema.py).
        wanted_years = (self._years_override if self._years_override is not None
                        else Params().run.years)
        years = chosen_years(inflows_df, wanted_years)

        # One run is one scenario. This used to sweep every scenario in the
        # file, writing each one's output over the last one's.
        wanted = (self._scenario_override if self._scenario_override is not None
                  else Params().run.scenario)
        self.scenario = chosen_scenario(inflows_df, wanted)
        scenarios = [self.scenario]
        locations = inflows_df['Location'].unique() if 'Location' in inflows_df.columns else [None]
        additional_specifications = inflows_df['additionalSpecification'].unique() if 'additionalSpecification' in inflows_df.columns else [None]

        input_dfs = []
        for year, scenario, location, additional_specification in product(years, scenarios, locations, additional_specifications):
            # Select the inflows, TCs and composition for this year, scenario, location and additionalSpecification
            inflows_df_selection = HelperFunctions.select_df_by_year_scenario_location(df=inflows_df, year=year, scenario=scenario, location=location, additional_specification=additional_specification)
            if len(inflows_df_selection)==0:
                # If there are no inflows provided for this combination of year, scenario ..., skip it.
                continue

            composition_df_selection = HelperFunctions.select_df_by_year_scenario_location(df=composition_df, year=year, scenario=scenario, location=location, additional_specification=additional_specification)

            tcs_df_selection = HelperFunctions.select_df_by_year_scenario_location(df=tcs_df, year=year, scenario=scenario, location=location, additional_specification=additional_specification)

            inflows_df_selection = inflows_df_selection[InputDataFormat.input_columns].replace('n/a','')
            composition_df_selection = composition_df_selection[InputDataFormat.composition_columns].replace('n/a','')
            # The mandatory columns, plus any uncertainty columns the table
            # carries. Narrowing to the mandatory list alone silently dropped
            # value_min and value_max, so a table with ranges reached the Monte
            # Carlo looking deterministic and every draw came back identical --
            # a failure that produces plausible numbers and announces nothing.
            kept = InputDataFormat.TCs_columns + [
                column for column in InputDataFormat.uncertainty_columns
                if column in tcs_df_selection.columns]
            tcs_df_selection = tcs_df_selection[kept].replace('n/a','')

            input_dfs.append({
                "Year":year,
                "Scenario": scenario,
                "Location": location,
                "additionalSpecification": additional_specification,
                "inflows_df": inflows_df_selection,
                "composition_df":composition_df_selection,
                "tcs_df": tcs_df_selection
            })
        return input_dfs


    def output_path(self, filename: str) -> str:
        """
        Where a solution is written.

        One subfolder per scenario, so separate runs accumulate rather than
        overwrite -- comparing scenarios is analysis done afterwards on these
        files, which requires them all to still exist. Without a scenario
        dimension the layout is unchanged.
        """
        parts = [self.data_folder, OUTPUT_DATA_FOLDER_NAME]
        if getattr(self, 'scenario', None):
            parts.append(self.scenario)
        folder = os.path.join(*parts)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

    def solve_models_and_write_to_output(self) -> pd.DataFrame:
        """
        Solve all entries in the variable self.input_data. Creates an output file where the solution is stored.
        """
        columns = ["Year", "Scenario", "Location", "additionalSpecification",
                   "Stock/Flow ID", "Layer 1", "Layer 2", "Layer 3", "Layer 4", "Value"]
        solutions = []
        for entry in self.input_data:
            # Solve the system for a specific year, location, scenario and additionalSpecification
            solution = self.solve_model(
                inflows_df=entry["inflows_df"],
                composition_df=entry["composition_df"],
                tcs_df=entry["tcs_df"]
            )
            solution['Year'] = entry['Year']
            solution['Scenario'] = entry['Scenario']
            solution['Location'] = entry['Location']
            solution['additionalSpecification'] = entry['additionalSpecification']

            solutions.append(solution)

        # Collected and concatenated once, rather than concatenated onto an empty
        # frame inside the loop. That older form did two harmful things: it was
        # quadratic in the number of year/scenario cells, and seeding from
        # pd.DataFrame(columns=[...]) made every column object dtype -- so Value
        # came back as boxed Python floats, which survives the CSV round trip
        # unnoticed and defeats every numpy fast path (DEFECTS.md 3.4).
        full_solution = (pd.concat(solutions, ignore_index=True) if solutions
                         else pd.DataFrame({name: pd.Series(dtype='float64' if name == 'Value'
                                                            else 'object')
                                            for name in columns}))

        # Sort the result, and select only the relevant columns and rows.
        full_solution = full_solution.sort_values(by=['Year','Scenario', 'Location','additionalSpecification', 'Stock/Flow ID', 'Layer 1','Layer 2','Layer 3','Layer 4'])
        empty_cols = [col for col in ["Scenario", "Location", "additionalSpecification", "Year"] if full_solution[col].isna().all()]
        full_solution = full_solution.drop(columns=empty_cols)
        full_solution = full_solution[full_solution.Value!=0]
        full_solution.to_csv(self.output_path(SOLUTION_FILENAME), index=False)
        return full_solution

    def solve_model(self, inflows_df: pd.DataFrame, composition_df: pd.DataFrame, tcs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Solve the system given a specific set of inflows, composition and TCs. Takes the following steps:
        1. Combine the inflows and composition dataframes to determine the initial flow
        2. Loop over all the processes in order (assuming no feedback loops in the system) and 
            determine the outflows of each process 1 by 1
        3. Add the outflows that feed into the same flows together
        """
        flows_result = self.create_initial_flows(inflows_df=inflows_df, composition_df=composition_df)

        process_sequence = self.get_process_sequence_from_tcs(tcs_df)
        for _, row in process_sequence.iterrows():
            process_inflow = flows_result[flows_result["Stock/Flow ID"]==row["Input_FlowID"]].drop(columns=["Stock/Flow ID"])
            process_tcs = tcs_df[(tcs_df["Input_FlowID"]==row["Input_FlowID"])&(tcs_df["Output_FlowID"]==row["Output_FlowID"])]
            process_outflow = self.solve_process(process_tcs=process_tcs, process_inflow=process_inflow)
            process_outflow["Stock/Flow ID"] = row["Output_FlowID"]
            flows_result = pd.concat([flows_result, process_outflow], ignore_index=True)

        return flows_result.groupby(["Stock/Flow ID","Layer 1","Layer 2","Layer 3","Layer 4"],as_index=False).agg({"Value":"sum"})

    @staticmethod
    def expand_wildcards(tcs_df: pd.DataFrame, composition_df: pd.DataFrame) -> pd.DataFrame:
        """
        Turn a key containing '*' into one row per resource at that layer.

        The asterisk means "every resource in this layer", so the text around it
        carries no meaning of its own -- 'P*' and '*' expand identically, since
        the layer column already says which set is meant. That is also how
        RecoveryModelLA reads it (`fill_star_values`), which is what makes the
        two engines agree on this input rather than one of them silently
        producing nothing.

        Args:
            tcs_df: TCs with their layers already renamed to 'Layer 1'..'Layer 4'
            composition_df: supplies which resources exist at each layer
        """
        layers = ["Layer 1", "Layer 2", "Layer 3", "Layer 4"]
        known = {layer: sorted({value for value in composition_df[layer].unique() if value})
                 for layer in layers}

        for key_column, layer_column in (("Input_layer_key", "Input_layer"),
                                         ("TC_target_key", "TC_target_layer")):
            if not tcs_df[key_column].astype(str).str.contains(r"\*", regex=True).any():
                continue
            tcs_df = tcs_df.copy()
            tcs_df[key_column] = [
                known.get(layer, []) if "*" in str(key) else key
                for key, layer in zip(tcs_df[key_column], tcs_df[layer_column])
            ]
            tcs_df = tcs_df.explode(key_column).reset_index(drop=True)

        return tcs_df

    @staticmethod
    def create_initial_flows(inflows_df: pd.DataFrame, composition_df: pd.DataFrame) -> pd.DataFrame:
        """
        Use the provided inflows and composition to determine the initial inflow (with composition)
        into the system. 
        """
        product_flows = inflows_df[['Stock/Flow ID', 'Substance_main_parent', 'Value']].copy()
        product_flows.rename(columns={'Substance_main_parent': 'Layer 1'}, inplace=True)
        product_flows['Layer 2'] = ''
        product_flows['Layer 3'] = ''
        product_flows['Layer 4'] = ''
        column_order = ['Stock/Flow ID', 'Layer 1', 'Layer 2', 'Layer 3', 'Layer 4', 'Value']
        product_flows = product_flows[column_order]

        # Composition is defined PER FLOW. The user guide gives 'Stock/ID' as
        # "Stock/Flow ID for the flow the material is contained in", and this
        # column used to be dropped here and every merge done on the resource
        # layers alone -- so a composition written for one flow was applied to
        # every flow carrying the same parent, inventing mass (DEFECTS.md 2.1).
        # Carrying it into the join keys is the whole fix.
        composition_df = composition_df[["Stock/ID", "Layer 1", "Layer 2", "Layer 3",
                                         "Layer 4", "Value"]].rename(
            columns={"Stock/ID": "Stock/Flow ID"})

        # Apply composition p-c layer
        layer_2_composition = composition_df[(composition_df['Layer 3']=="") & (composition_df['Layer 4']=='')].copy()
        df_merged = layer_2_composition.merge(product_flows, on=["Stock/Flow ID", "Layer 1"], suffixes=("", "_inflow"))
        df_merged["Value"] = df_merged["Value_inflow"]*df_merged["Value"]
        layer_2_flows = df_merged[["Stock/Flow ID","Layer 1","Layer 2", "Layer 3","Layer 4","Value"]]

        # Apply composition c-m layer
        layer_3_composition = composition_df[(composition_df['Layer 3']!="") & (composition_df['Layer 4']=='')].copy()
        df_merged = layer_3_composition.merge(layer_2_flows, on=["Stock/Flow ID", "Layer 1", "Layer 2"], suffixes=("","_inflow"))
        df_merged["Value"] = df_merged["Value_inflow"]*df_merged["Value"]
        layer_3_flows = df_merged[["Stock/Flow ID","Layer 1","Layer 2", "Layer 3","Layer 4","Value"]]

        # Apply composition m-e layer
        layer_4_composition = composition_df[(composition_df['Layer 3']!="") & (composition_df['Layer 4']!='')].copy()
        df_merged = layer_4_composition.merge(layer_3_flows, on=["Stock/Flow ID", "Layer 1", "Layer 2", "Layer 3"], suffixes=("","_inflow"))
        df_merged["Value"] = df_merged["Value_inflow"]*df_merged["Value"]
        layer_4_flows = df_merged[["Stock/Flow ID","Layer 1","Layer 2", "Layer 3","Layer 4","Value"]]

        # Add them all together in a big dataframe that now contains the inflow at the level of every layer
        return pd.concat([product_flows, layer_2_flows, layer_3_flows, layer_4_flows], ignore_index=True)

    @staticmethod
    def get_process_sequence_from_tcs(tcs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Assuming a system with no feedback loops, order all the combinations of flows (processes) that are in the TCs in a way
        that they can be solved one by one. Returns a dataframe with all flow combination, in such an order
        that they can be applied one by one.
        """
        unique_flow_combinations = tcs_df[['Input_FlowID', 'Output_FlowID']].drop_duplicates()
        edges = unique_flow_combinations.apply(lambda row: (row["Input_FlowID"], row["Output_FlowID"]), axis=1).tolist()
        Graph = nx.DiGraph()
        Graph.add_edges_from(edges)
        try:
            node_order = list(nx.topological_sort(Graph))
            node_position = {node: index for index, node in enumerate(node_order)}
            sorted_edges = sorted(edges, key=lambda edge: node_position[edge[0]])
        except nx.NetworkXUnfeasible:
            raise ValueError("The flows in this system cannot be solved as a sequential system: it contains cycles.")

        return pd.DataFrame(sorted_edges, columns=['Input_FlowID', 'Output_FlowID'])

    @staticmethod
    def solve_process(process_tcs: pd.DataFrame, process_inflow: pd.DataFrame) -> pd.DataFrame:
        """
        The outflows of one process: its inflow rows, each scaled by the
        coefficient that applies to it.

        Which coefficient applies to which row is decided by
        `src/process_join.py`, not here, so that the Monte Carlo solve pairs
        exactly the same rows with exactly the same coefficients. Everything
        this function still owns is the arithmetic: multiply, and drop the
        rows that came out zero.
        """
        tcs = process_tcs.reset_index(drop=True)
        tcs = tcs.assign(**{TC_POSITION: np.arange(len(tcs))})

        inflow = process_inflow.reset_index(drop=True)
        inflow = inflow.assign(**{INFLOW_POSITION: np.arange(len(inflow))})

        pairs = process_pairs(tcs, inflow[LAYERS + [INFLOW_POSITION]])
        if pairs.empty:
            return pd.DataFrame({**{layer: pd.Series(dtype='object') for layer in LAYERS},
                                 'Value': pd.Series(dtype='float64')})

        values = (inflow['Value'].to_numpy(dtype=float)[pairs[INFLOW_POSITION].to_numpy()]
                  * tcs['value'].to_numpy(dtype=float)[pairs[TC_POSITION].to_numpy()])

        outflow = pairs[LAYERS].copy()
        outflow['Value'] = values
        # A coefficient of exactly zero contributes nothing and is dropped, which
        # is what keeps the intermediate frames small (DEFECTS.md 1.3). Rows with
        # no matching coefficient never appeared in the first place: a missing
        # coefficient is the absence of a route, not a transfer of nothing.
        return outflow[outflow['Value'] != 0.0].reset_index(drop=True)

class HelperFunctions:
    @staticmethod
    def is_year_match(year_data, year_target):
        """Kept for callers; the rule itself lives in src/selection.py."""
        return _is_year_match(year_data, year_target)

    @staticmethod
    def select_df_by_year_scenario_location(df: pd.DataFrame, year: str | None, location: str | None, scenario: str | None, additional_specification: str | None) -> pd.DataFrame:
        """
        Kept for callers; the rule itself lives in src/selection.py, which the
        LA engine now uses too. Two copies of a selection rule is how the two
        engines came apart in the first place (DEFECTS.md 2.4).
        """
        return select(df, year, scenario, location, additional_specification)
