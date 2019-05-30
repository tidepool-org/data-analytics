# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that qualifies all bigdata donation project donors.
"""

# %% REQUIRED LIBRARIES
import datetime as dt
import os
import argparse
import time
import json
import glob
import subprocess as sub
import pandas as pd
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

parser.add_argument("-q",
                    "--qualification-criteria",
                    dest="qualification_criteria",
                    default=os.path.abspath(
                        os.path.join(
                        os.path.dirname(__file__),
                        "tidepool-qualification-criteria.json")
                    ),
                    type=argparse.FileType('r'),
                    help="JSON file to be processed, see " +
                         "tidepool-qualification-critier.json " +
                         "for a list of required fields")

parser.add_argument(
    "-s",
    "--save-dayStats",
    dest="save_dayStats",
    default="False",
    help="save the day stats used for qualifying (True/False)"
)

args = parser.parse_args()


# %% FUNCTIONS
def qualify_data(userid):

    qualify_path = os.path.join(
        ".", "qualify_single_dataset.py"
    )

    p = sub.Popen(
        [
             "python", qualify_path,
             "-d", args.date_stamp,
             "-u", userid,
#             "-q", args.qualification_criteria,
             "-s", args.save_dayStats,
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


# %% START OF CODE
date_stamp = args.date_stamp
phi_date_stamp = "PHI-" + date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

uniqueDonorList_path = os.path.join(
    donor_folder,
    phi_date_stamp + "-uniqueDonorList.csv"
)

qualCriteria = json.load(args.qualification_criteria)
qualCriteria_df = pd.DataFrame(qualCriteria)
qualifiedOn = dt.datetime.now().strftime("%Y-%m-%d")

qualify_path = os.path.join(
    donor_folder,
    args.date_stamp + "-qualified-by-" + qualCriteria["name"] + "-criteria"
)

final_donor_list = pd.read_csv(uniqueDonorList_path, low_memory=False)

# use multiple cores to process
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
pool = Pool(os.cpu_count())
pool.map(qualify_data, final_donor_list.userID.values)
pool.close()

endTime = time.time()
print("finshed at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
total_duration = round((endTime - startTime) / 60, 1)
print("total duration was %s minutes" % total_duration)

# save all metadata
all_metadata = pd.DataFrame()
metadata_path = os.path.join(qualify_path, "metadata")

all_files = glob.glob(os.path.join(metadata_path, "*.csv"))
for f in all_files:
    temp_meta = pd.read_csv(f)
    temp_meta.rename(columns={"Unnamed: 0":"userid"}, inplace=True)
    all_metadata = pd.concat(
        [all_metadata, temp_meta],
        ignore_index=True,
        sort=False
    )

all_metadata.to_csv(
    os.path.join(donor_folder, phi_date_stamp + "-qualification-metadata.csv")
)
