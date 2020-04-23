# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that gets distributions and stats for all donors,
NOTE: this needs to be refactored because it is currently set up to run
on json files that are in a snowflake path

"""

# %% REQUIRED LIBRARIES
import datetime as dt
import pandas as pd
import subprocess as sub
import os
import glob
import time
import argparse
from multiprocessing import Pool


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "get distribution and stats for all donor's json data"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument(
    "-i",
    "--input-json-data-path",
    dest="json_data_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data", "dremio", "**", "*.json"
        ),
    ),
    help="the path where json data is located"
)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="date_stamp",
    default=dt.datetime.now().strftime("%Y-%m-%d"),
    help="date, in '%Y-%m-%d' format, of the date when " +
    "donors were accepted"
)

parser.add_argument(
    "-o",
    "--output-data-path",
    dest="data_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data"
        )
    ),
    help="the output path where the data is stored"
)

args = parser.parse_args()


# %% FUNCTIONS
def run_process(json_data_path):
    userid = json_data_path[-15:-5]

    # check to see if the file was already processed
    phi_date_stamp = "PHI-" + args.date_stamp

    metadata_path = os.path.join(
        args.data_path,
        phi_date_stamp + "-donor-data",
        phi_date_stamp + "-cgm-metadata"
    )

    all_metadata_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
    if userid not in str(all_metadata_files):

        p = sub.Popen(
            [
                 "python", "get_cgm_distributions_and_stats.py",
                 "-i", json_data_path,
                 "-u", userid,
                 "-d", args.date_stamp,
                 "-o", args.data_path
             ],
            stdout=sub.PIPE,
            stderr=sub.PIPE
        )

        output, errors = p.communicate()
        output = output.decode("utf-8")
        errors = errors.decode("utf-8")

        if errors == '':
            print(output)
        else:
            print(errors)
    else:
        print(userid, "was already processed")

    return


# %% GET A LIST OF DONOR JSON FILE LOCATIONS
all_files = glob.glob(args.json_data_path, recursive=True)

# use multiple cores to process
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
pool = Pool(int(os.cpu_count()))
pool.map(run_process, all_files)
pool.close()
endTime = time.time()
print(
  "finshed pulling data at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
total_duration = round((endTime - startTime) / 60, 1)
print("total duration was %s minutes" % total_duration)
