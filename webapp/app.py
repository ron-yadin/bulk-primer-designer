import os
import zipfile
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import mysql.connector
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory

import csv_transform  # custom csv_transform module

# load mysql db secrets from .env
load_dotenv()
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():
    """
    Flask route handler for the home page.

    Supports both GET and POST requests. For GET requests, renders the home page.
    For POST requests, processes the uploaded CSV file, creates a zip file containing
    input and output CSVs,  adds submission details to a MySQL database, and renders
    the home page with relevant information.

    Returns:
    - GET request: Rendered HTML template for the home page.
    - POST request:
        - Rendered HTML template with error message if file extension is not .csv or
          if the CSV processing encounters an error.
        - Rendered HTML template with processed input and output DataFrames if successful,
          along with details stored in a MySQL database.
    """

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
        return render_template("error.html", message=error_message_str)

    # run this block upon "POST" request from CSV upload
    if request.method == "POST":
        # get file object from html form
        submitter = request.form.get("submitter")
        file = request.files["file"]
        if file:
            # get filename, separate name & extension
            filename = file.filename
            filename_no_ext, file_ext = tuple(filename.split("."))

            # verify file extension type
            try:
                assert file_ext.lower() == "csv"
            except:
                error_message_str = (
                    f"Exptected .csv file extension, but .{file_ext} detected"
                )
                return render_template("error.html", message=error_message_str)

            # get current time (US/Pacific) & format for output names
            current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
            formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            # create zip file name and path variables
            zip_file_name = f"{formatted_time}_{filename_no_ext}.zip"
            zip_file_path = f"/app/data/{zip_file_name}"

            # process csv file object, return both input and output dfs
            input_valid, input_df, output_df = csv_transform.process_csv(file)

            # handle cases of invalid input, direct user to the error message page
            if input_valid == False:
                # in this case, error_message_str stored in input_df variable
                return render_template("error.html", message=input_df)

            # connect to MySQL database
            mydb = mysql.connector.connect(
                host="mysql",
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
            )
            mycursor = mydb.cursor()

            # add record to submission table
            sql = "INSERT INTO submissions (submitter, submission_name) VALUES (%s, %s)"
            val = (submitter, filename_no_ext)
            mycursor.execute(sql, val)
            mydb.commit()

            # add records to inputs table
            submission_id = mycursor.lastrowid
            inputs_vals = []

            for index, row in input_df.iterrows():
                inputs_vals.append((submission_id, row["x"], row["y"]))

            inputs_sql = "INSERT INTO inputs (submission_id, x, y) VALUES (%s, %s, %s)"
            mycursor.executemany(inputs_sql, inputs_vals)
            mydb.commit()

            # add records to outputs table
            mycursor.execute(
                f"SELECT * FROM inputs WHERE submission_id = {submission_id}"
            )
            inputs_rows = mycursor.fetchall()
            inputs_rows_df = pd.DataFrame(
                inputs_rows, columns=["input_id", "submission_id", "x", "y"]
            )
            outputs_vals = list(
                zip(
                    inputs_rows_df["input_id"].astype(float).values,
                    output_df["sum"].astype(float).values,
                )
            )
            outputs_sql = "INSERT INTO outputs (input_id, sum) VALUES (%s, %s)"
            mycursor.executemany(outputs_sql, outputs_vals)
            mydb.commit()

            # create BytesIO object to store the zip file in memory
            zip_buffer = BytesIO()

            # create a ZipFile object
            with zipfile.ZipFile(
                zip_buffer, "a", zipfile.ZIP_DEFLATED, False
            ) as zip_file:
                # write input CSV to the zip file
                zip_file.writestr(
                    f"{formatted_time}_{filename_no_ext}_input.csv",
                    input_df.to_csv(index=False),
                )
                # write output CSV to the zip file
                zip_file.writestr(
                    f"{formatted_time}_{filename_no_ext}_output.csv",
                    output_df.to_csv(index=False),
                )

            # move buffer position to the beginning to prepare for reading
            zip_buffer.seek(0)
            # write the zip file to the Docker volume
            with open(zip_file_path, "wb") as zip_file:
                zip_file.write(zip_buffer.read())
            # render index.html file, sending all relevant outputs and variables
            return render_template(
                "index.html",
                tables=[output_df.to_html(classes="data")],
                file_created=True,
                file_path=zip_file_path,
                result_file_name=zip_file_name,
            )

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    """
    Flask route handler for downloading files from the '/app/data/' directory.

    Parameters:
    - filename (str): The name of the file to be downloaded.

    Returns:
    - File download response: Downloads the specified file as an attachment.
    """
    return send_from_directory("/app/data/", filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
