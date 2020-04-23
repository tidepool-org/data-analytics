# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that accepts all bigdata donation project donors,
and then pulls of their datasets for further processing.
"""

# %% REQUIRED LIBRARIES
from accept_new_donors_and_get_donor_list import accept_and_get_list
import datetime as dt
import pandas as pd
import subprocess as sub
import os
import glob
import time
import argparse
from multiprocessing import Pool


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "accepts new donors (shares) and grab their data"
parser = argparse.ArgumentParser(description=codeDescription)

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

parser.add_argument(
    "-s",
    "--save-donor-list",
    dest="save_donor_list",
    default=True,
    help="specify if you want to save the donor list (True/False)"
)

args = parser.parse_args()


# %% FUNCTIONS
def run_process(func_name, userid, donor_group):
    func_path = os.path.join(".", func_name)

    p = sub.Popen(
        [
             "python", func_path,
             "-d", args.date_stamp,
             "-dg", donor_group,
             "-u", userid,
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

    return


def get_all_data(userid, donor_group):

    run_process("get_single_donor_metadata.py", userid, donor_group)
    run_process("get_single_tidepool_dataset_json.py", userid, donor_group)

    return


# %% GET LATEST DONOR LIST
final_donor_list = accept_and_get_list(args)


# %% GET DONOR META DATA AND DATASETS
# use multiple cores to process
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
pool = Pool(os.cpu_count())
pool.starmap(get_all_data, zip(
    final_donor_list["userID"],
    final_donor_list["donorGroup"]
))
pool.close()
endTime = time.time()
print(
  "finshed pulling data at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
total_duration = round((endTime - startTime) / 60, 1)
print("total duration was %s minutes" % total_duration)


# %% COMBINE AND SAVE ALL DONOR METADATA
print("combining all metadata")
phi_date_stamp = "PHI-" + args.date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

metadata_path = os.path.join(
    args.data_path,
    phi_date_stamp + "-donor-data",
    phi_date_stamp + "-metadata"
)

all_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
all_metadata = pd.DataFrame()
for f in all_files:
    temp_meta = pd.read_csv(f)
    temp_meta.rename(columns={"Unnamed: 0": "userid"}, inplace=True)
    all_metadata = pd.concat(
        [all_metadata, temp_meta],
        ignore_index=True,
        sort=False
    )

all_metadata.to_csv(
    os.path.join(donor_folder, phi_date_stamp + "-donor-metadata.csv")
)
print("saving metadata...code complete")
