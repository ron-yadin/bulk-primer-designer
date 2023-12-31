import json
import os
import zipfile
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

import load_database  # custum module to load MySQL database
import primer_designer  # custom csv_transform module

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()
# Set the secret key from the environment variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")


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
            (
                input_valid,
                input_df,
                all_options_ranked_df,
                optimal_primer_results_df,
            ) = primer_designer.process_csv(file)

            # handle cases of invalid input, direct user to the error message page
            if input_valid == False:
                # in this case, error_message_str stored in input_df variable
                return render_template("error.html", message=input_df)

            # load the MySQL database
            database_load_valid, databse_load_message = load_database.load_database(
                submitter=submitter,
                submission_name=filename_no_ext,
                input_df=input_df,
                output_df=all_options_ranked_df,
            )

            # handle cases of invalid dabatase load, direct user to the error message page
            if database_load_valid == False:
                return render_template("error.html", message=databse_load_message)

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
                # write all_options_ranked_df CSV to the zip file
                zip_file.writestr(
                    f"{formatted_time}_{filename_no_ext}_all_options_ranked.csv",
                    all_options_ranked_df.to_csv(index=False),
                )
                # write optimal_primer_results_df CSV to the zip file
                zip_file.writestr(
                    f"{formatted_time}_{filename_no_ext}_optimal_primer_results.csv",
                    optimal_primer_results_df.to_csv(index=False),
                )

            # move buffer position to the beginning to prepare for reading
            zip_buffer.seek(0)
            # write the zip file to the Docker volume
            with open(zip_file_path, "wb") as zip_file:
                zip_file.write(zip_buffer.read())

            # subset columns to simplify table returned to html webapp
            primer_results_for_display = optimal_primer_results_df[
                [
                    "primer_name",
                    "direction",
                    "primer_sequence",
                    "length",
                    "melt_temperature",
                    "gc_percentage",
                    "gc_clamp",
                ]
            ]

            # Store variables for 'success' route in session
            session["primer_results_for_display"] = primer_results_for_display.to_json()
            session["file_created"] = True
            session["file_path"] = zip_file_path
            session["result_file_name"] = zip_file_name

            # redirect to success route to display results, and avoid resubmitting post request on refresh
            return redirect(url_for("success"))

    return render_template("index.html")


@app.route("/success")
def success():

    # Retrieve variables from session
    primer_results_for_display = pd.DataFrame(
        json.loads(session["primer_results_for_display"])
    )
    file_created = session["file_created"]
    file_path = session["file_path"]
    result_file_name = session["result_file_name"]

    # render index.html file, sending all relevant outputs and variables
    return render_template(
        "success.html",
        tables=[primer_results_for_display.to_html(classes="data")],
        file_created=file_created,
        file_path=file_path,
        result_file_name=result_file_name,
    )


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
