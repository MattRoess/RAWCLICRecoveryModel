# -*- coding: utf-8 -*-
"""

@Author: Adrien Perello / Harmjan de Vries
@Date: 24.03.2024
"""
# %%
import numpy as np
import pandas as pd
import os
from scipy.sparse import coo_array, csc_array, csr_array, eye_array, linalg
from typing import List
from dataclasses import dataclass
from itertools import product

from src.rest import add_rest
from src.selection import chosen_scenario, chosen_years, is_year_match, select
from src.tc_precedence import apply_precedence
from src.validate_inputs import InputDataError, validate


# Definition of file/folder names within the overarching data directory
OUTPUT_DATA_FOLDER_NAME = "output_data"
INPUT_DATA_FOLDER_NAME = "input_data"

INPUTS_FILENAME = "inputs.csv"
COMPOSITION_FILENAME = "composition.csv"
SOLUTION_FILENAME = "solution_LA_model.csv"


@dataclass
class InputDataFormat:
    """
    Dataclass defining mandatory columns for each input table
    """
    input_columns = ['Stock/Flow ID','Substance_main_parent','Value']
    TCs_columns = ['Input_FlowID','Input_layer','Input_layer_key','Output_FlowID','TC_target_layer','TC_target_key','value']
    composition_columns = ['Stock/ID','Layer 1','Layer 2','Layer 3','Layer 4', 'Value']

    optional_columns = ['Location','Year','Scenario', 'additionalSpecification']

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
            'additionalSpecification': str,
            'DQS': float,
            'CV': float,
        }


class RecoveryModelLA:
    """Class representing the Linear Algebra based recovery model, as documented in the doc/Recovery_model_documentation.pdf"""
    def __init__(self, data_folder: str, layer_names: List[str],
                 scenario: str | None = None, years: str | None = None,
                 working_unit: str | None = None,
                 tables: dict | None = None):
        """
        Initialize the System class.
         - Defines and creates folder structure
         - Creates matrices for composition, TC and input data
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
        # The inflow and composition can be handed over in memory rather than
        # read from CSVs. That is how the upstream data reaches the model: it
        # lives in .npy arrays, and writing a copy of it to disk on the way past
        # would be a second version of the truth that goes stale.
        self._tables = tables

        # Check the input tables before anything is encoded. This engine maps
        # every key to an integer with .replace(), which leaves an unknown key
        # as a string and fails later inside np.dot with a message naming
        # neither the column nor the value (DEFECTS.md 2.7).
        validate(data_folder, tables)

        if not os.path.exists(os.path.join(self.data_folder, OUTPUT_DATA_FOLDER_NAME)):
            os.makedirs(os.path.join(self.data_folder, OUTPUT_DATA_FOLDER_NAME))

        # Read excel files
        self.input_matrices = self.read_input_data()

    def read_input_data(self) -> dict:
        """
        Read inflows, composition and TCs files and creates the matrices to be used in the model.

        Returns:
            A dictionary with the input inflows, compositions and TCs for each year, scenario, location and additionalSpecification
        """
        # Load the input files
        read = dict(dtype=InputDataFormat.dtypes, keep_default_na=False, na_values=[])
        given = self._tables or {}
        inflows_df = given.get('inputs')
        if inflows_df is None:
            inflows_df = pd.read_csv(
                os.path.join(self.data_folder, INPUT_DATA_FOLDER_NAME, INPUTS_FILENAME),
                **read)
        inflows_df = inflows_df.copy()
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

        composition_df = given.get('composition')
        if composition_df is None:
            composition_df = pd.read_csv(
                os.path.join(self.data_folder, INPUT_DATA_FOLDER_NAME,
                             COMPOSITION_FILENAME), **read)
        composition_df = composition_df.copy()
        tcs_df = given.get('tcs')
        if tcs_df is None:
            # Wherever this case keeps them: the TCs sheet of case.xlsx, or
            # TCs.csv for a hand-built folder (src/case_tables.py).
            from src import case_tables
            tcs_df = case_tables.read(self.data_folder, 'TCs')
        tcs_df = tcs_df.copy()

        # Real composition data is incomplete: the copper in a wire is often
        # known when the wire's own weight is not. A parent is therefore the sum
        # of its known children plus a derived `rest`, so that closure to 1 holds
        # at every layer and the unspecified part is visible rather than absent.
        # Without this the shortfall simply had no row (src/rest.py).
        composition_df, self.rest_notes = add_rest(composition_df)


        # Same precedence resolution the optimized engine applies, on the same
        # table, before this engine's own encoding touches it (DEFECTS.md 2.3).
        tcs_df = apply_precedence(tcs_df, composition_df)

        tcs_df.loc[tcs_df['Input_layer_key'] == '', 'Input_layer'] = ''

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


        # Create required variables for decoding and encoding the data into sparse matrices.
        # - encoding_dict maps each flow or resource to a unique integer
        # - decoding_dict maps the integer back to the flow or resource
        # - dims is the number of different options for each flow or layer
        # - size is the size of the complete vectors and matrices
        self.decoding_dict = {}
        # SORTED, not just set(). Set iteration order for strings depends on
        # Python's per-process hash randomisation, so this encoding -- and with
        # it the ordering of the sparse system and the accumulation order in
        # spsolve -- used to change between runs. See DEFECTS.md section 3.5.
        all_flows = sorted(set(tcs_df['Input_FlowID']).union(set(tcs_df['Output_FlowID'])))
        self.decoding_dict['Stock/Flow ID'] = dict(enumerate(all_flows))
        for layer_index in range(0,4):
            layer_name = self.layer_names[layer_index]
            # Sorted for the same reason as all_flows above. 'empty' stays
            # first: it is index 0 by construction, not by name.
            layer_unique_resources = ['empty'] + sorted(
                set(composition_df['Layer ' + str(layer_index + 1)].dropna()))
            self.decoding_dict[layer_name] = dict(enumerate(layer_unique_resources))
        self.encoding_dict = {col: {v: k for k, v in dct.items()} for col, dct in self.decoding_dict.items()}
        self.dims = self.get_dims() 
        self.size = np.prod(self.dims, dtype=int)

        input_matrices = []
        for year, scenario, location, additional_specification in product(years, scenarios, locations, additional_specifications):
            try:
                inflows_vector = self.create_inflows_vector(inflows_df=inflows_df, year=year,scenario=scenario, location=location, additional_specification=additional_specification)
            except AssertionError:
                # If there is no inflows for this year, location, scenario and additionalSpecification combination, this error is raised and we skip the combination
                continue
            composition_matrix = self.create_composition_matrix(composition_df=composition_df, year=year, scenario=scenario, location=location,additional_specification=additional_specification)
            tcs_matrix = self.create_tcs_matrix(tcs_df=tcs_df, year=year, scenario=scenario, location=location,additional_specification=additional_specification)

            input_matrices.append({
                        "Year":year,
                        "Scenario": scenario,
                        "Location": location,
                        "additionalSpecification": additional_specification,
                        "inflows_vector": inflows_vector,
                        "composition_matrix": composition_matrix,
                        "tcs_matrix": tcs_matrix
                    })
        return input_matrices
                    
    def encode(self, frame: pd.DataFrame, column: str, mapping: dict,
               table: str) -> pd.Series:
        """
        Replace a key column with its integer code, naming anything unmapped.

        `.map()` rather than `.replace()`. `.replace()` leaves an unmapped
        value as the original STRING, which then reached ravel_multi_index's
        arithmetic and failed as `TypeError: unsupported operand type(s) for
        +: 'int' and 'str'` -- naming neither the column, the value nor the
        file (DEFECTS.md 2.7). `.map()` yields NaN for a miss, which can be
        said out loud.

        src/validate_inputs.py refuses an unknown key before any of this runs.
        This is the second line, for a caller that hands tables over in memory
        and skips the file checks, and for anything that becomes unknown only
        after the table has been rewritten.
        """
        encoded = frame[column].map(mapping)
        missing = encoded.isna()
        if missing.any():
            unknown = sorted({str(value) for value in frame.loc[missing, column]})
            shown = ', '.join(repr(value) for value in unknown[:8])
            more = f' and {len(unknown) - 8} more' if len(unknown) > 8 else ''
            raise InputDataError(
                f"{self.data_folder}: {table} has {len(unknown)} value(s) in "
                f"column '{column}' that appear nowhere the model can place "
                f"them:\n    {shown}{more}\n\n"
                f"A key has to exist in the composition (for a resource) or in "
                f"the transfer\ncoefficients (for a flow) before it can be "
                f"encoded. Check the spelling\nagainst those tables.")
        return encoded

    def create_inflows_vector(self, inflows_df: pd.DataFrame, year:str, scenario: str, location:str, additional_specification: str) -> csc_array:
        """
        Create the 1XN composition input vector for a specific year, scenario, location and additionalSpecification

        :returns:
            An CSR matrix containing the inflows values at appropriate indices
        """
        # Filter the selected year, scenario, location and additionalSpecification
        inflows_df = select(inflows_df, year, scenario, location,
                            additional_specification, drop=False)
        inflows_df = inflows_df[InputDataFormat.input_columns]
        if len(inflows_df)==0:
            raise AssertionError("This combination of year, scenario, location and additionalSpecification does not exist.")

        # Create a new dataframe that expresses the flows/resources in encodable form.
        # Rows are collected in a list and the frame built once: appending row by row
        # is quadratic, and DataFrame._append was removed in pandas 3.
        encoding_columns = ['Stock/Flow ID'] + self.layer_names
        encoding_rows = []
        for _, row in inflows_df.iterrows():
            new_row = {}
            new_row['Stock/Flow ID'] = row['Stock/Flow ID']
            new_row[self.layer_names[0]] = row['Substance_main_parent']
            for layer in self.layer_names[1:]:
                new_row[layer] = 'empty'
            encoding_rows.append(new_row)
        # Column order is enforced because the frame is later read positionally (.values)
        encoding_df = pd.DataFrame(encoding_rows, columns=encoding_columns)

        for column, mapping in self.encoding_dict.items():
            encoding_df[column] = self.encode(encoding_df, column, mapping,
                                             'the inflow table')

        inflows_values = inflows_df['Value'].values
        inflows_rows = encoding_df.values

        input_rows = HelperFunctions.ravel_multi_index(multi_index=inflows_rows, dimensions=self.dims)
        return HelperFunctions.create_vector(values=inflows_values, rows=input_rows, size=self.size)

    def create_composition_matrix(self, composition_df: pd.DataFrame, year:str, scenario: str, location:str, additional_specification: str) -> csr_array:
        """
        Reads composition input dataframe for a year, scenario, location and additionalSpecification and creates a 
        NxN matrix that can be used for the model computation.
        See the written documentation for explanation of how these matrices are created.

        :returns:
            A CSR matrix containing the composition values at appropriate indices
        """
        # Select the rows for this year, scenario, location and
        # additionalSpecification. Shared with the optimized engine: this used
        # to match by substring, so 'BAU' also selected 'BAU_high' and the two
        # engines quietly disagreed (DEFECTS.md 2.4).
        composition_df = select(composition_df, year, scenario, location,
                                additional_specification, drop=False)


        composition_df = composition_df[InputDataFormat.composition_columns]
        composition_df[['Layer 1','Layer 2','Layer 3','Layer 4']] = composition_df[['Layer 1','Layer 2','Layer 3','Layer 4']].replace('','empty')
        composition_df.columns = ['Stock/Flow ID'] + self.layer_names + ['Value']

        # Encode all columns that have an encoding. 
        for column, mapping in self.encoding_dict.items():
            composition_df[column] = self.encode(composition_df, column, mapping,
                                                'the composition table')

        composition_values = composition_df["Value"].values

        # The row value is the contained resource, and the column value is the containing resource. 
        # This means the row value is the specified composition and the column value is obtained by replacing the smallest material with 'empty'.
        composition_rows = composition_df[['Stock/Flow ID'] + self.layer_names].values
        composition_cols = composition_df[['Stock/Flow ID'] + self.layer_names].apply(HelperFunctions.set_rightmost_nonzero_to_zero, axis=1).values
        composition_rows = HelperFunctions.ravel_multi_index(multi_index=composition_rows, dimensions=self.dims)
        composition_cols = HelperFunctions.ravel_multi_index(multi_index=composition_cols, dimensions=self.dims)
        comp_matrix = HelperFunctions.create_sparse_matrix(values=composition_values, rows=composition_rows, cols=composition_cols, size=self.size)
        return comp_matrix

    def create_tcs_matrix(self, tcs_df: pd.DataFrame, year: str, location: str, scenario: str, additional_specification: str) -> csr_array:
        """
        Read the input TCs and converts it to a NxN matrix that can be used for the model computation. 
        See the written documentation for explanation of how these matrices are created.

        Returns:
            A CSR matrix containing the TC values at appropriate indices
        """
        # Same shared selection as the composition above (DEFECTS.md 2.4).
        tcs_df = select(tcs_df, year, scenario, location,
                        additional_specification, drop=False)


        tcs_df = tcs_df[InputDataFormat.TCs_columns]

        # This snippet explodes all values with a *, e.g P* will be exploded to make an entry for every product.
        def fill_star_values(row, column_key, column_layer):
            if '*' in row[column_key]:
                return list(self.encoding_dict[row[column_layer]].keys())
            return row[column_key]
        tcs_df['Input_layer_key'] = tcs_df.apply(lambda row: fill_star_values(row, 'Input_layer_key', 'Input_layer'), axis=1)
        tcs_df['TC_target_key'] = tcs_df.apply(lambda row: fill_star_values(row, 'TC_target_key', 'TC_target_layer'), axis=1)
        tcs_df = tcs_df.explode('Input_layer_key')
        tcs_df = tcs_df.explode('TC_target_key')

        # We create a sorted version of the tcs_df, where the TCs that are more important are sorted towards
        # the bottom, so that they are processed last and overwrite previous TCs. This sort puts the highest level (product) on top
        # and the lowest level (element) to the bottom of the DF.
        layer_order = {name: i for i, name in enumerate(self.layer_names)}
        tcs_df['input_layer_sort'] = tcs_df['Input_layer'].map(layer_order)
        tcs_df = tcs_df.sort_values(by='input_layer_sort',ascending=True)
        
        # Now we create a new dataframe that has the same shape as the final matrix. We fill it row by row and use it to create the final matrix.
        new_tcs_columns = ['Input_FlowID'] + ['Input_'+layer_name for layer_name in self.layer_names]+['Output_FlowID'] +['Output_'+layer_name for layer_name in self.layer_names]+['value']
        # As above: collect rows and build the frame once, rather than appending in a loop.
        new_tcs_rows = []
        for _, row in tcs_df.iterrows():
            # For each TC entry, fill the values one-by-one.
            new_row = {}
            new_row['Input_FlowID'] = row['Input_FlowID']
            new_row['Output_FlowID'] = row['Output_FlowID']
            new_row['value'] = row['value']
            for layer in self.layer_names:
                if row['Input_layer']==layer:
                    new_row['Input_'+layer] = row['Input_layer_key']
                    new_row['Output_'+layer] = row['Input_layer_key']
                elif row['TC_target_layer']==layer:
                    new_row['Input_'+layer] = row['TC_target_key']
                    new_row['Output_'+layer] = row['TC_target_key']
                else:
                    new_row['Input_'+layer] = list(self.decoding_dict[layer].values())
                    new_row['Output_'+layer] = list(self.decoding_dict[layer].values())
            new_tcs_rows.append(new_row)
        new_tcs_df = pd.DataFrame(new_tcs_rows, columns=new_tcs_columns)


        for layer in self.layer_names:
            new_tcs_df = new_tcs_df.explode(['Input_'+layer, 'Output_'+layer])

        # Only keep the highest priority entry for each combination of layers, remove the rest.
        new_tcs_df = new_tcs_df.groupby([col for col in new_tcs_df.columns if col != 'value'], as_index=False).last()

        flows = self.encoding_dict['Stock/Flow ID']
        for side in ('Input_FlowID', 'Output_FlowID'):
            new_tcs_df[side] = self.encode(new_tcs_df, side, flows,
                                          'the transfer coefficients')
        for layer in self.layer_names:
            encoding = self.encoding_dict[layer]
            for side in ('Input_' + layer, 'Output_' + layer):
                new_tcs_df[side] = self.encode(new_tcs_df, side, encoding,
                                              'the transfer coefficients')

        tcs_values = new_tcs_df["value"].values
        tcs_cols = new_tcs_df[['Input_FlowID']+['Input_'+layer for layer in self.layer_names]].values
        tcs_rows = new_tcs_df[['Output_FlowID']+['Output_'+layer for layer in self.layer_names]].values
        tc_rows = HelperFunctions.ravel_multi_index(multi_index=tcs_rows, dimensions=self.dims)
        tc_cols = HelperFunctions.ravel_multi_index(multi_index=tcs_cols, dimensions=self.dims)
        tc_matrix = HelperFunctions.create_sparse_matrix(values=tcs_values, cols=tc_cols, rows=tc_rows, size=self.size)
        return tc_matrix

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
        Solve all entries in the variable self.input_matrices, which contains the model matrices
        for every year, location, scenario and additionalSpecification Creates an ouput CSV where the solutions are stored.
        """
        columns = ["Year", "Scenario", "Location", "additionalSpecification",
                   "Stock/Flow ID", "Layer 1", "Layer 2", "Layer 3", "Layer 4", "Value"]
        solutions = []
        for entry in self.input_matrices:
            solution = self.solve_model(
                inflows_vector=entry["inflows_vector"],
                composition_matrix=entry["composition_matrix"],
                tcs_matrix=entry["tcs_matrix"]
            )
            solution['Year'] = entry['Year']
            solution['Scenario'] = entry['Scenario']
            solution['Location'] = entry['Location']
            solution['additionalSpecification'] = entry['additionalSpecification']
            solutions.append(solution)

        # Concatenated once. Seeding from pd.DataFrame(columns=[...]) and growing
        # it in the loop made every column object dtype, so Value came back as
        # boxed Python floats (DEFECTS.md 3.4). Same fix as the optimized engine,
        # so the two keep returning the same thing.
        full_solution = (pd.concat(solutions, ignore_index=True) if solutions
                         else pd.DataFrame({name: pd.Series(dtype='float64' if name == 'Value'
                                                            else 'object')
                                            for name in columns}))

        # Sort the result, and select only the relevant columns.
        full_solution = full_solution.sort_values(by=['Year','Scenario', 'Location','additionalSpecification','Stock/Flow ID', 'Layer 1','Layer 2','Layer 3','Layer 4'])
        empty_cols = [col for col in ["Scenario", "Location", "additionalSpecification", "Year"] if full_solution[col].isna().all()]
        full_solution = full_solution.drop(columns=empty_cols)

        full_solution.to_csv(self.output_path(SOLUTION_FILENAME), index=False)
        return full_solution


    def solve_model(self, inflows_vector: csc_array, composition_matrix: csr_array, tcs_matrix: csr_array) -> pd.DataFrame:
        """
        - Solve the system of linear equations
        - Return the solution back to human-readable interpretation

        Returns:
            Dataframe containing the system's solution
        """
        # Solve the system of equations
        arr = linalg.spsolve(eye_array(self.size) - tcs_matrix - composition_matrix, inflows_vector)

        # Decode the solution
        mask = arr != 0
        int_idx = np.nonzero(mask)[0]
        midx = HelperFunctions.unravel_multi_index(indices=int_idx,dimensions=self.dims)

        idx = pd.MultiIndex.from_arrays(midx.T, names=['Stock/Flow ID'] + self.layer_names)
        solution = pd.Series(arr[mask], index=idx)
        solution = solution[solution != 0]

        solution = self.decode_label(solution.reset_index())
        solution = solution.replace('empty','')
        solution.columns = ['Stock/Flow ID', 'Layer 1', 'Layer 2','Layer 3', 'Layer 4', 'Value']

        return solution

    def decode_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform a dataframe full of integer-based representation of resources back to human-readable string representation.
        
        Args:
            df: Dataframe to be decoded

        Returns:
            Decoded dataframe
        """
        decoded_df = df.copy()
        if isinstance(decoded_df.columns, pd.MultiIndex):
            for col in decoded_df.columns.levels[0]:
                decoded_df[col] = self.decode_label(decoded_df[col])
        else:
            for col in set(decoded_df.columns) & set(self.decoding_dict):
                decoded_df[col] = decoded_df[col].map(self.decoding_dict[col], na_action="ignore")
        return decoded_df

    def get_dims(self) -> tuple:
        """
        Get the dimension of each layer of the system. 
        - For flows, the dimension is the number of flows
        - For resources, the dimension is the number of resources in that layer + the 'empty' designation

        Returns:
            The shape of each layer of the system, which corresponds to the number of possible resources in that layer + an empty layer
        """
        return tuple(len(self.encoding_dict[layer]) for layer in ['Stock/Flow ID'] + self.layer_names)


class HelperFunctions:
    @staticmethod
    def set_rightmost_nonzero_to_zero(row: pd.Series) -> pd.Series:
        """
        Helper function to set the last of a set of values to zero
        Args:
            row: Row to be modified

        Returns:
            Modified row with the last non-zero value set to zero
        """
        nonzero_indices = row[row != 0].index
        if not nonzero_indices.empty:
            row[nonzero_indices[-1]] = 0
        return row
    
    @staticmethod
    def ravel_multi_index(multi_index: np.ndarray, dimensions: tuple) -> np.ndarray:
        """
        Helper function to convert a multi-dimensional index to a flat (1D) index

        Args:
            multi_index: Array of indices for each dimension (shape: [n, len(dimensions)])
            dimensions: The shape of the multi-dimensional array
        Returns:
            Flattened indices corresponding to the input multi-dimensional indices
        """
        dimension_products = np.array([np.prod(dimensions[i + 1 :]) if i + 1 < len(dimensions) else 1 for i in range(len(dimensions))])
        return np.dot(multi_index, dimension_products)

    @staticmethod
    def unravel_multi_index(indices: np.ndarray, dimensions: tuple) -> np.ndarray:
        """
        Helper function to convert a flat (1D) index back to the multi-dimensional representation

        Args:
            indices: Array of flat indices to be converted to multi-dimensional representation
            dimensions: The shape of the multi-dimensional array
        Returns:
            Multi-dimensional representation of the input vector
        """
        coords = np.unravel_index(indices, dimensions)
        return np.vstack(coords).T
    
    @staticmethod
    def create_sparse_matrix(values: np.ndarray, rows: np.ndarray, cols: np.ndarray, size: int) -> csr_array:
        """
        Creates a sparse matrix in CSR format based on input row, column and data values.

        Args:
            values: Values to be filled into the matrix
            rows: Row indices for each value
            cols: column indices for each value
            size: Desired size of the sparse matrix

        Returns: 
            CSR array created based on input values
        """
        # coo_array, not coo_matrix. The latter is the legacy `spmatrix`
        # branch, and this result is combined with `eye_array` from the sparse
        # ARRAY API in solve_model. The two differ in operator semantics --
        # `*` is matrix multiplication for spmatrix and elementwise for
        # sparray -- so mixing them is a trap for whoever edits this next
        # (DEFECTS.md 3.8). The type hints already said csr_array; now they
        # are true.
        return coo_array((values, (rows, cols)), shape=(size, size)).tocsr()
    
    @staticmethod
    def create_vector(values: np.ndarray, rows: np.ndarray, size: int) -> csc_array:
        """
        Create an Nx1 sparse matrix based on the specified input values

        Args:
            values: Values to be filled into the vector
            rows: Row indices for each value
            size: Desired size of the vector

        Returns:
            CSC array created based on input values -- CSC, not CSR: it is a
            single column, and the hint used to say otherwise.
        """
        cols = np.zeros_like(rows)
        coo_arr = coo_array((values, (rows, cols)), shape=(size, 1))
        return coo_arr.tocsc()
    
    @staticmethod
    def is_year_match(year_data, year_target):
        """
        Whether a row's year matches the year being solved.

        Kept as a method because callers use it; the rule itself now lives in
        src/selection.py, shared with the optimized engine. It used to match by
        substring here -- `str(year_target) in year_data` -- so 2020 also
        matched 12020, and this engine disagreed with the other one on any
        table holding more than one year (DEFECTS.md 2.4).
        """
        return is_year_match(year_data, year_target)