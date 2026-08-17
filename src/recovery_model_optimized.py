# -*- coding: utf-8 -*-
"""

@Author: Adrien Perello / Harmjan de Vries
@Date: 24.03.2024
"""
# %%
import pandas as pd
import os
from typing import List
from dataclasses import dataclass
import networkx as nx
from itertools import product

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
    def __init__(self, data_folder: str, layer_names: List[str]):
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


        # Define the years, locations, scenarios and additionalSpecifications with the inflows file as the defining basis
        years = inflows_df['Year'].unique() if 'Year' in inflows_df.columns else [None]
        scenarios = inflows_df['Scenario'].unique() if 'Scenario' in inflows_df.columns else [None]
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
            tcs_df_selection = tcs_df_selection[InputDataFormat.TCs_columns].replace('n/a','')

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


    def solve_models_and_write_to_output(self) -> pd.DataFrame:
        """
        Solve all entries in the variable self.input_data. Creates an output file where the solution is stored.
        """
        full_solution = pd.DataFrame(columns=["Year","Scenario","Location","additionalSpecification","Stock/Flow ID","Layer 1","Layer 2","Layer 3","Layer 4","Value"])
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

            # Add the solution to the full output file
            full_solution = pd.concat([full_solution, solution],ignore_index=True)

        # Sort the result, and select only the relevant columns and rows.
        full_solution = full_solution.sort_values(by=['Year','Scenario', 'Location','additionalSpecification', 'Stock/Flow ID', 'Layer 1','Layer 2','Layer 3','Layer 4'])
        empty_cols = [col for col in ["Scenario", "Location", "additionalSpecification", "Year"] if full_solution[col].isna().all()]
        full_solution = full_solution.drop(columns=empty_cols)
        full_solution = full_solution[full_solution.Value!=0]
        full_solution.to_csv(os.path.join(self.data_folder, OUTPUT_DATA_FOLDER_NAME, SOLUTION_FILENAME),index=False)
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
        Use the flows into a specific process together with the TCs for that process to determine the outflows of that process.
        """
        def process_outflow(process_inflow: pd.DataFrame, tcs: pd.DataFrame, input_layer: str, target_layer: str):
            """
            Apply all TCs for the given input layer and target layer.
            """
            if input_layer==target_layer:
                # A same-layer TC carries a resource to another flow unchanged --
                # a component does not turn into a different component -- so the
                # two keys must name the same resource, which the loader enforces
                # (DEFECTS.md 2.5). Match on Input_layer_key: matching on
                # TC_target_key instead, as this did, moved the WRONG resource
                # whenever the two keys differed, silently and by whatever the
                # two happened to hold.
                tcs_layer = tcs[(tcs["Input_layer"]==input_layer)&(tcs["TC_target_layer"]==target_layer)][["Input_layer_key","value"]]
                tcs_layer = tcs_layer.rename(columns={"Input_layer_key": input_layer, "value": "TC"})
                process_outflow = process_inflow.merge(tcs_layer, on=[input_layer], how='left')
            else:
                tcs_layer = tcs[(tcs["Input_layer"]==input_layer)&(tcs["TC_target_layer"]==target_layer)][["Input_layer_key","TC_target_key","value"]]
                
                # This snippet of code fills the data gaps when the Input_layer_key is left empty.
                if int(target_layer[-1])-int(input_layer[-1])==1: # if the layers follow each other, e.g Layer 1->Layer 2
                    unique_list = process_inflow[input_layer].unique().tolist()
                    tcs_layer['Input_layer_key'] = tcs_layer['Input_layer_key'].apply(lambda x: unique_list if x == '' else x)
                    tcs_layer = tcs_layer.explode('Input_layer_key')
                    tcs_layer = tcs_layer.drop_duplicates(subset=['TC_target_key', 'Input_layer_key'])

                # This snippet is taken from chatgpt, i have no idea but it works
                if tcs_layer['Input_layer_key'].eq('').any():
                    # Apply the TC to **all rows** of that input layer
                    keys_to_expand = process_inflow[input_layer].dropna().unique().tolist()
                    tcs_layer = tcs_layer.copy()
                    tcs_layer['Input_layer_key'] = tcs_layer['Input_layer_key'].replace('', None)
                    tcs_layer = tcs_layer.explode('Input_layer_key')
                    tcs_layer = pd.concat([
                        tcs_layer[tcs_layer['Input_layer_key'].notna()],
                        pd.DataFrame([
                            {'Input_layer_key': key, 'TC_target_key': row['TC_target_key'], 'value': row['value']}
                            for _, row in tcs_layer[tcs_layer['Input_layer_key'].isna()].iterrows()
                            for key in keys_to_expand
                        ])
                    ], ignore_index=True)
                
                
                tcs_layer.rename(columns={"Input_layer_key": input_layer, "TC_target_key": target_layer, "value": "TC"}, inplace=True)
                process_outflow = process_inflow.merge(tcs_layer, on=[input_layer, target_layer], how='left')
            # Rows with no matching TC get a TC of 0, i.e. none of that resource is
            # transferred. This must be an assignment, not fillna(inplace=True): under
            # copy-on-write the inplace form silently does nothing, leaving the TC as
            # NaN. The Value!=0 filter below then prunes nothing and the intermediate
            # result grows 16x per process step.
            process_outflow["TC"] = process_outflow["TC"].fillna(0)
            process_outflow["Value"] *= process_outflow["TC"]
            return process_outflow[process_outflow["Value"]!=0.0].drop(columns=["TC"])

        process_outflows = []
        for in_layer in ["Layer 1","Layer 2","Layer 3","Layer 4"]:
            for out_layer in ["Layer 1","Layer 2","Layer 3","Layer 4"]:
                process_outflow_iter = process_outflow(process_inflow, process_tcs, in_layer, out_layer)
                process_outflows.append(process_outflow_iter)

        return pd.concat(process_outflows, ignore_index=True)


class HelperFunctions:
    @staticmethod
    def is_year_match(year_data, year_target):
        """
        Helper function to check if a year is an exact match or within a range.

        Args:
            year_data: The year value(s) in the column (can be int or str).
            year_target: The year instance to be matched (can be int or str).

        Returns:
            True if there is a match, otherwise False.
        """
        year_target = str(year_target)
        year_data = str(year_data)
        if year_data == year_target:
            return True

        # Handle ranges in year_data
        if '-' in year_data:
            start, end = map(int, year_data.split('-'))
            if start <= int(year_target) <= end:
                return True

        # Handle ranges in year_target
        if '-' in year_target:
            start, end = map(int, year_target.split('-'))
            if start <= int(year_data) <= end:
                return True

        return False
    
    @staticmethod
    def select_df_by_year_scenario_location(df: pd.DataFrame, year: str | None, location: str | None, scenario:  str | None, additional_specification: str | None) -> pd.DataFrame:
        check_year = 'Year' in df.columns and df['Year'].dropna().astype(bool).any()
        check_scenario = 'Scenario' in df.columns and df['Scenario'].dropna().astype(bool).any()
        check_location = 'Location' in df.columns and df['Location'].dropna().astype(bool).any()
        check_additional_specification= 'additionalSpecification' in df.columns and df['additionalSpecification'].dropna().astype(bool).any()

        
        return df.loc[
            (df['Year'].apply(lambda y: HelperFunctions.is_year_match(y, year)) if check_year else pd.Series(True, index=df.index)) & 
            (df['Scenario'] == scenario if check_scenario else pd.Series(True, index=df.index)) & 
            (df['Location'] == location if check_location else pd.Series(True, index=df.index)) & 
            (df['additionalSpecification'] == additional_specification if check_additional_specification else pd.Series(True, index=df.index))
            ].drop(columns=['Year','Scenario','Location', 'additionalSpecification'], errors='ignore')