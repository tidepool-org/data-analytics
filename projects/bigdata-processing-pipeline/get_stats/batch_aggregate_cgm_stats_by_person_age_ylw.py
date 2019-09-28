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
    dest="cgm_file_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data",
            "PHI-2019-07-17-donor-data",
            "PHI-2019-07-17-cgm-stats",
        )
    ),
    help="the path where the cgm stats data is located"
)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="date_stamp",
    default="2019-07-17",
    help="date, in '%Y-%m-%d' format, of the date when " +
    "donors were accepted"
)

parser.add_argument(
    "-o",
    "--output-data-path",
    dest="data_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data",
            "PHI-2019-07-17-donor-data",

        )
    ),
    help="the output path where the data is stored"
)

args = parser.parse_args()


# %% FUNCTIONS
def run_process(cgm_file_path):

    save_file_path = os.path.join(
        args.data_path,
        args.date_stamp + "-aggregate-cgm-stats"
    )

    p = sub.Popen(
        [
             "python", "aggregate_cgm_stats_by_person_age_ylw.py",
             "-i", cgm_file_path,
             "-o", save_file_path
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

    return


# %% GET A LIST OF CGM STATS FILES
all_files = glob.glob(os.path.join(args.cgm_file_path, "*.gz"))

# use multiple cores to process
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
pool = Pool(int(os.cpu_count()/2))
pool.map(run_process, all_files)
pool.close()
endTime = time.time()
print(
  "finshed pulling data at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
total_duration = round((endTime - startTime) / 60, 1)
print("total duration was %s minutes" % total_duration)


# %% combine all files into a single data frame
print("combining all of the output files")
all_data = pd.DataFrame()
all_output = glob.glob(os.path.join(
    args.data_path,
    args.date_stamp + "-aggregate-cgm-stats",
    "*.gz")
)
for f in all_output:
    temp_data = pd.read_csv(f, index_col=0)
    all_data = pd.concat(
        [all_data, temp_data],
        ignore_index=True,
        sort=False
    )

all_data.to_csv(
    os.path.join(
        args.data_path,
        args.date_stamp + "-aggregate-cgm-stats.csv.gz"
    )
)

print("saving one giant csv file...code complete")
