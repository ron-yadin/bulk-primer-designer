from io import StringIO

import pandas as pd


def process_csv(file_object_in):
    """
    Process a CSV file, performing specific transformations on the data.

    Parameters:
    - file_object_in (file-like object): A file-like object containing CSV data.

    Returns:
    - tuple: A tuple containing three elements:
        - bool: Indicates whether the input CSV file meets the expected assumptions.
        - str or pandas.DataFrame: If assumptions are not met, an error message describing the issue; otherwise, the original input DataFrame.
        - None or pandas.DataFrame: If assumptions are not met, None; otherwise, the transformed DataFrame.

    Assumptions:
    - The CSV file must have columns named 'x' and 'y'.
    - The data in these columns must be numeric (either 'int64' or 'float64').

    Transformation Logic:
    - Adds a new column 'sum' to the DataFrame, representing the row-wise sum of values in columns 'x' and 'y'.

    Note:
    - If input_valid is False, error_message contains details about the assumption violation.
    - If input_valid is True, the original DataFrame (input_df) and the transformed DataFrame (output_df) are returned.
    """
    content = file_object_in.read().decode("utf-8")
    input_df = pd.read_csv(StringIO(content))

    # check that input_df meets assumptions
    # check input columns match expected
    try:
        expected_columns = ["x", "y"]
        for col in list(input_df.columns):
            assert col in expected_columns
    except:
        error_message_str = f"Exptected columns {expected_columns}, but {list(input_df.columns)} detected"
        # If assumption not met, return input_valid as False,
        # error message in place of input_df, and output_df as None
        return False, error_message_str, None

    # check input data types match expected
    try:
        input_dtypes = list(set(list(input_df.dtypes.values)))
        for dtype in input_dtypes:
            assert dtype == "int64" or dtype == "float64"
    except:
        error_message_str = f"Exptected numeric values, but non-numeric value detected"
        # If assumption not met, return input_valid as False,
        # error message in place of input_df, and output_df as None
        return False, error_message_str, None

    # convert all values in input_df to float
    input_df = input_df.astype(float)

    # copy input_df to output_df for processing
    output_df = input_df.copy()

    # transformation logic to get from input to output
    output_df["sum"] = output_df["x"] + output_df["y"]

    # convert all values in output_df to float
    output_df = output_df.astype(float)

    # return input_valid as True if assumptions met, input_df, and output_df
    return True, input_df, output_df
