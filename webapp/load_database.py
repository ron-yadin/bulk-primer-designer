import os

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# load mysql db secrets from .env
load_dotenv()
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")


def load_database(submitter, submission_name, input_df, output_df):

    # check that .env file has been configured correctly
    try:
        for env_var in [MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]:
            assert env_var != None
            assert env_var != ""
            assert type(env_var) == str
    except:
        error_message_str = f"""Error in .env file configuration!
        Environtment variables MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE must be set
        as valid values in .env file in project directory."""
        return False, error_message_str

    # connect to MySQL database
    mydb = mysql.connector.connect(
        host="mysql",
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    mycursor = mydb.cursor()

    # add record to submissions table
    sql = "INSERT INTO submissions (submitter, submission_name) VALUES (%s, %s)"
    val = (submitter, submission_name)
    mycursor.execute(sql, val)
    mydb.commit()

    # add records to amplicons table
    submission_id = mycursor.lastrowid
    inputs_vals = []

    for index, row in input_df.iterrows():
        inputs_vals.append((submission_id, row["amplicon name"], row["sequence"]))

    inputs_sql = "INSERT INTO amplicons (submission_id, amplicon_name, DNA_sequence) VALUES (%s, %s, %s)"
    mycursor.executemany(inputs_sql, inputs_vals)
    mydb.commit()

    # TODO: add amplicon sequence or amplicon name to output df to merge amplicon ID to primer options
    # add records to primers_all_options table
    mycursor.execute(f"SELECT * FROM amplicons WHERE submission_id = {submission_id}")
    inputs_rows = mycursor.fetchall()
    inputs_rows_df = pd.DataFrame(
        inputs_rows,
        columns=["amplicon_id", "submission_id", "amplicon_name", "DNA_sequence"],
    )

    merged_amplicons_output_df = output_df.merge(
        inputs_rows_df, how="left", on="amplicon_name"
    )

    outputs_vals = list(
        zip(
            [float(submission_id)] * len(merged_amplicons_output_df),
            merged_amplicons_output_df["amplicon_id"].astype(float).values,
            merged_amplicons_output_df["primer_name"].values,
            merged_amplicons_output_df["direction"].values,
            merged_amplicons_output_df["option_group_index"].astype(float).values,
            merged_amplicons_output_df["primer_sequence"].values,
            merged_amplicons_output_df["gc_clamp"].astype(float).values,
            merged_amplicons_output_df["length"].astype(float).values,
            merged_amplicons_output_df["gc_percentage"].astype(float).values,
            merged_amplicons_output_df["melt_temperature"].astype(float).values,
            merged_amplicons_output_df["melt_temp_target_distance"]
            .astype(float)
            .values,
            merged_amplicons_output_df["gc_percentage_target_distance"]
            .astype(float)
            .values,
            merged_amplicons_output_df["melt_temperature_score"].astype(float).values,
            merged_amplicons_output_df["gc_percentage_score"].astype(float).values,
            merged_amplicons_output_df["total_score"].astype(float).values,
            merged_amplicons_output_df["option_group_rank"].astype(float).values,
        )
    )
    print(outputs_vals, flush=True)
    outputs_sql = """
    INSERT INTO primers_all_options (
        submission_id, 
        amplicon_id, 
        primer_name, 
        direction,
        option_group_index,
        primer_sequence,
        gc_clamp,
        `length`,
        gc_percentage,
        melt_temperature,
        melt_temp_target_distance,
        gc_percentage_target_distance,
        melt_temperature_score,
        gc_percentage_score,
        total_score,
        option_group_rank)
    VALUES (%s, %s, %s, %s, 
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s)
    """
    mycursor.executemany(outputs_sql, outputs_vals)
    mydb.commit()

    return True, "Database load successful"
